"""Independent new-version expectations; historical starter corpus stays unchanged."""

from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from etf_advisor.domain.construction import (
    PortfolioConstructionInput,
    PortfolioConstructionPolicy,
    PortfolioSleeve,
    _classify_candidates,
    _select_subset,
    construct_model_portfolio,
    validate_persisted_construction,
)
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.revision import ConstructionFeedback, RevisionInputs
from etf_advisor.evaluation.starter import case_artifact, load_starter_dataset
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.us_starter import StarterRequestV1

MARKERS = dict(
    starter_shortlist_algorithm="sleeve-category-feasible-v2",
    starter_subset_algorithm="sleeve-count-category-v1",
)
REPRO = dict(
    SPY="Large Blend",
    IVV="Large Blend",
    VOO="Large Blend",
    VTI="Large Blend",
    QQQ="Large Growth",
    VEA="Foreign Large Blend",
    VWO="Diversified Emerging Mkts",
    BND="Intermediate Core Bond",
    AGG="Intermediate Core Bond",
    SPAB="Intermediate Core Bond",
)


@pytest.fixture(scope="module")
def dataset() -> dict[str, Any]:
    return load_starter_dataset()


def inputs(
    dataset: dict[str, Any], risk: str = "moderate", capacity: int = 10, reproduction: bool = False
) -> PortfolioConstructionInput:
    data = deepcopy(dataset)
    case = dict(field_changes=[])
    if reproduction:
        for record in data["artifact"]["snapshot"]["records"]:
            record["category"]["value"] = REPRO.get(
                record["symbol"], "Unsupported synthetic category"
            )
    artifact = case_artifact(data, case)
    assert artifact.snapshot is not None
    request = StarterRequestV1(
        schema="us-starter-request-v1",
        universe_digest=artifact.universe_digest,
        artifact_digest=artifact.digest,
    )
    profile = InvestorProfile.model_validate(
        {
            **data["profile"],
            "risk_tolerance": risk,
            "objective": {"conservative": "income", "moderate": "balanced", "aggressive": "growth"}[
                risk
            ],
            "starter_request": request.model_dump(mode="json"),
        }
    )
    sources = [
        GraphEnrichedSource(
            document_id=d.document_id, content=d.content, metadata=d.chroma_metadata()
        )
        for d in artifact.snapshot.to_source_documents()
    ]
    evidence = select_candidate_evidence(
        profile,
        sources,
        query="Invented issue153 evidence",
        checked_at=datetime.fromisoformat(data["checked_at"]),
        max_age=timedelta(hours=120),
        future_tolerance=timedelta(minutes=5),
        limit=capacity,
        starter_artifact=artifact,
    )
    from etf_advisor.domain.screening import screen_candidate_evidence

    return PortfolioConstructionInput(
        profile=profile,
        policy_calculation=calculate_policy(profile),
        candidate_evidence=evidence,
        candidate_screening=screen_candidate_evidence(evidence),
        construction_policy=PortfolioConstructionPolicy(**MARKERS),
    )


# Exact independent vectors from approved design, not production-captured output.
VECTORS = {
    (3, "conservative"): (
        ["SPY", "BND", "AGG"],
        [2000, 4000, 4000],
        [20000, 40000, 40000],
        [5000, 10000, 10000],
    ),
    (3, "moderate"): (
        ["SPY", "QQQ", "BND"],
        [2875, 2875, 4250],
        [28750, 28750, 42500],
        [7188, 7187, 10625],
    ),
    (3, "aggressive"): (
        ["SPY", "QQQ", "BND"],
        [4750, 4750, 500],
        [47500, 47500, 5000],
        [11875, 11875, 1250],
    ),
    (5, "conservative"): (
        ["SPY", "QQQ", "BND", "AGG", "SPAB"],
        [1000, 1000, 2667, 2667, 2666],
        [10000, 10000, 26670, 26670, 26660],
        [2500, 2500, 6668, 6667, 6665],
    ),
    (5, "moderate"): (
        ["SPY", "QQQ", "VEA", "BND", "AGG"],
        [1917, 1917, 1916, 2125, 2125],
        [19170, 19170, 19160, 21250, 21250],
        [4793, 4792, 4790, 5313, 5312],
    ),
    (5, "aggressive"): (
        ["SPY", "QQQ", "VEA", "VWO", "BND"],
        [2375, 2375, 2375, 2375, 500],
        [23750, 23750, 23750, 23750, 5000],
        [5938, 5938, 5937, 5937, 1250],
    ),
}


