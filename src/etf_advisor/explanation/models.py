"""Typed contracts for generated, source-grounded review explanations."""

from __future__ import annotations

import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Final, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from etf_advisor.domain.construction import (
    PortfolioConstructionBundle,
    PortfolioConstructionInput,
    validate_persisted_construction,
)
from etf_advisor.domain.policy import PolicyCalculation, calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import CandidateScreeningBundle
from etf_advisor.rag.evidence import CandidateEvidence, CandidateEvidenceBundle, EvidenceStatus

MAX_EXPLANATION_CANDIDATES = 10

_PROHIBITED_CLAIM_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    (
        "guaranteed_outcome",
        re.compile(
            r"\b(?:guarantee(?:d|s)?|assur(?:e|ed|es)|certain(?:ly)?)\b.{0,80}"
            r"\b(?:return|returns|profit|profits|gain|gains|income|outperform(?:ance)?)\b"
        ),
    ),
    (
        "guaranteed_outcome",
        re.compile(
            r"\b(?:return|returns|profit|profits|gain|gains|income|outperformance)\b"
            r".{0,80}\b(?:is|are|will be)\s+(?:guaranteed|assured|certain)\b"
        ),
    ),
    (
        "personalized_trade_instruction",
        re.compile(
            r"\b(?:you|investors?|the user|this investor)\s+"
            r"(?:should|must|need(?:s)? to|ought to)\s+"
            r"(?:buy|sell|purchase|hold|trade|invest in|allocate(?: funds)? to)\b"
        ),
    ),
    (
        "imperative_trade_instruction",
        re.compile(
            r"(?:^|[.!?]\s+)(?:buy|sell|purchase|hold|trade|invest in|"
            r"allocate(?: funds)? to)\b"
        ),
    ),
    (
        "recommendation_or_suitability",
        re.compile(
            r"\b(?:(?:i|we|this explanation|the system)\s+"
            r"(?:recommend|advise|endorse)|(?:is|are)\s+(?:suitable|appropriate)\s+"
            r"for\s+(?:you|the user|this investor))\b"
        ),
    ),
    (
        "forecast",
        re.compile(
            r"\b(?:will(?!\s+not\b)|is expected to|are expected to|is projected to|"
            r"are projected to)\b.{0,80}\b(?:return|gain|rise|fall|outperform|underperform|"
            r"yield)\b"
        ),
    ),
    (
        "risk_free_outcome",
        re.compile(r"\b(?:risk[- ]free|can(?:not|'t) lose|no downside risk)\b"),
    ),
)

_NUMERIC_CLAIM_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])[+-]?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?|[.,]\d+)%?"
)
_NON_SUPPORT_METADATA_FIELDS: Final[frozenset[str]] = frozenset(
    {"source", "source_url", "observed_at"}
)


class ProviderFailureCode(StrEnum):
    """Stable, non-secret categories for provider troubleshooting."""

    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    INVALID_RESPONSE = "invalid_response"
    UNAVAILABLE = "unavailable"
    PROVIDER_ERROR = "provider_error"


class ExplanationContractFailureCode(StrEnum):
    """Stable, non-secret categories for local explanation validation failures."""

    PROHIBITED_CLAIM = "prohibited_claim"
    UNKNOWN_POLICY_REFERENCE = "unknown_policy_reference"
    UNKNOWN_CONSTRUCTION_REFERENCE = "unknown_construction_reference"
    UNKNOWN_SOURCE_REFERENCE = "unknown_source_reference"
    SUBJECT_MISMATCH = "subject_mismatch"
    UNSUPPORTED_NUMERIC_CLAIM = "unsupported_numeric_claim"
    CONTRACT_VALIDATION_ERROR = "contract_validation_error"


class ExplanationContractError(ValueError):
    """Raised when generated content fails one deterministic local contract rule."""

    def __init__(self, code: ExplanationContractFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ProviderFailureDiagnostic(BaseModel):
    """Redacted provider failure details safe for graph state and local presentation."""

    model_config = ConfigDict(extra="forbid")

    code: ProviderFailureCode
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=200)
    method: str = Field(min_length=1, max_length=80)
    http_status: int | None = Field(default=None, ge=100, le=599)


