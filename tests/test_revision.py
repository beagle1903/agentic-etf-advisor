"""Deterministic revision routing and replay acceptance for Issue #40."""

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from test_workflow import (
    _current_evidence_retriever,
    _valid_generated_explanation,
    review_decision,
    valid_profile,
)

from etf_advisor.dashboard import review_payload
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.revision import (
    ARTIFACTS,
    CLASSES,
    STAGES,
    ReviewDecision,
    RevisionLedger,
    digest,
    plan_revision,
)
from etf_advisor.explanation import ExplanationGenerationError, ExplanationResult
from etf_advisor.graph.revision import _sealed_values, operation_digest, validate_revision_state
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.evidence import CandidateEvidenceBundle, EvidenceRetrievalError

FEEDBACK = [
    {"kind": "profile", "patch": {"initial_investment_usd": 60_000}},
    {"kind": "evidence", "refresh": True, "candidate_limit": 5},
    {"kind": "screening_policy", "patch": {"max_expense_ratio_pct": 0.8}},
    {"kind": "construction_policy", "patch": {"max_positions": 4}},
    {"kind": "explanation", "instruction": "Use shorter sentences."},
]


class Adapters:
    def __init__(self) -> None:
        self.retrieval_calls = 0
        self.provider_calls = 0
        self.instructions = []
        self.fail_retrieval = False
        self.fail_provider = False
        self.crash_retrieval = False
        self.crash_provider = False

    def retrieve(self, profile: Any, *, limit: int = 5) -> Any:
        self.retrieval_calls += 1
        if self.crash_retrieval:
            raise RuntimeError("simulated loss after external call")
        if self.fail_retrieval:
            raise EvidenceRetrievalError("Source evidence retrieval failed.")
        return _current_evidence_retriever().retrieve(profile, limit=limit)

    def generate(self, request: Any) -> Any:
        self.provider_calls += 1
        self.instructions.append(request.revision_instruction)
        if self.crash_provider:
            raise RuntimeError("simulated loss after external call")
        if self.fail_provider:
            raise ExplanationGenerationError("The explanation provider is unavailable.")
        return ExplanationResult(
            provider="test", model="fixed", explanation=_valid_generated_explanation()
        )