@pytest.mark.parametrize("risk", ["conservative", "moderate", "aggressive"])
@pytest.mark.parametrize("capacity", [3, 5, 10])
def test_reproduction_exact_vectors(dataset: dict[str, Any], risk: str, capacity: int) -> None:
    result = construct_model_portfolio(inputs(dataset, risk, capacity, True))
    assert result.draft is not None
    positions = result.draft.positions
    expected = VECTORS[min(capacity, 5), risk]
    assert (
        [p.symbol for p in positions],
        [p.weight_bps for p in positions],
        [p.initial_usd_cents for p in positions],
        [p.recurring_usd_cents for p in positions],
    ) == expected
    assert result.starter_selection is not None
    assert result.starter_selection["algorithm"] == MARKERS["starter_shortlist_algorithm"]
    assert result.starter_selection["subset_algorithm"] == MARKERS["starter_subset_algorithm"]


@pytest.mark.parametrize("risk", ["conservative", "moderate", "aggressive"])
@pytest.mark.parametrize("capacity", [3, 5, 10])
def test_separate_new_expectations_for_unchanged_old_corpus(
    dataset: dict[str, Any], risk: str, capacity: int
) -> None:
    result = construct_model_portfolio(inputs(dataset, risk, capacity))
    assert result.draft is not None
    if capacity == 3:
        symbols = ["SPY", "BND", "AGG"] if risk == "conservative" else ["SPY", "IVV", "BND"]
        weights = VECTORS[3, risk][1]
    elif risk == "conservative":
        symbols, weights = ["SPY", "BND", "AGG", "SCHZ", "SPAB"], [2000] * 5
    elif risk == "moderate":
        symbols, weights = ["SPY", "IVV", "VOO", "BND", "AGG"], [1917, 1917, 1916, 2125, 2125]
    else:
        symbols, weights = ["SPY", "IVV", "VOO", "VTI", "BND"], [2375] * 4 + [500]
    assert [(p.symbol, p.weight_bps) for p in result.draft.positions] == list(
        zip(symbols, weights, strict=True)
    )
    if capacity > 3 and risk == "conservative":
        initial, recurring = [20000] * 5, [5000] * 5
    else:
        initial, recurring = VECTORS[min(capacity, 5), risk][2:]
    assert [p.initial_usd_cents for p in result.draft.positions] == initial
    assert [p.recurring_usd_cents for p in result.draft.positions] == recurring


def test_boundaries_omission_feedback_and_input_context(dataset: dict[str, Any]) -> None:
    policy = PortfolioConstructionPolicy()
    for mode in ("python", "json"):
        assert "starter_subset_algorithm" not in policy.model_dump(mode=mode)
    for value in (None, "unknown"):
        with pytest.raises(ValueError):
            PortfolioConstructionPolicy.model_validate(
                {**MARKERS, "starter_subset_algorithm": value}
            )
    with pytest.raises(ValueError, match="requires shortlist v2"):
        PortfolioConstructionPolicy(starter_subset_algorithm="sleeve-count-category-v1")
    for marker, value in MARKERS.items():
        for replacement in (value, None):
            with pytest.raises(ValueError):
                ConstructionFeedback(kind="construction_policy", patch={marker: replacement})
    current = inputs(dataset)
    raw = current.model_dump(mode="json")
    raw["profile"].pop("starter_request")
    with pytest.raises(ValueError, match="requires starter research"):
        PortfolioConstructionInput.model_validate(raw)
    with pytest.raises(ValueError, match="requires starter research"):
        RevisionInputs.model_validate(
            dict(
                profile=raw["profile"],
                construction_policy=MARKERS,
                screening_policy={},
                candidate_limit=10,
                with_evidence=True,
                with_explanation=False,
                explanation_instruction="",
            )
        )


