"""Audit identifier injection and replay regressions for PR #45."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from test_revision import FEEDBACK, Adapters, start
from test_workflow import valid_profile

from etf_advisor.graph.revision import RevisionRuntime, current_inputs, validate_revision_state
from etf_advisor.graph.workflow import build_graph

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)


class SequentialIdentifiers:
    def __init__(self, next_number: int = 1) -> None:
        self.next_number = next_number
        self.generated: list[str] = []

    def __call__(self) -> str:
        identifier = f"audit-{self.next_number}"
        self.next_number += 1
        self.generated.append(identifier)
        return identifier


def test_injected_identifiers_reproduce_root_retry_and_child_audit_state() -> None:
    states = []
    for _ in range(2):
        identifiers, adapters = SequentialIdentifiers(), Adapters()
        adapters.fail_retrieval = True
        graph = build_graph(
            checkpointer=InMemorySaver(),
            candidate_retriever=adapters,
            explanation_generator=adapters,
            clock=lambda: NOW,
            identifier_factory=identifiers,
        )
        config = {"configurable": {"thread_id": "reproducible-audit"}}
        failed = graph.invoke({"profile": valid_profile()}, config)
        revision = validate_revision_state(failed).revisions[-1]
        assert failed["status"] == "evidence_blocked"
        adapters.fail_retrieval = False
        reviewed = graph.invoke(
            {
                "retry_request": {
                    "action": "retry",
                    "revision_id": revision.revision_id,
                    "operation_id": revision.receipts[-1].operation_id,
                }
            },
            config,
        )
        assert reviewed["status"] == "awaiting_human_review"
        revised = graph.invoke(
            Command(
                resume={
                    "decision_id": "reviewer-decision",
                    "revision_id": revision.revision_id,
                    "action": "edit",
                    "disposition": "revise",
                    "note": "Update the initial amount.",
                    "feedback": [FEEDBACK[0]],
                    "submitted_at": NOW.isoformat(),
                }
            ),
            config,
        )
        assert revised["status"] == "awaiting_human_review"
        state = dict(graph.get_state(config).values)
        ledger = validate_revision_state(state)
        allocated = set(ledger.artifacts)
        allocated.update(revision.revision_id for revision in ledger.revisions)
        allocated.update(
            receipt.operation_id for revision in ledger.revisions for receipt in revision.receipts
        )
        assert allocated == set(identifiers.generated)
        assert len(allocated) == len(identifiers.generated)
        assert ledger.revisions[0].profile_version_id != ledger.revisions[1].profile_version_id
        assert [
            r.attempt
            for r in ledger.revisions[0].receipts
            if r.stage == "retrieve_candidate_evidence"
        ] == [1, 2]
        states.append(state)
    assert states[0] == states[1]


def test_uncommitted_prepare_can_be_reproduced_with_restored_identifier_sequence() -> None:
    class FailingPrepareSaver(InMemorySaver):
        def __init__(self) -> None:
            super().__init__()
            self.prepared_ledgers: list[dict[str, Any]] = []
            self.fail = True

        def put(self, config: Any, checkpoint: Any, metadata: Any, new_versions: Any) -> Any:
            state = checkpoint["channel_values"]
            if state.get("status") == "operation_prepared":
                self.prepared_ledgers.append(deepcopy(state["revision_ledger"]))
                if self.fail:
                    raise RuntimeError("uncommitted prepare")
            return super().put(config, checkpoint, metadata, new_versions)

    saver, identifiers, adapters = FailingPrepareSaver(), SequentialIdentifiers(), Adapters()
    config = {"configurable": {"thread_id": "replayed-prepare"}}
    graph = build_graph(
        checkpointer=saver,
        candidate_retriever=adapters,
        clock=lambda: NOW,
        identifier_factory=identifiers,
    )
    graph.invoke(
        {"profile": valid_profile()},
        config,
        interrupt_before=["prepare_retrieve_candidate_evidence"],
    )
    assert graph.get_state(config).next == ("prepare_retrieve_candidate_evidence",)
    committed_state = deepcopy(graph.get_state(config).values)
    committed_cursor = identifiers.next_number
    with pytest.raises(RuntimeError, match="uncommitted prepare"):
        graph.invoke(None, config)
    assert adapters.retrieval_calls == 0
    # Reproduce the transition from its prior state and factory cursor. Pending LangGraph
    # writes may survive a checkpoint failure, so do not bypass the restore/retry guards.
    restored = RevisionRuntime(
        inputs=current_inputs(committed_state),
        clock=lambda: NOW,
        identifier_factory=SequentialIdentifiers(committed_cursor),
    )
    result = restored.prepare(committed_state, "retrieve_candidate_evidence")
    assert result["status"] == "operation_prepared"
    assert result["revision_ledger"] == saver.prepared_ledgers[0]
    assert adapters.retrieval_calls == 0
    validate_revision_state(result)


def test_success_reuse_and_approval_do_not_allocate_new_identifiers() -> None:
    _graph, config, _state, adapters, saver = start()

    def unexpected_identifier() -> str:
        raise AssertionError("Restore and success reuse must retain saved identities.")

    restored = build_graph(
        checkpointer=saver,
        candidate_retriever=adapters,
        explanation_generator=adapters,
        identifier_factory=unexpected_identifier,
    )
    restored.update_state(config, {}, as_node="prepare_draft_explanation")
    paused = restored.invoke(None, config)
    revision = validate_revision_state(paused).revisions[-1]
    result = restored.invoke(
        Command(
            resume={
                "decision_id": "approval",
                "revision_id": revision.revision_id,
                "action": "approve",
                "submitted_at": datetime.now(UTC).isoformat(),
            }
        ),
        config,
    )
    assert result["status"] == "approved"
    assert adapters.retrieval_calls == adapters.provider_calls == 1


def test_identifier_collision_cannot_overwrite_a_retained_artifact() -> None:
    adapters = Adapters()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=adapters,
        identifier_factory=lambda: "duplicate-artifact",
    )
    result = graph.invoke(
        {"profile": valid_profile()}, {"configurable": {"thread_id": "id-collision"}}
    )
    assert result["status"] == "revision_blocked"
    ledger = validate_revision_state(result)
    assert len(ledger.artifacts) == 1
    assert ledger.artifacts["duplicate-artifact"].value == result["profile"]
    assert adapters.retrieval_calls == 0
