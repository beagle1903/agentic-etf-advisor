import json
from datetime import UTC, datetime, timedelta
from typing import Any

from etf_advisor.domain.construction import (
    ConstructionCheckName,
    ConstructionReason,
    PortfolioConstructionInput,
    PortfolioConstructionPolicy,
    construct_model_portfolio,
    validate_persisted_construction,
    validate_portfolio_draft,
)
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.rag.evidence import CandidateEvidenceBundle, select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.models import ResearchField

OBSERVED_AT = datetime(2026, 9, 1, 20, tzinfo=UTC)
CHECKED_AT = datetime(2026, 9, 2, 8, tzinfo=UTC)
CANDIDATES = [
    ("SPY", "Large Blend"),
    ("VTI", "Large Blend"),
    ("QQQ", "Large Growth"),
    ("VEA", "Foreign Large Blend"),
    ("BND", "Intermediate Core Bond"),
]


def test_balanced_portfolio_matches_accepted_weight_and_cash_fixture() -> None:
    inputs = _construction_input(_profile())

    first = construct_model_portfolio(inputs)
    second = construct_model_portfolio(inputs)

    assert first.status == "ready"
    assert first == second
    assert json.dumps(first.model_dump(mode="json"), sort_keys=True) == json.dumps(
        second.model_dump(mode="json"), sort_keys=True
    )
    assert first.draft is not None
    assert [position.symbol for position in first.draft.positions] == [
        "SPY",
        "VTI",
        "QQQ",
        "VEA",
        "BND",
    ]
    assert [position.weight_bps for position in first.draft.positions] == [
        1_438,
        1_438,
        1_437,
        1_437,
        4_250,
    ]
    assert [position.initial_usd_cents for position in first.draft.positions] == [
        14_380,
        14_380,
        14_370,
        14_370,
        42_500,
    ]
    assert [position.recurring_usd_cents for position in first.draft.positions] == [
        3_595,
        3_595,
        3_593,
        3_592,
        10_625,
    ]
    assert first.draft.total_weight_bps == 10_000
    assert first.draft.initial_total_cents == 100_000
    assert first.draft.recurring_total_cents == 25_000
    assert all(check.passed for check in first.validation.checks)
    assert first.draft.positions[0].source_category == "Large Blend"
    assert first.draft.positions[0].source_url.endswith("/SPY/")
    assert first.draft.positions[0].policy_reference == (
        "policy.target_allocation.growth_assets_pct"
    )


def test_conservative_profile_passes_exact_position_and_category_boundaries() -> None:
    profile = _profile(risk_tolerance="conservative", objective="income")

    result = construct_model_portfolio(_construction_input(profile))

    assert result.status == "ready"
    assert result.draft is not None
    assert [position.weight_bps for position in result.draft.positions] == [
        500,
        500,
        500,
        500,
        8_000,
    ]
    assert result.draft.sleeve_weight_bps == {"growth": 2_000, "defensive": 8_000}


def test_aggressive_two_candidate_input_blocks_before_assigning_weights() -> None:
    profile = _profile(risk_tolerance="aggressive", objective="growth")
    inputs = _construction_input(profile, candidates=CANDIDATES[2::2])

    result = construct_model_portfolio(inputs)

    assert result.status == "blocked"
    assert result.draft is None
    assert result.errors[0].code == ConstructionReason.INSUFFICIENT_ELIGIBLE_CANDIDATES


def test_missing_nonzero_sleeve_coverage_blocks_subset_search() -> None:
    inputs = _construction_input(_profile(), candidates=CANDIDATES[:4])

    result = construct_model_portfolio(inputs)

    assert result.status == "blocked"
    assert result.errors[0].code == ConstructionReason.MISSING_SLEEVE_COVERAGE


def test_position_maximum_can_make_all_sleeve_covered_subsets_infeasible() -> None:
    inputs = _construction_input(
        _profile(),
        construction_policy=PortfolioConstructionPolicy(max_position_weight_bps=4_000),
    )

    result = construct_model_portfolio(inputs)

    assert result.status == "blocked"
    assert result.errors[0].code == ConstructionReason.POSITION_CONSTRAINTS_INFEASIBLE


def test_unsupported_category_is_audited_but_does_not_block_feasible_subset() -> None:
    inputs = _construction_input(
        _profile(),
        candidates=[*CANDIDATES, ("GLD", "Commodities Focused")],
    )

    result = construct_model_portfolio(inputs)

    assert result.status == "ready"
    assert [(item.symbol, item.reason_code) for item in result.excluded_candidates] == [
        ("GLD", ConstructionReason.CATEGORY_UNSUPPORTED)
    ]


