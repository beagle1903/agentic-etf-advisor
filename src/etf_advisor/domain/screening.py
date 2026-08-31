"""Pure, source-attributable ETF candidate screening."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Final, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from etf_advisor.data.quality import FreshnessStatus, ObservationHealth
from etf_advisor.rag.evidence import CandidateEvidence, CandidateEvidenceBundle, EvidenceStatus
from etf_advisor.research.models import ResearchField, WeightedExposure


class ScreeningContractError(ValueError):
    """Raised when candidate evidence cannot be screened without changing its meaning."""


class ScreeningVerdict(StrEnum):
    """Three-valued result used for rules and whole candidates."""

    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class ScreeningCriterion(StrEnum):
    """Stable deterministic rules applied to every candidate."""

    US_LISTING = "us_listing"
    INSTRUMENT_TYPE = "instrument_type"
    FRESHNESS = "freshness"
    EXPENSE_RATIO = "expense_ratio"
    LIQUIDITY = "liquidity"
    CONCENTRATION = "concentration"
    SECTOR_EXCLUSIONS = "sector_exclusions"


class ScreeningReason(StrEnum):
    """Stable reason codes suitable for UI tables and audit records."""

    US_LISTING_CONFIRMED = "us_listing_confirmed"
    ETF_TYPE_CONFIRMED = "etf_type_confirmed"
    SOURCE_CURRENT = "source_current"
    SOURCE_HEALTH_UNKNOWN = "source_health_unknown"
    EXPENSE_RATIO_WITHIN_LIMIT = "expense_ratio_within_limit"
    EXPENSE_RATIO_ABOVE_LIMIT = "expense_ratio_above_limit"
    EXPENSE_RATIO_UNKNOWN = "expense_ratio_unknown"
    VOLUME_MEETS_MINIMUM = "volume_meets_minimum"
    VOLUME_BELOW_MINIMUM = "volume_below_minimum"
    VOLUME_UNKNOWN = "volume_unknown"
    CONCENTRATION_WITHIN_LIMIT = "concentration_within_limit"
    CONCENTRATION_ABOVE_LIMIT = "concentration_above_limit"
    CONCENTRATION_UNKNOWN = "concentration_unknown"
    NO_SECTOR_EXCLUSIONS = "no_sector_exclusions"
    SECTOR_EXCLUSIONS_CLEAR = "sector_exclusions_clear"
    EXCLUDED_SECTOR_DETECTED = "excluded_sector_detected"
    SECTOR_EXPOSURE_UNKNOWN = "sector_exposure_unknown"
    UNSUPPORTED_SECTOR_EXCLUSION = "unsupported_sector_exclusion"


class CandidateScreeningPolicy(BaseModel):
    """Illustrative, configurable research filters; not suitability thresholds."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)

    max_expense_ratio_pct: float = Field(default=1.0, ge=0, le=100)
    min_average_daily_volume: float = Field(default=100_000, ge=0)
    max_top_10_concentration_pct: float = Field(default=60.0, ge=0, le=100)
    excluded_sector_weight_tolerance_pct: float = Field(default=0.0, ge=0, le=100)


