import json
from datetime import UTC, datetime, timedelta

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.explanation import (
    ExplanationGenerationError,
    ExplanationRequest,
    ExplanationResult,
    GeneratedExplanation,
    GroundedStatement,
    GroundingBasis,
)
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.evidence import (
    CandidateEvidenceBundle,
    EvidenceRetrievalError,
    HybridCandidateEvidenceRetriever,
    select_candidate_evidence,
)
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, SectorExposure


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
    assert "source evidence" not in paused["__interrupt__"][0].value["question"].lower()
    assert "candidate_evidence" not in paused["__interrupt__"][0].value
    assert paused["draft_policy"]["target_allocation"] == {
        "growth_assets_pct": 70.0,
        "defensive_assets_pct": 30.0,
    }
    assert paused["draft_policy"]["initial_investment_usd"]["growth_assets_usd"] == 35_000.0
    json.dumps(paused["draft_policy"])

    completed = graph.invoke(Command(resume={"action": "approve"}), config=config)

    assert completed["status"] == "approved"
    assert completed["final_message"].startswith("Policy draft approved")
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
            "quote_type": "ETF",
            "market": "us_market",
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
    assert paused["candidate_screening"]["status"] == "ready"
    assert paused["candidate_screening"]["candidates"][0]["verdict"] == "unknown"
    assert paused["__interrupt__"][0].value["candidate_evidence"] == paused["candidate_evidence"]
    assert paused["__interrupt__"][0].value["candidate_screening"] == paused["candidate_screening"]
    assert "source evidence" in paused["__interrupt__"][0].value["question"].lower()
    json.dumps(paused["candidate_evidence"])
    json.dumps(paused["candidate_screening"])

    completed = graph.invoke(
        Command(resume={"action": "approve"}),
        config={"configurable": {"thread_id": "evidence-review"}},
    )

    assert completed["status"] == "approved"
    assert completed["final_message"].startswith("Candidate screening")
    assert "No ETF recommendation or trade" in completed["final_message"]


def test_injected_explanation_is_grounded_before_review() -> None:
    retriever = _current_evidence_retriever()
    calls: list[str] = []

    class FixedGenerator:
        def generate(self, request: ExplanationRequest) -> ExplanationResult:
            calls.append(request.profile.objective.value)
            assert request.candidate_evidence.status == "ready"
            return ExplanationResult(
                provider="test",
                model="fixed",
                explanation=_valid_generated_explanation(),
            )

    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=retriever,
        explanation_generator=FixedGenerator(),
    )
    config = {"configurable": {"thread_id": "explanation-review"}}

    paused = graph.invoke({"profile": valid_profile()}, config=config)

    assert paused["status"] == "awaiting_human_review"
    assert paused["draft_explanation"]["status"] == "ready"
    assert paused["draft_explanation"]["citations"][0]["document_id"] == "doc-spy"
    assert paused["__interrupt__"][0].value["draft_explanation"] == paused["draft_explanation"]
    assert "grounded explanation" in paused["__interrupt__"][0].value["question"].lower()
    json.dumps(paused["draft_explanation"])

    completed = graph.invoke(Command(resume={"action": "approve"}), config=config)
    assert completed["status"] == "approved"
    assert completed["final_message"].startswith("Grounded explanation")
    assert calls == ["growth"]


def test_explanation_failure_stops_before_human_review() -> None:
    class FailingGenerator:
        def generate(self, request: ExplanationRequest) -> ExplanationResult:
            raise ExplanationGenerationError("provider unavailable")

    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=_current_evidence_retriever(),
        explanation_generator=FailingGenerator(),
    )

    result = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "explanation-failure"}},
    )

    assert result["status"] == "explanation_blocked"
    assert result["draft_explanation"] == {}
    assert result["explanation_errors"] == [
        {"type": "generation_error", "message": "provider unavailable"}
    ]
    assert "__interrupt__" not in result