def _replace_with_coherent_stale_field_state(state: dict[str, Any]) -> None:
    evidence_payload = deepcopy(state["candidate_evidence"])
    candidate = evidence_payload["candidates"][0]
    provenance = json.loads(candidate["metadata"]["field_provenance_json"])
    checked_at = datetime.fromisoformat(evidence_payload["checked_at"].replace("Z", "+00:00"))
    stale_at = checked_at - timedelta(hours=24, microseconds=1)
    provenance["expense_ratio_pct"]["observed_at"] = stale_at.isoformat()
    candidate["metadata"]["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    evidence_payload["snapshot_version"] = None
    evidence_payload["snapshot_digest"] = None
    evidence_payload = CandidateEvidenceBundle.model_validate(evidence_payload).model_dump(
        mode="json"
    )
    state["candidate_evidence"] = evidence_payload
    screening_payload = deepcopy(state["candidate_screening"])
    screening_payload["candidates"][0]["rules"][3]["citation"]["observed_at"] = stale_at.isoformat()
    state["candidate_screening"] = screening_payload

    raw_ledger = state["revision_ledger"]
    revision = raw_ledger["revisions"][-1]
    evidence_id = revision["artifacts"]["candidate_evidence"]
    evidence_digest = digest(evidence_payload)
    raw_ledger["artifacts"][evidence_id]["value"] = evidence_payload
    raw_ledger["artifacts"][evidence_id]["digest"] = evidence_digest
    screening_id = revision["artifacts"]["candidate_screening"]
    raw_ledger["artifacts"][screening_id]["value"] = screening_payload
    raw_ledger["artifacts"][screening_id]["digest"] = digest(screening_payload)
    retrieval_receipt = next(
        receipt
        for receipt in revision["receipts"]
        if receipt["stage"] == "retrieve_candidate_evidence"
    )
    retrieval_receipt["output_digest"] = evidence_digest

    ledger = RevisionLedger.model_validate(raw_ledger)
    current = ledger.revisions[-1]
    explanation_receipt = next(
        receipt for receipt in current.receipts if receipt.stage == "draft_explanation"
    )
    explanation_receipt.input_digest = operation_digest(
        ledger,
        current,
        "draft_explanation",
    )
    state["revision_ledger"] = ledger.model_dump(mode="json", exclude_none=True)
    state["revision_digest"] = digest(_sealed_values(state))


def start(*, evidence: bool = True, explanation: bool = True) -> tuple[Any, Any, Any, Any, Any]:
    adapters = Adapters()
    saver = InMemorySaver()
    graph = build_graph(
        checkpointer=saver,
        candidate_retriever=adapters if evidence else None,
        explanation_generator=adapters if evidence and explanation else None,
    )
    config = {"configurable": {"thread_id": "revision-test"}, "recursion_limit": 100}
    state = graph.invoke({"profile": valid_profile()}, config)
    assert state["status"] == "awaiting_human_review"
    return graph, config, state, adapters, saver


@pytest.mark.parametrize("index", range(5), ids=CLASSES)
@pytest.mark.parametrize("action", ["edit", "reject"])
def test_feedback_routes_exact_boundary_and_preserves_upstream(index: int, action: str) -> None:
    graph, config, parent, adapters, _ = start()
    decision = review_decision(parent, action, [FEEDBACK[index]])
    updates = list(graph.stream(Command(resume=decision), config, stream_mode="updates"))
    visited = [name for update in updates for name in update if name != "__interrupt__"]
    assert visited[:2] == ["human_review", "finalize_review"]
    expected_stages = [
        "validate_profile",
        "draft_policy",
        "prepare_retrieve_candidate_evidence",
        "retrieve_candidate_evidence",
        "screen_candidates",
        "construct_portfolio",
        "prepare_draft_explanation",
        "draft_explanation",
        "human_review",
    ]
    first = [0, 2, 4, 5, 6][index]
    # An interrupted human-review node has no normal update.
    assert visited[2:] == expected_stages[first:-1]
    cleared = updates[1]["finalize_review"]
    for name in ARTIFACTS[index:]:
        assert cleared[name] == {}
    assert cleared["review_decision"] == {}
    assert cleared["final_message"] == ""
    child = dict(graph.get_state(config).values)
    assert child["status"] == "awaiting_human_review"
    ledger = validate_revision_state(child)
    previous, current = ledger.revisions
    assert current.parent_revision_id == previous.revision_id
    assert current.triggering_decision_id == previous.review_decision_id == decision["decision_id"]
    assert current.review_decision_id is None
    assert current.plan.restart_stage == STAGES[index]
    for name in ARTIFACTS[:index]:
        assert current.artifacts[name] == previous.artifacts[name]
        assert child[name] == parent[name]
    for name in ARTIFACTS[index:]:
        assert current.artifacts[name] != previous.artifacts[name]
    assert adapters.retrieval_calls == (2 if index <= 1 else 1)
    assert adapters.provider_calls == 2
    assert adapters.instructions[-1] == (FEEDBACK[4]["instruction"] if index == 4 else "")
    assert previous.status == ("rejected" if action == "reject" else "revised")
    json.dumps(child)


@pytest.mark.parametrize("indexes", [[4, 2], [4, 3, 1], [4, 3, 2, 1, 0]])
def test_mixed_feedback_earliest_stage_and_all_patches(indexes: list[int]) -> None:
    graph, config, parent, adapters, _ = start()
    child = graph.invoke(
        Command(resume=review_decision(parent, "edit", [FEEDBACK[i] for i in indexes])), config
    )
    assert child["status"] == "awaiting_human_review"
    revision = validate_revision_state(child).revisions[-1]
    assert revision.plan.restart_stage == STAGES[min(indexes)]
    assert revision.plan.feedback_classes == [CLASSES[i] for i in sorted(indexes)]
    assert revision.inputs["explanation_instruction"] == FEEDBACK[4]["instruction"]
    assert adapters.retrieval_calls == (2 if min(indexes) <= 1 else 1)
    assert adapters.provider_calls == 2


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_terminal_decisions_do_not_call_adapters(action: str) -> None:
    graph, config, parent, adapters, _ = start()
    result = graph.invoke(Command(resume=review_decision(parent, action)), config)
    assert result["status"] == ("approved" if action == "approve" else "rejected")
    ledger = validate_revision_state(result)
    assert len(ledger.revisions) == 1
    assert ledger.revisions[0].review_decision_id in ledger.decisions
    assert adapters.retrieval_calls == adapters.provider_calls == 1


def test_policy_only_revision_has_no_invented_downstream_lineage() -> None:
    graph, config, parent, adapters, _ = start(evidence=False)
    child = graph.invoke(Command(resume=review_decision(parent, "edit", [FEEDBACK[0]])), config)
    ledger = validate_revision_state(child)
    for revision in ledger.revisions:
        assert set(revision.artifacts) == {"draft_policy"}
        assert revision.receipts == []
    assert "review_decision_id" not in child["revision_ledger"]["revisions"][-1]
    assert adapters.retrieval_calls == adapters.provider_calls == 0
    completed = graph.invoke(Command(resume=review_decision(child)), config)
    assert validate_revision_state(completed).revisions[-1].review_decision_id is not None


@pytest.mark.parametrize(
    "change",
    [
        {"action": "approve", "feedback": [FEEDBACK[0]]},
        {"disposition": "close", "feedback": [FEEDBACK[0]]},
        {"feedback": []},
        {"feedback": [{"kind": "profile", "patch": {"horizon_years": 0}}]},
        {"feedback": [{"kind": "profile", "patch": {"allocation": 100}}]},
        {"feedback": [{"kind": "screening_policy", "patch": {"unknown": 1}}]},
        {"feedback": [{"kind": "construction_policy", "patch": {"max_positions": 0}}]},
        {"feedback": [{"kind": "explanation", "instruction": " ", "patch": {"weights": 100}}]},
        {"feedback": [{"kind": "evidence", "refresh": False, "candidate_limit": 5}]},
        {"feedback": [FEEDBACK[0], FEEDBACK[0]]},
        {"feedback": [FEEDBACK[0], {"kind": "unknown"}]},
        {"revision_id": "old-revision"},
        {"submitted_at": "2000-01-01T00:00:00Z"},
        {"submitted_at": "2999-01-01T00:00:00Z"},
        {"submitted_at": "2026-09-05T00:00:00"},
        {"note": "x" * 2001},
    ],
)
def test_invalid_decision_applies_no_partial_patch_or_side_effect(change: dict[str, Any]) -> None:
    graph, config, parent, adapters, _ = start()
    decision = {**review_decision(parent, "edit", [FEEDBACK[0]]), **change}
    result = graph.invoke(Command(resume=decision), config)
    assert result["status"] == "revision_blocked"
    assert result["profile"] == parent["profile"]
    expected_ledger = deepcopy(parent["revision_ledger"])
    expected_ledger["revisions"][-1]["status"] = "blocked"
    assert result["revision_ledger"] == expected_ledger
    assert adapters.retrieval_calls == adapters.provider_calls == 1


@pytest.mark.parametrize("index", [1, 2, 3, 4])
def test_disabled_stage_feedback_is_rejected(index: int) -> None:
    graph, config, parent, _, _ = start(evidence=False)
    result = graph.invoke(
        Command(resume=review_decision(parent, "edit", [FEEDBACK[index]])), config
    )
    assert result["status"] == "revision_blocked"


@pytest.mark.parametrize("stage", ["retrieve_candidate_evidence", "draft_explanation"])
def test_successful_receipt_reuse_after_new_runtime_has_zero_adapter_calls(stage: str) -> None:
    _graph, config, state, adapters, saver = start()
    before = validate_revision_state(state)
    before_revision = before.revisions[-1]
    before_artifacts = dict(before_revision.artifacts)
    before_operations = dict(before_revision.operations)
    restored = build_graph(
        checkpointer=saver, candidate_retriever=adapters, explanation_generator=adapters
    )
    # Reschedule the exact completed side-effect node through the preceding durable node.
    restored.update_state(config, {}, as_node="prepare_" + stage)
    result = restored.invoke(None, config)
    assert result["status"] == "awaiting_human_review"
    assert adapters.retrieval_calls == adapters.provider_calls == 1
    after = validate_revision_state(result).revisions[-1]
    assert after.artifacts == before_artifacts
    assert after.operations == before_operations


@pytest.mark.parametrize(
    "as_node",
    ["prepare_draft_explanation", "draft_explanation"],
    ids=["explanation-output-reuse", "review"],
)
def test_coherent_stale_field_restore_blocks_semantically_without_adapter_calls(
    as_node: str,
) -> None:
    graph, config, _state, adapters, saver = start()
    altered = deepcopy(dict(graph.get_state(config).values))
    _replace_with_coherent_stale_field_state(altered)
    validate_revision_state(altered)
    graph.update_state(config, altered, as_node=as_node)
    restored = build_graph(
        checkpointer=saver,
        candidate_retriever=adapters,
        explanation_generator=adapters,
    )

    result = restored.invoke(None, config)

    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1
    provenance = json.loads(
        altered["candidate_evidence"]["candidates"][0]["metadata"]["field_provenance_json"]
    )
    assert provenance["expense_ratio_pct"]["value"] == 0.1
    assert altered["candidate_screening"]["status"] == "ready"
    assert altered["portfolio_construction"]["status"] == "ready"


@pytest.mark.parametrize("stage", ["retrieve_candidate_evidence", "draft_explanation"])
@pytest.mark.parametrize("ambiguous", [False, True])
def test_failed_or_ambiguous_operation_requires_explicit_new_attempt(
    stage: str, ambiguous: bool
) -> None:
    adapters, saver = Adapters(), InMemorySaver()
    is_retrieval = stage == "retrieve_candidate_evidence"
    failure_attribute = ("crash_" if ambiguous else "fail_") + (
        "retrieval" if is_retrieval else "provider"
    )
    setattr(adapters, failure_attribute, True)
    config = {"configurable": {"thread_id": "retry-test"}}
    graph = build_graph(
        checkpointer=saver, candidate_retriever=adapters, explanation_generator=adapters
    )
    if ambiguous:
        with pytest.raises(RuntimeError, match="simulated loss"):
            graph.invoke({"profile": valid_profile()}, config)
        state = graph.get_state(config).values
    else:
        state = graph.invoke({"profile": valid_profile()}, config)
    prior = validate_revision_state(state).revisions[-1].receipts[-1]
    assert prior.status == ("started" if ambiguous else "failed")
    setattr(adapters, failure_attribute, False)
    restored = build_graph(
        checkpointer=saver, candidate_retriever=adapters, explanation_generator=adapters
    )
    calls = (adapters.retrieval_calls, adapters.provider_calls)
    if ambiguous:
        blocked = restored.invoke(None, config)
        assert blocked["status"] == "revision_blocked"
        assert (adapters.retrieval_calls, adapters.provider_calls) == calls
    result = restored.invoke(
        {
            "retry_request": {
                "action": "retry",
                "revision_id": prior.revision_id,
                "operation_id": prior.operation_id,
            }
        },
        config,
    )
    assert result["status"] == "awaiting_human_review"
    receipts = [
        r for r in validate_revision_state(result).revisions[-1].receipts if r.stage == stage
    ]
    assert [r.attempt for r in receipts] == [1, 2]
    assert receipts[0] == prior
    assert receipts[1].operation_id != prior.operation_id
    assert receipts[1].status == "succeeded"
    assert (adapters.retrieval_calls, adapters.provider_calls) == (
        (2, 1) if is_retrieval else (1, 2)
    )


@pytest.mark.parametrize(
    "tamper",
    [
        "missing",
        "duplicate",
        "order",
        "revision",
        "thread",
        "input",
        "output",
        "output_missing",
        "started",
        "malformed",
    ],
)
def test_bad_restored_receipts_never_invoke_adapter(tamper: str) -> None:
    graph, config, _state, adapters, saver = start()
    altered = deepcopy(dict(graph.get_state(config).values))
    ledger = altered["revision_ledger"]
    receipts = ledger["revisions"][0]["receipts"]
    receipt = receipts[-1]
    if tamper == "missing":
        receipts.pop()
    elif tamper == "duplicate":
        receipts.append(deepcopy(receipt))
    elif tamper == "order":
        receipt["attempt"] = 2
    elif tamper in {"revision", "thread"}:
        receipt[tamper + "_id"] = "different"
    elif tamper in {"input", "output"}:
        receipt[tamper + "_digest"] = "0" * 64
    elif tamper == "output_missing":
        del ledger["artifacts"][receipt["output_id"]]
    elif tamper == "started":
        receipt["status"] = "started"
        for key in ("completed_at", "output_id", "output_digest"):
            receipt.pop(key)
    else:
        receipt["attempt"] = "bad"
    # Exercise semantic receipt guards independently of the outer tamper-evident seal.
    altered["revision_digest"] = digest(_sealed_values(altered))
    graph.update_state(config, altered, as_node="prepare_draft_explanation")
    restored = build_graph(
        checkpointer=saver, candidate_retriever=adapters, explanation_generator=adapters
    )
    blocked = restored.invoke(None, config)
    assert blocked["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1


@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "draft_policy",
        "candidate_evidence",
        "candidate_screening",
        "portfolio_construction",
        "draft_explanation",
        "revision_ledger",
    ],
)
def test_review_restore_detects_tampered_checkpoint_before_approval(field: str) -> None:
    graph, config, _parent, adapters, saver = start()
    altered = deepcopy(dict(graph.get_state(config).values))
    altered[field]["unexpected"] = "tamper"
    graph.update_state(config, altered, as_node="draft_explanation")
    restored = build_graph(checkpointer=saver)
    result = restored.invoke(None, config)
    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1