class ScreeningCitation(BaseModel):
    """Exact source identity for one deterministic rule result."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=300)
    symbol: str = Field(min_length=1, max_length=12)
    field_name: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=80)
    source_url: str = Field(min_length=1, max_length=1000)
    observed_at: datetime

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Screening citations require an HTTP(S) source URL.")
        return normalized

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Screening citation timestamps must be timezone-aware.")
        return value.astimezone(UTC)


class ScreeningRuleResult(BaseModel):
    """One auditable pass, fail, or unknown judgment."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    criterion: ScreeningCriterion
    verdict: ScreeningVerdict
    reason_code: ScreeningReason
    message: str = Field(min_length=1, max_length=1000)
    observed_value: str | float | None = None
    threshold: str | float | None = None
    citation: ScreeningCitation | None = None
    unresolved_exclusions: list[str] = Field(default_factory=list, max_length=25)

    @field_validator("unresolved_exclusions")
    @classmethod
    def normalize_unresolved_exclusions(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = value.strip()
            key = item.casefold()
            if not item or len(item) > 200:
                raise ValueError("Unresolved exclusions must be non-empty and at most 200 chars.")
            if key not in seen:
                normalized.append(item)
                seen.add(key)
        return normalized

    @model_validator(mode="after")
    def validate_unresolved_exclusions(self) -> ScreeningRuleResult:
        if self.unresolved_exclusions and self.criterion != ScreeningCriterion.SECTOR_EXCLUSIONS:
            raise ValueError("Only the sector-exclusion rule can retain unresolved exclusions.")
        if self.unresolved_exclusions and self.verdict == ScreeningVerdict.PASS:
            raise ValueError("A passing rule cannot retain unresolved exclusions.")
        if (
            self.reason_code == ScreeningReason.UNSUPPORTED_SECTOR_EXCLUSION
            and not self.unresolved_exclusions
        ):
            raise ValueError("Unsupported sector exclusions must be retained explicitly.")
        return self


class CandidateScreeningResult(BaseModel):
    """Deterministic comparison result for one retrieved candidate."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=300)
    symbol: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=200)
    verdict: ScreeningVerdict
    rules: list[ScreeningRuleResult]

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_rule_summary(self) -> CandidateScreeningResult:
        expected = list(ScreeningCriterion)
        actual = [rule.criterion for rule in self.rules]
        if actual != expected:
            raise ValueError("Candidate screening rules must appear exactly once in stable order.")
        if self.verdict != _overall_verdict([rule.verdict for rule in self.rules]):
            raise ValueError("Candidate screening verdict must match its rule results.")
        for rule in self.rules:
            citation = rule.citation
            if citation is not None and (
                citation.document_id != self.document_id or citation.symbol != self.symbol
            ):
                raise ValueError("Screening citations must match their candidate identity.")
        return self


class CandidateScreeningBundle(BaseModel):
    """Review-ready comparison table derived from one ready evidence bundle."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready"] = "ready"
    checked_at: datetime
    excluded_sectors: list[str]
    policy: CandidateScreeningPolicy
    candidates: list[CandidateScreeningResult]

    @field_validator("checked_at")
    @classmethod
    def normalize_checked_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Candidate screening timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_candidates(self) -> CandidateScreeningBundle:
        identities = [(candidate.document_id, candidate.symbol) for candidate in self.candidates]
        if len(identities) != len(set(identities)):
            raise ValueError("Candidate screening identities must be unique.")
        return self


DEFAULT_SCREENING_POLICY: Final[CandidateScreeningPolicy] = CandidateScreeningPolicy()

# Yahoo's current source taxonomy plus common user-facing aliases. Terms outside this
# closed set cannot be verified from sector-level evidence and therefore remain unknown.
_SECTOR_ALIASES: Final[dict[str, str]] = {
    "basic materials": "basic materials",
    "materials": "basic materials",
    "communication services": "communication services",
    "consumer cyclical": "consumer cyclical",
    "consumer discretionary": "consumer cyclical",
    "consumer defensive": "consumer defensive",
    "consumer staples": "consumer defensive",
    "energy": "energy",
    "financial services": "financial services",
    "financials": "financial services",
    "health care": "healthcare",
    "healthcare": "healthcare",
    "industrials": "industrials",
    "real estate": "real estate",
    "technology": "technology",
    "information technology": "technology",
    "utilities": "utilities",
}


def screen_candidate_evidence(
    evidence: CandidateEvidenceBundle,
    policy: CandidateScreeningPolicy = DEFAULT_SCREENING_POLICY,
) -> CandidateScreeningBundle:
    """Apply deterministic rules without ranking candidates or calling side effects."""

    validated_evidence = CandidateEvidenceBundle.model_validate(evidence.model_dump(mode="python"))
    validated_policy = CandidateScreeningPolicy.model_validate(policy.model_dump(mode="python"))
    if validated_evidence.status != EvidenceStatus.READY:
        raise ScreeningContractError("Candidate screening requires ready source evidence.")

    health_by_identity = {
        (
            item.symbol.strip().upper(),
            item.source,
            item.source_url,
            item.observed_at,
        ): item
        for item in validated_evidence.health.observations
    }
    results = [
        _screen_candidate(
            candidate,
            excluded_sectors=validated_evidence.excluded_sectors,
            policy=validated_policy,
            health=health_by_identity.get(
                (
                    candidate.symbol,
                    candidate.source,
                    candidate.source_url,
                    candidate.observed_at,
                )
            ),
            max_age_hours=validated_evidence.health.max_age_hours,
        )
        for candidate in validated_evidence.candidates
    ]
    return CandidateScreeningBundle(
        checked_at=validated_evidence.checked_at,
        excluded_sectors=list(validated_evidence.excluded_sectors),
        policy=validated_policy,
        candidates=results,
    )


