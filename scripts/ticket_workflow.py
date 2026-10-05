"""Finite development governance. Recorded evidence, never a runtime kill switch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = Path("docs/workflow/tickets")
ADOPTION = "2026-09-26T04:23:34Z"
BOOTSTRAP_EVENTS = 18
BOOTSTRAP_DIGEST = "ad92fa4555aa4162c9cefcfce7f6c2d233bdc318748b0b6b6b04bff208ae2779"
BOOTSTRAP_APPROVAL = (
    "https://github.com/beagle1903/agentic-etf-advisor/issues/73#issuecomment-5843156904"
)
ISSUE84_INITIAL_DIGEST = "462e26fdb7ae6be1315f55809630edd6c800fbad11295a3060aff4c932f3740c"
ISSUE83_BLOCKER_DIGEST = "d9ce023c33d2047faf2881d60dc54dae51e3594e175d9da23f5f6661e073cf56"
ISSUE23_COMPLETE_DIGEST = "edb0ea490e463a75cbb92696e1400c2ad8f32e939ae9fb905db132cb27e0baac"
ISSUE83_LEGACY_DIGEST = "b46ec791f25f51f7e022d00e6a654e0429e59b59a874500247f7f974c60664f9"
POLICIES = {"timed-v1", "cycles-v1"}
PINNED = {
    "bounded_worker": ("gpt-6-luna", "medium"),
    "implementation_worker": ("gpt-6-sol", "medium"),
    "implementation_specialist": ("gpt-6-sol", "high"),
}
NORMAL_OWNER = {
    "mechanical": "bounded_worker",
    "ordinary": "implementation_worker",
    "consequential": "implementation_worker",
    "high-risk/disputed": "implementation_worker",
    "difficult": "implementation_specialist",
}
COUNTS = {
    "implementation": 1,
    "initial_review": 1,
    "remediation": 1,
    "final_review": 1,
    "design_reset": 1,
}
PHASES = {
    "planning",
    "design",
    "challenge",
    "implementation",
    "initial_review",
    "remediation",
    "final_review",
    "design_reset",
    "verification",
}
ROLES = {
    "planning": {"planning_analyst"},
    "design": {"design_architect"},
    "challenge": {"code_reviewer"},
    "design_reset": {"design_architect"},
    "initial_review": {"code_reviewer"},
    "final_review": {"code_reviewer"},
    "implementation": {"bounded_worker", "implementation_worker", "implementation_specialist"},
    "remediation": {"bounded_worker", "implementation_worker", "implementation_specialist"},
    "verification": {"bounded_worker", "implementation_worker", "implementation_specialist"},
}


class Invalid(ValueError):
    """Fail-closed recorded workflow error."""


def keys(value: object, expected: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise Invalid(f"expected fields {sorted(expected)}")
    return value


def text(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise Invalid("expected nonempty bounded text")
    return value


def integer(value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise Invalid("expected bounded nonnegative integer")
    if value > 10_000_000:
        raise Invalid("integer exceeds bound")
    return value


def timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise Invalid("expected UTC seconds timestamp")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise Invalid("invalid UTC time") from exc


def identifiers(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise Invalid("expected nonempty frozen identifiers")
    result = [text(item) for item in value]
    if len(result) != len(set(result)):
        raise Invalid("duplicate identifier")
    return result


def authority(value: object, kind: str) -> None:
    item = keys(value, {"kind", "name", "evidence"})
    if item["kind"] != kind:
        raise Invalid(f"requires named {kind} authority")
    text(item["name"])
    text(item["evidence"])


def unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("duplicate JSON key")
        result[key] = value
    return result


def load(raw: str) -> dict:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(Invalid("nonfinite JSON")),
        )
    except (ValueError, TypeError) as exc:
        raise Invalid(f"invalid ledger JSON: {exc}") from exc
    value = keys(value, {"schema", "events"})
    if type(value["schema"]) is not int or value["schema"] != 1:
        raise Invalid("unsupported ledger schema")
    if not isinstance(value["events"], list) or not value["events"]:
        raise Invalid("empty event history")
    return value


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def sha(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        raise Invalid("expected SHA256 content digest")
    return value


def owner(value: object) -> dict:
    result = keys(value, {"role", "model", "effort", "session"})
    role = text(result["role"])
    if role not in PINNED or (result["model"], result["effort"]) != PINNED[role]:
        raise Invalid("owner role/model/effort does not match pinned routing")
    text(result["session"])
    return result


def definitions(value: object) -> dict:
    if not isinstance(value, dict) or not value:
        raise Invalid("complete frozen definitions required")
    for key, definition in value.items():
        text(key)
        text(definition)
    return value


def capsule(value: object, state: State) -> dict:
    value = keys(
        value,
        {
            "id",
            "generation",
            "repo",
            "issue",
            "classification",
            "owner",
            "rationale",
            "authorization",
            "scope",
            "non_goals",
            "invariants",
            "interfaces",
            "json_state_impact",
            "acceptance",
            "verification",
            "documentation",
            "risks",
            "escalation_triggers",
            "escalation",
        },
    )
    text(value["id"])
    integer(value["generation"], 1)
    integer(value["issue"], 1)
    if (value["repo"], value["issue"], value["classification"]) != (
        state.repo,
        state.issue,
        state.classification,
    ):
        raise Invalid("capsule identity/classification mismatch")
    selected = owner(value["owner"])
    for key in ("rationale", "json_state_impact"):
        text(value[key])
    authority(value["authorization"], "user")
    for key in (
        "non_goals",
        "interfaces",
        "verification",
        "documentation",
        "risks",
        "escalation_triggers",
    ):
        identifiers(value[key])
    for key, expected in (
        ("scope", state.scope),
        ("invariants", state.invariants),
        ("acceptance", state.acceptance),
    ):
        if set(definitions(value[key])) != set(expected):
            raise Invalid("capsule frozen identifiers differ from ticket")
    if (
        selected["role"] != NORMAL_OWNER[state.classification]
        and selected["role"] != "implementation_specialist"
    ):
        raise Invalid("capsule owner ignores classification")
    if selected["role"] == "implementation_specialist":
        escalation(value["escalation"])
    elif value["escalation"] is not None:
        raise Invalid("unexpected initial owner escalation")
    return value


def escalation(value: object) -> None:
    value = keys(value, {"authority", "trigger", "evidence"})
    authority(value["authority"], "coordinator")
    if value["trigger"] not in {
        "complexity",
        "unresolved_failure",
        "concurrency",
        "migration",
        "consequential_ambiguity",
    }:
        raise Invalid("recorded concrete specialist escalation required")
    text(value["evidence"])


def capsule_ref(value: dict) -> dict:
    return {"id": value["id"], "generation": value["generation"], "digest": digest(value)}


def require_capsule(value: object, state: State) -> None:
    value = keys(value, {"id", "generation", "digest"})
    text(value["id"])
    integer(value["generation"], 1)
    sha(value["digest"])
    if not state.capsule or value != capsule_ref(state.capsule):
        raise Invalid("stale or mismatched capsule content/generation")


def evidence_key(value: object) -> str:
    return " ".join(text(value).split())


def sole_legacy_lineage(value: dict, predecessors: dict[int, dict] | None) -> None:
    """A timed descendant may migrate only while every ancestor has one successor."""
    current = value
    seen: set[int] = set()
    while (link := current["events"][0]["data"].get("predecessor")) is not None:
        issue = integer(link["issue"], 1)
        if issue in seen or not predecessors or issue not in predecessors:
            raise Invalid("missing or cyclic legacy predecessor")
        seen.add(issue)
        parent = predecessors[issue]
        splits = [item for item in parent["events"] if item["type"] in {"split", "cycle_split"}]
        if (
            len(splits) != 1
            or splits[0]["data"]["successor"] != current["events"][0]["data"]["issue"]
        ):
            raise Invalid("migrated legacy lineage requires sole successor at every ancestor")
        current = parent


@dataclass
class State:
    repo: str
    issue: int
    classification: str
    acceptance: list[str]
    invariants: list[str]
    review_required: bool
    scope: list[str] = field(default_factory=list)
    capsule: dict | None = None
    approved_owner: dict | None = None
    design_ref: dict | None = None
    challenge_ref: dict | None = None
    approved_ref: dict | None = None
    write_authors: set[str] = field(default_factory=set)
    sessions: dict[str, str] = field(default_factory=dict)
    review_content: str | None = None
    verified_content: str | None = None
    acceptance_content: str | None = None
    delivery_binding: dict | None = None
    budget_seconds: int = 7200
    lifetime_policy: str = "timed-v1"
    elapsed_seconds: int = 0
    limits: dict = field(default_factory=lambda: COUNTS.copy())
    counts: dict = field(default_factory=lambda: dict.fromkeys(COUNTS, 0))
    active: dict | None = None
    suspended: dict | None = None
    clock_running: bool = True
    last: datetime | None = None
    design_session: str | None = None
    design_started: bool = False
    challenge_session: str | None = None
    author_session: str | None = None
    challenge_ok: bool = False
    ready: bool = False
    verified: bool = False
    accepted: bool = False
    reviewed: bool = False
    initial_failed: bool = False
    remediated: bool = False
    final_failed: bool = False
    blockers: dict = field(default_factory=dict)
    delivered: bool = False
    split_remaining: int | None = None
    split_remaining_counts: dict | None = None
    splits: dict = field(default_factory=dict)
    extension_authorizations: set[str] = field(default_factory=set)

    def elapsed(self, now: datetime) -> int:
        if self.last is not None and now < self.last:
            raise Invalid("time predates recorded history")
        extra = int((now - self.last).total_seconds()) if self.clock_running and self.last else 0
        return self.elapsed_seconds + extra

    def gate(self, operation: str, now: datetime, *, allow_bootstrap: bool = False) -> None:
        if not self.capsule and not allow_bootstrap:
            raise Invalid("complete frozen capsule binding required")
        if (
            self.delivered
            or self.split_remaining is not None
            or self.split_remaining_counts is not None
        ):
            raise Invalid("terminal ticket; explicit user decision required")
        if self.lifetime_policy == "timed-v1" and self.elapsed(now) >= self.budget_seconds:
            raise Invalid("active-time budget exhausted; stop for user decision")
        if operation == "delivery":
            if not self.clock_running:
                raise Invalid("explicit coordination resume required before delivery")
            if self.active or self.suspended or self.blockers or self.final_failed:
                raise Invalid("open phase or unresolved blocker denies delivery")
            if not self.ready or not self.verified or not self.accepted:
                raise Invalid("incomplete design, verification or acceptance")
            if (self.review_required or self.counts["initial_review"]) and not self.reviewed:
                raise Invalid("clean required review missing")
            if not self.verified_content or self.verified_content != self.acceptance_content:
                raise Invalid("verification and acceptance content differ")
            if (
                self.review_required or self.counts["initial_review"]
            ) and self.review_content != self.verified_content:
                raise Invalid("review and verified content differ")
            return
        if operation not in PHASES:
            raise Invalid("unknown phase")
        if self.active or self.suspended:
            raise Invalid("overlapping phases forbidden")
        if not self.clock_running:
            raise Invalid("explicit coordination resume required")
        if self.final_failed:
            raise Invalid("failed final review; stop for explicit finite user extension")
        if operation in self.counts and self.counts[operation] >= self.limits[operation]:
            raise Invalid(f"{operation} lifetime limit exhausted; stop for user decision")
        if operation == "design" and self.design_started:
            raise Invalid("subsequent architecture work must reserve a design_reset slot")
        if operation == "challenge" and (not self.design_session or self.challenge_session):
            raise Invalid("one independent challenge per completed design; reset required")
        if (
            operation
            in {
                "implementation",
                "remediation",
                "verification",
                "initial_review",
                "final_review",
            }
            and not self.ready
        ):
            raise Invalid("approved DESIGN_READY required")
        if operation == "initial_review" and not self.author_session:
            raise Invalid("implementation has not completed")
        if operation == "remediation" and not self.initial_failed:
            raise Invalid("remediation requires initial review findings")
        if operation == "final_review" and not self.remediated:
            raise Invalid("final review requires completed remediation")


def replay(value: dict, now: datetime, *, predecessors: dict[int, dict] | None = None) -> State:
    value = load(json.dumps(value, allow_nan=False))
    state = None
    previous = None
    bootstrap = (
        len(value["events"]) >= BOOTSTRAP_EVENTS
        and digest({"schema": 1, "events": value["events"][:BOOTSTRAP_EVENTS]}) == BOOTSTRAP_DIGEST
    )
    for index, event in enumerate(value["events"]):
        event = keys(event, {"type", "at", "data"})
        at = timestamp(event["at"])
        if at > now or (previous and at < previous):
            raise Invalid("future or backwards event time")
        previous = at
        kind, data = event["type"], event["data"]
        if state is not None:
            if state.delivered or (
                (state.split_remaining is not None or state.split_remaining_counts is not None)
                and kind not in {"split", "cycle_split"}
            ):
                raise Invalid("terminal history cannot be reopened")
            state.elapsed_seconds = state.elapsed(at)
            state.last = at
        if index == 0:
            if kind != "initialize":
                raise Invalid("initialization must be first")
            initial_fields = {
                "repo",
                "issue",
                "classification",
                "scope",
                "invariants",
                "acceptance",
                "review_required",
                "authority",
                "adoption",
                "predecessor",
            }
            expected = initial_fields if bootstrap else initial_fields | {"capsule"}
            if "lifetime_policy" in data:
                expected = expected | {"lifetime_policy"}
            data = keys(data, expected)
            repo = text(data["repo"])
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
                raise Invalid("invalid repository identity")
            issue = integer(data["issue"], 1)
            classification = data["classification"]
            if classification not in {
                "mechanical",
                "ordinary",
                "consequential",
                "high-risk/disputed",
                "difficult",
            }:
                raise Invalid("invalid classification")
            scope = identifiers(data["scope"])
            if type(data["review_required"]) is not bool:
                raise Invalid("review_required must be boolean")
            if (
                classification in {"consequential", "high-risk/disputed"}
                and not data["review_required"]
            ):
                raise Invalid("classification requires independent review")
            authority(data["authority"], "coordinator")
            state = State(
                repo,
                issue,
                classification,
                identifiers(data["acceptance"]),
                identifiers(data["invariants"]),
                data["review_required"],
            )
            state.scope = scope
            state.lifetime_policy = data.get("lifetime_policy", "timed-v1")
            if state.lifetime_policy not in POLICIES:
                raise Invalid("unknown lifetime policy")
            if not bootstrap:
                if data["adoption"] is not None:
                    raise Invalid(
                        "future adoption forbidden; only approved Issue73 bootstrap exists"
                    )
                state.capsule = capsule(data["capsule"], state)
                if state.capsule["generation"] != 1:
                    raise Invalid("future initialization starts at capsule generation one")
                state.approved_owner = state.capsule["owner"]
            if data["adoption"] is not None:
                adoption = keys(data["adoption"], {"from", "phases", "evidence"})
                start = timestamp(adoption["from"])
                if start > at:
                    raise Invalid("adoption starts after initialization")
                text(adoption["evidence"])
                if not isinstance(adoption["phases"], list) or not adoption["phases"]:
                    raise Invalid("adoption must name known completed phases")
                state.elapsed_seconds = int((at - start).total_seconds())
                for phase in adoption["phases"]:
                    phase = keys(phase, {"phase", "session", "outcome"})
                    if phase["phase"] not in PHASES or phase["outcome"] != "pass":
                        raise Invalid("adopt only known successful phases; failures require events")
                    session = text(phase["session"])
                    state.sessions[session] = next(iter(ROLES[phase["phase"]]))
                    if phase["phase"] in state.counts:
                        state.counts[phase["phase"]] += 1
                    completed(state, phase["phase"], session, "pass")
            if data["predecessor"] is not None:
                pred = keys(data["predecessor"], {"issue", "digest"})
                pred_issue = integer(pred["issue"], 1)
                if pred_issue == issue or not predecessors or pred_issue not in predecessors:
                    raise Invalid("explicit predecessor validation required")
                history = predecessors[pred_issue]
                prefixes = [
                    {"schema": 1, "events": history["events"][:end]}
                    for end in range(1, len(history["events"]) + 1)
                ]
                parent = next(
                    (item for item in prefixes if digest(item) == text(pred["digest"])), None
                )
                if parent is None:
                    raise Invalid("predecessor digest mismatch")
                parent_state = replay(
                    parent,
                    at,
                    predecessors={k: v for k, v in predecessors.items() if k != pred_issue},
                )
                if parent_state.repo != repo or issue not in parent_state.splits:
                    raise Invalid("predecessor did not allocate this successor")
                allocation = parent_state.splits[issue]
                if allocation.get("policy", "timed-v1") != state.lifetime_policy:
                    raise Invalid("successor lifetime policy differs from allocation")
                if state.lifetime_policy == "timed-v1":
                    state.budget_seconds = allocation["seconds"]
                state.counts = allocation["counts"].copy()
                state.limits = allocation["limits"].copy()
                state.extension_authorizations = set(allocation["extensions"])
                state.write_authors = set(allocation["authors"])
                state.sessions = allocation["sessions"].copy()
                if data["adoption"] is not None:
                    raise Invalid("successor cannot also adopt history")
            if any(state.counts[k] > state.limits[k] for k in COUNTS):
                raise Invalid("adoption exceeds phase limits")
        elif state is None:
            raise Invalid("missing state")
        elif kind == "capsule_binding":
            data = keys(data, {"authority", "prefix_digest", "capsule"})
            authority(data["authority"], "coordinator")
            if (
                not bootstrap
                or index != BOOTSTRAP_EVENTS
                or state.capsule
                or data["prefix_digest"] != BOOTSTRAP_DIGEST
            ):
                raise Invalid("capsule binding is restricted to approved historical Issue73 prefix")
            if data["authority"] != {
                "kind": "coordinator",
                "name": "/root",
                "evidence": BOOTSTRAP_APPROVAL,
            }:
                raise Invalid("bootstrap authority differs from approved adoption")
            state.capsule = capsule(data["capsule"], state)
            if state.capsule["generation"] != 1 or state.capsule["owner"] != {
                "role": "implementation_worker",
                "model": "gpt-6-sol",
                "effort": "medium",
                "session": "/root/bounded_workflow_implementation",
            }:
                raise Invalid(
                    "historical bootstrap owner/generation differs from known approved session"
                )
            state.approved_owner = state.capsule["owner"]
            state.design_ref = state.challenge_ref = state.approved_ref = capsule_ref(state.capsule)
            state.accepted = state.verified = state.reviewed = False
            if state.active:
                state.active["capsule"] = capsule_ref(state.capsule)
        elif kind == "phase_start":
            historical = bootstrap and index < BOOTSTRAP_EVENTS
            expected = {"phase", "session", "role"}
            if not historical:
                expected.add("capsule")
                if data.get("phase") in {"initial_review", "final_review", "verification"}:
                    expected.add("content")
            data = keys(data, expected)
            phase, session = text(data["phase"]), text(data["session"])
            state.gate(phase, at, allow_bootstrap=historical)
            if not historical:
                require_capsule(data["capsule"], state)
                if "content" in data:
                    sha(data["content"])
            if data["role"] not in ROLES[phase]:
                raise Invalid("phase role mismatch")
            if phase == "design_reset" and session in state.sessions:
                raise Invalid("design reset requires a fresh architect session")
            if session in state.sessions and state.sessions[session] != data["role"]:
                raise Invalid("role change requires a fresh separate session")
            state.sessions[session] = data["role"]
            if phase in {"challenge", "initial_review", "final_review"} and session in {
                state.design_session,
                *state.write_authors,
            }:
                raise Invalid("independent read-only session required")
            if phase in {"implementation", "remediation", "verification"} and session in {
                state.design_session,
                state.challenge_session,
            }:
                raise Invalid("separate write-capable session required")
            if phase in {"implementation", "remediation", "verification"}:
                if not historical and (data["role"], session) != (
                    state.approved_owner["role"],
                    state.approved_owner["session"],
                ):
                    raise Invalid("write phase differs from classification and approved owner")
                if not historical and state.approved_ref != capsule_ref(state.capsule):
                    raise Invalid("approved capsule generation differs from write phase")
                state.write_authors.add(session)
            if phase in state.counts:
                state.counts[phase] += 1
            if phase == "design_reset":
                state.ready = state.challenge_ok = False
                state.challenge_session = None
                state.design_session = None
                state.design_ref = state.challenge_ref = state.approved_ref = None
                if state.capsule:
                    state.capsule = {**state.capsule, "generation": state.capsule["generation"] + 1}
                    data = {**data, "capsule": capsule_ref(state.capsule)}
            if phase == "design":
                state.design_started = True
            if phase in {"implementation", "remediation", "design_reset"}:
                state.accepted = state.verified = state.reviewed = False
            state.active = {**data, "at": event["at"]}
        elif kind == "capsule_update":
            data = keys(data, {"authority", "capsule"})
            authority(data["authority"], "coordinator")
            if not state.active or state.active["phase"] != "design_reset" or not state.capsule:
                raise Invalid("capsule revision requires reserved active design reset")
            revised = capsule(data["capsule"], state)
            for key in (
                "id",
                "generation",
                "classification",
                "scope",
                "non_goals",
                "invariants",
                "acceptance",
                "owner",
            ):
                if revised[key] != state.capsule[key]:
                    raise Invalid("reset cannot change frozen scope, definitions or ownership")
            state.capsule = revised
            state.active["capsule"] = capsule_ref(revised)
        elif kind == "owner_handoff":
            data = keys(data, {"authority", "owner", "capsule", "reason", "escalation"})
            authority(data["authority"], "coordinator")
            require_capsule(data["capsule"], state)
            text(data["reason"])
            selected = owner(data["owner"])
            if state.active or state.suspended or selected["session"] in state.sessions:
                raise Invalid("owner handoff requires fresh separate sequential session")
            if selected["role"] != state.approved_owner["role"]:
                if selected["role"] != "implementation_specialist":
                    raise Invalid(
                        "owner role change requires classified design or specialist escalation"
                    )
                escalation(data["escalation"])
            elif data["escalation"] is not None:
                raise Invalid("same-role handoff does not change escalation")
            state.approved_owner = selected
        elif kind == "phase_resume":
            data = keys(data, {"session"})
            if state.active or not state.suspended or data["session"] != state.suspended["session"]:
                raise Invalid("no matching interrupted session")
            if (
                (state.lifetime_policy == "timed-v1" and state.elapsed(at) >= state.budget_seconds)
                or state.delivered
                or state.split_remaining is not None
                or state.split_remaining_counts is not None
            ):
                raise Invalid("resume budget exhausted or terminal ticket")
            state.active = {**state.suspended, "at": event["at"]}
            state.suspended = None
            state.clock_running = True
        elif kind in {"phase_end", "pause"}:
            data = keys(data, {"session", "outcome", "evidence"})
            text(data["evidence"])
            if not state.active or data["session"] != state.active["session"]:
                raise Invalid("no matching active session")
            if data["outcome"] not in {"pass", "fail", "interrupted"}:
                raise Invalid("invalid phase outcome")
            if kind == "pause" and data["outcome"] != "interrupted":
                raise Invalid("pause must be interrupted")
            phase = state.active["phase"]
            state.elapsed_seconds = state.elapsed(at)
            if data["outcome"] == "interrupted":
                state.suspended = state.active.copy()
                state.clock_running = False
            else:
                completed(state, phase, data["session"], data["outcome"])
            state.active = None
        elif kind in {"coordination_pause", "coordination_resume"}:
            data = keys(data, {"authority", "evidence"})
            authority(data["authority"], "coordinator")
            text(data["evidence"])
            if (
                state.active
                or state.suspended
                or state.delivered
                or state.split_remaining is not None
                or state.split_remaining_counts is not None
            ):
                raise Invalid("coordination pause/resume requires nonterminal between-phase state")
            running = kind == "coordination_resume"
            if state.clock_running == running:
                raise Invalid("duplicate coordination pause/resume")
            if (
                running
                and state.lifetime_policy == "timed-v1"
                and state.elapsed(at) >= state.budget_seconds
            ):
                raise Invalid("coordination resume budget exhausted")
            state.clock_running = running
        elif kind == "design_ready":
            historical = bootstrap and index < BOOTSTRAP_EVENTS
            data = keys(
                data,
                {"authority", "evidence"} if historical else {"authority", "evidence", "capsule"},
            )
            authority(data["authority"], "coordinator")
            text(data["evidence"])
            if (
                state.active
                or state.suspended
                or (
                    not state.design_session
                    and (state.classification == "consequential" or state.design_started)
                )
            ):
                raise Invalid("completed separate design required")
            if state.classification == "consequential" and not state.challenge_ok:
                raise Invalid("unresolved consequential design challenge")
            if not historical:
                require_capsule(data["capsule"], state)
                if state.classification == "consequential" and (
                    state.design_ref != data["capsule"] or state.challenge_ref != data["capsule"]
                ):
                    raise Invalid("design/challenge/approval must bind current capsule")
                state.approved_ref = data["capsule"]
            state.ready = True
        elif kind == "acceptance":
            historical = bootstrap and index < BOOTSTRAP_EVENTS
            data = keys(
                data,
                {"ids", "evidence"} if historical else {"ids", "evidence", "capsule", "content"},
            )
            if set(identifiers(data["ids"])) != set(state.acceptance):
                raise Invalid("incomplete frozen acceptance")
            text(data["evidence"])
            if state.active or not state.author_session:
                raise Invalid("acceptance requires completed implementation")
            if not historical:
                require_capsule(data["capsule"], state)
                state.acceptance_content = sha(data["content"])
            state.accepted = True
        elif kind == "blocker":
            data = keys(data, {"id", "criterion", "scenario", "evidence"})
            ident = text(data["id"])
            if ident in state.blockers or data["criterion"] not in {
                *state.acceptance,
                *state.invariants,
            }:
                raise Invalid("duplicate blocker or unfrozen criterion")
            text(data["scenario"])
            text(data["evidence"])
            required_remediation = state.counts["remediation"]
            if not state.active or state.active["phase"] != "remediation":
                required_remediation += 1
            state.blockers[ident] = {**data, "required_remediation": required_remediation}
        elif kind == "resolve":
            data = keys(data, {"id", "evidence"})
            text(data["evidence"])
            if data["id"] not in state.blockers or state.active:
                raise Invalid("unknown blocker or active phase")
            if (
                not state.remediated
                or state.counts["remediation"] < state.blockers[data["id"]]["required_remediation"]
            ):
                raise Invalid("blocker resolution requires completed remediation evidence")
            del state.blockers[data["id"]]
        elif kind == "policy_transition":
            data = keys(
                data,
                {"authority", "from", "to", "prefix_digest", "reason", "time_blocker_waivers"},
            )
            authority(data["authority"], "user")
            authorization = evidence_key(data["authority"]["evidence"])
            if authorization in state.extension_authorizations:
                raise Invalid("policy authorization already consumed")
            text(data["reason"])
            if (
                data["from"] != "timed-v1"
                or data["to"] != "cycles-v1"
                or state.lifetime_policy != "timed-v1"
                or state.delivered
                or state.split_remaining is not None
                or state.split_remaining_counts is not None
                or data["prefix_digest"] != digest({"schema": 1, "events": value["events"][:index]})
            ):
                raise Invalid("invalid or stale policy transition")
            waivers = data["time_blocker_waivers"]
            if (
                not isinstance(waivers, list)
                or any(not isinstance(item, str) for item in waivers)
                or len(waivers) != len(set(waivers))
            ):
                raise Invalid("invalid time blocker waivers")
            for ident in waivers:
                if (
                    ident != "B83-EXHAUSTED"
                    or state.repo != "beagle1903/agentic-etf-advisor"
                    or state.issue != 83
                    or ident not in state.blockers
                    or not any(
                        item["type"] == "blocker" and digest(item) == ISSUE83_BLOCKER_DIGEST
                        for item in value["events"][:index]
                    )
                ):
                    raise Invalid("unapproved time blocker waiver")
                del state.blockers[ident]
            if value["events"][0]["data"].get("predecessor") is not None:
                sole_legacy_lineage(value, predecessors)
            state.lifetime_policy = "cycles-v1"
            state.extension_authorizations.add(authorization)
        elif kind == "extension":
            data = keys(data, {"authority", "seconds", "counts", "reason"})
            authority(data["authority"], "user")
            authorization = evidence_key(data["authority"]["evidence"])
            if authorization in state.extension_authorizations:
                raise Invalid("finite extension authorization already consumed")
            text(data["reason"])
            seconds = integer(data["seconds"])
            counts = keys(data["counts"], set(COUNTS))
            deltas = {k: integer(v) for k, v in counts.items()}
            if (
                state.active
                or state.delivered
                or state.split_remaining is not None
                or state.split_remaining_counts is not None
                or not (seconds or any(deltas.values()))
            ):
                raise Invalid("invalid extension or terminal/active ticket")
            if state.lifetime_policy == "cycles-v1" and (seconds or not any(deltas.values())):
                raise Invalid("cycle extension requires zero seconds and positive count delta")
            state.budget_seconds += seconds
            state.extension_authorizations.add(authorization)
            for phase, delta in deltas.items():
                state.limits[phase] += delta
            if state.final_failed:
                if not deltas["final_review"] or not deltas["remediation"]:
                    raise Invalid(
                        "failed final review extension must bound remediation and final review"
                    )
                state.final_failed = False
                state.remediated = False
        elif kind == "charge":
            data = keys(data, {"authority", "seconds", "evidence"})
            authority(data["authority"], "coordinator")
            text(data["evidence"])
            state.elapsed_seconds += integer(data["seconds"], 1)
        elif kind == "split":
            if state.lifetime_policy != "timed-v1":
                raise Invalid("timed split forbidden for cycle policy")
            data = keys(data, {"authority", "successor", "seconds", "reason"})
            authority(data["authority"], "user")
            text(data["reason"])
            successor, seconds = integer(data["successor"], 1), integer(data["seconds"], 1)
            if (
                state.active
                or state.delivered
                or successor == state.issue
                or successor in state.splits
            ):
                raise Invalid("invalid split")
            if state.split_remaining is None:
                state.split_remaining = max(0, state.budget_seconds - state.elapsed(at))
                state.clock_running = False
            if seconds > state.split_remaining:
                raise Invalid("successor allocations exceed remaining budget")
            state.split_remaining -= seconds
            state.splits[successor] = {
                "policy": "timed-v1",
                "seconds": seconds,
                "counts": state.counts.copy(),
                "limits": state.limits.copy(),
                "extensions": sorted(state.extension_authorizations),
                "authors": sorted(state.write_authors),
                "sessions": state.sessions.copy(),
            }
        elif kind == "cycle_split":
            data = keys(data, {"authority", "successor", "remaining_counts", "reason"})
            authority(data["authority"], "user")
            authorization = evidence_key(data["authority"]["evidence"])
            if authorization in state.extension_authorizations:
                raise Invalid("cycle allocation authorization already consumed")
            text(data["reason"])
            successor = integer(data["successor"], 1)
            allocation = keys(data["remaining_counts"], set(COUNTS))
            allocation = {key: integer(value) for key, value in allocation.items()}
            if state.lifetime_policy != "cycles-v1" or not any(allocation.values()):
                raise Invalid("cycle split requires positive attempt allocation")
            if (
                state.active
                or state.suspended
                or state.delivered
                or state.split_remaining is not None
                or successor == state.issue
                or successor in state.splits
            ):
                raise Invalid("invalid cycle split")
            if state.split_remaining_counts is None:
                state.split_remaining_counts = {
                    key: state.limits[key] - state.counts[key] for key in COUNTS
                }
                state.clock_running = False
            if any(allocation[key] > state.split_remaining_counts[key] for key in COUNTS):
                raise Invalid("successor allocations exceed remaining attempts")
            for key in COUNTS:
                state.split_remaining_counts[key] -= allocation[key]
            state.extension_authorizations.add(authorization)
            state.splits[successor] = {
                "policy": "cycles-v1",
                "counts": state.counts.copy(),
                "limits": {key: state.counts[key] + allocation[key] for key in COUNTS},
                "extensions": sorted(state.extension_authorizations),
                "authors": sorted(state.write_authors),
                "sessions": state.sessions.copy(),
            }
        elif kind == "delivery":
            data = keys(data, {"evidence", "pr", "repo", "content", "capsule"})
            text(data["evidence"])
            integer(data["pr"], 1)
            require_capsule(data["capsule"], state)
            if data["repo"] != state.repo or sha(data["content"]) != state.verified_content:
                raise Invalid("delivery identity/content mismatch")
            state.gate("delivery", at)
            state.delivered = True
            state.delivery_binding = {
                "pr": data["pr"],
                "repo": data["repo"],
                "content": data["content"],
            }
            state.clock_running = False
        else:
            raise Invalid("unknown or repeated initialization event")
        state.last = at
    assert state is not None
    state.elapsed(now)
    return state


def completed(state: State, phase: str, session: str, outcome: str) -> None:
    if phase in {"design", "design_reset"}:
        if outcome == "pass":
            state.design_session = session
            state.design_started = True
            state.design_ref = state.active.get("capsule") if state.active else None
    elif phase == "challenge":
        state.challenge_session = session
        state.challenge_ok = outcome == "pass" and session != state.design_session
        state.challenge_ref = (
            state.active.get("capsule") if outcome == "pass" and state.active else None
        )
    elif phase == "implementation" and outcome == "pass":
        state.author_session = session
    elif phase == "verification":
        state.verified = outcome == "pass"
        state.verified_content = (
            state.active.get("content") if outcome == "pass" and state.active else None
        )
    elif phase == "initial_review":
        state.reviewed = outcome == "pass"
        state.initial_failed = outcome != "pass"
        state.review_content = (
            state.active.get("content") if outcome == "pass" and state.active else None
        )
    elif phase == "remediation":
        state.remediated = outcome == "pass"
    elif phase == "final_review":
        state.reviewed = outcome == "pass"
        state.final_failed = outcome != "pass"
        state.review_content = (
            state.active.get("content") if outcome == "pass" and state.active else None
        )


def read_all(root: Path) -> dict[int, dict]:
    ledgers = {}
    for path in sorted((root / DIRECTORY).glob("*.json")):
        value = load(path.read_text(encoding="utf-8"))
        first = keys(value["events"][0], {"type", "at", "data"})
        if not isinstance(first["data"], dict):
            raise Invalid("initialization data must be an object")
        issue = integer(first["data"].get("issue"), 1)
        if path.name != f"issue-{issue}.json" or issue in ledgers:
            raise Invalid("duplicate or misnamed issue ledger")
        ledgers[issue] = value
    return ledgers


def content_digest(root: Path, issue: int, ref: str | None = None) -> str:
    """Canonical Git content, excluding only this ticket's mutable ledger/lock/temp files."""
    excluded = f"{DIRECTORY.as_posix()}/issue-{issue}.json"
    prefix = f"{DIRECTORY.as_posix()}/"

    def include(path: str) -> bool:
        return path != excluded and not (
            path.startswith(prefix) and (path.endswith(".lock") or path.endswith(".tmp"))
        )

    records = []
    if ref is None:
        names = (
            subprocess.check_output(
                ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root
            )
            .decode()
            .split("\0")
        )
        staged = (
            subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root)
            .decode()
            .split("\0")
        )
        modes = {item.split("\t", 1)[1]: item.split()[0] for item in staged if item}
        for name in sorted(set(names) - {""}):
            if not include(name):
                continue
            path = root / name
            if not path.exists():
                continue
            data = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            if b"\0" not in data[:8000]:
                data = data.replace(b"\r\n", b"\n")
            mode = modes.get(name, "120000" if path.is_symlink() else "100644")
            records.append((name, mode, hashlib.sha256(data).hexdigest()))
    else:
        listing = (
            subprocess.check_output(["git", "ls-tree", "-r", "-z", ref], cwd=root)
            .decode()
            .split("\0")
        )
        entries = [
            (item.split("\t", 1)[1], *item.split("\t", 1)[0].split()) for item in listing if item
        ]
        entries = [
            (name, mode, obj)
            for name, mode, kind, obj in entries
            if include(name) and kind == "blob"
        ]
        raw = subprocess.check_output(
            ["git", "cat-file", "--batch"],
            cwd=root,
            input="".join(obj + "\n" for _, _, obj in entries).encode(),
        )
        position = 0
        for name, mode, _ in entries:
            end = raw.index(b"\n", position)
            size = int(raw[position:end].split()[-1])
            data = raw[end + 1 : end + 1 + size]
            position = end + size + 2
            records.append((name, mode, hashlib.sha256(data).hexdigest()))
    return digest(sorted(records))