def test_detached_interrupt_policy_tampering_passes_seal_but_blocks_dashboard_review() -> None:
    _graph, _config, parent, adapters, _saver = start()
    detached = deepcopy(parent)
    alternate_profile = InvestorProfile.model_validate(parent["profile"]).model_copy(
        update={"initial_investment_usd": 75_000}
    )
    detached["__interrupt__"][0].value["draft_policy"] = calculate_policy(
        alternate_profile
    ).model_dump(mode="json")
    before = deepcopy(detached)

    validate_revision_state(detached)
    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(detached)

    assert detached == before
    assert adapters.retrieval_calls == adapters.provider_calls == 1


def test_detached_interrupt_cannot_hide_all_checkpointed_review_artifacts() -> None:
    _graph, _config, parent, adapters, _saver = start()
    detached = deepcopy(parent)
    for field in (
        "candidate_evidence",
        "candidate_screening",
        "portfolio_construction",
        "draft_explanation",
    ):
        detached["__interrupt__"][0].value.pop(field)
    before = deepcopy(detached)

    validate_revision_state(detached)
    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(detached)

    assert detached == before
    assert adapters.retrieval_calls == adapters.provider_calls == 1


def test_planner_is_pure_and_round_trips() -> None:
    _, _, parent, _, _ = start()
    inputs = parent["revision_ledger"]["revisions"][0]["inputs"]
    original = deepcopy(inputs)
    decision = ReviewDecision.model_validate(review_decision(parent, "edit", FEEDBACK))
    assert plan_revision(decision, inputs) == plan_revision(decision, inputs)
    assert inputs == original
    assert ReviewDecision.model_validate_json(decision.model_dump_json()) == decision


