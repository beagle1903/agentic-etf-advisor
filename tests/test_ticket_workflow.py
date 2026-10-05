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
    init = ledger()["events"][0]
    init["data"]["lifetime_policy"] = "cycles-v1"
    workflow.append(tmp_path, 73, init, START)
    path = tmp_path / workflow.DIRECTORY / "issue-73.json"
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
    old_event = {**pr(), "number": 80}
    old_event["pull_request"]["head"] = {"sha": "a"}
    base = {"sha": "base-a", "ref": "main", "repo": {"full_name": "owner/repo"}}
    old_event["pull_request"]["base"] = base
    metadata = {"number": 80, "body": "Primary issue: #74", "head": {"sha": "a"}, "base": base}
    assert workflow.current_pr(old_event, metadata)["pull_request"]["body"] == "Primary issue: #74"
    metadata["head"]["sha"] = "b"
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
    request = pr()
    request["pull_request"].update(
        head={"sha": "same-head"},
        base={"sha": "base-a", "ref": "main", "repo": {"full_name": "owner/repo"}},
    )
    metadata = {"number": 80, **copy.deepcopy(request["pull_request"])}
    assert workflow.current_pr(request, metadata)["pull_request"]["base"] == metadata["base"]
    metadata["base"][field] = {"full_name": "other/repo"} if field == "repo" else "changed"
    with pytest.raises(workflow.Invalid, match="stale base"):
        workflow.current_pr(request, metadata)


@pytest.mark.parametrize("cli_base", ["base-a", "different-base"])
def test_ci_prefix_uses_validated_base_sha(monkeypatch, tmp_path, cli_base):
    import io

    request = pr("", "2026-09-25T00:00:00Z")
    request["pull_request"].update(
        head={"sha": "same-head"},
        base={"sha": "base-a", "ref": "main", "repo": {"full_name": "owner/repo"}},
    )
    path = tmp_path / "event.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    metadata = {"number": 80, **request["pull_request"]}
    monkeypatch.setattr(workflow, "validate_all", lambda *_: {})
    monkeypatch.setattr(
        workflow.urllib.request, "urlopen", lambda *_args, **_kw: io.StringIO(json.dumps(metadata))
    )
    bases = []
    monkeypatch.setattr(
        workflow,
        "check_prefix",
        lambda _root, base, _ledgers, _primary: bases.append(base) or set(),
    )
    monkeypatch.setattr(sys, "argv", ["workflow", "ci", "--event", str(path), "--base", cli_base])
    if cli_base == "base-a":
        workflow.main()
        assert bases == ["base-a"]
    else:
        with pytest.raises(SystemExit) as failure:
            workflow.main()
        assert failure.value.code == 1
        assert bases == []


def cycle_ledger(issue: int = 90) -> dict:
    value = ledger(issue=issue)
    value["events"][0]["data"]["lifetime_policy"] = "cycles-v1"
    return value


def transition(value: dict, offset: int, *, waivers: list[str] | None = None) -> None:
    add(
        value,
        "policy_transition",
        offset,
        authority={**USER, "evidence": f"cycle approval {offset}"},
        **{"from": "timed-v1", "to": "cycles-v1"},
        prefix_digest=workflow.digest(value),
        reason="User selected cycle limits",
        time_blocker_waivers=[] if waivers is None else waivers,
    )


def test_cycle_policy_ignores_long_wait_but_keeps_attempt_limits():
    value = cycle_ledger()
    ready(value, 1)
    result = state(value, 100_000)
    assert result.lifetime_policy == "cycles-v1"
    result.gate("implementation", START + timedelta(seconds=100_000))
    phase(value, "implementation", 100_001)
    with pytest.raises(workflow.Invalid, match="lifetime limit"):
        state(value, 100_100).gate("implementation", START + timedelta(seconds=100_100))