def test_offline_repeat_and_sum_preserving_tamper(
    dataset: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    current = inputs(dataset)
    expected = construct_model_portfolio(current)
    import socket
    import sys

    import etf_advisor.clock as clock
    import etf_advisor.data.starter_collection as collection
    import etf_advisor.research.us_starter as preparation
    from etf_advisor.data.yahoo_research import YahooResearchAdapter
    from etf_advisor.explanation.provider import LangChainExplanationGenerator
    from etf_advisor.rag.evidence import PreparedStarterEvidenceRetriever

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("New selector crossed source/provider/artifact/network/clock boundary")

    for cls in (
        YahooResearchAdapter,
        LangChainExplanationGenerator,
        PreparedStarterEvidenceRetriever,
    ):
        monkeypatch.setattr(cls, "__init__", forbidden)
    monkeypatch.setattr(collection, "run_pass", forbidden)
    monkeypatch.setattr(preparation, "prepare_from_pass", forbidden)
    monkeypatch.setattr(preparation.StarterArtifact, "load", forbidden)
    original_clock = clock.system_utc_now
    for name, module in list(sys.modules.items()):
        if name.startswith("etf_advisor") and module is not None:
            for attr, value in list(vars(module).items()):
                if value is original_clock:
                    monkeypatch.setattr(module, attr, forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("artifact read"))
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **k: pytest.fail("artifact read"))
    restored = PortfolioConstructionInput.model_validate_json(current.model_dump_json())
    assert construct_model_portfolio(restored).model_dump_json() == expected.model_dump_json()
    assert validate_persisted_construction(restored, expected) == expected
    for field in ("weight_bps", "initial_usd_cents", "recurring_usd_cents"):
        assert expected.draft is not None
        bad = expected.model_copy(deep=True)
        assert bad.draft is not None
        setattr(bad.draft.positions[0], field, getattr(bad.draft.positions[0], field) + 1)
        setattr(bad.draft.positions[1], field, getattr(bad.draft.positions[1], field) - 1)
        assert validate_persisted_construction(restored, bad).status == "blocked"
    bad = expected.model_copy(deep=True)
    assert bad.starter_selection is not None
    bad.starter_selection.pop("subset_algorithm")
    assert validate_persisted_construction(restored, bad).status == "blocked"
    historical = current.model_copy(
        update={
            "construction_policy": PortfolioConstructionPolicy(
                starter_shortlist_algorithm="sleeve-category-feasible-v2"
            )
        }
    )
    assert validate_persisted_construction(historical, expected).status == "blocked"


def test_objective_tie_order_constraints_and_zero_boundary(dataset: dict[str, Any]) -> None:
    current = inputs(dataset)
    eligible, _, error = _classify_candidates(current, current.construction_policy)
    assert error is None
    # All categories equal within sleeves: no hidden preference for more growth at exact tie.
    from dataclasses import replace

    pool = [
        replace(e, category="same growth" if e.sleeve == PortfolioSleeve.GROWTH else "same bond")
        for e in [*eligible[:6], *eligible[16:]]
    ]
    policy = current.construction_policy.model_copy(
        update={"max_positions": 5, "max_category_weight_bps": 10000}
    )
    chosen, _ = _select_subset(
        pool, {PortfolioSleeve.GROWTH: 5000, PortfolioSleeve.DEFENSIVE: 5000}, policy
    )
    assert chosen is not None
    assert len(chosen[0]) == 5  # Larger beats a four-position perfect ratio.
    assert sum(e.sleeve == PortfolioSleeve.GROWTH for e in chosen[0]) == 3  # source-order tie.
    # A distinct bonds-first original evidence order must win the same exact tie
    # with fewer growth positions: there is no hidden larger-growth preference.
    reordered = [replace(item, index=index) for index, item in enumerate([*pool[6:], *pool[:6]])]
    chosen2, _ = _select_subset(
        reordered, {PortfolioSleeve.GROWTH: 5000, PortfolioSleeve.DEFENSIVE: 5000}, policy
    )
    assert chosen2 is not None
    assert sum(e.sleeve == PortfolioSleeve.GROWTH for e in chosen2[0]) == 2
    policy = policy.model_copy(update={"min_position_weight_bps": 2500})
    chosen, _ = _select_subset(
        pool, {PortfolioSleeve.GROWTH: 5750, PortfolioSleeve.DEFENSIVE: 4250}, policy
    )
    assert chosen is not None
    assert len(chosen[0]) == 3
    chosen, _ = _select_subset(
        pool,
        {PortfolioSleeve.GROWTH: 0, PortfolioSleeve.DEFENSIVE: 10000},
        policy.model_copy(update={"min_position_weight_bps": 0}),
    )
    assert chosen is not None
    assert len(chosen[0]) == 5
    assert sum(w for e, w in zip(*chosen, strict=True) if e.sleeve == PortfolioSleeve.GROWTH) == 0


