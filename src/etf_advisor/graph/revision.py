"""Revision orchestration and persisted prepare/execute side-effect boundaries."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any, cast

from langchain_core.runnables import RunnableConfig

from etf_advisor.clock import Clock
from etf_advisor.domain.construction import (
    PortfolioConstructionPolicy,
)
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.revision import (
    ARTIFACTS,
    ERRORS,
    Artifact,
    OperationReceipt,
    OperationStage,
    RetryRequest,
    ReviewDecision,
    Revision,
    RevisionInputs,
    RevisionLedger,
    digest,
    plan_revision,
)
from etf_advisor.domain.screening import CandidateScreeningPolicy
from etf_advisor.explanation import (
    ExplanationBundle,
    ExplanationResult,
    build_explanation_request,
    validate_and_bundle_explanation,
)
from etf_advisor.graph import nodes
from etf_advisor.graph.state import AdvisorState
from etf_advisor.identifiers import IdentifierFactory
from etf_advisor.rag.evidence import CandidateEvidenceBundle, EvidenceStatus


def _sealed_values(state: AdvisorState) -> dict[str, Any]:
    return {
        key: state.get(key)
        for key in (
            "revision_ledger",
            "profile",
            *ARTIFACTS,
            *ERRORS,
            "status",
            "final_message",
            "review_decision",
            "retry_operation_id",
            "next_stage",
        )
    }


def _seal(state: AdvisorState, ledger: RevisionLedger) -> AdvisorState:
    state["revision_ledger"] = ledger.model_dump(mode="json", exclude_none=True)
    state["revision_digest"] = digest(_sealed_values(state))
    return state


def validate_revision_state(state: AdvisorState, thread_id: str | None = None) -> RevisionLedger:
    """Check retained identity, ordering, references and current checkpoint integrity."""
    if state.get("revision_digest") != digest(_sealed_values(state)):
        raise ValueError("Revision state digest mismatch.")
    ledger = RevisionLedger.model_validate(state["revision_ledger"])
    if thread_id is not None and ledger.thread_id != thread_id:
        raise ValueError("Cross-thread revision state.")
    revision_ids: set[str] = set()
    operation_ids: set[str] = set()
    referenced_decisions: set[str] = set()
    for sequence, revision in enumerate(ledger.revisions, 1):
        if revision.sequence != sequence or revision.revision_id in revision_ids:
            raise ValueError("Duplicate or out-of-order revision.")
        revision_ids.add(revision.revision_id)
        if (
            RevisionInputs.model_validate(revision.inputs).model_dump(mode="json")
            != revision.inputs
        ):
            raise ValueError("Malformed or noncanonical revision inputs.")
        if revision.created_at.utcoffset() is None:
            raise ValueError("Revision requires an aware timestamp.")
        if digest(revision.inputs["profile"]) != revision.profile_digest:
            raise ValueError("Profile digest mismatch.")
        profile_artifact = ledger.artifacts[revision.profile_version_id]
        if profile_artifact.value != revision.inputs["profile"]:
            raise ValueError("Profile version mismatch.")
        if sequence == 1:
            if revision.parent_revision_id or revision.triggering_decision_id or revision.plan:
                raise ValueError("Root revision cannot have a parent decision.")
        else:
            parent = ledger.revisions[sequence - 2]
            if (
                revision.parent_revision_id != parent.revision_id
                or revision.triggering_decision_id != parent.review_decision_id
                or not parent.review_decision_id
            ):
                raise ValueError("Revision triggering decision mismatch.")
            expected = plan_revision(ledger.decisions[parent.review_decision_id], parent.inputs)
            if revision.plan != expected or revision.inputs != expected.inputs:
                raise ValueError("Revision plan mismatch.")
            if revision.created_at < parent.created_at:
                raise ValueError("Revision timestamp order mismatch.")
            if (
                revision.inputs["profile"] == parent.inputs["profile"]
                and revision.profile_version_id != parent.profile_version_id
            ):
                raise ValueError("Unchanged profile identity was relabeled.")
        if revision.review_decision_id:
            decision = ledger.decisions[revision.review_decision_id]
            if (
                decision.revision_id != revision.revision_id
                or decision.decision_id != revision.review_decision_id
                or decision.submitted_at < revision.created_at
            ):
                raise ValueError("Review decision identity mismatch.")
            referenced_decisions.add(decision.decision_id)
        if revision.completed_at is not None and (
            revision.completed_at.utcoffset() is None or revision.completed_at < revision.created_at
        ):
            raise ValueError("Revision completion timestamp mismatch.")
        for name, artifact_id in revision.artifacts.items():
            if name not in ARTIFACTS or ledger.artifacts[artifact_id].artifact_id != artifact_id:
                raise ValueError("Invalid artifact reference.")
            if name != "draft_policy" and not revision.inputs["with_evidence"]:
                raise ValueError("Disabled stage has an artifact.")
            if name == "draft_explanation" and not revision.inputs["with_explanation"]:
                raise ValueError("Disabled provider has an artifact.")
            if (
                sequence > 1
                and revision.plan is not None
                and name not in revision.plan.invalidated
                and artifact_id != ledger.revisions[sequence - 2].artifacts.get(name)
            ):
                raise ValueError("Unchanged upstream artifact identity was relabeled.")
        attempts: dict[str, list[OperationReceipt]] = {}
        for receipt in revision.receipts:
            prior = attempts.setdefault(receipt.stage, [])
            if (
                receipt.operation_id in operation_ids
                or receipt.attempt != len(prior) + 1
                or receipt.thread_id != ledger.thread_id
                or receipt.revision_id != revision.revision_id
                or receipt.started_at < revision.created_at
            ):
                raise ValueError("Operation identity or ordering mismatch.")
            if prior and (
                prior[-1].status == "succeeded" or receipt.started_at < prior[-1].started_at
            ):
                raise ValueError("Invalid retry sequence.")
            if receipt.stage == "retrieve_candidate_evidence" and attempts.get("draft_explanation"):
                raise ValueError("Retrieval cannot follow explanation within one revision.")
            operation_ids.add(receipt.operation_id)
            prior.append(receipt)
            if receipt.status == "succeeded":
                output = ledger.artifacts[cast(str, receipt.output_id)]
                if output.digest != receipt.output_digest:
                    raise ValueError("Receipt output digest mismatch.")
        if revision.operations != {
            stage: receipts[-1].operation_id for stage, receipts in attempts.items()
        }:
            raise ValueError("Attempt manifest differs from operation receipts.")
        for stage, receipts in attempts.items():
            expected_input = operation_digest(ledger, revision, cast(OperationStage, stage))
            if any(receipt.input_digest != expected_input for receipt in receipts):
                raise ValueError("Operation input digest mismatch.")
        for name, stage in (
            ("candidate_evidence", "retrieve_candidate_evidence"),
            ("draft_explanation", "draft_explanation"),
        ):
            side_effect_id = revision.artifacts.get(name)
            if side_effect_id is None:
                continue
            artifact = ledger.artifacts[side_effect_id]
            if artifact.value.get("status") != "ready":
                continue
            inherited = (
                sequence > 1 and revision.plan is not None and name not in revision.plan.invalidated
            )
            if inherited:
                if side_effect_id != ledger.revisions[sequence - 2].artifacts.get(name):
                    raise ValueError("Unchanged artifact identity was relabeled.")
            else:
                receipts = attempts.get(stage, [])
                if (
                    not receipts
                    or receipts[-1].status != "succeeded"
                    or receipts[-1].output_id != side_effect_id
                ):
                    raise ValueError("Reached side effect is missing its successful receipt.")
    if referenced_decisions != set(ledger.decisions):
        raise ValueError("Orphan or duplicate review decision.")
    for key, artifact in ledger.artifacts.items():
        if key != artifact.artifact_id:
            raise ValueError("Artifact identity mismatch.")
    current = ledger.revisions[-1]
    if current.review_decision_id and state.get("review_decision") != ledger.decisions[
        current.review_decision_id
    ].model_dump(mode="json"):
        raise ValueError("Current review decision differs from retained decision.")
    if state["profile"] != current.inputs["profile"]:
        raise ValueError("Current profile differs from revision inputs.")
    for name in ARTIFACTS:
        current_id = current.artifacts.get(name)
        expected_value = ledger.artifacts[current_id].value if current_id else {}
        if state.get(name, {}) != expected_value:
            raise ValueError("Current artifact differs from revision reference.")
    return ledger


def operation_digest(ledger: RevisionLedger, revision: Revision, stage: OperationStage) -> str:
    inputs = revision.inputs
    if stage == "retrieve_candidate_evidence":
        value = {"profile": inputs["profile"], "candidate_limit": inputs["candidate_limit"]}
    else:
        value = {
            "profile": inputs["profile"],
            "instruction": inputs["explanation_instruction"],
            **{name: ledger.artifacts[revision.artifacts[name]].digest for name in ARTIFACTS[:4]},
        }
    return digest(
        {
            "thread_id": ledger.thread_id,
            "revision_id": revision.revision_id,
            "stage": stage,
            "inputs": value,
        }
    )


def _block(state: AdvisorState) -> AdvisorState:
    # Preserve the original ledger/digest as diagnostic evidence; never repair tampering.
    result: AdvisorState = {
        **state,
        "status": "revision_blocked",
        "final_message": "Revision or replay contract failed.",
        "revision_errors": [
            {"type": "revision_contract", "message": "Revision or replay contract failed."}
        ],
    }
    try:
        ledger = validate_revision_state(state)
    except (KeyError, TypeError, ValueError):
        return result
    if not ledger.revisions[-1].review_decision_id:
        ledger.revisions[-1].status = "blocked"
    return _seal(result, ledger)


class RevisionRuntime:
    """Adapter-neutral runtime. Local permits are deliberately never checkpointed.

    Preparation durably writes started; execution consumes a one-use local permit before
    calling an adapter. A new process, repeated execution, or uncertain write cannot recreate
    that permit. Only explicit retry may prepare another attempt.
    """

    def __init__(
        self, *, clock: Clock, identifier_factory: IdentifierFactory, inputs: dict[str, Any]
    ) -> None:
        self.clock = clock
        self.identifier_factory = identifier_factory
        self.inputs = inputs
        self._permits: set[str] = set()

    def _record(self, ledger: RevisionLedger, value: dict[str, Any]) -> str:
        artifact = Artifact(
            artifact_id=self.identifier_factory(), digest=digest(value), value=value
        )
        if artifact.artifact_id in ledger.artifacts:
            raise ValueError("Identifier factory reused an artifact identity.")
        ledger.artifacts[artifact.artifact_id] = artifact
        return artifact.artifact_id

    def begin(self, state: AdvisorState, config: RunnableConfig) -> AdvisorState:
        try:
            if "revision_ledger" in state:
                ledger = validate_revision_state(state, str(config["configurable"]["thread_id"]))
                request = RetryRequest.model_validate(state.get("retry_request", {}))
                revision = ledger.revisions[-1]
                receipt = next(
                    r for r in revision.receipts if r.operation_id == request.operation_id
                )
                latest = [r for r in revision.receipts if r.stage == receipt.stage][-1]
                if (
                    request.revision_id != revision.revision_id
                    or receipt != latest
                    or receipt.status == "succeeded"
                    or revision.review_decision_id
                ):
                    raise ValueError("Retry does not target the current failed/ambiguous attempt.")
                result = deepcopy(state)
                result["retry_request"] = {}
                result["revision_errors"] = []
                result["next_stage"] = "prepare_" + receipt.stage
                result["status"] = "retry_requested"
                # Authorization is scoped to the exact last operation and consumed by prepare.
                result["retry_operation_id"] = receipt.operation_id
                index = 1 if receipt.stage == "retrieve_candidate_evidence" else 4
                for name in ARTIFACTS[index:]:
                    cast(dict[str, Any], result)[name] = {}
                    revision.artifacts.pop(name, None)
                for name in ERRORS[index:]:
                    cast(dict[str, Any], result)[name] = []
                result["review_decision"] = {}
                result["final_message"] = ""
                return _seal(result, ledger)
            if (
                state.get("retry_request")
                or state.get("revision_digest")
                or state.get("status")
                or any(state.get(name) for name in ARTIFACTS)
            ):
                raise ValueError("Missing revision ledger.")
            result = nodes.validate_profile(state)
            if result["validation_errors"]:
                return result
            inputs = {**self.inputs, "profile": result["profile"]}
            now = self.clock()
            ledger = RevisionLedger(
                thread_id=str(config["configurable"]["thread_id"]),
                revisions=[
                    Revision(
                        revision_id=self.identifier_factory(),
                        sequence=1,
                        created_at=now,
                        status="running",
                        inputs=inputs,
                        profile_version_id="pending",
                        profile_digest=digest(inputs["profile"]),
                    )
                ],
            )
            ledger.revisions[0].profile_version_id = self._record(ledger, inputs["profile"])
            result["next_stage"] = "validate_profile"
            result["revision_errors"] = []
            result["retry_operation_id"] = ""
            return _seal(result, ledger)
        except (KeyError, TypeError, ValueError, StopIteration):
            return _block(state)

    def pure(
        self, state: AdvisorState, function: Callable[[AdvisorState], AdvisorState]
    ) -> AdvisorState:
        try:
            ledger = validate_revision_state(state)
            result = cast(AdvisorState, {**state, **function(deepcopy(state))})
            return self.record_result(result, ledger)
        except (KeyError, TypeError, ValueError):
            return _block(state)

    def record_result(self, result: AdvisorState, ledger: RevisionLedger) -> AdvisorState:
        revision = ledger.revisions[-1]
        for name in ARTIFACTS:
            value = cast(dict[str, Any], result).get(name, {})
            if value:
                previous = revision.artifacts.get(name)
                if previous and ledger.artifacts[previous].value != value:
                    raise ValueError("A reached artifact cannot be silently overwritten.")
                if not previous:
                    revision.artifacts[name] = self._record(ledger, value)
        revision.status = result["status"]
        return _seal(result, ledger)

    def prepare(self, state: AdvisorState, stage: OperationStage) -> AdvisorState:
        try:
            ledger = validate_revision_state(state)
            revision = ledger.revisions[-1]
            prior = [receipt for receipt in revision.receipts if receipt.stage == stage]
            result = deepcopy(state)
            if prior and prior[-1].status == "succeeded":
                self.validate_output(state, stage)
                result["status"] = "operation_reused"
                return _seal(result, ledger)
            if prior and state.get("retry_operation_id") != prior[-1].operation_id:
                raise ValueError("Explicit retry required.")
            if not prior and state.get("retry_operation_id"):
                raise ValueError("Retry receipt is missing.")
            receipt = OperationReceipt(
                thread_id=ledger.thread_id,
                revision_id=revision.revision_id,
                stage=stage,
                attempt=len(prior) + 1,
                operation_id=self.identifier_factory(),
                input_digest=operation_digest(ledger, revision, stage),
                status="started",
                started_at=self.clock(),
            )
            revision.receipts.append(receipt)
            revision.operations[stage] = receipt.operation_id
            self._permits.add(receipt.operation_id)
            result["retry_operation_id"] = ""
            result["status"] = "operation_prepared"
            return _seal(result, ledger)
        except (KeyError, TypeError, ValueError):
            return _block(state)

    def execute(
        self,
        state: AdvisorState,
        stage: OperationStage,
        function: Callable[[AdvisorState], AdvisorState],
    ) -> AdvisorState:
        try:
            ledger = validate_revision_state(state)
            revision = ledger.revisions[-1]
            receipt = [r for r in revision.receipts if r.stage == stage][-1]
            if receipt.status == "succeeded":
                self.validate_output(state, stage)
                result = deepcopy(state)
                result["status"] = "awaiting_human_review"
                return _seal(result, ledger)
            if receipt.status != "started" or receipt.operation_id not in self._permits:
                raise ValueError("Ambiguous operation requires explicit retry.")
            self._permits.remove(receipt.operation_id)
            result = cast(AdvisorState, {**state, **function(deepcopy(state))})
            receipt.completed_at = self.clock()
            if result["status"] == "awaiting_human_review":
                self.validate_output(result, stage)
                name = "candidate_evidence" if stage == "retrieve_candidate_evidence" else stage
                value = result[name]
                receipt.output_id = self._record(ledger, value)
                receipt.output_digest = digest(value)
                revision.artifacts[name] = receipt.output_id
                receipt.status = "succeeded"
            else:
                receipt.status = "failed"
            return self.record_result(result, ledger)
        except (IndexError, KeyError, TypeError, ValueError):
            return _block(state)

    def validate_output(self, state: AdvisorState, stage: OperationStage) -> None:
        if stage == "retrieve_candidate_evidence":
            bundle = CandidateEvidenceBundle.model_validate(state["candidate_evidence"])
            profile = InvestorProfile.model_validate(state["profile"])
            if (
                bundle.status != EvidenceStatus.READY
                or bundle.objective != profile.objective
                or bundle.risk_tolerance != profile.risk_tolerance
                or bundle.excluded_sectors != profile.excluded_sectors
                or bundle.requested_limit
                != state["revision_ledger"]["revisions"][-1]["inputs"]["candidate_limit"]
            ):
                raise ValueError("Evidence request mismatch.")
        else:
            request = build_explanation_request(
                profile=state["profile"],
                draft_policy=state["draft_policy"],
                candidate_evidence=state["candidate_evidence"],
                candidate_screening=state["candidate_screening"],
                portfolio_construction=state["portfolio_construction"],
            )
            bundle_explanation = ExplanationBundle.model_validate(state["draft_explanation"])
            expected = validate_and_bundle_explanation(
                request,
                ExplanationResult(
                    provider=bundle_explanation.provider,
                    model=bundle_explanation.model,
                    explanation=bundle_explanation.explanation,
                ),
            )
            if expected != bundle_explanation:
                raise ValueError("Explanation output mismatch.")

    def review(self, state: AdvisorState) -> AdvisorState:
        try:
            ledger = validate_revision_state(state)
            revision = ledger.revisions[-1]
            if revision.review_decision_id:
                raise ValueError("Revision already reviewed.")
            if state["draft_policy"] != calculate_policy(
                InvestorProfile.model_validate(state["profile"])
            ).model_dump(mode="json"):
                raise ValueError("Policy mismatch.")
            if revision.inputs["with_evidence"]:
                self.validate_output(state, "retrieve_candidate_evidence")
                expected = nodes.screen_candidates(
                    state,
                    policy=CandidateScreeningPolicy.model_validate(
                        revision.inputs["screening_policy"]
                    ),
                )
                if expected["candidate_screening"] != state["candidate_screening"]:
                    raise ValueError("Screening mismatch.")
                expected = nodes.construct_portfolio(
                    state,
                    policy=PortfolioConstructionPolicy.model_validate(
                        revision.inputs["construction_policy"]
                    ),
                )
                if (
                    expected["status"] != "awaiting_human_review"
                    or expected["portfolio_construction"] != state["portfolio_construction"]
                ):
                    raise ValueError("Construction mismatch.")
            if revision.inputs["with_explanation"]:
                self.validate_output(state, "draft_explanation")
        except (KeyError, TypeError, ValueError):
            return _block(state)
        # Interrupt must remain outside exception handlers and has no adapter/clock side effect.
        response = nodes.request_human_review(state)
        try:
            response["review_decision"] = ReviewDecision.model_validate(
                response["review_decision"]
            ).model_dump(mode="json")
            return _seal(cast(AdvisorState, {**state, **response}), ledger)
        except (KeyError, TypeError, ValueError):
            return _block(state)

    def decide(self, state: AdvisorState) -> AdvisorState:
        try:
            ledger = validate_revision_state(state)
            revision = ledger.revisions[-1]
            decision = ReviewDecision.model_validate(state["review_decision"])
            if (
                decision.revision_id != revision.revision_id
                or revision.review_decision_id
                or decision.decision_id in ledger.decisions
                or decision.submitted_at < revision.created_at
            ):
                raise ValueError("Stale or duplicate review decision.")
            plan = (
                plan_revision(decision, revision.inputs)
                if decision.disposition == "revise"
                else None
            )
            now = self.clock()
            if decision.submitted_at > now:
                raise ValueError("Future review decision.")
            ledger.decisions[decision.decision_id] = decision
            revision.review_decision_id = decision.decision_id
            revision.completed_at = now
            result = deepcopy(state)
            result["review_decision"] = decision.model_dump(mode="json")
            result["next_stage"] = "end"
            if plan is None:
                revision.status = "approved" if decision.action == "approve" else "rejected"
                result["status"] = revision.status
                result["final_message"] = (
                    nodes.finalize_review(state)["final_message"]
                    if decision.action == "approve"
                    else decision.note
                )
            else:
                revision.status = "rejected" if decision.action == "reject" else "revised"
                child = Revision(
                    revision_id=self.identifier_factory(),
                    sequence=revision.sequence + 1,
                    parent_revision_id=revision.revision_id,
                    triggering_decision_id=decision.decision_id,
                    created_at=now,
                    status="running",
                    inputs=plan.inputs,
                    plan=plan,
                    profile_digest=digest(plan.inputs["profile"]),
                    profile_version_id=(
                        revision.profile_version_id
                        if plan.inputs["profile"] == revision.inputs["profile"]
                        else self._record(ledger, plan.inputs["profile"])
                    ),
                    artifacts={
                        name: artifact_id
                        for name, artifact_id in revision.artifacts.items()
                        if name not in plan.invalidated
                    },
                )
                ledger.revisions.append(child)
                for name in plan.invalidated:
                    cast(dict[str, Any], result)[name] = (
                        [] if name in ERRORS else ("" if name == "final_message" else {})
                    )
                result["profile"] = plan.inputs["profile"]
                result["status"] = "revision_planned"
                result["next_stage"] = plan.restart_stage
            return _seal(result, ledger)
        except (KeyError, TypeError, ValueError):
            return _block(state)


def current_inputs(state: AdvisorState) -> dict[str, Any]:
    return cast(dict[str, Any], state["revision_ledger"]["revisions"][-1]["inputs"])
