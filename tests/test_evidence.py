import json
from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest
from pydantic import ValidationError

from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.rag.evidence import (
    CandidateEvidence,
    CandidateEvidenceBundle,
    EvidenceRetrievalError,
    EvidenceStatus,
    HybridCandidateEvidenceRetriever,
    build_candidate_query,
    select_candidate_evidence,
)
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, SectorExposure

CHECKED_AT = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def profile(
    *, objective: str = "balanced", excluded_sectors: list[str] | None = None
) -> InvestorProfile:
    return InvestorProfile(
        horizon_years=12,
        risk_tolerance="moderate",
        objective=objective,
        max_drawdown_pct=25,
        initial_investment_usd=25_000,
        recurring_monthly_usd=500,
        excluded_sectors=excluded_sectors or [],
    )


def source(
    symbol: str,
    *,
    observed_at: datetime = CHECKED_AT - timedelta(hours=1),
    distance: float = 0.1,
    graph_context: GraphContext | None = None,
    metadata_overrides: dict[str, str | int | float | bool] | None = None,
) -> GraphEnrichedSource:
    metadata: dict[str, str | int | float | bool] = {
        "symbol": symbol,
        "name": f"{symbol} test ETF",
        "source": "yahoo_finance",
        "source_url": f"https://finance.yahoo.com/quote/{symbol}/",
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "quote_type": "ETF",
        "market": "us_market",
        "category": "Large Blend",
        "fund_family": "Example Funds",
        "expense_ratio_pct": 0.03,
    }
    if metadata_overrides:
        metadata.update(metadata_overrides)
    return GraphEnrichedSource(
        document_id=f"doc-{symbol.lower()}-{observed_at.hour}",
        content=f"{symbol} source facts",
        metadata=metadata,
        distance=distance,
        graph_context=graph_context,
    )


def test_query_is_deterministic_and_carries_profile_constraints() -> None:
    query = build_candidate_query(profile(objective="growth", excluded_sectors=["energy"]))

    assert query == (
        "US-listed ETF research evidence for long-horizon growth objectives and moderate "
        "risk tolerance. Return attributable reported category, fund family, expense ratio, "
        "latest close, and source timestamps. Reported sector exposure must be checked against "
        "these exclusions: energy."
    )


def test_current_sources_become_ranked_json_safe_evidence() -> None:
    results = select_candidate_evidence(
        profile(excluded_sectors=["energy"]),
        [
            source(
                "SPY",
                graph_context=GraphContext(
                    source_document_id="doc-spy-11",
                    symbol="SPY",
                    etf_name="SPDR S&P 500 ETF Trust",
                    fund_family="State Street Global Advisors",
                    category="Large Blend",
                ),
            ),
            source("BND", distance=0.2),
        ],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
        limit=2,
    )

    assert results.status == EvidenceStatus.READY
    assert [candidate.symbol for candidate in results.candidates] == ["SPY", "BND"]
    assert results.candidates[0].source_url.endswith("/SPY/")
    assert results.candidates[0].graph_context is not None
    assert results.candidates[0].graph_context.fund_family == "State Street Global Advisors"
    assert results.health.healthy is True
    assert any("sector exclusions" in warning.lower() for warning in results.warnings)
    json.dumps(results.model_dump(mode="json"))


