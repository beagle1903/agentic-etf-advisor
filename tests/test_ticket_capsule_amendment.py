"""Test-only historical Issue123 prefix and explicitly synthetic later authorities."""

import copy
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ticket_workflow as workflow  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/issue123-original31.json"
NOW = datetime(2026, 10, 29, tzinfo=UTC)
AT = datetime(2026, 10, 28, tzinfo=UTC)
SYNTHETIC_AUTHORITY = {
    "kind": "user",
    "name": "synthetic-test-user",
    "evidence": "Synthetic distinct operational Issue123 amendment authorization for tests only",
}


def source():
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(value["events"]) == 31
    assert workflow.digest(value) == workflow.AMENDMENT_PREFIX_DIGEST
    return value


def synthetic_amendment(value, approval=None, seconds=0):
    approval = copy.deepcopy(approval or SYNTHETIC_AUTHORITY)
    old = workflow.replay(value, NOW).capsule
    replacement, changes = workflow.amendment_target(old, approval)
    prefix = {"event_count": len(value["events"]), "digest": workflow.digest(value)}
    return {
        "type": "capsule_amendment",
        "at": (AT + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": {
            "amendment": workflow.AMENDMENT_VERSION,
            "authority": approval,
            "capsule": workflow.capsule_ref(old),
            "source_history": prefix,
            "replacement": replacement,
            "target": workflow.capsule_ref(replacement),
            "changes": changes,
            "reason": "Synthetic test of the exact governance amendment only",
        },
    }


def amended(approval=None):
    value = source()
    value["events"].append(synthetic_amendment(value, approval))
    return value