def validate_all(root: Path, now: datetime) -> dict[int, dict]:
    ledgers = read_all(root)
    validate_ledgers(ledgers, now)
    return ledgers


def validate_ledgers(ledgers: dict[int, dict], now: datetime) -> None:
    """Validate histories and their actual predecessor links before family checks."""
    for issue, value in ledgers.items():
        others = {k: v for k, v in ledgers.items() if k != issue}
        state = replay(value, now, predecessors=others)
        if (
            state.lifetime_policy == "cycles-v1"
            and value["events"][0]["data"].get("predecessor")
            and value["events"][0]["data"].get("lifetime_policy") != "cycles-v1"
        ):
            sole_legacy_lineage(value, others)
    validate_lineage_authorizations(ledgers)


def validate_lineage_authorizations(ledgers: dict[int, dict]) -> None:
    """Cycle approvals cannot reuse any split approval in their validated family."""
    roots: dict[int, int] = {}

    def root(issue: int, visiting: set[int]) -> int:
        if issue in roots:
            return roots[issue]
        if issue in visiting:
            raise Invalid("cyclic ticket predecessor")
        visiting.add(issue)
        predecessor = ledgers[issue]["events"][0]["data"].get("predecessor")
        ancestor = predecessor["issue"] if predecessor else None
        if ancestor is not None and ancestor not in ledgers:
            raise Invalid("missing ticket predecessor")
        roots[issue] = root(ancestor, visiting) if ancestor is not None else issue
        visiting.remove(issue)
        return roots[issue]

    timed_splits: set[tuple[int, str]] = set()
    used: set[tuple[int, str]] = set()
    for issue, value in ledgers.items():
        family = root(issue, set())
        policy = value["events"][0]["data"].get("lifetime_policy", "timed-v1")
        for event in value["events"]:
            kind = event["type"]
            if kind == "policy_transition":
                policy = "cycles-v1"
            if kind == "split":
                approval = evidence_key(event["data"]["authority"]["evidence"])
                timed_splits.add((family, approval))
            if (
                kind == "cycle_split"
                or kind == "policy_transition"
                or (kind == "extension" and policy == "cycles-v1")
            ):
                approval = evidence_key(event["data"]["authority"]["evidence"])
                identity = (family, approval)
                if identity in used:
                    raise Invalid("cycle lineage authorization already consumed")
                used.add(identity)
    if used & timed_splits:
        raise Invalid("timed split authorization already consumed in cycle lineage")


