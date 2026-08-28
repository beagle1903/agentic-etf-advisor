"""Construction of the human-reviewed LangGraph workflow."""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from etf_advisor.graph.nodes import (
    draft_policy,
    finalize_review,
    request_human_review,
    retrieve_candidate_evidence,
    validate_profile,
)
from etf_advisor.graph.state import AdvisorState
from etf_advisor.rag.evidence import CandidateEvidenceRetriever


def route_after_validation(state: AdvisorState) -> Literal["draft_policy", "end"]:
    return "end" if state.get("validation_errors") else "draft_policy"


def build_graph(
    checkpointer: Any | None = None,
    *,
    candidate_retriever: CandidateEvidenceRetriever | None = None,
    candidate_limit: int = 5,
) -> Any:
    """Build the workflow with optional, explicitly injected source evidence."""

    if candidate_limit < 1 or candidate_limit > 50:
        raise ValueError("candidate_limit must be between 1 and 50.")

    builder = StateGraph(AdvisorState)
    builder.add_node("validate_profile", validate_profile)
    builder.add_node("draft_policy", draft_policy)
    if candidate_retriever is not None:
        builder.add_node(
            "retrieve_candidate_evidence",
            lambda state: retrieve_candidate_evidence(
                state,
                retriever=candidate_retriever,
                limit=candidate_limit,
            ),
        )
    builder.add_node("human_review", request_human_review)
    builder.add_node("finalize_review", finalize_review)

    builder.add_edge(START, "validate_profile")
    builder.add_conditional_edges(
        "validate_profile",
        route_after_validation,
        {"draft_policy": "draft_policy", "end": END},
    )
    if candidate_retriever is None:
        builder.add_edge("draft_policy", "human_review")
    else:
        builder.add_edge("draft_policy", "retrieve_candidate_evidence")
        builder.add_conditional_edges(
            "retrieve_candidate_evidence",
            route_after_evidence,
            {"human_review": "human_review", "end": END},
        )
    builder.add_edge("human_review", "finalize_review")
    builder.add_edge("finalize_review", END)

    return builder.compile(checkpointer=checkpointer)


def route_after_evidence(state: AdvisorState) -> Literal["human_review", "end"]:
    candidate_evidence = state.get("candidate_evidence", {})
    return "human_review" if candidate_evidence.get("status") == "ready" else "end"


graph = build_graph()
