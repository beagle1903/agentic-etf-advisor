"""Revision-aware human-reviewed LangGraph workflow."""

from collections.abc import Callable, Hashable
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph._internal._constants import CONFIG_KEY_DURABILITY
from langgraph.graph import END, START, StateGraph

from etf_advisor.clock import Clock, system_utc_now
from etf_advisor.domain.construction import DEFAULT_CONSTRUCTION_POLICY, PortfolioConstructionPolicy
from etf_advisor.domain.screening import DEFAULT_SCREENING_POLICY, CandidateScreeningPolicy
from etf_advisor.explanation import ExplanationGenerator
from etf_advisor.graph import nodes
from etf_advisor.graph.revision import (
    RevisionRuntime,
    _block,
    current_inputs,
    validate_revision_state,
)
from etf_advisor.graph.state import AdvisorState
from etf_advisor.rag.evidence import MAX_CANDIDATE_LIMIT, CandidateEvidenceRetriever


def route_after_validation(state: AdvisorState) -> Literal["draft_policy", "end"]:
    return "draft_policy" if state.get("status") == "profile_validated" else "end"


def build_graph(
    checkpointer: Any | None = None,
    *,
    candidate_retriever: CandidateEvidenceRetriever | None = None,
    candidate_limit: int = 5,
    explanation_generator: ExplanationGenerator | None = None,
    screening_policy: CandidateScreeningPolicy = DEFAULT_SCREENING_POLICY,
    construction_policy: PortfolioConstructionPolicy = DEFAULT_CONSTRUCTION_POLICY,
    clock: Clock = system_utc_now,
) -> Any:
    """Build pure revision routes with explicitly injected adapters and clock."""
    if candidate_limit < 1 or candidate_limit > MAX_CANDIDATE_LIMIT:
        raise ValueError(f"candidate_limit must be between 1 and {MAX_CANDIDATE_LIMIT}.")
    if explanation_generator is not None and candidate_retriever is None:
        raise ValueError("An explanation generator requires a candidate evidence retriever.")
    runtime = RevisionRuntime(
        clock=clock,
        inputs={
            "with_evidence": candidate_retriever is not None,
            "with_explanation": explanation_generator is not None,
            "candidate_limit": candidate_limit,
            "screening_policy": CandidateScreeningPolicy.model_validate(
                screening_policy.model_dump(mode="json")
            ).model_dump(mode="json"),
            "construction_policy": PortfolioConstructionPolicy.model_validate(
                construction_policy.model_dump(mode="json")
            ).model_dump(mode="json"),
            "explanation_instruction": "",
        },
    )

    def retrieve(state: AdvisorState) -> AdvisorState:
        if candidate_retriever is None:
            return {
                "status": "evidence_blocked",
                "candidate_evidence": {},
                "evidence_errors": [
                    {
                        "type": "adapter_unavailable",
                        "message": "Reattach the retrieval adapter to retry.",
                    }
                ],
            }
        return nodes.retrieve_candidate_evidence(
            state, retriever=candidate_retriever, limit=current_inputs(state)["candidate_limit"]
        )

    def explain(state: AdvisorState) -> AdvisorState:
        if explanation_generator is None:
            return {
                "status": "explanation_blocked",
                "draft_explanation": {},
                "explanation_errors": [
                    {
                        "type": "adapter_unavailable",
                        "message": "Reattach the provider adapter to retry.",
                    }
                ],
            }
        return nodes.draft_explanation(state, generator=explanation_generator)

    builder = StateGraph(AdvisorState)

    def guarded(function: Callable[[AdvisorState], AdvisorState]) -> Callable[..., AdvisorState]:
        def run(state: AdvisorState, config: RunnableConfig) -> AdvisorState:
            try:
                if config["configurable"].get(CONFIG_KEY_DURABILITY) != "sync":
                    raise ValueError("Revision operations require synchronous checkpoints.")
                validate_revision_state(state, str(config["configurable"]["thread_id"]))
            except (KeyError, TypeError, ValueError):
                return _block(state)
            return function(state)

        return run

    def add_node(name: str, function: Callable[[AdvisorState], AdvisorState]) -> None:
        builder.add_node(name, guarded(function))

    builder.add_node("begin_revision", runtime.begin)
    add_node("validate_profile", lambda state: runtime.pure(state, nodes.validate_profile))
    add_node("draft_policy", lambda state: runtime.pure(state, nodes.draft_policy))
    add_node(
        "prepare_retrieve_candidate_evidence",
        lambda state: runtime.prepare(state, "retrieve_candidate_evidence"),
    )
    add_node(
        "retrieve_candidate_evidence",
        lambda state: runtime.execute(state, "retrieve_candidate_evidence", retrieve),
    )
    add_node(
        "screen_candidates",
        lambda state: runtime.pure(
            state,
            lambda value: nodes.screen_candidates(
                value,
                policy=CandidateScreeningPolicy.model_validate(
                    current_inputs(value)["screening_policy"]
                ),
            ),
        ),
    )
    add_node(
        "construct_portfolio",
        lambda state: runtime.pure(
            state,
            lambda value: nodes.construct_portfolio(
                value,
                policy=PortfolioConstructionPolicy.model_validate(
                    current_inputs(value)["construction_policy"]
                ),
            ),
        ),
    )
    add_node("prepare_draft_explanation", lambda state: runtime.prepare(state, "draft_explanation"))
    add_node(
        "draft_explanation", lambda state: runtime.execute(state, "draft_explanation", explain)
    )
    add_node("human_review", runtime.review)
    add_node("finalize_review", runtime.decide)

    routes: dict[Hashable, str] = {
        name: name
        for name in (
            "validate_profile",
            "screen_candidates",
            "construct_portfolio",
            "prepare_retrieve_candidate_evidence",
            "prepare_draft_explanation",
        )
    }
    routes.update(
        {
            "retrieve_candidate_evidence": "prepare_retrieve_candidate_evidence",
            "draft_explanation": "prepare_draft_explanation",
            "end": END,
        }
    )

    def next_revision(state: AdvisorState) -> str:
        return (
            "end"
            if state.get("status") in {"revision_blocked", "invalid_profile"}
            else state["next_stage"]
        )

    builder.add_edge(START, "begin_revision")
    builder.add_conditional_edges("begin_revision", next_revision, routes)
    builder.add_conditional_edges(
        "validate_profile", route_after_validation, {"draft_policy": "draft_policy", "end": END}
    )
    builder.add_conditional_edges(
        "draft_policy",
        lambda state: (
            "end"
            if state.get("status") == "revision_blocked"
            else ("evidence" if current_inputs(state)["with_evidence"] else "review")
        ),
        {"evidence": "prepare_retrieve_candidate_evidence", "review": "human_review", "end": END},
    )
    for stage in ("retrieve_candidate_evidence", "draft_explanation"):
        builder.add_conditional_edges(
            "prepare_" + stage,
            lambda state: "end" if state.get("status") == "revision_blocked" else "execute",
            {"execute": stage, "end": END},
        )
    builder.add_conditional_edges(
        "retrieve_candidate_evidence",
        route_after_evidence,
        {"next": "screen_candidates", "end": END},
    )
    builder.add_conditional_edges(
        "screen_candidates", route_after_screening, {"next": "construct_portfolio", "end": END}
    )
    builder.add_conditional_edges(
        "construct_portfolio",
        lambda state: (
            "end"
            if state.get("status") != "awaiting_human_review"
            else ("explain" if current_inputs(state)["with_explanation"] else "review")
        ),
        {"explain": "prepare_draft_explanation", "review": "human_review", "end": END},
    )
    builder.add_conditional_edges(
        "draft_explanation", route_after_explanation, {"human_review": "human_review", "end": END}
    )
    builder.add_conditional_edges(
        "human_review",
        lambda state: "end" if state.get("status") == "revision_blocked" else "decide",
        {"decide": "finalize_review", "end": END},
    )
    builder.add_conditional_edges("finalize_review", next_revision, routes)
    # LangGraph's default is async; a started receipt must be committed before the
    # execute superstep. Guards also reject caller overrides to async/exit.
    return builder.compile(checkpointer=checkpointer).with_config(
        {"configurable": {CONFIG_KEY_DURABILITY: "sync"}}
    )


def route_after_evidence(state: AdvisorState) -> Literal["next", "end"]:
    return "next" if state.get("status") == "awaiting_human_review" else "end"


def route_after_explanation(state: AdvisorState) -> Literal["human_review", "end"]:
    return "human_review" if state.get("status") == "awaiting_human_review" else "end"


def route_after_screening(state: AdvisorState) -> Literal["next", "end"]:
    return "next" if state.get("status") == "awaiting_human_review" else "end"


def route_after_construction(state: AdvisorState) -> Literal["next", "end"]:
    return "next" if state.get("status") == "awaiting_human_review" else "end"


graph = build_graph()