def test_injected_clock_is_retained_in_revision_and_receipts() -> None:
    now = datetime(2026, 9, 5, tzinfo=UTC)
    adapters = Adapters()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=adapters,
        explanation_generator=adapters,
        clock=lambda: now,
    )
    state = graph.invoke({"profile": valid_profile()}, {"configurable": {"thread_id": "clock"}})
    revision = validate_revision_state(state).revisions[-1]
    assert revision.created_at == now
    assert all(r.started_at == r.completed_at == now for r in revision.receipts)


@pytest.mark.parametrize("stage", ["retrieve_candidate_evidence", "draft_explanation"])
def test_started_receipt_commit_failure_prevents_adapter_call(stage: str) -> None:
    class FailingCheckpointSaver(InMemorySaver):
        def put(self, config: Any, checkpoint: Any, metadata: Any, new_versions: Any) -> Any:
            state = checkpoint["channel_values"]
            ledger = state.get("revision_ledger", {})
            revisions = ledger.get("revisions", [])
            if revisions and any(
                r["stage"] == stage and r["status"] == "started" for r in revisions[-1]["receipts"]
            ):
                raise RuntimeError("simulated checkpoint commit failure")
            return super().put(config, checkpoint, metadata, new_versions)

    adapters = Adapters()
    graph = build_graph(
        checkpointer=FailingCheckpointSaver(),
        candidate_retriever=adapters,
        explanation_generator=adapters,
    )
    with pytest.raises(RuntimeError, match="simulated checkpoint commit failure"):
        graph.invoke(
            {"profile": valid_profile()}, {"configurable": {"thread_id": "commit-failure"}}
        )
    assert adapters.retrieval_calls == (0 if stage == "retrieve_candidate_evidence" else 1)
    assert adapters.provider_calls == 0


