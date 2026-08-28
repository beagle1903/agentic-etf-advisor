"""Pure and interrupting nodes used by the advisory graph."""

from typing import Any

from langgraph.types import interrupt
from pydantic import ValidationError

from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.graph.state import AdvisorState
from etf_advisor.rag.evidence import (
    CandidateEvidenceRetriever,
    EvidenceRetrievalError,
    EvidenceStatus,
)


def validate_profile(state: AdvisorState) -> AdvisorState:
    """Validate and normalize untrusted profile input."""

    try:
        profile = InvestorProfile.model_validate(state.get("profile", {}))
    except ValidationError as exc:
        errors = [dict(error) for error in exc.errors(include_url=False)]
        return {
            "validation_errors": errors,
            "status": "invalid_profile",
        }

    return {
        "profile": profile.model_dump(mode="json"),
        "validation_errors": [],
        "status": "profile_validated",
    }


def draft_policy(state: AdvisorState) -> AdvisorState:
    """Create a deterministic policy draft before any ETF-level recommendation."""

    profile = InvestorProfile.model_validate(state["profile"])
    calculation = calculate_policy(profile)
    return {
        "draft_policy": calculation.model_dump(mode="json"),
        "status": "awaiting_human_review",
    }


def retrieve_candidate_evidence(
    state: AdvisorState,
    *,
    retriever: CandidateEvidenceRetriever,
    limit: int,
) -> AdvisorState:
    """Retrieve review evidence through an explicitly injected side-effect boundary."""

    profile = InvestorProfile.model_validate(state["profile"])
    try:
        bundle = retriever.retrieve(profile, limit=limit)
    except EvidenceRetrievalError as exc:
        return {
            "evidence_errors": [{"type": "retrieval_error", "message": str(exc)}],
            "status": "evidence_blocked",
        }

    payload = bundle.model_dump(mode="json")
    if bundle.status != EvidenceStatus.READY:
        return {
            "candidate_evidence": payload,
            "evidence_errors": [
                {"type": "evidence_guardrail", "message": message} for message in bundle.errors
            ],
            "status": "evidence_blocked",
        }
    return {
        "candidate_evidence": payload,
        "evidence_errors": [],
        "status": "awaiting_human_review",
    }


def request_human_review(state: AdvisorState) -> AdvisorState:
    """Pause durably so a person can approve, edit, or reject the draft."""

    review_payload: dict[str, Any] = {
        "kind": "portfolio_policy_review",
        "question": "Approve this policy draft and its source evidence before finalization?",
        "allowed_actions": ["approve", "edit", "reject"],
        "draft_policy": state["draft_policy"],
    }
    if "candidate_evidence" in state:
        review_payload["candidate_evidence"] = state["candidate_evidence"]
    decision = interrupt(review_payload)
    if not isinstance(decision, dict):
        decision = {"action": "reject", "feedback": "Review response must be an object."}
    return {"review_decision": decision, "status": "awaiting_human_review"}


def finalize_review(state: AdvisorState) -> AdvisorState:
    """Finalize only an explicit approval; all other responses require revision."""

    decision = state.get("review_decision", {})
    action = decision.get("action")
    if action == "approve":
        return {
            "status": "approved",
            "final_message": (
                "Policy draft and source evidence approved for the next research stage. "
                "No ETF recommendation or trade has been produced."
            ),
        }

    feedback = decision.get("feedback", "The reviewer did not approve the draft.")
    return {
        "status": "needs_revision",
        "final_message": str(feedback),
    }