def _screen_candidate(
    candidate: CandidateEvidence,
    *,
    excluded_sectors: list[str],
    policy: CandidateScreeningPolicy,
    health: ObservationHealth | None,
    max_age_hours: float,
) -> CandidateScreeningResult:
    provenance = _field_provenance(candidate)
    rules = [
        _confirmed_rule(
            candidate,
            criterion=ScreeningCriterion.US_LISTING,
            reason=ScreeningReason.US_LISTING_CONFIRMED,
            message="Source metadata confirms a US-market listing.",
            observed_value=candidate.market,
            field_name="market",
            provenance=provenance.get("market"),
        ),
        _confirmed_rule(
            candidate,
            criterion=ScreeningCriterion.INSTRUMENT_TYPE,
            reason=ScreeningReason.ETF_TYPE_CONFIRMED,
            message="Source metadata confirms the instrument is an ETF.",
            observed_value=candidate.quote_type,
            field_name="quote_type",
            provenance=provenance.get("quote_type"),
        ),
        _freshness_rule(candidate, health, max_age_hours=max_age_hours),
        _numeric_rule(
            candidate,
            provenance=provenance.get("expense_ratio_pct"),
            field_name="expense_ratio_pct",
            criterion=ScreeningCriterion.EXPENSE_RATIO,
            threshold=policy.max_expense_ratio_pct,
            pass_when=lambda value: value <= policy.max_expense_ratio_pct,
            pass_reason=ScreeningReason.EXPENSE_RATIO_WITHIN_LIMIT,
            fail_reason=ScreeningReason.EXPENSE_RATIO_ABOVE_LIMIT,
            unknown_reason=ScreeningReason.EXPENSE_RATIO_UNKNOWN,
            pass_message="Expense ratio is at or below the illustrative maximum.",
            fail_message="Expense ratio is above the illustrative maximum.",
            expected_unit="percent",
            threshold_unit="%",
            maximum_value=100,
        ),
        _numeric_rule(
            candidate,
            provenance=provenance.get("average_daily_volume"),
            field_name="average_daily_volume",
            criterion=ScreeningCriterion.LIQUIDITY,
            threshold=policy.min_average_daily_volume,
            pass_when=lambda value: value >= policy.min_average_daily_volume,
            pass_reason=ScreeningReason.VOLUME_MEETS_MINIMUM,
            fail_reason=ScreeningReason.VOLUME_BELOW_MINIMUM,
            unknown_reason=ScreeningReason.VOLUME_UNKNOWN,
            pass_message="Average daily volume meets the illustrative minimum.",
            fail_message="Average daily volume is below the illustrative minimum.",
            expected_unit="shares",
            threshold_unit="shares",
        ),
        _numeric_rule(
            candidate,
            provenance=provenance.get("top_10_concentration_pct"),
            field_name="top_10_concentration_pct",
            criterion=ScreeningCriterion.CONCENTRATION,
            threshold=policy.max_top_10_concentration_pct,
            pass_when=lambda value: value <= policy.max_top_10_concentration_pct,
            pass_reason=ScreeningReason.CONCENTRATION_WITHIN_LIMIT,
            fail_reason=ScreeningReason.CONCENTRATION_ABOVE_LIMIT,
            unknown_reason=ScreeningReason.CONCENTRATION_UNKNOWN,
            pass_message="Top-ten concentration is at or below the illustrative maximum.",
            fail_message="Top-ten concentration is above the illustrative maximum.",
            expected_unit="percent",
            threshold_unit="%",
            maximum_value=100,
        ),
        _sector_rule(
            candidate,
            provenance=provenance.get("sector_exposures"),
            excluded_sectors=excluded_sectors,
            tolerance=policy.excluded_sector_weight_tolerance_pct,
        ),
    ]
    return CandidateScreeningResult(
        document_id=candidate.document_id,
        symbol=candidate.symbol,
        name=candidate.name,
        verdict=_overall_verdict([rule.verdict for rule in rules]),
        rules=rules,
    )


