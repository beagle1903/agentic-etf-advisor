"""Missing frozen Issue105 crash, bounds, and identity scenarios."""

import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_issue105_app import _Documents, _Graph
from test_issue105_catalogue import CREATED, _Collector, _isin, catalogue
from test_us_eu_contract import _record

from etf_advisor.catalogue.research_job import (
    CachedResearchRecord,
    ResearchJobError,
    ResearchJobPolicy,
    ResearchJobStore,
    _digest,
    advance_catalogue_research,
    begin_catalogue_research,
    finalize_catalogue_research,
    publish_catalogue_research,
    retry_catalogue_research,
)
from etf_advisor.catalogue.research_scope import plan_catalogue_scope
from etf_advisor.data.quality import MarketDataQualityError
from etf_advisor.data.reference_facts import (
    LocalReferenceFacts,
    ReferenceFactsFile,
    ReferenceFactsRecord,
)
from etf_advisor.data.yahoo_budget import YahooBudgetError, YahooRequestBudget
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity, publish_research_snapshot


def _job(tmp_path: Path, count: int = 2, policy: ResearchJobPolicy | None = None):
    scope = plan_catalogue_scope(
        catalogue(), {"listing_ids": [row["listing_id"] for row in catalogue()["direct"][:count]]}
    )
    store = ResearchJobStore(tmp_path)
    job = begin_catalogue_research(
        scope, [], policy or ResearchJobPolicy(batch_size=count), clock=lambda: CREATED, store=store
    )
    return scope, store, job


def test_started_attempt_crash_requires_exact_retry(tmp_path: Path, monkeypatch) -> None:
    scope, store, job = _job(tmp_path, 1)
    collector = _Collector(CREATED - timedelta(minutes=1))
    original = store.write

    def crash_result(candidate, *, expected_generation):
        if candidate.cached:
            raise OSError("result commit interrupted")
        return original(candidate, expected_generation=expected_generation)

    monkeypatch.setattr(store, "write", crash_result)
    with pytest.raises(OSError, match="result commit"):
        advance_catalogue_research(
            job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
        )
    saved = store.read(job.job_id)
    attempts = saved.attempts[scope.members[0].listing_id]
    assert attempts[-1].status == "started"
    assert saved.cached == {}
    assert (
        advance_catalogue_research(
            saved.job_id, saved.generation, collector=collector, store=store, clock=lambda: CREATED
        )
        == saved
    )
    monkeypatch.setattr(store, "write", original)
    recovered = retry_catalogue_research(
        saved.job_id,
        scope.members[0].listing_id,
        attempts[-1].attempt_id,
        saved.generation,
        collector=collector,
        store=store,
        clock=lambda: CREATED,
    )
    assert len(recovered.cached) == 1
    assert len(collector.calls) == 2
    assert recovered.attempts[scope.members[0].listing_id][-1].status == "succeeded"


def test_swallowed_transport_breach_cannot_be_cached(tmp_path: Path) -> None:
    scope, store, job = _job(tmp_path, 1)

    class SwallowsBudgetError:
        def collect(self, listing, snapshot_version, references, budget, *, clock):
            budget.breached = True
            return _Collector(CREATED - timedelta(minutes=1)).collect(
                listing, snapshot_version, references, budget, clock=clock
            )

    result = advance_catalogue_research(
        job.job_id,
        job.generation,
        collector=SwallowsBudgetError(),
        store=store,
        clock=lambda: CREATED,
    )
    assert result.cached == {}
    assert result.attempts[scope.members[0].listing_id][-1].code == "transport_bound_exceeded"


@pytest.mark.parametrize(("deadline", "max_requests"), [(89, 12), (300, 1)])
def test_bnd_issuer_fallback_reserves_time_and_requests_before_invocation(
    monkeypatch, deadline: int, max_requests: int
) -> None:
    import etf_advisor.data.yahoo_research as yahoo_research

    monkeypatch.setattr(yahoo_research, "bounded_yahoo_session", lambda budget: object())
    monkeypatch.setattr(
        yahoo_research.YahooResearchAdapter,
        "_fetch_one",
        lambda self, symbol: SimpleNamespace(info={"exchange": "PCX"}, top_holdings=None),
    )
    collector = yahoo_research.YahooCatalogueResearchCollector(issuer_client=object())
    budget = YahooRequestBudget(deadline=deadline, max_requests=max_requests, monotonic=lambda: 0.0)
    with pytest.raises(YahooBudgetError, match="bnd_issuer_reservation_unavailable"):
        collector.collect(
            SimpleNamespace(symbol="BND", exchange="PCX"),
            "version",
            LocalReferenceFacts({}),
            budget,
            clock=lambda: CREATED,
        )