def test_expired_suspended_legacy_transitions_without_resuming():
    value = ledger(issue=91)
    ready(value, 1)
    add(
        value,
        "phase_start",
        2,
        phase="implementation",
        role="implementation_worker",
        session="worker",
    )
    add(value, "pause", 3, session="worker", outcome="interrupted", evidence="quota wait")
    transition(value, 100_000)
    result = state(value, 100_001)
    assert result.suspended and result.active is None
    add(value, "phase_resume", 100_002, session="worker")
    assert state(value, 100_003).active


def test_transition_keeps_substantive_blockers_and_is_single_use():
    value = ledger(issue=92)
    add(
        value, "blocker", 1, id="defect", criterion="AC1", scenario="unsafe result", evidence="case"
    )
    transition(value, 2)
    result = state(value)
    assert "defect" in result.blockers
    with pytest.raises(workflow.Invalid, match="invalid or stale policy transition"):
        transition(value, 3)
        state(value)


def test_cycle_split_conserves_siblings_and_inherits_counts():
    parent = cycle_ledger(93)
    ready(parent, 1)
    phase(parent, "implementation", 2)
    first = {key: 0 for key in workflow.COUNTS}
    first["initial_review"] = 1
    second = {key: 0 for key in workflow.COUNTS}
    second["final_review"] = 1
    add(
        parent,
        "cycle_split",
        5,
        authority=USER,
        successor=94,
        remaining_counts=first,
        reason="bounded split",
    )
    add(
        parent,
        "cycle_split",
        6,
        authority={**USER, "evidence": "separate sibling allocation approval"},
        successor=95,
        remaining_counts=second,
        reason="bounded split",
    )
    assert state(parent).split_remaining_counts["initial_review"] == 0
    child = cycle_ledger(94)
    child["events"][0]["at"] = at(7)
    child["events"][0]["data"]["predecessor"] = {"issue": 93, "digest": workflow.digest(parent)}
    inherited = state(child, predecessors={93: parent})
    assert inherited.counts["implementation"] == 1
    assert inherited.limits["implementation"] == 1
    assert inherited.limits["initial_review"] == 1
    with pytest.raises(workflow.Invalid, match="lifetime limit"):
        inherited.gate("implementation", START + timedelta(seconds=100))
    third = {key: 0 for key in workflow.COUNTS}
    third["initial_review"] = 1
    add(
        parent,
        "cycle_split",
        7,
        authority={**USER, "evidence": "separate over-allocation approval"},
        successor=96,
        remaining_counts=third,
        reason="overallocate",
    )
    with pytest.raises(workflow.Invalid, match="allocations exceed"):
        state(parent)


def test_cycle_split_approval_cannot_extend_successor_under_alias_or_whitespace():
    parent = cycle_ledger(190)
    allocation = dict.fromkeys(workflow.COUNTS, 0)
    allocation["implementation"] = 1
    split_authority = {**USER, "evidence": "approved  bounded\nallocation"}
    add(
        parent,
        "cycle_split",
        1,
        authority=split_authority,
        successor=191,
        remaining_counts=allocation,
        reason="one successor allocation",
    )
    child = cycle_ledger(191)
    child["events"][0]["at"] = at(2)
    child["events"][0]["data"]["predecessor"] = {
        "issue": 190,
        "digest": workflow.digest(parent),
    }
    assert state(child, predecessors={190: parent}).limits["implementation"] == 1
    add(
        child,
        "extension",
        3,
        authority={
            **split_authority,
            "name": "renamed",
            "evidence": " approved bounded allocation ",
        },
        seconds=0,
        counts=allocation,
        reason="attempted reuse of split approval",
    )
    with pytest.raises(workflow.Invalid, match="already consumed"):
        state(child, predecessors={190: parent})


