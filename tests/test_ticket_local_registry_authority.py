"""Historical Issue123 prefix; every appended authority and outcome is synthetic."""

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

FIXTURE = ROOT / "tests/fixtures/issue123-original41.json"
NOW = datetime(2026, 10, 30, 8, 20, tzinfo=UTC)
AT = datetime(2026, 10, 30, 8, 5, tzinfo=UTC)
AUTH = {
    "kind": "user",
    "name": "synthetic-test-user",
    "evidence": "Synthetic distinct local registry operational approval for tests only",
}


def source():
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(value["events"]) == 41
    assert workflow.digest(value) == workflow.LOCAL_REGISTRY_PREFIX_DIGEST
    assert (
        workflow.capsule_ref(workflow.replay(value, NOW).capsule) == workflow.LOCAL_REGISTRY_SOURCE
    )
    return value


def transition(value, auth=None, offset=0):
    auth = copy.deepcopy(auth or AUTH)
    old = workflow.replay(value, NOW).capsule
    replacement, changes = workflow.local_registry_target(old, auth)
    return {
        "type": "local_registry_authority",
        "at": (AT + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": {
            "transition": workflow.LOCAL_REGISTRY_VERSION,
            "authority": auth,
            "capsule": workflow.capsule_ref(old),
            "source_history": {
                "event_count": len(value["events"]),
                "digest": workflow.digest(value),
            },
            "replacement": replacement,
            "target": workflow.capsule_ref(replacement),
            "changes": changes,
            "reason": "Synthetic bounded local authority test only",
        },
    }


def changed():
    value = source()
    value["events"].append(transition(value))
    return value


