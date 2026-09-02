"""Pure, deterministic construction of illustrative ETF model portfolios."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from itertools import combinations
from typing import Any, Final, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from etf_advisor.domain.policy import PolicyCalculation, calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import (
    CandidateScreeningBundle,
    CandidateScreeningResult,
    ScreeningContractError,
    ScreeningVerdict,
    screen_candidate_evidence,
)
from etf_advisor.rag.evidence import CandidateEvidence, CandidateEvidenceBundle, EvidenceStatus
from etf_advisor.research.models import ResearchField

TOTAL_WEIGHT_BPS: Final[int] = 10_000


def _normalize_category(value: str) -> str:
    return " ".join(value.split()).casefold()


class PortfolioSleeve(StrEnum):
    """The two policy sleeves supported by the current calculation contract."""

    GROWTH = "growth"
    DEFENSIVE = "defensive"


class ConstructionReason(StrEnum):
    """Stable construction, exclusion, validation, and recomputation reasons."""

    CANDIDATE_SCREENING_FAILED = "candidate_screening_failed"
    CANDIDATE_SCREENING_UNKNOWN = "candidate_screening_unknown"
    CATEGORY_MISSING = "category_missing"
    CATEGORY_UNSUPPORTED = "category_unsupported"
    CATEGORY_PROVENANCE_CONFLICT = "category_provenance_conflict"
    UPSTREAM_CONTRACT_MISMATCH = "upstream_contract_mismatch"
    EVIDENCE_NOT_READY = "evidence_not_ready"
    SCREENING_RECOMPUTATION_MISMATCH = "screening_recomputation_mismatch"
    MISSING_SLEEVE_COVERAGE = "missing_sleeve_coverage"
    INSUFFICIENT_ELIGIBLE_CANDIDATES = "insufficient_eligible_candidates"
    POSITION_CONSTRAINTS_INFEASIBLE = "position_constraints_infeasible"
    CATEGORY_LIMIT_INFEASIBLE = "category_limit_infeasible"
    ALLOCATION_BAND_MISMATCH = "allocation_band_mismatch"
    ALLOCATION_PRECISION_UNSUPPORTED = "allocation_precision_unsupported"
    WEIGHT_RECONCILIATION_FAILED = "weight_reconciliation_failed"
    CASH_RECONCILIATION_FAILED = "cash_reconciliation_failed"
    PERSISTED_CONSTRUCTION_MISMATCH = "persisted_construction_mismatch"


class ConstructionCheckName(StrEnum):
    """Stable order for independent construction validation checks."""

    UPSTREAM_CONSISTENCY = "upstream_consistency"
    ALLOCATION_BAND_CONSISTENCY = "allocation_band_consistency"
    ELIGIBILITY = "eligibility"
    SLEEVE_COVERAGE = "sleeve_coverage"
    POSITION_COUNT = "position_count"
    POSITION_WEIGHTS = "position_weights"
    CATEGORY_CONCENTRATION = "category_concentration"
    WEIGHT_TOTAL = "weight_total"
    SLEEVE_TOTALS = "sleeve_totals"
    INITIAL_CASH = "initial_cash"
    RECURRING_CASH = "recurring_cash"
    SOURCE_ATTRIBUTION = "source_attribution"
    PERSISTED_RECOMPUTATION = "persisted_recomputation"


def _default_category_sleeves() -> dict[PortfolioSleeve, list[str]]:
    return {
        PortfolioSleeve.GROWTH: [
            "Large Blend",
            "Large Growth",
            "Foreign Large Blend",
            "Diversified Emerging Mkts",
        ],
        PortfolioSleeve.DEFENSIVE: ["Intermediate Core Bond"],
    }


class PortfolioConstructionPolicy(BaseModel):
    """Checkpointed illustrative rules for deterministic subset construction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    min_positions: int = Field(default=3, ge=1, le=50)
    max_positions: int = Field(default=5, ge=1, le=50)
    min_position_weight_bps: int = Field(default=500, ge=0, le=TOTAL_WEIGHT_BPS)
    max_position_weight_bps: int = Field(default=8_000, ge=0, le=TOTAL_WEIGHT_BPS)
    max_category_weight_bps: int = Field(default=8_000, ge=0, le=TOTAL_WEIGHT_BPS)
    weight_precision_bps: int = Field(default=1, ge=1, le=TOTAL_WEIGHT_BPS)
    category_sleeves: dict[PortfolioSleeve, list[str]] = Field(
        default_factory=_default_category_sleeves
    )

    @model_validator(mode="after")
    def validate_bounds_and_categories(self) -> PortfolioConstructionPolicy:
        if self.min_positions > self.max_positions:
            raise ValueError("Minimum positions cannot exceed maximum positions.")
        if self.min_position_weight_bps > self.max_position_weight_bps:
            raise ValueError("Minimum position weight cannot exceed maximum position weight.")
        if set(self.category_sleeves) != set(PortfolioSleeve):
            raise ValueError("Construction policy must configure growth and defensive sleeves.")
        normalized: set[str] = set()
        for categories in self.category_sleeves.values():
            if not categories:
                raise ValueError("Every construction sleeve requires at least one category.")
            for category in categories:
                key = _normalize_category(category)
                if not key or len(category) > 200:
                    raise ValueError("Construction categories must be non-empty and bounded.")
                if key in normalized:
                    raise ValueError("A normalized category can belong to only one sleeve.")
                normalized.add(key)
        return self


