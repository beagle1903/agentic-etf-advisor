import json
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Literal

import pytest

from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import (
    CandidateScreeningPolicy,
    ScreeningContractError,
    ScreeningCriterion,
    ScreeningFieldFreshnessError,
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


@pytest.mark.parametrize(
    "field_name",
    [
        "market",
        "quote_type",
        "expense_ratio_pct",
        "average_daily_volume",
        "top_10_concentration_pct",
        "sector_exposures",
    ],
)
@pytest.mark.parametrize(
    ("offset", "expected_code"),
    [
        (-timedelta(hours=1), None),
        (-timedelta(hours=24), None),
        (-timedelta(hours=24, microseconds=1), "field_stale"),
        (timedelta(minutes=5), None),
        (timedelta(minutes=5, microseconds=1), "field_future"),
    ],
)
def test_consumed_field_freshness_uses_exact_persisted_boundaries(
    field_name: str,
    offset: timedelta,
    expected_code: str | None,
) -> None:
    evidence = _evidence(excluded_sectors=["tobacco"] if field_name == "sector_exposures" else None)
    observed_at = CHECKED_AT + offset
    _set_field_observed_at(evidence, field_name, observed_at)

    if expected_code is None:
        screening = screen_candidate_evidence(evidence)
        citation = next(
            rule.citation
            for rule in screening.candidates[0].rules
            if rule.citation is not None and rule.citation.field_name == field_name
        )
        assert citation.observed_at == observed_at
        return

    with pytest.raises(ScreeningFieldFreshnessError) as raised:
        screen_candidate_evidence(evidence)
    assert raised.value.code == expected_code
    assert raised.value.checked_at == CHECKED_AT
    assert raised.value.citation.document_id == "doc-spy"
    assert raised.value.citation.symbol == "SPY"
    assert raised.value.citation.field_name == field_name
    assert raised.value.citation.source_url == SOURCE_URL
    assert raised.value.citation.observed_at == observed_at


def test_field_freshness_accepts_timezone_equivalent_boundary() -> None:
    evidence = _evidence()
    observed_at = (CHECKED_AT - timedelta(hours=23)).astimezone(timezone(timedelta(hours=-7)))
    _set_field_observed_at(evidence, "expense_ratio_pct", observed_at)

    rule = screen_candidate_evidence(evidence).candidates[0].rules[3]

    assert rule.reason_code == ScreeningReason.EXPENSE_RATIO_WITHIN_LIMIT
    assert rule.citation is not None
    assert rule.citation.observed_at == CHECKED_AT - timedelta(hours=23)


def test_field_freshness_honors_zero_future_tolerance() -> None:
    evidence = _evidence(future_tolerance=timedelta(0))
    _set_field_observed_at(
        evidence,
        "average_daily_volume",
        CHECKED_AT + timedelta(microseconds=1),
    )

    with pytest.raises(ScreeningFieldFreshnessError) as raised:
        screen_candidate_evidence(evidence)

    assert raised.value.code == "field_future"
    assert raised.value.citation.field_name == "average_daily_volume"


def test_first_consumed_field_freshness_violation_blocks_in_stable_order() -> None:
    evidence = _evidence(expense_ratio_pct=2.0, missing_fields={"average_daily_volume"})
    _set_field_observed_at(
        evidence,
        "market",
        CHECKED_AT - timedelta(hours=24, microseconds=1),
    )
    _set_field_observed_at(
        evidence,
        "expense_ratio_pct",
        CHECKED_AT + timedelta(minutes=5, microseconds=1),
    )

    with pytest.raises(ScreeningFieldFreshnessError) as raised:
        screen_candidate_evidence(evidence)

    assert raised.value.code == "field_stale"
    assert raised.value.citation.field_name == "market"


def test_unavailable_field_age_does_not_override_unknown_result() -> None:
    evidence = _evidence(missing_fields={"expense_ratio_pct"})
    _set_field_observed_at(
        evidence,
        "expense_ratio_pct",
        CHECKED_AT - timedelta(days=30),
    )

    rule = screen_candidate_evidence(evidence).candidates[0].rules[3]

    assert rule.verdict == ScreeningVerdict.UNKNOWN
    assert rule.reason_code == ScreeningReason.EXPENSE_RATIO_UNKNOWN


def test_absent_canonical_identity_provenance_is_unknown_without_document_citation() -> None:
    evidence = _evidence()
    _remove_field_provenance(evidence, "market")
    _remove_field_provenance(evidence, "quote_type")

    candidate = screen_candidate_evidence(evidence).candidates[0]

    assert candidate.verdict == ScreeningVerdict.UNKNOWN
    assert candidate.rules[0].reason_code == ScreeningReason.US_LISTING_UNKNOWN
    assert candidate.rules[0].citation is None
    assert candidate.rules[1].reason_code == ScreeningReason.ETF_TYPE_UNKNOWN
    assert candidate.rules[1].citation is None


@pytest.mark.parametrize("field_name", ["market", "quote_type"])
def test_explicitly_missing_canonical_identity_remains_a_contract_error(field_name: str) -> None:
    evidence = _evidence(missing_fields={field_name})

    with pytest.raises(ScreeningContractError, match=f"{field_name} provenance conflicts"):
        screen_candidate_evidence(evidence)


def test_no_exclusions_ignore_unused_stale_sector_field() -> None:
    evidence = _evidence()
    _set_field_observed_at(
        evidence,
        "sector_exposures",
        CHECKED_AT - timedelta(days=30),
    )

    rule = screen_candidate_evidence(evidence).candidates[0].rules[-1]

    assert rule.reason_code == ScreeningReason.NO_SECTOR_EXCLUSIONS


def test_requested_unsupported_exclusion_enforces_available_sector_freshness() -> None:
    evidence = _evidence(excluded_sectors=["tobacco"])
    _set_field_observed_at(
        evidence,
        "sector_exposures",
        CHECKED_AT - timedelta(days=30),
    )

    with pytest.raises(ScreeningFieldFreshnessError) as raised:
        screen_candidate_evidence(evidence)

    assert raised.value.code == "field_stale"
    assert raised.value.citation.field_name == "sector_exposures"


@pytest.mark.parametrize("stale", [False, True], ids=["current", "stale"])
@pytest.mark.parametrize(
    "graph_status", [None, "source_error"], ids=["absent-graph", "unavailable-graph"]
)
def test_requested_exclusion_validates_available_sector_shape_before_freshness(
    stale: bool,
    graph_status: Literal["source_error"] | None,
) -> None:
    evidence = _evidence(excluded_sectors=["energy"])
    candidate = evidence.candidates[0]
    provenance = json.loads(candidate.metadata["field_provenance_json"])
    provenance["sector_exposures"]["value"] = [{"bad": 1}]
    if stale:
        provenance["sector_exposures"]["observed_at"] = (
            CHECKED_AT - timedelta(days=30)
        ).isoformat()
    candidate.metadata["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    candidate.graph_context = (
        None
        if graph_status is None
        else GraphContext(
            source_document_id="doc-spy",
            symbol="SPY",
            etf_name="SPDR S&P 500 ETF Trust",
            sector_exposures_status=graph_status,
            sector_exposures=[],
        )
    )
    evidence.snapshot_version = None
    evidence.snapshot_digest = None

    with pytest.raises(
        ScreeningContractError, match="sector exposure provenance is malformed"
    ) as raised:
        screen_candidate_evidence(evidence)

    assert not isinstance(raised.value, ScreeningFieldFreshnessError)


def test_average_daily_volume_uses_canonical_shares_per_day_unit() -> None:
    evidence = _evidence()

    liquidity_rule = screen_candidate_evidence(evidence).candidates[0].rules[4]

    assert liquidity_rule.verdict == ScreeningVerdict.PASS
    assert liquidity_rule.observed_value == 100_000
    assert liquidity_rule.threshold == "100000 shares/day"


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


def test_source_error_exposures_remain_unknown_after_real_evidence_selection() -> None:
    evidence = _evidence(
        excluded_sectors=["energy"],
        missing_fields={"top_10_concentration_pct", "sector_exposures"},
    )

    candidate = screen_candidate_evidence(evidence).candidates[0]
    concentration_rule = candidate.rules[5]
    sector_rule = candidate.rules[6]

    assert candidate.verdict == ScreeningVerdict.UNKNOWN
    assert concentration_rule.reason_code == ScreeningReason.CONCENTRATION_UNKNOWN
    assert concentration_rule.observed_value == MissingReason.SOURCE_ERROR
    assert concentration_rule.citation is not None
    assert concentration_rule.citation.source_url == SOURCE_URL
    assert sector_rule.reason_code == ScreeningReason.SECTOR_EXPOSURE_UNKNOWN
    assert sector_rule.observed_value == MissingReason.SOURCE_ERROR
    assert sector_rule.unresolved_exclusions == ["energy"]
    assert sector_rule.citation is not None
    assert sector_rule.citation.source_url == SOURCE_URL


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

    evidence.snapshot_version = None
    evidence.snapshot_digest = None
    with pytest.raises(ScreeningContractError, match="graph sector weights conflict"):
        screen_candidate_evidence(evidence)


def test_scalar_metadata_status_must_match_field_provenance() -> None:
    evidence = _evidence()
    evidence.candidates[0].metadata["expense_ratio_pct_status"] = "source_error"

    evidence.snapshot_version = None
    evidence.snapshot_digest = None
    with pytest.raises(ScreeningContractError, match="status conflicts"):
        screen_candidate_evidence(evidence)


def test_wrong_scalar_unit_blocks_screening_before_review() -> None:
    evidence = _evidence()
    provenance = json.loads(evidence.candidates[0].metadata["field_provenance_json"])
    provenance["expense_ratio_pct"]["unit"] = "fraction"
    evidence.candidates[0].metadata["field_provenance_json"] = json.dumps(provenance)

    evidence.snapshot_version = None
    evidence.snapshot_digest = None
    with pytest.raises(ScreeningContractError, match="must use percent units"):
        screen_candidate_evidence(evidence)


def test_scalar_contract_violation_precedes_field_freshness() -> None:
    evidence = _evidence()
    provenance = json.loads(evidence.candidates[0].metadata["field_provenance_json"])
    provenance["expense_ratio_pct"]["unit"] = "fraction"
    provenance["expense_ratio_pct"]["observed_at"] = (CHECKED_AT - timedelta(days=30)).isoformat()
    evidence.candidates[0].metadata["field_provenance_json"] = json.dumps(provenance)
    evidence.snapshot_version = None
    evidence.snapshot_digest = None

    with pytest.raises(ScreeningContractError, match="must use percent units") as raised:
        screen_candidate_evidence(evidence)

    assert not isinstance(raised.value, ScreeningFieldFreshnessError)


def test_sector_contract_violation_precedes_field_freshness() -> None:
    evidence = _evidence(excluded_sectors=["technology"], technology_weight_pct=25)
    evidence.candidates[0].graph_context = GraphContext(
        source_document_id="doc-spy",
        symbol="SPY",
        etf_name="SPDR S&P 500 ETF Trust",
        sector_exposures_status="available",
        sector_exposures=[SectorExposure(name="Technology", weight_pct=24)],
    )
    _set_field_observed_at(
        evidence,
        "sector_exposures",
        CHECKED_AT - timedelta(days=30),
    )

    with pytest.raises(ScreeningContractError, match="graph sector weights conflict") as raised:
        screen_candidate_evidence(evidence)

    assert not isinstance(raised.value, ScreeningFieldFreshnessError)


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
    future_tolerance: timedelta = timedelta(minutes=5),
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
        "average_daily_volume": "shares_per_day",
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
        future_tolerance=future_tolerance,
    )


def _set_field_observed_at(
    evidence: CandidateEvidenceBundle,
    field_name: str,
    observed_at: datetime,
) -> None:
    candidate = evidence.candidates[0]
    provenance = json.loads(candidate.metadata["field_provenance_json"])
    provenance[field_name]["observed_at"] = observed_at.isoformat()
    candidate.metadata["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    evidence.snapshot_version = None
    evidence.snapshot_digest = None


def _remove_field_provenance(evidence: CandidateEvidenceBundle, field_name: str) -> None:
    candidate = evidence.candidates[0]
    provenance = json.loads(candidate.metadata["field_provenance_json"])
    del provenance[field_name]
    candidate.metadata["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    candidate.metadata.pop(f"{field_name}_status")
    evidence.snapshot_version = None
    evidence.snapshot_digest = None