def append(root: Path, issue: int, event: dict, now: datetime) -> State:
    """One writer, lock, validate candidate, atomic replace; never rewrite prior events."""
    path = root / DIRECTORY / f"issue-{integer(issue, 1)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise Invalid("another writer or abandoned lock; coordinator must inspect") from exc
    try:
        os.close(fd)
        ledgers = read_all(root)
        value = ledgers.get(issue, {"schema": 1, "events": []})
        if (
            not value["events"]
            and event.get("type") == "initialize"
            and event.get("data", {}).get("lifetime_policy") != "cycles-v1"
        ):
            raise Invalid("new initialization requires cycles-v1 lifetime policy")
        if (
            event.get("type") == "phase_start"
            and event.get("data", {}).get("phase")
            in {
                "initial_review",
                "final_review",
                "verification",
            }
            and event["data"].get("content") != content_digest(root, issue)
        ):
            raise Invalid("phase reservation does not match current repository content")
        if event.get("type") in {"phase_end", "acceptance", "delivery"} and value["events"]:
            prior = replay(
                value, now, predecessors={k: v for k, v in ledgers.items() if k != issue}
            )
            expected = event.get("data", {}).get("content")
            if (
                event["type"] == "phase_end"
                and event.get("data", {}).get("outcome") == "pass"
                and prior.active
                and prior.active["phase"] in {"initial_review", "final_review", "verification"}
            ):
                expected = prior.active.get("content")
            if expected is not None and expected != content_digest(root, issue):
                raise Invalid("repository content changed after recorded verification/review")
        candidate = {"schema": 1, "events": [*value["events"], event]}
        state = replay(
            candidate, now, predecessors={k: v for k, v in ledgers.items() if k != issue}
        )
        if state.issue != issue:
            raise Invalid("requested issue differs from initialized issue")
        validate_ledgers({**ledgers, issue: candidate}, now)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
        ) as target:
            target.write(json.dumps(candidate, indent=2, allow_nan=False) + "\n")
            target.flush()
            os.fsync(target.fileno())
            temp = Path(target.name)
        try:
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        return state
    finally:
        lock.unlink(missing_ok=True)