def append(value, kind, offset, **data):
    value["events"].append(
        {
            "type": kind,
            "at": (AT + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": data,
        }
    )


def phase(value, name, offset, session, role, outcome="pass", **extra):
    cap = workflow.capsule_ref(workflow.replay(value, NOW).capsule)
    append(
        value, "phase_start", offset, phase=name, session=session, role=role, capsule=cap, **extra
    )
    append(
        value,
        "phase_end",
        offset + 1,
        session=session,
        outcome=outcome,
        evidence="Synthetic phase result only",
    )


def test_exact_eight_path_target_and_preserved_history():
    value = source()
    prior = workflow.replay(value, NOW)
    event = transition(value)
    value["events"].append(event)
    state = workflow.replay(value, NOW)
    assert list(event["data"]["changes"]["definitions"]) == [
        "scope.S123-1",
        "non_goals[1]",
        "invariants.INV123-3",
        "interfaces",
        "json_state_impact",
        "acceptance.AC123-2",
        "acceptance.AC123-5",
        "verification[0]",
    ]
    assert state.capsule["generation"] == 5
    assert state.capsule["authorization"] == AUTH
    assert state.capsule_amendment == prior.capsule_amendment
    assert state.local_registry_authority["source"] == workflow.LOCAL_REGISTRY_SOURCE
    assert state.local_registry_authority["target"] == workflow.capsule_ref(state.capsule)
    for field in (
        "classification",
        "approved_owner",
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
        "delivery_binding",
        "historical_transition",
        "extension_authorizations",
    ):
        assert getattr(state, field) == getattr(prior, field)
    assert state.design_started
    for field in ("ready", "challenge_ok", "verified", "accepted", "reviewed", "remediated"):
        assert not getattr(state, field)
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
        assert getattr(state, field) is None
    assert workflow.authority_records(value)[-1]["class"] == "local_registry_authority"
    assert workflow.validate_map({123: value}, NOW)[123].capsule == state.capsule
    with pytest.raises(workflow.Invalid, match="design_reset slot"):
        state.gate("design", NOW)
    with pytest.raises(workflow.Invalid, match="design_reset lifetime limit"):
        state.gate("design_reset", NOW)


@pytest.mark.parametrize(
    "damage",
    [
        lambda e: e["data"].update(transition="wrong"),
        lambda e: e["data"].update(extra=True),
        lambda e: e["data"].pop("changes"),
        lambda e: e["data"]["source_history"].update(event_count=True),
        lambda e: e["data"]["source_history"].update(digest="0" * 64),
        lambda e: e["data"]["capsule"].update(generation=4.0),
        lambda e: e["data"]["replacement"].update(generation=5.0),
        lambda e: e["data"]["target"].update(generation=True),
        lambda e: e["data"]["changes"].update(extra=True),
        lambda e: e["data"]["changes"]["definitions"].update(ninth={}),
        lambda e: e["data"]["changes"]["definitions"]["interfaces"].update(after=None),
        lambda e: e["data"]["changes"]["definitions"]["interfaces"].update(after=[False]),
        lambda e: e["data"]["authority"].update(kind="coordinator"),
    ],
)
def test_rejects_wrong_shape_type_or_target(damage):
    value = changed()
    damage(value["events"][-1])
    with pytest.raises(workflow.Invalid):
        workflow.replay(value, NOW)


@pytest.mark.parametrize(
    "text",
    [
        "Synthetic distinct local registry operational approval for tests only",
        "  SYNTHETIC  DISTINCT LOCAL REGISTRY OPERATIONAL APPROVAL FOR TESTS ONLY  ",
        "fullwidth variant",
    ],
)
def test_rejects_consumed_authority_even_with_new_display_name(text):
    value = source()
    original = value["events"][0]["data"]["capsule"]["authorization"]["evidence"]
    if text.startswith("  "):
        original = "  " + original.upper().replace(" ", "  ") + "  "
    elif text == "fullwidth variant":
        original = chr(ord(original[0]) + 0xFEE0) + original[1:]
    event = transition(value, {"kind": "user", "name": "new-name", "evidence": original})
    replacement, changes = workflow.local_registry_target(
        workflow.replay(value, NOW).capsule, event["data"]["authority"]
    )
    event["data"]["replacement"] = replacement
    event["data"]["target"] = workflow.capsule_ref(replacement)
    event["data"]["changes"] = changes
    value["events"].append(event)
    with pytest.raises(workflow.Invalid, match="already consumed"):
        workflow.replay(value, NOW)


@pytest.mark.parametrize(
    "approval",
    [
        workflow.GOVERNANCE_APPROVAL_DIGEST,
        workflow.ISSUE132_GOVERNANCE_APPROVAL_DIGEST,
    ],
)
def test_governance_approval_rejected_with_recomputed_valid_target(approval):
    value = source()
    if approval == workflow.ISSUE132_GOVERNANCE_APPROVAL_DIGEST:
        issue132 = json.loads(
            (ROOT / "docs/workflow/tickets/issue-132.json").read_text(encoding="utf-8")
        )
        evidence = issue132["events"][0]["data"]["capsule"]["authorization"]["evidence"]
    else:
        issue128 = json.loads(
            (ROOT / "docs/workflow/tickets/issue-128.json").read_text(encoding="utf-8")
        )
        evidence = issue128["events"][0]["data"]["capsule"]["authorization"]["evidence"]
    assert workflow.digest(workflow.normalized_evidence(evidence)) == approval
    auth = {"kind": "user", "name": "renamed-test-user", "evidence": "  " + evidence.upper() + "  "}
    value["events"].append(transition(value, auth))
    with pytest.raises(workflow.Invalid, match="governance approval"):
        workflow.replay(value, NOW)


def test_rejects_repeated_transition_and_changed_original_prefix():
    value = changed()
    duplicate = copy.deepcopy(value["events"][-1])
    duplicate["at"] = (AT + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    value["events"].append(duplicate)
    with pytest.raises(workflow.Invalid):
        workflow.replay(value, NOW)
    value = changed()
    value["events"][0]["data"]["capsule"]["scope"]["S123-1"] += " drift"
    with pytest.raises(workflow.Invalid):
        workflow.replay(value, NOW)


def test_complete_suffix_binding_and_cleared_stale_success():
    value = source()
    value["events"].append(
        {
            "type": "extension",
            "at": AT.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": {
                "authority": {
                    "kind": "user",
                    "name": "synthetic-user",
                    "evidence": "synthetic extra reset grant",
                },
                "counts": {
                    "implementation": 0,
                    "initial_review": 0,
                    "remediation": 0,
                    "final_review": 0,
                    "design_reset": 1,
                },
                "seconds": 0,
                "reason": "Synthetic grant only",
            },
        }
    )
    # Complete prefix changes; the event must bind the full current history.
    event = transition(value, offset=1)
    value["events"].append(event)
    state = workflow.replay(value, NOW)
    assert state.local_registry_authority["source_history"]["event_count"] == 42
    with pytest.raises(workflow.Invalid):
        state.gate("design", NOW)
    event["data"]["source_history"]["digest"] = workflow.LOCAL_REGISTRY_PREFIX_DIGEST
    with pytest.raises(workflow.Invalid, match="complete history"):
        workflow.replay(value, NOW)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("repo", "other/repo"),
        ("issue", 124),
        ("policy", "timed-v1"),
        ("classification", "ordinary"),
        ("review_required", False),
        ("active", {"phase": "implementation"}),
        ("suspended", {"phase": "design"}),
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
        ("capsule_amendment", None),
        ("local_registry_authority", {}),
    ],
)
def test_pure_admission_rejects_invalid_lifecycle(field, bad):
    value = source()
    event = transition(value)
    state = workflow.replay(value, NOW)
    setattr(state, field, bad)
    with pytest.raises(workflow.Invalid):
        workflow.admit_local_registry_authority(state, value, len(value["events"]), event["data"])