def test_screening_contract_failure_stops_before_explanation_or_review() -> None:
    class TamperedRetriever:
        def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> CandidateEvidenceBundle:
            bundle = _current_evidence_retriever().retrieve(profile, limit=limit)
            bundle.candidates[0].metadata["field_provenance_json"] = "{not-json"
            return bundle

    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=TamperedRetriever(),
    )

    result = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "screening-contract-failure"}},
    )

    assert result["status"] == "screening_blocked"
    assert result["candidate_screening"] == {}
    assert result["screening_errors"] == [
        {
            "type": "screening_contract",
            "message": "Candidate screening failed source or policy contract validation.",
        }
    ]
    assert "__interrupt__" not in result


def test_prohibited_explanation_claim_stops_before_human_review() -> None:
    class UnsafeGenerator:
        def generate(self, request: ExplanationRequest) -> ExplanationResult:
            explanation = _valid_generated_explanation()
            explanation.evidence_points[0].text = "SPY guarantees positive returns."
            return ExplanationResult(
                provider="test",
                model="unsafe",
                explanation=explanation,
            )

    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=_current_evidence_retriever(),
        explanation_generator=UnsafeGenerator(),
    )

    result = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "unsafe-explanation"}},
    )

    assert result["status"] == "explanation_blocked"
    assert result["draft_explanation"] == {}
    assert result["explanation_errors"] == [
        {
            "type": "explanation_contract",
            "message": "Generated explanation failed safety or grounding validation.",
        }
    ]
    assert "__interrupt__" not in result


def test_reused_thread_clears_prior_explanation_before_provider_failure() -> None:
    class SwitchableGenerator:
        fail = False

        def generate(self, request: ExplanationRequest) -> ExplanationResult:
            if self.fail:
                raise ExplanationGenerationError("provider unavailable")
            return ExplanationResult(
                provider="test",
                model="fixed",
                explanation=_valid_generated_explanation(),
            )

    generator = SwitchableGenerator()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=_current_evidence_retriever(),
        explanation_generator=generator,
    )
    config = {"configurable": {"thread_id": "reused-explanation-thread"}}

    first_paused = graph.invoke({"profile": valid_profile()}, config=config)
    assert first_paused["draft_explanation"]["status"] == "ready"
    graph.invoke(Command(resume={"action": "approve"}), config=config)

    generator.fail = True
    second_result = graph.invoke({"profile": valid_profile()}, config=config)

    assert second_result["status"] == "explanation_blocked"
    assert second_result["draft_explanation"] == {}
    assert second_result["review_decision"] == {}
    assert second_result["final_message"] == ""
    assert "__interrupt__" not in second_result


def test_explanation_generator_requires_evidence_retriever() -> None:
    class UnusedGenerator:
        def generate(self, request: ExplanationRequest) -> ExplanationResult:
            raise AssertionError("must not be called")

    with pytest.raises(ValueError, match="requires a candidate evidence retriever"):
        build_graph(explanation_generator=UnusedGenerator())


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
            "quote_type": "ETF",
            "market": "us_market",
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
    assert result["candidate_evidence"] == {}
    assert result["candidate_screening"] == {}
    assert result["screening_errors"] == []
    assert result["evidence_errors"] == [
        {"type": "retrieval_error", "message": "source service unavailable"}
    ]
    assert "__interrupt__" not in result