@pytest.mark.parametrize("durability", ["async", "exit"])
def test_unsafe_durability_override_blocks_before_adapters(durability: str) -> None:
    adapters = Adapters()
    graph = build_graph(
        checkpointer=InMemorySaver(), candidate_retriever=adapters, explanation_generator=adapters
    )
    result = graph.invoke(
        {"profile": valid_profile()},
        {"configurable": {"thread_id": "durability"}},
        durability=durability,
    )
    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 0


def test_cross_thread_restore_blocks_before_adapter_or_review() -> None:
    graph, config, _parent, adapters, saver = start()
    state = dict(graph.get_state(config).values)
    other_config = {"configurable": {"thread_id": "different-thread"}}
    graph.update_state(other_config, state, as_node="prepare_draft_explanation")
    restored = build_graph(
        checkpointer=saver, candidate_retriever=adapters, explanation_generator=adapters
    )
    result = restored.invoke(None, other_config)
    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1


@pytest.mark.parametrize("field", ["revision_ledger", "revision_digest"])
def test_missing_restored_revision_metadata_cannot_initialize_new_run(field: str) -> None:
    graph, config, _parent, adapters, _saver = start()
    state = dict(graph.get_state(config).values)
    state.pop(field)
    new_config = {"configurable": {"thread_id": "missing-ledger"}}
    result = graph.invoke(state, new_config)
    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1