def test_result_ack_loss_preserves_success_without_recollection(
    tmp_path: Path, monkeypatch
) -> None:
    scope, store, job = _job(tmp_path, 1)
    collector = _Collector(CREATED - timedelta(minutes=1))
    original = store.write

    def lose_ack(candidate, *, expected_generation):
        saved = original(candidate, expected_generation=expected_generation)
        if candidate.cached:
            raise OSError("result acknowledgement lost")
        return saved

    monkeypatch.setattr(store, "write", lose_ack)
    with pytest.raises(OSError, match="acknowledgement lost"):
        advance_catalogue_research(
            job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
        )
    saved = store.read(job.job_id)
    assert len(saved.cached) == 1
    assert saved.attempts[scope.members[0].listing_id][-1].status == "succeeded"
    monkeypatch.setattr(store, "write", original)
    with pytest.raises(ResearchJobError, match="retry_not_current_member"):
        retry_catalogue_research(
            saved.job_id,
            scope.members[0].listing_id,
            saved.attempts[scope.members[0].listing_id][-1].attempt_id,
            saved.generation,
            collector=collector,
            store=store,
            clock=lambda: CREATED,
        )
    assert len(collector.calls) == 1


def test_foreign_cached_member_rejects_before_canonical_commit(tmp_path: Path) -> None:
    scope, store, job = _job(tmp_path, 2)
    collector = _Collector(CREATED - timedelta(minutes=1))
    done = advance_catalogue_research(
        job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
    )
    first, second = (member.listing_id for member in scope.members)
    foreign = done.cached[second]
    substituted = CachedResearchRecord(
        listing_id=first, record=foreign.record, digest=foreign.digest
    )
    contaminated = store.write(
        done.model_copy(update={"cached": {**done.cached, first: substituted}}),
        expected_generation=done.generation,
    )
    with pytest.raises(ResearchJobError, match="collected_identity_mismatch"):
        finalize_catalogue_research(
            contaminated.job_id, store=store, clock=lambda: CREATED + timedelta(minutes=1)
        )
    assert store.read(done.job_id).finalization is None
    assert len(collector.calls) == 2


@pytest.mark.parametrize("ingested_at", ["2026-10-22T08:00:00Z", "2026-10-23T08:01:00Z"])
def test_invalid_cache_coordinates_reject_before_replacement(
    tmp_path: Path, ingested_at: str
) -> None:
    scope, store, job = _job(tmp_path, 1)
    done = advance_catalogue_research(
        job.job_id,
        job.generation,
        collector=_Collector(CREATED - timedelta(minutes=1)),
        store=store,
        clock=lambda: CREATED,
    )
    listing_id = scope.members[0].listing_id
    record = json.loads(json.dumps(done.cached[listing_id].record))
    record["name"]["ingested_at"] = ingested_at
    tampered = CachedResearchRecord(listing_id=listing_id, record=record, digest=_digest(record))
    changed = store.write(
        done.model_copy(update={"cached": {listing_id: tampered}}),
        expected_generation=done.generation,
    )
    with pytest.raises(ResearchJobError, match="collected_coordinate_mismatch"):
        finalize_catalogue_research(
            changed.job_id, store=store, clock=lambda: CREATED + timedelta(minutes=2)
        )
    assert store.read(done.job_id).finalization is None


def test_exhaustion_and_stale_complete_cache_never_publish(tmp_path: Path) -> None:
    scope, store, job = _job(tmp_path, 1, ResearchJobPolicy(attempts_per_listing=2))
    collector = _Collector(CREATED - timedelta(minutes=1))
    collector.fail_symbol = scope.members[0].symbol
    failed = advance_catalogue_research(
        job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
    )
    failed = retry_catalogue_research(
        job.job_id,
        scope.members[0].listing_id,
        failed.attempts[scope.members[0].listing_id][-1].attempt_id,
        failed.generation,
        collector=collector,
        store=store,
        clock=lambda: CREATED,
    )
    assert len(failed.attempts[scope.members[0].listing_id]) == 2
    with pytest.raises(ResearchJobError, match="retry_not_authorized"):
        retry_catalogue_research(
            job.job_id,
            scope.members[0].listing_id,
            failed.attempts[scope.members[0].listing_id][-1].attempt_id,
            failed.generation,
            collector=collector,
            store=store,
            clock=lambda: CREATED,
        )
    assert len(collector.calls) == 2
    fresh_scope, fresh_store, fresh_job = _job(tmp_path / "fresh", 1)
    fresh = _Collector(CREATED - timedelta(minutes=1))
    done = advance_catalogue_research(
        fresh_job.job_id,
        fresh_job.generation,
        collector=fresh,
        store=fresh_store,
        clock=lambda: CREATED,
    )
    with pytest.raises(ResearchJobError, match="research_source_stale_or_future"):
        finalize_catalogue_research(
            done.job_id, store=fresh_store, clock=lambda: CREATED + timedelta(days=9)
        )
    assert fresh_store.read(done.job_id).finalization is None
    assert len(fresh_scope.members) == 1