DEFAULT_CONSTRUCTION_POLICY: Final[PortfolioConstructionPolicy] = PortfolioConstructionPolicy()


class ConstructionError(BaseModel):
    """One stable fail-closed construction error."""

    model_config = ConfigDict(extra="forbid")

    code: ConstructionReason
    message: str = Field(min_length=1, max_length=1000)


class ExcludedCandidate(BaseModel):
    """Auditable candidate-local exclusion that never receives a weight."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=300)
    symbol: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=200)
    reason_code: ConstructionReason
    screening_verdict: ScreeningVerdict
    screening_reason_codes: list[str]

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class PortfolioPosition(BaseModel):
    """One fully attributable position in an illustrative model portfolio."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=300)
    symbol: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=80)
    source_url: str = Field(min_length=1, max_length=1000)
    observed_at: datetime
    sleeve: PortfolioSleeve
    source_category: str = Field(min_length=1, max_length=200)
    weight_bps: int = Field(ge=0, le=TOTAL_WEIGHT_BPS)
    initial_usd_cents: int = Field(ge=0)
    recurring_usd_cents: int = Field(ge=0)
    reason_code: Literal["supports_growth_target", "supports_defensive_target"]
    policy_reference: Literal[
        "policy.target_allocation.growth_assets_pct",
        "policy.target_allocation.defensive_assets_pct",
    ]
    screening_reason_codes: list[str]

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
            raise ValueError("Portfolio position sources require an HTTP(S) URL.")
        return normalized

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Portfolio position timestamps must be timezone-aware.")
        return value.astimezone(UTC)


class PortfolioDraft(BaseModel):
    """Exact integer allocation produced by the deterministic constructor."""

    model_config = ConfigDict(extra="forbid")

    positions: list[PortfolioPosition]
    total_weight_bps: int = Field(ge=0, le=TOTAL_WEIGHT_BPS)
    sleeve_weight_bps: dict[PortfolioSleeve, int]
    initial_total_cents: int = Field(ge=0)
    recurring_total_cents: int = Field(ge=0)


class ConstructionValidationCheck(BaseModel):
    """One stable pass/fail result from the independent draft validator."""

    model_config = ConfigDict(extra="forbid")

    name: ConstructionCheckName
    passed: bool
    reason_code: ConstructionReason | None = None
    message: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_reason(self) -> ConstructionValidationCheck:
        if self.passed == (self.reason_code is not None):
            raise ValueError("Failed checks require a reason and passing checks cannot have one.")
        return self


class PortfolioValidationResult(BaseModel):
    """Independent ordered validation of a constructed draft."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    checks: list[ConstructionValidationCheck]

    @model_validator(mode="after")
    def validate_summary(self) -> PortfolioValidationResult:
        if [check.name for check in self.checks] != list(ConstructionCheckName):
            raise ValueError("Construction validation checks must appear exactly once in order.")
        if self.valid != all(check.passed for check in self.checks):
            raise ValueError("Construction validation status must match its checks.")
        return self


class PortfolioConstructionBundle(BaseModel):
    """One JSON-safe construction result checkpointed by the workflow."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "blocked"]
    policy: PortfolioConstructionPolicy
    draft: PortfolioDraft | None = None
    validation: PortfolioValidationResult
    excluded_candidates: list[ExcludedCandidate]
    errors: list[ConstructionError]

    @model_validator(mode="after")
    def validate_status(self) -> PortfolioConstructionBundle:
        if self.status == "ready":
            if self.draft is None or self.errors or not self.validation.valid:
                raise ValueError("Ready construction requires a valid draft and no errors.")
        elif self.draft is not None or not self.errors:
            raise ValueError("Blocked construction requires errors and cannot expose a draft.")
        return self


class PortfolioConstructionInput(BaseModel):
    """The five validated, JSON-serializable inputs to pure construction."""

    model_config = ConfigDict(extra="forbid")

    profile: InvestorProfile
    policy_calculation: PolicyCalculation
    candidate_evidence: CandidateEvidenceBundle
    candidate_screening: CandidateScreeningBundle
    construction_policy: PortfolioConstructionPolicy = DEFAULT_CONSTRUCTION_POLICY