def _confirmed_rule(
    candidate: CandidateEvidence,
    *,
    criterion: ScreeningCriterion,
    reason: ScreeningReason,
    message: str,
    observed_value: str,
    field_name: str,
    provenance: ResearchField[Any] | None,
) -> ScreeningRuleResult:
    citation = _candidate_citation(candidate, field_name)
    if provenance is not None:
        if provenance.missing_reason is not None or provenance.value != observed_value:
            raise ScreeningContractError(
                f"{candidate.document_id}: {field_name} provenance conflicts with evidence."
            )
        citation = _field_citation(candidate, field_name, provenance)
    return ScreeningRuleResult(
        criterion=criterion,
        verdict=ScreeningVerdict.PASS,
        reason_code=reason,
        message=message,
        observed_value=observed_value,
        citation=citation,
    )


def _freshness_rule(
    candidate: CandidateEvidence,
    health: ObservationHealth | None,
    *,
    max_age_hours: float,
) -> ScreeningRuleResult:
    citation = _candidate_citation(candidate, "observed_at")
    if health is None:
        return ScreeningRuleResult(
            criterion=ScreeningCriterion.FRESHNESS,
            verdict=ScreeningVerdict.UNKNOWN,
            reason_code=ScreeningReason.SOURCE_HEALTH_UNKNOWN,
            message="No matching source-health observation is available.",
            observed_value=candidate.observed_at.isoformat(),
            citation=citation,
        )
    if health.status != FreshnessStatus.CURRENT:
        raise ScreeningContractError(
            f"{candidate.document_id}: ready evidence contains non-current source health."
        )
    return ScreeningRuleResult(
        criterion=ScreeningCriterion.FRESHNESS,
        verdict=ScreeningVerdict.PASS,
        reason_code=ScreeningReason.SOURCE_CURRENT,
        message="Observation is within the configured freshness window.",
        observed_value=f"{health.age_hours:g} hours old",
        threshold=f"maximum {max_age_hours:g} hours",
        citation=citation,
    )


def _numeric_rule(
    candidate: CandidateEvidence,
    *,
    provenance: ResearchField[Any] | None,
    field_name: str,
    criterion: ScreeningCriterion,
    threshold: float,
    pass_when: Callable[[float], bool],
    pass_reason: ScreeningReason,
    fail_reason: ScreeningReason,
    unknown_reason: ScreeningReason,
    pass_message: str,
    fail_message: str,
    expected_unit: str,
    threshold_unit: str,
    maximum_value: float | None = None,
) -> ScreeningRuleResult:
    if provenance is None:
        return ScreeningRuleResult(
            criterion=criterion,
            verdict=ScreeningVerdict.UNKNOWN,
            reason_code=unknown_reason,
            message=f"{field_name} has no field-level provenance.",
            threshold=f"{threshold:g} {threshold_unit}",
            citation=_candidate_citation(candidate, field_name),
        )
    citation = _field_citation(candidate, field_name, provenance)
    if provenance.unit != expected_unit:
        raise ScreeningContractError(
            f"{candidate.document_id}: {field_name} must use {expected_unit} units."
        )
    if provenance.missing_reason is not None:
        return ScreeningRuleResult(
            criterion=criterion,
            verdict=ScreeningVerdict.UNKNOWN,
            reason_code=unknown_reason,
            message=f"{field_name} is unavailable: {provenance.missing_reason.value}.",
            observed_value=provenance.missing_reason.value,
            threshold=f"{threshold:g} {threshold_unit}",
            citation=citation,
        )
    value = _finite_number(
        candidate,
        field_name,
        provenance.value,
        maximum=maximum_value,
    )
    verdict = ScreeningVerdict.PASS if pass_when(value) else ScreeningVerdict.FAIL
    return ScreeningRuleResult(
        criterion=criterion,
        verdict=verdict,
        reason_code=pass_reason if verdict == ScreeningVerdict.PASS else fail_reason,
        message=pass_message if verdict == ScreeningVerdict.PASS else fail_message,
        observed_value=value,
        threshold=f"{threshold:g} {threshold_unit}",
        citation=citation,
    )