def test_cycle_split_approval_cannot_be_reused_for_sibling():
    parent = cycle_ledger(192)
    allocation = dict.fromkeys(workflow.COUNTS, 0)
    allocation["initial_review"] = 1
    add(
        parent,
        "cycle_split",
        1,
        authority={**USER, "evidence": "approved sibling allocation"},
        successor=193,
        remaining_counts=allocation,
        reason="first sibling",
    )
    add(
        parent,
        "cycle_split",
        2,
        authority={**USER, "name": "renamed", "evidence": " approved  sibling\nallocation "},
        successor=194,
        remaining_counts=allocation,
        reason="attempted reused approval",
    )
    with pytest.raises(workflow.Invalid, match="already consumed"):
        state(parent)


@pytest.mark.parametrize("sibling_first", [True, False])
def test_later_sibling_approval_cannot_extend_earlier_child(tmp_path, sibling_first):
    parent = cycle_ledger(195)
    implementation = dict.fromkeys(workflow.COUNTS, 0)
    implementation["implementation"] = 1
    review = dict.fromkeys(workflow.COUNTS, 0)
    review["final_review"] = 1
    add(
        parent,
        "cycle_split",
        1,
        authority={**USER, "evidence": "first approval"},
        successor=196,
        remaining_counts=implementation,
        reason="first child",
    )
    child = cycle_ledger(196)
    child["events"][0]["at"] = at(2)
    child["events"][0]["data"]["predecessor"] = {
        "issue": 195,
        "digest": workflow.digest(parent),
    }
    sibling = event(
        "cycle_split",
        3 if sibling_first else 4,
        authority={**USER, "evidence": "later  sibling\napproval"},
        successor=197,
        remaining_counts=review,
        reason="second child",
    )
    reused = event(
        "extension",
        4 if sibling_first else 3,
        authority={**USER, "name": "alias", "evidence": " later sibling approval "},
        seconds=0,
        counts=implementation,
        reason="reused sibling approval",
    )
    if sibling_first:
        parent["events"].append(sibling)
        target, candidate = 196, reused
    else:
        child["events"].append(reused)
        target, candidate = 195, sibling
    directory = tmp_path / workflow.DIRECTORY
    directory.mkdir(parents=True)
    for issue, value in ((195, parent), (196, child)):
        (directory / f"issue-{issue}.json").write_text(json.dumps(value), encoding="utf-8")
    original = (directory / f"issue-{target}.json").read_bytes()
    with pytest.raises(workflow.Invalid, match="lineage authorization already consumed"):
        workflow.append(tmp_path, target, candidate, START + timedelta(seconds=5))
    assert (directory / f"issue-{target}.json").read_bytes() == original


def test_sibling_approval_cannot_extend_descendant(tmp_path):
    parent = cycle_ledger(198)
    implementation = dict.fromkeys(workflow.COUNTS, 0)
    implementation["implementation"] = 1
    review = dict.fromkeys(workflow.COUNTS, 0)
    review["final_review"] = 1
    add(
        parent,
        "cycle_split",
        1,
        authority={**USER, "evidence": "first allocation"},
        successor=199,
        remaining_counts=implementation,
        reason="first child",
    )
    child = cycle_ledger(199)
    child["events"][0]["at"] = at(2)
    child["events"][0]["data"]["predecessor"] = {
        "issue": 198,
        "digest": workflow.digest(parent),
    }
    add(
        child,
        "cycle_split",
        3,
        authority={**USER, "evidence": "descendant allocation"},
        successor=200,
        remaining_counts=implementation,
        reason="grandchild",
    )
    grandchild = cycle_ledger(200)
    grandchild["events"][0]["at"] = at(4)
    grandchild["events"][0]["data"]["predecessor"] = {
        "issue": 199,
        "digest": workflow.digest(child),
    }
    add(
        parent,
        "cycle_split",
        5,
        authority={**USER, "evidence": "later sibling approval"},
        successor=201,
        remaining_counts=review,
        reason="later sibling",
    )
    directory = tmp_path / workflow.DIRECTORY
    directory.mkdir(parents=True)
    for issue, value in ((198, parent), (199, child), (200, grandchild)):
        (directory / f"issue-{issue}.json").write_text(json.dumps(value), encoding="utf-8")
    reused = event(
        "extension",
        6,
        authority={**USER, "name": "alias", "evidence": " later  sibling\napproval "},
        seconds=0,
        counts=implementation,
        reason="reused ancestor sibling approval",
    )
    with pytest.raises(workflow.Invalid, match="lineage authorization already consumed"):
        workflow.append(tmp_path, 200, reused, START + timedelta(seconds=7))