@dataclass(frozen=True)
class _EligibleCandidate:
    index: int
    candidate: CandidateEvidence
    screening: CandidateScreeningResult
    sleeve: PortfolioSleeve
    category: str
    category_provenance: ResearchField[Any]


class _CategoryConflict(ValueError):
    pass


def construct_model_portfolio(
    construction_input: PortfolioConstructionInput,
) -> PortfolioConstructionBundle:
    """Construct the same draft or blocker for the same validated inputs."""

    inputs = PortfolioConstructionInput.model_validate(construction_input.model_dump(mode="python"))
    policy = inputs.construction_policy
    upstream_error = _validate_upstream(inputs)
    if upstream_error is not None:
        return _blocked_bundle(policy, upstream_error)

    target_or_error = _target_basis_points(inputs.policy_calculation, policy)
    if isinstance(target_or_error, ConstructionReason):
        return _blocked_bundle(
            policy,
            target_or_error,
            passed_checks={ConstructionCheckName.UPSTREAM_CONSISTENCY},
        )
    targets = target_or_error

    eligible, excluded, category_error = _classify_candidates(inputs, policy)
    passed = {
        ConstructionCheckName.UPSTREAM_CONSISTENCY,
        ConstructionCheckName.ALLOCATION_BAND_CONSISTENCY,
    }
    if category_error is not None:
        return _blocked_bundle(policy, category_error, excluded, passed_checks=passed)
    if len(eligible) < policy.min_positions:
        return _blocked_bundle(
            policy,
            ConstructionReason.INSUFFICIENT_ELIGIBLE_CANDIDATES,
            excluded,
            passed_checks=passed,
        )
    passed.add(ConstructionCheckName.ELIGIBILITY)

    selected, failure = _select_subset(eligible, targets, policy)
    if selected is None:
        return _blocked_bundle(policy, failure, excluded, passed_checks=passed)

    positions_without_cash, weights = selected
    try:
        initial_by_sleeve, initial_total = _policy_cash_cents(
            inputs.policy_calculation, "initial_investment_usd"
        )
        recurring_by_sleeve, recurring_total = _policy_cash_cents(
            inputs.policy_calculation, "recurring_monthly_usd"
        )
        initial_cents = _allocate_all_cash(positions_without_cash, weights, initial_by_sleeve)
        recurring_cents = _allocate_all_cash(positions_without_cash, weights, recurring_by_sleeve)
    except ValueError:
        return _blocked_bundle(
            policy,
            ConstructionReason.CASH_RECONCILIATION_FAILED,
            excluded,
            passed_checks=passed,
        )

    positions = [
        _position_from_candidate(item, weights[index], initial_cents[index], recurring_cents[index])
        for index, item in enumerate(positions_without_cash)
    ]
    draft = PortfolioDraft(
        positions=positions,
        total_weight_bps=sum(weights),
        sleeve_weight_bps={
            sleeve: sum(position.weight_bps for position in positions if position.sleeve == sleeve)
            for sleeve in PortfolioSleeve
        },
        initial_total_cents=initial_total,
        recurring_total_cents=recurring_total,
    )
    validation = validate_portfolio_draft(inputs, draft)
    if not validation.valid:
        failed = next(check for check in validation.checks if not check.passed)
        return _blocked_bundle(
            policy,
            failed.reason_code or ConstructionReason.WEIGHT_RECONCILIATION_FAILED,
            excluded,
            validation=validation,
        )
    return PortfolioConstructionBundle(
        status="ready",
        policy=policy,
        draft=draft,
        validation=validation,
        excluded_candidates=excluded,
        errors=[],
    )


def blocked_model_portfolio(
    policy: PortfolioConstructionPolicy,
    reason: ConstructionReason,
) -> PortfolioConstructionBundle:
    """Build a stable blocker when graph-state input cannot form the typed boundary."""

    validated_policy = PortfolioConstructionPolicy.model_validate(policy.model_dump(mode="python"))
    return _blocked_bundle(validated_policy, reason)