def _sector_rule(
    candidate: CandidateEvidence,
    *,
    provenance: ResearchField[Any] | None,
    excluded_sectors: list[str],
    tolerance: float,
) -> ScreeningRuleResult:
    if not excluded_sectors:
        return ScreeningRuleResult(
            criterion=ScreeningCriterion.SECTOR_EXCLUSIONS,
            verdict=ScreeningVerdict.PASS,
            reason_code=ScreeningReason.NO_SECTOR_EXCLUSIONS,
            message="No sector exclusions were requested.",
            threshold=f"greater than {tolerance:g}%",
        )

    citation = (
        _field_citation(candidate, "sector_exposures", provenance)
        if provenance is not None
        else _candidate_citation(candidate, "sector_exposures")
    )
    requested, unsupported = _normalize_requested_sectors(excluded_sectors)
    context = candidate.graph_context
    if (
        context is None
        or context.sector_exposures_status != "available"
        or provenance is None
        or provenance.missing_reason is not None
    ):
        missing_status = (
            context.sector_exposures_status
            if context is not None and context.sector_exposures_status is not None
            else "not_available"
        )
        return ScreeningRuleResult(
            criterion=ScreeningCriterion.SECTOR_EXCLUSIONS,
            verdict=ScreeningVerdict.UNKNOWN,
            reason_code=ScreeningReason.SECTOR_EXPOSURE_UNKNOWN,
            message="Structured sector evidence is unavailable; exclusions cannot be verified.",
            observed_value=missing_status,
            threshold=f"greater than {tolerance:g}%",
            citation=citation,
            unresolved_exclusions=excluded_sectors,
        )

    source_exposures = _weighted_exposures(candidate, provenance.value)
    graph_weights = {
        _canonical_sector(item.name): item.weight_pct for item in context.sector_exposures
    }
    source_weights = {_canonical_sector(item.name): item.weight_pct for item in source_exposures}
    if graph_weights != source_weights:
        raise ScreeningContractError(
            f"{candidate.document_id}: graph sector weights conflict with field provenance."
        )

    detected = {
        sector: graph_weights.get(sector, 0.0)
        for sector in requested
        if graph_weights.get(sector, 0.0) > tolerance
    }
    if detected:
        details = ", ".join(f"{name}={weight:g}%" for name, weight in sorted(detected.items()))
        message = "Reported exposure exceeds the tolerance for an excluded sector."
        if unsupported:
            message += " Other exclusions remain unresolved outside the sector taxonomy."
        return ScreeningRuleResult(
            criterion=ScreeningCriterion.SECTOR_EXCLUSIONS,
            verdict=ScreeningVerdict.FAIL,
            reason_code=ScreeningReason.EXCLUDED_SECTOR_DETECTED,
            message=message,
            observed_value=details,
            threshold=f"greater than {tolerance:g}%",
            citation=citation,
            unresolved_exclusions=unsupported,
        )
    if unsupported:
        return ScreeningRuleResult(
            criterion=ScreeningCriterion.SECTOR_EXCLUSIONS,
            verdict=ScreeningVerdict.UNKNOWN,
            reason_code=ScreeningReason.UNSUPPORTED_SECTOR_EXCLUSION,
            message="One or more exclusions are outside the available sector taxonomy.",
            observed_value=", ".join(unsupported),
            threshold=f"greater than {tolerance:g}%",
            citation=citation,
            unresolved_exclusions=unsupported,
        )
    return ScreeningRuleResult(
        criterion=ScreeningCriterion.SECTOR_EXCLUSIONS,
        verdict=ScreeningVerdict.PASS,
        reason_code=ScreeningReason.SECTOR_EXCLUSIONS_CLEAR,
        message="No requested sector exceeds the configured exposure tolerance.",
        observed_value=", ".join(sorted(requested)),
        threshold=f"greater than {tolerance:g}%",
        citation=citation,
    )


