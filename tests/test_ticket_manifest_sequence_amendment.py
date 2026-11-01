"""Exact historical prefix; all later events and authorities in this file are synthetic."""

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

FIXTURE = ROOT / "tests/fixtures/issue123-original49.json"
NOW = datetime(2026, 11, 2, tzinfo=UTC)
AT = datetime(2026, 11, 1, 7, 5, tzinfo=UTC)
AUTH = {
    "kind": "user",
    "name": "synthetic-sequencing-user",
    "evidence": "Unique synthetic sequencing transition authority",
}


def source():
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(value["events"]) == 49
    assert (
        workflow.digest({"schema": 1, "events": value["events"][:47]})
        == "dc69597ff2b6ddd9cd9c0b41dbc5111ea956291f557221b460fd3a7b4f902471"
    )
    assert workflow.digest(value) == workflow.MANIFEST_SEQUENCE_PREFIX_DIGEST
    assert (
        workflow.capsule_ref(workflow.replay(value, NOW).capsule)
        == workflow.MANIFEST_SEQUENCE_SOURCE
    )
    return value


def event(value, auth=None, seconds=0):
    auth = copy.deepcopy(AUTH if auth is None else auth)
    old = workflow.replay(value, NOW).capsule
    replacement, changes = workflow.manifest_sequence_target(old, auth)
    return {
        "type": "manifest_sequence_amendment",
        "at": (AT + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": {
            "transition": workflow.MANIFEST_SEQUENCE_VERSION,
            "authority": auth,
            "capsule": workflow.capsule_ref(old),
            "source_history": {
                "event_count": len(value["events"]),
                "digest": workflow.digest(value),
            },
            "replacement": replacement,
            "target": workflow.capsule_ref(replacement),
            "changes": changes,
            "reason": "Synthetic exact sequencing transition test",
        },
    }


def changed():
    value = source()
    value["events"].append(event(value))
    return value


