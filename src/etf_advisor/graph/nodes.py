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
            "draft_policy": {},
            "candidate_evidence": {},
            "evidence_errors": [],
            "review_decision": {},
            "status": "invalid_profile",
            "final_message": "",
        }

    return {
        "profile": profile.model_dump(mode="json"),
        "validation_errors": [],
        "draft_policy": {},
        "candidate_evidence": {},
        "evidence_errors": [],
        "review_decision": {},
        "status": "profile_validated",
        "final_message": "",
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
            "candidate_evidence": {},
            "evidence_errors": [{"type": "retrieval_error", "message": str(exc)}],
            "status": "evidence_blocked",
        }

    payload = bundle.model_dump(mode="json")
    contract_errors: list[str] = []
    if bundle.objective != profile.objective:
        contract_errors.append("Evidence objective does not match the validated profile.")
    if bundle.risk_tolerance != profile.risk_tolerance:
        contract_errors.append("Evidence risk tolerance does not match the validated profile.")
    if bundle.excluded_sectors != profile.excluded_sectors:
        contract_errors.append("Evidence exclusions do not match the validated profile.")
    if bundle.requested_limit != limit:
        contract_errors.append("Evidence candidate limit does not match the workflow request.")
    if contract_errors:
        payload["status"] = EvidenceStatus.BLOCKED
        payload["errors"] = [*bundle.errors, *contract_errors]
        return {
            "candidate_evidence": payload,
            "evidence_errors": [
                {"type": "evidence_contract", "message": message} for message in contract_errors
            ],
            "status": "evidence_blocked",
        }
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

    candidate_evidence = state.get("candidate_evidence", {})
    has_ready_evidence = candidate_evidence.get("status") == EvidenceStatus.READY
    review_payload: dict[str, Any] = {
        "kind": "portfolio_policy_review",
        "question": (
            "Approve this policy draft and its source evidence before finalization?"
            if has_ready_evidence
            else "Approve this policy draft before finalization?"
        ),
        "allowed_actions": ["approve", "edit", "reject"],
        "draft_policy": state["draft_policy"],
    }
    if has_ready_evidence:
        review_payload["candidate_evidence"] = candidate_evidence
    decision = interrupt(review_payload)
    if not isinstance(decision, dict):
        decision = {"action": "reject", "feedback": "Review response must be an object."}
    return {"review_decision": decision, "status": "awaiting_human_review"}


def finalize_review(state: AdvisorState) -> AdvisorState:
    """Finalize only an explicit approval; all other responses require revision."""

    decision = state.get("review_decision", {})
    action = decision.get("action")
    if action == "approve":
        has_ready_evidence = (
            state.get("candidate_evidence", {}).get("status") == EvidenceStatus.READY
        )
        return {
            "status": "approved",
            "final_message": (
                (
                    "Policy draft and source evidence approved for the next research stage. "
                    if has_ready_evidence
                    else "Policy draft approved for the next research stage. "
                )
                + "No ETF recommendation or trade has been produced."
            ),
        }

    feedback = decision.get("feedback", "The reviewer did not approve the draft.")
    return {
        "status": "needs_revision",
        "final_message": str(feedback),
    }