class ExplanationGenerationError(RuntimeError):
    """Raised when a provider cannot return a valid structured explanation."""

    def __init__(
        self,
        message: str,
        *,
        diagnostic: ProviderFailureDiagnostic | None = None,
    ) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic


class GroundingBasis(StrEnum):
    POLICY = "policy_calculation"
    CONSTRUCTION = "portfolio_construction"
    SOURCE = "source_evidence"


class GroundedStatement(BaseModel):
    """One generated statement with explicit, machine-checkable grounding references."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=1200)
    basis: GroundingBasis
    references: list[str] = Field(min_length=1, max_length=5)
    subject_symbols: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def validate_shape(self) -> GroundedStatement:
        if len(self.references) != len(set(self.references)):
            raise ValueError("Statement grounding references must be unique.")
        normalized_symbols = [symbol.strip().upper() for symbol in self.subject_symbols]
        if any(not symbol for symbol in normalized_symbols):
            raise ValueError("Statement subject symbols must not be empty.")
        if len(normalized_symbols) != len(set(normalized_symbols)):
            raise ValueError("Statement subject symbols must be unique.")
        self.subject_symbols = normalized_symbols
        if self.basis == GroundingBasis.POLICY and self.subject_symbols:
            raise ValueError("Policy statements cannot claim ETF subjects.")
        if self.basis == GroundingBasis.SOURCE and not self.subject_symbols:
            raise ValueError("Source-evidence statements must identify their ETF subjects.")
        return self


class GeneratedExplanation(BaseModel):
    """Structured provider output before deterministic grounding validation."""

    model_config = ConfigDict(extra="forbid")

    summary: GroundedStatement
    policy_points: list[GroundedStatement] = Field(min_length=1, max_length=6)
    evidence_points: list[GroundedStatement] = Field(min_length=1, max_length=10)
    tradeoffs: list[GroundedStatement] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_section_basis(self) -> GeneratedExplanation:
        if self.summary.basis != GroundingBasis.POLICY:
            raise ValueError("The explanation summary must be grounded in policy calculation.")
        if any(point.basis != GroundingBasis.POLICY for point in self.policy_points):
            raise ValueError("Policy points must use policy-calculation grounding.")
        if any(point.basis != GroundingBasis.SOURCE for point in self.evidence_points):
            raise ValueError("Evidence points must use source-evidence grounding.")
        return self


class ExplanationRequest(BaseModel):
    """Validated inputs exposed to an explanation generator."""

    model_config = ConfigDict(extra="forbid")

    profile: InvestorProfile
    draft_policy: PolicyCalculation
    candidate_evidence: CandidateEvidenceBundle
    candidate_screening: CandidateScreeningBundle
    portfolio_construction: PortfolioConstructionBundle
    revision_instruction: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_consistency(self) -> ExplanationRequest:
        if self.candidate_evidence.status != EvidenceStatus.READY:
            raise ValueError("Explanation generation requires ready source evidence.")
        if self.draft_policy != calculate_policy(self.profile):
            raise ValueError("Policy calculation does not match the validated profile.")
        if self.profile.objective != self.draft_policy.objective:
            raise ValueError("Policy objective does not match the validated profile.")
        if self.profile.risk_tolerance != self.draft_policy.risk_tolerance:
            raise ValueError("Policy risk tolerance does not match the validated profile.")
        if self.profile.excluded_sectors != self.draft_policy.excluded_sectors:
            raise ValueError("Policy exclusions do not match the validated profile.")
        if self.profile.objective != self.candidate_evidence.objective:
            raise ValueError("Evidence objective does not match the validated profile.")
        if self.profile.risk_tolerance != self.candidate_evidence.risk_tolerance:
            raise ValueError("Evidence risk tolerance does not match the validated profile.")
        if self.profile.excluded_sectors != self.candidate_evidence.excluded_sectors:
            raise ValueError("Evidence exclusions do not match the validated profile.")
        recomputed = validate_persisted_construction(
            PortfolioConstructionInput(
                profile=self.profile,
                policy_calculation=self.draft_policy,
                candidate_evidence=self.candidate_evidence,
                candidate_screening=self.candidate_screening,
                construction_policy=self.portfolio_construction.policy,
            ),
            self.portfolio_construction,
        )
        if recomputed.status != "ready":
            raise ValueError(
                "Explanation generation requires deterministically revalidated portfolio "
                "construction."
            )
        self.portfolio_construction = recomputed
        return self


class ExplanationResult(BaseModel):
    """Structured explanation plus provider identity supplied by the adapter."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=200)
    explanation: GeneratedExplanation


