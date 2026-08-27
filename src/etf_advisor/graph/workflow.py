"""Construction of the first human-reviewed LangGraph workflow."""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from etf_advisor.graph.nodes import (
    draft_policy,
    finalize_review,
    request_human_review,
    validate_profile,
)
from etf_advisor.graph.state import AdvisorState


def route_after_validation(state: AdvisorState) -> Literal["draft_policy", "end"]:
    return "end" if state.get("validation_errors") else "draft_policy"


def build_graph(checkpointer: Any | None = None) -> Any:
    """Build the workflow; inject a durable checkpointer outside managed runtimes."""

    builder = StateGraph(AdvisorState)
    builder.add_node("validate_profile", validate_profile)
    builder.add_node("draft_policy", draft_policy)
    builder.add_node("human_review", request_human_review)
    builder.add_node("finalize_review", finalize_review)

    builder.add_edge(START, "validate_profile")
    builder.add_conditional_edges(
        "validate_profile",
        route_after_validation,
        {"draft_policy": "draft_policy", "end": END},
    )
    builder.add_edge("draft_policy", "human_review")
    builder.add_edge("human_review", "finalize_review")
    builder.add_edge("finalize_review", END)

    return builder.compile(checkpointer=checkpointer)


graph = build_graph()
