"""Testable orchestration boundary for the local human-review dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from etf_advisor.checkpoint import (
    DashboardCheckpointStore,
    MemoryCheckpointStore,
    PostgresCheckpointStore,
)
from etf_advisor.clock import system_utc_now
from etf_advisor.config import settings
from etf_advisor.domain.construction import (
    PortfolioConstructionBundle,
    PortfolioConstructionInput,
    validate_persisted_construction,
)
from etf_advisor.domain.policy import PolicyCalculation
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import CandidateScreeningBundle, screen_candidate_evidence
from etf_advisor.explanation import (
    ExplanationBundle,
    ExplanationResult,
    build_explanation_request,
    validate_and_bundle_explanation,
)
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
    durable_checkpoint: bool = False
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
    candidate_screening: CandidateScreeningBundle | None = None
    portfolio_construction: PortfolioConstructionBundle | None = None
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
        screening = self.candidate_screening
        construction = self.portfolio_construction
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

        if (evidence is None) != (screening is None):
            raise ValueError("Review evidence and candidate screening must appear together.")
        if evidence is not None and screening is not None:
            expected_screening = screen_candidate_evidence(evidence, screening.policy)
            if screening != expected_screening:
                raise ValueError("Review screening must match recomputed source evidence rules.")

        if (evidence is None) != (construction is None):
            raise ValueError("Review evidence and portfolio construction must appear together.")
        if construction is not None and construction.status != "ready":
            raise ValueError("Review portfolio construction must be ready.")

        if explanation is not None:
            if evidence is None or construction is None:
                raise ValueError("A review explanation requires a validated portfolio.")
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
    """One graph thread backed by either browser memory or a durable store."""

    graph: Any | None
    config: dict[str, Any]
    state: dict[str, Any]
    checkpoint_store: DashboardCheckpointStore | None = None

    @property
    def thread_id(self) -> str:
        """Return the opaque identifier required to restore this exact graph thread."""

        value = self.config.get("configurable", {}).get("thread_id")
        if not isinstance(value, str) or not value:
            raise ValueError("Dashboard run is missing its thread identifier.")
        return value

    @property
    def durable(self) -> bool:
        return self.checkpoint_store is not None and self.checkpoint_store.durable

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
        command: Command[Any] = Command(resume=decision)
        if self.checkpoint_store is None:
            if self.graph is None:
                raise RuntimeError("Dashboard run has no workflow runtime.")
            result = self.graph.invoke(command, config=self.config)
        else:
            with self.checkpoint_store.open() as saver:
                graph = build_graph(checkpointer=saver)
                result = graph.invoke(command, config=self.config)
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
        checkpoint_store: DashboardCheckpointStore = (
            PostgresCheckpointStore(settings.postgres_uri)
            if validated_options.durable_checkpoint
            else MemoryCheckpointStore()
        )
        checkpoint_store.setup()
        selected_thread_id = thread_id or str(uuid4())
        if checkpoint_store.durable:
            selected_thread_id = _validated_review_token(selected_thread_id)
        config = {"configurable": {"thread_id": selected_thread_id}}
        with checkpoint_store.open() as saver:
            graph = build_graph(
                checkpointer=saver,
                candidate_retriever=candidate_retriever,
                candidate_limit=validated_options.candidate_limit,
                explanation_generator=explanation_generator,
            )
            state = dict(graph.invoke({"profile": profile}, config=config))
        return DashboardRun(
            graph=None if checkpoint_store.durable else graph,
            config=config,
            state=state,
            checkpoint_store=checkpoint_store if checkpoint_store.durable else None,
        )
    finally:
        if graph_store is not None:
            graph_store.close()


def load_dashboard_run(
    review_token: str,
    *,
    checkpoint_store: DashboardCheckpointStore | None = None,
) -> DashboardRun:
    """Restore one durable thread without exposing or enumerating other checkpoints."""

    token = _validated_review_token(review_token)
    store = checkpoint_store or PostgresCheckpointStore(settings.postgres_uri)
    if not store.durable:
        raise ValueError("Saved reviews require a durable checkpoint store.")
    store.setup()
    config = {"configurable": {"thread_id": token}}
    with store.open() as saver:
        graph = build_graph(checkpointer=saver)
        snapshot = graph.get_state(config)

    if not snapshot.values:
        raise ValueError("No saved review was found for that token.")
    state = dict(snapshot.values)
    if snapshot.interrupts:
        state["__interrupt__"] = snapshot.interrupts
    if state.get("status") == "awaiting_human_review":
        review_payload(state)
    return DashboardRun(graph=None, config=config, state=state, checkpoint_store=store)


def _validated_review_token(value: str) -> str:
    normalized = value.strip()
    try:
        parsed = UUID(normalized)
    except ValueError as exc:
        raise ValueError("Review token must be a valid UUID.") from exc
    if parsed.version != 4:
        raise ValueError("Review token must be a version-4 UUID.")
    return str(parsed)


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
        construction = payload.portfolio_construction
        if construction is not None:
            evidence = payload.candidate_evidence
            screening = payload.candidate_screening
            if evidence is None or screening is None:
                raise ValueError("Review construction requires evidence and screening.")
            checkpointed_policy = PolicyCalculation.model_validate(state.get("draft_policy", {}))
            checkpointed_evidence = CandidateEvidenceBundle.model_validate(
                state.get("candidate_evidence", {})
            )
            checkpointed_screening = CandidateScreeningBundle.model_validate(
                state.get("candidate_screening", {})
            )
            checkpointed_construction = PortfolioConstructionBundle.model_validate(
                state.get("portfolio_construction", {})
            )
            checkpoint_pairs: tuple[tuple[BaseModel, BaseModel], ...] = (
                (checkpointed_policy, payload.draft_policy),
                (checkpointed_evidence, evidence),
                (checkpointed_screening, screening),
                (checkpointed_construction, construction),
            )
            checkpointed_explanation: ExplanationBundle | None = None
            if payload.draft_explanation is not None:
                checkpointed_explanation = ExplanationBundle.model_validate(
                    state.get("draft_explanation", {})
                )
                checkpoint_pairs = (
                    *checkpoint_pairs,
                    (checkpointed_explanation, payload.draft_explanation),
                )
            if any(checkpointed != interrupted for checkpointed, interrupted in checkpoint_pairs):
                raise ValueError("Review payload must match checkpointed workflow state.")
            inputs = PortfolioConstructionInput(
                profile=InvestorProfile.model_validate(state.get("profile", {})),
                policy_calculation=checkpointed_policy,
                candidate_evidence=checkpointed_evidence,
                candidate_screening=checkpointed_screening,
                construction_policy=checkpointed_construction.policy,
            )
            recomputed = validate_persisted_construction(inputs, checkpointed_construction)
            if recomputed.status != "ready":
                raise ValueError("Review construction failed deterministic recomputation.")
            if checkpointed_explanation is not None:
                explanation_request = build_explanation_request(
                    profile=state.get("profile", {}),
                    draft_policy=state.get("draft_policy", {}),
                    candidate_evidence=state.get("candidate_evidence", {}),
                )
                recomputed_explanation = validate_and_bundle_explanation(
                    explanation_request,
                    ExplanationResult(
                        provider=checkpointed_explanation.provider,
                        model=checkpointed_explanation.model,
                        explanation=checkpointed_explanation.explanation,
                    ),
                )
                if recomputed_explanation != checkpointed_explanation:
                    raise ValueError(
                        "Review explanation failed deterministic safety recomputation."
                    )
    except (TypeError, ValidationError) as exc:
        raise ValueError("Workflow review payload failed contract validation.") from exc
    except ValueError as exc:
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
