"""Testable orchestration boundary for the local human-review dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from etf_advisor.clock import system_utc_now
from etf_advisor.config import settings
from etf_advisor.domain.policy import PolicyCalculation
from etf_advisor.explanation import ExplanationBundle
from etf_advisor.explanation.provider import create_explanation_generator
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.chroma_store import ChromaDocumentStore
from etf_advisor.rag.evidence import (
    MAX_CANDIDATE_LIMIT,
    CandidateEvidenceBundle,
    EvidenceStatus,
    HybridCandidateEvidenceRetriever,
)
from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.neo4j_store import Neo4jGraphStore

REVIEW_ACTIONS = ("approve", "edit", "reject")
type ReviewAction = Literal["approve", "edit", "reject"]


class DashboardOptions(BaseModel):
    """Optional side effects enabled for one local dashboard run."""

    model_config = ConfigDict(extra="forbid")

    with_evidence: bool = False
    with_explanation: bool = False
    candidate_limit: int = Field(default=5, ge=1, le=MAX_CANDIDATE_LIMIT)

    @model_validator(mode="after")
    def validate_dependencies(self) -> DashboardOptions:
        if self.with_explanation and not self.with_evidence:
            raise ValueError("Provider explanations require source evidence.")
        return self


class ReviewPayload(BaseModel):
    """Complete, fail-closed contract for content rendered at human review."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["portfolio_policy_review"]
    question: str = Field(min_length=1, max_length=500)
    allowed_actions: list[ReviewAction] = Field(min_length=3, max_length=3)
    draft_policy: PolicyCalculation
    candidate_evidence: CandidateEvidenceBundle | None = None
    draft_explanation: ExplanationBundle | None = None

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Review question must not be empty.")
        return normalized

    @model_validator(mode="after")
    def validate_review_consistency(self) -> ReviewPayload:
        if set(self.allowed_actions) != set(REVIEW_ACTIONS):
            raise ValueError("Review actions must contain approve, edit, and reject exactly once.")

        evidence = self.candidate_evidence
        explanation = self.draft_explanation
        if evidence is not None:
            if evidence.status != EvidenceStatus.READY:
                raise ValueError("Review evidence must be ready.")
            if evidence.objective != self.draft_policy.objective:
                raise ValueError("Review evidence objective must match the policy draft.")
            if evidence.risk_tolerance != self.draft_policy.risk_tolerance:
                raise ValueError("Review evidence risk tolerance must match the policy draft.")
            if evidence.excluded_sectors != self.draft_policy.excluded_sectors:
                raise ValueError("Review evidence exclusions must match the policy draft.")

        if explanation is not None:
            if evidence is None:
                raise ValueError("A review explanation requires source evidence.")
            candidates = {candidate.document_id: candidate for candidate in evidence.candidates}
            for citation in explanation.citations:
                candidate = candidates.get(citation.document_id)
                if candidate is None or (
                    citation.symbol != candidate.symbol
                    or citation.source != candidate.source
                    or citation.source_url != candidate.source_url
                    or citation.observed_at != candidate.observed_at.isoformat()
                ):
                    raise ValueError(
                        "Explanation citations must match the validated review evidence."
                    )
        return self


@dataclass
class DashboardRun:
    """One in-memory graph thread retained by a Streamlit browser session."""

    graph: Any
    config: dict[str, Any]
    state: dict[str, Any]

    def resume(self, action: str, feedback: str = "") -> dict[str, Any]:
        """Resume the exact paused thread with a validated human decision."""

        payload = review_payload(self.state)
        normalized_action = action.strip().lower()
        allowed_actions = payload.get("allowed_actions", [])
        if normalized_action not in REVIEW_ACTIONS or normalized_action not in allowed_actions:
            raise ValueError("Review action is not allowed by the workflow interrupt.")

        normalized_feedback = feedback.strip()
        if normalized_action in {"edit", "reject"} and not normalized_feedback:
            raise ValueError("Edit and reject decisions require reviewer feedback.")

        decision: dict[str, str] = {"action": normalized_action}
        if normalized_feedback:
            decision["feedback"] = normalized_feedback
        result = self.graph.invoke(Command(resume=decision), config=self.config)
        self.state = dict(result)
        return self.state


def start_dashboard_run(
    profile: dict[str, object],
    options: DashboardOptions,
    *,
    thread_id: str | None = None,
) -> DashboardRun:
    """Build and invoke one local workflow, closing retrieval resources after drafting."""

    validated_options = DashboardOptions.model_validate(options.model_dump(mode="python"))
    graph_store: Neo4jGraphStore | None = None
    try:
        candidate_retriever: HybridCandidateEvidenceRetriever | None = None
        if validated_options.with_evidence:
            semantic_store = ChromaDocumentStore(
                host=settings.chroma_host,
                port=settings.chroma_port,
                collection_name=settings.chroma_collection,
            )
            graph_store = Neo4jGraphStore(
                uri=settings.neo4j_uri,
                auth=settings.neo4j_credentials(),
            )
            candidate_retriever = HybridCandidateEvidenceRetriever(
                HybridRetriever(semantic_store, graph_store),
                clock=system_utc_now,
                max_age=timedelta(hours=settings.market_data_max_age_hours),
                future_tolerance=timedelta(minutes=settings.market_data_future_tolerance_minutes),
            )

        explanation_generator = (
            create_explanation_generator(settings) if validated_options.with_explanation else None
        )
        graph = build_graph(
            checkpointer=InMemorySaver(),
            candidate_retriever=candidate_retriever,
            candidate_limit=validated_options.candidate_limit,
            explanation_generator=explanation_generator,
        )
        config = {"configurable": {"thread_id": thread_id or str(uuid4())}}
        state = dict(graph.invoke({"profile": profile}, config=config))
        return DashboardRun(graph=graph, config=config, state=state)
    finally:
        if graph_store is not None:
            graph_store.close()


def review_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Return the validated payload emitted by the current LangGraph interrupt."""

    if state.get("status") != "awaiting_human_review":
        raise ValueError("Workflow is not awaiting human review.")
    interrupts = state.get("__interrupt__")
    if not isinstance(interrupts, (list, tuple)) or len(interrupts) != 1:
        raise ValueError("Workflow did not expose exactly one review interrupt.")
    value = getattr(interrupts[0], "value", None)
    if not isinstance(value, dict) or value.get("kind") != "portfolio_policy_review":
        raise ValueError("Workflow exposed an unsupported review interrupt.")
    try:
        payload = ReviewPayload.model_validate(value)
    except (TypeError, ValidationError) as exc:
        raise ValueError("Workflow review payload failed contract validation.") from exc
    return payload.model_dump(mode="json", exclude_none=True)


def parse_excluded_sectors(value: str) -> list[str]:
    """Normalize a comma-separated UI field while preserving the first spelling."""

    sectors: list[str] = []
    seen: set[str] = set()
    for item in value.split(","):
        sector = item.strip()
        key = sector.casefold()
        if sector and key not in seen:
            sectors.append(sector)
            seen.add(key)
    return sectors
