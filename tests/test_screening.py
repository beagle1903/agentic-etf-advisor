import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import (
    CandidateScreeningPolicy,
    ScreeningContractError,
    ScreeningCriterion,
    ScreeningReason,
    ScreeningVerdict,
    screen_candidate_evidence,
)
from etf_advisor.rag.evidence import CandidateEvidenceBundle, select_candidate_evidence
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, SectorExposure
from etf_advisor.research.models import MissingReason, ResearchField, WeightedExposure

OBSERVED_AT = datetime(2026, 8, 30, 20, tzinfo=UTC)
CHECKED_AT = datetime(2026, 8, 31, 8, tzinfo=UTC)
SOURCE_URL = "https://finance.yahoo.com/quote/SPY/"


def test_boundary_values_pass_with_stable_reason_codes_and_citations() -> None:
    evidence = _evidence(excluded_sectors=["Information Technology"])

    bundle = screen_candidate_evidence(evidence)

    assert bundle.status == "ready"
    assert bundle.checked_at == CHECKED_AT
    assert len(bundle.candidates) == 1
    candidate = bundle.candidates[0]
    assert candidate.verdict == ScreeningVerdict.PASS
    assert [rule.criterion for rule in candidate.rules] == list(ScreeningCriterion)
    assert [rule.reason_code for rule in candidate.rules] == [
        ScreeningReason.US_LISTING_CONFIRMED,
        ScreeningReason.ETF_TYPE_CONFIRMED,
        ScreeningReason.SOURCE_CURRENT,
        ScreeningReason.EXPENSE_RATIO_WITHIN_LIMIT,
        ScreeningReason.VOLUME_MEETS_MINIMUM,
        ScreeningReason.CONCENTRATION_WITHIN_LIMIT,
        ScreeningReason.SECTOR_EXCLUSIONS_CLEAR,
    ]
    expense_rule = candidate.rules[3]
    assert expense_rule.observed_value == 1.0
    assert expense_rule.threshold == "1 %"
    assert expense_rule.citation is not None
    assert expense_rule.citation.field_name == "expense_ratio_pct"
    assert expense_rule.citation.source_url == SOURCE_URL
    json.dumps(bundle.model_dump(mode="json"))


def test_conflicting_constraints_fail_without_model_ranking() -> None:
    evidence = _evidence(
        excluded_sectors=["technology"],
        expense_ratio_pct=1.01,
        average_daily_volume=99_999,
        top_10_concentration_pct=60.01,
        technology_weight_pct=25,
    )

    candidate = screen_candidate_evidence(evidence).candidates[0]

    assert candidate.verdict == ScreeningVerdict.FAIL
    failures = {rule.reason_code for rule in candidate.rules if rule.verdict == "fail"}
    assert failures == {
        ScreeningReason.EXPENSE_RATIO_ABOVE_LIMIT,
        ScreeningReason.VOLUME_BELOW_MINIMUM,
        ScreeningReason.CONCENTRATION_ABOVE_LIMIT,
        ScreeningReason.EXCLUDED_SECTOR_DETECTED,
    }


@pytest.mark.parametrize(
    ("field_name", "criterion", "reason"),
    [
        (
            "expense_ratio_pct",
            ScreeningCriterion.EXPENSE_RATIO,
            ScreeningReason.EXPENSE_RATIO_UNKNOWN,
        ),
        (
            "average_daily_volume",
            ScreeningCriterion.LIQUIDITY,
            ScreeningReason.VOLUME_UNKNOWN,
        ),
        (
            "top_10_concentration_pct",
            ScreeningCriterion.CONCENTRATION,
            ScreeningReason.CONCENTRATION_UNKNOWN,
        ),
    ],
)
def test_missing_scalar_evidence_is_unknown_not_pass(
    field_name: str,
    criterion: ScreeningCriterion,
    reason: ScreeningReason,
) -> None:
    evidence = _evidence(missing_fields={field_name})

    candidate = screen_candidate_evidence(evidence).candidates[0]
    rule = next(item for item in candidate.rules if item.criterion == criterion)

    assert candidate.verdict == ScreeningVerdict.UNKNOWN
    assert rule.verdict == ScreeningVerdict.UNKNOWN
    assert rule.reason_code == reason
    assert rule.observed_value == MissingReason.SOURCE_ERROR


def test_unsupported_industry_exclusion_is_unknown_not_a_false_sector_pass() -> None:
    evidence = _evidence(excluded_sectors=["tobacco"])

    rule = screen_candidate_evidence(evidence).candidates[0].rules[-1]

    assert rule.verdict == ScreeningVerdict.UNKNOWN
    assert rule.reason_code == ScreeningReason.UNSUPPORTED_SECTOR_EXCLUSION
    assert rule.observed_value == "tobacco"
    assert rule.unresolved_exclusions == ["tobacco"]


def test_supported_exclusion_failure_precedes_unknown_unsupported_term() -> None:
    evidence = _evidence(
        excluded_sectors=["tobacco", "technology"],
        technology_weight_pct=25,
    )

    rule = screen_candidate_evidence(evidence).candidates[0].rules[-1]

    assert rule.verdict == ScreeningVerdict.FAIL
    assert rule.reason_code == ScreeningReason.EXCLUDED_SECTOR_DETECTED
    assert rule.observed_value == "technology=25%"
    assert rule.unresolved_exclusions == ["tobacco"]
    assert "remain unresolved" in rule.message