def test_retry_cannot_reexecute_successful_receipt() -> None:
    graph, config, state, adapters, _ = start()
    revision = validate_revision_state(state).revisions[-1]
    result = graph.invoke(
        {
            "retry_request": {
                "action": "retry",
                "revision_id": revision.revision_id,
                "operation_id": revision.receipts[-1].operation_id,
            }
        },
        config,
    )
    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1


@pytest.mark.parametrize(
    "tamper", ["parent", "trigger", "own_decision", "plan", "profile_version", "artifact"]
)
def test_child_lineage_tampering_fails_semantic_validation(tamper: str) -> None:
    graph, config, parent, adapters, saver = start()
    graph.invoke(Command(resume=review_decision(parent, "edit", [FEEDBACK[4]])), config)
    altered = deepcopy(dict(graph.get_state(config).values))
    revisions = altered["revision_ledger"]["revisions"]
    child = revisions[-1]
    if tamper == "parent":
        child["parent_revision_id"] = "foreign-parent"
    elif tamper == "trigger":
        child["triggering_decision_id"] = "foreign-decision"
    elif tamper == "own_decision":
        child["review_decision_id"] = revisions[0]["review_decision_id"]
    elif tamper == "plan":
        child["plan"]["restart_stage"] = "construct_portfolio"
    elif tamper == "profile_version":
        child["profile_version_id"] = child["artifacts"]["draft_policy"]
    else:
        child["artifacts"]["candidate_evidence"] = child["artifacts"]["draft_policy"]
    altered["revision_digest"] = digest(_sealed_values(altered))
    graph.update_state(config, altered, as_node="draft_explanation")
    restored = build_graph(checkpointer=saver)
    result = restored.invoke(None, config)
    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == 1
    assert adapters.provider_calls == 2