def validate_portfolio_draft(
    construction_input: PortfolioConstructionInput,
    draft: PortfolioDraft,
) -> PortfolioValidationResult:
    """Independently validate every authoritative property of a draft."""

    inputs = PortfolioConstructionInput.model_validate(construction_input.model_dump(mode="python"))
    validated_draft = PortfolioDraft.model_validate(draft.model_dump(mode="python"))
    policy = inputs.construction_policy
    target_or_error = _target_basis_points(inputs.policy_calculation, policy)
    targets = target_or_error if isinstance(target_or_error, dict) else None
    upstream_ok = _validate_upstream(inputs) is None
    eligible, _, category_error = _classify_candidates(inputs, policy)
    eligible_by_id = {item.candidate.document_id: item for item in eligible}

    identities_unique = len(
        {position.document_id for position in validated_draft.positions}
    ) == len(validated_draft.positions)
    eligibility_ok = upstream_ok and category_error is None and identities_unique
    attribution_ok = eligibility_ok
    for position in validated_draft.positions:
        item = eligible_by_id.get(position.document_id)
        if item is None:
            eligibility_ok = False
            attribution_ok = False
            continue
        expected = _position_from_candidate(
            item,
            position.weight_bps,
            position.initial_usd_cents,
            position.recurring_usd_cents,
        )
        if (
            position.model_copy(
                update={
                    "weight_bps": expected.weight_bps,
                    "initial_usd_cents": expected.initial_usd_cents,
                    "recurring_usd_cents": expected.recurring_usd_cents,
                }
            )
            != expected
        ):
            eligibility_ok = False
            attribution_ok = False

    nonzero_sleeves = {sleeve for sleeve, weight in (targets or {}).items() if weight > 0}
    actual_sleeves = {position.sleeve for position in validated_draft.positions}
    sleeve_coverage_ok = targets is not None and nonzero_sleeves <= actual_sleeves
    count_ok = policy.min_positions <= len(validated_draft.positions) <= policy.max_positions
    position_weights_ok = all(
        policy.min_position_weight_bps <= position.weight_bps <= policy.max_position_weight_bps
        and position.weight_bps % policy.weight_precision_bps == 0
        for position in validated_draft.positions
    )
    category_totals: dict[str, int] = defaultdict(int)
    for position in validated_draft.positions:
        category_totals[_normalize_category(position.source_category)] += position.weight_bps
    category_ok = all(total <= policy.max_category_weight_bps for total in category_totals.values())
    weight_total_ok = (
        sum(position.weight_bps for position in validated_draft.positions) == TOTAL_WEIGHT_BPS
        and validated_draft.total_weight_bps == TOTAL_WEIGHT_BPS
    )
    actual_sleeve_totals = {
        sleeve: sum(
            position.weight_bps
            for position in validated_draft.positions
            if position.sleeve == sleeve
        )
        for sleeve in PortfolioSleeve
    }
    sleeve_totals_ok = (
        targets is not None
        and actual_sleeve_totals == targets
        and validated_draft.sleeve_weight_bps == targets
    )
    initial_ok = _validate_cash_allocations(inputs, validated_draft, recurring=False)
    recurring_ok = _validate_cash_allocations(inputs, validated_draft, recurring=True)

    outcomes = {
        ConstructionCheckName.UPSTREAM_CONSISTENCY: upstream_ok,
        ConstructionCheckName.ALLOCATION_BAND_CONSISTENCY: targets is not None,
        ConstructionCheckName.ELIGIBILITY: eligibility_ok,
        ConstructionCheckName.SLEEVE_COVERAGE: sleeve_coverage_ok,
        ConstructionCheckName.POSITION_COUNT: count_ok,
        ConstructionCheckName.POSITION_WEIGHTS: position_weights_ok,
        ConstructionCheckName.CATEGORY_CONCENTRATION: category_ok,
        ConstructionCheckName.WEIGHT_TOTAL: weight_total_ok,
        ConstructionCheckName.SLEEVE_TOTALS: sleeve_totals_ok,
        ConstructionCheckName.INITIAL_CASH: initial_ok,
        ConstructionCheckName.RECURRING_CASH: recurring_ok,
        ConstructionCheckName.SOURCE_ATTRIBUTION: attribution_ok,
        ConstructionCheckName.PERSISTED_RECOMPUTATION: True,
    }
    return _validation_result(outcomes)


def validate_persisted_construction(
    construction_input: PortfolioConstructionInput,
    persisted: PortfolioConstructionBundle,
) -> PortfolioConstructionBundle:
    """Fail closed when a checkpoint differs from deterministic recomputation."""

    expected = construct_model_portfolio(construction_input)
    try:
        actual = PortfolioConstructionBundle.model_validate(persisted.model_dump(mode="python"))
    except (AttributeError, TypeError, ValueError, ValidationError):
        actual = None
    if actual == expected:
        return expected
    outcomes = {check.name: check.passed for check in expected.validation.checks}
    outcomes[ConstructionCheckName.PERSISTED_RECOMPUTATION] = False
    validation = _validation_result(outcomes)
    return _blocked_bundle(
        expected.policy,
        ConstructionReason.PERSISTED_CONSTRUCTION_MISMATCH,
        expected.excluded_candidates,
        validation=validation,
    )


