import json

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from etf_advisor.graph.workflow import build_graph


def valid_profile() -> dict[str, object]:
    return {
        "horizon_years": 15,
        "risk_tolerance": "moderate",
        "objective": "growth",
        "max_drawdown_pct": 30,
        "initial_investment_usd": 50_000,
        "recurring_monthly_usd": 1_000,
        "excluded_sectors": ["tobacco"],
    }


def test_invalid_profile_stops_before_review() -> None:
    graph = build_graph(checkpointer=InMemorySaver())
    result = graph.invoke(
        {"profile": {"horizon_years": 0}},
        config={"configurable": {"thread_id": "invalid-profile"}},
    )

    assert result["status"] == "invalid_profile"
    assert result["validation_errors"]
    assert "__interrupt__" not in result


def test_valid_profile_pauses_and_resumes_after_approval() -> None:
    graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "approval-flow"}}

    paused = graph.invoke({"profile": valid_profile()}, config=config)

    assert paused["status"] == "awaiting_human_review"
    assert paused["__interrupt__"]
    assert paused["draft_policy"]["target_allocation"] == {
        "growth_assets_pct": 70.0,
        "defensive_assets_pct": 30.0,
    }
    assert paused["draft_policy"]["initial_investment_usd"]["growth_assets_usd"] == 35_000.0
    json.dumps(paused["draft_policy"])

    completed = graph.invoke(Command(resume={"action": "approve"}), config=config)

    assert completed["status"] == "approved"
    assert "No ETF recommendation or trade" in completed["final_message"]


def test_rejection_routes_to_revision() -> None:
    graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "rejection-flow"}}
    graph.invoke({"profile": valid_profile()}, config=config)

    completed = graph.invoke(
        Command(resume={"action": "reject", "feedback": "Reduce the growth range."}),
        config=config,
    )

    assert completed["status"] == "needs_revision"
    assert completed["final_message"] == "Reduce the growth range."