def test_new_append_requires_cycles_even_if_backdated(tmp_path):
    old = ledger(issue=97)["events"][0]
    with pytest.raises(workflow.Invalid, match="requires cycles-v1"):
        workflow.append(tmp_path, 97, old, START)
    old["at"] = at(-10)
    with pytest.raises(workflow.Invalid, match="requires cycles-v1"):
        workflow.append(tmp_path, 97, old, START)


def retained_auth_pair() -> tuple[dict, dict]:
    directory = Path(__file__).parent / "fixtures" / "ticket_workflow"
    parent = workflow.load((directory / "issue-23.json").read_text(encoding="utf-8"))
    child = workflow.load((directory / "issue-83.json").read_text(encoding="utf-8"))
    assert len(parent["events"]) == 10
    assert workflow.digest(parent) == workflow.ISSUE23_COMPLETE_DIGEST
    assert len(child["events"]) == 9
    assert workflow.digest(child) == workflow.ISSUE83_LEGACY_DIGEST
    child["events"].append(
        {
            "type": "policy_transition",
            "at": "2026-10-04T17:11:17Z",
            "data": {
                "authority": {
                    "kind": "user",
                    "name": "beagle1903",
                    "evidence": "User authorized the cycle policy for the retained Issue83 history",
                },
                "from": "timed-v1",
                "to": "cycles-v1",
                "prefix_digest": workflow.ISSUE83_LEGACY_DIGEST,
                "reason": "Replace completion time with counted attempts",
                "time_blocker_waivers": ["B83-EXHAUSTED"],
            },
        }
    )
    return parent, child


@pytest.mark.parametrize("reuse_at", ["transition", "extension"])
def test_retained_timed_split_approval_cannot_authorize_cycle_work(reuse_at):
    parent, child = retained_auth_pair()
    original = parent["events"][-1]["data"]["authority"]["evidence"]
    reused = {"kind": "user", "name": "renamed", "evidence": "  ".join(original.split())}
    if reuse_at == "transition":
        child["events"][9]["data"]["authority"] = reused
    else:
        child["events"].append(
            {
                "type": "extension",
                "at": "2026-10-04T17:11:18Z",
                "data": {
                    "authority": reused,
                    "seconds": 0,
                    "counts": {**dict.fromkeys(workflow.COUNTS, 0), "implementation": 1},
                    "reason": "attempted reuse of old split approval",
                },
            }
        )
    with pytest.raises(workflow.Invalid, match="timed split authorization already consumed"):
        workflow.validate_ledgers(
            {23: parent, 83: child}, datetime(2026, 10, 4, 17, 11, 30, tzinfo=UTC)
        )


def test_retained_timed_split_accepts_distinct_cycle_approval():
    parent, child = retained_auth_pair()
    child["events"].append(
        {
            "type": "extension",
            "at": "2026-10-04T17:11:18Z",
            "data": {
                "authority": {**USER, "evidence": "distinct cycle extension approval"},
                "seconds": 0,
                "counts": {**dict.fromkeys(workflow.COUNTS, 0), "implementation": 1},
                "reason": "one separate finite attempt",
            },
        }
    )
    workflow.validate_ledgers(
        {23: parent, 83: child}, datetime(2026, 10, 4, 17, 11, 30, tzinfo=UTC)
    )