def test_missing_sector_evidence_is_unknown() -> None:
    evidence = _evidence(excluded_sectors=["energy"], missing_fields={"sector_exposures"})

    rule = screen_candidate_evidence(evidence).candidates[0].rules[-1]

    assert rule.verdict == ScreeningVerdict.UNKNOWN
    assert rule.reason_code == ScreeningReason.SECTOR_EXPOSURE_UNKNOWN
    assert rule.unresolved_exclusions == ["energy"]


def test_configurable_policy_changes_only_deterministic_threshold_judgments() -> None:
    evidence = _evidence(expense_ratio_pct=1.5)
    policy = CandidateScreeningPolicy(max_expense_ratio_pct=2.0)

    candidate = screen_candidate_evidence(evidence, policy).candidates[0]

    assert candidate.verdict == ScreeningVerdict.PASS
    assert candidate.rules[3].reason_code == ScreeningReason.EXPENSE_RATIO_WITHIN_LIMIT


def test_graph_sector_weight_must_match_canonical_field_provenance() -> None:
    evidence = _evidence(excluded_sectors=["technology"], technology_weight_pct=25)
    evidence.candidates[0].graph_context = GraphContext(
        source_document_id="doc-spy",
        symbol="SPY",
        etf_name="SPDR S&P 500 ETF Trust",
        sector_exposures_status="available",
        sector_exposures=[SectorExposure(name="Technology", weight_pct=24)],
    )

    with pytest.raises(ScreeningContractError, match="graph sector weights conflict"):
        screen_candidate_evidence(evidence)


def test_scalar_metadata_status_must_match_field_provenance() -> None:
    evidence = _evidence()
    evidence.candidates[0].metadata["expense_ratio_pct_status"] = "source_error"

    with pytest.raises(ScreeningContractError, match="status conflicts"):
        screen_candidate_evidence(evidence)


def test_wrong_scalar_unit_blocks_screening_before_review() -> None:
    evidence = _evidence()
    provenance = json.loads(evidence.candidates[0].metadata["field_provenance_json"])
    provenance["expense_ratio_pct"]["unit"] = "fraction"
    evidence.candidates[0].metadata["field_provenance_json"] = json.dumps(provenance)

    with pytest.raises(ScreeningContractError, match="must use percent units"):
        screen_candidate_evidence(evidence)


def test_out_of_range_percentage_blocks_screening_before_review() -> None:
    evidence = _evidence(expense_ratio_pct=101)

    with pytest.raises(ScreeningContractError, match="cannot exceed 100"):
        screen_candidate_evidence(evidence)


def _evidence(
    *,
    excluded_sectors: list[str] | None = None,
    missing_fields: set[str] | None = None,
    expense_ratio_pct: float = 1.0,
    average_daily_volume: float = 100_000,
    top_10_concentration_pct: float = 60.0,
    technology_weight_pct: float = 0.0,
) -> CandidateEvidenceBundle:
    missing = missing_fields or set()
    values: dict[str, Any] = {
        "market": "us_market",
        "quote_type": "ETF",
        "expense_ratio_pct": expense_ratio_pct,
        "average_daily_volume": average_daily_volume,
        "top_10_concentration_pct": top_10_concentration_pct,
        "sector_exposures": [
            WeightedExposure(name="Technology", weight_pct=technology_weight_pct),
            WeightedExposure(name="Energy", weight_pct=10),
        ],
    }
    units = {
        "market": "classification",
        "quote_type": "classification",
        "expense_ratio_pct": "percent",
        "average_daily_volume": "shares",
        "top_10_concentration_pct": "percent",
        "sector_exposures": "percent",
    }
    provenance: dict[str, dict[str, Any]] = {}
    metadata: dict[str, str | int | float | bool] = {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "source": "yahoo_finance",
        "source_url": SOURCE_URL,
        "observed_at": OBSERVED_AT.isoformat(),
        "quote_type": "ETF",
        "market": "us_market",
    }
    for field_name, value in values.items():
        field = ResearchField[Any](
            value=None if field_name in missing else value,
            unit=units[field_name],
            provider="yahoo_finance",
            source_url=SOURCE_URL,
            observed_at=OBSERVED_AT,
            ingested_at=CHECKED_AT,
            snapshot_version="screening-test-v1",
            missing_reason=(MissingReason.SOURCE_ERROR if field_name in missing else None),
        )
        provenance[field_name] = field.model_dump(mode="json")
        metadata[f"{field_name}_status"] = (
            field.missing_reason.value if field.missing_reason is not None else "available"
        )
        if field.missing_reason is None and isinstance(value, (str, int, float, bool)):
            metadata[field_name] = value
    metadata["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    sector_missing = "sector_exposures" in missing
    result = GraphEnrichedSource(
        document_id="doc-spy",
        content="Versioned SPY research facts.",
        metadata=metadata,
        graph_context=GraphContext(
            source_document_id="doc-spy",
            symbol="SPY",
            etf_name="SPDR S&P 500 ETF Trust",
            sector_exposures_status="source_error" if sector_missing else "available",
            sector_exposures=(
                []
                if sector_missing
                else [
                    SectorExposure(name="Technology", weight_pct=technology_weight_pct),
                    SectorExposure(name="Energy", weight_pct=10),
                ]
            ),
        ),
    )
    profile = InvestorProfile(
        horizon_years=15,
        risk_tolerance="moderate",
        objective="growth",
        max_drawdown_pct=30,
        initial_investment_usd=50_000,
        recurring_monthly_usd=1_000,
        excluded_sectors=excluded_sectors or [],
    )
    return select_candidate_evidence(
        profile,
        [result],
        query="screening test evidence",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
    )