def synthetic_generation_six_route():
    value = changed()
    baseline = workflow.replay(value, NOW)
    append(
        value,
        "extension",
        1,
        authority={
            "kind": "user",
            "name": "synthetic",
            "evidence": "Separate synthetic reset and work grant",
        },
        seconds=0,
        counts={
            "implementation": 1,
            "initial_review": 0,
            "remediation": 0,
            "final_review": 0,
            "design_reset": 1,
        },
        reason="Synthetic finite grant only",
    )
    assert workflow.replay(value, NOW).counts == baseline.counts
    phase(
        value,
        "design_reset",
        2,
        "synthetic-new-architect",
        "design_architect",
        criterion="INV123-3",
        reason="Synthetic target design",
    )
    assert workflow.replay(value, NOW).capsule["generation"] == 6
    phase(value, "challenge", 4, "synthetic-independent-challenge", "code_reviewer")
    append(
        value,
        "design_ready",
        6,
        authority={"kind": "coordinator", "name": "synthetic", "evidence": "Synthetic approval"},
        evidence="Synthetic fresh target approval",
        capsule=workflow.capsule_ref(workflow.replay(value, NOW).capsule),
    )
    approved = workflow.replay(value, NOW)
    assert approved.ready and approved.challenge_ok and not approved.author_session
    phase(value, "implementation", 7, approved.approved_owner["session"], "implementation_worker")
    implemented = workflow.replay(value, NOW)
    assert implemented.blockers == baseline.blockers and not implemented.remediated
    phase(value, "remediation", 9, approved.approved_owner["session"], "implementation_worker")
    append(value, "resolve", 11, id="B123-REFERENCE", evidence="Synthetic remediation")
    append(value, "resolve", 12, id="B123-ELIGIBLE-POOL", evidence="Synthetic remediation")
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
    assert final.ready and final.verified and final.accepted and final.reviewed
    assert not final.blockers
    assert final.counts["design_reset"] == 3
    final.gate("delivery", NOW)
    return value


def test_synthetic_generation_six_fresh_gates_and_final_review():
    synthetic_generation_six_route()


def test_later_capsule_update_references_local_authority_without_second_grant():
    value = changed()
    append(
        value,
        "extension",
        1,
        authority={
            "kind": "user",
            "name": "synthetic",
            "evidence": "Separate synthetic reset grant",
        },
        seconds=0,
        counts={
            "implementation": 0,
            "initial_review": 0,
            "remediation": 0,
            "final_review": 0,
            "design_reset": 1,
        },
        reason="Synthetic finite grant only",
    )
    current = workflow.replay(value, NOW)
    phase_ref = workflow.capsule_ref(current.capsule)
    append(
        value,
        "phase_start",
        2,
        phase="design_reset",
        role="design_architect",
        session="synthetic-reference-architect",
        criterion="INV123-3",
        reason="Synthetic bounded revision",
        capsule=phase_ref,
    )
    revised = copy.deepcopy(workflow.replay(value, NOW).capsule)
    assert revised["generation"] == 6
    revised["authorization"] = copy.deepcopy(AUTH)
    append(
        value,
        "capsule_update",
        3,
        authority={
            "kind": "coordinator",
            "name": "synthetic",
            "evidence": "Synthetic reset record",
        },
        capsule=revised,
    )
    state = workflow.replay(value, NOW)
    records = workflow.authority_records(value)
    local_record = next(
        record for record in records if record["class"] == "local_registry_authority"
    )
    update_record = records[-1]
    assert update_record["class"] == "capsule_update"
    assert update_record["reference"] is True
    assert update_record["evidence"] == local_record["evidence"]
    assert state.authorization_history == workflow.replay(changed(), NOW).authorization_history | {
        workflow.normalized_evidence("Separate synthetic reset grant")
    }
    assert workflow.validate_map({123: value}, NOW)[123].capsule == revised