def test_snapshot_identity_is_explicit_and_mixed_or_partial_identity_blocks() -> None:
    from etf_advisor.domain.profile import InvestorProfile
    from etf_advisor.rag.evidence import CandidateEvidenceBundle

    bundle = _current_evidence_retriever().retrieve(InvestorProfile.model_validate(valid_profile()))
    assert bundle.snapshot_version == "local-synthetic-v1"
    assert len(bundle.snapshot_digest) == 64
    payload = bundle.model_dump(mode="json")
    payload["snapshot_version"] = None
    payload["snapshot_digest"] = None
    for candidate in payload["candidates"]:
        candidate["metadata"].update(snapshot_version="published-v1", snapshot_digest="a" * 64)
    published = CandidateEvidenceBundle.model_validate(payload)
    assert published.snapshot_version == "published-v1"
    assert published.snapshot_digest == "a" * 64
    for mutation in ("mixed", "missing", "tampered"):
        altered = deepcopy(published.model_dump(mode="json"))
        if mutation == "mixed":
            altered["candidates"][0]["metadata"]["snapshot_version"] = "published-v2"
        elif mutation == "missing":
            del altered["candidates"][0]["metadata"]["snapshot_digest"]
        else:
            altered["snapshot_digest"] = "b" * 64
        with pytest.raises(ValueError, match="snapshot identit"):
            CandidateEvidenceBundle.model_validate(altered)


@pytest.mark.parametrize(
    "decision", [None, [], "approve", {"action": "approve", "note": float("nan")}]
)
def test_malformed_resume_fails_closed_without_non_json_state(decision: Any) -> None:
    graph, config, _state, adapters, _saver = start()
    # LangGraph reserves None to mean no resume; a list/string exercises non-object input.
    command_value = {"action": None} if decision is None else decision
    result = graph.invoke(Command(resume=command_value), config)
    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1
    json.dumps(dict(graph.get_state(config).values), allow_nan=False)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "Please buy SPY.",
        "SPY is recommended for you.",
        "SPY shall outperform.",
        "Please purchase cost-efficient SPY.",
        "Please trade volume-weighted SPY.",
        "Please hold period-sensitive SPY.",
        "SPY shall not only outperform but also gain.",
        "SPY is not only recommended for you; it is preferred.",
        "Please do not only buy SPY, but also hold SPY.",
        "Please do not buy SPY but buy QQQ.",
        "Please do not buy SPY;Please buy QQQ.",
        "Please do not buy SPY,but please buy QQQ.",
        "Please, buy SPY.",
        "Please kindly buy SPY.",
        "SPY is highly recommended for you.",
    ],
)
def test_matching_receipt_digest_does_not_bypass_output_safety_validation(
    unsafe_text: str,
) -> None:
    graph, config, _state, adapters, saver = start()
    altered = deepcopy(dict(graph.get_state(config).values))
    receipt = altered["revision_ledger"]["revisions"][-1]["receipts"][-1]
    output = altered["revision_ledger"]["artifacts"][receipt["output_id"]]
    output["value"]["explanation"]["summary"]["text"] = unsafe_text
    output["digest"] = receipt["output_digest"] = digest(output["value"])
    altered["draft_explanation"] = deepcopy(output["value"])
    altered["revision_digest"] = digest(_sealed_values(altered))
    graph.update_state(config, altered, as_node="prepare_draft_explanation")
    restored = build_graph(
        checkpointer=saver, candidate_retriever=adapters, explanation_generator=adapters
    )
    result = restored.invoke(None, config)
    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1
    assert unsafe_text not in json.dumps(result.get("explanation_errors", []))
    receipts = validate_revision_state(result).revisions[-1].receipts
    assert len(receipts) == 2
    assert receipts[-1].attempt == 1
    assert "__interrupt__" not in result


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "Please buy SPY.",
        "SPY is recommended for you.",
        "SPY shall outperform.",
        "Please purchase cost-efficient SPY.",
        "Please trade volume-weighted SPY.",
        "Please hold period-sensitive SPY.",
        "SPY shall not only outperform but also gain.",
        "SPY is not only recommended for you; it is preferred.",
        "Please do not only buy SPY, but also hold SPY.",
        "Please do not buy SPY but buy QQQ.",
        "Please do not buy SPY;Please buy QQQ.",
        "Please do not buy SPY,but please buy QQQ.",
        "Please, buy SPY.",
        "Please kindly buy SPY.",
        "SPY is highly recommended for you.",
    ],
)
def test_restored_revision_review_revalidates_new_prohibited_forms(
    unsafe_text: str,
) -> None:
    graph, config, _state, adapters, saver = start()
    altered = deepcopy(dict(graph.get_state(config).values))
    receipt = altered["revision_ledger"]["revisions"][-1]["receipts"][-1]
    output = altered["revision_ledger"]["artifacts"][receipt["output_id"]]
    output["value"]["explanation"]["summary"]["text"] = unsafe_text
    output["digest"] = receipt["output_digest"] = digest(output["value"])
    altered["draft_explanation"] = deepcopy(output["value"])
    altered["revision_digest"] = digest(_sealed_values(altered))
    graph.update_state(config, altered, as_node="draft_explanation")
    restored = build_graph(checkpointer=saver)

    result = restored.invoke(None, config)

    assert result["status"] == "revision_blocked"
    assert adapters.retrieval_calls == adapters.provider_calls == 1
    assert "__interrupt__" not in result