def test_category_priority_and_feasible_alternatives(dataset: dict[str, Any]) -> None:
    current = inputs(dataset)
    eligible, _, _ = _classify_candidates(current, current.construction_policy)
    by_symbol = {e.candidate.symbol: e for e in eligible}
    pool = [by_symbol[s] for s in ("SPY", "IVV", "VOO", "VTI", "BND", "AGG", "SCHZ")]
    policy = current.construction_policy
    targets = {PortfolioSleeve.GROWTH: 2000, PortfolioSleeve.DEFENSIVE: 8000}
    # One growth/four bonds is unavailable; next-best feasible count uses two/three,
    # even though three growth/two bonds would have greater category diversity.
    chosen, _ = _select_subset(pool, targets, policy)
    assert chosen is not None
    assert [e.candidate.symbol for e in chosen[0]] == ["SPY", "IVV", "BND", "AGG", "SCHZ"]
    # All bonds share a category: coverage is a tie-break, never a distinctness veto.
    assert len({e.category for e in chosen[0]}) == 3
    # The ideal split (two growth at this tied target) violates minimum weight;
    # one growth and four bonds remains feasible at maximum cardinality.
    pool = [by_symbol[s] for s in ("SPY", "IVV", "VOO", "VTI", "BND", "AGG", "SCHZ", "SPAB")]
    chosen, _ = _select_subset(
        pool,
        {PortfolioSleeve.GROWTH: 3000, PortfolioSleeve.DEFENSIVE: 7000},
        policy.model_copy(update={"min_position_weight_bps": 1600}),
    )
    assert chosen is not None
    assert len(chosen[0]) == 5
    assert sum(e.sleeve == PortfolioSleeve.GROWTH for e in chosen[0]) == 1


def test_new_root_retry_receipt_reuse_and_saved_version_children(dataset: dict[str, Any]) -> None:
    from datetime import UTC, datetime

    from langgraph.checkpoint.memory import InMemorySaver

    from etf_advisor.domain.revision import ReviewDecision, plan_revision
    from etf_advisor.graph.revision import validate_revision_state
    from etf_advisor.graph.workflow import build_graph
    from etf_advisor.rag.evidence import EvidenceRetrievalError

    current = inputs(dataset)

    class Retriever:
        calls = 0

        def retrieve(self, profile: Any, *, limit: int = 5) -> Any:
            self.calls += 1
            if self.calls == 1:
                raise EvidenceRetrievalError("Synthetic first-attempt failure")
            return current.candidate_evidence

    retriever, saver = Retriever(), InMemorySaver()
    config = {"configurable": {"thread_id": "issue153-retry"}}
    graph = build_graph(
        checkpointer=saver,
        candidate_retriever=retriever,
        candidate_limit=10,
        clock=lambda: datetime(2026, 11, 5, 13, tzinfo=UTC),
    )
    failed = graph.invoke({"profile": current.profile.model_dump(mode="json")}, config)
    revision = validate_revision_state(failed).revisions[-1]
    assert all(revision.inputs["construction_policy"][k] == v for k, v in MARKERS.items())
    prior = revision.receipts[-1]
    graph = build_graph(
        checkpointer=saver,
        candidate_retriever=retriever,
        candidate_limit=10,
        clock=lambda: datetime(2026, 11, 5, 13, tzinfo=UTC),
    )
    ready = graph.invoke(
        {
            "retry_request": {
                "action": "retry",
                "revision_id": prior.revision_id,
                "operation_id": prior.operation_id,
            }
        },
        config,
    )
    assert ready["status"] == "awaiting_human_review", ready.get("evidence_errors")
    assert retriever.calls == 2
    restored = graph.invoke(None, config)
    assert restored["portfolio_construction"] == ready["portfolio_construction"]
    assert retriever.calls == 2
    revision = validate_revision_state(ready).revisions[-1]
    for marker_policy in (
        MARKERS,
        {"starter_shortlist_algorithm": MARKERS["starter_shortlist_algorithm"]},
        {},
    ):
        saved = deepcopy(revision.inputs)
        saved["construction_policy"].pop("starter_shortlist_algorithm", None)
        saved["construction_policy"].pop("starter_subset_algorithm", None)
        saved["construction_policy"].update(marker_policy)
        assert (
            RevisionInputs.model_validate(saved).model_dump(mode="json")["construction_policy"]
            == saved["construction_policy"]
        )
        decision = ReviewDecision.model_validate(
            dict(
                decision_id="child153",
                revision_id=revision.revision_id,
                action="edit",
                disposition="revise",
                note="Inspect counts",
                submitted_at=datetime(2026, 11, 5, 13, tzinfo=UTC),
                feedback=[{"kind": "construction_policy", "patch": {"max_positions": 4}}],
            )
        )
        child = plan_revision(decision, saved)
        for marker in MARKERS:
            assert child.inputs["construction_policy"].get(marker) == marker_policy.get(marker)
