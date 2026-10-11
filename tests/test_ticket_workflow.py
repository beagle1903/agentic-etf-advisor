"""Finite ticket transitions, adversarial history and CI binding."""

import copy
import json
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
    with pytest.raises(workflow.Invalid, match="split is unsupported"):
        state(damaged)
    bad_initial = owner_ledger()
    bad_initial["events"][0]["data"]["predecessor"] = {"issue": 1, "digest": "0" * 64}
    with pytest.raises(workflow.Invalid, match="predecessor is unsupported"):
        state(bad_initial)


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
    path.with_suffix(".lock").touch()
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
    assert workflow.check_prefix(
        tmp_path, "main", {86: transitioned}, START + timedelta(seconds=1)
    ) == {86}

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


def full_pr(body="Primary issue: #73", *, fork=False):
    value = pr(body)
    value["pull_request"].update(
        number=80,
        head={
            "sha": "a" * 40,
            "ref": "feature",
            "repo": {"full_name": "fork/repo" if fork else "beagle1903/agentic-etf-advisor"},
        },
        base={
            "sha": "b" * 40,
            "ref": "main",
            "repo": {"full_name": "beagle1903/agentic-etf-advisor"},
        },
    )
    return value


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
    metadata = copy.deepcopy(old_event["pull_request"])
    metadata["body"] = "Primary issue: #74"
    before_event, before_live = copy.deepcopy(old_event), copy.deepcopy(metadata)
    assert workflow.current_pr(old_event, metadata)["pull_request"] == metadata
    assert (old_event, metadata) == (before_event, before_live)
    metadata["head"]["sha"] = "c" * 40
    with pytest.raises(workflow.Invalid, match="stale identity"):
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


@pytest.mark.parametrize(
    "side,field", [(side, field) for side in ("head", "base") for field in ("sha", "ref", "repo")]
)
def test_ci_rejects_live_branch_change_with_same_head_sha(side, field):
    request = full_pr(fork=True)
    metadata = copy.deepcopy(request["pull_request"])
    assert workflow.current_pr(request, metadata)["pull_request"] == metadata
    metadata[side][field] = (
        {"full_name": "other/repo"}
        if field == "repo"
        else ("c" * 40 if field == "sha" else "other-branch")
    )
    with pytest.raises(workflow.Invalid, match="stale"):
        workflow.current_pr(request, metadata)


@pytest.mark.parametrize("field", ["number", "created_at"])
def test_ci_rejects_live_scalar_identity_change(field):
    request = full_pr()
    metadata = copy.deepcopy(request["pull_request"])
    metadata[field] = 81 if field == "number" else "2026-09-27T04:23:34Z"
    with pytest.raises(workflow.Invalid, match="stale"):
        workflow.current_pr(request, metadata)


@pytest.mark.parametrize("fork", [False, True])
def test_ci_accepts_complete_matching_identity(fork):
    request = full_pr(fork=fork)
    metadata = copy.deepcopy(request["pull_request"])
    metadata["body"] = "Primary issue: #74"
    assert workflow.current_pr(request, metadata)["pull_request"] == metadata


def test_ci_accepts_matching_64_character_shas():
    request = full_pr()
    request["pull_request"]["head"]["sha"] = "a" * 64
    request["pull_request"]["base"]["sha"] = "b" * 64
    metadata = copy.deepcopy(request["pull_request"])
    assert workflow.current_pr(request, metadata)["pull_request"] == metadata


def test_ci_accepts_ordinary_unicode_branch_and_fork_names():
    request = full_pr(fork=True)
    request["pull_request"]["head"]["ref"] = "özellik"
    request["pull_request"]["head"]["repo"]["full_name"] = "münchen/repo"
    metadata = copy.deepcopy(request["pull_request"])
    assert workflow.current_pr(request, metadata)["pull_request"] == metadata


@pytest.mark.parametrize("target", ["queued", "live", "both"])
@pytest.mark.parametrize("side", ["head", "base"])
@pytest.mark.parametrize("field", ["ref", "repo"])
def test_ci_rejects_bidirectional_control_in_identity(target, side, field):
    request = full_pr(fork=True)
    metadata = copy.deepcopy(request["pull_request"])
    assert workflow.current_pr(request, metadata)["pull_request"] == metadata
    malformed = "feature\u202ehidden" if field == "ref" else "owner\u202eextra/repo"
    snapshots = {
        "queued": [request["pull_request"]],
        "live": [metadata],
        "both": [request["pull_request"], metadata],
    }
    for value in snapshots[target]:
        if field == "ref":
            value[side]["ref"] = malformed
        else:
            value[side]["repo"]["full_name"] = malformed
    if side == "base" and field == "repo" and target == "both":
        request["repository"]["full_name"] = malformed
    with pytest.raises(workflow.Invalid):
        workflow.current_pr(request, metadata)


@pytest.mark.parametrize(
    "side,field", [(side, field) for side in ("head", "base") for field in ("sha", "ref", "repo")]
)
def test_ci_rejects_changed_queued_branch_identity(side, field):
    request = full_pr(fork=True)
    metadata = copy.deepcopy(request["pull_request"])
    request["pull_request"][side][field] = (
        {"full_name": "other/repo"}
        if field == "repo"
        else ("c" * 40 if field == "sha" else "other-branch")
    )
    with pytest.raises(workflow.Invalid, match="stale"):
        workflow.current_pr(request, metadata)