def approved_legacy_23_83(
    ledgers: dict[int, dict], originals: dict[int, dict], primary: int | None
) -> bool:
    """Allow only the exact unmerged design/successor pair on Issue83's PR."""
    if primary != 83 or 23 in originals or 83 in originals:
        return False
    parent, child = ledgers.get(23), ledgers.get(83)
    if parent is None or child is None:
        return False
    if (
        len(parent["events"]) != 10
        or digest(parent) != ISSUE23_COMPLETE_DIGEST
        or len(child["events"]) < 10
        or digest({"schema": 1, "events": child["events"][:9]}) != ISSUE83_LEGACY_DIGEST
    ):
        return False
    first_parent, first_child = parent["events"][0]["data"], child["events"][0]["data"]
    if (
        any(
            initial.get("repo") != "beagle1903/agentic-etf-advisor"
            for initial in (first_parent, first_child)
        )
        or first_parent.get("issue") != 23
        or first_child.get("issue") != 83
    ):
        return False
    transition = child["events"][9]
    if transition.get("type") != "policy_transition" or not isinstance(
        transition.get("data"), dict
    ):
        return False
    data = transition["data"]
    if (
        data.get("from") != "timed-v1"
        or data.get("to") != "cycles-v1"
        or data.get("prefix_digest") != ISSUE83_LEGACY_DIGEST
        or data.get("time_blocker_waivers") != ["B83-EXHAUSTED"]
    ):
        return False
    try:
        replay(child, timestamp(child["events"][-1]["at"]), predecessors={23: parent})
    except (Invalid, KeyError, TypeError, ValueError):
        return False
    return True