def _validate_upstream(inputs: PortfolioConstructionInput) -> ConstructionReason | None:
    if inputs.candidate_evidence.status != EvidenceStatus.READY:
        return ConstructionReason.EVIDENCE_NOT_READY
    for candidate in inputs.candidate_evidence.candidates:
        try:
            _category_provenance(candidate)
        except _CategoryConflict:
            return ConstructionReason.CATEGORY_PROVENANCE_CONFLICT
    profile = inputs.profile
    policy = inputs.policy_calculation
    if policy != calculate_policy(profile):
        return ConstructionReason.UPSTREAM_CONTRACT_MISMATCH
    evidence = inputs.candidate_evidence
    if (
        evidence.objective != profile.objective
        or evidence.risk_tolerance != profile.risk_tolerance
        or evidence.excluded_sectors != profile.excluded_sectors
        or inputs.candidate_screening.checked_at != evidence.checked_at
        or inputs.candidate_screening.excluded_sectors != evidence.excluded_sectors
    ):
        return ConstructionReason.UPSTREAM_CONTRACT_MISMATCH
    try:
        recomputed = screen_candidate_evidence(evidence, inputs.candidate_screening.policy)
    except (ScreeningContractError, TypeError, ValueError, ValidationError):
        return ConstructionReason.UPSTREAM_CONTRACT_MISMATCH
    if recomputed != inputs.candidate_screening:
        return ConstructionReason.SCREENING_RECOMPUTATION_MISMATCH
    return None


def _target_basis_points(
    calculation: PolicyCalculation,
    policy: PortfolioConstructionPolicy,
) -> dict[PortfolioSleeve, int] | ConstructionReason:
    if policy.weight_precision_bps != 1:
        return ConstructionReason.ALLOCATION_PRECISION_UNSUPPORTED
    growth = Decimal(str(calculation.target_allocation.growth_assets_pct)) * Decimal(100)
    defensive = Decimal(str(calculation.target_allocation.defensive_assets_pct)) * Decimal(100)
    if growth != growth.to_integral_value() or defensive != defensive.to_integral_value():
        return ConstructionReason.ALLOCATION_PRECISION_UNSUPPORTED
    targets = {
        PortfolioSleeve.GROWTH: int(growth),
        PortfolioSleeve.DEFENSIVE: int(defensive),
    }
    if sum(targets.values()) != TOTAL_WEIGHT_BPS:
        return ConstructionReason.WEIGHT_RECONCILIATION_FAILED
    growth_band = calculation.allocation_bands.get("growth_assets_pct", [])
    defensive_band = calculation.allocation_bands.get("defensive_assets_pct", [])
    if (
        len(growth_band) != 2
        or len(defensive_band) != 2
        or not growth_band[0] * 100 <= targets[PortfolioSleeve.GROWTH] <= growth_band[1] * 100
        or not defensive_band[0] * 100
        <= targets[PortfolioSleeve.DEFENSIVE]
        <= defensive_band[1] * 100
    ):
        return ConstructionReason.ALLOCATION_BAND_MISMATCH
    return targets


def _classify_candidates(
    inputs: PortfolioConstructionInput,
    policy: PortfolioConstructionPolicy,
) -> tuple[list[_EligibleCandidate], list[ExcludedCandidate], ConstructionReason | None]:
    eligible: list[_EligibleCandidate] = []
    excluded: list[ExcludedCandidate] = []
    category_map = {
        _normalize_category(category): (sleeve, " ".join(category.split()))
        for sleeve, categories in policy.category_sleeves.items()
        for category in categories
    }
    screening_by_id = {
        result.document_id: result for result in inputs.candidate_screening.candidates
    }
    for index, candidate in enumerate(inputs.candidate_evidence.candidates):
        screening = screening_by_id[candidate.document_id]
        nonpassing_reasons = [
            rule.reason_code.value
            for rule in screening.rules
            if rule.verdict != ScreeningVerdict.PASS
        ]
        if screening.verdict != ScreeningVerdict.PASS:
            reason = (
                ConstructionReason.CANDIDATE_SCREENING_FAILED
                if screening.verdict == ScreeningVerdict.FAIL
                else ConstructionReason.CANDIDATE_SCREENING_UNKNOWN
            )
            excluded.append(_excluded(candidate, screening, reason, nonpassing_reasons))
            continue
        try:
            category_result = _category_provenance(candidate)
        except _CategoryConflict:
            return eligible, excluded, ConstructionReason.CATEGORY_PROVENANCE_CONFLICT
        if category_result is None:
            excluded.append(
                _excluded(candidate, screening, ConstructionReason.CATEGORY_MISSING, [])
            )
            continue
        category_value, provenance = category_result
        mapped = category_map.get(_normalize_category(category_value))
        if mapped is None:
            excluded.append(
                _excluded(candidate, screening, ConstructionReason.CATEGORY_UNSUPPORTED, [])
            )
            continue
        sleeve, canonical_category = mapped
        eligible.append(
            _EligibleCandidate(
                index=index,
                candidate=candidate,
                screening=screening,
                sleeve=sleeve,
                category=canonical_category,
                category_provenance=provenance,
            )
        )
    return eligible, excluded, None