def append(value, kind, offset, **data):
    value["events"].append(
        {
            "type": kind,
            "at": (AT + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": data,
        }
    )


def phase(value, name, offset, session, role, **extra):
    cap = workflow.capsule_ref(workflow.replay(value, NOW).capsule)
    append(
        value, "phase_start", offset, phase=name, session=session, role=role, capsule=cap, **extra
    )
    append(
        value,
        "phase_end",
        offset + 1,
        session=session,
        outcome="pass",
        evidence="Synthetic bounded outcome",
    )


def first_ascii_fullwidth(value):
    for index, char in enumerate(value):
        if "A" <= char <= "Z" or "a" <= char <= "z":
            return value[:index] + chr(ord(char) + 0xFEE0) + value[index + 1 :]
    raise AssertionError("authority evidence has no ASCII letter")


def test_exact_one_path_target_state_and_consuming_record():
    value = source()
    prior = workflow.replay(value, NOW)
    proposed = event(value)
    target = proposed["data"]["replacement"]
    assert len(target["scope"]["S123-1"]) == 3998
    assert workflow.digest(target["scope"]["S123-1"]) == workflow.MANIFEST_SEQUENCE_SCOPE_DIGEST
    assert list(proposed["data"]["changes"]["definitions"]) == ["scope.S123-1"]
    old = prior.capsule
    unchanged = copy.deepcopy(target)
    unchanged["scope"]["S123-1"] = old["scope"]["S123-1"]
    unchanged["generation"] = old["generation"]
    unchanged["authorization"] = old["authorization"]
    assert unchanged == old
    value["events"].append(proposed)
    state = workflow.replay(value, NOW)
    assert state.capsule == target
    assert state.manifest_sequence_amendment == {
        "contract": workflow.MANIFEST_SEQUENCE_VERSION,
        "source": workflow.MANIFEST_SEQUENCE_SOURCE,
        "target": workflow.capsule_ref(target),
        "source_history": proposed["data"]["source_history"],
        "event": 49,
    }
    assert workflow.authority_records(value)[-1]["class"] == "manifest_sequence_amendment"
    assert workflow.validate_map({123: value}, NOW)[123].capsule == target
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
        "capsule_amendment",
        "local_registry_authority",
        "budget_seconds",
        "policy",
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
    with pytest.raises(workflow.Invalid):
        state.gate("design_reset", NOW)
    with pytest.raises(workflow.Invalid):
        state.gate("design", NOW)
    with pytest.raises(workflow.Invalid):
        state.gate("initial_review", NOW)


@pytest.mark.parametrize(
    "damage",
    [
        lambda e: e["data"].update(transition="wrong"),
        lambda e: e["data"].update(extra=True),
        lambda e: e["data"].pop("changes"),
        lambda e: e["data"].update(reason=""),
        lambda e: e["data"].update(capsule={}),
        lambda e: e["data"]["source_history"].update(event_count=True),
        lambda e: e["data"]["source_history"].update(event_count=50),
        lambda e: e["data"]["source_history"].update(digest="0" * 64),
        lambda e: e["data"].update(target={}),
        lambda e: e["data"].update(changes={}),
        lambda e: e["data"]["changes"]["definitions"].update({"interfaces": {}}),
        lambda e: e["data"]["replacement"].update(json_state_impact="wrong"),
        lambda e: e["data"]["replacement"].update(generation=7.0),
        lambda e: e["data"]["replacement"]["scope"].update({"S123-1": "wrong"}),
        lambda e: e["data"].update(authority=None),
    ],
)
def test_invalid_event_specific_target_or_shape_fails(damage):
    value = source()
    proposed = event(value)
    damage(proposed)
    value["events"].append(proposed)
    with pytest.raises(workflow.Invalid):
        workflow.replay(value, NOW)


def test_consumed_authority_and_prefix_mutation_rejected():
    value = source()
    for consumed in list(workflow.replay(value, NOW).authorization_history):
        auth = {**AUTH, "name": "changed name", "evidence": "  " + consumed.upper() + "  "}
        invalid = copy.deepcopy(value)
        invalid["events"].append(event(invalid, auth))
        with pytest.raises(workflow.Invalid):
            workflow.replay(invalid, NOW)
    invalid = copy.deepcopy(value)
    invalid["events"][48]["data"]["evidence"] += " altered"
    invalid["events"].append(event(value))
    with pytest.raises(workflow.Invalid):
        workflow.replay(invalid, NOW)


@pytest.mark.parametrize(
    "variation",
    [
        lambda text: text,
        lambda text: "  " + text.upper() + "  ",
        lambda text: "\n" + text.replace(" ", "  ") + "\n",
        first_ascii_fullwidth,
    ],
)
def test_all_nine_denied_authorities_with_valid_targets(variation):
    records = json.loads(
        (ROOT / "tests/fixtures/issue134-authority-evidence.json").read_text(encoding="utf-8")
    )
    assert set(records) == {
        "Issue128 governance",
        "Issue132 governance",
        "Issue134 G",
        "Held R",
        "C recorded bullet",
        "D-curator recorded bullet",
        "D-proof-review recorded bullet",
        "D-key recorded bullet",
        "D-publication recorded bullet",
    }
    for label, evidence in records.items():
        assert (
            workflow.digest(workflow.normalized_evidence(evidence))
            in workflow.MANIFEST_SEQUENCE_DENIED_AUTHORITY_DIGESTS
        ), label
        value = source()
        proposed = event(
            value, {**AUTH, "name": "changed synthetic name", "evidence": variation(evidence)}
        )
        value["events"].append(proposed)
        with pytest.raises(workflow.Invalid, match="authority"):
            workflow.replay(value, NOW)


def test_native_duplicate_key_and_nonfinite_rejected():
    raw = FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(workflow.Invalid):
        workflow.load('{"schema":1,"schema":1,"events":[]}')
    with pytest.raises(workflow.Invalid):
        workflow.load(raw.replace('"schema": 1', '"schema": NaN', 1))


@pytest.mark.parametrize(
    "field,bad",
    [
        ("active", {"phase": "design"}),
        ("suspended", {"phase": "design"}),
        ("clock_running", False),
        ("delivered", True),
        ("delivery_history", [{}]),
        ("delivery_binding", {}),
        ("retired", True),
        ("split_remaining", 0),
        ("split_pool", {}),
        ("splits", {99: {}}),
        ("predecessor", True),
        ("ancestry", [99]),
        ("retained_reservation_open", True),
        ("historical_transition", {}),
        ("final_failed", True),
        ("capsule_amendment", None),
        ("local_registry_authority", None),
        ("manifest_sequence_amendment", {}),
    ],
)
def test_pure_admission_lifecycle_guards(field, bad):
    value = source()
    proposed = event(value)
    state = workflow.replay(value, NOW)
    setattr(state, field, bad)
    with pytest.raises(workflow.Invalid):
        workflow.admit_manifest_sequence_amendment(
            state, value, len(value["events"]), proposed["data"]
        )


@pytest.mark.parametrize(
    "field,bad",
    [
        ("repo", "elsewhere/repo"),
        ("issue", 999),
        ("policy", "timed-v1"),
        ("classification", "ordinary"),
        ("review_required", False),
    ],
)
def test_pure_admission_source_identity_guards(field, bad):
    value = source()
    proposed = event(value)
    state = workflow.replay(value, NOW)
    setattr(state, field, bad)
    with pytest.raises(workflow.Invalid):
        workflow.admit_manifest_sequence_amendment(
            state, value, len(value["events"]), proposed["data"]
        )


def test_full_owner_and_session_must_be_exact():
    value = source()
    proposed = event(value)
    for change in (
        {"session": "/root/other"},
        {"role": "implementation_specialist"},
        {"model": "gpt-6-astra"},
        {"effort": "high"},
    ):
        state = workflow.replay(value, NOW)
        state.approved_owner.update(change)
        with pytest.raises(workflow.Invalid, match="owner"):
            workflow.admit_manifest_sequence_amendment(
                state, value, len(value["events"]), proposed["data"]
            )


def test_valid_distinct_grant_suffix_and_repeated_event_denied():
    value = source()
    append(
        value,
        "extension",
        0,
        authority={**AUTH, "evidence": "Distinct synthetic prospective grant"},
        seconds=0,
        counts={k: (1 if k == "implementation" else 0) for k in workflow.COUNTS},
        reason="Distinct finite synthetic grant",
    )
    proposed = event(value, seconds=1)
    value["events"].append(proposed)
    assert workflow.replay(value, NOW).manifest_sequence_amendment["event"] == 50
    with pytest.raises(workflow.Invalid):
        workflow.replay({"schema": 1, "events": value["events"] + [proposed]}, NOW)


def test_valid_completed_planning_suffix_binds_full_preceding_history():
    value = source()
    phase(value, "planning", 0, "synthetic-new-planner", "planning_analyst")
    proposed = event(value, seconds=2)
    assert proposed["data"]["source_history"]["event_count"] == 51
    value["events"].append(proposed)
    assert workflow.replay(value, NOW).manifest_sequence_amendment["event"] == 51


def test_later_capsule_update_references_authority_without_second_grant():
    value = changed()
    append(
        value,
        "extension",
        1,
        authority={**AUTH, "evidence": "Separate synthetic reset grant"},
        seconds=0,
        counts={k: (1 if k == "design_reset" else 0) for k in workflow.COUNTS},
        reason="Synthetic reset grant",
    )
    append(
        value,
        "phase_start",
        2,
        phase="design_reset",
        role="design_architect",
        session="synthetic-reference-architect",
        criterion="INV123-4",
        reason="Synthetic bounded reset",
        capsule=workflow.capsule_ref(workflow.replay(value, NOW).capsule),
    )
    revised = copy.deepcopy(workflow.replay(value, NOW).capsule)
    assert revised["generation"] == 8
    assert revised["authorization"] == AUTH
    append(
        value,
        "capsule_update",
        3,
        authority={
            "kind": "coordinator",
            "name": "synthetic",
            "evidence": "Synthetic capsule update",
        },
        capsule=revised,
    )
    records = workflow.authority_records(value)
    assert len([r for r in records if r["class"] == "manifest_sequence_amendment"]) == 1
    assert records[-1]["class"] == "capsule_update" and records[-1]["reference"] is True
    assert workflow.validate_map({123: value}, NOW)[123].capsule == revised


def test_same_ticket_later_grant_cannot_reuse_manifest_authority():
    value = changed()
    append(
        value,
        "extension",
        1,
        authority={**AUTH, "name": "renamed", "evidence": " " + AUTH["evidence"].upper() + " "},
        seconds=0,
        counts={k: (1 if k == "design_reset" else 0) for k in workflow.COUNTS},
        reason="Synthetic attempted reuse",
    )
    with pytest.raises(workflow.Invalid, match="already consumed"):
        workflow.replay(value, NOW)


def synthetic_complete_value(*, deliver=True):
    value = changed()
    original = workflow.replay(value, NOW)
    held = json.loads(
        (ROOT / "tests/fixtures/issue134-authority-evidence.json").read_text(encoding="utf-8")
    )["Held R"]
    append(
        value,
        "extension",
        1,
        authority={"kind": "user", "name": "synthetic", "evidence": held},
        seconds=0,
        counts={k: (1 if k == "design_reset" else 0) for k in workflow.COUNTS},
        reason="Synthetic shape of separately approved held reset",
    )
    assert workflow.replay(value, NOW).counts == original.counts
    phase(
        value,
        "design_reset",
        2,
        "synthetic-architect",
        "design_architect",
        criterion="INV123-4",
        reason="Synthetic gen8 design",
    )
    state = workflow.replay(value, NOW)
    assert state.capsule["generation"] == 8 and state.counts["design_reset"] == 4
    phase(value, "challenge", 4, "synthetic-independent-challenge", "code_reviewer")
    append(
        value,
        "design_ready",
        6,
        authority={
            "kind": "coordinator",
            "name": "synthetic",
            "evidence": "Synthetic gen8 approval",
        },
        evidence="Synthetic approval",
        capsule=workflow.capsule_ref(workflow.replay(value, NOW).capsule),
    )
    owner = original.approved_owner["session"]
    phase(value, "implementation", 7, owner, "implementation_worker")
    assert workflow.replay(value, NOW).counts["implementation"] == 6
    phase(value, "remediation", 9, owner, "implementation_worker")
    for offset, blocker in enumerate(original.blockers, 11):
        append(value, "resolve", offset, id=blocker, evidence="Synthetic remediation evidence")
    content = "a" * 64
    phase(value, "verification", 13, owner, "implementation_worker", content=content)
    append(
        value,
        "acceptance",
        15,
        ids=original.acceptance,
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
    assert final.counts["remediation"] == 2 and final.counts["final_review"] == 1
    assert final.ready and final.verified and final.accepted and final.reviewed
    final.gate("delivery", NOW)
    if deliver:
        append(
            value,
            "delivery",
            18,
            evidence="Synthetic original-PR delivery",
            pr=124,
            repo=original.repo,
            content=content,
            capsule=workflow.capsule_ref(final.capsule),
        )
        delivered = workflow.replay(value, NOW)
        assert delivered.delivered and delivered.delivery_binding["pr"] == 124
        assert delivered.delivery_binding["content"] == content
    return value


def test_synthetic_reset_through_independent_final_review_and_delivery_gate():
    synthetic_complete_value()


@pytest.mark.parametrize("reverse", [False, True])
def test_connected_child_rejects_reused_manifest_authority_in_both_orders(reverse):
    parent = synthetic_complete_value(deliver=False)
    append(
        parent,
        "extension",
        18,
        authority={**AUTH, "evidence": "Synthetic separate split allocation"},
        seconds=0,
        counts={k: (1 if k == "implementation" else 0) for k in workflow.COUNTS},
        reason="Synthetic conserved child allocation",
    )
    split_authority = {**AUTH, "evidence": "Synthetic distinct child split authority"}
    child_capsule = copy.deepcopy(workflow.replay(parent, NOW).capsule)
    child_capsule["id"] = "synthetic-child-202"
    child_capsule["issue"] = 202
    child_capsule["generation"] = 1
    child_capsule["owner"]["session"] = "synthetic-child-owner-202"
    child_capsule["authorization"] = copy.deepcopy(split_authority)
    append(
        parent,
        "split",
        19,
        authority=split_authority,
        capsule=workflow.capsule_ref(workflow.replay(parent, NOW).capsule),
        children=[
            {
                "issue": 202,
                "counts": {k: (1 if k == "implementation" else 0) for k in workflow.COUNTS},
                "capsule": child_capsule,
            }
        ],
        reason="Synthetic single-child split",
    )
    first = copy.deepcopy(source()["events"][0])
    first["at"] = (AT + timedelta(seconds=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    first["data"]["issue"] = 202
    first["data"]["classification"] = "consequential"
    first["data"]["authority"] = {
        "kind": "coordinator",
        "name": "synthetic",
        "evidence": "Synthetic child init",
    }
    first["data"]["capsule"] = copy.deepcopy(child_capsule)
    first["data"]["predecessor"] = {"issue": 123, "digest": workflow.digest(parent)}
    child = {"schema": 1, "events": [first]}
    reused = {**AUTH, "name": "different name", "evidence": "  " + AUTH["evidence"].upper() + "  "}
    append(
        child,
        "extension",
        21,
        authority=reused,
        seconds=0,
        counts={k: (1 if k == "implementation" else 0) for k in workflow.COUNTS},
        reason="Synthetic child grant",
    )
    distinct = copy.deepcopy(child)
    distinct["events"][-1]["data"]["authority"]["evidence"] = "Synthetic distinct child grant"
    assert workflow.validate_map({123: parent, 202: distinct}, NOW)[202].predecessor
    pair = {123: parent, 202: child}
    if reverse:
        pair = dict(reversed(list(pair.items())))
    with pytest.raises(workflow.Invalid, match="authority reused within connected lineage"):
        workflow.validate_map(pair, NOW)


def test_atomic_append_invalid_candidate_preserves_original_bytes(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    path = tmp_path / workflow.DIRECTORY / "issue-123.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(FIXTURE.read_bytes())
    original = path.read_bytes()
    bad = event(source())
    bad["data"]["target"]["digest"] = "0" * 64
    with pytest.raises(workflow.Invalid):
        workflow.append(tmp_path, 123, bad, NOW)
    assert path.read_bytes() == original
    assert not (path.parent / "repository.lock").exists()
    assert workflow.append(tmp_path, 123, event(source()), NOW).manifest_sequence_amendment