def check_prefix(
    root: Path, base: str, ledgers: dict[int, dict], primary: int | None = None
) -> set[int]:
    merge_base = subprocess.check_output(
        ["git", "merge-base", base, "HEAD"], cwd=root, text=True
    ).strip()
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", merge_base, str(DIRECTORY).replace("\\", "/")],
        cwd=root,
        text=True,
    ).splitlines()
    originals = {}
    for name in files:
        if not name.endswith(".json"):
            continue
        old = load(
            subprocess.check_output(["git", "show", f"{merge_base}:{name}"], cwd=root, text=True)
        )
        issue = old["events"][0]["data"]["issue"]
        originals[issue] = old
        current = ledgers.get(issue)
        if current is None or current["events"][: len(old["events"])] != old["events"]:
            raise Invalid("merge-base ledger history edited or deleted")
    legacy_pair = approved_legacy_23_83(ledgers, originals, primary)
    for issue, value in ledgers.items():
        if issue not in originals:
            initial = value["events"][0]
            if initial["data"].get("lifetime_policy") != "cycles-v1":
                approved_84 = (
                    issue == 84
                    and primary == 84
                    and initial["data"].get("repo") == "beagle1903/agentic-etf-advisor"
                    and digest({"schema": 1, "events": [initial]}) == ISSUE84_INITIAL_DIGEST
                    and value["events"][0]["data"]["issue"] == 84
                )
                if not approved_84 and not (legacy_pair and issue in {23, 83}):
                    raise Invalid("new ledger introduction requires cycles-v1 policy")
    return {issue for issue, value in ledgers.items() if originals.get(issue) != value}


