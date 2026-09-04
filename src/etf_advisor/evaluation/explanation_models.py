"""JSON-serializable contracts for offline explanation evaluation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from etf_advisor.explanation.models import ExplanationRequest, ExplanationResult


class ExplanationEvaluationDimension(StrEnum):
    """Quality dimensions required in the first explanation baseline."""

    CITATION_VALIDITY = "citation_validity"
    CLAIM_SUPPORT = "claim_support"
    PORTFOLIO_CONSTRUCTION_GROUNDING = "portfolio_construction_grounding"
    SUBJECT_SOURCE_AGREEMENT = "subject_source_agreement"
    REFUSAL_BEHAVIOR = "refusal_behavior"
    UNSAFE_LANGUAGE = "unsafe_language"
    PROMPT_INJECTION_RESISTANCE = "prompt_injection_resistance"


class ExplanationEvaluationDecision(StrEnum):
    """Whether an output is allowed to reach human review."""

    ACCEPT = "accept"
    REJECT = "reject"


class ExplanationEvaluationCase(BaseModel):
    """One curated provider output and its expected fail-closed decision."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    dimensions: list[ExplanationEvaluationDimension] = Field(min_length=1)
    expected_decision: ExplanationEvaluationDecision
    expectation: str = Field(min_length=1)
    result: ExplanationResult | None = None
    provider_refusal: bool = False

    @model_validator(mode="after")
    def validate_case_shape(self) -> ExplanationEvaluationCase:
        if len(self.dimensions) != len(set(self.dimensions)):
            raise ValueError(f"Explanation case '{self.case_id}' has duplicate dimensions.")
        if (self.result is None) == (not self.provider_refusal):
            raise ValueError(
                "Explanation cases require exactly one provider result or provider refusal."
            )
        if self.provider_refusal and self.expected_decision != ExplanationEvaluationDecision.REJECT:
            raise ValueError("A provider refusal cannot be expected to reach human review.")
        return self


class ExplanationEvaluationDataset(BaseModel):
    """Versioned request plus curated outputs replayed through production validation."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    request: ExplanationRequest
    cases: list[ExplanationEvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dataset(self) -> ExplanationEvaluationDataset:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Explanation evaluation dataset has duplicate case IDs.")
        covered = {dimension for case in self.cases for dimension in case.dimensions}
        missing = set(ExplanationEvaluationDimension) - covered
        if missing:
            values = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"Explanation evaluation dataset is missing dimensions: {values}.")
        return self


class ExplanationDimensionScore(BaseModel):
    """Deterministic classification accuracy for one quality dimension."""

    case_count: int = Field(ge=1)
    correct_count: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=1)


class ExplanationEvaluationCaseResult(BaseModel):
    """Sanitized decision result for one curated case."""

    case_id: str
    dimensions: list[ExplanationEvaluationDimension]
    expected_decision: ExplanationEvaluationDecision
    actual_decision: ExplanationEvaluationDecision
    passed: bool
    reason: str


class ExplanationEvaluationMetrics(BaseModel):
    """Aggregate gate and required dimension scores."""

    case_count: int
    correct_count: int
    decision_accuracy: float
    citation_validity: ExplanationDimensionScore
    claim_support: ExplanationDimensionScore
    portfolio_construction_grounding: ExplanationDimensionScore
    subject_source_agreement: ExplanationDimensionScore
    refusal_behavior: ExplanationDimensionScore
    unsafe_language: ExplanationDimensionScore
    prompt_injection_resistance: ExplanationDimensionScore
    passed: bool


class ExplanationEvaluationReport(BaseModel):
    """Stable offline report with no provider, network, database, or clock dependency."""

    dataset_id: str
    version: int
    metrics: ExplanationEvaluationMetrics
    cases: list[ExplanationEvaluationCaseResult]
    conclusion: str
