"""Explicit, resumable local research jobs for pinned catalogue scopes."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from etf_advisor.catalogue.research_scope import CatalogueScopeV1, ScopeMember, _digest
from etf_advisor.data.reference_facts import (
    LocalReferenceFacts,
    ReferenceFactsRecord,
    load_reference_facts,
)
from etf_advisor.data.research_quality import assess_research_fields
from etf_advisor.data.yahoo_budget import YahooRequestBudget
from etf_advisor.encoding import encode_fields, strict_json
from etf_advisor.research.models import ETFResearchRecord, ETFResearchSnapshot

MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
MAX_RECORD_BYTES = 256 * 1024
MAX_REFERENCE_FILES = 10


class ResearchJobError(ValueError):
    pass


class ResearchJobPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    batch_size: int = Field(default=5, ge=1, le=10)
    attempts_per_listing: int = Field(default=2, ge=1, le=3)
    yahoo_requests_per_attempt: int = Field(default=12, ge=1, le=12)
    yahoo_timeout_seconds: float = Field(default=10, gt=0, le=10)
    deadline_seconds: float = Field(default=300, ge=30, le=600)
    yahoo_response_bytes: int = Field(default=2 * 1024 * 1024, gt=0, le=2 * 1024 * 1024)
    max_age_hours: float = Field(default=120, gt=0, le=24 * 365)
    future_tolerance_minutes: float = Field(default=5, ge=0, le=60)


class ResearchAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    status: str = Field(pattern=r"^(started|succeeded|failed)$")
    code: str | None = None


class CachedResearchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_id: str
    record: dict[str, Any]
    digest: str

    @model_validator(mode="after")
    def validate_digest(self) -> CachedResearchRecord:
        if self.digest != _digest(self.record):
            raise ValueError("cached_record_digest_mismatch")
        return self


class ResearchJob(BaseModel):
    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)

    schema_id: str = Field(pattern=r"^catalogue-research-job-v1$", alias="schema")
    job_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    generation: int = Field(ge=0)
    scope: CatalogueScopeV1
    snapshot_version: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    created_at: datetime
    policy: ResearchJobPolicy
    references: list[dict[str, Any]]
    reference_digest: str
    attempts: dict[str, list[ResearchAttempt]]
    cached: dict[str, CachedResearchRecord]
    finalization: dict[str, Any] | None = None
    publication: str = Field(default="not_started", pattern=r"^(not_started|started|succeeded)$")

    @model_validator(mode="after")
    def validate_job(self) -> ResearchJob:
        ids = {member.listing_id for member in self.scope.members}
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("job_time_not_utc")
        if set(self.attempts) != ids or not set(self.cached) <= ids:
            raise ValueError("job_membership_mismatch")
        if self.reference_digest != _digest(self.references):
            raise ValueError("reference_digest_mismatch")
        for listing_id, item in self.cached.items():
            if item.listing_id != listing_id:
                raise ValueError("cached_listing_mismatch")
            if len(_bytes(item.record)) > MAX_RECORD_BYTES:
                raise ValueError("cached_record_limit_exceeded")
            if not self.attempts[listing_id] or self.attempts[listing_id][-1].status != "succeeded":
                raise ValueError("cached_attempt_mismatch")
        for listing_id, attempts in self.attempts.items():
            if len(attempts) > self.policy.attempts_per_listing:
                raise ValueError("attempt_limit_exceeded")
            if any(attempt.status == "succeeded" for attempt in attempts) != (
                listing_id in self.cached
            ):
                raise ValueError("attempt_success_mismatch")
        if self.finalization is not None:
            _validate_finalization(self)
        return self


def _bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


class ResearchRecordCollector(Protocol):
    def collect(
        self,
        listing: ScopeMember,
        snapshot_version: str,
        references: LocalReferenceFacts,
        budget: YahooRequestBudget,
        *,
        clock: Callable[[], datetime],
    ) -> ETFResearchRecord: ...


class ResearchPublisher(Protocol):
    def publish(self, snapshot: ETFResearchSnapshot) -> Any: ...


class ResearchJobStore:
    """One atomic JSON manifest per job; native lock survives process crashes."""

    def __init__(
        self, root: Path = Path(".artifacts/catalogue-research"), lock_timeout: float = 5.0
    ) -> None:
        self.root = root
        self.lock_timeout = lock_timeout

    def _path(self, job_id: str) -> Path:
        if re.fullmatch(r"[0-9a-f-]{36}", job_id) is None:
            raise ResearchJobError("invalid_job_id")
        return self.root / f"{job_id}.json"

    @contextmanager
    def lock(self, job_id: str) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(job_id).with_suffix(".lock")
        with path.open("a+b") as handle:
            handle.seek(0)
            if not handle.read(1):
                handle.seek(0)
                handle.write(b"0")
                handle.flush()
            deadline = time.monotonic() + self.lock_timeout
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt

                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(  # type: ignore[attr-defined]
                            handle.fileno(),
                            getattr(fcntl, "LOCK_EX") | getattr(fcntl, "LOCK_NB"),  # noqa: B009
                        )
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise ResearchJobError("job_lock_timeout") from exc
                    time.sleep(0.05)
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]

    def read(self, job_id: str) -> ResearchJob:
        path = self._path(job_id)
        data = path.read_bytes()
        if len(data) > 64 * 1024 * 1024:
            raise ResearchJobError("job_manifest_limit_exceeded")
        job = ResearchJob.model_validate(strict_json(data.decode("utf-8")))
        if job.job_id != job_id:
            raise ResearchJobError("job_identity_mismatch")
        return job

    def write(self, job: ResearchJob, *, expected_generation: int) -> ResearchJob:
        path = self._path(job.job_id)
        current = self.read(job.job_id) if path.exists() else None
        if (current.generation if current else -1) != expected_generation:
            raise ResearchJobError("job_generation_conflict")
        next_job = job.model_copy(update={"generation": expected_generation + 1})
        next_job = ResearchJob.model_validate(next_job.model_dump(mode="json"))
        data = _bytes(next_job.model_dump(mode="json"))
        if len(data) > 64 * 1024 * 1024:
            raise ResearchJobError("job_manifest_limit_exceeded")
        temp = path.with_name(f".{uuid4().hex}.tmp")
        try:
            with temp.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        return next_job


def _utc(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchJobError("clock_requires_utc")
    return value.astimezone(UTC)


def _references(paths: list[Path], scope: CatalogueScopeV1) -> list[dict[str, Any]]:
    if len(paths) > MAX_REFERENCE_FILES:
        raise ResearchJobError("reference_file_limit_exceeded")
    symbols = [member.symbol for member in scope.members]
    expected = {member.symbol: member.exchange for member in scope.members}
    records: dict[tuple[str, str], ReferenceFactsRecord] = {}
    for path in paths:
        loaded = load_reference_facts(path, symbols)
        for key, record in loaded.records.items():
            if key in records or expected.get(record.symbol) != record.exchange:
                raise ResearchJobError("reference_identity_conflict")
            records[key] = record
    if len(records) > 100:
        raise ResearchJobError("reference_record_limit_exceeded")
    return [records[key].model_dump(mode="json") for key in sorted(records)]


def _local_references(job: ResearchJob) -> LocalReferenceFacts:
    records = [ReferenceFactsRecord.model_validate(record) for record in job.references]
    return LocalReferenceFacts({(record.symbol, record.exchange): record for record in records})


def begin_catalogue_research(
    scope: CatalogueScopeV1,
    reference_inputs: list[Path],
    policy: ResearchJobPolicy,
    *,
    clock: Callable[[], datetime],
    identifiers: Callable[[], str] = lambda: str(uuid4()),
    store: ResearchJobStore,
) -> ResearchJob:
    scope = CatalogueScopeV1.model_validate(scope.model_dump(mode="json"))
    policy = ResearchJobPolicy.model_validate(policy)
    references = _references(reference_inputs, scope)
    job_id = identifiers()
    if re.fullmatch(r"[0-9a-f-]{36}", job_id) is None:
        raise ResearchJobError("invalid_job_id")
    job = ResearchJob(
        schema="catalogue-research-job-v1",
        job_id=job_id,
        generation=0,
        scope=scope,
        snapshot_version=f"catalogue-{job_id}",
        created_at=_utc(clock),
        policy=policy,
        references=references,
        reference_digest=_digest(references),
        attempts={member.listing_id: [] for member in scope.members},
        cached={},
    )
    with store.lock(job_id):
        return store.write(job, expected_generation=-1)


def _encoded_record(record: ETFResearchRecord) -> dict[str, Any]:
    raw = record.model_dump(mode="json")
    return {
        "symbol": raw["symbol"],
        "advisory_contract": raw["advisory_contract"],
        **encode_fields(
            {key: value for key, value in raw.items() if key not in {"symbol", "advisory_contract"}}
        ),
    }


def _validate_collected(
    record: ETFResearchRecord,
    listing: ScopeMember,
    version: str,
    created_at: datetime,
) -> dict[str, Any]:
    record = ETFResearchRecord.model_validate(record.model_dump(mode="python"))
    if record.symbol != listing.symbol or record.advisory_contract != "us-eu-v1":
        raise ResearchJobError("collected_identity_mismatch")
    if record.listing_exchange is None or record.listing_exchange.value != listing.exchange:
        raise ResearchJobError("collected_exchange_mismatch")
    for field in record.research_fields().values():
        if field.snapshot_version != version or field.ingested_at.tzinfo is None:
            raise ResearchJobError("collected_coordinate_mismatch")
    ingestion_times = {field.ingested_at for field in record.research_fields().values()}
    if len(ingestion_times) != 1 or next(iter(ingestion_times)) < created_at:
        raise ResearchJobError("collected_coordinate_mismatch")
    payload = _encoded_record(record)
    if len(_bytes(payload)) > MAX_RECORD_BYTES:
        raise ResearchJobError("cached_record_limit_exceeded")
    return payload


def _advance_one(
    job: ResearchJob,
    member: ScopeMember,
    collector: ResearchRecordCollector,
    store: ResearchJobStore,
    clock: Callable[[], datetime],
    deadline: float,
    monotonic: Callable[[], float],
) -> ResearchJob:
    attempts = {key: list(value) for key, value in job.attempts.items()}
    attempt_id = str(uuid4())
    attempts[member.listing_id].append(ResearchAttempt(attempt_id=attempt_id, status="started"))
    job = store.write(
        job.model_copy(update={"attempts": attempts}), expected_generation=job.generation
    )
    budget = YahooRequestBudget(
        deadline=deadline,
        max_requests=job.policy.yahoo_requests_per_attempt,
        request_timeout=job.policy.yahoo_timeout_seconds,
        max_response_bytes=job.policy.yahoo_response_bytes,
        monotonic=monotonic,
    )
    try:
        record = collector.collect(
            member, job.snapshot_version, _local_references(job), budget, clock=clock
        )
        budget.check()
        payload = _validate_collected(record, member, job.snapshot_version, job.created_at)
    except Exception as exc:
        code = "collection_failed"
        if budget.breached:
            code = "transport_bound_exceeded"
        elif isinstance(exc, ResearchJobError):
            code = str(exc)
        attempts = {key: list(value) for key, value in job.attempts.items()}
        attempts[member.listing_id][-1] = ResearchAttempt(
            attempt_id=attempt_id, status="failed", code=code
        )
        return store.write(
            job.model_copy(update={"attempts": attempts}), expected_generation=job.generation
        )
    attempts = {key: list(value) for key, value in job.attempts.items()}
    attempts[member.listing_id][-1] = ResearchAttempt(attempt_id=attempt_id, status="succeeded")
    cached = dict(job.cached)
    cached[member.listing_id] = CachedResearchRecord(
        listing_id=member.listing_id, record=payload, digest=_digest(payload)
    )
    return store.write(
        job.model_copy(update={"attempts": attempts, "cached": cached}),
        expected_generation=job.generation,
    )


def advance_catalogue_research(
    job_id: str,
    expected_generation: int,
    *,
    collector: ResearchRecordCollector,
    store: ResearchJobStore,
    clock: Callable[[], datetime],
    monotonic: Callable[[], float] = time.monotonic,
) -> ResearchJob:
    with store.lock(job_id):
        job = store.read(job_id)
        if job.generation != expected_generation or job.finalization is not None:
            raise ResearchJobError("job_generation_or_state_conflict")
        deadline = monotonic() + job.policy.deadline_seconds
        pending = [member for member in job.scope.members if member.listing_id not in job.cached]
        for member in pending[: job.policy.batch_size]:
            if job.attempts[member.listing_id]:
                break
            if monotonic() >= deadline:
                break
            job = _advance_one(job, member, collector, store, clock, deadline, monotonic)
            if job.attempts[member.listing_id][-1].status != "succeeded":
                break
        return job


def retry_catalogue_research(
    job_id: str,
    listing_id: str,
    previous_attempt_id: str,
    expected_generation: int,
    *,
    collector: ResearchRecordCollector,
    store: ResearchJobStore,
    clock: Callable[[], datetime],
    monotonic: Callable[[], float] = time.monotonic,
) -> ResearchJob:
    with store.lock(job_id):
        job = store.read(job_id)
        if job.generation != expected_generation or job.finalization is not None:
            raise ResearchJobError("job_generation_or_state_conflict")
        next_member = next(
            (member for member in job.scope.members if member.listing_id not in job.cached), None
        )
        if next_member is None or next_member.listing_id != listing_id:
            raise ResearchJobError("retry_not_current_member")
        attempts = job.attempts[listing_id]
        if (
            not attempts
            or attempts[-1].attempt_id != previous_attempt_id
            or attempts[-1].status not in {"failed", "started"}
            or len(attempts) >= job.policy.attempts_per_listing
        ):
            raise ResearchJobError("retry_not_authorized")
        return _advance_one(
            job,
            next_member,
            collector,
            store,
            clock,
            monotonic() + job.policy.deadline_seconds,
            monotonic,
        )


def _record_from_cache(item: CachedResearchRecord) -> ETFResearchRecord:
    # The schema-2 snapshot decoder validates exact numeric/proof wire contracts.
    from etf_advisor.encoding import decode_fields

    raw = item.record
    record = ETFResearchRecord.model_validate(
        {
            "symbol": raw["symbol"],
            "advisory_contract": raw["advisory_contract"],
            **decode_fields(
                {
                    key: value
                    for key, value in raw.items()
                    if key not in {"symbol", "advisory_contract"}
                }
            ),
        }
    )
    if _encoded_record(record) != raw:
        raise ResearchJobError("cached_record_noncanonical")
    return record


def _detached_record(record: ETFResearchRecord, at: datetime) -> ETFResearchRecord:
    updates: dict[str, Any] = {}
    for name, field in record.research_fields().items():
        updates[name] = field.model_copy(update={"ingested_at": at})
    return record.model_copy(update=updates)


def _validate_finalization(job: ResearchJob) -> ETFResearchSnapshot:
    final = job.finalization
    if not isinstance(final, dict) or set(final) != {"payload", "digest"}:
        raise ValueError("invalid_finalization")
    if len(_bytes(final["payload"])) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot_payload_limit_exceeded")
    snapshot = ETFResearchSnapshot.model_validate(final["payload"])
    if (
        snapshot.content_digest() != final["digest"]
        or snapshot.snapshot_version != job.snapshot_version
        or snapshot.universe_id != "catalogue-research-v1"
        or snapshot.universe_version != job.scope.digest
        or [record.symbol for record in snapshot.records]
        != [member.symbol for member in job.scope.members]
        or set(job.cached) != set(job.attempts)
    ):
        raise ValueError("finalization_identity_mismatch")
    for member, record in zip(job.scope.members, snapshot.records, strict=True):
        source = _record_from_cache(job.cached[member.listing_id])
        if _detached_record(source, snapshot.ingested_at) != record:
            raise ValueError("finalization_source_mismatch")
    return snapshot


def finalize_catalogue_research(
    job_id: str,
    *,
    store: ResearchJobStore,
    clock: Callable[[], datetime],
) -> ETFResearchSnapshot:
    with store.lock(job_id):
        job = store.read(job_id)
        if job.finalization is not None:
            return _validate_finalization(job)
        if set(job.cached) != {member.listing_id for member in job.scope.members}:
            raise ResearchJobError("research_incomplete")
        sources = []
        for member in job.scope.members:
            cached = job.cached[member.listing_id]
            source = _record_from_cache(cached)
            if (
                _validate_collected(source, member, job.snapshot_version, job.created_at)
                != cached.record
            ):
                raise ResearchJobError("cached_record_noncanonical")
            sources.append(source)
        at = _utc(clock)
        if at < job.created_at or any(
            field.ingested_at > at
            for record in sources
            for field in record.research_fields().values()
        ):
            raise ResearchJobError("finalization_clock_inconsistent")
        snapshot = ETFResearchSnapshot(
            schema_version=2,
            advisory_contract="us-eu-v1",
            snapshot_version=job.snapshot_version,
            universe_id="catalogue-research-v1",
            universe_version=job.scope.digest,
            ingested_at=at,
            records=[_detached_record(record, at) for record in sources],
        )
        report = assess_research_fields(
            snapshot,
            checked_at=at,
            max_age=timedelta(hours=job.policy.max_age_hours),
            future_tolerance=timedelta(minutes=job.policy.future_tolerance_minutes),
        )
        if not report.healthy:
            raise ResearchJobError("research_source_stale_or_future")
        payload = snapshot.model_dump(mode="json")
        if len(_bytes(payload)) > MAX_SNAPSHOT_BYTES:
            raise ResearchJobError("snapshot_payload_limit_exceeded")
        job = store.write(
            job.model_copy(
                update={
                    "finalization": {
                        "payload": payload,
                        "digest": snapshot.content_digest(),
                    }
                }
            ),
            expected_generation=job.generation,
        )
        return _validate_finalization(job)


def publish_catalogue_research(
    job_id: str,
    *,
    publisher: ResearchPublisher,
    store: ResearchJobStore,
) -> Any:
    with store.lock(job_id):
        job = store.read(job_id)
        snapshot = _validate_finalization(job)
        if job.publication != "started":
            job = store.write(
                job.model_copy(update={"publication": "started"}),
                expected_generation=job.generation,
            )
        result = publisher.publish(snapshot)
        store.write(
            job.model_copy(update={"publication": "succeeded"}), expected_generation=job.generation
        )
        return result