def test_record_and_canonical_payload_limits_reject_before_publication(
    tmp_path: Path, monkeypatch
) -> None:
    import etf_advisor.catalogue.research_job as jobs

    scope, store, job = _job(tmp_path, 1)
    collector = _Collector(CREATED - timedelta(minutes=1))
    monkeypatch.setattr(jobs, "MAX_RECORD_BYTES", 100)
    failed = advance_catalogue_research(
        job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
    )
    assert failed.attempts[scope.members[0].listing_id][-1].code == "cached_record_limit_exceeded"
    assert not failed.cached
    monkeypatch.setattr(jobs, "MAX_RECORD_BYTES", 256 * 1024)
    done = retry_catalogue_research(
        failed.job_id,
        scope.members[0].listing_id,
        failed.attempts[scope.members[0].listing_id][-1].attempt_id,
        failed.generation,
        collector=collector,
        store=store,
        clock=lambda: CREATED,
    )
    monkeypatch.setattr(jobs, "MAX_SNAPSHOT_BYTES", 100)
    with pytest.raises(ResearchJobError, match="snapshot_payload_limit_exceeded"):
        finalize_catalogue_research(done.job_id, store=store, clock=lambda: CREATED)
    assert store.read(done.job_id).finalization is None


def _reference(symbol: str, exchange: str, index: int) -> ReferenceFactsRecord:
    record = _record(symbol, exchange, "USD", "Large Blend", _isin(index))
    return ReferenceFactsRecord(
        symbol=symbol,
        exchange=exchange,
        **{
            name: getattr(record, name)
            for name in (
                "share_class_id",
                "economic_group_id",
                "domicile",
                "fund_base_currency",
                "share_class_currency",
            )
        },
    )


def test_reference_file_count_duplicate_foreign_and_pinned_resume(tmp_path: Path) -> None:
    scope = plan_catalogue_scope(
        catalogue(), {"listing_ids": [row["listing_id"] for row in catalogue()["direct"][:2]]}
    )
    store = ResearchJobStore(tmp_path / "jobs")
    calls: list[str] = []

    class Spy:
        def collect(self, listing, snapshot_version, references, budget, *, clock):
            calls.append(listing.symbol)
            record = references.lookup(listing.symbol, listing.exchange)
            assert record is not None
            from etf_advisor.data.reference_facts import LocalReferenceFacts

            return _Collector(CREATED - timedelta(minutes=1)).collect(
                listing,
                snapshot_version,
                LocalReferenceFacts({(listing.symbol, listing.exchange): record}),
                budget,
                clock=clock,
            )

    one = _reference(scope.members[0].symbol, scope.members[0].exchange, 0)
    two = _reference(scope.members[1].symbol, scope.members[1].exchange, 1)
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    first.write_text(ReferenceFactsFile(schema_version=1, records=[one]).model_dump_json())
    second.write_text(ReferenceFactsFile(schema_version=1, records=[two]).model_dump_json())
    with pytest.raises(ResearchJobError, match="reference_file_limit_exceeded"):
        begin_catalogue_research(
            scope, [first] * 11, ResearchJobPolicy(), clock=lambda: CREATED, store=store
        )
    with pytest.raises(ResearchJobError, match="reference_identity_conflict"):
        begin_catalogue_research(
            scope, [first, first], ResearchJobPolicy(), clock=lambda: CREATED, store=store
        )
    foreign = tmp_path / "foreign.json"
    foreign.write_text(
        ReferenceFactsFile(
            schema_version=1, records=[_reference("SPY", "NYQ", 2)]
        ).model_dump_json()
    )
    with pytest.raises(ValueError):
        begin_catalogue_research(
            scope, [foreign], ResearchJobPolicy(), clock=lambda: CREATED, store=store
        )
    assert calls == []
    job = begin_catalogue_research(
        scope, [first, second], ResearchJobPolicy(batch_size=2), clock=lambda: CREATED, store=store
    )
    pinned = json.dumps(job.references, sort_keys=True)
    first.write_text("edited after start", encoding="utf-8")
    completed = advance_catalogue_research(
        job.job_id, job.generation, collector=Spy(), store=store, clock=lambda: CREATED
    )
    assert len(completed.cached) == 2, completed.attempts
    assert json.dumps(store.read(job.job_id).references, sort_keys=True) == pinned
    assert calls == [member.symbol for member in scope.members]


