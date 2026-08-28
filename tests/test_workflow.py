import json
from datetime import UTC, datetime, timedelta

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.evidence import (
    EvidenceRetrievalError,
    HybridCandidateEvidenceRetriever,
)
from etf_advisor.rag.models import GraphEnrichedSource


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


def test_non_quantizable_cash_amount_stops_before_policy_calculation() -> None:
    graph = build_graph(checkpointer=InMemorySaver())
    profile = valid_profile()
    profile["initial_investment_usd"] = 1e26

    result = graph.invoke(
        {"profile": profile},
        config={"configurable": {"thread_id": "invalid-cash-amount"}},
    )

    assert result["status"] == "invalid_profile"
    assert result["validation_errors"][0]["loc"] == ("initial_investment_usd",)
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


def test_injected_evidence_is_attached_to_review_interrupt() -> None:
    checked_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = GraphEnrichedSource(
        document_id="doc-spy",
        content="SPY source facts",
        metadata={
            "symbol": "SPY",
            "name": "SPDR S&P 500 ETF Trust",
            "source": "yahoo_finance",
            "source_url": "https://finance.yahoo.com/quote/SPY/",
            "observed_at": "2026-08-28T11:00:00Z",
        },
    )
    retriever = HybridCandidateEvidenceRetriever(
        _FixedSearch([result]),
        clock=lambda: checked_at,
        max_age=timedelta(hours=24),
    )
    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=retriever,
        candidate_limit=2,
    )

    paused = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "evidence-review"}},
    )

    assert paused["status"] == "awaiting_human_review"
    assert paused["candidate_evidence"]["status"] == "ready"
    assert paused["candidate_evidence"]["candidates"][0]["symbol"] == "SPY"
    assert paused["__interrupt__"][0].value["candidate_evidence"] == paused["candidate_evidence"]
    json.dumps(paused["candidate_evidence"])

    completed = graph.invoke(
        Command(resume={"action": "approve"}),
        config={"configurable": {"thread_id": "evidence-review"}},
    )

    assert completed["status"] == "approved"
    assert "No ETF recommendation or trade" in completed["final_message"]


def test_blocked_evidence_stops_before_human_review() -> None:
    checked_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    stale = GraphEnrichedSource(
        document_id="doc-stale",
        content="Stale source facts",
        metadata={
            "symbol": "SPY",
            "source": "yahoo_finance",
            "source_url": "https://finance.yahoo.com/quote/SPY/",
            "observed_at": "2026-08-26T00:00:00Z",
        },
    )
    retriever = HybridCandidateEvidenceRetriever(
        _FixedSearch([stale]),
        clock=lambda: checked_at,
        max_age=timedelta(hours=24),
    )
    graph = build_graph(checkpointer=InMemorySaver(), candidate_retriever=retriever)

    result = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "blocked-evidence"}},
    )

    assert result["status"] == "evidence_blocked"
    assert result["candidate_evidence"]["status"] == "blocked"
    assert result["candidate_evidence"]["health"]["observations"][0]["status"] == "stale"
    assert result["evidence_errors"]
    assert "__interrupt__" not in result


def test_retrieval_failure_stops_before_human_review() -> None:
    class FailingRetriever:
        def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> object:
            raise EvidenceRetrievalError("source service unavailable")

    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=FailingRetriever(),
    )

    result = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "retrieval-failure"}},
    )

    assert result["status"] == "evidence_blocked"
    assert result["evidence_errors"] == [
        {"type": "retrieval_error", "message": "source service unavailable"}
    ]
    assert "__interrupt__" not in result


class _FixedSearch:
    def __init__(self, results: list[GraphEnrichedSource]) -> None:
        self.results = results

    def search(self, query: str, limit: int = 5) -> list[GraphEnrichedSource]:
        return self.results[:limit]
