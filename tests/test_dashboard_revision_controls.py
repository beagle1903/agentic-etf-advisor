"""Focused Issue #42 dashboard revision, retry, audit, and lifecycle regressions."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from test_checkpoint_lifecycle import Store as DurableStore
from test_revision import Adapters, valid_profile

import etf_advisor.dashboard_app as dashboard_app
from etf_advisor.checkpoint import MemoryCheckpointStore
from etf_advisor.dashboard import (
    DashboardRun,
    dashboard_audit,
    delete_saved_review,
    inspect_saved_review_lifecycle,
)
from etf_advisor.dashboard_app import (
    _SELECTED_REVIEW_KEY,
    _build_feedback_items,
    _restore_saved_run,
    _retry_target,
)
from etf_advisor.graph.revision import validate_revision_state
from etf_advisor.graph.workflow import build_graph

TOKEN = "a5556b2c-7fb1-4da7-8563-ec419b41d101"
OTHER = "61609d86-3541-4c4f-878d-4a38912f248c"


class Time:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 10, 8, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class ExitFailingStore(MemoryCheckpointStore):
    """Raise once after a managed invocation has already committed its writes."""

    def __init__(self) -> None:
        super().__init__(clock=Time())
        self.fail_next_exit = False

    @contextmanager
    def managed(self, thread_id: str, *, create: bool = False) -> Iterator[Any]:
        with super().managed(thread_id, create=create) as saver:
            yield saver
        if self.fail_next_exit:
            self.fail_next_exit = False
            raise RuntimeError("managed exit failed after committed mutation")


def _run(
    *,
    token: str = TOKEN,
    adapters: Adapters | None = None,
    durable: bool = False,
    clock: Any | None = None,
    checkpoint_store: MemoryCheckpointStore | None = None,
) -> DashboardRun:
    store = checkpoint_store or (
        DurableStore(clock=clock or Time())
        if durable
        else MemoryCheckpointStore(clock=clock or Time())
    )
    with store.managed(token, create=True) as saver:
        graph = build_graph(
            checkpointer=saver,
            candidate_retriever=adapters,
            explanation_generator=adapters,
        )
        state = dict(
            graph.invoke({"profile": valid_profile()}, {"configurable": {"thread_id": token}})
        )
    return DashboardRun(
        graph=None,
        config={"configurable": {"thread_id": token}},
        state=state,
        checkpoint_store=store,
        candidate_retriever=None if store.durable else adapters,
        explanation_generator=None if store.durable else adapters,
    )


def _revision_id(run: DashboardRun) -> str:
    return validate_revision_state(run.state, run.thread_id).revisions[-1].revision_id


def test_feedback_builder_emits_all_five_exact_typed_payloads() -> None:
    selected = [
        "profile",
        "evidence",
        "screening_policy",
        "construction_policy",
        "explanation",
    ]
    values = {
        "profile": {"horizon_years": 18},
        "evidence": {"candidate_limit": 6},
        "screening_policy": {"max_expense_ratio_pct": 0.75},
        "construction_policy": {"max_positions": 4},
        "explanation": {"instruction": "Use shorter sentences."},
    }
    assert _build_feedback_items(selected, values) == [
        {"kind": "profile", "patch": {"horizon_years": 18}},
        {"kind": "evidence", "refresh": True, "candidate_limit": 6},
        {"kind": "screening_policy", "patch": {"max_expense_ratio_pct": 0.75}},
        {"kind": "construction_policy", "patch": {"max_positions": 4}},
        {"kind": "explanation", "instruction": "Use shorter sentences."},
    ]


@pytest.mark.parametrize(
    ("feedback", "restart", "calls"),
    [
        ({"kind": "profile", "patch": {"horizon_years": 18}}, "validate_profile", (2, 2)),
        (
            {"kind": "evidence", "refresh": True, "candidate_limit": 4},
            "retrieve_candidate_evidence",
            (2, 1),
        ),
        (
            {"kind": "screening_policy", "patch": {"max_expense_ratio_pct": 2.0}},
            "screen_candidates",
            (1, 2),
        ),
        (
            {"kind": "construction_policy", "patch": {"max_category_weight_bps": 9000}},
            "construct_portfolio",
            (1, 2),
        ),
        (
            {"kind": "explanation", "instruction": "Use shorter sentences."},
            "draft_explanation",
            (1, 2),
        ),
    ],
)
def test_each_feedback_class_uses_graph_plan_and_expected_adapter_calls(
    feedback: dict[str, Any], restart: str, calls: tuple[int, int]
) -> None:
    adapters = Adapters()
    run = _run(adapters=adapters)
    parent = _revision_id(run)
    result = run.resume(
        "edit",
        "Apply the typed change.",
        disposition="revise",
        feedback_items=[feedback],
        expected_revision_id=parent,
    )
    ledger = validate_revision_state(result, TOKEN)
    child = ledger.revisions[-1]
    assert child.parent_revision_id == parent
    assert child.plan is not None and child.plan.restart_stage == restart
    assert child.plan.feedback_classes == [feedback["kind"]]
    assert (adapters.retrieval_calls, adapters.provider_calls) == calls


def test_mixed_feedback_uses_earliest_graph_route_and_preserves_exact_lineage() -> None:
    adapters = Adapters()
    run = _run(adapters=adapters)
    parent = _revision_id(run)
    run.resume(
        "reject",
        "Change the profile and explanation.",
        disposition="revise",
        feedback_items=[
            {"kind": "explanation", "instruction": "Be concise."},
            {"kind": "profile", "patch": {"horizon_years": 20}},
        ],
        expected_revision_id=parent,
    )
    ledger = validate_revision_state(run.state, TOKEN)
    previous, current = ledger.revisions[-2:]
    assert previous.status == "rejected"
    assert current.parent_revision_id == previous.revision_id
    assert current.triggering_decision_id == previous.review_decision_id
    assert current.plan is not None
    assert current.plan.restart_stage == "validate_profile"
    assert current.plan.feedback_classes == ["profile", "explanation"]


@pytest.mark.parametrize(
    ("action", "disposition", "expected"),
    [("approve", None, "approved"), ("reject", "close", "rejected")],
)
def test_terminal_decisions_need_no_external_adapters(
    action: str, disposition: str | None, expected: str
) -> None:
    run = _run(durable=True)
    revision = _revision_id(run)
    result = run.resume(
        action,
        "Close this review." if action == "reject" else "",
        disposition=disposition,
        expected_revision_id=revision,
    )
    assert result["status"] == expected


def test_durable_policy_only_profile_revision_remains_supported() -> None:
    run = _run(durable=True)
    parent = _revision_id(run)
    result = run.resume(
        "edit",
        "Extend the horizon.",
        disposition="revise",
        feedback_items=[{"kind": "profile", "patch": {"horizon_years": 19}}],
        expected_revision_id=parent,
    )
    assert result["status"] == "awaiting_human_review"
    assert validate_revision_state(result, TOKEN).revisions[-1].parent_revision_id == parent


def test_stale_or_duplicate_rendered_revision_fails_before_second_decision() -> None:
    run = _run()
    parent = _revision_id(run)
    run.resume(
        "edit",
        "Extend the horizon.",
        disposition="revise",
        feedback_items=[{"kind": "profile", "patch": {"horizon_years": 19}}],
        expected_revision_id=parent,
    )
    before = deepcopy(run.state["revision_ledger"])
    with pytest.raises(ValueError, match="stale"):
        run.resume("approve", expected_revision_id=parent)
    assert run.state["revision_ledger"] == before
    assert len(validate_revision_state(run.state, TOKEN).decisions) == 1


def test_unavailable_adapter_preflight_does_not_mutate_ledger_or_lifecycle() -> None:
    adapters = Adapters()
    run = _run(adapters=adapters)
    run.explanation_generator_usable = False
    revision = _revision_id(run)
    state = deepcopy(run.state)
    lifecycle = deepcopy(run.lifecycle())
    with pytest.raises(ValueError, match="explanation adapter is unavailable"):
        run.resume(
            "edit",
            "Rewrite the explanation.",
            disposition="revise",
            feedback_items=[{"kind": "explanation", "instruction": "Be concise."}],
            expected_revision_id=revision,
        )
    assert run.state == state
    assert run.lifecycle() == lifecycle
    assert (adapters.retrieval_calls, adapters.provider_calls) == (1, 1)


@pytest.mark.parametrize(
    ("feedback", "restart"),
    [
        (
            {"kind": "screening_policy", "patch": {"max_expense_ratio_pct": 2.0}},
            "screen_candidates",
        ),
        (
            {"kind": "construction_policy", "patch": {"max_category_weight_bps": 9000}},
            "construct_portfolio",
        ),
        ({"kind": "explanation", "instruction": "Use shorter sentences."}, "draft_explanation"),
    ],
)
def test_downstream_explanation_reruns_keep_generator_when_retriever_is_closed(
    feedback: dict[str, Any], restart: str
) -> None:
    adapters = Adapters()
    run = _run(adapters=adapters)
    run.candidate_retriever_usable = False
    run.explanation_generator_usable = True
    parent = _revision_id(run)

    result = run.resume(
        "edit",
        "Apply the downstream-only change.",
        disposition="revise",
        feedback_items=[feedback],
        expected_revision_id=parent,
    )

    child = validate_revision_state(result, TOKEN).revisions[-1]
    assert child.plan is not None and child.plan.restart_stage == restart
    assert (adapters.retrieval_calls, adapters.provider_calls) == (1, 2)


def test_failed_retry_is_exact_and_ineligible_success_has_zero_calls() -> None:
    adapters = Adapters()
    adapters.fail_retrieval = True
    run = _run(adapters=adapters)
    receipt = validate_revision_state(run.state, TOKEN).revisions[-1].receipts[-1]
    assert receipt.status == "failed"
    target = _retry_target(run.audit())
    assert target == {
        "revision_id": receipt.revision_id,
        "operation_id": receipt.operation_id,
        "stage": receipt.stage,
        "status": "failed",
    }
    adapters.fail_retrieval = False
    result = run.retry(receipt.operation_id, expected_revision_id=receipt.revision_id)
    assert result["status"] == "awaiting_human_review"
    calls = (adapters.retrieval_calls, adapters.provider_calls)
    with pytest.raises(ValueError, match="current failed or ambiguous"):
        run.retry(receipt.operation_id, expected_revision_id=receipt.revision_id)
    assert (adapters.retrieval_calls, adapters.provider_calls) == calls


def test_unknown_submission_requires_no_call_refresh_before_retry() -> None:
    adapters = Adapters()
    run = _run(adapters=adapters)
    revision = _revision_id(run)
    adapters.crash_provider = True
    with pytest.raises(RuntimeError, match="simulated loss"):
        run.resume(
            "edit",
            "Rewrite the explanation.",
            disposition="revise",
            feedback_items=[{"kind": "explanation", "instruction": "Be concise."}],
            expected_revision_id=revision,
        )
    assert run.submission_outcome_unknown is True
    calls = (adapters.retrieval_calls, adapters.provider_calls)
    with pytest.raises(ValueError, match="Refresh this exact thread"):
        run.resume("approve")
    run.refresh()
    assert run.submission_outcome_unknown is False
    assert (adapters.retrieval_calls, adapters.provider_calls) == calls
    retry = _retry_target(run.audit())
    assert retry is not None and retry["status"] == "started"
    adapters.crash_provider = False
    assert (
        run.retry(retry["operation_id"], expected_revision_id=retry["revision_id"])["status"]
        == "awaiting_human_review"
    )


def test_decision_context_exit_failure_requires_refresh_after_committed_mutation() -> None:
    store = ExitFailingStore()
    run = _run(checkpoint_store=store)
    parent = _revision_id(run)
    store.fail_next_exit = True

    with pytest.raises(RuntimeError, match="managed exit failed"):
        run.resume(
            "edit",
            "Extend the horizon.",
            disposition="revise",
            feedback_items=[{"kind": "profile", "patch": {"horizon_years": 19}}],
            expected_revision_id=parent,
        )

    assert run.submission_outcome_unknown is True
    with pytest.raises(ValueError, match="Refresh this exact thread"):
        run.resume("approve")
    refreshed = run.refresh()
    child = validate_revision_state(refreshed, TOKEN).revisions[-1]
    assert run.submission_outcome_unknown is False
    assert child.parent_revision_id == parent


def test_retry_context_exit_failure_requires_refresh_after_committed_mutation() -> None:
    adapters = Adapters()
    adapters.fail_retrieval = True
    store = ExitFailingStore()
    run = _run(adapters=adapters, checkpoint_store=store)
    failed = validate_revision_state(run.state, TOKEN).revisions[-1].receipts[-1]
    adapters.fail_retrieval = False
    store.fail_next_exit = True

    with pytest.raises(RuntimeError, match="managed exit failed"):
        run.retry(failed.operation_id, expected_revision_id=failed.revision_id)

    assert run.submission_outcome_unknown is True
    assert (adapters.retrieval_calls, adapters.provider_calls) == (2, 1)
    with pytest.raises(ValueError, match="Refresh this exact thread"):
        run.retry(failed.operation_id, expected_revision_id=failed.revision_id)
    refreshed = run.refresh()
    assert run.submission_outcome_unknown is False
    assert refreshed["status"] == "awaiting_human_review"
    assert (adapters.retrieval_calls, adapters.provider_calls) == (2, 1)


def test_failed_restore_replaces_stale_query_token_for_next_rerun(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {"dashboard_run": object()}
            self.query_params: dict[str, str] = {"review": OTHER}
            self.errors: list[str] = []

        def error(self, message: str) -> None:
            self.errors.append(message)

    def fail_restore(token: str) -> None:
        assert token == TOKEN
        raise ValueError("damaged exact token")

    monkeypatch.setattr(dashboard_app, "load_dashboard_run", fail_restore)
    st = FakeStreamlit()

    _restore_saved_run(st, TOKEN)

    assert "dashboard_run" not in st.session_state
    assert st.session_state["restore_attempted_token"] == TOKEN
    assert st.session_state[_SELECTED_REVIEW_KEY] == TOKEN
    assert st.query_params["review"] == TOKEN
    assert st.errors == [
        "The saved review could not be restored. Check the token, checkpoint dependency, "
        "and local PostgreSQL service."
    ]
    should_auto_restore = (
        "dashboard_run" not in st.session_state
        and st.query_params["review"]
        and st.session_state.get("restore_attempted_token") != st.query_params["review"]
    )
    assert should_auto_restore is False


def test_allowlisted_audit_omits_values_profiles_tokens_and_raw_content() -> None:
    run = _run(adapters=Adapters())
    history = dashboard_audit(run.state, TOKEN)
    serialized = repr(history)
    assert "thread_id" not in history
    assert TOKEN not in serialized
    assert "value" not in serialized
    assert "content" not in serialized
    assert "raw_provider_output" not in serialized
    revision = history["revisions"][0]
    assert set(revision["profile_version"]) == {"artifact_id", "digest"}
    assert revision["snapshot"]["version"] == "local-synthetic-v1"
    assert revision["receipts"][0]["status"] == "succeeded"


def test_lifecycle_inspection_does_not_renew_and_expired_token_can_be_deleted() -> None:
    time = Time()
    run = _run(durable=True, clock=time)
    store = run.checkpoint_store
    assert store is not None
    before = inspect_saved_review_lifecycle(TOKEN, checkpoint_store=store)
    time.now += timedelta(days=30)
    expired = inspect_saved_review_lifecycle(TOKEN, checkpoint_store=store)
    assert expired["status"] == "expired"
    assert expired["lifecycle"]["last_activity_at"] == before["lifecycle"]["last_activity_at"]
    assert delete_saved_review(TOKEN, TOKEN, confirmed=False, checkpoint_store=store) == "failure"
    assert delete_saved_review(TOKEN, OTHER, confirmed=True, checkpoint_store=store) == "failure"
    assert delete_saved_review(TOKEN, TOKEN, confirmed=True, checkpoint_store=store) == "deleted"
    assert inspect_saved_review_lifecycle(TOKEN, checkpoint_store=store) == {"status": "not_found"}
    assert delete_saved_review(TOKEN, TOKEN, confirmed=True, checkpoint_store=store) == "not_found"


def test_legacy_exact_token_can_be_inspected_and_deleted_without_graph_restore() -> None:
    store = DurableStore(clock=Time())
    with store.open() as saver:
        graph = build_graph(checkpointer=saver)
        graph.invoke({"profile": valid_profile()}, {"configurable": {"thread_id": TOKEN}})
    assert inspect_saved_review_lifecycle(TOKEN, checkpoint_store=store) == {"status": "legacy"}
    assert delete_saved_review(TOKEN, TOKEN, confirmed=True, checkpoint_store=store) == "deleted"


def test_tampered_audit_does_not_block_independent_exact_deletion() -> None:
    run = _run(durable=True)
    store = run.checkpoint_store
    assert store is not None
    run.state["revision_digest"] = "0" * 64
    with pytest.raises(ValueError, match="audit"):
        run.audit()
    assert delete_saved_review(TOKEN, TOKEN, confirmed=True, checkpoint_store=store) == "deleted"
    assert inspect_saved_review_lifecycle(TOKEN, checkpoint_store=store) == {"status": "not_found"}


def test_exact_deletion_leaves_other_thread_intact_and_sanitizes_store_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    time = Time()
    first = _run(durable=True, clock=time)
    store = first.checkpoint_store
    assert isinstance(store, DurableStore)
    with store.managed(OTHER, create=True) as saver:
        graph = build_graph(checkpointer=saver)
        graph.invoke({"profile": valid_profile()}, {"configurable": {"thread_id": OTHER}})
    assert delete_saved_review(TOKEN, TOKEN, confirmed=True, checkpoint_store=store) == "deleted"
    assert inspect_saved_review_lifecycle(OTHER, checkpoint_store=store)["status"] == "active"

    def fail(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("private database details")

    monkeypatch.setattr(store, "delete", fail)
    assert delete_saved_review(OTHER, OTHER, confirmed=True, checkpoint_store=store) == "failure"


def test_streamlit_policy_review_renders_revision_lifecycle_and_typed_controls() -> None:
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")
    app_path = Path(__file__).parents[1] / "src" / "etf_advisor" / "dashboard_app.py"
    app = streamlit_testing.AppTest.from_file(str(app_path))
    app.session_state["dashboard_run"] = _run()
    app.run(timeout=10)
    assert not app.exception
    assert any(button.label == "Refresh exact thread" for button in app.button)
    assert any(button.label == "Discard process-local state" for button in app.button)
    decision = next(radio for radio in app.radio if radio.label == "Decision")
    decision.set_value("Edit")
    app.run(timeout=10)
    assert any(select.label == "Typed feedback" for select in app.multiselect)
    assert any(expander.label == "Revision and operation history" for expander in app.expander)