def _category_provenance(
    candidate: CandidateEvidence,
) -> tuple[str, ResearchField[Any]] | None:
    raw = candidate.metadata.get("field_provenance_json")
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise _CategoryConflict
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _CategoryConflict from exc
    if not isinstance(payload, dict):
        raise _CategoryConflict
    category_payload = payload.get("category")
    if category_payload is None:
        return None
    if not isinstance(category_payload, dict):
        raise _CategoryConflict
    try:
        provenance = ResearchField[Any].model_validate(category_payload)
    except ValidationError as exc:
        raise _CategoryConflict from exc
    expected_status = (
        "available" if provenance.missing_reason is None else provenance.missing_reason.value
    )
    if candidate.metadata.get("category_status") != expected_status:
        raise _CategoryConflict
    if provenance.missing_reason is not None:
        if candidate.category is not None or candidate.metadata.get("category") is not None:
            raise _CategoryConflict
        return None
    value = provenance.value
    if not isinstance(value, str) or not value.strip():
        raise _CategoryConflict
    flattened = candidate.metadata.get("category")
    if not isinstance(flattened, str):
        raise _CategoryConflict
    if (
        _normalize_category(flattened) != _normalize_category(value)
        or candidate.category is None
        or _normalize_category(candidate.category) != _normalize_category(value)
    ):
        raise _CategoryConflict
    return value, provenance


def _select_subset(
    eligible: list[_EligibleCandidate],
    targets: dict[PortfolioSleeve, int],
    policy: PortfolioConstructionPolicy,
) -> tuple[tuple[list[_EligibleCandidate], list[int]] | None, ConstructionReason]:
    required_sleeves = {sleeve for sleeve, target in targets.items() if target > 0}
    if not required_sleeves <= {item.sleeve for item in eligible}:
        return None, ConstructionReason.MISSING_SLEEVE_COVERAGE
    saw_covered = False
    saw_position_feasible = False
    maximum = min(policy.max_positions, len(eligible))
    for size in range(maximum, policy.min_positions - 1, -1):
        for indexes in combinations(range(len(eligible)), size):
            subset = [eligible[index] for index in indexes]
            if not required_sleeves <= {item.sleeve for item in subset}:
                continue
            saw_covered = True
            weights = _equal_sleeve_weights(subset, targets)
            if not all(
                policy.min_position_weight_bps <= weight <= policy.max_position_weight_bps
                for weight in weights
            ):
                continue
            saw_position_feasible = True
            category_totals: dict[str, int] = defaultdict(int)
            for item, weight in zip(subset, weights, strict=True):
                category_totals[_normalize_category(item.category)] += weight
            if any(total > policy.max_category_weight_bps for total in category_totals.values()):
                continue
            return (subset, weights), ConstructionReason.WEIGHT_RECONCILIATION_FAILED
    if not saw_covered:
        return None, ConstructionReason.MISSING_SLEEVE_COVERAGE
    if not saw_position_feasible:
        return None, ConstructionReason.POSITION_CONSTRAINTS_INFEASIBLE
    return None, ConstructionReason.CATEGORY_LIMIT_INFEASIBLE


def _equal_sleeve_weights(
    subset: list[_EligibleCandidate],
    targets: dict[PortfolioSleeve, int],
) -> list[int]:
    weights = [0] * len(subset)
    for sleeve in PortfolioSleeve:
        indexes = [index for index, item in enumerate(subset) if item.sleeve == sleeve]
        target = targets[sleeve]
        if not indexes:
            continue
        quotient, remainder = divmod(target, len(indexes))
        for offset, index in enumerate(indexes):
            weights[index] = quotient + (1 if offset < remainder else 0)
    return weights


def _policy_cash_cents(
    calculation: PolicyCalculation,
    field_name: Literal["initial_investment_usd", "recurring_monthly_usd"],
) -> tuple[dict[PortfolioSleeve, int], int]:
    cash = getattr(calculation, field_name)
    total = _exact_cents(cash.total_usd)
    by_sleeve = {
        PortfolioSleeve.GROWTH: _exact_cents(cash.growth_assets_usd),
        PortfolioSleeve.DEFENSIVE: _exact_cents(cash.defensive_assets_usd),
    }
    if sum(by_sleeve.values()) != total:
        raise ValueError("Policy cash sleeves do not reconcile.")
    return by_sleeve, total


def _exact_cents(value: float) -> int:
    cents = Decimal(str(value)) * Decimal(100)
    if cents != cents.to_integral_value() or cents < 0:
        raise ValueError("Policy cash must be an exact non-negative cent amount.")
    return int(cents)


