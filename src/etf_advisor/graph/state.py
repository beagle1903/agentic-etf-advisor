"""JSON-serializable state for the advisory workflow."""

from typing import Any, TypedDict


class AdvisorState(TypedDict, total=False):
    revision_ledger: dict[str, Any]
    revision_digest: str
    revision_errors: list[dict[str, Any]]
    retry_request: dict[str, Any]
    retry_operation_id: str
    next_stage: str
    profile: dict[str, Any]
    validation_errors: list[dict[str, Any]]
    draft_policy: dict[str, Any]
    candidate_evidence: dict[str, Any]
    evidence_errors: list[dict[str, Any]]
    candidate_screening: dict[str, Any]
    screening_errors: list[dict[str, Any]]
    portfolio_construction: dict[str, Any]
    construction_errors: list[dict[str, Any]]
    draft_explanation: dict[str, Any]
    explanation_errors: list[dict[str, Any]]
    review_decision: dict[str, Any]
    status: str
    final_message: str