def test_reused_thread_cannot_review_retained_evidence_after_retrieval_failure() -> None:
    checked_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    current = GraphEnrichedSource(
        document_id="doc-spy",
        content="SPY source facts",
        metadata={
            "symbol": "SPY",
            "source": "yahoo_finance",
            "source_url": "https://finance.yahoo.com/quote/SPY/",
            "observed_at": "2026-08-28T11:00:00Z",
            "quote_type": "ETF",
            "market": "us_market",
        },
    )
    search = _SwitchableSearch([current])
    retriever = HybridCandidateEvidenceRetriever(
        search,
        clock=lambda: checked_at,
        max_age=timedelta(hours=24),
    )
    graph = build_graph(checkpointer=InMemorySaver(), candidate_retriever=retriever)
    config = {"configurable": {"thread_id": "reused-evidence-thread"}}

    first_paused = graph.invoke({"profile": valid_profile()}, config=config)
    assert first_paused["candidate_evidence"]["status"] == "ready"
    first_completed = graph.invoke(Command(resume={"action": "approve"}), config=config)
    assert first_completed["status"] == "approved"

    search.fail = True
    second_result = graph.invoke({"profile": valid_profile()}, config=config)

    assert second_result["status"] == "evidence_blocked"
    assert second_result["candidate_evidence"] == {}
    assert second_result["candidate_screening"] == {}
    assert second_result["screening_errors"] == []
    assert second_result["evidence_errors"] == [
        {"type": "retrieval_error", "message": "Source evidence retrieval failed."}
    ]
    assert second_result["review_decision"] == {}
    assert second_result["final_message"] == ""
    assert "__interrupt__" not in second_result


def test_evidence_for_a_different_profile_is_blocked_before_review() -> None:
    checked_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    source_result = GraphEnrichedSource(
        document_id="doc-spy",
        content="SPY source facts",
        metadata={
            "symbol": "SPY",
            "source": "yahoo_finance",
            "source_url": "https://finance.yahoo.com/quote/SPY/",
            "observed_at": "2026-08-28T11:00:00Z",
            "quote_type": "ETF",
            "market": "us_market",
        },
    )

    class MismatchedRetriever:
        def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> CandidateEvidenceBundle:
            different_profile = profile.model_copy(update={"objective": "income"})
            return select_candidate_evidence(
                different_profile,
                [source_result],
                query="income evidence",
                checked_at=checked_at,
                max_age=timedelta(hours=24),
                limit=limit,
            )

    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=MismatchedRetriever(),
    )

    result = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "mismatched-evidence-profile"}},
    )

    assert result["status"] == "evidence_blocked"
    assert result["candidate_evidence"]["status"] == "blocked"
    assert result["candidate_evidence"]["errors"] == [
        "Evidence objective does not match the validated profile."
    ]
    assert result["evidence_errors"] == [
        {
            "type": "evidence_contract",
            "message": "Evidence objective does not match the validated profile.",
        }
    ]
    assert "__interrupt__" not in result


def test_workflow_revalidates_freshness_from_replaceable_retrievers() -> None:
    checked_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    current = GraphEnrichedSource(
        document_id="doc-spy",
        content="SPY source facts",
        metadata={
            "symbol": "SPY",
            "source": "yahoo_finance",
            "source_url": "https://finance.yahoo.com/quote/SPY/",
            "observed_at": "2026-08-28T11:00:00Z",
            "quote_type": "ETF",
            "market": "us_market",
        },
    )
    ready = select_candidate_evidence(
        InvestorProfile.model_validate(valid_profile()),
        [current],
        query="broad US exposure",
        checked_at=checked_at,
        max_age=timedelta(hours=24),
    )
    stale_time = checked_at - timedelta(hours=48)
    forged_observation = ready.health.observations[0].model_copy(update={"observed_at": stale_time})
    forged_health = ready.health.model_copy(update={"observations": [forged_observation]})
    forged_candidate = ready.candidates[0].model_copy(update={"observed_at": stale_time})
    forged_bundle = ready.model_copy(
        update={"health": forged_health, "candidates": [forged_candidate]}
    )

    class ForgedRetriever:
        def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> CandidateEvidenceBundle:
            return forged_bundle

    graph = build_graph(checkpointer=InMemorySaver(), candidate_retriever=ForgedRetriever())
    result = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "forged-freshness"}},
    )

    assert result["status"] == "evidence_blocked"
    assert result["candidate_evidence"] == {}
    assert result["evidence_errors"] == [
        {
            "type": "evidence_contract",
            "message": "Source evidence bundle failed contract validation.",
        }
    ]
    assert "__interrupt__" not in result