@pytest.mark.parametrize(
    "allowed_text",
    [
        "Please do not buy SPY.",
        "SPY is not recommended for you.",
        "SPY shall not outperform.",
        "Please do not purchase cost-efficient SPY.",
        "Please do not trade volume-weighted SPY.",
        "Please do not hold period-sensitive SPY.",
        "SPY shall not outperform; it may gain.",
        "SPY is not recommended for you; it is discussed for context.",
        "Please do not buy SPY; compare it for context.",
        "Please do not buy SPY but do not buy QQQ.",
        "Please do not buy SPY;Please do not buy QQQ.",
        "Please do not buy SPY,but please do not buy QQQ.",
        "Please, do not buy SPY.",
        "Please kindly do not buy SPY.",
        "SPY is not highly recommended for you.",
        "Trade volume has increased.",
        "Trade volume reflects liquidity.",
        "Purchase costs depend on the broker.",
        "Hold periods depend on the objective.",
    ],
)
def test_successful_explanation_receipt_reuse_accepts_explicit_negation(
    allowed_text: str,
) -> None:
    graph, config, _state, adapters, saver = start()
    altered = deepcopy(dict(graph.get_state(config).values))
    receipt = altered["revision_ledger"]["revisions"][-1]["receipts"][-1]
    output = altered["revision_ledger"]["artifacts"][receipt["output_id"]]
    output["value"]["explanation"]["summary"]["text"] = allowed_text
    output["digest"] = receipt["output_digest"] = digest(output["value"])
    altered["draft_explanation"] = deepcopy(output["value"])
    altered["revision_digest"] = digest(_sealed_values(altered))
    graph.update_state(config, altered, as_node="prepare_draft_explanation")
    restored = build_graph(
        checkpointer=saver, candidate_retriever=adapters, explanation_generator=adapters
    )

    result = restored.invoke(None, config)

    assert result["status"] == "awaiting_human_review"
    assert adapters.retrieval_calls == adapters.provider_calls == 1
    assert validate_revision_state(result).revisions[-1].receipts[-1].attempt == 1
    json.dumps(dict(restored.get_state(config).values), allow_nan=False)


def test_dashboard_adapter_submits_typed_revision_and_close() -> None:
    from etf_advisor.dashboard import DashboardRun

    graph, config, state, _adapters, _saver = start(evidence=False)
    run = DashboardRun(graph=graph, config=config, state=state)
    child = run.resume(
        "edit", "Change the initial amount.", disposition="revise", feedback_items=[FEEDBACK[0]]
    )
    assert child["status"] == "awaiting_human_review"
    assert child["profile"]["initial_investment_usd"] == 60_000
    closed = run.resume("reject", "Close this draft.", disposition="close")
    assert closed["status"] == "rejected"
    assert len(validate_revision_state(closed).decisions) == 2
