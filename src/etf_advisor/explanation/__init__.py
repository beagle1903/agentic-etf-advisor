"""Source-grounded explanation contracts and provider adapters."""

from etf_advisor.explanation.models import (
    ExplanationBundle,
    ExplanationContractError,
    ExplanationContractFailureCode,
    ExplanationGenerationError,
    ExplanationGenerator,
    ExplanationRequest,
    ExplanationResult,
    GeneratedExplanation,
    GroundedStatement,
    GroundingBasis,
    ProviderFailureCode,
    ProviderFailureDiagnostic,
    build_explanation_request,
    validate_and_bundle_explanation,
)

__all__ = [
    "ExplanationBundle",
    "ExplanationContractError",
    "ExplanationContractFailureCode",
    "ExplanationGenerationError",
    "ExplanationGenerator",
    "ExplanationRequest",
    "ExplanationResult",
    "GeneratedExplanation",
    "GroundedStatement",
    "GroundingBasis",
    "ProviderFailureCode",
    "ProviderFailureDiagnostic",
    "build_explanation_request",
    "validate_and_bundle_explanation",
]