def _field_provenance(candidate: CandidateEvidence) -> dict[str, ResearchField[Any]]:
    raw = candidate.metadata.get("field_provenance_json")
    if raw is None:
        return {}
    if not isinstance(raw, str):
        raise ScreeningContractError(
            f"{candidate.document_id}: field provenance must be canonical JSON text."
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScreeningContractError(
            f"{candidate.document_id}: field provenance is not valid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ScreeningContractError(
            f"{candidate.document_id}: field provenance must be a JSON object."
        )

    parsed: dict[str, ResearchField[Any]] = {}
    for field_name, field_payload in payload.items():
        if not isinstance(field_name, str) or not isinstance(field_payload, dict):
            raise ScreeningContractError(
                f"{candidate.document_id}: field provenance entries are malformed."
            )
        try:
            field = ResearchField[Any].model_validate(field_payload)
        except ValidationError as exc:
            raise ScreeningContractError(
                f"{candidate.document_id}: {field_name} provenance failed validation."
            ) from exc
        expected_status = (
            "available" if field.missing_reason is None else field.missing_reason.value
        )
        if candidate.metadata.get(f"{field_name}_status") != expected_status:
            raise ScreeningContractError(
                f"{candidate.document_id}: {field_name} status conflicts with provenance."
            )
        if (
            field.missing_reason is None
            and isinstance(field.value, (str, int, float, bool))
            and candidate.metadata.get(field_name) != field.value
        ):
            raise ScreeningContractError(
                f"{candidate.document_id}: {field_name} metadata conflicts with provenance."
            )
        parsed[field_name] = field
    return parsed


def _field_citation(
    candidate: CandidateEvidence,
    field_name: str,
    provenance: ResearchField[Any],
) -> ScreeningCitation:
    return ScreeningCitation(
        document_id=candidate.document_id,
        symbol=candidate.symbol,
        field_name=field_name,
        source=provenance.provider,
        source_url=provenance.source_url,
        observed_at=provenance.observed_at,
    )


def _candidate_citation(candidate: CandidateEvidence, field_name: str) -> ScreeningCitation:
    return ScreeningCitation(
        document_id=candidate.document_id,
        symbol=candidate.symbol,
        field_name=field_name,
        source=candidate.source,
        source_url=candidate.source_url,
        observed_at=candidate.observed_at,
    )


def _finite_number(
    candidate: CandidateEvidence,
    field_name: str,
    value: Any,
    *,
    maximum: float | None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScreeningContractError(
            f"{candidate.document_id}: {field_name} must be a finite number."
        )
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ScreeningContractError(
            f"{candidate.document_id}: {field_name} must be a non-negative finite number."
        )
    if maximum is not None and number > maximum:
        raise ScreeningContractError(
            f"{candidate.document_id}: {field_name} cannot exceed {maximum:g}."
        )
    return number


def _weighted_exposures(candidate: CandidateEvidence, value: Any) -> list[WeightedExposure]:
    if not isinstance(value, list):
        raise ScreeningContractError(f"{candidate.document_id}: sector_exposures must be a list.")
    try:
        exposures = [WeightedExposure.model_validate(item) for item in value]
    except ValidationError as exc:
        raise ScreeningContractError(
            f"{candidate.document_id}: sector exposure provenance is malformed."
        ) from exc
    if not exposures:
        raise ScreeningContractError(
            f"{candidate.document_id}: available sector exposure provenance cannot be empty."
        )
    names = [_canonical_sector(item.name) for item in exposures]
    if len(names) != len(set(names)):
        raise ScreeningContractError(
            f"{candidate.document_id}: sector exposure provenance contains duplicates."
        )
    return exposures


def _normalize_requested_sectors(sectors: list[str]) -> tuple[set[str], list[str]]:
    normalized: set[str] = set()
    unsupported: list[str] = []
    for sector in sectors:
        key = _normalize_words(sector)
        canonical = _SECTOR_ALIASES.get(key)
        if canonical is None:
            unsupported.append(sector)
        else:
            normalized.add(canonical)
    return normalized, unsupported


def _canonical_sector(value: str) -> str:
    normalized = _normalize_words(value)
    return _SECTOR_ALIASES.get(normalized, normalized)


def _normalize_words(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").split()).casefold()


def _overall_verdict(verdicts: list[ScreeningVerdict]) -> ScreeningVerdict:
    if ScreeningVerdict.FAIL in verdicts:
        return ScreeningVerdict.FAIL
    if ScreeningVerdict.UNKNOWN in verdicts:
        return ScreeningVerdict.UNKNOWN
    return ScreeningVerdict.PASS