def append(value, kind, offset, **data):
    value["events"].append(
        {
            "type": kind,
            "at": (AT + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": data,
        }
    )


def phase(value, name, start, session, role, outcome="pass", **extra):
    cap = workflow.capsule_ref(workflow.replay(value, NOW).capsule)
    append(
        value, "phase_start", start, phase=name, session=session, role=role, capsule=cap, **extra
    )
    append(
        value,
        "phase_end",
        start + 1,
        session=session,
        outcome=outcome,
        evidence="Synthetic phase evidence only",
    )


def test_exact_target_clears_only_current_success_and_preserves_historical_debt():
    value = source()
    old = workflow.replay(value, NOW)
    value["events"].append(synthetic_amendment(value))
    updated = workflow.replay(value, NOW)
    assert updated.classification == "consequential"
    assert updated.capsule["generation"] == 3
    assert updated.capsule["authorization"] == SYNTHETIC_AUTHORITY
    assert updated.approved_owner == old.approved_owner
    for field in (
        "counts",
        "limits",
        "local_counts",
        "inherited_counts",
        "blockers",
        "sessions",
        "write_authors",
        "pending_repair",
        "verification_repair_count",
        "initial_failed",
        "final_failed",
        "delivery_history",
    ):
        assert getattr(updated, field) == getattr(old, field)
    assert updated.elapsed_seconds == old.elapsed_seconds + int((AT - old.last).total_seconds())
    assert updated.design_started and not updated.ready and not updated.challenge_ok
    assert (
        not updated.verified
        and not updated.accepted
        and not updated.reviewed
        and not updated.remediated
    )
    for field in (
        "design_session",
        "challenge_session",
        "author_session",
        "design_ref",
        "challenge_ref",
        "approved_ref",
        "verified_content",
        "acceptance_content",
        "review_content",
    ):
        assert getattr(updated, field) is None
    assert updated.capsule_amendment["source"] == workflow.AMENDMENT_SOURCE
    assert updated.capsule_amendment["target"] == workflow.capsule_ref(updated.capsule)
    assert len(workflow.authority_records(value)) >= 2
    assert workflow.authority_records(value)[-1]["class"] == "capsule_amendment"
    assert workflow.validate_map({123: value}, NOW)[123].capsule == updated.capsule
    with pytest.raises(workflow.Invalid, match="design_reset slot"):
        updated.gate("design", NOW)
    with pytest.raises(workflow.Invalid, match="design_reset lifetime limit"):
        updated.gate("design_reset", NOW)
    with pytest.raises(workflow.Invalid, match="implementation lifetime limit"):
        updated.gate("implementation", NOW)


@pytest.mark.parametrize(
    "damage",
    [
        lambda e: e["data"].update(amendment="unknown"),
        lambda e: e["data"].update(reason=None),
        lambda e: e["data"].update(extra=True),
        lambda e: e["data"].pop("changes"),
        lambda e: e["data"]["source_history"].update(event_count=True),
        lambda e: e["data"]["source_history"].update(digest="0" * 64),
        lambda e: e["data"]["target"].update(digest="0" * 64),
        lambda e: e["data"]["replacement"].update(generation=4),
        lambda e: e["data"]["changes"]["classification"].update(after="ordinary"),
        lambda e: e["data"]["authority"].update(kind="coordinator"),
    ],
)
def test_exact_amendment_rejects_malformed_or_rebound_event(damage):
    value = amended()
    damage(value["events"][-1])
    with pytest.raises(workflow.Invalid):
        workflow.replay(value, NOW)


@pytest.mark.parametrize(
    "presentation",
    [
        lambda value: value,
        lambda value: value.upper(),
        lambda value: "  " + value + "  ",
        lambda value: value.replace(" ", "  "),
        lambda value: "".join(
            chr(ord(ch) + 0xFEE0) if 33 <= ord(ch) <= 126 else ch for ch in value
        ),
        lambda value: "  ".join(
            "".join(chr(ord(ch) + 0xFEE0) if 33 <= ord(ch) <= 126 else ch for ch in word)
            for word in value.upper().split()
        ),
    ],
)
def test_governance_approval_cannot_apply_operational_amendment(presentation):
    governance = json.loads(
        (ROOT / "docs/workflow/tickets/issue-128.json").read_text(encoding="utf-8")
    )
    evidence = governance["events"][0]["data"]["capsule"]["authorization"]["evidence"]
    assert (
        workflow.digest(workflow.normalized_evidence(evidence))
        == workflow.GOVERNANCE_APPROVAL_DIGEST
    )
    for name in ("burha", "renamed human"):
        authority = {"kind": "user", "name": name, "evidence": presentation(evidence)}
        value = amended(authority)
        with pytest.raises(workflow.Invalid, match="governance approval"):
            workflow.replay(value, NOW)


def test_distinct_synthetic_authority_passes_and_source_authority_reuse_fails():
    value = amended()
    assert workflow.replay(value, NOW).capsule["classification"] == "consequential"
    source_authority = source()["events"][0]["data"]["capsule"]["authorization"]
    with pytest.raises(workflow.Invalid, match="already consumed"):
        workflow.replay(amended(source_authority), NOW)


def test_original_prefix_tamper_and_repeated_amendment_reject():
    value = source()
    value["events"][0]["data"]["authority"]["name"] = "tampered"
    value["events"].append(synthetic_amendment(value))
    with pytest.raises(workflow.Invalid, match="immutable history prefix"):
        workflow.replay(value, NOW)
    value = amended()
    repeated = copy.deepcopy(value["events"][-1])
    repeated["at"] = (AT + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    value["events"].append(repeated)
    with pytest.raises(workflow.Invalid):
        workflow.replay(value, NOW)


def test_valid_planning_suffix_is_bound_and_pause_cannot_be_amended():
    value = source()
    coordinator = {"kind": "coordinator", "name": "synthetic", "evidence": "planning only"}
    append(
        value,
        "coordination_pause",
        -3,
        authority=coordinator,
        evidence="Synthetic offline planning pause",
    )
    bad = copy.deepcopy(value)
    bad["events"].append(synthetic_amendment(bad))
    with pytest.raises(workflow.Invalid, match="between-phase"):
        workflow.replay(bad, NOW)
    append(
        value,
        "coordination_resume",
        -2,
        authority=coordinator,
        evidence="Synthetic planning resume",
    )
    value["events"].append(synthetic_amendment(value))
    assert workflow.replay(value, NOW).capsule_amendment["source_history"]["event_count"] == 33
    value["events"][-1]["data"]["source_history"]["digest"] = workflow.AMENDMENT_PREFIX_DIGEST
    with pytest.raises(workflow.Invalid, match="complete history"):
        workflow.replay(value, NOW)


def test_synthetic_finite_grant_fresh_design_and_target_work_route():
    value = amended()
    amended_state = workflow.replay(value, NOW)
    with pytest.raises(workflow.Invalid):
        attempted = copy.deepcopy(value)
        phase(attempted, "design", 1, "synthetic-architect", "design_architect")
        workflow.replay(attempted, NOW)
    append(
        value,
        "extension",
        1,
        authority={
            "kind": "user",
            "name": "synthetic",
            "evidence": "Synthetic separate finite grant for reset and implementation",
        },
        seconds=0,
        counts={
            "implementation": 1,
            "initial_review": 0,
            "remediation": 0,
            "final_review": 0,
            "design_reset": 1,
        },
        reason="Synthetic finite count grant for test only",
    )
    assert workflow.replay(value, NOW).counts == amended_state.counts
    phase(
        value,
        "design_reset",
        2,
        "synthetic-new-architect",
        "design_architect",
        criterion="INV123-1",
        reason="Synthetic target design",
    )
    assert workflow.replay(value, NOW).capsule["generation"] == 4
    with pytest.raises(workflow.Invalid, match="approved DESIGN_READY"):
        workflow.replay(value, NOW).gate("implementation", NOW)
    phase(value, "challenge", 4, "synthetic-independent-challenge", "code_reviewer")
    append(
        value,
        "design_ready",
        6,
        authority={
            "kind": "coordinator",
            "name": "synthetic",
            "evidence": "Synthetic coordinator design approval",
        },
        evidence="Synthetic target design ready",
        capsule=workflow.capsule_ref(workflow.replay(value, NOW).capsule),
    )
    approved = workflow.replay(value, NOW)
    assert approved.ready and approved.challenge_ok and not approved.author_session
    with pytest.raises(workflow.Invalid, match="completed implementation"):
        attempted = copy.deepcopy(value)
        append(
            attempted,
            "acceptance",
            7,
            ids=approved.acceptance,
            evidence="stale",
            capsule=workflow.capsule_ref(approved.capsule),
            content="0" * 64,
        )
        workflow.replay(attempted, NOW)
    phase(value, "implementation", 7, approved.approved_owner["session"], "implementation_worker")
    implemented = workflow.replay(value, NOW)
    assert implemented.author_session == approved.approved_owner["session"]
    assert implemented.counts["implementation"] == amended_state.counts["implementation"] + 1
    assert implemented.blockers == amended_state.blockers
    assert not implemented.remediated
    with pytest.raises(workflow.Invalid, match="blocker resolution"):
        attempted = copy.deepcopy(value)
        append(
            attempted,
            "resolve",
            9,
            id="B123-REFERENCE",
            evidence="stale remediation must not count",
        )
        workflow.replay(attempted, NOW)
    phase(value, "remediation", 9, approved.approved_owner["session"], "implementation_worker")
    append(value, "resolve", 11, id="B123-REFERENCE", evidence="Synthetic target remediation")
    append(value, "resolve", 12, id="B123-ELIGIBLE-POOL", evidence="Synthetic target remediation")
    content = "a" * 64
    phase(
        value,
        "verification",
        13,
        approved.approved_owner["session"],
        "implementation_worker",
        content=content,
    )
    append(
        value,
        "acceptance",
        15,
        ids=approved.acceptance,
        evidence="Synthetic frozen acceptance",
        capsule=workflow.capsule_ref(workflow.replay(value, NOW).capsule),
        content=content,
    )
    phase(
        value,
        "final_review",
        16,
        "synthetic-independent-final-review",
        "code_reviewer",
        content=content,
    )
    final = workflow.replay(value, NOW)
    assert final.counts["remediation"] == amended_state.counts["remediation"] + 1
    assert final.counts["final_review"] == amended_state.counts["final_review"] + 1
    assert final.ready and final.verified and final.accepted and final.reviewed
    assert not final.blockers
    final.gate("delivery", NOW)


def test_amendment_authority_cannot_be_reused_for_later_grant():
    value = amended()
    append(
        value,
        "extension",
        1,
        authority={**SYNTHETIC_AUTHORITY, "name": "renamed"},
        seconds=0,
        counts={
            "implementation": 1,
            "initial_review": 0,
            "remediation": 0,
            "final_review": 0,
            "design_reset": 0,
        },
        reason="Synthetic reuse attempt",
    )
    with pytest.raises(workflow.Invalid, match="already consumed"):
        workflow.replay(value, NOW)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("repo", "another/repository"),
        ("issue", 124),
        ("policy", "timed-v1"),
        ("classification", "consequential"),
        ("review_required", False),
        ("active", {"phase": "implementation"}),
        ("suspended", {"phase": "implementation"}),
        ("clock_running", False),
        ("delivered", True),
        ("delivery_history", [{"pr": 1}]),
        ("retired", True),
        ("split_remaining", 0),
        ("split_pool", {}),
        ("splits", {124: {}}),
        ("predecessor", True),
        ("ancestry", [100]),
        ("retained_reservation_open", True),
        ("final_failed", True),
    ],
)
def test_pure_admission_rejects_prohibited_source_or_lifecycle(field, bad):
    value = source()
    event = synthetic_amendment(value)
    current = workflow.replay(value, NOW)
    setattr(current, field, bad)
    with pytest.raises(workflow.Invalid):
        workflow.admit_capsule_amendment(current, value, len(value["events"]), event["data"])


def test_atomic_append_invalid_event_preserves_historical_bytes(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    target = tmp_path / workflow.DIRECTORY / "issue-123.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(FIXTURE.read_bytes())
    before = target.read_bytes()
    value = source()
    bad = synthetic_amendment(value)
    bad["data"]["target"]["digest"] = "0" * 64
    with pytest.raises(workflow.Invalid):
        workflow.append(tmp_path, 123, bad, NOW)
    assert target.read_bytes() == before
    assert not (target.parent / "repository.lock").exists()
    accepted = workflow.append(tmp_path, 123, synthetic_amendment(value), NOW)
    assert accepted.capsule_amendment is not None
    after = target.read_bytes()
    with pytest.raises(workflow.Invalid):
        workflow.append(tmp_path, 123, synthetic_amendment(value), NOW)
    assert target.read_bytes() == after
