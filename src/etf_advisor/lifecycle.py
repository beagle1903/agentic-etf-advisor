"""JSON operational metadata and managed synchronous checkpoint access."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Literal, cast
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from etf_advisor.clock import Clock
from etf_advisor.domain.revision import digest
from etf_advisor.graph.revision import validate_revision_state
from etf_advisor.graph.state import AdvisorState


def review_token(value: str) -> str:
    try:
        parsed = UUID(value.strip())
        if parsed.version != 4:
            raise ValueError
        return str(parsed)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("Review token must be a version-4 UUID.") from None


def utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("Lifecycle clock must return aware UTC.")
    return value


class LifecycleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    thread_id: str
    version: int = Field(ge=1, strict=True)
    retention_days: int = Field(default=30, ge=1, le=365, strict=True)
    last_activity_at: datetime
    expires_at: datetime
    events: list[str]
    integrity: str

    @field_validator("last_activity_at", "expires_at")
    @classmethod
    def aware_utc(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def coherent(self) -> LifecycleRecord:
        if self.expires_at != self.last_activity_at + timedelta(days=self.retention_days):
            raise ValueError("Invalid lifecycle expiry.")
        if self.events != sorted(set(self.events)) or "creation" not in self.events:
            raise ValueError("Invalid lifecycle events.")
        if self.integrity != digest(self.model_dump(mode="json", exclude={"integrity"})):
            raise ValueError("Lifecycle integrity mismatch.")
        return self


def record(values: dict[str, Any]) -> LifecycleRecord:
    # Canonical JSON time serialization is part of the integrity contract.
    provisional = LifecycleRecord.model_construct(**values, integrity="")
    payload = provisional.model_dump(mode="json", exclude={"integrity"})
    return LifecycleRecord.model_validate({**payload, "integrity": digest(payload)})


class ExpiredPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cutoff: datetime
    candidates: dict[str, str]  # Exact token -> lifecycle integrity/version at preview.
    integrity: str

    @model_validator(mode="after")
    def coherent(self) -> ExpiredPreview:
        utc(self.cutoff)
        if self.integrity != digest(self.model_dump(mode="json", exclude={"integrity"})):
            raise ValueError("Invalid prune preview.")
        return self


def semantic_events(values: dict[str, Any], thread_id: str) -> set[str]:
    """Only accepted, sealed semantic transitions renew retention, never input writes."""
    try:
        ledger = validate_revision_state(cast(AdvisorState, values), thread_id)
    except (KeyError, TypeError, ValueError, IndexError):
        return set()
    events = {"decision:" + key for key in ledger.decisions}
    events.update("child:" + r.revision_id for r in ledger.revisions[1:])
    for revision in ledger.revisions:
        for receipt in revision.receipts:
            if receipt.attempt > 1:
                # The accepted request is keyed by the previous attempt, before prepare.
                prior = [r for r in revision.receipts if r.stage == receipt.stage]
                events.add("retry:" + prior[receipt.attempt - 2].operation_id)
        if revision.status in {
            "approved",
            "rejected",
            "invalid_profile",
            "evidence_blocked",
            "screening_blocked",
            "construction_blocked",
            "explanation_blocked",
        }:
            events.add(
                "terminal:" + digest([revision.revision_id, revision.status, revision.operations])
            )
    if values.get("status") == "retry_requested" and values.get("retry_operation_id"):
        events.add("retry:" + values["retry_operation_id"])
    return events


class LifecycleStore:
    """Store contract shared by deterministic memory and local PostgreSQL adapters.

    Adapter operations below run under exclusion. atomic() covers one saver write and
    metadata, or whole-thread deletion, never an entire graph invocation.
    """

    durable: bool
    clock: Clock
    retention_days: int

    def setup(self) -> None:
        raise NotImplementedError

    def open(self) -> Any:
        raise NotImplementedError

    def exclusion(self, thread_id: str) -> Any:
        raise NotImplementedError

    def atomic(self, saver: Any, thread_id: str) -> Any:
        raise NotImplementedError

    def read_metadata(self, saver: Any, thread_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def write_metadata(self, saver: Any, thread_id: str, value: dict[str, Any]) -> None:
        raise NotImplementedError

    def metadata_items(self, saver: Any) -> list[tuple[str, dict[str, Any]]]:
        raise NotImplementedError

    def erase(self, saver: Any, thread_id: str) -> bool:
        raise NotImplementedError

    def exists(self, saver: Any, thread_id: str) -> bool:
        return (
            next(saver.list({"configurable": {"thread_id": thread_id}}, limit=1), None) is not None
        )

    def _read(self, saver: Any, thread_id: str) -> LifecycleRecord:
        value = self.read_metadata(saver, thread_id)
        if value is None:
            raise ValueError("Saved review has no lifecycle metadata; exact deletion is available.")
        try:
            result = LifecycleRecord.model_validate(value)
            if result.thread_id != thread_id:
                raise ValueError
            return result
        except (TypeError, ValueError):
            raise ValueError("Saved lifecycle failed contract validation.") from None

    @contextmanager
    def managed(self, thread_id: str, *, create: bool = False) -> Iterator[ManagedSaver]:
        if self.durable:
            thread_id = review_token(thread_id)
        with self.exclusion(thread_id), self.open() as saver:
            now = utc(self.clock())
            if create:
                if self.read_metadata(saver, thread_id) is not None or self.exists(
                    saver, thread_id
                ):
                    raise ValueError("Saved review already exists.")
                initial = record(
                    {
                        "thread_id": thread_id,
                        "version": 1,
                        "retention_days": self.retention_days,
                        "last_activity_at": now,
                        "expires_at": now + timedelta(days=self.retention_days),
                        "events": ["creation"],
                    }
                )
            else:
                initial = self._read(saver, thread_id)
                if now < initial.last_activity_at:
                    raise ValueError("Lifecycle clock moved backward.")
                if self.durable and initial.expires_at <= now:
                    raise ValueError("Saved review has expired.")
            managed = ManagedSaver(self, saver, thread_id, initial, create)
            try:
                yield managed
            finally:
                managed.active = False

    def inspect(self, thread_id: str) -> dict[str, Any]:
        if self.durable:
            thread_id = review_token(thread_id)
        with self.exclusion(thread_id), self.open() as saver:
            now = utc(self.clock())
            if self.read_metadata(saver, thread_id) is None:
                return {"status": "legacy" if self.exists(saver, thread_id) else "not_found"}
            item = self._read(saver, thread_id)
            if now < item.last_activity_at:
                raise ValueError("Lifecycle clock moved backward.")
            return {
                "status": "expired" if self.durable and item.expires_at <= now else "active",
                "lifecycle": item.model_dump(mode="json"),
            }

    def preview_expired(self) -> ExpiredPreview:
        cutoff = utc(self.clock())
        candidates = {}
        with self.open() as saver:
            for key, raw in self.metadata_items(saver):
                try:
                    item = LifecycleRecord.model_validate(raw)
                    if item.thread_id != key:
                        continue
                    if item.last_activity_at > cutoff:
                        raise RuntimeError("Lifecycle clock moved backward.")
                    if self.durable and item.expires_at <= cutoff:
                        candidates[key] = item.integrity
                except (TypeError, ValueError):
                    continue  # Legacy/malformed records are never automatically deleted.
        values = {"cutoff": cutoff.isoformat().replace("+00:00", "Z"), "candidates": candidates}
        return ExpiredPreview.model_validate({**values, "integrity": digest(values)})

    def prune(self, preview: ExpiredPreview) -> dict[str, str]:
        preview = ExpiredPreview.model_validate(preview.model_dump(mode="json"))
        outcomes = {}
        for key, expected in preview.candidates.items():
            try:
                if self.durable:
                    review_token(key)
                with self.exclusion(key), self.open() as saver, self.atomic(saver, key):
                    if self.read_metadata(saver, key) is None:
                        outcomes[key] = "skipped" if self.exists(saver, key) else "not_found"
                        continue
                    try:
                        current = self._read(saver, key)
                    except ValueError:
                        outcomes[key] = "skipped"
                        continue
                    if current.integrity != expected or current.expires_at > preview.cutoff:
                        outcomes[key] = "skipped"
                    else:
                        outcomes[key] = "deleted" if self.erase(saver, key) else "not_found"
            except Exception:
                outcomes[key] = "failure"
        return outcomes

    def delete(self, token: str, *, confirmed: bool = False) -> str:
        try:
            token = review_token(token)
            if confirmed is not True:
                return "failure"
            with self.exclusion(token), self.open() as saver, self.atomic(saver, token):
                return "deleted" if self.erase(saver, token) else "not_found"
        except Exception:
            return "failure"


class ManagedSaver(BaseCheckpointSaver[str]):
    """Invocation-scoped saver; stale graph/runtime handles cannot write after exit."""

    def __init__(
        self,
        store: LifecycleStore,
        saver: Any,
        thread_id: str,
        initial: LifecycleRecord,
        creating: bool,
    ) -> None:
        super().__init__(serde=saver.serde)
        self.store, self.saver, self.thread_id = store, saver, thread_id
        self.initial, self.creating = initial, creating
        self.active = True
        self.io_lock = RLock()

    def check(self, config: Any) -> None:
        if not self.active or config.get("configurable", {}).get("thread_id") != self.thread_id:
            raise ValueError("Saved review runtime is no longer valid.")

    def get_tuple(self, config: Any) -> Any:
        self.check(config)
        return self.saver.get_tuple(config)

    def list(
        self, config: Any, *, filter: Any = None, before: Any = None, limit: int | None = None
    ) -> Iterator[Any]:
        self.check(config)
        yield from self.saver.list(config, filter=filter, before=before, limit=limit)

    def get_next_version(self, current: Any, channel: Any) -> Any:
        return self.saver.get_next_version(current, channel)

    @contextmanager
    def commit(self, config: Any, values: dict[str, Any]) -> Iterator[None]:
        with self.io_lock:
            self.check(config)
            with self.store.atomic(self.saver, self.thread_id):
                previous = (
                    self.initial if self.creating else self.store._read(self.saver, self.thread_id)
                )
                events = set(previous.events) | semantic_events(values, self.thread_id)
                now = previous.last_activity_at
                if events != set(previous.events):
                    now = utc(self.store.clock())
                    if now < previous.last_activity_at:
                        raise ValueError("Lifecycle clock moved backward.")
                updated = record(
                    {
                        "thread_id": self.thread_id,
                        "version": previous.version if self.creating else previous.version + 1,
                        "retention_days": previous.retention_days,
                        "last_activity_at": now,
                        "expires_at": now + timedelta(days=previous.retention_days),
                        "events": sorted(events),
                    }
                )
                yield
                self.store.write_metadata(
                    self.saver, self.thread_id, updated.model_dump(mode="json")
                )
            self.creating = False

    def put(self, config: Any, checkpoint: Any, metadata: Any, new_versions: Any) -> Any:
        with self.commit(config, checkpoint["channel_values"]):
            result = self.saver.put(config, checkpoint, metadata, new_versions)
        return result

    def put_writes(
        self, config: Any, writes: Sequence[tuple[str, Any]], task_id: str, task_path: str = ""
    ) -> None:
        # Pending writes do not publish a coherent graph checkpoint or renew activity.
        with self.commit(config, {}):
            self.saver.put_writes(config, writes, task_id, task_path)