def test_timed_split_approval_cannot_extend_cycle_grandchild():
    parent = ledger(issue=210)
    old_approval = {**USER, "evidence": "original timed split approval"}
    add(parent, "split", 1, authority=old_approval, successor=211, seconds=3000, reason="child")
    child = ledger(issue=211)
    child["events"][0]["at"] = at(2)
    child["events"][0]["data"]["predecessor"] = {"issue": 210, "digest": workflow.digest(parent)}
    transition(child, 3)
    remaining = {**dict.fromkeys(workflow.COUNTS, 0), "implementation": 1}
    add(
        child,
        "cycle_split",
        4,
        authority={**USER, "evidence": "distinct grandchild allocation"},
        successor=212,
        remaining_counts=remaining,
        reason="grandchild",
    )
    grandchild = cycle_ledger(212)
    grandchild["events"][0]["at"] = at(5)
    grandchild["events"][0]["data"]["predecessor"] = {
        "issue": 211,
        "digest": workflow.digest(child),
    }
    add(
        grandchild,
        "extension",
        6,
        authority={
            **old_approval,
            "name": "renamed",
            "evidence": " original  timed\nsplit approval ",
        },
        seconds=0,
        counts=remaining,
        reason="reused ancestor approval",
    )
    with pytest.raises(workflow.Invalid, match="timed split authorization already consumed"):
        workflow.validate_ledgers(
            {210: parent, 211: child, 212: grandchild}, START + timedelta(seconds=10)
        )


def test_historical_timed_only_duplicate_split_approvals_still_replay():
    parent = ledger(issue=213)
    add(parent, "split", 1, authority=USER, successor=214, seconds=3000, reason="first")
    add(
        parent,
        "split",
        2,
        authority={**USER, "name": "renamed", "evidence": " explicit  finite\napproval "},
        successor=215,
        seconds=3000,
        reason="second",
    )
    workflow.validate_ledgers({213: parent}, START + timedelta(seconds=3))


def test_migrated_timed_child_rejects_later_sibling_split():
    parent = ledger(issue=216)
    add(parent, "split", 1, authority=USER, successor=217, seconds=3000, reason="child")
    child = ledger(issue=217)
    child["events"][0]["at"] = at(2)
    child["events"][0]["data"]["predecessor"] = {"issue": 216, "digest": workflow.digest(parent)}
    transition(child, 3)
    add(
        parent,
        "split",
        4,
        authority={**USER, "evidence": "later historical sibling approval"},
        successor=218,
        seconds=3000,
        reason="later sibling",
    )
    with pytest.raises(workflow.Invalid, match="sole successor"):
        workflow.validate_ledgers({216: parent, 217: child}, START + timedelta(seconds=5))


def empty_merge_base(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"], cwd=tmp_path, check=True, capture_output=True
    )