def test_failed_screening_candidate_is_audited_and_never_weighted() -> None:
    inputs = _construction_input(_profile())
    candidate = inputs.candidate_evidence.candidates[0]
    provenance = json.loads(candidate.metadata["field_provenance_json"])
    provenance["expense_ratio_pct"]["value"] = 2.0
    candidate.metadata["expense_ratio_pct"] = 2.0
    candidate.metadata["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    inputs.candidate_screening = screen_candidate_evidence(inputs.candidate_evidence)

    result = construct_model_portfolio(inputs)

    assert result.status == "ready"
    assert result.draft is not None
    assert "SPY" not in {position.symbol for position in result.draft.positions}
    excluded = result.excluded_candidates[0]
    assert excluded.reason_code == ConstructionReason.CANDIDATE_SCREENING_FAILED
    assert excluded.screening_reason_codes == ["expense_ratio_above_limit"]


def test_missing_category_is_audited_without_guessing_a_sleeve() -> None:
    inputs = _construction_input(_profile())
    candidate = inputs.candidate_evidence.candidates[0]
    provenance = json.loads(candidate.metadata["field_provenance_json"])
    provenance.pop("category")
    candidate.metadata.pop("category")
    candidate.metadata.pop("category_status")
    candidate.metadata["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    candidate.category = None
    inputs.candidate_screening = screen_candidate_evidence(inputs.candidate_evidence)

    result = construct_model_portfolio(inputs)

    assert result.status == "ready"
    assert result.draft is not None
    assert "SPY" not in {position.symbol for position in result.draft.positions}
    assert result.excluded_candidates[0].reason_code == ConstructionReason.CATEGORY_MISSING


def test_category_provenance_conflict_blocks_complete_construction() -> None:
    inputs = _construction_input(_profile())
    inputs.candidate_evidence.candidates[0].category = "Large Growth"

    result = construct_model_portfolio(inputs)

    assert result.status == "blocked"
    assert result.errors[0].code == ConstructionReason.CATEGORY_PROVENANCE_CONFLICT
    assert result.draft is None


def test_screening_recomputation_mismatch_blocks_complete_construction() -> None:
    inputs = _construction_input(_profile())
    inputs.candidate_screening = inputs.candidate_screening.model_copy(update={"candidates": []})

    result = construct_model_portfolio(inputs)

    assert result.status == "blocked"
    assert result.errors[0].code == ConstructionReason.SCREENING_RECOMPUTATION_MISMATCH


def test_configured_position_bound_is_authoritative() -> None:
    inputs = _construction_input(
        _profile(),
        construction_policy=PortfolioConstructionPolicy(
            min_positions=3,
            max_positions=4,
            min_position_weight_bps=500,
            max_position_weight_bps=8_000,
            max_category_weight_bps=8_000,
        ),
    )

    result = construct_model_portfolio(inputs)

    assert result.status == "ready"
    assert result.draft is not None
    assert [position.symbol for position in result.draft.positions] == ["SPY", "VTI", "QQQ", "BND"]
    assert [position.weight_bps for position in result.draft.positions] == [
        1_917,
        1_917,
        1_916,
        4_250,
    ]


def test_configured_category_limit_can_make_every_subset_infeasible() -> None:
    inputs = _construction_input(
        _profile(),
        construction_policy=PortfolioConstructionPolicy(max_category_weight_bps=4_249),
    )

    result = construct_model_portfolio(inputs)

    assert result.status == "blocked"
    assert result.errors[0].code == ConstructionReason.CATEGORY_LIMIT_INFEASIBLE


def test_unsupported_weight_precision_blocks_without_rounding() -> None:
    inputs = _construction_input(
        _profile(),
        construction_policy=PortfolioConstructionPolicy(weight_precision_bps=5),
    )

    result = construct_model_portfolio(inputs)

    assert result.status == "blocked"
    assert result.errors[0].code == ConstructionReason.ALLOCATION_PRECISION_UNSUPPORTED


def test_independent_validator_rejects_tampered_weight_and_cash() -> None:
    inputs = _construction_input(_profile())
    result = construct_model_portfolio(inputs)
    assert result.draft is not None
    first = result.draft.positions[0].model_copy(
        update={"weight_bps": 1_439, "initial_usd_cents": 14_381}
    )
    tampered = result.draft.model_copy(update={"positions": [first, *result.draft.positions[1:]]})

    validation = validate_portfolio_draft(inputs, tampered)

    failed = {check.name for check in validation.checks if not check.passed}
    assert ConstructionCheckName.WEIGHT_TOTAL in failed
    assert ConstructionCheckName.SLEEVE_TOTALS in failed
    assert ConstructionCheckName.INITIAL_CASH in failed


def test_persisted_bundle_must_equal_deterministic_recomputation() -> None:
    inputs = _construction_input(_profile())
    result = construct_model_portfolio(inputs)
    assert result.draft is not None
    tampered_position = result.draft.positions[0].model_copy(update={"name": "Tampered"})
    tampered_draft = result.draft.model_copy(
        update={"positions": [tampered_position, *result.draft.positions[1:]]}
    )
    persisted = result.model_copy(update={"draft": tampered_draft})

    checked = validate_persisted_construction(inputs, persisted)

    assert checked.status == "blocked"
    assert checked.draft is None
    assert checked.errors[0].code == ConstructionReason.PERSISTED_CONSTRUCTION_MISMATCH
    persisted_check = next(
        check
        for check in checked.validation.checks
        if check.name == ConstructionCheckName.PERSISTED_RECOMPUTATION
    )
    assert not persisted_check.passed


def test_nonzero_weights_may_receive_zero_cents_without_losing_cash() -> None:
    profile = _profile()
    profile.initial_investment_usd = 0.01
    profile.recurring_monthly_usd = 0

    result = construct_model_portfolio(_construction_input(profile))

    assert result.status == "ready"
    assert result.draft is not None
    assert sum(position.initial_usd_cents for position in result.draft.positions) == 1
    assert sum(position.recurring_usd_cents for position in result.draft.positions) == 0
    assert any(position.initial_usd_cents == 0 for position in result.draft.positions)


def _profile(
    *,
    risk_tolerance: str = "moderate",
    objective: str = "balanced",
) -> InvestorProfile:
    return InvestorProfile(
        horizon_years=15,
        risk_tolerance=risk_tolerance,
        objective=objective,
        max_drawdown_pct=30,
        initial_investment_usd=1_000,
        recurring_monthly_usd=250,
        excluded_sectors=[],
    )


def _construction_input(
    profile: InvestorProfile,
    *,
    candidates: list[tuple[str, str]] | None = None,
    construction_policy: PortfolioConstructionPolicy | None = None,
) -> PortfolioConstructionInput:
    evidence = _evidence(profile, candidates or CANDIDATES)
    return PortfolioConstructionInput(
        profile=profile,
        policy_calculation=calculate_policy(profile),
        candidate_evidence=evidence,
        candidate_screening=screen_candidate_evidence(evidence),
        construction_policy=construction_policy or PortfolioConstructionPolicy(),
    )


def _evidence(
    profile: InvestorProfile,
    candidates: list[tuple[str, str]],
) -> CandidateEvidenceBundle:
    return select_candidate_evidence(
        profile,
        [_source(symbol, category) for symbol, category in candidates],
        query="deterministic construction test evidence",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
        limit=len(candidates),
    )


def _source(symbol: str, category: str) -> GraphEnrichedSource:
    source_url = f"https://finance.yahoo.com/quote/{symbol}/"
    values: dict[str, Any] = {
        "market": "us_market",
        "quote_type": "ETF",
        "category": category,
        "expense_ratio_pct": 0.1,
        "average_daily_volume": 1_000_000,
        "top_10_concentration_pct": 40.0,
    }
    units = {
        "market": "classification",
        "quote_type": "classification",
        "category": "classification",
        "expense_ratio_pct": "percent",
        "average_daily_volume": "shares_per_day",
        "top_10_concentration_pct": "percent",
    }
    provenance: dict[str, dict[str, Any]] = {}
    metadata: dict[str, str | int | float | bool] = {
        "symbol": symbol,
        "name": f"{symbol} ETF",
        "source": "yahoo_finance",
        "source_url": source_url,
        "observed_at": OBSERVED_AT.isoformat(),
    }
    for field_name, value in values.items():
        field = ResearchField[Any](
            value=value,
            unit=units[field_name],
            provider="yahoo_finance",
            source_url=source_url,
            observed_at=OBSERVED_AT,
            ingested_at=CHECKED_AT,
            snapshot_version="construction-test-v1",
        )
        provenance[field_name] = field.model_dump(mode="json")
        metadata[field_name] = value
        metadata[f"{field_name}_status"] = "available"
    metadata["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    return GraphEnrichedSource(
        document_id=f"doc-{symbol.lower()}",
        content=f"Versioned {symbol} research facts.",
        metadata=metadata,
    )