def primary_issue(body: str) -> int:
    matches = re.findall(r"^Primary issue: #([1-9][0-9]*)\s*$", body, re.MULTILINE)
    if len(matches) != 1:
        raise Invalid("PR must contain exactly one Primary issue: #N line")
    return integer(int(matches[0]), 1)


def check_pr(
    event: dict,
    ledgers: dict[int, dict],
    created_at: str,
    now: datetime,
    changed: set[int] | None = None,
    content: str | None = None,
) -> str:
    pr = event["pull_request"]
    if timestamp(pr["created_at"]) < timestamp(ADOPTION) and not re.search(
        r"^Primary issue:", pr.get("body") or "", re.MULTILINE
    ):
        if changed:
            raise Invalid("changed ledger requires primary issue binding")
        return "Historical PR exempt; no retroactive ledger adoption."
    issue = primary_issue(pr.get("body") or "")
    if changed and issue not in changed:
        raise Invalid("primary issue does not match changed ledger")
    if issue not in ledgers:
        if timestamp(created_at) < timestamp(ADOPTION) and issue != 73:
            return "Historical issue exempt; no retroactive ledger adoption."
        raise Invalid("primary issue ledger missing")
    state = replay(
        ledgers[issue], now, predecessors={k: v for k, v in ledgers.items() if k != issue}
    )
    if state.repo != event["repository"]["full_name"]:
        raise Invalid("PR repository differs from ledger")
    actual_content = sha(content)
    if not state.delivered:
        raise Invalid("primary issue requires a recorded delivery event")
    if state.delivery_binding != {
        "pr": integer(event["number"], 1),
        "repo": state.repo,
        "content": actual_content,
    }:
        raise Invalid("delivered ledger belongs to another PR or different content")
    return "Primary issue delivery gate passed against recorded evidence."