class ExplanationCitation(BaseModel):
    """A deterministic citation copied from validated candidate evidence."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    symbol: str
    source: str
    source_url: str
    observed_at: str


class ExplanationBundle(BaseModel):
    """Review-ready explanation after deterministic grounding validation."""

    model_config = ConfigDict(extra="forbid")

    status: str = "ready"
    provider: str
    model: str
    explanation: GeneratedExplanation
    citations: list[ExplanationCitation]
    limitations: list[str]

    @model_validator(mode="after")
    def validate_ready_bundle(self) -> ExplanationBundle:
        if self.status != "ready":
            raise ValueError("A review explanation bundle must be ready.")
        cited_ids = {citation.document_id for citation in self.citations}
        referenced_ids = {
            reference
            for statement in _all_statements(self.explanation)
            if statement.basis == GroundingBasis.SOURCE
            for reference in statement.references
        }
        if cited_ids != referenced_ids:
            raise ValueError("Explanation citations must exactly match source references.")
        return self


class ExplanationGenerator(Protocol):
    """Replaceable side-effect boundary for provider-backed explanation generation."""

    def generate(self, request: ExplanationRequest) -> ExplanationResult: ...


def build_explanation_request(
    *,
    profile: dict[str, object],
    draft_policy: dict[str, object],
    candidate_evidence: dict[str, object],
    candidate_screening: dict[str, object],
    portfolio_construction: dict[str, object],
) -> ExplanationRequest:
    """Revalidate graph state before exposing it to a model provider."""

    return ExplanationRequest(
        profile=InvestorProfile.model_validate(profile),
        draft_policy=PolicyCalculation.model_validate(draft_policy),
        candidate_evidence=CandidateEvidenceBundle.model_validate(candidate_evidence),
        candidate_screening=CandidateScreeningBundle.model_validate(candidate_screening),
        portfolio_construction=PortfolioConstructionBundle.model_validate(portfolio_construction),
    )


def policy_reference_index(request: ExplanationRequest) -> dict[str, object]:
    """Return the only deterministic policy fields a generated statement may cite."""

    profile = request.profile
    policy = request.draft_policy
    return {
        "profile.horizon_years": profile.horizon_years,
        "profile.max_drawdown_pct": profile.max_drawdown_pct,
        "profile.objective": profile.objective.value,
        "profile.risk_tolerance": profile.risk_tolerance.value,
        "profile.excluded_sectors": list(profile.excluded_sectors),
        "policy.allocation_bands": policy.allocation_bands,
        "policy.target_allocation": policy.target_allocation.model_dump(mode="json"),
        "policy.initial_investment_usd": policy.initial_investment_usd.model_dump(mode="json"),
        "policy.recurring_monthly_usd": policy.recurring_monthly_usd.model_dump(mode="json"),
        "policy.notes": list(policy.notes),
    }


def exposed_candidates(request: ExplanationRequest) -> list[CandidateEvidence]:
    """Expose only candidates selected by the revalidated portfolio, in draft order."""

    draft = request.portfolio_construction.draft
    if draft is None:  # Defensive after request validation.
        return []
    candidates = {
        candidate.document_id: candidate for candidate in request.candidate_evidence.candidates
    }
    return [
        candidates[position.document_id]
        for position in draft.positions[:MAX_EXPLANATION_CANDIDATES]
    ]


def portfolio_reference_index(request: ExplanationRequest) -> dict[str, object]:
    """Return the only revalidated construction fields generated text may cite."""

    construction = request.portfolio_construction
    draft = construction.draft
    if draft is None:  # Defensive after request validation.
        return {}
    position_refs = {
        f"portfolio.positions.{index}": {
            "document_id": position.document_id,
            "symbol": position.symbol,
            "sleeve": position.sleeve.value,
            "source_category": position.source_category,
            "weight_bps": position.weight_bps,
            "weight_pct": str(Decimal(position.weight_bps) / Decimal(100)),
            "initial_usd_cents": position.initial_usd_cents,
            "initial_usd": str(Decimal(position.initial_usd_cents) / Decimal(100)),
            "recurring_usd_cents": position.recurring_usd_cents,
            "recurring_usd": str(Decimal(position.recurring_usd_cents) / Decimal(100)),
            "reason_code": position.reason_code,
            "policy_reference": position.policy_reference,
            "screening_reason_codes": list(position.screening_reason_codes),
        }
        for index, position in enumerate(draft.positions)
    }
    return {
        "portfolio.totals": {
            "total_weight_bps": draft.total_weight_bps,
            "total_weight_pct": str(Decimal(draft.total_weight_bps) / Decimal(100)),
            "sleeve_weight_bps": {
                sleeve.value: value for sleeve, value in draft.sleeve_weight_bps.items()
            },
            "initial_total_cents": draft.initial_total_cents,
            "initial_total_usd": str(Decimal(draft.initial_total_cents) / Decimal(100)),
            "recurring_total_cents": draft.recurring_total_cents,
            "recurring_total_usd": str(Decimal(draft.recurring_total_cents) / Decimal(100)),
        },
        "portfolio.constraints": construction.policy.model_dump(mode="json"),
        **position_refs,
    }


def validate_and_bundle_explanation(
    request: ExplanationRequest,
    result: ExplanationResult,
) -> ExplanationBundle:
    """Reject references not present in the exact policy/evidence input."""

    validated = ExplanationResult.model_validate(result.model_dump(mode="python"))
    _validate_prohibited_claims(validated.explanation)
    policy_refs = set(policy_reference_index(request))
    construction_refs = portfolio_reference_index(request)
    source_by_id = {candidate.document_id: candidate for candidate in exposed_candidates(request)}

    for statement in _all_statements(validated.explanation):
        if statement.basis == GroundingBasis.POLICY:
            unknown = set(statement.references) - policy_refs
            if unknown:
                raise ExplanationContractError(
                    ExplanationContractFailureCode.UNKNOWN_POLICY_REFERENCE,
                    "Policy statement contains an unknown grounding reference.",
                )
            continue

        if statement.basis == GroundingBasis.CONSTRUCTION:
            unknown = set(statement.references) - set(construction_refs)
            if unknown:
                raise ExplanationContractError(
                    ExplanationContractFailureCode.UNKNOWN_CONSTRUCTION_REFERENCE,
                    "Portfolio statement contains an unknown construction reference.",
                )
            expected_symbols = {
                symbol
                for reference in statement.references
                for symbol in _construction_reference_symbols(construction_refs[reference])
            }
            if set(statement.subject_symbols) != expected_symbols:
                raise ExplanationContractError(
                    ExplanationContractFailureCode.SUBJECT_MISMATCH,
                    "Portfolio statement subjects do not match its construction references.",
                )
            continue

        unknown = set(statement.references) - set(source_by_id)
        if unknown:
            raise ExplanationContractError(
                ExplanationContractFailureCode.UNKNOWN_SOURCE_REFERENCE,
                "Evidence statement contains an unknown source reference.",
            )
        cited_symbols = {source_by_id[reference].symbol for reference in statement.references}
        if set(statement.subject_symbols) != cited_symbols:
            raise ExplanationContractError(
                ExplanationContractFailureCode.SUBJECT_MISMATCH,
                "Evidence statement subjects do not match its cited sources.",
            )

    _validate_numeric_claim_support(request, validated.explanation, source_by_id)

    referenced_ids = {
        reference
        for statement in _all_statements(validated.explanation)
        if statement.basis == GroundingBasis.SOURCE
        for reference in statement.references
    }
    citations = [
        ExplanationCitation(
            document_id=candidate.document_id,
            symbol=candidate.symbol,
            source=candidate.source,
            source_url=candidate.source_url,
            observed_at=candidate.observed_at.isoformat(),
        )
        for candidate in exposed_candidates(request)
        if candidate.document_id in referenced_ids
    ]
    limitations = [
        "This is an educational explanation of an illustrative policy, not personalized advice.",
        "Retrieved ETF facts may be delayed, incomplete, or incorrect; review each cited source.",
        (
            "The explanation does not forecast returns or drawdowns, select an allocation, "
            "or execute trades."
        ),
    ]
    if request.profile.excluded_sectors:
        limitations.append(
            "Sector exclusion results are provided separately by deterministic screening; "
            "this explanation does not replace or extend those results."
        )
    return ExplanationBundle(
        provider=validated.provider,
        model=validated.model,
        explanation=validated.explanation,
        citations=citations,
        limitations=limitations,
    )


def _all_statements(explanation: GeneratedExplanation) -> list[GroundedStatement]:
    return [
        explanation.summary,
        *explanation.policy_points,
        *explanation.evidence_points,
        *explanation.tradeoffs,
    ]


def _validate_prohibited_claims(explanation: GeneratedExplanation) -> None:
    violations: list[str] = []
    for statement in _all_statements(explanation):
        normalized = " ".join(unicodedata.normalize("NFKC", statement.text).casefold().split())
        for name, pattern in _PROHIBITED_CLAIM_PATTERNS:
            if pattern.search(normalized):
                violations.append(name)
    if violations:
        categories = ", ".join(dict.fromkeys(violations))
        raise ExplanationContractError(
            ExplanationContractFailureCode.PROHIBITED_CLAIM,
            f"Generated explanation contains prohibited financial claims: {categories}.",
        )


def _validate_numeric_claim_support(
    request: ExplanationRequest,
    explanation: GeneratedExplanation,
    source_by_id: dict[str, CandidateEvidence],
) -> None:
    policy_refs = policy_reference_index(request)
    construction_refs = portfolio_reference_index(request)
    for statement in _all_statements(explanation):
        claimed_numbers = _numeric_tokens(statement.text)
        if not claimed_numbers:
            continue
        if statement.basis == GroundingBasis.POLICY:
            support_text = " ".join(
                json.dumps(policy_refs[reference], sort_keys=True)
                for reference in statement.references
            )
        elif statement.basis == GroundingBasis.CONSTRUCTION:
            support_text = " ".join(
                json.dumps(construction_refs[reference], sort_keys=True)
                for reference in statement.references
            )
        else:
            support_text = " ".join(
                _candidate_support_text(source_by_id[reference])
                for reference in statement.references
            )
        unsupported = claimed_numbers - _numeric_tokens(support_text)
        if unsupported:
            raise ExplanationContractError(
                ExplanationContractFailureCode.UNSUPPORTED_NUMERIC_CLAIM,
                "Generated explanation contains a numeric claim absent from its cited support.",
            )


def _construction_reference_symbols(value: object) -> set[str]:
    if not isinstance(value, dict):
        return set()
    symbol = value.get("symbol")
    return {symbol} if isinstance(symbol, str) and symbol else set()


def _candidate_support_text(candidate: CandidateEvidence) -> str:
    metadata = {
        key: value
        for key, value in candidate.metadata.items()
        if key not in _NON_SUPPORT_METADATA_FIELDS
    }
    return " ".join(
        (
            candidate.symbol,
            candidate.name or "",
            candidate.content,
            candidate.fund_family or "",
            candidate.category or "",
            (
                json.dumps(candidate.graph_context.model_dump(mode="json"), sort_keys=True)
                if candidate.graph_context is not None
                else ""
            ),
            json.dumps(metadata, sort_keys=True, default=str),
        )
    )


def _numeric_tokens(text: str) -> set[str]:
    normalized: set[str] = set()
    for raw in _NUMERIC_CLAIM_PATTERN.findall(text):
        try:
            number = raw.removesuffix("%")
            if "," in number and "." in number:
                number = number.replace(",", "")
            elif "," in number:
                parts = number.split(",")
                integer = parts[0]
                number = (
                    number.replace(",", "")
                    if len(parts) > 2 or (len(parts[-1]) == 3 and integer.lstrip("+-") != "0")
                    else number.replace(",", ".")
                )
            value = Decimal(number).normalize()
        except InvalidOperation:
            continue
        normalized.add(str(value))
    return normalized