def synthetic_connected_children():
    parent = synthetic_generation_six_route()
    append(
        parent,
        "extension",
        18,
        authority={
            "kind": "user",
            "name": "synthetic",
            "evidence": "Synthetic separate split pool",
        },
        seconds=0,
        counts={
            "implementation": 2,
            "initial_review": 0,
            "remediation": 0,
            "final_review": 0,
            "design_reset": 0,
        },
        reason="Synthetic finite split allocation only",
    )
    split_auth = {
        "kind": "user",
        "name": "synthetic",
        "evidence": "Synthetic separate split authority",
    }
    children = []
    for issue in (99, 202):
        capsule = copy.deepcopy(workflow.replay(parent, NOW).capsule)
        capsule["id"] = f"synthetic-issue-{issue}"
        capsule["issue"] = issue
        capsule["generation"] = 1
        capsule["owner"]["session"] = f"synthetic-child-owner-{issue}"
        capsule["authorization"] = copy.deepcopy(split_auth)
        children.append(
            {
                "issue": issue,
                "counts": {
                    "implementation": 1,
                    "initial_review": 0,
                    "remediation": 0,
                    "final_review": 0,
                    "design_reset": 0,
                },
                "capsule": capsule,
            }
        )
    append(
        parent,
        "split",
        19,
        authority=split_auth,
        capsule=workflow.capsule_ref(workflow.replay(parent, NOW).capsule),
        children=children,
        reason="Synthetic conserved child allocation",
    )
    successors = {}
    for child in children:
        issue = child["issue"]
        initial = copy.deepcopy(source()["events"][0])
        initial["at"] = (AT + timedelta(seconds=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = initial["data"]
        data["issue"] = issue
        data["classification"] = "consequential"
        data["authority"] = {
            "kind": "coordinator",
            "name": "synthetic",
            "evidence": "Synthetic child init",
        }
        data["capsule"] = copy.deepcopy(child["capsule"])
        data["predecessor"] = {"issue": 123, "digest": workflow.digest(parent)}
        successors[issue] = {"schema": 1, "events": [initial]}
    assert workflow.validate_map({123: parent, **successors}, NOW)[99].predecessor
    return parent, successors


def child_phase(parent, child, name, offset, session, role):
    cap = workflow.capsule_ref(workflow.replay(child, NOW, predecessors={123: parent}).capsule)
    append(child, "phase_start", offset, phase=name, session=session, role=role, capsule=cap)
    append(
        child,
        "phase_end",
        offset + 1,
        session=session,
        outcome="pass",
        evidence="Synthetic child phase outcome",
    )


def ready_child(parent, child):
    child_phase(parent, child, "design", 21, "synthetic-child-architect", "design_architect")
    child_phase(parent, child, "challenge", 23, "synthetic-child-challenge", "code_reviewer")
    append(
        child,
        "design_ready",
        25,
        authority={
            "kind": "coordinator",
            "name": "synthetic",
            "evidence": "Synthetic child approval",
        },
        evidence="Synthetic child approval only",
        capsule=workflow.capsule_ref(
            workflow.replay(child, NOW, predecessors={123: parent}).capsule
        ),
    )
    assert workflow.replay(child, NOW, predecessors={123: parent}).ready


@pytest.mark.parametrize("event_kind", ["extension", "split"])
@pytest.mark.parametrize("reuse_issue", [99, 202])
def test_connected_child_cannot_reuse_local_authority(event_kind, reuse_issue):
    parent, children = synthetic_connected_children()
    child = children[reuse_issue]
    reused = {
        "kind": "user",
        "name": "renamed",
        "evidence": "  " + AUTH["evidence"].upper().replace(" ", "  ") + "  ",
    }
    if event_kind == "extension":
        append(
            child,
            "extension",
            21,
            authority=reused,
            seconds=0,
            counts={
                "implementation": 1,
                "initial_review": 0,
                "remediation": 0,
                "final_review": 0,
                "design_reset": 0,
            },
            reason="Synthetic child grant",
        )
    else:
        ready_child(parent, child)
        grandchild_capsule = copy.deepcopy(
            workflow.replay(child, NOW, predecessors={123: parent}).capsule
        )
        grandchild_capsule["id"] = "synthetic-grandchild-303"
        grandchild_capsule["issue"] = 303
        grandchild_capsule["generation"] = 1
        grandchild_capsule["owner"]["session"] = "synthetic-grandchild-owner"
        grandchild_capsule["authorization"] = copy.deepcopy(reused)
        append(
            child,
            "split",
            26,
            authority=reused,
            capsule=workflow.capsule_ref(
                workflow.replay(child, NOW, predecessors={123: parent}).capsule
            ),
            children=[
                {
                    "issue": 303,
                    "counts": {
                        "implementation": 1,
                        "initial_review": 0,
                        "remediation": 0,
                        "final_review": 0,
                        "design_reset": 0,
                    },
                    "capsule": grandchild_capsule,
                }
            ],
            reason="Synthetic descendant split",
        )
    candidate = {123: parent, **children}
    if reuse_issue == 99:
        candidate = dict(reversed(list(candidate.items())))
    assert workflow.replay(child, NOW, predecessors={123: parent}).limits["implementation"] > 0
    record = workflow.authority_records(child)[-1]
    assert record["class"] == event_kind
    assert record["evidence"] == workflow.normalized_evidence(AUTH["evidence"])
    distinct = copy.deepcopy(candidate)
    distinct_event = distinct[reuse_issue]["events"][-1]
    distinct_event["data"]["authority"]["evidence"] = "Synthetic independent descendant authority"
    if event_kind == "split":
        distinct_event["data"]["children"][0]["capsule"]["authorization"]["evidence"] = (
            "Synthetic independent descendant authority"
        )
    assert workflow.validate_map(distinct, NOW)[reuse_issue].issue == reuse_issue
    with pytest.raises(workflow.Invalid, match="authority reused within connected lineage"):
        workflow.validate_map(candidate, NOW)


def test_same_ticket_continuation_cannot_reuse_local_authority():
    value = synthetic_generation_six_route()
    append(
        value,
        "continuation",
        18,
        authority={
            "kind": "user",
            "name": "renamed",
            "evidence": " " + AUTH["evidence"].upper() + " ",
        },
        capsule=workflow.capsule_ref(workflow.replay(value, NOW).capsule),
        counts={
            "implementation": 0,
            "initial_review": 0,
            "remediation": 1,
            "final_review": 1,
            "design_reset": 0,
        },
        reason="Synthetic later continuation",
    )
    distinct = copy.deepcopy(value)
    distinct["events"][-1]["data"]["authority"]["evidence"] = (
        "Synthetic distinct later continuation authority"
    )
    assert workflow.replay(distinct, NOW).pending_repair
    with pytest.raises(workflow.Invalid, match="authorization already consumed"):
        workflow.replay(value, NOW)


def test_atomic_append_invalid_event_preserves_historical_bytes(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    target = tmp_path / workflow.DIRECTORY / "issue-123.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(FIXTURE.read_bytes())
    before = target.read_bytes()
    value = source()
    bad = transition(value)
    bad["data"]["target"]["digest"] = "0" * 64
    with pytest.raises(workflow.Invalid):
        workflow.append(tmp_path, 123, bad, NOW)
    assert target.read_bytes() == before
    assert not (target.parent / "repository.lock").exists()
    accepted = workflow.append(tmp_path, 123, transition(value), NOW)
    assert accepted.local_registry_authority is not None
    after = target.read_bytes()
    with pytest.raises(workflow.Invalid):
        workflow.append(tmp_path, 123, transition(value), NOW)
    assert target.read_bytes() == after