@pytest.mark.parametrize("side", ["event", "queued", "live"])
def test_ci_rejects_event_base_or_nested_number_mismatch(side):
    request = full_pr()
    metadata = copy.deepcopy(request["pull_request"])
    if side == "event":
        request["repository"]["full_name"] = "other/repo"
    elif side == "queued":
        request["pull_request"]["number"] = 81
    else:
        metadata["number"] = 81
    with pytest.raises(workflow.Invalid, match="stale"):
        workflow.current_pr(request, metadata)


@pytest.mark.parametrize("body", [None, "", "Primary issue: #74"])
def test_ci_accepts_optional_live_body(body):
    request = full_pr()
    metadata = copy.deepcopy(request["pull_request"])
    if body is None:
        del metadata["body"]
    else:
        metadata["body"] = body
    assert workflow.current_pr(request, metadata)["pull_request"] == metadata


@pytest.mark.parametrize("target", ["queued", "live"])
@pytest.mark.parametrize(
    "mutation",
    [
        "missing_number",
        "bool_number",
        "missing_head",
        "null_base_repo",
        "bad_sha",
        "bad_ref",
        "bad_repo",
        "bad_time",
        "bad_body",
        "null_pr",
    ],
)
def test_ci_rejects_malformed_required_identity(target, mutation):
    request = full_pr()
    metadata = copy.deepcopy(request["pull_request"])
    value = request["pull_request"] if target == "queued" else metadata
    if mutation == "missing_number":
        del value["number"]
    elif mutation == "bool_number":
        value["number"] = True
    elif mutation == "missing_head":
        del value["head"]
    elif mutation == "null_base_repo":
        value["base"]["repo"] = None
    elif mutation == "bad_sha":
        value["head"]["sha"] = "A" * 40
    elif mutation == "bad_ref":
        value["head"]["ref"] = "bad\x80ref"
    elif mutation == "bad_repo":
        value["base"]["repo"]["full_name"] = "owner/ bad"
    elif mutation == "bad_time":
        value["created_at"] = "2026-09-26T04:23:34+00:00"
    elif mutation == "bad_body":
        value["body"] = []
    else:
        if target == "queued":
            request["pull_request"] = None
        else:
            metadata = None
    with pytest.raises(workflow.Invalid):
        workflow.current_pr(request, metadata)


@pytest.mark.parametrize("cli_base", ["b" * 40, "c" * 40])
def test_ci_prefix_uses_validated_base_sha(monkeypatch, tmp_path, cli_base):
    import io

    request = full_pr("")
    request["pull_request"]["created_at"] = "2026-09-25T00:00:00Z"
    path = tmp_path / "event.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    metadata = copy.deepcopy(request["pull_request"])
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


def test_ci_consumes_live_body_base_and_head(monkeypatch, tmp_path):
    import io

    request = full_pr()
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(request), encoding="utf-8")
    metadata = copy.deepcopy(request["pull_request"])
    metadata["body"] = "Primary issue: #74"
    seen = []

    def urlopen(http_request, **_kwargs):
        seen.append(http_request.full_url)
        result = metadata if len(seen) == 1 else {"number": 74, "created_at": at(0)}
        return io.StringIO(json.dumps(result))

    monkeypatch.setattr(workflow, "validate_all", lambda *_: {})
    monkeypatch.setattr(workflow.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(
        workflow, "check_prefix", lambda _root, base, _ledgers, _now: seen.append(base) or set()
    )
    monkeypatch.setattr(
        workflow,
        "content_digest",
        lambda _root, issue, head: seen.append((issue, head)) or "digest",
    )
    monkeypatch.setattr(
        workflow,
        "check_pr",
        lambda event, *_args: seen.append(event["pull_request"]["body"]) or "passed",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["workflow", "ci", "--event", str(event_file), "--base", "b" * 40],
    )
    workflow.main()
    assert seen[1] == "b" * 40
    assert seen[2].endswith("/issues/74")
    assert seen[3] == (74, "a" * 40)
    assert seen[4] == "Primary issue: #74"


def test_ci_stale_live_identity_stops_before_prefix_and_issue_lookup(monkeypatch, tmp_path):
    import io

    request = full_pr(fork=True)
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(request), encoding="utf-8")
    metadata = copy.deepcopy(request["pull_request"])
    metadata["head"]["repo"]["full_name"] = "other/repo"
    fetched = []
    prefixes = []

    def urlopen(http_request, **_kwargs):
        fetched.append(http_request.full_url)
        return io.StringIO(json.dumps(metadata))

    monkeypatch.setattr(workflow, "validate_all", lambda *_: {})
    monkeypatch.setattr(workflow.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(workflow, "check_prefix", lambda *_args: prefixes.append(True) or set())
    monkeypatch.setattr(
        sys, "argv", ["workflow", "ci", "--event", str(event_file), "--base", "b" * 40]
    )
    with pytest.raises(SystemExit) as failure:
        workflow.main()
    assert failure.value.code == 1
    assert len(fetched) == 1
    assert prefixes == []


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