def current_pr(event: dict, metadata: dict) -> dict:
    """Reject stale queued head/base identity before validating the live PR body."""
    recorded = event["pull_request"]
    if (
        metadata.get("number") != event["number"]
        or metadata["head"]["sha"] != recorded["head"]["sha"]
    ):
        raise Invalid("queued PR event has stale head or identity")
    for key in ("sha", "ref"):
        if text(metadata["base"][key]) != text(recorded["base"][key]):
            raise Invalid("queued PR event has stale base SHA or ref")
    if text(metadata["base"]["repo"]["full_name"]) != text(recorded["base"]["repo"]["full_name"]):
        raise Invalid("queued PR event has stale base repository")
    return {**event, "pull_request": {**recorded, "body": metadata.get("body")}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "check", "append", "ci", "status"])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--issue", type=int)
    parser.add_argument("--phase", default="delivery")
    parser.add_argument("--event", type=Path)
    parser.add_argument("--base")
    parser.add_argument("--now", default=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    args = parser.parse_args()
    try:
        now = timestamp(args.now)
        if args.command == "append":
            if args.issue is None or args.event is None:
                raise Invalid("append requires --issue and --event")
            event = json.loads(args.event.read_text(encoding="utf-8"), object_pairs_hook=unique)
            append(args.root, args.issue, event, now)
        else:
            ledgers = validate_all(args.root, now)
            changed = (
                check_prefix(args.root, args.base, ledgers)
                if args.base and args.command != "ci"
                else set()
            )
            if args.command in {"check", "status"}:
                if args.issue not in ledgers:
                    raise Invalid("requested issue ledger missing")
                state = replay(
                    ledgers[args.issue],
                    now,
                    predecessors={k: v for k, v in ledgers.items() if k != args.issue},
                )
                if args.command == "status":
                    print(
                        json.dumps(
                            {
                                "capsule": capsule_ref(state.capsule) if state.capsule else None,
                                "content": content_digest(args.root, args.issue),
                                "owner": state.approved_owner,
                                "counts": state.counts,
                                "limits": state.limits,
                                "remaining_counts": {
                                    key: state.limits[key] - state.counts[key] for key in COUNTS
                                },
                                "lifetime_policy": state.lifetime_policy,
                                "remaining_seconds": (
                                    state.budget_seconds - state.elapsed(now)
                                    if state.lifetime_policy == "timed-v1"
                                    else None
                                ),
                                "audit_elapsed_seconds": state.elapsed(now),
                                "active_phase": state.active["phase"] if state.active else None,
                                "suspended_phase": state.suspended["phase"]
                                if state.suspended
                                else None,
                                "blockers": sorted(state.blockers),
                                "verified": state.verified,
                                "reviewed": state.reviewed,
                            },
                            indent=2,
                        )
                    )
                    return
                state.gate(args.phase, now)
                if args.phase == "delivery" and state.verified_content != content_digest(
                    args.root, args.issue
                ):
                    raise Invalid("current content differs from verified delivery content")
            elif args.command == "ci":
                if args.event is None or not args.base:
                    raise Invalid("ci requires --event and --base")
                event = json.loads(args.event.read_text(encoding="utf-8"))
                repo = event["repository"]["full_name"]
                token = os.environ.get("GITHUB_TOKEN", "")
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                }
                request = urllib.request.Request(
                    f"https://api.github.com/repos/{repo}/pulls/{event['number']}", headers=headers
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    event = current_pr(event, json.load(response))
                if args.base != event["pull_request"]["base"]["sha"]:
                    raise Invalid("prefix base differs from validated PR base SHA")
                body = event["pull_request"].get("body") or ""
                primary = (
                    primary_issue(body)
                    if re.search(r"^Primary issue:", body, re.MULTILINE)
                    else None
                )
                changed = check_prefix(
                    args.root, event["pull_request"]["base"]["sha"], ledgers, primary
                )
                historical = timestamp(event["pull_request"]["created_at"]) < timestamp(ADOPTION)
                if historical and not re.search(r"^Primary issue:", body, re.MULTILINE):
                    if changed:
                        raise Invalid("changed ledger requires primary issue binding")
                    print("Historical PR exempt; append-only ledger validation passed.")
                    return
                issue = primary_issue(body)
                request = urllib.request.Request(
                    f"https://api.github.com/repos/{repo}/issues/{issue}",
                    headers=headers,
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    metadata = json.load(response)
                if "pull_request" in metadata or metadata.get("number") != issue:
                    raise Invalid("primary reference is not the expected issue")
                print(
                    check_pr(
                        event,
                        ledgers,
                        metadata["created_at"],
                        now,
                        changed,
                        content_digest(args.root, issue, event["pull_request"]["head"]["sha"]),
                    )
                )
                return
        print("Recorded ticket workflow validation passed; no runtime kill switch is implied.")
    except (
        Invalid,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
    ) as exc:
        parser.exit(1, f"Ticket workflow blocked: {exc}\n")


if __name__ == "__main__":
    main()