def _allocate_all_cash(
    subset: list[_EligibleCandidate],
    weights: list[int],
    cash_by_sleeve: dict[PortfolioSleeve, int],
) -> list[int]:
    allocations = [0] * len(subset)
    for sleeve in PortfolioSleeve:
        indexes = [index for index, item in enumerate(subset) if item.sleeve == sleeve]
        if not indexes:
            if cash_by_sleeve[sleeve] != 0:
                raise ValueError("Non-zero cash sleeve has no positions.")
            continue
        sleeve_weight = sum(weights[index] for index in indexes)
        if sleeve_weight <= 0:
            raise ValueError("Cash cannot be allocated over a zero-weight sleeve.")
        total_cents = cash_by_sleeve[sleeve]
        remainders: list[tuple[int, int]] = []
        allocated = 0
        for index in indexes:
            quotient, remainder = divmod(total_cents * weights[index], sleeve_weight)
            allocations[index] = quotient
            allocated += quotient
            remainders.append((remainder, index))
        for _, index in sorted(remainders, key=lambda item: (-item[0], item[1]))[
            : total_cents - allocated
        ]:
            allocations[index] += 1
    if sum(allocations) != sum(cash_by_sleeve.values()):
        raise ValueError("Cash allocations do not reconcile.")
    return allocations


def _position_from_candidate(
    item: _EligibleCandidate,
    weight_bps: int,
    initial_cents: int,
    recurring_cents: int,
) -> PortfolioPosition:
    provenance = item.category_provenance
    return PortfolioPosition(
        document_id=item.candidate.document_id,
        symbol=item.candidate.symbol,
        name=item.candidate.name,
        source=provenance.provider,
        source_url=provenance.source_url,
        observed_at=provenance.observed_at,
        sleeve=item.sleeve,
        source_category=item.category,
        weight_bps=weight_bps,
        initial_usd_cents=initial_cents,
        recurring_usd_cents=recurring_cents,
        reason_code=(
            "supports_growth_target"
            if item.sleeve == PortfolioSleeve.GROWTH
            else "supports_defensive_target"
        ),
        policy_reference=(
            "policy.target_allocation.growth_assets_pct"
            if item.sleeve == PortfolioSleeve.GROWTH
            else "policy.target_allocation.defensive_assets_pct"
        ),
        screening_reason_codes=[rule.reason_code.value for rule in item.screening.rules],
    )


def _validate_cash_allocations(
    inputs: PortfolioConstructionInput,
    draft: PortfolioDraft,
    *,
    recurring: bool,
) -> bool:
    try:
        field_name: Literal["initial_investment_usd", "recurring_monthly_usd"] = (
            "recurring_monthly_usd" if recurring else "initial_investment_usd"
        )
        expected_by_sleeve, expected_total = _policy_cash_cents(
            inputs.policy_calculation, field_name
        )
        subset: list[_EligibleCandidate] = []
        weights: list[int] = []
        eligible, _, error = _classify_candidates(inputs, inputs.construction_policy)
        if error is not None:
            return False
        eligible_by_id = {item.candidate.document_id: item for item in eligible}
        for position in draft.positions:
            item = eligible_by_id.get(position.document_id)
            if item is None:
                return False
            subset.append(item)
            weights.append(position.weight_bps)
        expected = _allocate_all_cash(subset, weights, expected_by_sleeve)
        actual = [
            position.recurring_usd_cents if recurring else position.initial_usd_cents
            for position in draft.positions
        ]
        reported_total = draft.recurring_total_cents if recurring else draft.initial_total_cents
        return actual == expected and sum(actual) == expected_total == reported_total
    except (KeyError, TypeError, ValueError):
        return False


def _excluded(
    candidate: CandidateEvidence,
    screening: CandidateScreeningResult,
    reason: ConstructionReason,
    screening_reasons: list[str],
) -> ExcludedCandidate:
    return ExcludedCandidate(
        document_id=candidate.document_id,
        symbol=candidate.symbol,
        name=candidate.name,
        reason_code=reason,
        screening_verdict=screening.verdict,
        screening_reason_codes=screening_reasons,
    )


def _validation_result(
    outcomes: dict[ConstructionCheckName, bool],
) -> PortfolioValidationResult:
    checks = [
        ConstructionValidationCheck(
            name=name,
            passed=outcomes.get(name, False),
            reason_code=None if outcomes.get(name, False) else _reason_for_check(name),
            message=(
                f"{name.value.replace('_', ' ').capitalize()} passed."
                if outcomes.get(name, False)
                else f"{name.value.replace('_', ' ').capitalize()} failed."
            ),
        )
        for name in ConstructionCheckName
    ]
    return PortfolioValidationResult(valid=all(check.passed for check in checks), checks=checks)


