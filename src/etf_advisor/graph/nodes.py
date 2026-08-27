"""Pure and interrupting nodes used by the first advisory graph."""

from typing import Any

from langgraph.types import interrupt
from pydantic import ValidationError

from etf_advisor.domain.profile import InvestorProfile, RiskTolerance
from etf_advisor.graph.state import AdvisorState

POLICY_BANDS: dict[RiskTolerance, dict[str, list[int]]] = {
    RiskTolerance.CONSERVATIVE: {
        "growth_assets_pct": [20, 45],
        "defensive_assets_pct": [55, 80],
    },
    RiskTolerance.MODERATE: {
        "growth_assets_pct": [45, 70],
        "defensive_assets_pct": [30, 55],
    },
    RiskTolerance.AGGRESSIVE: {
        "growth_assets_pct": [70, 95],
        "defensive_assets_pct": [5, 30],
    },
}


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
    bands = POLICY_BANDS[profile.risk_tolerance]

    draft: dict[str, Any] = {
        "objective": profile.objective.value,
        "horizon_years": profile.horizon_years,
        "risk_tolerance": profile.risk_tolerance.value,
        "allocation_bands": bands,
        "excluded_sectors": profile.excluded_sectors,
        "notes": [
            "These are policy ranges, not ETF recommendations.",
            "Live data, source retrieval, fees, liquidity, and tax context are not yet applied.",
        ],
    }
    return {"draft_policy": draft, "status": "awaiting_human_review"}


def request_human_review(state: AdvisorState) -> AdvisorState:
    """Pause durably so a person can approve, edit, or reject the draft."""

    decision = interrupt(
        {
            "kind": "portfolio_policy_review",
            "question": "Approve this policy draft before finalization?",
            "allowed_actions": ["approve", "edit", "reject"],
            "draft_policy": state["draft_policy"],
        }
    )
    if not isinstance(decision, dict):
        decision = {"action": "reject", "feedback": "Review response must be an object."}
    return {"review_decision": decision}


def finalize_review(state: AdvisorState) -> AdvisorState:
    """Finalize only an explicit approval; all other responses require revision."""

    decision = state.get("review_decision", {})
    action = decision.get("action")
    if action == "approve":
        return {
            "status": "approved",
            "final_message": (
                "Policy draft approved for the next research stage. "
                "No ETF recommendation or trade has been produced."
            ),
        }

    feedback = decision.get("feedback", "The reviewer did not approve the draft.")
    return {
        "status": "needs_revision",
        "final_message": str(feedback),
    }
