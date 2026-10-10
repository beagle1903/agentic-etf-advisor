"""Finite ticket transitions, adversarial history and CI binding."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ticket_workflow as workflow

START = datetime(2026, 9, 26, 4, 23, 34, tzinfo=UTC)
AUTH = {"kind": "coordinator", "name": "coordinator", "evidence": "approved issue comment"}
CONTENT = workflow.digest([])
USER = {"kind": "user", "name": "beagle1903", "evidence": "explicit finite approval"}


def issue92_fixture(name: str = "bootstrap_ledger") -> dict:
    """Return a fresh immutable archived baseline, never the current ledger tail."""
    filename = workflow.RECOVERY_SOURCE_FILES[name]
    path = Path(__file__).resolve().parents[1] / workflow.RECOVERY_ARCHIVE / filename
    value = workflow.strict_json(path.read_bytes())
    expected = {
        "bootstrap_ledger": workflow.RECOVERY_BOOTSTRAP,
        "stop_ledger": workflow.RECOVERY_STOP,
    }[name]
    assert workflow.digest(value) == expected
    return copy.deepcopy(value)


def issue92_recovery_event() -> dict:
    root = Path(__file__).resolve().parents[1]
    grant = workflow.strict_json(
        (root / workflow.RECOVERY_ARCHIVE / "finite-grant.json").read_bytes()
    )
    assert workflow.digest(grant) == workflow.RECOVERY_GRANT
    return {
        "type": "issue92_recovery",
        "at": grant["at"],
        "data": {
            "version": "issue92-single-recovery-v1",
            "authority": grant["authority"],
            "authority_anchor": grant["authority_anchor"],
            "capsule": grant["capsule"],
            "prefix_digest": workflow.RECOVERY_STOP,
            "grant_digest": workflow.RECOVERY_GRANT,
            "closeout_digest": workflow.RECOVERY_CLOSEOUT,
            "proposal_digest": workflow.RECOVERY_PROPOSAL,
            "reason": grant["reason"],
        },
    }


def issue92_recovery_fixture() -> dict:
    value = issue92_fixture("stop_ledger")
    value["events"].append(issue92_recovery_event())
    value["events"].append(
        {
            "type": "phase_start",
            "at": "2026-10-09T10:12:25Z",
            "data": {
                "phase": "remediation",
                "session": workflow.RECOVERY_OWNER,
                "role": "implementation_worker",
                "capsule": workflow.RECOVERY_CAPSULE_REF,
            },
        }
    )
    return value


def issue92_repaired_fixture(*, review: bool = False) -> dict:
    value = issue92_recovery_fixture()
    value["events"].extend(
        [
            {
                "type": "phase_end",
                "at": "2026-10-09T10:12:26Z",
                "data": {
                    "session": workflow.RECOVERY_OWNER,
                    "outcome": "pass",
                    "evidence": "fixture repair",
                },
            },
            {
                "type": "resolve",
                "at": "2026-10-09T10:12:27Z",
                "data": {"id": workflow.RECOVERY_BLOCKER, "evidence": "fixture repaired"},
            },
            {
                "type": "phase_start",
                "at": "2026-10-09T10:12:28Z",
                "data": {
                    "phase": "verification",
                    "session": workflow.RECOVERY_OWNER,
                    "role": "implementation_worker",
                    "capsule": workflow.RECOVERY_CAPSULE_REF,
                    "content": CONTENT,
                },
            },
            {
                "type": "phase_end",
                "at": "2026-10-09T10:12:29Z",
                "data": {
                    "session": workflow.RECOVERY_OWNER,
                    "outcome": "pass",
                    "evidence": "fresh verification",
                },
            },
            {
                "type": "acceptance",
                "at": "2026-10-09T10:12:30Z",
                "data": {
                    "ids": value["events"][0]["data"]["acceptance"],
                    "capsule": workflow.RECOVERY_CAPSULE_REF,
                    "content": CONTENT,
                    "evidence": "complete repaired acceptance",
                },
            },
        ]
    )
    if review:
        value["events"].extend(
            [
                {
                    "type": "phase_start",
                    "at": "2026-10-09T10:12:31Z",
                    "data": {
                        "phase": "initial_review",
                        "session": "new-independent-reviewer",
                        "role": "code_reviewer",
                        "capsule": workflow.RECOVERY_CAPSULE_REF,
                        "content": CONTENT,
                    },
                },
                {
                    "type": "phase_end",
                    "at": "2026-10-09T10:12:32Z",
                    "data": {
                        "session": "new-independent-reviewer",
                        "outcome": "pass",
                        "evidence": "clean repaired review",
                    },
                },
            ]
        )
    return value


def at(seconds: int) -> str:
    return (START + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def event(kind: str, offset: int, **data) -> dict:
    return {"type": kind, "at": at(offset), "data": data}


def make_capsule(consequential=False, issue=73):
    return {
        "id": f"issue-{issue}-capsule",
        "generation": 1,
        "repo": "beagle1903/agentic-etf-advisor",
        "issue": issue,
        "classification": "consequential" if consequential else "ordinary",
        "owner": {
            "role": "implementation_worker",
            "model": "gpt-6-sol",
            "effort": "medium",
            "session": "worker",
        },
        "rationale": "Approved established-contract implementation",
        "authorization": USER,
        "scope": {"workflow": "Workflow controls only"},
        "non_goals": ["Product changes"],
        "invariants": {"INV1": "Finite attempts fail closed"},
        "interfaces": ["Workflow CLI"],
        "json_state_impact": "none",
        "acceptance": {"AC1": "All finite replay controls pass"},
        "verification": ["Focused tests"],
        "documentation": ["Workflow guide"],
        "risks": ["Recorded evidence is not authenticated"],
        "escalation_triggers": ["Concrete complexity"],
        "escalation": None,
    }


def ledger(consequential: bool = False, issue: int = 73) -> dict:
    cap = make_capsule(consequential, issue)
    return {
        "schema": 1,
        "events": [
            event(
                "initialize",
                0,
                repo=cap["repo"],
                issue=issue,
                classification=cap["classification"],
                scope=["workflow"],
                invariants=["INV1"],
                acceptance=["AC1"],
                review_required=consequential,
                authority=AUTH,
                adoption=None,
                predecessor=None,
                capsule=cap,
            )
        ],
    }


def current_capsule(value):
    cap = copy.deepcopy(value["events"][0]["data"]["capsule"])
    for item in value["events"][1:]:
        if item["type"] == "phase_start" and item["data"]["phase"] == "design_reset":
            cap["generation"] += 1
        elif item["type"] == "capsule_update":
            cap = copy.deepcopy(item["data"]["capsule"])
    return cap


def add(value: dict, kind: str, offset: int, **data) -> None:
    if kind in {"phase_start", "design_ready", "acceptance", "delivery", "owner_handoff"}:
        data.setdefault("capsule", workflow.capsule_ref(current_capsule(value)))
    if kind == "phase_start" and data["phase"] in {
        "initial_review",
        "final_review",
        "verification",
    }:
        data.setdefault("content", CONTENT)
    if kind in {"acceptance", "delivery"}:
        data.setdefault("content", CONTENT)
    if kind == "delivery":
        data.setdefault("repo", value["events"][0]["data"]["repo"])
        data.setdefault("pr", 80)
    value["events"].append(event(kind, offset, **data))


def phase(
    value: dict, name: str, start: int, outcome: str = "pass", session: str | None = None
) -> None:
    writing = name in {"implementation", "remediation", "verification"}
    session = session or ("worker" if writing else name)
    role = "implementation_worker" if writing else next(iter(workflow.ROLES[name]))
    add(value, "phase_start", start, phase=name, role=role, session=session)
    add(
        value, "phase_end", start + 1, session=session, outcome=outcome, evidence="focused evidence"
    )


def ready(value: dict, seconds: int = 0) -> None:
    add(value, "design_ready", seconds, authority=AUTH, evidence="DESIGN_READY capsule")


def state(value: dict, seconds: int = 100, predecessors: dict | None = None) -> workflow.State:
    return workflow.replay(value, START + timedelta(seconds=seconds), predecessors=predecessors)


def owner_ledger(consequential: bool = False) -> dict:
    value = ledger(consequential, issue=86)
    value["events"][0]["data"]["policy"] = "owner-led-v1"
    return value


def split_child(parent: dict, issue: int, allocation: dict, evidence: str, offset: int) -> dict:
    child = owner_ledger()
    child["events"][0]["data"]["issue"] = issue
    child["events"][0]["data"]["capsule"] = make_capsule(issue=issue)
    child["events"][0]["data"]["capsule"]["authorization"] = {
        "kind": "user",
        "name": "user",
        "evidence": evidence,
    }
    child["events"][0]["at"] = at(offset)
    ref = workflow.capsule_ref(child["events"][0]["data"]["capsule"])
    add(
        parent,
        "split",
        offset,
        authority={"kind": "user", "name": "user", "evidence": evidence},
        capsule=workflow.capsule_ref(current_capsule(parent)),
        successor=issue,
        successor_capsule=ref,
        counts=allocation,
        reason="conserved owner-led allowance",
    )
    child["events"][0]["data"]["predecessor"] = {
        "issue": parent["events"][0]["data"]["issue"],
        "digest": workflow.digest(parent),
    }
    return child


def owner_ready(value: dict, offset: int = 5) -> None:
    if value["events"][0]["data"]["classification"] == "consequential":
        phase(value, "design", 1)
        phase(value, "challenge", 3)
    ready(value, offset)


def owner_certify(value: dict, offset: int, review: str | None = None) -> None:
    phase(value, "verification", offset)
    add(value, "acceptance", offset + 2, ids=["AC1"], evidence="current acceptance")
    if review:
        phase(value, review, offset + 3, session=f"review-{offset}")


def owner_continue(value: dict, offset: int, evidence: str) -> None:
    add(
        value,
        "continuation",
        offset,
        authority={"kind": "user", "name": "user", "evidence": evidence},
        counts={
            "implementation": 0,
            "initial_review": 0,
            "remediation": 1,
            "final_review": 1,
            "design_reset": 0,
        },
        capsule=workflow.capsule_ref(current_capsule(value)),
        reason="same-scope correction to verified implementation",
    )
    if state(value, offset).delivery_history and not state(value, offset).clock_running:
        add(
            value,
            "coordination_resume",
            offset + 1,
            authority=AUTH,
            evidence="continue after delivered coordination stop",
        )


def clean(consequential: bool = False, remediation: bool = False) -> dict:
    value = ledger(consequential)
    if consequential:
        phase(value, "design", 1)
        phase(value, "challenge", 3)
    ready(value, 5)
    phase(value, "implementation", 6)
    if consequential or remediation:
        phase(value, "initial_review", 8, "fail" if remediation else "pass")
    if remediation:
        add(
            value,
            "blocker",
            10,
            id="F1",
            criterion="AC1",
            scenario="extra phase bypass",
            evidence="repro",
        )
        phase(value, "remediation", 11)
        add(value, "resolve", 13, id="F1", evidence="regression passes")
        phase(value, "final_review", 14)
    phase(value, "verification", 16)
    add(value, "acceptance", 18, ids=["AC1"], evidence="complete AC matrix")
    return value


def test_owner_policy_elapsed_is_audit_and_legacy_still_exhausts():
    value = owner_ledger()
    owner_ready(value)
    add(
        value,
        "phase_start",
        6,
        phase="implementation",
        session="worker",
        role="implementation_worker",
    )
    add(value, "pause", 7300, session="worker", outcome="interrupted", evidence="quota pause")
    add(value, "phase_resume", 8000, session="worker")
    add(value, "phase_end", 8010, session="worker", outcome="pass", evidence="complete")
    result = state(value, 8010)
    assert result.elapsed_seconds == 7310
    assert result.counts["implementation"] == 1
    assert result.policy == "owner-led-v1"
    legacy = ledger()
    ready(legacy)
    with pytest.raises(workflow.Invalid, match="budget exhausted"):
        state(legacy, 7200).gate("implementation", START + timedelta(seconds=7200))


def test_owner_consequential_review_after_current_verification_and_same_owner_repair():
    value = owner_ledger(True)
    with pytest.raises(workflow.Invalid, match="DESIGN_READY"):
        state(value).gate("implementation", START + timedelta(seconds=100))
    phase(value, "design", 1)
    with pytest.raises(workflow.Invalid, match="challenge"):
        ready(value, 3)
        state(value)
    value["events"].pop()
    phase(value, "challenge", 3)
    ready(value, 5)
    phase(value, "implementation", 6)
    with pytest.raises(workflow.Invalid, match="verification and acceptance"):
        phase(value, "initial_review", 8)
        state(value)
    value["events"] = value["events"][:-2]
    owner_certify(value, 8, "initial_review")
    add(
        value,
        "blocker",
        14,
        id="F1",
        criterion="AC1",
        scenario="same-scope defect",
        evidence="review finding",
    )
    # The failed first review consumes its own slot and a finding author is excluded.
    value["events"][-2]["data"]["outcome"] = "fail"
    phase(value, "remediation", 15)
    add(value, "resolve", 17, id="F1", evidence="owner repair verified")
    owner_certify(value, 18, "final_review")
    add(value, "delivery", 24, evidence="same owner corrected")
    result = state(value, 24)
    assert result.delivered and result.write_authors == {"worker"}
    assert result.counts["remediation"] == result.counts["final_review"] == 1


def test_owner_blocker_cannot_start_remediation_before_implementation():
    value = owner_ledger()
    owner_ready(value)
    add(
        value,
        "blocker",
        6,
        id="EARLY",
        criterion="AC1",
        scenario="premature repair request",
        evidence="frozen criterion",
    )
    before = state(value, 6)
    assert before.counts["remediation"] == 0
    add(
        value, "phase_start", 7, phase="remediation", role="implementation_worker", session="worker"
    )
    with pytest.raises(workflow.Invalid, match="remediation requires completed implementation"):
        state(value, 7)
    assert before.counts["remediation"] == 0


@pytest.mark.parametrize("review", ["initial_review", "final_review"])
def test_owner_review_reservation_requires_exact_current_certified_content(review, tmp_path):
    value = owner_ledger(True)
    owner_ready(value)
    phase(value, "implementation", 6)
    if review == "initial_review":
        owner_certify(value, 8)
        offset = 11
    else:
        owner_certify(value, 8, "initial_review")
        owner_continue(value, 14, "finite correction for review reservation")
        phase(value, "remediation", 15)
        owner_certify(value, 17)
        offset = 20
    before = state(value, offset)
    assert before.verified_content == before.acceptance_content == CONTENT
    assert before.counts[review] == (1 if review == "initial_review" and offset == 20 else 0)
    base = copy.deepcopy(value)
    add(
        value,
        "phase_start",
        offset,
        phase=review,
        role="code_reviewer",
        session=f"fresh-{review}",
        content=workflow.digest(["changed after acceptance"]),
    )
    with pytest.raises(
        workflow.Invalid, match="review reservation differs from verified accepted content"
    ):
        state(value, offset)
    assert before.counts[review] == (1 if review == "initial_review" and offset == 20 else 0)

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    source = tmp_path / "source.txt"
    source.write_text("reviewed source\n", encoding="utf-8")
    original_content = workflow.content_digest(tmp_path, 86)
    for item in base["events"]:
        current = copy.deepcopy(item)
        if "content" in current["data"]:
            current["data"]["content"] = original_content
        workflow.append(tmp_path, 86, current, workflow.timestamp(current["at"]))
    path = tmp_path / workflow.DIRECTORY / "issue-86.json"
    prior_bytes = path.read_bytes()
    source.write_text("changed after acceptance\n", encoding="utf-8")
    wrong = copy.deepcopy(value["events"][-1])
    wrong["data"]["content"] = workflow.content_digest(tmp_path, 86)
    with pytest.raises(
        workflow.Invalid, match="review reservation differs from verified accepted content"
    ):
        workflow.append(tmp_path, 86, wrong, workflow.timestamp(wrong["at"]))
    assert path.read_bytes() == prior_bytes
    saved = workflow.read_all(tmp_path)[86]
    assert state(saved, offset).counts[review] == before.counts[review]


def test_owner_deliver_continue_twice_retains_exact_history_and_pr():
    value = owner_ledger(True)
    owner_ready(value)
    phase(value, "implementation", 6)
    owner_certify(value, 8, "initial_review")
    add(value, "delivery", 14, evidence="original delivery", pr=87)
    original = copy.deepcopy(value["events"])
    owner_continue(value, 15, "Issue86 explicit first finite repair")
    assert value["events"][: len(original)] == original
    partial = state(value, 16)
    assert not partial.delivered and len(partial.delivery_history) == 1
    with pytest.raises(workflow.Invalid, match="open phase or unresolved blocker"):
        partial.gate("delivery", START + timedelta(seconds=16))
    phase(value, "remediation", 17)
    owner_certify(value, 19, "final_review")
    add(value, "delivery", 25, evidence="first correction", pr=87)
    assert len(state(value, 25).delivery_history) == 2
    owner_continue(value, 26, "Issue86 explicit second finite repair")
    phase(value, "remediation", 28)
    owner_certify(value, 30, "final_review")
    add(value, "delivery", 36, evidence="second correction", pr=87)
    result = state(value, 36)
    assert result.delivery_history[0]["pr"] == result.delivery_history[-1]["pr"] == 87
    assert len(result.delivery_history) == 3
    assert result.counts["remediation"] == result.counts["final_review"] == 2
    assert value["events"][: len(original)] == original


def test_owner_authority_transition_and_split_boundaries():
    value = ledger(issue=86)
    original = copy.deepcopy(value["events"])
    add(
        value,
        "policy_transition",
        1,
        policy="owner-led-v1",
        authority=USER,
        capsule=workflow.capsule_ref(current_capsule(value)),
        reason="approved issue policy",
    )
    result = state(value)
    assert result.policy == "owner-led-v1" and value["events"][:1] == original
    ready(value, 2)
    phase(value, "implementation", 3)
    fullwidth = "".join(
        chr(0x3000) if letter == " " else chr(ord(letter) + 0xFEE0)
        for letter in "EXPLICIT FINITE APPROVAL"
    )
    for evidence in [
        " EXPLICIT   finite approval ",
        fullwidth,
    ]:
        damaged = copy.deepcopy(value)
        add(
            damaged,
            "extension",
            7,
            authority={"kind": "user", "name": "renamed", "evidence": evidence},
            seconds=0,
            counts={k: 1 if k == "remediation" else 0 for k in workflow.COUNTS},
            reason="finite repair",
        )
        with pytest.raises(workflow.Invalid, match="authorization already consumed"):
            state(damaged)
    for changed in [None, True, -1, {"bad": 1}]:
        damaged = copy.deepcopy(value)
        counts = {k: 0 for k in workflow.COUNTS}
        counts["remediation"] = changed
        add(
            damaged,
            "extension",
            7,
            authority={"kind": "user", "name": "user", "evidence": "new grant"},
            seconds=0,
            counts=counts,
            reason="finite repair",
        )
        with pytest.raises(workflow.Invalid):
            state(damaged)
    damaged = copy.deepcopy(value)
    add(
        damaged,
        "split",
        7,
        authority=USER,
        successor=87,
        seconds=1,
        reason="unsupported new policy split",
    )
    with pytest.raises(workflow.Invalid, match="expected fields"):
        state(damaged)


def test_owner_led_split_conserves_sibling_pool_and_inherited_counts():
    parent = owner_ledger()
    allocation = {key: int(key == "implementation") for key in workflow.COUNTS}
    child = split_child(parent, 93, allocation, "first child grant", 1)
    child_state = state(child, predecessors={86: parent})
    assert child_state.inherited_counts == dict.fromkeys(workflow.COUNTS, 0)
    assert child_state.limits == allocation
    assert state(parent).split_pool["implementation"] == 0
    second = copy.deepcopy(parent)
    second_child = split_child(second, 94, allocation, "second child grant", 2)
    with pytest.raises(workflow.Invalid, match="allocations exceed"):
        state(second)
    with pytest.raises(workflow.Invalid, match="allocations exceed"):
        state(second_child, predecessors={86: second})


def test_owner_led_child_inherits_consumption_and_uses_local_prerequisites():
    parent = owner_ledger()
    ready(parent, 1)
    phase(parent, "implementation", 2)
    add(
        parent,
        "extension",
        4,
        authority={"kind": "user", "name": "burha", "evidence": "one more implementation"},
        seconds=0,
        counts={key: int(key == "implementation") for key in workflow.COUNTS},
        reason="finite child allowance",
    )
    allocation = {key: int(key in {"implementation", "initial_review"}) for key in workflow.COUNTS}
    child = split_child(parent, 93, allocation, "child with inherited count", 5)
    inherited = state(child, predecessors={86: parent})
    assert inherited.counts["implementation"] == inherited.inherited_counts["implementation"] == 1
    assert inherited.limits["implementation"] == 2
    assert inherited.author_session is None and not inherited.ready
    ready(child, 6)
    phase(child, "implementation", 7)
    local = state(child, predecessors={86: parent})
    assert local.counts["implementation"] == 2 and local.author_session == "worker"
    assert local.counts["initial_review"] == 0 and local.limits["initial_review"] == 1


def test_owner_led_split_rejects_duplicate_child_missing_parent_cycle_and_capsule_substitution():
    parent = owner_ledger()
    allocation = {key: int(key == "implementation") for key in workflow.COUNTS}
    child = split_child(parent, 93, allocation, "first child grant", 1)
    duplicate = copy.deepcopy(parent)
    add(
        duplicate,
        "split",
        2,
        authority={"kind": "user", "name": "burha", "evidence": "other approval"},
        capsule=workflow.capsule_ref(current_capsule(duplicate)),
        successor=93,
        successor_capsule=workflow.capsule_ref(child["events"][0]["data"]["capsule"]),
        counts={key: 0 for key in workflow.COUNTS} | {"initial_review": 1},
        reason="duplicate child",
    )
    with pytest.raises(workflow.Invalid, match="invalid owner-led split"):
        state(duplicate)
    with pytest.raises(workflow.Invalid, match="explicit predecessor validation"):
        state(child)
    swapped = copy.deepcopy(child)
    swapped["events"][0]["data"]["capsule"]["authorization"]["evidence"] = "substituted grant"
    with pytest.raises(workflow.Invalid, match="successor policy/capsule mismatch"):
        state(swapped, predecessors={86: parent})
    cycle = copy.deepcopy(parent)
    cycle["events"][0]["data"]["predecessor"] = {"issue": 93, "digest": workflow.digest(child)}
    with pytest.raises(workflow.Invalid, match="cyclic ticket lineage"):
        workflow.lineage_audit({86: cycle, 93: child}, Path.cwd(), START + timedelta(seconds=10))
    other = owner_ledger()
    other["events"][0]["data"]["issue"] = 87
    other["events"][0]["data"]["capsule"] = make_capsule(issue=87)
    split_child(other, 93, allocation, "other parent grant", 1)
    with pytest.raises(workflow.Invalid, match="duplicate successor allocation"):
        workflow.lineage_audit(
            {86: parent, 87: other, 93: child}, Path.cwd(), START + timedelta(seconds=10)
        )


def test_owner_led_lineage_rejects_approval_reuse_in_either_sibling_order():
    parent = owner_ledger()
    first_allocation = {key: int(key == "implementation") for key in workflow.COUNTS}
    child_a = split_child(parent, 93, first_allocation, "first child grant", 1)
    second_allocation = {key: int(key == "initial_review") for key in workflow.COUNTS}
    child_b = split_child(parent, 94, second_allocation, "second child grant", 3)
    fullwidth = "".join(
        chr(ord(letter) + 0xFEE0) if letter != " " else chr(0x3000)
        for letter in "second child grant"
    )
    for evidence in ["SECOND  CHILD GRANT", fullwidth]:
        for offset in (2, 4):
            candidate = copy.deepcopy(child_a)
            add(
                candidate,
                "extension",
                offset,
                authority={"kind": "user", "name": "renamed", "evidence": evidence},
                seconds=0,
                counts=second_allocation,
                reason="duplicate approval",
            )
            with pytest.raises(workflow.Invalid, match="reused"):
                workflow.lineage_audit(
                    {86: parent, 93: candidate, 94: child_b},
                    Path.cwd(),
                    START + timedelta(seconds=10),
                )
    assert (
        workflow.lineage_audit(
            {86: parent, 93: child_a, 94: child_b}, Path.cwd(), START + timedelta(seconds=10)
        )
        is None
    )


def test_saved_issue92_bootstrap_is_pinned_and_retains_failed_history(tmp_path):
    root = Path(__file__).resolve().parents[1]
    value = issue92_fixture()
    current = workflow.replay(value, datetime.now(UTC), root=root)
    assert current.counts == {
        "implementation": 5,
        "initial_review": 3,
        "remediation": 4,
        "final_review": 4,
        "design_reset": 4,
    }
    assert current.limits == {
        "implementation": 5,
        "initial_review": 4,
        "remediation": 4,
        "final_review": 4,
        "design_reset": 4,
    }
    assert current.active["phase"] == "implementation" and current.author_session is None
    assert current.historical_delivery_history[0]["pr"] == 85
    assert {item["outcome"] for item in current.historical_outcomes} >= {
        "blocked",
        "fail",
        "DESIGN_READY",
        "CHALLENGE_PASS",
    }
    h = {item["slot"]: item for item in current.historical_outcomes if item["source"] == "H"}
    assert set(h) == {f"H{i}" for i in range(1, 11)}
    assert h["H6"]["imported_outcome"] == "open" and h["H6"]["outcome"] == "pass"
    assert all(h[f"H{i}"]["outcome"] == "pass" for i in range(7, 11))
    assert {item["id"] for item in current.historical_findings} >= {
        "B85-EXTERNAL-JOURNAL-FILE-RACE"
    }
    assert (
        len(
            [
                item
                for item in current.historical_reservations
                if item.get("phase") == "verification"
            ]
        )
        == 7
    )
    with pytest.raises(workflow.Invalid, match="overlapping phases"):
        current.gate("implementation", datetime.now(UTC))
    altered = copy.deepcopy(value)
    altered["events"][0]["data"]["issue84_remainder"]["grant_digest"] = "0" * 64
    with pytest.raises(workflow.Invalid, match="unapproved Issue84 remainder"):
        workflow.replay(altered, datetime.now(UTC), root=root)
    archive = tmp_path / workflow.REMAINDER_ARCHIVE
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, archive)
    (archive / "last-recovery-journal.json").write_bytes(b"{}")
    with pytest.raises(workflow.Invalid, match="archived source R changed"):
        workflow.replay(value, datetime.now(UTC), root=tmp_path)
    bad_initial = owner_ledger()
    bad_initial["events"][0]["data"]["predecessor"] = {"issue": 1, "digest": "0" * 64}
    with pytest.raises(workflow.Invalid, match="explicit predecessor validation required"):
        state(bad_initial)


def test_issue92_one_verification_and_historical_reviewer_exclusions():
    root = Path(__file__).resolve().parents[1]
    value = issue92_fixture()
    cap = workflow.capsule_ref(value["events"][0]["data"]["capsule"])
    owner = "/root/issue84_remainder_implementation"
    value["events"].append(
        {
            "type": "phase_end",
            "at": "2026-10-08T09:07:37Z",
            "data": {"session": owner, "outcome": "pass", "evidence": "implementation self-check"},
        }
    )
    value["events"].append(
        {
            "type": "phase_start",
            "at": "2026-10-08T09:07:38Z",
            "data": {
                "phase": "verification",
                "session": owner,
                "role": "implementation_worker",
                "capsule": cap,
                "content": CONTENT,
            },
        }
    )
    value["events"].append(
        {
            "type": "phase_end",
            "at": "2026-10-08T09:07:39Z",
            "data": {"session": owner, "outcome": "pass", "evidence": "formal verification"},
        }
    )
    value["events"].append(
        {
            "type": "acceptance",
            "at": "2026-10-08T09:07:40Z",
            "data": {
                "ids": value["events"][0]["data"]["acceptance"],
                "capsule": cap,
                "content": CONTENT,
                "evidence": "focused criteria",
            },
        }
    )
    future = datetime(2026, 11, 1, tzinfo=UTC)
    verified = workflow.replay(value, future, root=root)
    assert verified.local_verification_starts == 1
    with pytest.raises(workflow.Invalid, match="verification reservation exhausted"):
        verified.gate("verification", future)
    bad = copy.deepcopy(value)
    bad["events"].append(
        {
            "type": "phase_start",
            "at": "2026-10-08T09:07:41Z",
            "data": {
                "phase": "initial_review",
                "session": "/root/pr85_last_recovery_implementation",
                "role": "code_reviewer",
                "capsule": cap,
                "content": CONTENT,
            },
        }
    )
    with pytest.raises(workflow.Invalid, match="independent read-only session"):
        workflow.replay(bad, future, root=root)
    bad["events"][-1]["data"]["session"] = "/root/issue84_correction_challenge"
    with pytest.raises(workflow.Invalid, match="independent read-only session"):
        workflow.replay(bad, future, root=root)
    good = copy.deepcopy(value)
    good["events"].append(
        {
            "type": "phase_start",
            "at": "2026-10-08T09:07:41Z",
            "data": {
                "phase": "initial_review",
                "session": "new-reviewer",
                "role": "code_reviewer",
                "capsule": cap,
                "content": CONTENT,
            },
        }
    )
    assert workflow.replay(good, future, root=root).active["phase"] == "initial_review"


def synthetic_timed_pair(monkeypatch):
    parent = ledger(issue=23)
    for _ in range(8):
        add(parent, "charge", 0, authority=AUTH, seconds=143, evidence="recorded historical time")
    add(
        parent,
        "split",
        0,
        authority={"kind": "user", "name": "burha", "evidence": "parent split"},
        successor=83,
        seconds=6051,
        reason="historical allocation",
    )
    assert workflow.replay(parent, START).split_remaining == 5
    child = ledger(issue=83)
    child["events"][0]["data"]["capsule"]["owner"]["session"] = "/root/issue83_implementation"
    child["events"][0]["data"]["predecessor"] = {"issue": 23, "digest": workflow.digest(parent)}
    ready(child, 0)
    for _ in range(4):
        add(child, "charge", 0, authority=AUTH, seconds=1, evidence="historical charge")
    add(
        child,
        "phase_start",
        0,
        phase="implementation",
        role="implementation_worker",
        session="/root/issue83_implementation",
    )
    add(
        child,
        "phase_end",
        0,
        session="/root/issue83_implementation",
        outcome="interrupted",
        evidence="capacity interruption",
    )
    add(
        child,
        "blocker",
        0,
        id="B83-EXHAUSTED",
        criterion="AC1",
        scenario="timed budget ended",
        evidence="retained interrupted outcome",
    )
    assert len(child["events"]) == 9
    monkeypatch.setattr(workflow, "ISSUE23_DIGEST", workflow.digest(parent))
    monkeypatch.setattr(workflow, "ISSUE83_DIGEST", workflow.digest(child))
    return parent, child


def synthetic_transition(parent, child, evidence="transition only"):
    add(
        child,
        "lineage_policy_transition",
        1,
        policy="owner-led-v1",
        authority={"kind": "user", "name": "burha", "evidence": evidence},
        capsule=workflow.capsule_ref(current_capsule(child)),
        prefix_digest=workflow.ISSUE83_DIGEST,
        predecessor={"issue": 23, "events": 10, "digest": workflow.ISSUE23_DIGEST},
        time_barrier="B83-EXHAUSTED",
        reason="time interpretation only",
    )
    return workflow.replay(child, START + timedelta(days=365), predecessors={23: parent})


def test_exact_suspended_lineage_transition_and_distinct_resume(monkeypatch):
    parent, child = synthetic_timed_pair(monkeypatch)
    transitioned = synthetic_transition(parent, child)
    assert transitioned.policy == "owner-led-v1"
    assert transitioned.ancestor_split_remaining_seconds == 5
    assert transitioned.historical_timed_debt_seconds is not None
    assert transitioned.suspended["phase"] == "implementation"
    assert transitioned.counts["implementation"] == transitioned.limits["implementation"] == 1
    assert (
        transitioned.author_session is None
        and not transitioned.verified
        and not transitioned.reviewed
    )
    assert list(transitioned.blockers) == ["B83-EXHAUSTED"]
    bad = copy.deepcopy(child)
    add(
        bad,
        "phase_resume",
        2,
        session="/root/issue83_implementation",
        authority={"kind": "user", "name": "renamed", "evidence": "TRANSITION  ONLY"},
        capsule=workflow.capsule_ref(current_capsule(bad)),
        reason="reused authority",
    )
    with pytest.raises(workflow.Invalid, match="distinct finite user authority"):
        workflow.replay(bad, START + timedelta(days=365), predecessors={23: parent})
    bad["events"][-1]["data"]["authority"]["evidence"] = "separate resume grant"
    resumed = workflow.replay(bad, START + timedelta(days=365), predecessors={23: parent})
    assert resumed.active["phase"] == "implementation" and resumed.counts["implementation"] == 1
    assert list(resumed.blockers) == ["B83-EXHAUSTED"] and resumed.author_session is None


def test_lineage_transition_rejects_zeroed_parent_residual(monkeypatch):
    parent, child = synthetic_timed_pair(monkeypatch)
    parent["events"][-1]["data"]["seconds"] = 6056
    monkeypatch.setattr(workflow, "ISSUE23_DIGEST", workflow.digest(parent))
    child["events"][0]["data"]["predecessor"]["digest"] = workflow.ISSUE23_DIGEST
    monkeypatch.setattr(workflow, "ISSUE83_DIGEST", workflow.digest(child))
    with pytest.raises(workflow.Invalid, match="five timed seconds"):
        synthetic_transition(parent, child)


def test_transitioned_child_cannot_reuse_timed_ancestor_approval(monkeypatch):
    parent, child = synthetic_timed_pair(monkeypatch)
    synthetic_transition(parent, child)
    add(
        child,
        "extension",
        2,
        authority={"kind": "user", "name": "different", "evidence": " PARENT  SPLIT "},
        seconds=0,
        counts={key: int(key == "remediation") for key in workflow.COUNTS},
        reason="old timed grant cannot replenish counts",
    )
    with pytest.raises(workflow.Invalid, match="authorization already consumed"):
        workflow.replay(child, START + timedelta(days=365), predecessors={23: parent})


def test_only_exact_timed_pair_may_be_introduced_and_cannot_deliver_uncertified(
    tmp_path, monkeypatch
):
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "baseline.txt").write_text("baseline", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=tmp_path, check=True)
    parent, child = synthetic_timed_pair(monkeypatch)
    synthetic_transition(parent, child)
    now = START + timedelta(days=1)
    assert workflow.check_prefix(tmp_path, "main", {23: parent, 83: child}, now) == {23, 83}
    with pytest.raises(workflow.Invalid, match="delivery"):
        workflow.replay(child, now, predecessors={23: parent}).gate("delivery", now)
    missing = copy.deepcopy(child)
    missing["events"].pop()
    with pytest.raises(workflow.Invalid, match="new ledger introduction"):
        workflow.check_prefix(tmp_path, "main", {23: parent, 83: missing}, now)
    altered = copy.deepcopy(parent)
    altered["events"][1]["data"]["seconds"] += 1
    with pytest.raises(workflow.Invalid):
        workflow.check_prefix(tmp_path, "main", {23: altered, 83: child}, now)


def test_transition_append_requires_literal_raw_pair_before_mutation(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    parent, child = synthetic_timed_pair(monkeypatch)
    ticket_dir = tmp_path / workflow.DIRECTORY
    ticket_dir.mkdir(parents=True)
    parent_path = ticket_dir / "issue-23.json"
    child_path = ticket_dir / "issue-83.json"
    parent_raw = (json.dumps(parent, indent=2) + "\n").encode()
    child_raw = (json.dumps(child, indent=2) + "\n").encode()
    parent_path.write_bytes(parent_raw)
    child_path.write_bytes(child_raw)
    monkeypatch.setattr(workflow, "ISSUE23_RAW_SHA256", hashlib.sha256(parent_raw).hexdigest())
    monkeypatch.setattr(workflow, "ISSUE83_RAW_SHA256", hashlib.sha256(child_raw).hexdigest())
    ref = workflow.capsule_ref(current_capsule(child))
    item = event(
        "lineage_policy_transition",
        1,
        policy="owner-led-v1",
        authority={"kind": "user", "name": "burha", "evidence": "distinct transition authority"},
        capsule=ref,
        prefix_digest=workflow.ISSUE83_DIGEST,
        predecessor={"issue": 23, "events": 10, "digest": workflow.ISSUE23_DIGEST},
        time_barrier="B83-EXHAUSTED",
        reason="time only",
    )
    assert workflow.append(tmp_path, 83, item, START + timedelta(seconds=1)).lineage_transition
    child_path.write_bytes(child_raw)
    parent_path.write_bytes(parent_raw + b" ")
    with pytest.raises(workflow.Invalid, match="raw retained histories"):
        workflow.append(tmp_path, 83, item, START + timedelta(seconds=1))
    assert child_path.read_bytes() == child_raw


def issue92_certified_value() -> dict:
    value = issue92_fixture()
    cap = workflow.capsule_ref(value["events"][0]["data"]["capsule"])
    owner = "/root/issue84_remainder_implementation"
    value["events"].extend(
        [
            {
                "type": "phase_end",
                "at": "2026-10-08T09:07:37Z",
                "data": {"session": owner, "outcome": "pass", "evidence": "implementation"},
            },
            {
                "type": "phase_start",
                "at": "2026-10-08T09:07:38Z",
                "data": {
                    "phase": "verification",
                    "session": owner,
                    "role": "implementation_worker",
                    "capsule": cap,
                    "content": CONTENT,
                },
            },
            {
                "type": "phase_end",
                "at": "2026-10-08T09:07:39Z",
                "data": {"session": owner, "outcome": "pass", "evidence": "verification"},
            },
            {
                "type": "acceptance",
                "at": "2026-10-08T09:07:40Z",
                "data": {
                    "ids": value["events"][0]["data"]["acceptance"],
                    "capsule": cap,
                    "content": CONTENT,
                    "evidence": "acceptance",
                },
            },
            {
                "type": "phase_start",
                "at": "2026-10-08T09:07:41Z",
                "data": {
                    "phase": "initial_review",
                    "session": "new-reviewer",
                    "role": "code_reviewer",
                    "capsule": cap,
                    "content": CONTENT,
                },
            },
            {
                "type": "phase_end",
                "at": "2026-10-08T09:07:42Z",
                "data": {
                    "session": "new-reviewer",
                    "outcome": "pass",
                    "evidence": "independent clean review",
                },
            },
        ]
    )
    return value


def test_issue92_publication_target_and_new_pr_content_binding():
    root = Path(__file__).resolve().parents[1]
    value = issue92_certified_value()
    future = datetime(2026, 11, 1, tzinfo=UTC)
    without_target = copy.deepcopy(value)
    without_target["events"].append(
        {
            "type": "delivery",
            "at": "2026-10-08T09:07:43Z",
            "data": {
                "repo": workflow.REMAINDER_REPO,
                "pr": 93,
                "content": CONTENT,
                "capsule": workflow.capsule_ref(value["events"][0]["data"]["capsule"]),
                "evidence": "unsupported transport",
            },
        }
    )
    with pytest.raises(workflow.Invalid, match="publication target"):
        workflow.replay(without_target, future, root=root)
    value["events"].append(
        {
            "type": "publication_target",
            "at": "2026-10-08T09:07:43Z",
            "data": {
                "repo": workflow.REMAINDER_REPO,
                "pr": 93,
                "grant_digest": workflow.REMAINDER_GRANT,
                "evidence": "new PR allocation",
            },
        }
    )
    wrong = copy.deepcopy(value)
    wrong["events"][-1]["data"]["pr"] = 85
    with pytest.raises(workflow.Invalid, match="publication target differs"):
        workflow.replay(wrong, future, root=root)
    value["events"].append(
        {
            "type": "delivery",
            "at": "2026-10-08T09:07:44Z",
            "data": {
                "repo": workflow.REMAINDER_REPO,
                "pr": 93,
                "content": CONTENT,
                "capsule": workflow.capsule_ref(value["events"][0]["data"]["capsule"]),
                "evidence": "new content certification",
            },
        }
    )
    delivered = workflow.replay(value, future, root=root)
    assert delivered.delivered and delivered.delivery_binding == {
        "repo": workflow.REMAINDER_REPO,
        "pr": 93,
        "content": CONTENT,
    }
    assert delivered.historical_delivery_history[0]["pr"] == 85
    event = {
        "number": 93,
        "repository": {"full_name": workflow.REMAINDER_REPO},
        "pull_request": {
            "body": "Primary issue: #92",
            "created_at": "2026-10-08T09:07:45Z",
            "head": {
                "ref": "codex/issue-92-issue84-remainder",
                "repo": {"full_name": workflow.REMAINDER_REPO},
            },
            "base": {"ref": "main", "repo": {"full_name": workflow.REMAINDER_REPO}},
        },
    }
    assert "passed" in workflow.check_pr(
        event, {92: value}, "2026-10-08T09:07:35Z", future, {92}, CONTENT, root=root
    )
    event["number"] = 85
    with pytest.raises(workflow.Invalid, match="publication PR identity"):
        workflow.check_pr(
            event, {92: value}, "2026-10-08T09:07:35Z", future, {92}, CONTENT, root=root
        )
    event["number"] = 93
    event["pull_request"]["body"] = "Primary issue: #84"
    with pytest.raises(workflow.Invalid, match="primary issue does not match"):
        workflow.check_pr(
            event, {92: value}, "2026-10-08T09:07:35Z", future, {92}, CONTENT, root=root
        )


@pytest.mark.parametrize(
    "damage", ["missing_source", "changed_supplemental", "changed_manifest", "changed_grant"]
)
def test_issue92_complete_source_and_grant_integrity(tmp_path, damage):
    root = Path(__file__).resolve().parents[1]
    value = issue92_fixture()
    archive = tmp_path / workflow.REMAINDER_ARCHIVE
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, archive)
    target = {
        "missing_source": "correction-journal.json",
        "changed_supplemental": "supplemental-completed.json",
        "changed_manifest": "closeout-manifest.json",
        "changed_grant": "finite-disposition-92.json",
    }[damage]
    if damage == "missing_source":
        (archive / target).unlink()
    else:
        (archive / target).write_bytes(b"{}")
    with pytest.raises((workflow.Invalid, OSError)):
        workflow.replay(value, datetime.now(UTC), root=tmp_path)


def test_issue92_rejects_capsule_substitution_and_second_source_claim():
    root = Path(__file__).resolve().parents[1]
    value = issue92_fixture()
    changed = copy.deepcopy(value)
    changed["events"][0]["data"]["capsule"]["rationale"] = "unapproved changed capsule"
    with pytest.raises(workflow.Invalid, match="execution capsule differs"):
        workflow.replay(changed, datetime.now(UTC), root=root)
    with pytest.raises(workflow.Invalid, match="claimed by another ticket"):
        workflow.lineage_audit({92: value, 93: copy.deepcopy(value)}, root, datetime.now(UTC))


@pytest.mark.parametrize(
    "damaged_name",
    ["closeout-manifest.json", "finite-disposition-92.json", "last-recovery-journal.json"],
)
def test_issue92_append_rechecks_actual_archive_and_grant_bytes(
    tmp_path, monkeypatch, damaged_name
):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    archive = tmp_path / workflow.REMAINDER_ARCHIVE
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, archive)
    ticket_dir = tmp_path / workflow.DIRECTORY
    ticket_dir.mkdir(parents=True)
    value = issue92_fixture()
    ticket = ticket_dir / "issue-92.json"
    ticket.write_text(json.dumps(value), encoding="utf-8")
    item = {
        "type": "phase_end",
        "at": "2026-10-08T09:07:37Z",
        "data": {
            "session": "/root/issue84_remainder_implementation",
            "outcome": "pass",
            "evidence": "fixture implementation",
        },
    }
    future = datetime(2026, 11, 1, tzinfo=UTC)
    baseline = ticket.read_bytes()
    assert (
        workflow.append(tmp_path, 92, item, future).author_session
        == "/root/issue84_remainder_implementation"
    )
    ticket.write_bytes(baseline)
    real_working = workflow.working_bytes
    calls = 0

    def changed_working(root_path, issue):
        nonlocal calls
        calls += 1
        if calls == 2:
            (archive / damaged_name).write_bytes((archive / damaged_name).read_bytes() + b" ")
        return real_working(root_path, issue)

    monkeypatch.setattr(workflow, "working_bytes", changed_working)
    with pytest.raises(workflow.Invalid, match="append input changed"):
        workflow.append(tmp_path, 92, item, future)
    assert ticket.read_bytes() == baseline


def assert_issue92_event_derived_state(value: dict, state: workflow.State) -> None:
    """Check mutable saved tails from event facts, independently of production replay."""
    events = value["events"]
    starts = [event for event in events if event["type"] == "phase_start"]
    expected_counts = {
        "implementation": 4,
        "initial_review": 3,
        "remediation": 4,
        "final_review": 4,
        "design_reset": 4,
    }
    expected_limits = {
        "implementation": 5,
        "initial_review": 4,
        "remediation": 4,
        "final_review": 4,
        "design_reset": 4,
    }
    expected_verification_limit = 1
    stages = {"recovery": "absent", "pr": "absent", "fixture": "absent"}
    failures = {"recovery": None, "pr": None, "fixture": None}
    current_stage = None
    active = None
    suspended = None
    verified_content = None
    acceptance_content = None
    review_content = None
    delivery_content = None
    for index, event in enumerate(events, 1):
        kind, data = event["type"], event["data"]
        if kind == "issue92_recovery":
            current_stage = "recovery"
            stages[current_stage] = "repair_pending"
            expected_limits.update(remediation=5, initial_review=4)
            expected_verification_limit = 2
        elif kind == "issue92_pr_identity_repair":
            current_stage = "pr"
            stages[current_stage] = "repair_pending"
            expected_limits.update(remediation=6, final_review=5)
            expected_verification_limit = 3
        elif kind == "issue92_stage_fixture_repair":
            current_stage = "fixture"
            stages[current_stage] = "repair_pending"
            expected_limits["remediation"] = 7
            expected_verification_limit = 4
        elif kind == "phase_start":
            phase = data["phase"]
            if phase in expected_counts:
                expected_counts[phase] += 1
            active = {**data, "at": event["at"]}
            if phase in {"remediation", "verification"}:
                verified_content = acceptance_content = review_content = None
            if current_stage and phase in {
                "remediation",
                "verification",
                "final_review",
                "initial_review",
            }:
                stages[current_stage] = {
                    "remediation": "repairing",
                    "verification": "verifying",
                    "final_review": "reviewing",
                    "initial_review": "reviewing",
                }[phase]
        elif kind == "pause":
            suspended, active = active, None
        elif kind == "phase_resume":
            active, suspended = {**suspended, "at": event["at"]}, None
        elif kind == "phase_end":
            phase = active["phase"]
            if data["outcome"] == "pass":
                if phase == "verification":
                    verified_content = active["content"]
                elif phase in {"initial_review", "final_review"}:
                    review_content = active["content"]
            active = None
            if current_stage and phase in {
                "remediation",
                "verification",
                "final_review",
                "initial_review",
            }:
                if data["outcome"] == "fail":
                    stages[current_stage] = "failed"
                    failures[current_stage] = {"phase": phase, "event_index": index}
                else:
                    stages[current_stage] = {
                        "remediation": "repaired",
                        "verification": "verified",
                        "final_review": "reviewed",
                        "initial_review": "reviewed",
                    }[phase]
        elif kind == "acceptance":
            acceptance_content = data["content"]
        elif kind == "delivery" and current_stage:
            stages[current_stage] = "delivered"
            delivery_content = data["content"]
    assert state.counts == expected_counts
    assert state.limits == expected_limits
    assert state.local_verification_starts == sum(
        event["data"]["phase"] == "verification" for event in starts
    )
    assert state.local_verification_limit == expected_verification_limit
    assert state.active == active
    assert state.suspended == suspended
    assert state.issue92_recovery_stage == stages["recovery"]
    assert state.issue92_pr_identity_stage == stages["pr"]
    assert state.issue92_stage_fixture_stage == stages["fixture"]
    assert state.issue92_pr_identity_failure == failures["pr"]
    assert state.issue92_stage_fixture_failure == failures["fixture"]
    assert state.verified_content == verified_content
    assert state.acceptance_content == acceptance_content
    assert state.review_content == review_content
    if delivery_content is not None:
        assert state.delivery_binding["content"] == delivery_content


def test_issue92_actual_saved_recovery_and_portable_baselines():
    root = Path(__file__).resolve().parents[1]
    current = workflow.read_all(root)[92]
    stop = issue92_fixture("stop_ledger")
    bootstrap = issue92_fixture()
    assert stop["events"][:2] == bootstrap["events"]
    assert current["events"][:6] == stop["events"]
    assert current["events"][6:8] == issue92_recovery_fixture()["events"][6:8]
    assert workflow.digest({"schema": 1, "events": current["events"][:6]}) == workflow.RECOVERY_STOP
    state = workflow.replay(current, datetime.now(UTC), root=root)
    assert state.issue92_recovery_ref == {
        "grant_digest": workflow.RECOVERY_GRANT,
        "proposal_digest": workflow.RECOVERY_PROPOSAL,
        "closeout_digest": workflow.RECOVERY_CLOSEOUT,
    }
    assert_issue92_event_derived_state(current, state)
    assert state.inherited_counts == workflow.INHERITED_REMAINDER_COUNTS
    assert state.historical_delivery_history[0]["pr"] == 85
    if state.active and state.active["phase"] in {
        "verification",
        "initial_review",
        "final_review",
    }:
        assert state.active["content"] == workflow.content_digest(root, 92)
    if state.delivered:
        assert state.delivery_binding["content"] == workflow.content_digest(root, 92)
    assert (
        workflow.replay(bootstrap, datetime(2026, 11, 1, tzinfo=UTC), root=root).active["phase"]
        == "implementation"
    )
    stopped = workflow.replay(stop, datetime(2026, 11, 1, tzinfo=UTC), root=root)
    assert set(stopped.blockers) == {workflow.RECOVERY_BLOCKER}
    with pytest.raises(workflow.Invalid, match="finite grant has no allowance"):
        stopped.gate("remediation", datetime(2026, 11, 1, tzinfo=UTC))


def test_issue92_recovery_counted_progression_and_conserved_review():
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    recovering = workflow.replay(issue92_recovery_fixture(), future, root=root)
    assert recovering.issue92_recovery_stage == "repairing"
    assert recovering.counts == {
        "implementation": 5,
        "initial_review": 3,
        "remediation": 5,
        "final_review": 4,
        "design_reset": 4,
    }
    assert recovering.limits == recovering.counts | {"initial_review": 4}
    assert recovering.local_verification_starts == 1
    assert recovering.local_verification_limit == 2
    assert not recovering.verified and not recovering.accepted and not recovering.reviewed
    assert set(recovering.blockers) == {workflow.RECOVERY_BLOCKER}
    repaired = workflow.replay(issue92_repaired_fixture(), future, root=root)
    assert repaired.issue92_recovery_stage == "verified"
    assert repaired.local_verification_starts == 2
    assert repaired.verified and repaired.accepted and not repaired.reviewed
    with pytest.raises(workflow.Invalid, match="verification reservation exhausted"):
        repaired.gate("verification", future)
    reviewed = workflow.replay(issue92_repaired_fixture(review=True), future, root=root)
    assert reviewed.issue92_recovery_stage == "reviewed"
    assert reviewed.reviewed and reviewed.counts["initial_review"] == 4
    assert reviewed.counts["final_review"] == 4
    assert reviewed.issue92_review_disposition == (
        "retain-unused-initial-review-after-single-pre-review-repair"
    )


@pytest.mark.parametrize(
    "field,bad",
    [
        ("grant_digest", "0" * 64),
        ("proposal_digest", "0" * 64),
        ("closeout_digest", "0" * 64),
        ("prefix_digest", "0" * 64),
        ("authority_anchor", "reused alias"),
        ("version", "other"),
    ],
)
def test_issue92_recovery_rejects_changed_event_bindings(field, bad):
    root = Path(__file__).resolve().parents[1]
    value = issue92_recovery_fixture()
    value["events"][6]["data"][field] = bad
    with pytest.raises(workflow.Invalid, match="exact stopped failed history"):
        workflow.replay(value, datetime(2026, 11, 1, tzinfo=UTC), root=root)


def test_issue92_recovery_rejects_wrong_owner_capsule_and_extra_keys():
    root = Path(__file__).resolve().parents[1]
    value = issue92_recovery_fixture()
    future = datetime(2026, 11, 1, tzinfo=UTC)
    changed = copy.deepcopy(value)
    changed["events"][7]["data"]["session"] = "replacement"
    with pytest.raises(workflow.Invalid, match="write phase differs"):
        workflow.replay(changed, future, root=root)
    changed = copy.deepcopy(value)
    changed["events"][6]["data"]["capsule"]["generation"] = 2
    with pytest.raises(workflow.Invalid, match="capsule content/generation"):
        workflow.replay(changed, future, root=root)
    changed = copy.deepcopy(value)
    changed["events"][6]["data"]["unexpected"] = "x"
    with pytest.raises(workflow.Invalid, match="expected fields"):
        workflow.replay(changed, future, root=root)
    changed = copy.deepcopy(value)
    changed["events"][6]["at"] = "2026-10-09T10:12:24Z"
    with pytest.raises(workflow.Invalid, match="exact stopped failed history"):
        workflow.replay(changed, future, root=root)
    changed = copy.deepcopy(value)
    changed["events"][5]["data"]["scenario"] = "relabelled old failure"
    with pytest.raises(workflow.Invalid, match="exact stopped failed history"):
        workflow.replay(changed, future, root=root)
    changed = copy.deepcopy(value)
    changed["events"].insert(7, copy.deepcopy(changed["events"][6]))
    with pytest.raises(workflow.Invalid):
        workflow.replay(changed, future, root=root)


def test_issue92_recovery_rejects_premature_and_repeated_actions():
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    value = issue92_recovery_fixture()
    value["events"].append(
        {
            "type": "resolve",
            "at": "2026-10-09T10:12:26Z",
            "data": {"id": workflow.RECOVERY_BLOCKER, "evidence": "premature"},
        }
    )
    with pytest.raises(workflow.Invalid, match="active phase"):
        workflow.replay(value, future, root=root)
    value = issue92_recovery_fixture()
    value["events"].append(
        {
            "type": "phase_end",
            "at": "2026-10-09T10:12:26Z",
            "data": {"session": workflow.RECOVERY_OWNER, "outcome": "pass", "evidence": "repair"},
        }
    )
    second = copy.deepcopy(value)
    second["events"].append(
        {
            "type": "phase_start",
            "at": "2026-10-09T10:12:27Z",
            "data": value["events"][7]["data"],
        }
    )
    with pytest.raises(workflow.Invalid, match="single recovery remediation"):
        workflow.replay(second, future, root=root)
    premature = copy.deepcopy(value)
    premature["events"].append(
        {
            "type": "phase_start",
            "at": "2026-10-09T10:12:27Z",
            "data": {
                "phase": "verification",
                "session": workflow.RECOVERY_OWNER,
                "role": "implementation_worker",
                "capsule": workflow.RECOVERY_CAPSULE_REF,
                "content": CONTENT,
            },
        }
    )
    with pytest.raises(workflow.Invalid, match="completed bounded remediation"):
        workflow.replay(premature, future, root=root)
    review = issue92_repaired_fixture()
    review["events"].pop()  # remove acceptance, retain completed verification
    review["events"].append(
        {
            "type": "phase_start",
            "at": "2026-10-09T10:12:30Z",
            "data": {
                "phase": "initial_review",
                "session": "new-independent-reviewer",
                "role": "code_reviewer",
                "capsule": workflow.RECOVERY_CAPSULE_REF,
                "content": CONTENT,
            },
        }
    )
    with pytest.raises(workflow.Invalid, match="review requires current matching"):
        workflow.replay(review, future, root=root)


@pytest.mark.parametrize("phase", ["remediation", "verification", "initial_review"])
def test_issue92_completed_recovery_failure_stops_phase_and_delivery(phase):
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    if phase == "remediation":
        value = issue92_recovery_fixture()
    elif phase == "verification":
        value = issue92_repaired_fixture()
        value["events"] = value["events"][:-2]  # end at fresh verification start
    else:
        value = issue92_repaired_fixture(review=True)
        value["events"] = value["events"][:-1]
    value["events"].append(
        {
            "type": "phase_end",
            "at": "2026-10-09T10:12:33Z",
            "data": {
                "session": "new-independent-reviewer"
                if phase == "initial_review"
                else workflow.RECOVERY_OWNER,
                "outcome": "fail",
                "evidence": "completed failed gate",
            },
        }
    )
    failed = workflow.replay(value, future, root=root)
    assert failed.issue92_recovery_stage == "failed"
    assert failed.issue92_recovery_failure == phase
    with pytest.raises(workflow.Invalid):
        failed.gate("delivery", future)
    failed_value = copy.deepcopy(value)
    failed_value["events"].append(
        {
            "type": "acceptance",
            "at": "2026-10-09T10:12:34Z",
            "data": {
                "ids": value["events"][0]["data"]["acceptance"],
                "capsule": workflow.RECOVERY_CAPSULE_REF,
                "content": CONTENT,
                "evidence": "false recertification",
            },
        }
    )
    with pytest.raises(workflow.Invalid, match="stops substantive events"):
        workflow.replay(failed_value, future, root=root)


def test_issue92_normalized_reviewer_aliases_excluded_after_positive_gate():
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    base = issue92_repaired_fixture()
    assert workflow.replay(issue92_repaired_fixture(review=True), future, root=root).reviewed
    for session in (
        " /ROOT/ISSUE84_REMAINDER_IMPLEMENTATION ",
        "/ROOT/ISSUE92_RECOVERY_DESIGN",
        "/root/issue92_recovery_challenge",
    ):
        bad = copy.deepcopy(base)
        bad["events"].append(
            {
                "type": "phase_start",
                "at": "2026-10-09T10:12:31Z",
                "data": {
                    "phase": "initial_review",
                    "session": session,
                    "role": "code_reviewer",
                    "capsule": workflow.RECOVERY_CAPSULE_REF,
                    "content": CONTENT,
                },
            }
        )
        with pytest.raises(workflow.Invalid, match="independent read-only"):
            workflow.replay(bad, future, root=root)


@pytest.mark.parametrize(
    "filename",
    [
        *workflow.RECOVERY_SOURCE_FILES.values(),
        *workflow.RECOVERY_CLOSEOUT_FILES.values(),
        "closeout-manifest.json",
        "finite-grant.json",
    ],
)
def test_issue92_recovery_every_frozen_source_rejects_mutation(tmp_path, filename):
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, tmp_path / workflow.REMAINDER_ARCHIVE)
    shutil.copytree(root / workflow.RECOVERY_ARCHIVE, tmp_path / workflow.RECOVERY_ARCHIVE)
    future = datetime(2026, 11, 1, tzinfo=UTC)
    assert (
        workflow.replay(issue92_recovery_fixture(), future, root=tmp_path).active["phase"]
        == "remediation"
    )
    target = tmp_path / workflow.RECOVERY_ARCHIVE / filename
    target.write_bytes(b"{}")
    with pytest.raises((workflow.Invalid, OSError, KeyError, TypeError)):
        workflow.replay(issue92_recovery_fixture(), future, root=tmp_path)


@pytest.mark.parametrize(
    "filename", ["finite-grant.json", "closeout-manifest.json", "challenge-result.json"]
)
def test_issue92_recovery_append_rechecks_grant_closeout_and_source_bytes(
    tmp_path, monkeypatch, filename
):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, tmp_path / workflow.REMAINDER_ARCHIVE)
    archive = tmp_path / workflow.RECOVERY_ARCHIVE
    shutil.copytree(root / workflow.RECOVERY_ARCHIVE, archive)
    ticket = tmp_path / workflow.DIRECTORY / "issue-92.json"
    ticket.parent.mkdir(parents=True)
    ticket.write_text(json.dumps(issue92_recovery_fixture()), encoding="utf-8")
    baseline = ticket.read_bytes()
    item = {
        "type": "phase_end",
        "at": "2026-10-09T10:12:26Z",
        "data": {
            "session": workflow.RECOVERY_OWNER,
            "outcome": "pass",
            "evidence": "fixture repair selfcheck",
        },
    }
    future = datetime(2026, 11, 1, tzinfo=UTC)
    assert workflow.append(tmp_path, 92, item, future).issue92_recovery_stage == "repaired"
    ticket.write_bytes(baseline)
    original_working = workflow.working_bytes
    calls = 0

    def mutate_on_final(root_path, issue):
        nonlocal calls
        calls += 1
        if calls == 2:
            target = archive / filename
            target.write_bytes(target.read_bytes() + b" ")
        return original_working(root_path, issue)

    monkeypatch.setattr(workflow, "working_bytes", mutate_on_final)
    with pytest.raises(workflow.Invalid, match="append input changed"):
        workflow.append(tmp_path, 92, item, future)
    assert calls >= 2
    assert ticket.read_bytes() == baseline


def test_issue92_recovery_event_append_source_and_membership_races(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, tmp_path / workflow.REMAINDER_ARCHIVE)
    shutil.copytree(root / workflow.RECOVERY_ARCHIVE, tmp_path / workflow.RECOVERY_ARCHIVE)
    ticket = tmp_path / workflow.DIRECTORY / "issue-92.json"
    ticket.parent.mkdir(parents=True)
    ticket.write_text(json.dumps(issue92_fixture("stop_ledger")), encoding="utf-8")
    baseline = ticket.read_bytes()
    item = issue92_recovery_event()
    event_file = tmp_path / "candidate-event.json"
    event_file.write_text(json.dumps(item), encoding="utf-8")
    future = datetime(2026, 11, 1, tzinfo=UTC)
    assert (
        workflow.append(tmp_path, 92, item, future, source_path=event_file).issue92_recovery_stage
        == "repair_pending"
    )
    ticket.write_bytes(baseline)
    original_working = workflow.working_bytes
    calls = 0

    def mutate_source(root_path, issue):
        nonlocal calls
        calls += 1
        if calls == 2:
            event_file.write_bytes(event_file.read_bytes() + b" ")
        return original_working(root_path, issue)

    monkeypatch.setattr(workflow, "working_bytes", mutate_source)
    with pytest.raises(workflow.Invalid, match="append input changed"):
        workflow.append(tmp_path, 92, item, future, source_path=event_file)
    assert calls >= 2 and ticket.read_bytes() == baseline


@pytest.mark.parametrize(
    "damage",
    ["boolean_count", "changed_delta", "changed_owner", "changed_publication", "reused_authority"],
)
def test_issue92_recovery_rejects_rebound_bad_grant(tmp_path, monkeypatch, damage):
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, tmp_path / workflow.REMAINDER_ARCHIVE)
    folder = tmp_path / workflow.RECOVERY_ARCHIVE
    shutil.copytree(root / workflow.RECOVERY_ARCHIVE, folder)
    path = folder / "finite-grant.json"
    grant = workflow.strict_json(path.read_bytes())
    if damage == "boolean_count":
        grant["count_deltas"]["remediation"] = True
    elif damage == "changed_delta":
        grant["supplemental_deltas"]["verification"] = 2
    elif damage == "changed_owner":
        grant["owner"]["session"] = "/root/replacement"
    elif damage == "changed_publication":
        grant["publication"]["additional_count"] = 1
    else:
        grant["authority"]["evidence"] = workflow.remainder_sources(root)[1]["authority"][
            "evidence"
        ]
    path.write_text(json.dumps(grant), encoding="utf-8")
    monkeypatch.setattr(workflow, "RECOVERY_GRANT", workflow.digest(grant))
    with pytest.raises(
        workflow.Invalid,
        match=(
            r"recovery grant differs|publication grant differs|"
            r"reuses prior authority|bounded nonnegative integer"
        ),
    ):
        workflow.recovery_sources(tmp_path)


@pytest.mark.parametrize("damage", ["failed_challenge", "blocked_decision"])
def test_issue92_recovery_rejects_rebound_failed_challenge_or_approval(
    tmp_path, monkeypatch, damage
):
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, tmp_path / workflow.REMAINDER_ARCHIVE)
    folder = tmp_path / workflow.RECOVERY_ARCHIVE
    shutil.copytree(root / workflow.RECOVERY_ARCHIVE, folder)
    name = "challenge-result.json" if damage == "failed_challenge" else "coordinator-decision.json"
    path = folder / name
    value = workflow.strict_json(path.read_bytes())
    value["outcome"] = "CHALLENGE_FAIL" if damage == "failed_challenge" else "blocked"
    path.write_text(json.dumps(value), encoding="utf-8")
    manifest_path = folder / "closeout-manifest.json"
    manifest = workflow.strict_json(manifest_path.read_bytes())
    descriptor_name = "challenge_result" if damage == "failed_challenge" else "coordinator_decision"
    manifest["sources"][descriptor_name]["raw_sha256"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    manifest["sources"][descriptor_name]["canonical_sha256"] = workflow.digest(value)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    grant_path = folder / "finite-grant.json"
    grant = workflow.strict_json(grant_path.read_bytes())
    grant["closeout_digest"] = workflow.digest(manifest)
    grant_path.write_text(json.dumps(grant), encoding="utf-8")
    monkeypatch.setattr(workflow, "RECOVERY_CLOSEOUT", workflow.digest(manifest))
    monkeypatch.setattr(workflow, "RECOVERY_GRANT", workflow.digest(grant))
    with pytest.raises(workflow.Invalid, match="challenge or coordinator approval absent"):
        workflow.recovery_sources(tmp_path)


def test_issue92_recovery_interrupted_resumes_exact_reservation_without_count():
    root = Path(__file__).resolve().parents[1]
    value = issue92_recovery_fixture()
    value["events"].extend(
        [
            {
                "type": "phase_end",
                "at": "2026-10-09T10:12:26Z",
                "data": {
                    "session": workflow.RECOVERY_OWNER,
                    "outcome": "interrupted",
                    "evidence": "capacity interruption",
                },
            },
            {
                "type": "phase_resume",
                "at": "2026-10-09T10:12:27Z",
                "data": {"session": workflow.RECOVERY_OWNER},
            },
        ]
    )
    state = workflow.replay(value, datetime(2026, 11, 1, tzinfo=UTC), root=root)
    assert state.active["phase"] == "remediation"
    assert state.counts["remediation"] == 5
    assert state.local_verification_starts == 1


def test_issue92_recovered_publication_and_exact_pr_binding():
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    value = issue92_repaired_fixture(review=True)
    target = {
        "type": "publication_target",
        "at": "2026-10-09T10:12:33Z",
        "data": {
            "repo": workflow.REMAINDER_REPO,
            "pr": 93,
            "grant_digest": workflow.REMAINDER_GRANT,
            "evidence": "one new PR",
        },
    }
    value["events"].append(target)
    assert workflow.replay(value, future, root=root).publication_target["pr"] == 93
    value["events"].append(
        {
            "type": "delivery",
            "at": "2026-10-09T10:12:34Z",
            "data": {
                "repo": workflow.REMAINDER_REPO,
                "pr": 93,
                "content": CONTENT,
                "capsule": workflow.RECOVERY_CAPSULE_REF,
                "evidence": "saved repaired delivery",
            },
        }
    )
    assert workflow.replay(value, future, root=root).issue92_recovery_stage == "delivered"
    event = {
        "number": 93,
        "repository": {"full_name": workflow.REMAINDER_REPO},
        "pull_request": {
            "body": "Primary issue: #92",
            "created_at": "2026-10-09T10:12:35Z",
            "head": {
                "ref": "codex/issue-92-issue84-remainder",
                "repo": {"full_name": workflow.REMAINDER_REPO},
            },
            "base": {"ref": "main", "repo": {"full_name": workflow.REMAINDER_REPO}},
        },
    }
    assert "passed" in workflow.check_pr(
        event, {92: value}, "2026-10-09T10:12:34Z", future, {92}, CONTENT, root=root
    )
    for field, bad in (("number", 85), ("number", 94)):
        changed = copy.deepcopy(event)
        changed[field] = bad
        with pytest.raises(workflow.Invalid):
            workflow.check_pr(
                changed, {92: value}, "2026-10-09T10:12:34Z", future, {92}, CONTENT, root=root
            )
    for field, bad in (("body", "Primary issue: #84"), ("created_at", "2026-10-09T10:12:25Z")):
        changed = copy.deepcopy(event)
        changed["pull_request"][field] = bad
        with pytest.raises(workflow.Invalid):
            workflow.check_pr(
                changed, {92: value}, "2026-10-09T10:12:34Z", future, {92}, CONTENT, root=root
            )
    for field, bad in (("head", "other"), ("base", "other")):
        changed = copy.deepcopy(event)
        changed["pull_request"][field]["ref"] = bad
        with pytest.raises(workflow.Invalid, match="publication PR identity"):
            workflow.check_pr(
                changed, {92: value}, "2026-10-09T10:12:34Z", future, {92}, CONTENT, root=root
            )
    with pytest.raises(workflow.Invalid, match="different content"):
        workflow.check_pr(
            event, {92: value}, "2026-10-09T10:12:34Z", future, {92}, "0" * 64, root=root
        )


def test_issue92_recovered_target_append_requires_actual_current_content(tmp_path):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    shutil.copytree(root / workflow.REMAINDER_ARCHIVE, tmp_path / workflow.REMAINDER_ARCHIVE)
    shutil.copytree(root / workflow.RECOVERY_ARCHIVE, tmp_path / workflow.RECOVERY_ARCHIVE)
    source = tmp_path / "source.txt"
    source.write_bytes(b"original\n")
    ticket = tmp_path / workflow.DIRECTORY / "issue-92.json"
    ticket.parent.mkdir(parents=True)
    value = issue92_repaired_fixture(review=True)
    ticket.write_text(json.dumps(value), encoding="utf-8")
    current_content = workflow.content_digest(tmp_path, 92)
    for item in value["events"]:
        if item["data"].get("content") == CONTENT:
            item["data"]["content"] = current_content
    ticket.write_text(json.dumps(value), encoding="utf-8")
    baseline = ticket.read_bytes()
    target = {
        "type": "publication_target",
        "at": "2026-10-09T10:12:33Z",
        "data": {
            "repo": workflow.REMAINDER_REPO,
            "pr": 93,
            "grant_digest": workflow.REMAINDER_GRANT,
            "evidence": "one new PR",
        },
    }
    future = datetime(2026, 11, 1, tzinfo=UTC)
    assert workflow.append(tmp_path, 92, target, future).publication_target["pr"] == 93
    ticket.write_bytes(baseline)
    source.write_bytes(b"changed\n")
    with pytest.raises(workflow.Invalid, match="target differs from current content"):
        workflow.append(tmp_path, 92, target, future)
    assert ticket.read_bytes() == baseline


def test_issue92_recovery_marker_claim_and_ordinary_renewals_reject():
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    value = issue92_recovery_fixture()
    assert workflow.lineage_audit({92: value}, root, future) is None
    duplicate = copy.deepcopy(value)
    del duplicate["events"][0]["data"]["issue84_remainder"]
    with pytest.raises(workflow.Invalid, match="recovery marker claimed outside"):
        workflow.lineage_audit({92: value, 93: duplicate}, root, future)
    for kind in ("extension", "continuation"):
        bad = copy.deepcopy(value)
        bad["events"].append({"type": kind, "at": "2026-10-09T10:12:26Z", "data": {}})
        with pytest.raises(workflow.Invalid, match="forbids"):
            workflow.replay(bad, future, root=root)
    reviewed = issue92_repaired_fixture(review=True)
    reviewed["events"].append(
        {
            "type": "publication_target",
            "at": "2026-10-09T10:12:33Z",
            "data": {
                "repo": workflow.REMAINDER_REPO,
                "pr": 85,
                "grant_digest": workflow.REMAINDER_GRANT,
                "evidence": "old target alias",
            },
        }
    )
    with pytest.raises(workflow.Invalid, match="publication target differs"):
        workflow.replay(reviewed, future, root=root)


def test_repository_lock_blocks_cross_ticket_writers(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    workflow.append(tmp_path, 86, owner_ledger()["events"][0], START)
    second = owner_ledger()
    second["events"][0]["data"]["issue"] = 87
    second["events"][0]["data"]["capsule"] = make_capsule(issue=87)
    workflow.append(tmp_path, 87, second["events"][0], START)
    lock = tmp_path / workflow.DIRECTORY / ".repository.lock"
    lock.touch()
    for issue in (86, 87):
        current = workflow.read_all(tmp_path)[issue]
        ready_event = event(
            "design_ready",
            1,
            authority=AUTH,
            evidence="ready",
            capsule=workflow.capsule_ref(current["events"][0]["data"]["capsule"]),
        )
        with pytest.raises(workflow.Invalid, match="another writer"):
            workflow.append(tmp_path, issue, ready_event, START + timedelta(seconds=1))
    assert len(workflow.read_all(tmp_path)[86]["events"]) == 1
    assert len(workflow.read_all(tmp_path)[87]["events"]) == 1


@pytest.mark.parametrize("damage", ["raw_crlf", "new_member"])
def test_append_final_raw_content_and_membership_race(tmp_path, monkeypatch, damage):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    source = tmp_path / "source.txt"
    source.write_bytes(b"alpha\nbeta\n")
    initial = owner_ledger()["events"][0]
    workflow.append(tmp_path, 86, initial, START)
    ticket = tmp_path / workflow.DIRECTORY / "issue-86.json"
    baseline = ticket.read_bytes()
    item = event(
        "design_ready",
        1,
        authority=AUTH,
        evidence="approved",
        capsule=workflow.capsule_ref(initial["data"]["capsule"]),
    )
    assert workflow.append(tmp_path, 86, item, START + timedelta(seconds=1)).ready
    ticket.write_bytes(baseline)
    canonical_before = workflow.content_digest(tmp_path, 86)
    real_working = workflow.working_bytes
    calls = 0

    def changed_working(root_path, issue):
        nonlocal calls
        calls += 1
        if calls == 2:
            if damage == "raw_crlf":
                source.write_bytes(b"alpha\r\nbeta\r\n")
            else:
                (tmp_path / "new-member.txt").write_bytes(b"new member")
        return real_working(root_path, issue)

    monkeypatch.setattr(workflow, "working_bytes", changed_working)
    with pytest.raises(workflow.Invalid, match="append input changed"):
        workflow.append(tmp_path, 86, item, START + timedelta(seconds=1))
    assert ticket.read_bytes() == baseline
    if damage == "raw_crlf":
        assert workflow.content_digest(tmp_path, 86) == canonical_before


def test_owner_continuation_rejects_reused_authority_and_wrong_pr():
    value = owner_ledger(True)
    owner_ready(value)
    phase(value, "implementation", 6)
    owner_certify(value, 8, "initial_review")
    add(value, "delivery", 14, evidence="original", pr=87)
    with pytest.raises(workflow.Invalid, match="terminal"):
        damaged = copy.deepcopy(value)
        phase(damaged, "remediation", 15)
        state(damaged)
    owner_continue(value, 15, "explicit finite continuation")
    for evidence in [" EXPLICIT\nFINITE continuation ", "explicit finite continuation"]:
        damaged = copy.deepcopy(value)
        add(
            damaged,
            "continuation",
            17,
            authority={"kind": "user", "name": "renamed", "evidence": evidence},
            counts={k: 1 if k in {"remediation", "final_review"} else 0 for k in workflow.COUNTS},
            capsule=workflow.capsule_ref(current_capsule(damaged)),
            reason="same-scope correction",
        )
        with pytest.raises(workflow.Invalid, match="authorization already consumed"):
            state(damaged)
    phase(value, "remediation", 17)
    owner_certify(value, 19, "final_review")
    wrong = copy.deepcopy(value)
    add(wrong, "delivery", 25, evidence="wrong PR", pr=88)
    with pytest.raises(workflow.Invalid, match="original repository and PR"):
        state(wrong)
    add(value, "delivery", 25, evidence="same PR", pr=87)
    with pytest.raises(workflow.Invalid, match="another PR"):
        workflow.check_pr(
            pr(body="Primary issue: #86"),
            {86: value},
            at(0),
            START + timedelta(seconds=25),
            content=CONTENT,
        )


def test_owner_current_certification_cannot_reuse_old_review_or_failed_remediation():
    value = owner_ledger(True)
    owner_ready(value)
    phase(value, "implementation", 6)
    owner_certify(value, 8, "initial_review")
    add(value, "delivery", 14, evidence="original", pr=87)
    owner_continue(value, 15, "fresh specific continuation")
    damaged = copy.deepcopy(value)
    add(damaged, "delivery", 17, evidence="stale reused delivery", pr=87)
    with pytest.raises(workflow.Invalid, match="delivery identity/content mismatch"):
        state(damaged)
    phase(value, "remediation", 17, outcome="fail")
    with pytest.raises(workflow.Invalid, match="completed remediation"):
        state(value, 19).gate("final_review", START + timedelta(seconds=19))
    assert not state(value, 19).remediated


def test_owner_failed_verification_and_final_review_never_reuse_old_success():
    value = owner_ledger(True)
    owner_ready(value)
    phase(value, "implementation", 6)
    owner_certify(value, 8, "initial_review")
    add(value, "delivery", 14, evidence="original", pr=87)
    owner_continue(value, 15, "finite failure repair allowance")
    phase(value, "remediation", 17)
    phase(value, "verification", 19, outcome="fail")
    failed = state(value, 21)
    assert not failed.verified and not failed.accepted and not failed.reviewed
    with pytest.raises(workflow.Invalid, match="current matching verification"):
        add(value, "acceptance", 21, ids=["AC1"], evidence="stale acceptance")
        state(value, 21)
    value["events"].pop()
    with pytest.raises(workflow.Invalid, match="bounded remediation"):
        state(value, 21).gate("verification", START + timedelta(seconds=21))
    add(
        value,
        "blocker",
        21,
        id="VF1",
        criterion="AC1",
        scenario="failed verification requires source correction",
        evidence="failed gate",
    )
    add(
        value,
        "extension",
        22,
        authority={"kind": "user", "name": "user", "evidence": "fresh finite failed check repair"},
        seconds=0,
        counts={k: 1 if k in {"remediation", "final_review"} else 0 for k in workflow.COUNTS},
        reason="repair failed verification",
    )
    phase(value, "remediation", 23)
    add(value, "resolve", 25, id="VF1", evidence="repaired")
    owner_certify(value, 26)
    phase(value, "final_review", 29, outcome="fail")
    failed = state(value, 31)
    assert failed.final_failed and not failed.reviewed
    with pytest.raises(workflow.Invalid, match="open phase or unresolved blocker"):
        add(value, "delivery", 31, evidence="failed final", pr=87)
        state(value, 31)


def test_owner_handoff_preserves_historical_reviewer_exclusion():
    value = owner_ledger(True)
    owner_ready(value)
    phase(value, "implementation", 6)
    owner_certify(value, 8, "initial_review")
    add(value, "delivery", 14, evidence="original", pr=87)
    owner_continue(value, 15, "finite handoff repair grant")
    add(
        value,
        "owner_handoff",
        17,
        authority=AUTH,
        owner={
            "role": "implementation_worker",
            "model": "gpt-6-sol",
            "effort": "medium",
            "session": "replacement-owner",
        },
        reason="explicit legitimate owner handoff",
        escalation=None,
    )
    add(
        value,
        "phase_start",
        18,
        phase="remediation",
        role="implementation_worker",
        session="replacement-owner",
    )
    add(
        value,
        "phase_end",
        19,
        session="replacement-owner",
        outcome="pass",
        evidence="repair complete",
    )
    add(
        value,
        "phase_start",
        20,
        phase="verification",
        role="implementation_worker",
        session="replacement-owner",
    )
    add(
        value,
        "phase_end",
        21,
        session="replacement-owner",
        outcome="pass",
        evidence="fresh verification",
    )
    add(value, "acceptance", 22, ids=["AC1"], evidence="fresh acceptance")
    assert state(value, 22).write_authors == {"worker", "replacement-owner"}
    add(value, "phase_start", 23, phase="final_review", role="code_reviewer", session="worker")
    with pytest.raises(workflow.Invalid, match="independent read-only session"):
        state(value, 23)


def test_owner_actual_saved_delivery_continuation_and_redelivery(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    source = tmp_path / "source.txt"
    source.write_text("original content\n", encoding="utf-8")
    value = owner_ledger(True)
    owner_ready(value)
    phase(value, "implementation", 6)
    first_content = workflow.content_digest(tmp_path, 86)
    owner_certify(value, 8, "initial_review")
    add(value, "delivery", 14, evidence="first published content", pr=87)
    for item in value["events"]:
        if item["type"] in {"phase_start", "acceptance", "delivery"} and "content" in item["data"]:
            item["data"]["content"] = first_content
        workflow.append(tmp_path, 86, item, workflow.timestamp(item["at"]))
    saved = workflow.read_all(tmp_path)[86]
    original = copy.deepcopy(saved["events"])
    assert workflow.check_pr(
        {**pr(body="Primary issue: #86"), "number": 87},
        {86: saved},
        at(0),
        START + timedelta(seconds=14),
        content=first_content,
    )
    source.write_text("repaired content\n", encoding="utf-8")
    repaired_content = workflow.content_digest(tmp_path, 86)
    owner_continue(value, 15, "new finite correction approval")
    phase(value, "remediation", 17)
    owner_certify(value, 19, "final_review")
    add(value, "delivery", 25, evidence="correction published", pr=87)
    for item in value["events"][len(original) :]:
        if item["type"] in {"phase_start", "acceptance", "delivery"} and "content" in item["data"]:
            item["data"]["content"] = repaired_content
        workflow.append(tmp_path, 86, item, workflow.timestamp(item["at"]))
    saved = workflow.validate_all(tmp_path, START + timedelta(seconds=25))[86]
    assert saved["events"][: len(original)] == original
    assert workflow.check_pr(
        {**pr(body="Primary issue: #86"), "number": 87},
        {86: saved},
        at(0),
        START + timedelta(seconds=25),
        content=repaired_content,
    )
    assert len(state(saved, 25).delivery_history) == 2
    with pytest.raises(workflow.Invalid, match="different content"):
        workflow.check_pr(
            {**pr(body="Primary issue: #86"), "number": 87},
            {86: saved},
            at(0),
            START + timedelta(seconds=25),
            content=first_content,
        )


@pytest.mark.parametrize(
    "damage", ["event", "target", "other", "added", "removed", "temp", "source"]
)
def test_atomic_append_rechecks_actual_disk_inputs_before_replace(tmp_path, monkeypatch, damage):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    init = owner_ledger()["events"][0]
    workflow.append(tmp_path, 86, init, START)
    path = tmp_path / workflow.DIRECTORY / "issue-86.json"
    other = tmp_path / workflow.DIRECTORY / "issue-99.json"
    other.write_text(json.dumps(ledger(issue=99)), encoding="utf-8")
    event_file = tmp_path.parent / f"{tmp_path.name}-append-event.json"
    item = event(
        "design_ready",
        1,
        authority=AUTH,
        evidence="approved",
        capsule=workflow.capsule_ref(init["data"]["capsule"]),
    )
    event_file.write_text(json.dumps(item), encoding="utf-8")
    prior = path.read_bytes()
    prior_other = other.read_bytes()
    original_files = workflow.ledger_bytes
    original_digest = workflow.content_digest
    original_read = Path.read_bytes
    calls = {"ledgers": 0, "content": 0, "event": 0, "temp": 0}

    def changed_ledgers(root):
        calls["ledgers"] += 1
        if calls["ledgers"] == 2 and damage in {"target", "other", "added", "removed"}:
            if damage == "target":
                path.write_bytes(prior + b" ")
            elif damage == "other":
                other.write_bytes(prior_other + b" ")
            elif damage == "added":
                (path.parent / "issue-100.json").write_text("{}", encoding="utf-8")
            else:
                other.unlink()
        return original_files(root)

    def changed_digest(root, issue, ref=None):
        calls["content"] += 1
        if calls["content"] == 2 and damage == "source":
            (tmp_path / "source.txt").write_text("changed\n", encoding="utf-8")
        return original_digest(root, issue, ref)

    def changed_read(self):
        if self == event_file:
            calls["event"] += 1
            if calls["event"] == 2 and damage == "event":
                event_file.write_text(json.dumps({**item, "at": at(2)}), encoding="utf-8")
        if self.suffix == ".tmp":
            calls["temp"] += 1
            if calls["temp"] == 1 and damage == "temp":
                self.write_bytes(b"tampered candidate")
        return original_read(self)

    monkeypatch.setattr(workflow, "ledger_bytes", changed_ledgers)
    monkeypatch.setattr(workflow, "content_digest", changed_digest)
    monkeypatch.setattr(Path, "read_bytes", changed_read)
    with pytest.raises(workflow.Invalid, match="append input changed"):
        workflow.append(tmp_path, 86, item, START + timedelta(seconds=1), source_path=event_file)
    if damage != "target":
        assert path.read_bytes() == prior
    else:
        assert path.read_bytes() == prior + b" "
    assert not path.with_suffix(".lock").exists()
    assert not list(path.parent.glob("*.tmp"))
    if damage == "temp":
        assert calls["temp"] == 1


@pytest.mark.parametrize("consequential,remediation", [(False, False), (True, False), (True, True)])
def test_clean_paths_allow_delivery_without_extra_review_slot(consequential, remediation):
    value = clean(consequential, remediation)
    result = state(value)
    result.gate("delivery", START + timedelta(seconds=100))
    add(value, "delivery", 100, evidence="verified delivery")
    assert state(value).delivered
    with pytest.raises(workflow.Invalid, match="terminal"):
        state(value).gate("implementation", START + timedelta(seconds=100))


@pytest.mark.parametrize("phase_name", list(workflow.COUNTS))
def test_lifetime_slots_never_restart(phase_name):
    value = clean(True, True)
    if phase_name == "design_reset":
        phase(value, "design_reset", 20)
    add(
        value,
        "phase_start",
        22,
        phase=phase_name,
        role=next(iter(workflow.ROLES[phase_name])),
        session="replacement-agent",
    )
    with pytest.raises(workflow.Invalid, match="lifetime limit"):
        state(value)


def test_reset_invalidates_approval_but_preserves_review_counts():
    value = clean(True, True)
    phase(value, "design_reset", 20)
    phase(value, "challenge", 22, session="fresh-challenger")
    ready(value, 24)
    result = state(value)
    assert result.counts["initial_review"] == result.counts["remediation"] == 1
    with pytest.raises(workflow.Invalid, match="lifetime limit"):
        result.gate("remediation", START + timedelta(seconds=100))


@pytest.mark.parametrize("seconds,allowed", [(7199, True), (7200, False), (7201, False)])
def test_open_phase_charged_to_exact_budget_boundary(seconds, allowed):
    value = ledger()
    ready(value)
    add(
        value,
        "phase_start",
        0,
        phase="implementation",
        role="implementation_worker",
        session="worker",
    )
    result = state(value, seconds)
    assert result.elapsed(START + timedelta(seconds=seconds)) == seconds
    add(value, "pause", seconds, session="worker", outcome="interrupted", evidence="quota pause")
    add(value, "phase_resume", seconds, session="worker")
    if allowed:
        assert state(value, seconds).counts["implementation"] == 1
    else:
        with pytest.raises(workflow.Invalid, match="budget exhausted"):
            state(value, seconds)


def test_pause_resume_no_charge_for_recorded_offline_interval_no_slot_replenishment():
    value = ledger()
    ready(value)
    add(
        value,
        "phase_start",
        0,
        phase="implementation",
        role="implementation_worker",
        session="worker",
    )
    add(value, "pause", 50, session="worker", outcome="interrupted", evidence="recorded pause")
    add(value, "phase_resume", 5000, session="worker")
    add(value, "phase_end", 5050, session="worker", outcome="pass", evidence="completed")
    result = state(value, 5050)
    assert result.elapsed_seconds == 100
    assert result.counts["implementation"] == 1
    with pytest.raises(workflow.Invalid, match="lifetime limit"):
        result.gate("implementation", START + timedelta(seconds=5050))


@pytest.mark.parametrize("damage", ["overlap", "backwards", "future", "wrong-end", "wrong-resume"])
def test_bad_time_or_session_transition(damage):
    value = ledger()
    ready(value)
    add(
        value,
        "phase_start",
        5,
        phase="implementation",
        role="implementation_worker",
        session="worker",
    )
    if damage == "overlap":
        add(
            value,
            "phase_start",
            6,
            phase="verification",
            role="implementation_worker",
            session="other",
        )
    elif damage == "backwards":
        add(value, "pause", 4, session="worker", outcome="interrupted", evidence="pause")
    elif damage == "future":
        value["events"][-1]["at"] = at(101)
    elif damage == "wrong-end":
        add(value, "phase_end", 6, session="other", outcome="pass", evidence="wrong")
    else:
        add(value, "pause", 6, session="worker", outcome="interrupted", evidence="pause")
        add(value, "phase_resume", 7, session="replacement")
    with pytest.raises(workflow.Invalid):
        state(value)


@pytest.mark.parametrize(
    "damage", ["missing-challenge", "failed-challenge", "same-session", "wrong-role"]
)
def test_consequential_design_gate(damage):
    value = ledger(True)
    phase(value, "design", 1)
    if damage != "missing-challenge":
        phase(
            value,
            "challenge",
            3,
            "fail" if damage == "failed-challenge" else "pass",
            "design" if damage == "same-session" else "challenge",
        )
        if damage == "wrong-role":
            value["events"][-2]["data"]["role"] = "implementation_worker"
    ready(value, 5)
    with pytest.raises(workflow.Invalid):
        state(value)


def test_failed_final_review_stops_even_with_remaining_time():
    value = clean(True, True)
    final = next(
        e
        for e in value["events"]
        if e["type"] == "phase_end" and e["data"]["session"] == "final_review"
    )
    final["data"]["outcome"] = "fail"
    value["events"] = value["events"][: value["events"].index(final) + 1]
    result = state(value)
    for operation in ("delivery", "verification", "design_reset"):
        with pytest.raises(workflow.Invalid):
            result.gate(operation, START + timedelta(seconds=100))


@pytest.mark.parametrize("damage", ["blocker", "acceptance", "verification", "review"])
def test_delivery_cannot_hide_incomplete_or_unsafe_work(damage):
    value = clean(True)
    if damage == "blocker":
        add(
            value,
            "blocker",
            19,
            id="F",
            criterion="INV1",
            scenario="unsafe history",
            evidence="repro",
        )
    elif damage == "acceptance":
        value["events"][-1]["data"]["ids"] = ["different"]
    else:
        name = "verification" if damage == "verification" else "initial_review"
        end = next(
            e
            for i, e in enumerate(value["events"])
            if e["type"] == "phase_end" and value["events"][i - 1]["data"].get("phase") == name
        )
        end["data"]["outcome"] = "fail"
    with pytest.raises(workflow.Invalid):
        state(value).gate("delivery", START + timedelta(seconds=100))


@pytest.mark.parametrize("damage", ["bool", "extra", "schema", "authority", "frozen"])
def test_strict_initialization(damage):
    value = ledger()
    data = value["events"][0]["data"]
    if damage == "bool":
        data["issue"] = True
    elif damage == "extra":
        data["remaining"] = 120
    elif damage == "schema":
        value["schema"] = True
    elif damage == "authority":
        data["authority"] = {"kind": "coordinator", "name": "", "evidence": ""}
    else:
        data["acceptance"] = ["AC1", "AC1"]
    with pytest.raises(workflow.Invalid):
        state(value)


@pytest.mark.parametrize(
    "raw", ['{"schema":1,"schema":1,"events":[]}', '{"schema":NaN,"events":[]}']
)
def test_duplicate_keys_and_nonfinite_json_fail(raw):
    with pytest.raises(workflow.Invalid):
        workflow.load(raw)


def test_extension_requires_explicit_named_user_and_finite_deltas():
    value = clean()
    add(
        value,
        "extension",
        20,
        authority=USER,
        seconds=60,
        counts={**dict.fromkeys(workflow.COUNTS, 0), "implementation": 1},
        reason="finite retry",
    )
    result = state(value)
    assert result.budget_seconds == 7260 and result.limits["implementation"] == 2
    result.gate("implementation", START + timedelta(seconds=100))
    bad = copy.deepcopy(value)
    bad["events"][-1]["data"]["authority"] = AUTH
    with pytest.raises(workflow.Invalid, match="user authority"):
        state(bad)
    bad = copy.deepcopy(value)
    bad["events"][-1]["data"]["seconds"] = True
    with pytest.raises(workflow.Invalid):
        state(bad)


def test_future_adoption_cannot_fabricate_prior_work():
    value = ledger(True)
    first = value["events"][0]
    first["at"] = at(600)
    first["data"]["adoption"] = {
        "from": at(0),
        "phases": [
            {"phase": "design", "session": "architect", "outcome": "pass"},
            {"phase": "challenge", "session": "challenger", "outcome": "pass"},
        ],
        "evidence": "approved adoption",
    }
    ready(value, 600)
    with pytest.raises(workflow.Invalid, match="future adoption forbidden"):
        state(value, 600)


def test_split_successors_validate_prefix_inherit_counts_and_share_remainder():
    parent = clean()
    add(
        parent,
        "split",
        20,
        authority=USER,
        successor=74,
        seconds=3000,
        reason="user-approved split",
    )
    prefix = copy.deepcopy(parent)
    add(parent, "split", 21, authority=USER, successor=75, seconds=3000, reason="sibling")
    child = ledger(issue=74)
    child["events"][0]["at"] = at(22)
    child["events"][0]["data"]["predecessor"] = {"issue": 73, "digest": workflow.digest(prefix)}
    result = state(child, predecessors={73: parent})
    assert result.budget_seconds == 3000 and result.counts["implementation"] == 1
    ready(child, 23)
    with pytest.raises(workflow.Invalid, match="lifetime limit"):
        state(child, predecessors={73: parent}).gate(
            "implementation", START + timedelta(seconds=100)
        )
    with pytest.raises(workflow.Invalid, match="predecessor validation"):
        state(child)
    add(parent, "split", 24, authority=USER, successor=76, seconds=3000, reason="overallocate")
    with pytest.raises(workflow.Invalid, match="allocations exceed"):
        state(parent)


def test_atomic_append_rejects_invalid_without_mutation_and_respects_lock(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    init = ledger()["events"][0]
    path = tmp_path / workflow.DIRECTORY / "issue-73.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"schema": 1, "events": [init]}), encoding="utf-8")
    prior = path.read_bytes()
    with pytest.raises(workflow.Invalid):
        workflow.append(
            tmp_path,
            73,
            event(
                "phase_start",
                1,
                phase="implementation",
                session="worker",
                role="implementation_worker",
            ),
            START + timedelta(seconds=1),
        )
    assert path.read_bytes() == prior
    (tmp_path / workflow.DIRECTORY / ".repository.lock").touch()
    with pytest.raises(workflow.Invalid, match="writer"):
        workflow.append(
            tmp_path,
            73,
            event("design_ready", 1, authority=AUTH, evidence="ready"),
            START + timedelta(seconds=1),
        )


@pytest.mark.parametrize("policy", [None, "unknown-v9"])
def test_new_ticket_append_requires_explicit_owner_policy_before_write(tmp_path, policy):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    initial = copy.deepcopy(owner_ledger()["events"][0])
    if policy is None:
        del initial["data"]["policy"]
    else:
        initial["data"]["policy"] = policy
    path = tmp_path / workflow.DIRECTORY / "issue-86.json"
    with pytest.raises(
        workflow.Invalid, match="new ticket creation requires explicit owner-led-v1"
    ):
        workflow.append(tmp_path, 86, initial, START)
    assert not path.exists() and not path.with_suffix(".lock").exists()
    owner_initial = owner_ledger()["events"][0]
    result = workflow.append(tmp_path, 86, owner_initial, START)
    assert result.policy == "owner-led-v1"
    assert workflow.read_all(tmp_path)[86]["events"] == [owner_initial]


def test_existing_timed_ledger_can_append_without_policy_rewrite(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    value = ledger(issue=73)
    path = tmp_path / workflow.DIRECTORY / "issue-73.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    add(value, "design_ready", 1, authority=AUTH, evidence="historical legacy approval")
    result = workflow.append(tmp_path, 73, value["events"][-1], START + timedelta(seconds=1))
    assert result.policy == "timed-v1"
    assert workflow.read_all(tmp_path)[73]["events"] == value["events"]


def test_merge_base_new_policy_requirement_and_explicit_transition(tmp_path):
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True
    )
    timed = ledger(issue=86)
    with pytest.raises(
        workflow.Invalid, match="new ledger introduction requires current owner-led-v1"
    ):
        workflow.check_prefix(tmp_path, "main", {86: timed}, START)
    owner = owner_ledger()
    assert workflow.check_prefix(tmp_path, "main", {86: owner}, START) == {86}
    transitioned = copy.deepcopy(timed)
    add(
        transitioned,
        "policy_transition",
        1,
        policy="owner-led-v1",
        authority=USER,
        capsule=workflow.capsule_ref(current_capsule(transitioned)),
        reason="explicitly authorized owner-led policy",
    )
    with pytest.raises(workflow.Invalid, match="new ledger introduction"):
        workflow.check_prefix(tmp_path, "main", {86: transitioned}, START + timedelta(seconds=1))

    # The same policyless prefix remains valid when it already exists at merge base.
    path = tmp_path / workflow.DIRECTORY / "issue-86.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(timed), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "historical timed"], cwd=tmp_path, check=True, capture_output=True
    )
    ready(timed, 2)
    assert workflow.check_prefix(tmp_path, "main", {86: timed}, START + timedelta(seconds=2)) == {
        86
    }


def test_merge_base_prefix_rejects_edits_and_deletion(tmp_path):
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    path = tmp_path / workflow.DIRECTORY / "issue-73.json"
    path.parent.mkdir(parents=True)
    value = ledger()
    path.write_text(json.dumps(value), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True
    )
    ready(value)
    assert workflow.check_prefix(tmp_path, "main", {73: value}) == {73}
    changed = copy.deepcopy(value)
    changed["events"][0]["data"]["scope"] = ["changed"]
    for current in ({73: changed}, {}):
        with pytest.raises(workflow.Invalid, match="edited or deleted"):
            workflow.check_prefix(tmp_path, "main", current)


def pr(body="Primary issue: #73", created="2026-09-26T04:23:34Z"):
    return {
        "number": 80,
        "pull_request": {"body": body, "created_at": created},
        "repository": {"full_name": "beagle1903/agentic-etf-advisor"},
    }


def full_pr(body="Primary issue: #73", created="2026-09-26T04:23:34Z"):
    value = pr(body, created)
    value["pull_request"].update(
        head={"sha": "a" * 40, "ref": "feature", "repo": {"full_name": "owner/fork"}},
        base={
            "sha": "b" * 40,
            "ref": "main",
            "repo": {"full_name": value["repository"]["full_name"]},
        },
    )
    return value


def issue92_pr_identity_fixture() -> dict:
    root = Path(__file__).resolve().parents[1]
    path = root / workflow.PR_IDENTITY_ARCHIVE / "issue92-ledger-at-review-stop.json"
    value = workflow.strict_json(path.read_bytes())
    assert workflow.digest(value) == workflow.PR_IDENTITY_STOP
    grant = workflow.strict_json(
        (root / workflow.PR_IDENTITY_ARCHIVE / "finite-grant.json").read_bytes()
    )
    assert workflow.digest(grant) == workflow.PR_IDENTITY_GRANT
    value["events"].extend(
        [
            {
                "type": "issue92_pr_identity_repair",
                "at": "2026-10-09T18:03:52Z",
                "data": {
                    "version": "issue92-pr-identity-repair-v1",
                    "authority": grant["authority"],
                    "authority_anchor": grant["authority_anchor"],
                    "capsule": grant["capsule"],
                    "prefix_digest": workflow.PR_IDENTITY_STOP,
                    "grant_digest": workflow.PR_IDENTITY_GRANT,
                    "source_manifest_digest": workflow.PR_IDENTITY_MANIFEST,
                    "closeout_digest": workflow.PR_IDENTITY_CLOSEOUT,
                    "proposal_digest": workflow.PR_IDENTITY_PROPOSAL,
                    "reason": grant["reason"],
                },
            },
            {
                "type": "phase_start",
                "at": "2026-10-09T18:03:52Z",
                "data": {
                    "phase": "remediation",
                    "session": workflow.RECOVERY_OWNER,
                    "role": "implementation_worker",
                    "capsule": workflow.RECOVERY_CAPSULE_REF,
                },
            },
        ]
    )
    return value


def issue92_stage_fixture() -> dict:
    root = Path(__file__).resolve().parents[1]
    path = root / workflow.STAGE_FIXTURE_ARCHIVE / "stop-ledger.json"
    value = workflow.strict_json(path.read_bytes())
    assert workflow.digest(value) == workflow.STAGE_FIXTURE_STOP
    grant = workflow.strict_json(
        (root / workflow.STAGE_FIXTURE_ARCHIVE / "finite-grant.json").read_bytes()
    )
    assert workflow.digest(grant) == workflow.STAGE_FIXTURE_GRANT
    value["events"].extend(
        [
            {
                "type": "issue92_stage_fixture_repair",
                "at": "2026-10-09T19:16:26Z",
                "data": {
                    "version": "issue92-stage-fixture-repair-v1",
                    "authority": grant["authority"],
                    "authority_anchor": grant["authority_anchor"],
                    "capsule": grant["capsule"],
                    "prefix_digest": workflow.STAGE_FIXTURE_STOP,
                    "grant_digest": workflow.STAGE_FIXTURE_GRANT,
                    "source_manifest_digest": workflow.STAGE_FIXTURE_MANIFEST,
                    "closeout_digest": workflow.STAGE_FIXTURE_CLOSEOUT,
                    "proposal_digest": workflow.STAGE_FIXTURE_PROPOSAL,
                    "reason": grant["reason"],
                },
            },
            {
                "type": "phase_start",
                "at": "2026-10-09T19:16:26Z",
                "data": {
                    "phase": "remediation",
                    "session": workflow.RECOVERY_OWNER,
                    "role": "implementation_worker",
                    "capsule": grant["capsule"],
                },
            },
        ]
    )
    return value


def stage_fixture_event(value: dict, kind: str, at: str, data: dict) -> dict:
    value["events"].append({"type": kind, "at": at, "data": data})
    return value


def test_issue92_stage_fixture_saved_and_immutable_projection_oracle(tmp_path):
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    archived_18 = issue92_pr_identity_fixture()
    assert len(archived_18["events"]) == 18
    pending = issue92_stage_fixture()
    pending["events"].pop()
    for value in (
        archived_18,
        workflow.strict_json(
            (root / workflow.STAGE_FIXTURE_ARCHIVE / "stop-ledger.json").read_bytes()
        ),
        pending,
        issue92_stage_fixture(),
        workflow.read_all(root)[92],
    ):
        saved = tmp_path / "saved-ledger.json"
        saved.write_text(json.dumps(value), encoding="utf-8")
        read_back = workflow.strict_json(saved.read_bytes())
        assert_issue92_event_derived_state(read_back, workflow.replay(read_back, future, root=root))
    assert workflow.replay(pending, future, root=root).issue92_stage_fixture_stage == (
        "repair_pending"
    )
    assert workflow.replay(archived_18, future, root=root).issue92_pr_identity_stage == "repairing"
    stopped = workflow.replay(
        workflow.strict_json(
            (root / workflow.STAGE_FIXTURE_ARCHIVE / "stop-ledger.json").read_bytes()
        ),
        future,
        root=root,
    )
    assert stopped.issue92_pr_identity_stage == "failed"
    assert stopped.local_verification_starts == stopped.local_verification_limit == 3
    repairing = workflow.replay(issue92_stage_fixture(), future, root=root)
    assert repairing.issue92_stage_fixture_stage == "repairing"
    assert repairing.counts["remediation"] == repairing.limits["remediation"] == 7
    assert repairing.local_verification_limit == 4
    for value, field, wrong in (
        (archived_18, "issue92_pr_identity_stage", "verified"),
        (issue92_stage_fixture(), "issue92_stage_fixture_stage", "verified"),
        (issue92_stage_fixture(), "local_verification_limit", 3),
    ):
        state = workflow.replay(value, future, root=root)
        setattr(state, field, wrong)
        with pytest.raises(AssertionError):
            assert_issue92_event_derived_state(value, state)


def test_issue92_stage_fixture_progression_pause_failure_and_oracle_sensitivity(tmp_path):
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    value = issue92_stage_fixture()
    owner = workflow.RECOVERY_OWNER
    capsule = value["events"][23]["data"]["capsule"]

    def check():
        saved = tmp_path / "saved-projection.json"
        saved.write_text(json.dumps(value), encoding="utf-8")
        read_back = workflow.strict_json(saved.read_bytes())
        state = workflow.replay(read_back, future, root=root)
        assert_issue92_event_derived_state(read_back, state)
        return state

    assert check().issue92_stage_fixture_stage == "repairing"
    stage_fixture_event(
        value,
        "pause",
        "2026-10-09T19:16:27Z",
        {
            "session": owner,
            "outcome": "interrupted",
            "evidence": "fixture pause",
        },
    )
    paused = check()
    assert paused.suspended["phase"] == "remediation"
    assert paused.counts["remediation"] == 7
    stage_fixture_event(value, "phase_resume", "2026-10-09T19:16:28Z", {"session": owner})
    assert check().active["phase"] == "remediation"
    failed = copy.deepcopy(value)
    stage_fixture_event(
        failed,
        "phase_end",
        "2026-10-09T19:16:29Z",
        {
            "session": owner,
            "outcome": "fail",
            "evidence": "fixture failure",
        },
    )
    failed_state = workflow.replay(failed, future, root=root)
    assert_issue92_event_derived_state(failed, failed_state)
    with pytest.raises(workflow.Invalid):
        failed_state.gate("verification", future)
    failed_state.issue92_stage_fixture_stage = "verified"
    with pytest.raises(AssertionError):
        assert_issue92_event_derived_state(failed, failed_state)

    stage_fixture_event(
        value,
        "phase_end",
        "2026-10-09T19:16:29Z",
        {
            "session": owner,
            "outcome": "pass",
            "evidence": "fixture repair",
        },
    )
    repaired = check()
    with pytest.raises(workflow.Invalid, match="resolved seventh remediation"):
        repaired.gate("verification", future)
    stage_fixture_event(
        value,
        "resolve",
        "2026-10-09T19:16:30Z",
        {
            "id": workflow.STAGE_FIXTURE_BLOCKER,
            "evidence": "fixture resolution",
        },
    )
    assert check().issue92_stage_fixture_stage == "repaired"
    stage_fixture_event(
        value,
        "phase_start",
        "2026-10-09T19:16:31Z",
        {
            "phase": "verification",
            "session": owner,
            "role": "implementation_worker",
            "capsule": capsule,
            "content": CONTENT,
        },
    )
    verifying = check()
    assert verifying.local_verification_starts == verifying.local_verification_limit == 4
    verifying.issue92_stage_fixture_stage = "repairing"
    with pytest.raises(AssertionError):
        assert_issue92_event_derived_state(value, verifying)
    failure = copy.deepcopy(value)
    stage_fixture_event(
        failure,
        "phase_end",
        "2026-10-09T19:16:32Z",
        {
            "session": owner,
            "outcome": "fail",
            "evidence": "fixture verification failure",
        },
    )
    assert_issue92_event_derived_state(failure, workflow.replay(failure, future, root=root))
    stage_fixture_event(
        value,
        "phase_end",
        "2026-10-09T19:16:32Z",
        {
            "session": owner,
            "outcome": "pass",
            "evidence": "fixture verified",
        },
    )
    assert check().issue92_stage_fixture_stage == "verified"
    stage_fixture_event(
        value,
        "acceptance",
        "2026-10-09T19:16:33Z",
        {
            "ids": value["events"][0]["data"]["acceptance"],
            "evidence": "fixture acceptance",
            "capsule": capsule,
            "content": CONTENT,
        },
    )
    assert check().accepted
    for prior_participant in (
        owner,
        "/root/issue92_stage_fixture_design",
        "/root/issue92_stage_fixture_challenge",
    ):
        rejected = copy.deepcopy(value)
        stage_fixture_event(
            rejected,
            "phase_start",
            "2026-10-09T19:16:34Z",
            {
                "phase": "final_review",
                "session": prior_participant,
                "role": "code_reviewer",
                "capsule": capsule,
                "content": CONTENT,
            },
        )
        with pytest.raises(workflow.Invalid):
            workflow.replay(rejected, future, root=root)
    reviewer = "/root/stage_fixture_independent_final_review"
    stage_fixture_event(
        value,
        "phase_start",
        "2026-10-09T19:16:34Z",
        {
            "phase": "final_review",
            "session": reviewer,
            "role": "code_reviewer",
            "capsule": capsule,
            "content": CONTENT,
        },
    )
    reviewing = check()
    assert reviewing.counts["final_review"] == reviewing.limits["final_review"] == 5
    failed_review = copy.deepcopy(value)
    stage_fixture_event(
        failed_review,
        "phase_end",
        "2026-10-09T19:16:35Z",
        {
            "session": reviewer,
            "outcome": "fail",
            "evidence": "fixture review failure",
        },
    )
    assert_issue92_event_derived_state(
        failed_review, workflow.replay(failed_review, future, root=root)
    )
    stage_fixture_event(
        value,
        "phase_end",
        "2026-10-09T19:16:35Z",
        {
            "session": reviewer,
            "outcome": "pass",
            "evidence": "fixture clean review",
        },
    )
    assert check().issue92_stage_fixture_stage == "reviewed"
    stage_fixture_event(
        value,
        "publication_target",
        "2026-10-09T19:16:36Z",
        {
            "repo": workflow.REMAINDER_REPO,
            "pr": 93,
            "grant_digest": workflow.REMAINDER_GRANT,
            "evidence": "fixture target",
        },
    )
    assert check().issue92_stage_fixture_stage == "reviewed"
    stage_fixture_event(
        value,
        "delivery",
        "2026-10-09T19:16:37Z",
        {
            "repo": workflow.REMAINDER_REPO,
            "pr": 93,
            "content": CONTENT,
            "capsule": capsule,
            "evidence": "fixture delivery",
        },
    )
    delivered = check()
    assert delivered.issue92_stage_fixture_stage == "delivered"
    assert delivered.delivery_binding["content"] == CONTENT


@pytest.mark.parametrize("damage", ["prefix", "grant", "authority", "owner", "duplicate"])
def test_issue92_stage_fixture_exact_bootstrap_rejects_mutations(damage):
    root = Path(__file__).resolve().parents[1]
    value = issue92_stage_fixture()
    if damage == "prefix":
        value["events"][22]["data"]["evidence"] = "altered stop"
    elif damage == "grant":
        value["events"][23]["data"]["grant_digest"] = "0" * 64
    elif damage == "authority":
        value["events"][23]["data"]["authority"]["evidence"] = "reused authority"
    elif damage == "owner":
        value["events"][24]["data"]["session"] = "/root/replacement"
    else:
        value["events"].append(copy.deepcopy(value["events"][23]))
    with pytest.raises(workflow.Invalid):
        workflow.replay(value, datetime(2026, 11, 1, tzinfo=UTC), root=root)


@pytest.mark.parametrize("order", ["earlier", "later_evidence", "later_anchor"])
def test_issue92_stage_fixture_authority_is_single_use_in_both_orders(order):
    root = Path(__file__).resolve().parents[1]
    value = issue92_stage_fixture()
    grant = workflow.strict_json(
        (root / workflow.STAGE_FIXTURE_ARCHIVE / "finite-grant.json").read_bytes()
    )
    assert workflow.replay(value, datetime(2026, 11, 1, tzinfo=UTC), root=root)
    if order == "earlier":
        value["events"][6]["data"]["authority"]["evidence"] = grant["authority"]["evidence"].upper()
    else:
        extension = {
            "type": "extension",
            "at": "2026-10-09T19:16:27Z",
            "data": {
                "authority": {
                    "kind": "user",
                    "name": "renamed",
                    "evidence": (
                        grant["authority"]["evidence"].upper()
                        if order == "later_evidence"
                        else "fresh distinct evidence"
                    ),
                    "anchor": (
                        grant["authority_anchor"].upper()
                        if order == "later_anchor"
                        else "fresh distinct anchor"
                    ),
                },
                "seconds": 0,
                "counts": dict.fromkeys(workflow.COUNTS, 0),
                "reason": "attempted authority reuse",
            },
        }
        value["events"].append(extension)
    with pytest.raises(workflow.Invalid):
        workflow.lineage_audit({92: value}, root, datetime(2026, 11, 1, tzinfo=UTC))


@pytest.mark.parametrize("damage", ["source", "manifest", "grant", "extra"])
def test_issue92_stage_fixture_package_bytes_are_immutable(tmp_path, damage):
    root = Path(__file__).resolve().parents[1]
    for folder in (
        workflow.REMAINDER_ARCHIVE,
        workflow.RECOVERY_ARCHIVE,
        workflow.PR_IDENTITY_ARCHIVE,
        workflow.STAGE_FIXTURE_ARCHIVE,
    ):
        shutil.copytree(root / folder, tmp_path / folder)
    assert workflow.stage_fixture_sources(tmp_path)[0]["schema"] == (
        "issue92-stage-fixture-repair-grant-v1"
    )
    if damage == "extra":
        (tmp_path / workflow.STAGE_FIXTURE_ARCHIVE / "unexpected.txt").write_text(
            "unexpected", encoding="utf-8"
        )
        with pytest.raises(workflow.Invalid, match="membership"):
            workflow.stage_fixture_sources(tmp_path)
        return
    filename = {
        "source": "verification/pytest-full.log",
        "manifest": "source-manifest.json",
        "grant": "finite-grant.json",
    }[damage]
    path = tmp_path / workflow.STAGE_FIXTURE_ARCHIVE / filename
    if damage == "grant":
        changed = workflow.strict_json(path.read_bytes())
        changed["seconds"] = 1
        path.write_text(json.dumps(changed), encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(workflow.Invalid):
        workflow.stage_fixture_sources(tmp_path)


@pytest.mark.parametrize(
    "damage",
    [
        "archive",
        "manifest",
        "grant",
        "event",
        "content",
        "member",
        "ledger_member",
        "ledger_bytes",
        "temp",
    ],
)
def test_issue92_stage_fixture_append_rechecks_actual_inputs(tmp_path, monkeypatch, damage):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for folder in (
        workflow.REMAINDER_ARCHIVE,
        workflow.RECOVERY_ARCHIVE,
        workflow.PR_IDENTITY_ARCHIVE,
        workflow.STAGE_FIXTURE_ARCHIVE,
    ):
        shutil.copytree(root / folder, tmp_path / folder)
    source = tmp_path / "source.txt"
    source.write_bytes(b"original\n")
    ticket = tmp_path / workflow.DIRECTORY / "issue-92.json"
    ticket.parent.mkdir(parents=True)
    value = issue92_stage_fixture()
    ticket.write_text(json.dumps({"schema": 1, "events": value["events"][:23]}), encoding="utf-8")
    baseline = ticket.read_bytes()
    item = value["events"][23]
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(item), encoding="utf-8")
    future = datetime(2026, 11, 1, tzinfo=UTC)
    assert (
        workflow.append(
            tmp_path,
            92,
            item,
            future,
            source_path=event_path,
        ).issue92_stage_fixture_stage
        == "repair_pending"
    )
    ticket.write_bytes(baseline)
    if damage == "temp":
        original_read = Path.read_bytes
        touched = False

        def changed_temp(path):
            nonlocal touched
            if path.suffix == ".tmp" and not touched:
                touched = True
                path.write_bytes(original_read(path) + b" ")
            return original_read(path)

        monkeypatch.setattr(Path, "read_bytes", changed_temp)
    else:
        original_working = workflow.working_bytes
        calls = 0

        def changed_input(root_path, issue):
            nonlocal calls
            calls += 1
            if calls == 2:
                if damage in {"archive", "manifest", "grant"}:
                    name = {
                        "archive": "verification/pytest-full.log",
                        "manifest": "source-manifest.json",
                        "grant": "finite-grant.json",
                    }[damage]
                    path = tmp_path / workflow.STAGE_FIXTURE_ARCHIVE / name
                    path.write_bytes(path.read_bytes() + b" ")
                elif damage == "event":
                    event_path.write_bytes(event_path.read_bytes() + b" ")
                elif damage == "content":
                    source.write_bytes(b"changed\n")
                elif damage == "member":
                    (tmp_path / "new-member.txt").write_text("new", encoding="utf-8")
                elif damage == "ledger_bytes":
                    ticket.write_bytes(ticket.read_bytes() + b" ")
                else:
                    (tmp_path / workflow.DIRECTORY / "issue-91.json").write_text(
                        "{}", encoding="utf-8"
                    )
            return original_working(root_path, issue)

        monkeypatch.setattr(workflow, "working_bytes", changed_input)
    with pytest.raises(workflow.Invalid, match="append input changed"):
        workflow.append(tmp_path, 92, item, future, source_path=event_path)
    assert ticket.read_bytes() == (baseline + b" " if damage == "ledger_bytes" else baseline)


def issue92_pr_identity_delivered_fixture() -> dict:
    value = issue92_pr_identity_fixture()
    owner = workflow.RECOVERY_OWNER
    capsule = workflow.RECOVERY_CAPSULE_REF
    value["events"].extend(
        [
            {
                "type": "phase_end",
                "at": "2026-10-09T18:03:53Z",
                "data": {"session": owner, "outcome": "pass", "evidence": "fixture"},
            },
            {
                "type": "resolve",
                "at": "2026-10-09T18:03:54Z",
                "data": {"id": workflow.PR_IDENTITY_BLOCKER, "evidence": "fixture"},
            },
            {
                "type": "phase_start",
                "at": "2026-10-09T18:03:55Z",
                "data": {
                    "phase": "verification",
                    "session": owner,
                    "role": "implementation_worker",
                    "capsule": capsule,
                    "content": CONTENT,
                },
            },
            {
                "type": "phase_end",
                "at": "2026-10-09T18:03:56Z",
                "data": {"session": owner, "outcome": "pass", "evidence": "fixture"},
            },
            {
                "type": "acceptance",
                "at": "2026-10-09T18:03:57Z",
                "data": {
                    "ids": value["events"][0]["data"]["acceptance"],
                    "evidence": "fixture",
                    "capsule": capsule,
                    "content": CONTENT,
                },
            },
            {
                "type": "phase_start",
                "at": "2026-10-09T18:03:58Z",
                "data": {
                    "phase": "final_review",
                    "session": "/root/fresh_independent_final_review",
                    "role": "code_reviewer",
                    "capsule": capsule,
                    "content": CONTENT,
                },
            },
            {
                "type": "phase_end",
                "at": "2026-10-09T18:03:59Z",
                "data": {
                    "session": "/root/fresh_independent_final_review",
                    "outcome": "pass",
                    "evidence": "fixture",
                },
            },
            {
                "type": "publication_target",
                "at": "2026-10-09T18:04:00Z",
                "data": {
                    "repo": workflow.REMAINDER_REPO,
                    "pr": 93,
                    "grant_digest": workflow.REMAINDER_GRANT,
                    "evidence": "fixture",
                },
            },
            {
                "type": "delivery",
                "at": "2026-10-09T18:04:01Z",
                "data": {
                    "repo": workflow.REMAINDER_REPO,
                    "pr": 93,
                    "content": CONTENT,
                    "capsule": capsule,
                    "evidence": "fixture",
                },
            },
        ]
    )
    return value


def test_issue92_actual_saved_pr_identity_repair_and_archived_stop():
    root = Path(__file__).resolve().parents[1]
    grant, closeout, manifest, stop, supplemental = workflow.pr_identity_sources(root)
    current = workflow.read_all(root)[92]
    assert current["events"][:16] == stop["events"]
    assert current["events"][16:18] == issue92_pr_identity_fixture()["events"][16:18]
    assert grant["closeout_digest"] == workflow.digest(closeout)
    assert grant["source_manifest_digest"] == workflow.digest(manifest)
    assert supplemental["events"][-1]["outcome"] == "approved"
    old = workflow.replay(stop, datetime.now(UTC), root=root)
    assert old.issue92_recovery_stage == "failed"
    assert old.issue92_pr_identity_stage == "absent"
    with pytest.raises(workflow.Invalid):
        old.gate("remediation", datetime.now(UTC))
    active = workflow.replay(current, datetime.now(UTC), root=root)
    assert_issue92_event_derived_state(current, active)
    assert active.issue92_recovery_stage == "failed"
    assert active.issue92_recovery_failure == "initial_review"
    assert active.counts["implementation"] == 5
    assert active.counts["initial_review"] == 4
    assert active.counts["remediation"] >= 6
    assert active.counts["design_reset"] == 4
    assert active.local_verification_starts >= 2


@pytest.mark.parametrize("field", ["ref", "repo", "both"])
def test_current_pr_rejects_live_head_identity_with_same_sha(field):
    request = full_pr()
    live = {"number": request["number"], **copy.deepcopy(request["pull_request"])}
    if field in {"ref", "both"}:
        live["head"]["ref"] = "other-branch"
    if field in {"repo", "both"}:
        live["head"]["repo"]["full_name"] = "other/fork"
    with pytest.raises(workflow.Invalid, match="stale head"):
        workflow.current_pr(request, live)


def test_current_pr_returns_live_fields_and_preserves_inputs():
    request = full_pr()
    live = {"number": 80, **copy.deepcopy(request["pull_request"]), "extra": "GitHub field"}
    live["body"] = "Primary issue: #74"
    original_request, original_live = copy.deepcopy(request), copy.deepcopy(live)
    result = workflow.current_pr(request, live)
    assert result["pull_request"]["head"] == live["head"]
    assert result["pull_request"]["base"] == live["base"]
    assert result["pull_request"]["body"] == "Primary issue: #74"
    assert result["pull_request"]["extra"] == "GitHub field"
    assert request == original_request
    assert live == original_live


@pytest.mark.parametrize(
    ("side", "field", "bad"),
    [
        ("head", "sha", "a"),
        ("head", "sha", "A" * 40),
        ("head", "sha", None),
        ("head", "ref", "bad branch"),
        ("head", "ref", None),
        ("head", "repo", None),
        ("base", "sha", "b"),
        ("base", "ref", ""),
        ("base", "repo", {}),
    ],
)
def test_current_pr_rejects_malformed_live_identity(side, field, bad):
    request = full_pr()
    live = {"number": 80, **copy.deepcopy(request["pull_request"])}
    live[side][field] = bad
    with pytest.raises(workflow.Invalid):
        workflow.current_pr(request, live)


@pytest.mark.parametrize("field", ["number", "created_at", "body"])
def test_current_pr_rejects_bad_live_pr_fields(field):
    request = full_pr()
    live = {"number": 80, **copy.deepcopy(request["pull_request"])}
    live[field] = {"number": True, "created_at": "yesterday", "body": 5}[field]
    with pytest.raises(workflow.Invalid):
        workflow.current_pr(request, live)


@pytest.mark.parametrize(
    ("location", "field", "bad"),
    [
        ("event", "number", True),
        ("event", "number", None),
        ("repository", "full_name", "owner /repo"),
        ("repository", "full_name", "one-component"),
        ("queued", "created_at", None),
        ("queued", "number", 81),
        ("live", "number", False),
        ("live", "head", None),
        ("live", "base", []),
        ("live_head_repo", "full_name", "bad/name/extra"),
        ("live_base_repo", "full_name", None),
    ],
)
def test_current_pr_rejects_malformed_queued_and_live_envelopes(location, field, bad):
    request = full_pr()
    live = {"number": 80, **copy.deepcopy(request["pull_request"])}
    target = {
        "event": request,
        "repository": request["repository"],
        "queued": request["pull_request"],
        "live": live,
        "live_head_repo": live["head"]["repo"],
        "live_base_repo": live["base"]["repo"],
    }[location]
    target[field] = bad
    with pytest.raises(workflow.Invalid):
        workflow.current_pr(request, live)


def test_issue92_pr_identity_stage_and_stale_certification_gates():
    root = Path(__file__).resolve().parents[1]
    value = issue92_pr_identity_fixture()
    future = datetime(2026, 11, 1, tzinfo=UTC)
    state = workflow.replay(value, future, root=root)
    assert state.verified_content is None
    assert state.acceptance_content is None
    assert state.issue92_recovery_stage == "failed"
    for phase in (
        "implementation",
        "initial_review",
        "final_review",
        "verification",
        "remediation",
    ):
        with pytest.raises(workflow.Invalid):
            state.gate(phase, future)
    value["events"].append(
        {
            "type": "phase_end",
            "at": "2026-10-09T18:03:53Z",
            "data": {"session": workflow.RECOVERY_OWNER, "outcome": "pass", "evidence": "fixture"},
        }
    )
    repaired = workflow.replay(value, future, root=root)
    assert repaired.issue92_pr_identity_stage == "repaired"
    with pytest.raises(workflow.Invalid, match="resolved sixth remediation"):
        repaired.gate("verification", future)
    with pytest.raises(workflow.Invalid):
        bad = copy.deepcopy(value)
        bad["events"].append(
            {
                "type": "resolve",
                "at": "2026-10-09T18:03:54Z",
                "data": {"id": workflow.RECOVERY_BLOCKER, "evidence": "wrong blocker"},
            }
        )
        workflow.replay(bad, future, root=root)
    value["events"].append(
        {
            "type": "resolve",
            "at": "2026-10-09T18:03:54Z",
            "data": {"id": workflow.PR_IDENTITY_BLOCKER, "evidence": "fixture"},
        }
    )
    assert workflow.replay(value, future, root=root).issue92_recovery_stage == "failed"
    assert workflow.replay(value, future, root=root).issue92_pr_identity_stage == "repaired"


def test_issue92_pr_identity_exact_prefix_and_grant_negatives():
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    source = issue92_pr_identity_fixture()
    for mutate in (
        lambda v: v["events"][15]["data"].update(evidence="changed"),
        lambda v: v["events"][16]["data"].update(grant_digest="0" * 64),
        lambda v: v["events"][16]["data"].update(authority_anchor="reused"),
        lambda v: v["events"][16]["data"].update(extra=True),
        lambda v: v["events"][17]["data"].update(session="/root/replacement"),
    ):
        value = copy.deepcopy(source)
        mutate(value)
        with pytest.raises(workflow.Invalid):
            workflow.replay(value, future, root=root)
    duplicate = copy.deepcopy(source)
    duplicate["events"].append(copy.deepcopy(duplicate["events"][16]))
    with pytest.raises(workflow.Invalid):
        workflow.replay(duplicate, future, root=root)


def test_issue92_pr_identity_fresh_certification_final_review_and_failure_stops():
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    value = issue92_pr_identity_fixture()
    failed = copy.deepcopy(value)
    failed["events"].append(
        {
            "type": "phase_end",
            "at": "2026-10-09T18:03:53Z",
            "data": {"session": workflow.RECOVERY_OWNER, "outcome": "fail", "evidence": "fixture"},
        }
    )
    failed_state = workflow.replay(failed, future, root=root)
    assert failed_state.issue92_pr_identity_failure == {"phase": "remediation", "event_index": 19}
    for phase in ("remediation", "verification", "final_review"):
        with pytest.raises(workflow.Invalid):
            failed_state.gate(phase, future)

    value["events"].extend(
        [
            {
                "type": "phase_end",
                "at": "2026-10-09T18:03:53Z",
                "data": {
                    "session": workflow.RECOVERY_OWNER,
                    "outcome": "pass",
                    "evidence": "fixture",
                },
            },
            {
                "type": "resolve",
                "at": "2026-10-09T18:03:54Z",
                "data": {"id": workflow.PR_IDENTITY_BLOCKER, "evidence": "fixture"},
            },
            {
                "type": "phase_start",
                "at": "2026-10-09T18:03:55Z",
                "data": {
                    "phase": "verification",
                    "session": workflow.RECOVERY_OWNER,
                    "role": "implementation_worker",
                    "capsule": workflow.RECOVERY_CAPSULE_REF,
                    "content": CONTENT,
                },
            },
        ]
    )
    verifying = workflow.replay(value, future, root=root)
    assert verifying.issue92_pr_identity_stage == "verifying"
    assert verifying.local_verification_starts == 3
    value["events"].append(
        {
            "type": "phase_end",
            "at": "2026-10-09T18:03:56Z",
            "data": {"session": workflow.RECOVERY_OWNER, "outcome": "pass", "evidence": "fixture"},
        }
    )
    verified = workflow.replay(value, future, root=root)
    assert verified.issue92_pr_identity_stage == "verified"
    assert verified.issue92_recovery_stage == "failed"
    with pytest.raises(workflow.Invalid, match="matching verification and acceptance"):
        verified.gate("final_review", future)
    value["events"].append(
        {
            "type": "acceptance",
            "at": "2026-10-09T18:03:57Z",
            "data": {
                "ids": verified.acceptance,
                "evidence": "fixture",
                "capsule": workflow.RECOVERY_CAPSULE_REF,
                "content": CONTENT,
            },
        }
    )
    accepted = workflow.replay(value, future, root=root)
    accepted.gate("final_review", future)
    value["events"].append(
        {
            "type": "phase_start",
            "at": "2026-10-09T18:03:58Z",
            "data": {
                "phase": "final_review",
                "session": "/root/fresh_independent_final_review",
                "role": "code_reviewer",
                "capsule": workflow.RECOVERY_CAPSULE_REF,
                "content": CONTENT,
            },
        }
    )
    reviewing = workflow.replay(value, future, root=root)
    assert reviewing.issue92_pr_identity_stage == "reviewing"
    for outcome in ("fail", "pass"):
        completed = copy.deepcopy(value)
        completed["events"].append(
            {
                "type": "phase_end",
                "at": "2026-10-09T18:03:59Z",
                "data": {
                    "session": "/root/fresh_independent_final_review",
                    "outcome": outcome,
                    "evidence": "fixture",
                },
            }
        )
        result = workflow.replay(completed, future, root=root)
        assert result.issue92_recovery_stage == "failed"
        assert result.issue92_pr_identity_stage == ("failed" if outcome == "fail" else "reviewed")
        if outcome == "fail":
            with pytest.raises(workflow.Invalid):
                result.gate("delivery", future)
        else:
            assert result.review_content == result.verified_content == CONTENT
            assert result.counts["final_review"] == 5


@pytest.mark.parametrize("phase", ["verification", "final_review"])
def test_issue92_pr_identity_later_completed_failures_stop(phase):
    root = Path(__file__).resolve().parents[1]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    value = issue92_pr_identity_delivered_fixture()
    start = next(
        index
        for index, item in enumerate(value["events"])
        if item["type"] == "phase_start" and item["data"]["phase"] == phase and index >= 18
    )
    end = start + 1
    value["events"] = value["events"][: end + 1]
    value["events"][end]["data"]["outcome"] = "fail"
    state = workflow.replay(value, future, root=root)
    assert state.issue92_pr_identity_stage == "failed"
    assert state.issue92_pr_identity_failure == {"phase": phase, "event_index": end + 1}
    assert state.issue92_recovery_stage == "failed"
    for later in ("remediation", "verification", "initial_review", "final_review", "delivery"):
        with pytest.raises(workflow.Invalid):
            state.gate(later, future)


@pytest.mark.parametrize(
    "session",
    [
        workflow.RECOVERY_OWNER,
        "/root/issue92_pr_identity_design",
        "/root/issue92_pr_identity_challenge",
        "/ROOT/ISSUE92_PR_IDENTITY_CHALLENGE",
        "/root/issue92_recovered_initial_review",
    ],
)
def test_issue92_pr_identity_final_review_excludes_prior_participants(session):
    root = Path(__file__).resolve().parents[1]
    value = issue92_pr_identity_delivered_fixture()
    start = next(
        index
        for index, item in enumerate(value["events"])
        if item["type"] == "phase_start" and item["data"]["phase"] == "final_review" and index >= 18
    )
    value["events"] = value["events"][: start + 1]
    value["events"][start]["data"]["session"] = session
    with pytest.raises(workflow.Invalid, match="independent read-only session"):
        workflow.replay(value, datetime(2026, 11, 1, tzinfo=UTC), root=root)


def test_current_pr_matching_fork_is_generic_but_issue92_rejects_it():
    request = full_pr("Primary issue: #92", "2026-10-09T18:03:53Z")
    request["number"] = 93
    request["pull_request"]["head"]["ref"] = "codex/issue-92-issue84-remainder"
    live = {"number": 93, **copy.deepcopy(request["pull_request"])}
    checked = workflow.current_pr(request, live)
    assert checked["pull_request"]["head"]["repo"]["full_name"] == "owner/fork"
    with pytest.raises(workflow.Invalid, match="publication PR identity"):
        workflow.check_pr(
            checked,
            {92: issue92_pr_identity_fixture()},
            "2026-10-09T18:03:53Z",
            datetime(2026, 11, 1, tzinfo=UTC),
            {92},
            CONTENT,
            root=Path(__file__).resolve().parents[1],
        )


@pytest.mark.parametrize(
    "damage",
    ["archive", "manifest", "grant", "event", "member", "content", "ledger_member"],
)
def test_issue92_pr_identity_append_rechecks_complete_inputs(tmp_path, monkeypatch, damage):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for folder in (
        workflow.REMAINDER_ARCHIVE,
        workflow.RECOVERY_ARCHIVE,
        workflow.PR_IDENTITY_ARCHIVE,
    ):
        shutil.copytree(root / folder, tmp_path / folder)
    source = tmp_path / "source.txt"
    source.write_bytes(b"original\n")
    ticket = tmp_path / workflow.DIRECTORY / "issue-92.json"
    ticket.parent.mkdir(parents=True)
    value = issue92_pr_identity_fixture()
    ticket.write_text(json.dumps({"schema": 1, "events": value["events"][:16]}), encoding="utf-8")
    original = ticket.read_bytes()
    item = value["events"][16]
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(item), encoding="utf-8")
    future = datetime(2026, 11, 1, tzinfo=UTC)
    assert (
        workflow.append(
            tmp_path, 92, item, future, source_path=event_path
        ).issue92_pr_identity_stage
        == "repair_pending"
    )
    ticket.write_bytes(original)
    real_working = workflow.working_bytes
    calls = 0

    def mutate(root_path, issue):
        nonlocal calls
        calls += 1
        if calls == 2:
            if damage in {"archive", "manifest", "grant"}:
                name = {
                    "archive": "independent-review-report.md",
                    "manifest": "source-manifest.json",
                    "grant": "finite-grant.json",
                }[damage]
                path = tmp_path / workflow.PR_IDENTITY_ARCHIVE / name
                path.write_bytes(path.read_bytes() + b" ")
            elif damage == "event":
                event_path.write_bytes(event_path.read_bytes() + b" ")
            elif damage == "member":
                (tmp_path / "new-member.txt").write_text("new", encoding="utf-8")
            elif damage == "content":
                source.write_bytes(b"changed\n")
            else:
                other = tmp_path / workflow.DIRECTORY / "issue-91.json"
                other.write_text("{}", encoding="utf-8")
        return real_working(root_path, issue)

    monkeypatch.setattr(workflow, "working_bytes", mutate)
    with pytest.raises(workflow.Invalid, match="append input changed"):
        workflow.append(tmp_path, 92, item, future, source_path=event_path)
    assert calls >= 2
    assert ticket.read_bytes() == original


@pytest.mark.parametrize("scenario", ["pass", "stale_ref", "matching_fork", "wrong_branch"])
def test_ci_main_uses_validated_live_head_base_and_issue92_identity(
    monkeypatch, tmp_path, capsys, scenario
):
    import io

    value = issue92_pr_identity_delivered_fixture()
    root = Path(__file__).resolve().parents[1]
    assert workflow.replay(value, datetime(2026, 11, 1, tzinfo=UTC), root=root).delivered
    queued = full_pr("Primary issue: #92", "2026-10-09T18:04:02Z")
    queued["number"] = 93
    queued["repository"]["full_name"] = workflow.REMAINDER_REPO
    queued["pull_request"]["head"]["ref"] = "codex/issue-92-issue84-remainder"
    queued["pull_request"]["head"]["repo"]["full_name"] = workflow.REMAINDER_REPO
    if scenario == "matching_fork":
        queued["pull_request"]["head"]["repo"]["full_name"] = "other/fork"
    if scenario == "wrong_branch":
        queued["pull_request"]["head"]["ref"] = "other-branch"
    live = {"number": 93, **copy.deepcopy(queued["pull_request"])}
    if scenario == "stale_ref":
        live["head"]["ref"] = "other-branch"
    path = tmp_path / "event.json"
    path.write_text(json.dumps(queued), encoding="utf-8")
    responses = [
        live,
        {"number": 92, "created_at": "2026-10-08T09:07:36Z"},
    ]
    seen_bases, seen_heads = [], []
    monkeypatch.setattr(workflow, "validate_all", lambda *_: {92: value})
    monkeypatch.setattr(
        workflow.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: io.StringIO(json.dumps(responses.pop(0))),
    )
    monkeypatch.setattr(
        workflow,
        "check_prefix",
        lambda _root, base, _ledgers, _now: seen_bases.append(base) or {92},
    )
    monkeypatch.setattr(
        workflow,
        "content_digest",
        lambda _root, _issue, head=None: seen_heads.append(head) or CONTENT,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "workflow",
            "ci",
            "--root",
            str(root),
            "--event",
            str(path),
            "--base",
            queued["pull_request"]["base"]["sha"],
            "--now",
            "2026-11-01T00:00:00Z",
        ],
    )
    if scenario == "pass":
        workflow.main()
        assert "delivery gate passed" in capsys.readouterr().out
        assert seen_bases == [live["base"]["sha"]]
        assert seen_heads == [live["head"]["sha"]]
    else:
        with pytest.raises(SystemExit) as failure:
            workflow.main()
        assert failure.value.code == 1
        if scenario == "stale_ref":
            assert seen_bases == []
        else:
            assert seen_bases == [live["base"]["sha"]]


def test_issue92_pr_identity_append_rejects_candidate_temp_race(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for folder in (
        workflow.REMAINDER_ARCHIVE,
        workflow.RECOVERY_ARCHIVE,
        workflow.PR_IDENTITY_ARCHIVE,
    ):
        shutil.copytree(root / folder, tmp_path / folder)
    ticket = tmp_path / workflow.DIRECTORY / "issue-92.json"
    ticket.parent.mkdir(parents=True)
    value = issue92_pr_identity_fixture()
    ticket.write_text(json.dumps({"schema": 1, "events": value["events"][:16]}), encoding="utf-8")
    original = ticket.read_bytes()
    item = value["events"][16]
    future = datetime(2026, 11, 1, tzinfo=UTC)
    assert workflow.append(tmp_path, 92, item, future).issue92_pr_identity_stage == "repair_pending"
    ticket.write_bytes(original)
    original_read = Path.read_bytes
    mutated = False

    def changed_temp(path):
        nonlocal mutated
        if path.suffix == ".tmp" and not mutated:
            mutated = True
            path.write_bytes(original_read(path) + b" ")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", changed_temp)
    with pytest.raises(workflow.Invalid, match="append input changed"):
        workflow.append(tmp_path, 92, item, future)
    assert mutated
    assert ticket.read_bytes() == original


@pytest.mark.parametrize(
    "damage",
    ["boolean_count", "wrong_owner", "extra_publication", "reused_authority", "seconds"],
)
def test_issue92_pr_identity_rejects_rebound_bad_grant(tmp_path, monkeypatch, damage):
    root = Path(__file__).resolve().parents[1]
    for folder in (
        workflow.REMAINDER_ARCHIVE,
        workflow.RECOVERY_ARCHIVE,
        workflow.PR_IDENTITY_ARCHIVE,
    ):
        shutil.copytree(root / folder, tmp_path / folder)
    path = tmp_path / workflow.PR_IDENTITY_ARCHIVE / "finite-grant.json"
    grant = workflow.strict_json(path.read_bytes())
    if damage == "boolean_count":
        grant["count_deltas"]["remediation"] = True
    elif damage == "wrong_owner":
        grant["owner"]["session"] = "/root/replacement"
    elif damage == "extra_publication":
        grant["publication"]["additional_count"] = 1
    elif damage == "reused_authority":
        grant["authority"]["evidence"] = workflow.pr_identity_sources(root)[4]["authority"][
            "evidence"
        ]
    else:
        grant["seconds"] = True
    path.write_text(json.dumps(grant), encoding="utf-8")
    monkeypatch.setattr(workflow, "PR_IDENTITY_GRANT", workflow.digest(grant))
    with pytest.raises(workflow.Invalid):
        workflow.pr_identity_sources(tmp_path)


@pytest.mark.parametrize("order", ["earlier", "later_evidence", "later_anchor"])
def test_issue92_pr_identity_authority_reuse_rejected_in_lineage(order):
    root = Path(__file__).resolve().parents[1]
    value = issue92_pr_identity_fixture()
    grant = workflow.strict_json(
        (root / workflow.PR_IDENTITY_ARCHIVE / "finite-grant.json").read_bytes()
    )
    if order == "earlier":
        value["events"][6]["data"]["authority"]["evidence"] = grant["authority"]["evidence"].upper()
    else:
        value["events"].append(
            {
                "type": "extension",
                "at": "2026-10-09T18:03:53Z",
                "data": {
                    "authority": {
                        "kind": "user",
                        "name": "renamed",
                        "evidence": (
                            grant["authority"]["evidence"].upper()
                            if order == "later_evidence"
                            else "distinct evidence"
                        ),
                        "anchor": (
                            grant["authority_anchor"].upper()
                            if order == "later_anchor"
                            else "distinct anchor"
                        ),
                    },
                    "seconds": 0,
                    "counts": dict.fromkeys(workflow.COUNTS, 0),
                    "reason": "attempted reuse",
                },
            }
        )
    with pytest.raises(workflow.Invalid, match="reused"):
        workflow.lineage_audit({92: value}, root, datetime(2026, 11, 1, tzinfo=UTC))


def test_issue92_pr_identity_interrupted_reservation_keeps_one_count():
    root = Path(__file__).resolve().parents[1]
    value = issue92_pr_identity_fixture()
    value["events"].extend(
        [
            {
                "type": "pause",
                "at": "2026-10-09T18:03:53Z",
                "data": {
                    "session": workflow.RECOVERY_OWNER,
                    "outcome": "interrupted",
                    "evidence": "fixture pause",
                },
            },
            {
                "type": "phase_resume",
                "at": "2026-10-20T18:03:53Z",
                "data": {"session": workflow.RECOVERY_OWNER},
            },
        ]
    )
    state = workflow.replay(value, datetime(2026, 11, 1, tzinfo=UTC), root=root)
    assert state.issue92_pr_identity_stage == "repairing"
    assert state.active["phase"] == "remediation"
    assert state.counts["remediation"] == 6
    assert state.local_verification_starts == 2


@pytest.mark.parametrize(
    "body", ["", "Primary issue: #74", "Primary issue: #73\nPrimary issue: #74"]
)
def test_pr_binding_rejects_missing_wrong_or_ambiguous_primary(body):
    with pytest.raises(workflow.Invalid):
        workflow.check_pr(
            pr(body), {73: clean(True)}, at(0), START + timedelta(seconds=100), {73}, CONTENT
        )


def test_pr_binding_and_precise_historical_exemption():
    delivered = clean(True)
    add(delivered, "delivery", 20, evidence="recorded original delivery")
    assert "passed" in workflow.check_pr(
        pr(), {73: delivered}, at(0), START + timedelta(seconds=100), {73}, CONTENT
    )
    old = "2026-09-25T00:00:00Z"
    assert "Historical" in workflow.check_pr(pr("", old), {}, old, START)
    assert "Historical" in workflow.check_pr(pr("Primary issue: #70"), {}, old, START)
    with pytest.raises(workflow.Invalid):
        workflow.check_pr(pr("Primary issue: #70"), {73: clean()}, old, START, {73})


def test_cli_runs_from_other_cwd(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    path = tmp_path / workflow.DIRECTORY / "issue-73.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(clean(True)), encoding="utf-8")
    script = Path(workflow.__file__).resolve()
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "check",
            "--root",
            str(tmp_path),
            "--issue",
            "73",
            "--phase",
            "delivery",
            "--now",
            at(100),
        ],
        cwd=tmp_path.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "no runtime kill switch" in result.stdout


def test_interphase_time_charged_until_explicit_coordination_pause():
    value = clean()
    add(value, "coordination_pause", 50, authority=AUTH, evidence="explicit offline pause")
    result = state(value, 5000)
    assert result.elapsed_seconds == 50
    with pytest.raises(workflow.Invalid, match="resume"):
        result.gate("delivery", START + timedelta(seconds=5000))
    add(value, "coordination_resume", 5000, authority=AUTH, evidence="back online")
    assert state(value, 5050).elapsed(START + timedelta(seconds=5050)) == 100


def test_new_blocker_cannot_use_stale_successful_remediation():
    value = clean(True, True)
    add(value, "blocker", 20, id="F2", criterion="AC1", scenario="new defect", evidence="repro")
    add(value, "resolve", 21, id="F2", evidence="stale old test")
    with pytest.raises(workflow.Invalid, match="completed remediation"):
        state(value)


def test_ci_refreshes_current_body_and_rejects_stale_head():
    old_event = full_pr()
    metadata = {"number": 80, **copy.deepcopy(old_event["pull_request"])}
    metadata["body"] = "Primary issue: #74"
    assert workflow.current_pr(old_event, metadata)["pull_request"]["body"] == "Primary issue: #74"
    metadata["head"]["sha"] = "c" * 40
    with pytest.raises(workflow.Invalid, match="stale head"):
        workflow.current_pr(old_event, metadata)


@pytest.mark.parametrize("number", [80, 81])
def test_ci_rejects_ready_ledger_without_recorded_delivery(number):
    value = clean(True)
    state(value).gate("delivery", START + timedelta(seconds=100))
    request = pr()
    request["number"] = number
    with pytest.raises(workflow.Invalid, match="recorded delivery"):
        workflow.check_pr(
            request, {73: value}, at(0), START + timedelta(seconds=100), {73}, CONTENT
        )


@pytest.mark.parametrize("field", ["sha", "ref", "repo"])
def test_ci_rejects_live_base_change_with_unchanged_head(field):
    request = full_pr()
    metadata = {"number": 80, **copy.deepcopy(request["pull_request"])}
    assert workflow.current_pr(request, metadata)["pull_request"]["base"] == metadata["base"]
    metadata["base"][field] = (
        {"full_name": "other/repo"}
        if field == "repo"
        else "c" * 40
        if field == "sha"
        else "changed"
    )
    with pytest.raises(workflow.Invalid, match="stale base"):
        workflow.current_pr(request, metadata)


@pytest.mark.parametrize("cli_base", ["b" * 40, "c" * 40])
def test_ci_prefix_uses_validated_base_sha(monkeypatch, tmp_path, cli_base):
    import io

    request = full_pr("", "2026-09-25T00:00:00Z")
    path = tmp_path / "event.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    metadata = {"number": 80, **request["pull_request"]}
    monkeypatch.setattr(workflow, "validate_all", lambda *_: {})
    monkeypatch.setattr(
        workflow.urllib.request, "urlopen", lambda *_args, **_kw: io.StringIO(json.dumps(metadata))
    )
    bases = []
    monkeypatch.setattr(
        workflow, "check_prefix", lambda _root, base, _ledgers, _now: bases.append(base) or set()
    )
    monkeypatch.setattr(sys, "argv", ["workflow", "ci", "--event", str(path), "--base", cli_base])
    if cli_base == "b" * 40:
        workflow.main()
        assert bases == ["b" * 40]
    else:
        with pytest.raises(SystemExit) as failure:
            workflow.main()
        assert failure.value.code == 1
        assert bases == []


def test_delivered_history_cannot_be_reopened():
    value = clean()
    add(value, "delivery", 20, evidence="clean delivery")
    add(value, "design_ready", 21, authority=AUTH, evidence="attempt to reopen")
    with pytest.raises(workflow.Invalid, match="terminal history"):
        state(value)


def test_failed_final_extension_does_not_clear_unresolved_blockers():
    value = clean(True, True)
    value["events"] = value["events"][
        : next(
            i
            for i, e in enumerate(value["events"])
            if e["type"] == "phase_end" and e["data"]["session"] == "final_review"
        )
        + 1
    ]
    value["events"][-1]["data"]["outcome"] = "fail"
    add(value, "blocker", 16, id="F2", criterion="INV1", scenario="safety defect", evidence="repro")
    add(
        value,
        "extension",
        17,
        authority=USER,
        seconds=60,
        counts={**dict.fromkeys(workflow.COUNTS, 0), "remediation": 1, "final_review": 1},
        reason="one finite further attempt",
    )
    result = state(value)
    assert not result.final_failed and result.blockers
    with pytest.raises(workflow.Invalid):
        result.gate("delivery", START + timedelta(seconds=100))


def test_initial_design_name_cannot_bypass_reset_reservation():
    value = clean(True)
    add(
        value,
        "phase_start",
        20,
        phase="design",
        role="design_architect",
        session="replacement-architect",
    )
    with pytest.raises(workflow.Invalid, match="design_reset slot"):
        state(value)


def test_failed_challenge_cannot_repeat_without_reset():
    value = ledger(True)
    phase(value, "design", 1)
    phase(value, "challenge", 3, "fail")
    add(
        value,
        "phase_start",
        5,
        phase="challenge",
        role="code_reviewer",
        session="replacement-challenger",
    )
    with pytest.raises(workflow.Invalid, match="reset required"):
        state(value)


def test_explicit_extension_approval_cannot_be_replayed_to_refill_budget():
    value = clean()
    data = {
        "authority": USER,
        "seconds": 60,
        "counts": dict.fromkeys(workflow.COUNTS, 0),
        "reason": "one minute approved",
    }
    add(value, "extension", 20, **data)
    add(value, "extension", 21, **data)
    with pytest.raises(workflow.Invalid, match="authorization already consumed"):
        state(value)


def review_failed():
    value = ledger(True)
    phase(value, "design", 1)
    phase(value, "challenge", 3)
    ready(value, 5)
    phase(value, "implementation", 6)
    phase(value, "initial_review", 8, "fail")
    return value


def test_R1_final_review_excludes_every_remediation_author():
    value = review_failed()
    add(
        value,
        "owner_handoff",
        10,
        authority=AUTH,
        owner={
            "role": "implementation_worker",
            "model": "gpt-6-sol",
            "effort": "medium",
            "session": "remediation",
        },
        reason="fresh same-role owner",
        escalation=None,
    )
    phase(value, "remediation", 11, session="remediation")
    phase(value, "final_review", 13, session="remediation")
    with pytest.raises(workflow.Invalid, match=r"independent read-only|fresh separate session"):
        state(value)


@pytest.mark.parametrize("next_phase", ["challenge", "approval"])
def test_R2_failed_reset_cannot_reuse_old_successful_design(next_phase):
    value = clean(True)
    phase(value, "design_reset", 20, "fail", "new-architect")
    if next_phase == "challenge":
        phase(value, "challenge", 22, session="new-challenger")
    else:
        ready(value, 22)
    with pytest.raises(workflow.Invalid):
        state(value)


def test_R3_future_adoption_cannot_fabricate_role_order_or_independence():
    value = ledger(True, issue=80)
    value["events"][0]["data"]["adoption"] = {
        "from": at(0),
        "phases": [
            {"phase": name, "session": "same-author", "outcome": "pass"}
            for name in ["design", "challenge", "implementation", "final_review", "verification"]
        ],
        "evidence": "pretended tooling adoption",
    }
    with pytest.raises(workflow.Invalid, match="future adoption forbidden"):
        state(value)


def test_R3_known_issue73_bootstrap_prefix_remains_exact_and_gets_bound():
    root = Path(__file__).resolve().parents[1]
    recorded = workflow.read_all(root)[73]
    prefix = {"schema": 1, "events": recorded["events"][: workflow.BOOTSTRAP_EVENTS]}
    assert workflow.digest(prefix) == workflow.BOOTSTRAP_DIGEST
    bound = {"schema": 1, "events": recorded["events"][: workflow.BOOTSTRAP_EVENTS + 1]}
    result = workflow.replay(bound, datetime.now(UTC))
    assert result.capsule and result.active["phase"] == "remediation"
    assert result.approved_owner["session"] == "/root/bounded_workflow_implementation"
    invalid = copy.deepcopy(bound)
    invalid["events"][0]["data"]["adoption"]["phases"][0]["session"] = "fabricated"
    with pytest.raises(workflow.Invalid):
        workflow.replay(invalid, datetime.now(UTC))


@pytest.mark.parametrize("damage", ["other-pr", "new-content"])
def test_R4_delivered_ledger_only_authorizes_original_pr_and_content(damage):
    value = clean(True)
    add(value, "delivery", 20, evidence="original delivery")
    current = pr()
    content = CONTENT
    if damage == "other-pr":
        current["number"] = 81
    else:
        content = "a" * 64
    with pytest.raises(workflow.Invalid, match="another PR or different content"):
        workflow.check_pr(
            current, {73: value}, at(0), START + timedelta(seconds=100), content=content
        )
    assert "passed" in workflow.check_pr(
        pr(), {73: value}, at(0), START + timedelta(seconds=100), content=CONTENT
    )


def test_R4_post_review_content_change_cannot_use_old_verification():
    value = clean(True)
    add(value, "delivery", 20, evidence="recorded original delivery")
    with pytest.raises(workflow.Invalid, match="different content"):
        workflow.check_pr(
            pr(), {73: value}, at(0), START + timedelta(seconds=100), content="a" * 64
        )


@pytest.mark.parametrize("presentation", ["name", "whitespace", "both"])
def test_R5_extension_approval_replay_ignores_display_name_and_whitespace(presentation):
    value = clean()
    data = {
        "authority": USER,
        "seconds": 60,
        "counts": dict.fromkeys(workflow.COUNTS, 0),
        "reason": "one minute",
    }
    add(value, "extension", 20, **data)
    changed = copy.deepcopy(data)
    if presentation in {"name", "both"}:
        changed["authority"]["name"] = "beagle1903 "
    if presentation in {"whitespace", "both"}:
        changed["authority"]["evidence"] = "  explicit\n finite   approval  "
    add(value, "extension", 21, **changed)
    with pytest.raises(workflow.Invalid, match="authorization already consumed"):
        state(value)


@pytest.mark.parametrize("field", ["scope", "invariants", "acceptance"])
def test_R6_same_ids_with_changed_meaning_break_design_challenge_binding(field):
    value = clean(True)
    definitions = value["events"][0]["data"]["capsule"][field]
    definitions[next(iter(definitions))] = "different contract with same ID"
    with pytest.raises(workflow.Invalid, match="capsule content/generation"):
        state(value)


def test_R6_challenge_and_approval_cannot_use_previous_generation():
    value = clean(True)
    old = workflow.capsule_ref(current_capsule(value))
    phase(value, "design_reset", 20)
    phase(value, "challenge", 22, session="fresh-challenger")
    value["events"][-2]["data"]["capsule"] = old
    with pytest.raises(workflow.Invalid, match="capsule content/generation"):
        state(value)


def test_R6_incomplete_capsule_and_outside_reset_redefinition_fail():
    value = ledger()
    del value["events"][0]["data"]["capsule"]["json_state_impact"]
    with pytest.raises(workflow.Invalid, match="expected fields"):
        state(value)
    value = clean(True)
    revised = current_capsule(value)
    revised["rationale"] = "new design"
    add(value, "capsule_update", 20, authority=AUTH, capsule=revised)
    with pytest.raises(workflow.Invalid, match="active design reset"):
        state(value)


def test_R7_consequential_bounded_worker_and_wrong_owner_session_are_rejected():
    for role, session in [
        ("bounded_worker", "worker"),
        ("implementation_worker", "unapproved-owner"),
    ]:
        value = ledger(True)
        phase(value, "design", 1)
        phase(value, "challenge", 3)
        ready(value, 5)
        add(value, "phase_start", 6, phase="implementation", role=role, session=session)
        with pytest.raises(workflow.Invalid, match="classification and approved owner"):
            state(value)


def test_R7_specialist_requires_concrete_recorded_escalation_and_pinned_settings():
    value = review_failed()
    specialist = {
        "role": "implementation_specialist",
        "model": "gpt-6-sol",
        "effort": "high",
        "session": "specialist",
    }
    add(
        value,
        "owner_handoff",
        10,
        authority=AUTH,
        owner=specialist,
        reason="concrete concurrency failure",
        escalation=None,
    )
    with pytest.raises(workflow.Invalid):
        state(value)
    value["events"][-1]["data"]["escalation"] = {
        "authority": AUTH,
        "trigger": "concurrency",
        "evidence": "reproducible concurrent write failure",
    }
    add(
        value,
        "phase_start",
        11,
        phase="remediation",
        role="implementation_specialist",
        session="specialist",
    )
    assert state(value).active["session"] == "specialist"
    value["events"][-2]["data"]["owner"]["effort"] = "max"
    with pytest.raises(workflow.Invalid, match="pinned routing"):
        state(value)


def test_content_digest_matches_git_tree_and_excludes_only_own_ledger(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".gitattributes").write_text("* text=auto eol=lf\n", encoding="utf-8")
    (tmp_path / "code.py").write_bytes(b"value=1\r\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True
    )
    original = workflow.content_digest(tmp_path, 73)
    assert workflow.content_digest(tmp_path, 73, "HEAD") == original
    tickets = tmp_path / workflow.DIRECTORY
    tickets.mkdir(parents=True)
    (tickets / "issue-73.json").write_text("mutable ledger", encoding="utf-8")
    assert workflow.content_digest(tmp_path, 73) == original
    (tmp_path / "code.py").write_text("value=2\n", encoding="utf-8")
    assert workflow.content_digest(tmp_path, 73) != original


def test_capsule_boolean_generation_is_rejected_not_equal_to_one():
    value = clean(True)
    value["events"][1]["data"]["capsule"]["generation"] = True
    with pytest.raises(workflow.Invalid, match="integer"):
        state(value)


def test_R7_mechanical_owner_routing_and_same_role_fresh_handoff():
    value = ledger()
    initial = value["events"][0]["data"]
    initial["classification"] = initial["capsule"]["classification"] = "mechanical"
    initial["capsule"]["owner"].update(role="bounded_worker", model="gpt-6-luna")
    ready(value)
    add(value, "phase_start", 1, phase="implementation", role="bounded_worker", session="worker")
    add(
        value,
        "phase_end",
        2,
        session="worker",
        outcome="pass",
        evidence="mechanical implementation",
    )
    add(value, "phase_start", 3, phase="verification", role="bounded_worker", session="worker")
    add(value, "phase_end", 4, session="worker", outcome="pass", evidence="focused verification")
    add(value, "acceptance", 5, ids=["AC1"], evidence="covered")
    state(value).gate("delivery", START + timedelta(seconds=100))


def test_append_cannot_certify_changed_content_after_review_reservation(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    value = clean(True)
    start = next(
        i
        for i, item in enumerate(value["events"])
        if item["type"] == "phase_start" and item["data"]["phase"] == "initial_review"
    )
    value["events"] = value["events"][: start + 1]
    path = tmp_path / workflow.DIRECTORY / "issue-73.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    before = path.read_bytes()
    (tmp_path / "new_code.py").write_text("changed=1\n", encoding="utf-8")
    with pytest.raises(workflow.Invalid, match="repository content changed"):
        workflow.append(
            tmp_path,
            73,
            event(
                "phase_end", 9, session="initial_review", outcome="pass", evidence="stale review"
            ),
            START + timedelta(seconds=9),
        )
    assert path.read_bytes() == before