def test_workflow_rejects_foreign_graph_context_from_replaceable_retriever() -> None:
    checked_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    source_result = GraphEnrichedSource(
        document_id="doc-spy",
        content="SPY source facts",
        metadata={
            "symbol": "SPY",
            "source": "yahoo_finance",
            "source_url": "https://finance.yahoo.com/quote/SPY/",
            "observed_at": "2026-08-28T11:00:00Z",
            "quote_type": "ETF",
            "market": "us_market",
        },
        graph_context=GraphContext(
            source_document_id="doc-spy",
            symbol="SPY",
            etf_name="SPY",
            sector_exposures_status="available",
            sector_exposures=[SectorExposure(name="technology", weight_pct=37.4)],
        ),
    )
    ready = select_candidate_evidence(
        InvestorProfile.model_validate(valid_profile()),
        [source_result],
        query="broad US exposure",
        checked_at=checked_at,
        max_age=timedelta(hours=24),
    )
    foreign_context = ready.candidates[0].graph_context.model_copy(
        update={
            "source_document_id": "doc-qqq",
            "symbol": "QQQ",
            "sector_exposures": [SectorExposure(name="technology", weight_pct=57.95)],
        }
    )
    forged_candidate = ready.candidates[0].model_copy(update={"graph_context": foreign_context})
    forged_bundle = ready.model_copy(update={"candidates": [forged_candidate]})

    class ForgedRetriever:
        def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> CandidateEvidenceBundle:
            return forged_bundle

    graph = build_graph(checkpointer=InMemorySaver(), candidate_retriever=ForgedRetriever())
    result = graph.invoke(
        {"profile": valid_profile()},
        config={"configurable": {"thread_id": "foreign-graph-context"}},
    )

    assert result["status"] == "evidence_blocked"
    assert result["candidate_evidence"] == {}
    assert result["evidence_errors"] == [
        {
            "type": "evidence_contract",
            "message": "Source evidence bundle failed contract validation.",
        }
    ]
    assert "__interrupt__" not in result


class _FixedSearch:
    def __init__(self, results: list[GraphEnrichedSource]) -> None:
        self.results = results

    def search(self, query: str, limit: int = 5) -> list[GraphEnrichedSource]:
        return self.results[:limit]


class _SwitchableSearch(_FixedSearch):
    def __init__(self, results: list[GraphEnrichedSource]) -> None:
        super().__init__(results)
        self.fail = False

    def search(self, query: str, limit: int = 5) -> list[GraphEnrichedSource]:
        if self.fail:
            raise OSError("store unavailable")
        return super().search(query, limit=limit)


def _current_evidence_retriever() -> HybridCandidateEvidenceRetriever:
    checked_at = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
    result = GraphEnrichedSource(
        document_id="doc-spy",
        content="SPY source facts",
        metadata={
            "symbol": "SPY",
            "source": "yahoo_finance",
            "source_url": "https://finance.yahoo.com/quote/SPY/",
            "observed_at": "2026-08-28T11:00:00Z",
            "quote_type": "ETF",
            "market": "us_market",
        },
    )
    return HybridCandidateEvidenceRetriever(
        _FixedSearch([result]),
        clock=lambda: checked_at,
        max_age=timedelta(hours=24),
    )


def _valid_generated_explanation() -> GeneratedExplanation:
    return GeneratedExplanation(
        summary=GroundedStatement(
            text="This illustrates a growth objective.",
            basis=GroundingBasis.POLICY,
            references=["profile.objective"],
        ),
        policy_points=[
            GroundedStatement(
                text="The target remains inside the policy band.",
                basis=GroundingBasis.POLICY,
                references=["policy.target_allocation"],
            )
        ],
        evidence_points=[
            GroundedStatement(
                text="SPY is source-grounded research context.",
                basis=GroundingBasis.SOURCE,
                references=["doc-spy"],
                subject_symbols=["SPY"],
            )
        ],
        tradeoffs=[
            GroundedStatement(
                text="The drawdown tolerance remains a review constraint.",
                basis=GroundingBasis.POLICY,
                references=["profile.max_drawdown_pct"],
            )
        ],
    )
