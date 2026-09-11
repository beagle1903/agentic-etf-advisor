"""Testable orchestration boundary for the local human-review dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from etf_advisor.audit import reconstruct_audit
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
from etf_advisor.domain.revision import RetryRequest, ReviewDecision, plan_revision
from etf_advisor.domain.screening import CandidateScreeningBundle, screen_candidate_evidence
from etf_advisor.explanation import (
    ExplanationBundle,
    ExplanationGenerator,
    ExplanationResult,
    build_explanation_request,
    validate_and_bundle_explanation,
)
from etf_advisor.explanation.provider import create_explanation_generator
from etf_advisor.graph.revision import validate_revision_state
from etf_advisor.graph.state import AdvisorState
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.chroma_store import ChromaDocumentStore
from etf_advisor.rag.evidence import (
    MAX_CANDIDATE_LIMIT,
    CandidateEvidenceBundle,
    CandidateEvidenceRetriever,
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
    revision_id: str | None = None

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
    # Transient process-local dependencies; never part of checkpoint state.
    candidate_retriever: CandidateEvidenceRetriever | None = field(default=None, repr=False)
    explanation_generator: ExplanationGenerator | None = field(default=None, repr=False)
    candidate_limit: int = field(default=5, repr=False)
    candidate_retriever_usable: bool | None = field(default=None, repr=False)
    explanation_generator_usable: bool | None = field(default=None, repr=False)
    submission_outcome_unknown: bool = field(default=False, repr=False)

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

    def resume(
        self,
        action: str,
        feedback: str = "",
        *,
        disposition: str | None = None,
        feedback_items: list[dict[str, Any]] | None = None,
        expected_revision_id: str | None = None,
    ) -> dict[str, Any]:
        """Resume the exact paused thread with a validated human decision."""
        if self.submission_outcome_unknown:
            raise ValueError("Refresh this exact thread before submitting another action.")

        payload = review_payload(self.state)
        normalized_action = action.strip().lower()
        allowed_actions = payload.get("allowed_actions", [])
        if normalized_action not in REVIEW_ACTIONS or normalized_action not in allowed_actions:
            raise ValueError("Review action is not allowed by the workflow interrupt.")

        normalized_feedback = feedback.strip()
        if normalized_action in {"edit", "reject"} and not normalized_feedback:
            raise ValueError("Edit and reject decisions require reviewer feedback.")

        rendered_revision_id = payload.get("revision_id")
        expected_revision_id = expected_revision_id or rendered_revision_id
        decision: dict[str, Any] = {"action": normalized_action}
        if normalized_feedback:
            decision["feedback"] = normalized_feedback
        if rendered_revision_id:
            decision = ReviewDecision.model_validate(
                {
                    "decision_id": str(uuid4()),
                    "revision_id": rendered_revision_id,
                    "action": normalized_action,
                    "disposition": disposition,
                    "note": normalized_feedback,
                    "feedback": feedback_items or [],
                    "submitted_at": system_utc_now(),
                }
            ).model_dump(mode="json")
        command: Command[Any] = Command(resume=decision)
        if self.checkpoint_store is None:
            if self.graph is None:
                raise RuntimeError("Dashboard run has no workflow runtime.")
            try:
                result = self.graph.invoke(command, config=self.config)
            except Exception:
                self.submission_outcome_unknown = True
                raise
        else:
            submission_started = False
            try:
                with self.checkpoint_store.managed(self.thread_id) as saver:
                    graph = self._build_managed_graph(saver)
                    current = self._snapshot(graph)
                    current_payload = review_payload(current)
                    if expected_revision_id != current_payload.get("revision_id"):
                        self.state = current
                        raise ValueError("The rendered revision is stale; refresh before acting.")
                    if rendered_revision_id and normalized_action != "approve":
                        validated_decision = ReviewDecision.model_validate(decision)
                        if validated_decision.disposition == "revise":
                            ledger = validate_revision_state(
                                cast(AdvisorState, current), self.thread_id
                            )
                            plan = plan_revision(validated_decision, ledger.revisions[-1].inputs)
                            self._require_plan_adapters(
                                plan.restart_stage, ledger.revisions[-1].inputs
                            )
                    submission_started = True
                    result = graph.invoke(command, config=self.config)
                self.state = dict(result)
            except Exception:
                if submission_started:
                    self.submission_outcome_unknown = True
                raise
            return self.state
        self.state = dict(result)
        return self.state

    def retry(self, operation_id: str, *, expected_revision_id: str) -> dict[str, Any]:
        """Explicitly retry the exact current failed or ambiguous operation."""
        if self.submission_outcome_unknown:
            raise ValueError("Refresh this exact thread before submitting another action.")
        if self.checkpoint_store is None:
            raise ValueError("Retry requires a managed checkpoint store.")
        request = RetryRequest.model_validate(
            {
                "action": "retry",
                "revision_id": expected_revision_id,
                "operation_id": operation_id,
            }
        )
        submission_started = False
        try:
            with self.checkpoint_store.managed(self.thread_id) as saver:
                graph = self._build_managed_graph(saver)
                current = self._snapshot(graph)
                ledger = validate_revision_state(cast(AdvisorState, current), self.thread_id)
                revision = ledger.revisions[-1]
                matches = [
                    receipt for receipt in revision.receipts if receipt.operation_id == operation_id
                ]
                if (
                    revision.revision_id != expected_revision_id
                    or revision.review_decision_id is not None
                    or len(matches) != 1
                ):
                    self.state = current
                    raise ValueError(
                        "Retry does not target the current failed or ambiguous attempt."
                    )
                receipt = matches[0]
                latest = [item for item in revision.receipts if item.stage == receipt.stage][-1]
                if latest != receipt or receipt.status == "succeeded":
                    self.state = current
                    raise ValueError(
                        "Retry does not target the current failed or ambiguous attempt."
                    )
                self._require_operation_adapter(receipt.stage)
                submission_started = True
                result = graph.invoke(
                    {"retry_request": request.model_dump(mode="json")}, config=self.config
                )
            self.state = dict(result)
        except Exception:
            if submission_started:
                self.submission_outcome_unknown = True
            raise
        return self.state

    def refresh(self) -> dict[str, Any]:
        """Reload the exact checkpoint without invoking workflow or external adapters."""
        if self.checkpoint_store is None:
            if self.graph is None or not hasattr(self.graph, "get_state"):
                raise ValueError("This dashboard run cannot be refreshed.")
            self.state = self._snapshot(self.graph)
        else:
            with self.checkpoint_store.managed(self.thread_id) as saver:
                self.state = self._snapshot(self._build_managed_graph(saver))
        self.submission_outcome_unknown = False
        return self.state

    def _build_managed_graph(self, saver: Any) -> Any:
        if self.durable:
            return build_graph(checkpointer=saver)
        # Graph construction preserves the workflow's evidence/explanation shape. Plan-derived
        # preflight below decides whether a route may actually call either retained adapter.
        retriever = self.candidate_retriever
        generator = (
            self.explanation_generator
            if retriever is not None and self.explanation_generator is not None
            else None
        )
        return build_graph(
            checkpointer=saver,
            candidate_retriever=retriever,
            explanation_generator=generator,
            candidate_limit=self.candidate_limit,
        )

    def _snapshot(self, graph: Any) -> dict[str, Any]:
        snapshot = graph.get_state(self.config)
        if not snapshot.values:
            raise ValueError("No saved review was found for this exact thread.")
        state = dict(snapshot.values)
        validate_revision_state(cast(AdvisorState, state), self.thread_id)
        if snapshot.interrupts:
            state["__interrupt__"] = snapshot.interrupts
        if state.get("status") == "awaiting_human_review":
            review_payload(state)
        return state

    def _require_plan_adapters(self, restart_stage: str, inputs: dict[str, Any]) -> None:
        stages = {
            "validate_profile": 0,
            "retrieve_candidate_evidence": 1,
            "screen_candidates": 2,
            "construct_portfolio": 3,
            "draft_explanation": 4,
        }
        index = stages[restart_stage]
        if inputs.get("with_evidence") and index <= 1:
            self._require_operation_adapter("retrieve_candidate_evidence")
        if inputs.get("with_explanation") and index <= 4:
            self._require_operation_adapter("draft_explanation")

    def _require_operation_adapter(self, stage: str) -> None:
        retriever_usable = (
            self.candidate_retriever is not None and self.candidate_retriever_usable is not False
        )
        generator_usable = (
            self.explanation_generator is not None
            and self.explanation_generator_usable is not False
        )
        if stage == "retrieve_candidate_evidence" and not retriever_usable:
            raise ValueError("The retrieval adapter is unavailable for this revision or retry.")
        if stage == "draft_explanation" and not generator_usable:
            raise ValueError("The explanation adapter is unavailable for this revision or retry.")

    def discard(self) -> None:
        """Discard process-local state and invalidate this cached runtime handle."""
        if not isinstance(self.checkpoint_store, MemoryCheckpointStore) or self.durable:
            raise ValueError("Discard requires a process-local checkpoint store.")
        self.checkpoint_store.discard(self.thread_id)
        self.graph = None
        self.state = {}
        self.candidate_retriever = None
        self.explanation_generator = None
        self.candidate_retriever_usable = False
        self.explanation_generator_usable = False
        self.submission_outcome_unknown = False

    def lifecycle(self) -> dict[str, Any]:
        """Inspect this exact run's lifecycle without extending its retention."""
        if self.checkpoint_store is None:
            raise RuntimeError("Dashboard run has no checkpoint store.")
        return self.checkpoint_store.inspect(self.thread_id)

    def audit(self) -> dict[str, Any]:
        """Return an allowlisted detached audit projection for this exact run."""
        return dashboard_audit(self.state, self.thread_id)


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
            PostgresCheckpointStore(
                settings.postgres_uri, retention_days=settings.checkpoint_retention_days
            )
            if validated_options.durable_checkpoint
            else MemoryCheckpointStore()
        )
        checkpoint_store.setup()
        selected_thread_id = thread_id or str(uuid4())
        if checkpoint_store.durable:
            selected_thread_id = _validated_review_token(selected_thread_id)
        config = {"configurable": {"thread_id": selected_thread_id}}
        with checkpoint_store.managed(selected_thread_id, create=True) as saver:
            graph = build_graph(
                checkpointer=saver,
                candidate_retriever=candidate_retriever,
                candidate_limit=validated_options.candidate_limit,
                explanation_generator=explanation_generator,
            )
            state = dict(graph.invoke({"profile": profile}, config=config))
        return DashboardRun(
            graph=None,
            config=config,
            state=state,
            checkpoint_store=checkpoint_store,
            candidate_retriever=candidate_retriever if not checkpoint_store.durable else None,
            explanation_generator=explanation_generator if not checkpoint_store.durable else None,
            candidate_limit=validated_options.candidate_limit
            if not checkpoint_store.durable
            else 5,
            candidate_retriever_usable=(
                False
                if candidate_retriever is not None
                and type(candidate_retriever).__name__ == "HybridCandidateEvidenceRetriever"
                and type(candidate_retriever).__module__.startswith("etf_advisor.")
                else None
            ),
            explanation_generator_usable=(
                explanation_generator is not None if not checkpoint_store.durable else False
            ),
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
    with store.managed(token) as saver:
        graph = build_graph(checkpointer=saver)
        snapshot = graph.get_state(config)

    if not snapshot.values:
        raise ValueError("No saved review was found for that token.")
    state = dict(snapshot.values)
    try:
        validate_revision_state(cast(AdvisorState, state), token)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Saved review failed revision contract validation.") from exc
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


def inspect_saved_review_lifecycle(
    review_token: str, *, checkpoint_store: DashboardCheckpointStore | None = None
) -> dict[str, Any]:
    """Inspect one exact durable token without restoring graph state or renewing retention."""
    try:
        token = _validated_review_token(review_token)
        store = checkpoint_store or PostgresCheckpointStore(settings.postgres_uri)
        if not store.durable:
            raise ValueError("Saved lifecycle inspection requires a durable checkpoint store.")
        store.setup()
        return store.inspect(token)
    except Exception:
        return {"status": "failure"}


def delete_saved_review(
    review_token: str,
    confirmation_token: str,
    *,
    confirmed: bool,
    checkpoint_store: DashboardCheckpointStore | None = None,
) -> str:
    """Permanently delete one exact durable thread after token re-entry and confirmation."""
    try:
        token = _validated_review_token(review_token)
        confirmation = _validated_review_token(confirmation_token)
        if token != confirmation or confirmed is not True:
            return "failure"
        store = checkpoint_store or PostgresCheckpointStore(settings.postgres_uri)
        if not store.durable:
            return "failure"
        store.setup()
        return store.delete(token, confirmed=True)
    except Exception:
        return "failure"


def dashboard_audit(state: dict[str, Any], thread_id: str) -> dict[str, Any]:
    """Project validated audit history without private artifact or provider content."""
    history = reconstruct_audit(state, thread_id)
    revisions: list[dict[str, Any]] = []
    for source in history["revisions"]:
        item = {
            key: source[key]
            for key in (
                "revision_id",
                "sequence",
                "parent_revision_id",
                "triggering_decision_id",
                "review_decision_id",
                "created_at",
                "completed_at",
                "status",
                "child_revision_ids",
            )
            if key in source
        }
        profile = source["profile_version"]
        item["profile_version"] = {
            "artifact_id": profile["artifact_id"],
            "digest": profile["digest"],
        }
        item["artifacts"] = {
            name: {"artifact_id": artifact["artifact_id"], "digest": artifact["digest"]}
            for name, artifact in source["artifacts"].items()
        }
        if "snapshot" in source:
            item["snapshot"] = dict(source["snapshot"])
        if source.get("plan"):
            plan = source["plan"]
            item["plan"] = {
                "restart_stage": plan["restart_stage"],
                "invalidated": list(plan["invalidated"]),
                "feedback_classes": list(plan["feedback_classes"]),
                "planning_digest": plan["planning_digest"],
            }
        if source.get("decision"):
            decision = source["decision"]
            item["decision"] = {
                key: decision[key]
                for key in (
                    "decision_id",
                    "revision_id",
                    "action",
                    "disposition",
                    "note",
                    "submitted_at",
                )
                if key in decision
            }
            item["decision"]["feedback_classes"] = [
                feedback["kind"] for feedback in decision.get("feedback", [])
            ]
        item["receipts"] = [
            {
                key: receipt[key]
                for key in (
                    "revision_id",
                    "stage",
                    "attempt",
                    "operation_id",
                    "input_digest",
                    "status",
                    "output_id",
                    "output_digest",
                    "started_at",
                    "completed_at",
                )
                if key in receipt
            }
            for receipt in source.get("receipts", [])
        ]
        revisions.append(item)
    return {"schema_version": history["schema_version"], "revisions": revisions}


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
        if payload.revision_id is not None or state.get("revision_ledger"):
            ledger = validate_revision_state(cast(AdvisorState, state))
            if payload.revision_id != ledger.revisions[-1].revision_id:
                raise ValueError("Review interrupt revision must match checkpointed state.")
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
            checkpointed_explanation_payload = state.get("draft_explanation", {})
            checkpoint_has_explanation = checkpointed_explanation_payload not in ({}, None)
            interrupt_has_explanation = payload.draft_explanation is not None
            if checkpoint_has_explanation != interrupt_has_explanation:
                raise ValueError(
                    "Review explanation presence must match checkpointed workflow state."
                )
            checkpointed_explanation: ExplanationBundle | None = None
            if payload.draft_explanation is not None:
                checkpointed_explanation = ExplanationBundle.model_validate(
                    checkpointed_explanation_payload
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
                    candidate_screening=state.get("candidate_screening", {}),
                    portfolio_construction=state.get("portfolio_construction", {}),
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
