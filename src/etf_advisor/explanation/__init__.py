"""Source-grounded explanation contracts and provider adapters."""

from etf_advisor.explanation.models import (
    ExplanationBundle,
    ExplanationGenerationError,
    ExplanationGenerator,
    ExplanationRequest,
    ExplanationResult,
    GeneratedExplanation,
    GroundedStatement,
    GroundingBasis,
    build_explanation_request,
    validate_and_bundle_explanation,
)

__all__ = [
    "ExplanationBundle",
    "ExplanationGenerationError",
    "ExplanationGenerator",
    "ExplanationRequest",
    "ExplanationResult",
    "GeneratedExplanation",
    "GroundedStatement",
    "GroundingBasis",
    "build_explanation_request",
    "validate_and_bundle_explanation",
]