def test_stale_source_blocks_review_evidence_and_retains_health_details() -> None:
    results = select_candidate_evidence(
        profile(),
        [source("SPY", observed_at=CHECKED_AT - timedelta(hours=25))],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.BLOCKED
    assert results.candidates == []
    assert results.health.healthy is False
    assert results.health.observations[0].status == "stale"
    assert results.health.observations[0].source_url.endswith("/SPY/")
    assert any("every observation is current" in error for error in results.errors)


def test_available_sector_context_is_preserved_for_deterministic_validation() -> None:
    context = GraphContext(
        source_document_id="doc-spy-11",
        symbol="SPY",
        etf_name="SPDR S&P 500 ETF Trust",
        sector_exposures_status="available",
        sector_exposures=[SectorExposure(name="technology", weight_pct=37.4)],
    )

    results = select_candidate_evidence(
        profile(excluded_sectors=["technology"]),
        [source("SPY", graph_context=context)],
        query="technology exclusion evidence",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.READY
    assert results.candidates[0].graph_context == context
    assert any(
        "attached for deterministic sector exclusions validation" in warning
        for warning in results.warnings
    )


def test_future_source_blocks_review_evidence() -> None:
    results = select_candidate_evidence(
        profile(),
        [source("QQQ", observed_at=CHECKED_AT + timedelta(minutes=6))],
        query="technology exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
        future_tolerance=timedelta(minutes=5),
    )

    assert results.status == EvidenceStatus.BLOCKED
    assert results.candidates == []
    assert results.health.observations[0].status == "future"


def test_missing_provenance_blocks_without_fabricating_source_details() -> None:
    results = select_candidate_evidence(
        profile(),
        [source("QQQ", metadata_overrides={"source_url": ""})],
        query="technology exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.BLOCKED
    assert results.candidates == []
    assert results.health.observations == []
    assert "doc-qqq-11" in results.errors[0]
    assert "source_url" in results.errors[0]


def test_malformed_source_url_blocks_review_evidence() -> None:
    results = select_candidate_evidence(
        profile(),
        [source("QQQ", metadata_overrides={"source_url": "not-a-url"})],
        query="technology exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.BLOCKED
    assert results.candidates == []
    assert results.health.observations == []
    assert "HTTP(S)" in results.errors[0]


def test_non_etf_source_blocks_review_evidence() -> None:
    results = select_candidate_evidence(
        profile(),
        [source("AAPL", metadata_overrides={"quote_type": "EQUITY"})],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.BLOCKED
    assert results.candidates == []
    assert "quote_type" in results.errors[0]


def test_non_us_listing_blocks_review_evidence() -> None:
    results = select_candidate_evidence(
        profile(),
        [source("EUNL.DE", metadata_overrides={"market": "de_market"})],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.BLOCKED
    assert results.candidates == []
    assert "market" in results.errors[0]


def test_invalid_source_content_blocks_without_crashing_the_workflow() -> None:
    sensitive_marker = "private-source-marker"
    invalid = source("SPY").model_copy(update={"content": sensitive_marker + ("x" * 12_000)})

    results = select_candidate_evidence(
        profile(),
        [invalid],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.BLOCKED
    assert results.candidates == []
    assert "evidence fields are invalid" in results.errors[0]
    assert sensitive_marker not in results.errors[0]


def test_mismatched_graph_context_is_omitted_without_fabricating_a_join() -> None:
    results = select_candidate_evidence(
        profile(),
        [
            source(
                "VTI",
                graph_context=GraphContext(
                    source_document_id="different-document",
                    symbol="QQQ",
                    etf_name="Wrong ETF context",
                ),
            )
        ],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.READY
    assert results.candidates[0].graph_context is None
    assert any("does not match" in warning for warning in results.warnings)


@pytest.mark.parametrize(
    ("context_update", "error_match"),
    [
        ({"source_document_id": "doc-qqq-11"}, "source document ID"),
        ({"symbol": "QQQ"}, "source symbol"),
    ],
)
def test_candidate_evidence_rejects_mismatched_persisted_graph_identity(
    context_update: dict[str, str],
    error_match: str,
) -> None:
    matching_context = GraphContext(
        source_document_id="doc-spy-11",
        symbol="SPY",
        etf_name="SPDR S&P 500 ETF Trust",
        sector_exposures_status="available",
        sector_exposures=[SectorExposure(name="technology", weight_pct=37.4)],
    )
    candidate = select_candidate_evidence(
        profile(),
        [source("SPY", graph_context=matching_context)],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    ).candidates[0]
    payload = candidate.model_dump(mode="python")
    payload["graph_context"].update(context_update)

    with pytest.raises(ValidationError, match=error_match):
        CandidateEvidence.model_validate(payload)


def test_empty_retrieval_blocks_with_an_explicit_error() -> None:
    results = select_candidate_evidence(
        profile(),
        [],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    assert results.status == EvidenceStatus.BLOCKED
    assert results.candidates == []
    assert results.health.healthy is False
    assert any("No source evidence" in error for error in results.errors)


def test_duplicate_symbols_keep_first_semantic_result() -> None:
    results = select_candidate_evidence(
        profile(),
        [source("VTI", distance=0.1), source("VTI", distance=0.2)],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
        limit=2,
    )

    assert results.status == EvidenceStatus.READY
    assert len(results.candidates) == 1
    assert results.candidates[0].distance == 0.1
    assert any("Duplicate source result" in warning for warning in results.warnings)


class FakeHybridSearch:
    results: ClassVar[list[GraphEnrichedSource]] = [source("SPY")]

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, limit: int = 5) -> list[GraphEnrichedSource]:
        self.calls.append((query, limit))
        return self.results


def test_hybrid_evidence_adapter_injects_clock_and_preserves_query() -> None:
    search = FakeHybridSearch()
    clock_calls = 0

    def clock() -> datetime:
        nonlocal clock_calls
        clock_calls += 1
        return CHECKED_AT

    adapter = HybridCandidateEvidenceRetriever(
        search,
        clock=clock,
        max_age=timedelta(hours=24),
    )
    result = adapter.retrieve(profile(objective="income"), limit=3)

    assert result.status == EvidenceStatus.READY
    assert result.candidates[0].symbol == "SPY"
    assert search.calls == [(build_candidate_query(profile(objective="income")), 3)]
    assert clock_calls == 1


def test_hybrid_evidence_adapter_translates_store_failures() -> None:
    class FailingSearch:
        def search(self, query: str, limit: int = 5) -> list[GraphEnrichedSource]:
            raise OSError("store unavailable")

    adapter = HybridCandidateEvidenceRetriever(
        FailingSearch(),
        clock=lambda: CHECKED_AT,
        max_age=timedelta(hours=24),
    )

    with pytest.raises(EvidenceRetrievalError, match="Source evidence retrieval failed"):
        adapter.retrieve(profile())


def test_hybrid_evidence_adapter_translates_clock_failures() -> None:
    def failing_clock() -> datetime:
        raise OSError("clock unavailable")

    adapter = HybridCandidateEvidenceRetriever(
        FakeHybridSearch(),
        clock=failing_clock,
        max_age=timedelta(hours=24),
    )

    with pytest.raises(EvidenceRetrievalError, match="Source evidence validation failed"):
        adapter.retrieve(profile())


def test_ready_bundle_requires_matching_healthy_observations() -> None:
    ready = select_candidate_evidence(
        profile(),
        [source("SPY")],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )
    unhealthy_payload = ready.model_dump(mode="python")
    unhealthy_payload["health"]["healthy"] = False

    with pytest.raises(ValidationError, match="recomputed freshness"):
        CandidateEvidenceBundle.model_validate(unhealthy_payload)

    mismatched_time_payload = ready.model_dump(mode="python")
    mismatched_time_payload["health"]["checked_at"] = CHECKED_AT - timedelta(minutes=1)

    with pytest.raises(ValidationError, match="same timestamp"):
        CandidateEvidenceBundle.model_validate(mismatched_time_payload)

    unexplained_block_payload = ready.model_dump(mode="python")
    unexplained_block_payload["status"] = "blocked"

    with pytest.raises(ValidationError, match="at least one error"):
        CandidateEvidenceBundle.model_validate(unexplained_block_payload)


def test_ready_bundle_recomputes_freshness_instead_of_trusting_status_labels() -> None:
    ready = select_candidate_evidence(
        profile(),
        [source("SPY")],
        query="broad US exposure",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )
    forged_payload = ready.model_dump(mode="python")
    stale_time = CHECKED_AT - timedelta(hours=48)
    forged_payload["candidates"][0]["observed_at"] = stale_time
    forged_payload["health"]["observations"][0]["observed_at"] = stale_time

    with pytest.raises(ValidationError, match="recomputed freshness"):
        CandidateEvidenceBundle.model_validate(forged_payload)
