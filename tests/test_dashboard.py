from types import SimpleNamespace
from typing import Any

import pytest

import etf_advisor.dashboard as dashboard
from etf_advisor.dashboard import (
    DashboardOptions,
    DashboardRun,
    parse_excluded_sectors,
    review_payload,
)


class FakeGraph:
    def __init__(self) -> None:
        self.inputs: list[object] = []

    def invoke(self, value: object, config: dict[str, Any]) -> dict[str, Any]:
        self.inputs.append(value)
        return {"status": "approved", "final_message": "Approved safely."}


def paused_state() -> dict[str, Any]:
    payload = {
        "kind": "portfolio_policy_review",
        "question": "Approve?",
        "allowed_actions": ["approve", "edit", "reject"],
        "draft_policy": {"target_allocation": {}},
    }
    return {
        "status": "awaiting_human_review",
        "__interrupt__": (SimpleNamespace(value=payload),),
    }


def test_dashboard_options_require_evidence_for_explanation() -> None:
    with pytest.raises(ValueError, match="require source evidence"):
        DashboardOptions(with_explanation=True)


def test_review_payload_rejects_missing_or_unsupported_interrupts() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        review_payload({"status": "awaiting_human_review"})

    state = paused_state()
    state["__interrupt__"] = (SimpleNamespace(value={"kind": "other"}),)
    with pytest.raises(ValueError, match="unsupported"):
        review_payload(state)


def test_dashboard_run_resumes_exact_thread_after_approval() -> None:
    graph = FakeGraph()
    run = DashboardRun(
        graph=graph,
        config={"configurable": {"thread_id": "dashboard-review"}},
        state=paused_state(),
    )

    completed = run.resume("approve")

    assert completed["status"] == "approved"
    assert run.config["configurable"]["thread_id"] == "dashboard-review"
    assert len(graph.inputs) == 1
    assert graph.inputs[0].resume == {"action": "approve"}


@pytest.mark.parametrize("action", ["edit", "reject"])
def test_revision_decisions_require_feedback(action: str) -> None:
    run = DashboardRun(graph=FakeGraph(), config={}, state=paused_state())

    with pytest.raises(ValueError, match="require reviewer feedback"):
        run.resume(action, "  ")


def test_dashboard_run_passes_trimmed_revision_feedback() -> None:
    graph = FakeGraph()
    run = DashboardRun(graph=graph, config={}, state=paused_state())

    run.resume("edit", "  Lower the growth range.  ")

    assert graph.inputs[0].resume == {
        "action": "edit",
        "feedback": "Lower the growth range.",
    }


def test_parse_excluded_sectors_trims_and_deduplicates_case_insensitively() -> None:
    assert parse_excluded_sectors(" Energy,utilities, energy, ,Health Care ") == [
        "Energy",
        "utilities",
        "Health Care",
    ]


def test_policy_only_dashboard_run_needs_no_live_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StartGraph(FakeGraph):
        def invoke(self, value: object, config: dict[str, Any]) -> dict[str, Any]:
            return paused_state()

    monkeypatch.setattr(dashboard, "build_graph", lambda **kwargs: StartGraph())
    monkeypatch.setattr(
        dashboard,
        "ChromaDocumentStore",
        lambda **kwargs: pytest.fail("policy-only run opened Chroma"),
    )
    monkeypatch.setattr(
        dashboard,
        "Neo4jGraphStore",
        lambda **kwargs: pytest.fail("policy-only run opened Neo4j"),
    )

    run = dashboard.start_dashboard_run(
        {"horizon_years": 10},
        DashboardOptions(),
        thread_id="offline-dashboard",
    )

    assert run.state["status"] == "awaiting_human_review"
    assert run.config == {"configurable": {"thread_id": "offline-dashboard"}}
