"""Deterministic store contracts: no database, market, or provider connections."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from threading import Event
from typing import Any

import pytest
from langgraph.types import Command
from test_revision import FEEDBACK, Adapters
from test_workflow import valid_profile

from etf_advisor.audit import reconstruct_audit
from etf_advisor.checkpoint import MemoryCheckpointStore
from etf_advisor.config import Settings
from etf_advisor.dashboard import DashboardOptions, start_dashboard_run
from etf_advisor.domain.revision import digest
from etf_advisor.graph.revision import _sealed_values
from etf_advisor.graph.workflow import build_graph
from etf_advisor.lifecycle import LifecycleRecord, semantic_events

TOKEN = "10000000-0000-4000-8000-000000000001"
OTHER = "10000000-0000-4000-8000-000000000002"
NOW = datetime(2026, 9, 7, tzinfo=UTC)


class Time:
    def __init__(self) -> None:
        self.now = NOW
        self.calls = 0

    def __call__(self) -> datetime:
        self.calls += 1
        return self.now


class Store(MemoryCheckpointStore):
    durable = True


def invoke(
    store: MemoryCheckpointStore,
    value: Any,
    *,
    create: bool = False,
    token: str = TOKEN,
    adapters: Any = None,
) -> dict[str, Any]:
    with store.managed(token, create=create) as saver:
        graph = build_graph(checkpointer=saver, clock=store.clock, candidate_retriever=adapters)
        return dict(graph.invoke(value, {"configurable": {"thread_id": token}}))


def start(store: MemoryCheckpointStore, token: str = TOKEN, adapters: Any = None) -> dict[str, Any]:
    return invoke(store, {"profile": valid_profile()}, create=True, token=token, adapters=adapters)


def decision(state: dict[str, Any], time: Time, *, edit: bool = False) -> Command[Any]:
    return Command(
        resume={
            "decision_id": "decision-" + str(len(state["revision_ledger"]["revisions"])),
            "revision_id": state["revision_ledger"]["revisions"][-1]["revision_id"],
            "action": "edit" if edit else "approve",
            "disposition": "revise" if edit else None,
            "note": "Change profile" if edit else "",
            "feedback": [FEEDBACK[0]] if edit else [],
            "submitted_at": time.now.isoformat(),
        }
    )


def metadata(store: Store, token: str = TOKEN) -> LifecycleRecord:
    return LifecycleRecord.model_validate(store._metadata[token])


def test_exact_expiry_read_restore_and_preview_never_renew() -> None:
    time = Time()
    store = Store(clock=time)
    start(store)
    original = metadata(store)
    assert original.expires_at == NOW + timedelta(days=30)
    time.now = original.expires_at - timedelta(microseconds=1)
    with store.managed(TOKEN) as saver:
        assert (
            build_graph(checkpointer=saver).get_state({"configurable": {"thread_id": TOKEN}}).values
        )
    assert store.inspect(TOKEN)["status"] == "active"
    assert store.preview_expired().candidates == {}
    assert metadata(store) == original
    time.now += timedelta(microseconds=1)
    assert store.inspect(TOKEN)["status"] == "expired"
    assert store.preview_expired().candidates == {TOKEN: original.integrity}
    with pytest.raises(ValueError, match="expired"):
        invoke(store, None)
    assert metadata(store) == original


@pytest.mark.parametrize("days", [1, 30, 365])
def test_effective_retention_is_persisted(days: int) -> None:
    store = Store(clock=Time(), retention_days=days)
    start(store)
    store.retention_days = 8
    assert metadata(store).retention_days == days
    assert metadata(store).expires_at == NOW + timedelta(days=days)


@pytest.mark.parametrize("days", [0, 366, 1.5, True, "30"])
def test_invalid_retention(days: Any) -> None:
    with pytest.raises(ValueError, match="integer"):
        Store(retention_days=days)


@pytest.mark.parametrize("days", [0, 366, 1.5, True])
def test_local_retention_setting_enforces_integer_bounds(days: Any) -> None:
    with pytest.raises(ValueError):
        Settings(checkpoint_retention_days=days)


@pytest.mark.parametrize(
    "bad_time", [NOW.replace(tzinfo=None), NOW.astimezone(timezone(timedelta(hours=3)))]
)
def test_clock_requires_aware_utc(bad_time: datetime) -> None:
    with pytest.raises(ValueError, match="UTC"):
        start(Store(clock=lambda: bad_time))


def test_backward_clock_rejected_without_writes() -> None:
    time = Time()
    store = Store(clock=time)
    start(store)
    before = metadata(store)
    time.now -= timedelta(microseconds=1)
    with pytest.raises(ValueError, match="backward"):
        invoke(store, None)
    assert metadata(store) == before


def test_child_decision_terminal_renew_once_and_deduplicate() -> None:
    time = Time()
    store = Store(clock=time)
    parent = start(store)
    time.now += timedelta(days=2)
    child = invoke(store, decision(parent, time, edit=True))
    renewed = metadata(store)
    assert renewed.last_activity_at == time.now
    assert len(renewed.events) == 3  # creation, accepted decision, child
    history = reconstruct_audit(child, TOKEN)
    assert json.loads(json.dumps(history)) == history
    first, second = history["revisions"]
    assert second["triggering_decision_id"] == first["decision"]["decision_id"]
    assert "decision" not in second
    assert set(second["artifacts"]) == {"draft_policy"}
    time.now += timedelta(days=2)
    completed = invoke(store, decision(child, time))
    terminal = metadata(store)
    assert completed["status"] == "approved"
    assert terminal.last_activity_at == time.now
    time.now += timedelta(days=2)
    invoke(store, None)  # completed invocation is a read/replay, not a new event
    assert metadata(store).last_activity_at == terminal.last_activity_at
    assert metadata(store).events == terminal.events
    assert semantic_events(completed, TOKEN) <= set(terminal.events)


def test_retry_renewal_and_started_receipt_committed_before_adapter() -> None:
    time = Time()
    store = Store(clock=time)

    class Failing(Adapters):
        def retrieve(self, profile: Any, *, limit: int = 5) -> Any:
            persisted = store._saver.get_tuple({"configurable": {"thread_id": TOKEN}})
            assert (
                persisted.checkpoint["channel_values"]["revision_ledger"]["revisions"][-1][
                    "receipts"
                ][-1]["status"]
                == "started"
            )
            return super().retrieve(profile, limit=limit)

    adapters = Failing()
    adapters.fail_retrieval = True
    failed = start(store, adapters=adapters)
    revision = failed["revision_ledger"]["revisions"][-1]
    operation = revision["receipts"][-1]["operation_id"]
    time.now += timedelta(days=2)
    invoke(
        store,
        {
            "retry_request": {
                "action": "retry",
                "revision_id": revision["revision_id"],
                "operation_id": operation,
            }
        },
        adapters=adapters,
    )
    assert adapters.retrieval_calls == 2
    assert metadata(store).last_activity_at == time.now
    assert "retry:" + operation in metadata(store).events


def test_invalid_decision_does_not_renew() -> None:
    time = Time()
    store = Store(clock=time)
    start(store)
    time.now += timedelta(days=1)
    invoke(store, Command(resume={"action": "approve"}))
    assert metadata(store).last_activity_at == NOW


def test_successful_receipt_reuse_does_not_renew_or_call_adapter() -> None:
    time = Time()
    store = Store(clock=time)
    adapters = Adapters()
    start(store, adapters=adapters)
    before = metadata(store)
    time.now += timedelta(days=2)
    config = {"configurable": {"thread_id": TOKEN}}
    with store.managed(TOKEN) as saver:
        restored = build_graph(
            checkpointer=saver,
            clock=time,
            candidate_retriever=adapters,
        )
        restored.update_state(config, {}, as_node="prepare_retrieve_candidate_evidence")
        result = restored.invoke(None, config)
    assert result["status"] == "awaiting_human_review"
    assert adapters.retrieval_calls == 1
    assert metadata(store).last_activity_at == before.last_activity_at
    assert metadata(store).events == before.events


def test_preview_exact_set_changed_candidate_skipped_new_expiry_waits() -> None:
    time = Time()
    store = Store(clock=time)
    start(store)
    time.now += timedelta(days=1)
    start(store, OTHER)
    time.now = NOW + timedelta(days=30)
    preview = store.preview_expired()
    assert set(preview.candidates) == {TOKEN}
    # Simulate an operator/store change after preview; prune must compare version/integrity.
    from etf_advisor.lifecycle import record

    values = metadata(store).model_dump(mode="python", exclude={"integrity"})
    values["version"] += 1
    store._metadata[TOKEN] = record(values).model_dump(mode="json")
    time.now += timedelta(days=2)
    assert store.prune(preview) == {TOKEN: "skipped"}
    assert set(store.preview_expired().candidates) == {TOKEN, OTHER}
    assert store.prune(store.preview_expired()) == {TOKEN: "deleted", OTHER: "deleted"}


def test_whole_thread_deletion_all_namespaces_and_confirmation() -> None:
    store = Store(clock=Time())
    start(store)
    start(store, OTHER)
    store._saver.storage[TOKEN]["child-ns"] = deepcopy(store._saver.storage[TOKEN][""])
    store._saver.blobs[(TOKEN, "child-ns", "extra", "1")] = ("bytes", b"fixture")
    store._saver.writes[(TOKEN, "child-ns", "checkpoint")] = {}
    assert store.delete(TOKEN) == "failure"
    assert store.delete("not-a-token", confirmed=True) == "failure"
    assert store.delete(TOKEN, confirmed=True) == "deleted"
    assert TOKEN not in store._metadata and TOKEN not in store._saver.storage
    assert not any(k[0] == TOKEN for k in (*store._saver.blobs, *store._saver.writes))
    assert store.inspect(OTHER)["status"] == "active"
    assert store.delete(TOKEN, confirmed=True) == "not_found"


def test_atomic_deletion_failure_restores_every_record(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store(clock=Time())
    start(store)
    before = deepcopy(
        (store._saver.storage, store._saver.blobs, store._saver.writes, store._metadata)
    )
    erase = store.erase

    def fail(saver: Any, key: str) -> bool:
        erase(saver, key)
        raise RuntimeError("private failure must not escape")

    monkeypatch.setattr(store, "erase", fail)
    assert store.delete(TOKEN, confirmed=True) == "failure"
    assert (
        store._saver.storage,
        store._saver.blobs,
        store._saver.writes,
        store._metadata,
    ) == before


def test_atomic_checkpoint_metadata_failure_prevents_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(clock=Time())
    adapters = Adapters()
    write = store.write_metadata

    def fail(saver: Any, key: str, value: dict[str, Any]) -> None:
        latest = saver.get_tuple({"configurable": {"thread_id": key}})
        if latest and latest.checkpoint["channel_values"].get("status") == "operation_prepared":
            raise RuntimeError("injected checkpoint failure")
        write(saver, key, value)

    monkeypatch.setattr(store, "write_metadata", fail)
    with pytest.raises(RuntimeError):
        start(store, adapters=adapters)
    assert adapters.retrieval_calls == 0
    latest = store._saver.get_tuple({"configurable": {"thread_id": TOKEN}})
    assert latest.checkpoint["channel_values"]["status"] != "operation_prepared"


def test_deletion_waits_for_invocation_and_stale_handle_cannot_recreate() -> None:
    store = Store(clock=Time())
    start(store)
    attempting = Event()

    def delete() -> str:
        attempting.set()
        return store.delete(TOKEN, confirmed=True)

    with ThreadPoolExecutor() as executor:
        with store.managed(TOKEN) as saver:
            graph = build_graph(checkpointer=saver)
            future = executor.submit(delete)
            assert attempting.wait(5)
            assert not future.done()
            assert graph.get_state({"configurable": {"thread_id": TOKEN}}).values
        assert future.result(timeout=5) == "deleted"
    with pytest.raises(ValueError, match="no longer valid"):
        graph.invoke(None, {"configurable": {"thread_id": TOKEN}})
    with pytest.raises(ValueError, match="no lifecycle"):
        invoke(store, None)
    assert store.inspect(TOKEN) == {"status": "not_found"}


@pytest.mark.parametrize("damage", ["legacy", "digest", "cross-thread", "version"])
def test_malformed_lifecycle_fails_closed_but_exact_deletion_works(damage: str) -> None:
    time = Time()
    store = Store(clock=time)
    start(store)
    if damage == "legacy":
        store._metadata.pop(TOKEN)
    elif damage == "digest":
        store._metadata[TOKEN]["integrity"] = "broken"
    elif damage == "cross-thread":
        store._metadata[TOKEN]["thread_id"] = OTHER
    else:
        store._metadata[TOKEN]["schema_version"] = 2
    with pytest.raises(ValueError):
        invoke(store, None)
    time.now += timedelta(days=31)
    assert store.preview_expired().candidates == {}
    assert store.delete(TOKEN, confirmed=True) == "deleted"


def test_memory_discard_invalidates_run_and_cached_runtime() -> None:
    run = start_dashboard_run(valid_profile(), DashboardOptions())
    store = run.checkpoint_store
    token = run.thread_id
    assert run.lifecycle()["status"] == "active"
    assert run.audit()["thread_id"] == token
    run.discard()
    assert run.graph is None and run.state == {}
    with pytest.raises(ValueError):
        run.resume("approve")
    assert store.inspect(token)["status"] == "not_found"


def test_full_audit_preserves_snapshot_receipts_and_detects_tampering() -> None:
    store = Store(clock=Time())
    state = start(store, adapters=Adapters())
    audit = reconstruct_audit(state, TOKEN)
    assert json.loads(json.dumps(audit)) == audit
    revision = audit["revisions"][0]
    assert revision["snapshot"]["version"] == "local-synthetic-v1"
    assert revision["receipts"][0]["status"] == "succeeded"
    audit["revisions"][0]["profile_version"]["value"].clear()
    assert reconstruct_audit(state, TOKEN)["revisions"][0]["profile_version"]["value"]
    tampered = deepcopy(state)
    tampered["revision_ledger"]["revisions"][0]["profile_digest"] = "0" * 64
    with pytest.raises(ValueError, match="audit"):
        reconstruct_audit(tampered, TOKEN)
    # Even a resealed artifact cannot mislabel its source snapshot.
    artifact_id = state["revision_ledger"]["revisions"][0]["artifacts"]["candidate_evidence"]
    tampered = deepcopy(state)
    artifact = tampered["revision_ledger"]["artifacts"][artifact_id]
    artifact["value"]["snapshot_digest"] = "0" * 64
    artifact["digest"] = digest(artifact["value"])
    tampered["candidate_evidence"] = deepcopy(artifact["value"])
    tampered["revision_ledger"]["revisions"][0]["receipts"][0]["output_digest"] = artifact["digest"]
    tampered["revision_digest"] = digest(_sealed_values(tampered))
    with pytest.raises(ValueError, match="audit"):
        reconstruct_audit(tampered, TOKEN)