def _reason_for_check(name: ConstructionCheckName) -> ConstructionReason:
    return {
        ConstructionCheckName.UPSTREAM_CONSISTENCY: ConstructionReason.UPSTREAM_CONTRACT_MISMATCH,
        ConstructionCheckName.ALLOCATION_BAND_CONSISTENCY: (
            ConstructionReason.ALLOCATION_BAND_MISMATCH
        ),
        ConstructionCheckName.ELIGIBILITY: ConstructionReason.CANDIDATE_SCREENING_UNKNOWN,
        ConstructionCheckName.SLEEVE_COVERAGE: ConstructionReason.MISSING_SLEEVE_COVERAGE,
        ConstructionCheckName.POSITION_COUNT: ConstructionReason.POSITION_CONSTRAINTS_INFEASIBLE,
        ConstructionCheckName.POSITION_WEIGHTS: ConstructionReason.POSITION_CONSTRAINTS_INFEASIBLE,
        ConstructionCheckName.CATEGORY_CONCENTRATION: (
            ConstructionReason.CATEGORY_LIMIT_INFEASIBLE
        ),
        ConstructionCheckName.WEIGHT_TOTAL: ConstructionReason.WEIGHT_RECONCILIATION_FAILED,
        ConstructionCheckName.SLEEVE_TOTALS: ConstructionReason.WEIGHT_RECONCILIATION_FAILED,
        ConstructionCheckName.INITIAL_CASH: ConstructionReason.CASH_RECONCILIATION_FAILED,
        ConstructionCheckName.RECURRING_CASH: ConstructionReason.CASH_RECONCILIATION_FAILED,
        ConstructionCheckName.SOURCE_ATTRIBUTION: (ConstructionReason.UPSTREAM_CONTRACT_MISMATCH),
        ConstructionCheckName.PERSISTED_RECOMPUTATION: (
            ConstructionReason.PERSISTED_CONSTRUCTION_MISMATCH
        ),
    }[name]


def _blocked_bundle(
    policy: PortfolioConstructionPolicy,
    reason: ConstructionReason,
    excluded: list[ExcludedCandidate] | None = None,
    *,
    passed_checks: set[ConstructionCheckName] | None = None,
    validation: PortfolioValidationResult | None = None,
) -> PortfolioConstructionBundle:
    if validation is None:
        passed = passed_checks or set()
        validation = _validation_result({name: name in passed for name in ConstructionCheckName})
    return PortfolioConstructionBundle(
        status="blocked",
        policy=policy,
        draft=None,
        validation=validation,
        excluded_candidates=list(excluded or []),
        errors=[ConstructionError(code=reason, message=_error_message(reason))],
    )


def _error_message(reason: ConstructionReason) -> str:
    messages = {
        ConstructionReason.CATEGORY_PROVENANCE_CONFLICT: (
            "Candidate category provenance conflicts with flattened source evidence."
        ),
        ConstructionReason.UPSTREAM_CONTRACT_MISMATCH: (
            "Portfolio construction inputs do not match their validated upstream contracts."
        ),
        ConstructionReason.EVIDENCE_NOT_READY: "Portfolio construction requires ready evidence.",
        ConstructionReason.SCREENING_RECOMPUTATION_MISMATCH: (
            "Persisted screening differs from deterministic recomputation."
        ),
        ConstructionReason.MISSING_SLEEVE_COVERAGE: (
            "Eligible candidates do not cover every non-zero policy sleeve."
        ),
        ConstructionReason.INSUFFICIENT_ELIGIBLE_CANDIDATES: (
            "Too few eligible candidates remain for the configured position minimum."
        ),
        ConstructionReason.POSITION_CONSTRAINTS_INFEASIBLE: (
            "No candidate subset satisfies the configured position bounds."
        ),
        ConstructionReason.CATEGORY_LIMIT_INFEASIBLE: (
            "No candidate subset satisfies the configured category limit."
        ),
        ConstructionReason.ALLOCATION_BAND_MISMATCH: (
            "The exact policy target does not match its checkpointed allocation bands."
        ),
        ConstructionReason.ALLOCATION_PRECISION_UNSUPPORTED: (
            "The policy target is not supported at one-basis-point precision."
        ),
        ConstructionReason.WEIGHT_RECONCILIATION_FAILED: (
            "Portfolio weights or sleeve totals do not reconcile exactly."
        ),
        ConstructionReason.CASH_RECONCILIATION_FAILED: (
            "Portfolio cash allocations do not reconcile exactly."
        ),
        ConstructionReason.PERSISTED_CONSTRUCTION_MISMATCH: (
            "Persisted construction differs from deterministic recomputation."
        ),
        ConstructionReason.CANDIDATE_SCREENING_FAILED: "Candidate screening failed.",
        ConstructionReason.CANDIDATE_SCREENING_UNKNOWN: "Candidate screening is unresolved.",
        ConstructionReason.CATEGORY_MISSING: "Candidate category evidence is missing.",
        ConstructionReason.CATEGORY_UNSUPPORTED: "Candidate category is unsupported.",
    }
    return messages[reason]
