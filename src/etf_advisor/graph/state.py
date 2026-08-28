"""JSON-serializable state for the advisory workflow."""

from typing import Any, TypedDict


class AdvisorState(TypedDict, total=False):
    profile: dict[str, Any]
    validation_errors: list[dict[str, Any]]
    draft_policy: dict[str, Any]
    candidate_evidence: dict[str, Any]
    evidence_errors: list[dict[str, Any]]
    draft_explanation: dict[str, Any]
    explanation_errors: list[dict[str, Any]]
    review_decision: dict[str, Any]
    status: str
    final_message: str
