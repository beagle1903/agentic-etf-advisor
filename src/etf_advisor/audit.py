"""Pure reconstruction of retained revision history; never allocates identities."""

from typing import Any, cast

from etf_advisor.graph.revision import validate_revision_state
from etf_advisor.graph.state import AdvisorState
from etf_advisor.rag.evidence import CandidateEvidenceBundle, EvidenceStatus


def reconstruct_audit(state: dict[str, Any], thread_id: str) -> dict[str, Any]:
    """Return a detached JSON view, failing closed on corrupt retained references."""
    try:
        ledger = validate_revision_state(cast(AdvisorState, state), thread_id)
        revisions: list[dict[str, Any]] = []
        for revision in ledger.revisions:
            item = revision.model_dump(mode="json", exclude_none=True)
            item["profile_version"] = ledger.artifacts[revision.profile_version_id].model_dump(
                mode="json"
            )
            item["artifacts"] = {
                name: ledger.artifacts[key].model_dump(mode="json")
                for name, key in revision.artifacts.items()
            }
            evidence_id = revision.artifacts.get("candidate_evidence")
            if evidence_id:
                raw = ledger.artifacts[evidence_id].value
                evidence = CandidateEvidenceBundle.model_validate(raw)
                if evidence.status == EvidenceStatus.READY:
                    if (raw.get("snapshot_version"), raw.get("snapshot_digest")) != (
                        evidence.snapshot_version,
                        evidence.snapshot_digest,
                    ):
                        raise ValueError("Missing snapshot identity.")
                    item["snapshot"] = {
                        "version": evidence.snapshot_version,
                        "digest": evidence.snapshot_digest,
                    }
            if revision.review_decision_id:
                item["decision"] = ledger.decisions[revision.review_decision_id].model_dump(
                    mode="json"
                )
            item["child_revision_ids"] = [
                child.revision_id
                for child in ledger.revisions
                if child.parent_revision_id == revision.revision_id
            ]
            revisions.append(item)
        return {"schema_version": 1, "thread_id": thread_id, "revisions": revisions}
    except (KeyError, TypeError, ValueError, IndexError):
        raise ValueError("Saved audit failed contract validation.") from None