def test_ten_distinct_reference_files_aggregate_for_ten_members(tmp_path: Path) -> None:
    rows = catalogue()["direct"][:10]
    scope = plan_catalogue_scope(catalogue(), {"listing_ids": [row["listing_id"] for row in rows]})
    files = []
    for index, member in enumerate(scope.members):
        path = tmp_path / f"reference-{index}.json"
        path.write_text(
            ReferenceFactsFile(
                schema_version=1,
                records=[_reference(member.symbol, member.exchange, index)],
            ).model_dump_json(),
            encoding="utf-8",
        )
        files.append(path)
    job = begin_catalogue_research(
        scope, files, ResearchJobPolicy(), clock=lambda: CREATED, store=ResearchJobStore(tmp_path)
    )
    assert len(job.references) == 10
    assert {entry["symbol"] for entry in job.references} == {
        member.symbol for member in scope.members
    }


@pytest.mark.parametrize("failure", ["stage", "activate", "ack"])
def test_request_publication_failure_and_exact_recovery(tmp_path: Path, failure: str) -> None:
    _, store, job = _job(tmp_path, 2)
    collector = _Collector(CREATED - timedelta(minutes=1))
    done = advance_catalogue_research(
        job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
    )
    snapshot = finalize_catalogue_research(done.job_id, store=store, clock=lambda: CREATED)
    documents, graph = _Documents(), _Graph()
    prior = ActiveSnapshotIdentity("prior", "0" * 64)
    graph.active = prior
    stage_calls = [0]
    original_stage = documents.stage_snapshot
    original_activate = graph.publish_snapshot

    def stage(rows):
        stage_calls[0] += 1
        if failure == "stage" and stage_calls[0] == 1:
            documents.rows = {rows[0].document_id: rows[0]}
            raise OSError("stage interrupted")
        return original_stage(rows)

    def activate(*args, **kwargs):
        if failure == "activate" and stage_calls[0] == 1:
            raise OSError("activation interrupted")
        result = original_activate(*args, **kwargs)
        if failure == "ack" and stage_calls[0] == 1:
            raise OSError("activation acknowledgement lost")
        return result

    documents.stage_snapshot = stage
    graph.publish_snapshot = activate

    class Publisher:
        def publish(self, payload):
            return publish_research_snapshot(payload, documents, graph, clock=lambda: CREATED)

    with pytest.raises(OSError):
        publish_catalogue_research(done.job_id, publisher=Publisher(), store=store)
    saved = store.read(done.job_id)
    assert saved.publication == "started"
    assert saved.finalization["digest"] == snapshot.content_digest()
    assert graph.active == (
        prior
        if failure in {"stage", "activate"}
        else ActiveSnapshotIdentity(snapshot.snapshot_version, snapshot.content_digest())
    )
    result = publish_catalogue_research(done.job_id, publisher=Publisher(), store=store)
    assert result.snapshot_digest == snapshot.content_digest()
    assert graph.active == ActiveSnapshotIdentity(
        snapshot.snapshot_version, snapshot.content_digest()
    )
    assert store.read(done.job_id).publication == "succeeded"
    assert stage_calls[0] == (1 if failure == "ack" else 2)
    assert len(collector.calls) == 2
    again = publish_catalogue_research(done.job_id, publisher=Publisher(), store=store)
    assert again.already_active is True
    assert stage_calls[0] == (1 if failure == "ack" else 2)


def test_stale_new_publication_rejects_before_staging(tmp_path: Path) -> None:
    scope, store, job = _job(tmp_path, 1)
    collector = _Collector(CREATED - timedelta(minutes=1))
    done = advance_catalogue_research(
        job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
    )
    finalize_catalogue_research(done.job_id, store=store, clock=lambda: CREATED)
    documents, graph = _Documents(), _Graph()
    graph.active = ActiveSnapshotIdentity("prior", "0" * 64)

    class Publisher:
        def publish(self, payload):
            return publish_research_snapshot(
                payload, documents, graph, clock=lambda: CREATED + timedelta(days=9)
            )

    with pytest.raises(MarketDataQualityError):
        publish_catalogue_research(done.job_id, publisher=Publisher(), store=store)
    assert graph.active == ActiveSnapshotIdentity("prior", "0" * 64)
    assert documents.rows == {}
    assert store.read(done.job_id).publication == "started"
    assert len(scope.members) == 1