def test_retained_auth_pair_intro_and_long_wait_preserve_attempts(tmp_path):
    empty_merge_base(tmp_path)
    parent, child = retained_auth_pair()
    pair = {23: parent, 83: child}
    assert workflow.check_prefix(tmp_path, "main", pair, 83) == {23, 83}
    result = workflow.replay(child, datetime(2026, 11, 1, tzinfo=UTC), predecessors={23: parent})
    assert result.lifetime_policy == "cycles-v1"
    assert result.suspended and result.suspended["session"] == "/root/issue83_implementation"
    assert result.counts["implementation"] == 1
    assert "B83-EXHAUSTED" not in result.blockers
    child["events"].append(
        {
            "type": "phase_resume",
            "at": "2026-11-01T00:00:01Z",
            "data": {"session": "/root/issue83_implementation"},
        }
    )
    resumed = workflow.replay(
        child, datetime(2026, 11, 1, 0, 0, 2, tzinfo=UTC), predecessors={23: parent}
    )
    assert resumed.active and resumed.counts["implementation"] == 1
    child["events"].append(
        {
            "type": "phase_end",
            "at": "2026-11-01T00:00:03Z",
            "data": {
                "session": "/root/issue83_implementation",
                "outcome": "pass",
                "evidence": "bounded work",
            },
        }
    )
    ended = workflow.replay(
        child, datetime(2026, 11, 1, 0, 0, 4, tzinfo=UTC), predecessors={23: parent}
    )
    assert workflow.check_prefix(tmp_path, "main", pair, 83) == {23, 83}
    with pytest.raises(workflow.Invalid, match="implementation lifetime limit"):
        ended.gate("implementation", datetime(2026, 11, 1, 0, 0, 4, tzinfo=UTC))
    with pytest.raises(workflow.Invalid, match="incomplete design, verification or acceptance"):
        ended.gate("delivery", datetime(2026, 11, 1, 0, 0, 4, tzinfo=UTC))
    with pytest.raises(workflow.Invalid, match="PR repository differs from ledger"):
        workflow.check_pr(
            {**pr("Primary issue: #83"), "repository": {"full_name": "other/repo"}},
            pair,
            "2026-10-04T00:00:00Z",
            datetime(2026, 11, 1, 0, 0, 4, tzinfo=UTC),
            {23, 83},
            CONTENT,
        )


@pytest.mark.parametrize(
    "damage",
    [
        "wrong-primary",
        "missing-parent",
        "missing-child",
        "altered-parent",
        "extra-sibling",
        "altered-child",
        "missing-transition",
        "misplaced-transition",
        "wrong-prefix",
        "missing-waiver",
        "unrelated-waiver",
        "wrong-repo",
        "extra-legacy",
    ],
)
def test_retained_auth_pair_introduction_fails_closed(tmp_path, damage):
    empty_merge_base(tmp_path)
    parent, child = retained_auth_pair()
    pair = {23: parent, 83: child}
    primary = 83
    if damage == "wrong-primary":
        primary = 84
    elif damage == "missing-parent":
        del pair[23]
    elif damage == "missing-child":
        del pair[83]
    elif damage == "altered-parent":
        parent["events"][0]["data"]["scope"][0] = "changed"
    elif damage == "extra-sibling":
        parent["events"].append(copy.deepcopy(parent["events"][-1]))
    elif damage == "altered-child":
        child["events"][0]["data"]["scope"][0] = "changed"
    elif damage == "missing-transition":
        child["events"].pop()
    elif damage == "misplaced-transition":
        child["events"].insert(
            9,
            {
                "type": "charge",
                "at": "2026-10-04T17:11:17Z",
                "data": {"authority": AUTH, "seconds": 1, "evidence": "injected event"},
            },
        )
    elif damage == "wrong-prefix":
        child["events"][9]["data"]["prefix_digest"] = "0" * 64
    elif damage == "missing-waiver":
        child["events"][9]["data"]["time_blocker_waivers"] = []
    elif damage == "unrelated-waiver":
        child["events"][9]["data"]["time_blocker_waivers"] = ["other"]
    elif damage == "wrong-repo":
        child["events"][0]["data"]["repo"] = "other/repo"
    else:
        pair[85] = ledger(issue=85)
    with pytest.raises(workflow.Invalid, match="new ledger introduction requires cycles-v1"):
        workflow.check_prefix(tmp_path, "main", pair, primary)


def test_cycle_extension_uses_counts_only_and_single_authority():
    value = cycle_ledger(98)
    delta = {key: 0 for key in workflow.COUNTS}
    delta["implementation"] = 1
    add(
        value,
        "extension",
        1,
        authority=USER,
        seconds=0,
        counts=delta,
        reason="one extra implementation",
    )
    assert state(value).limits["implementation"] == 2
    add(
        value,
        "extension",
        2,
        authority={**USER, "name": "alias"},
        seconds=0,
        counts=delta,
        reason="replay",
    )
    with pytest.raises(workflow.Invalid, match="already consumed"):
        state(value)


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
