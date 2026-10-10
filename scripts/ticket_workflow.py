"""Finite development governance. Recorded evidence, never a runtime kill switch."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
import tempfile
import unicodedata
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
REMAINDER_ISSUE = 92
REMAINDER_REPO = "beagle1903/agentic-etf-advisor"
REMAINDER_MANIFEST = "a161bebe339b8c8ad97fc934896089a501d3f6756ff3102843d539c702ec6eb8"
REMAINDER_PROPOSAL = "48d4b86ce324331a5d2dbf8ae0d42254243de83f4cd329fc7f4a63c067ab8458"
REMAINDER_GRANT = "76f78ac061f9e2c69b6a3aba6e4e89f4b7875321facce3e79b3c6dbdc1f53c2d"
REMAINDER_CAPSULE = "197879ccd445194f77287455919e1f15efb5dce4366c5283a000ab6405dbeace"
REMAINDER_ARCHIVE = Path("docs/workflow/history/issue-84")
RECOVERY_ARCHIVE = Path("docs/workflow/history/issue-92-recovery-v1")
RECOVERY_STOP = "290ffe7e16d19de8c7e67df54cbf06c517e6313778a377da20877af9490a967a"
RECOVERY_BOOTSTRAP = "b43fb7a3df8e01e474aa3ebe40ccc0897d13e5dcbdc368ce524600fe75b41c2e"
RECOVERY_PROPOSAL = "2c18aaa09100b679add0d422850cb85d9aa747c90322c78874e842581c699c1b"
RECOVERY_MANIFEST = "6451c9e60e8782a88b7b5135d4acf83c46f7993dc7e143725ca15032b531d374"
RECOVERY_CLOSEOUT = "cceaadefea56843630f0156d83f7c13a0a7172c7a6fa44858d85be21ef2b7d48"
RECOVERY_GRANT = "ecba220c1e266721d5e199a8d8c5b3e0d0ae7722a2b430b182d6b4019fa369b0"
RECOVERY_FAILED_CONTENT = "a69779793820e624eb12f66f0fb6f243db7f7fc14940161b984a46ec5c6e5d4f"
RECOVERY_BLOCKER = "B92-LIVE-LEDGER-FIXTURE-DRIFT"
RECOVERY_OWNER = "/root/issue84_remainder_implementation"
RECOVERY_ORIGINAL_CAPSULE = {
    "id": "issue-84-cycle-bounded-workflow",
    "generation": 3,
    "digest": "df870f205cc3a8053c152699ce16030a1cedc518fdda0588ae16d3cbcd95fda9",
}
RECOVERY_CAPSULE_REF = {
    "id": "issue-92-issue84-remainder",
    "generation": 1,
    "digest": REMAINDER_CAPSULE,
}
PR_IDENTITY_ARCHIVE = Path("docs/workflow/history/issue-92-pr-identity-repair-v1")
PR_IDENTITY_STOP = "61532d8802dc4a19a0b2b15d5bbbb35fa5b163ebdaa92ee15fdf860789154f2e"
PR_IDENTITY_STOP_RAW = "910929a9a2d3b51bd4261d7173ff3d97cd91e253870db8f4cc24add0047094a8"
PR_IDENTITY_CONTENT = "6f985a3dd80b75e430422b3ab9c86a0793e88345af135970bbb63776bce89c87"
PR_IDENTITY_PROPOSAL = "0704db76d635bc2a3132c492e250e70bd2f03f349735e38fe8847427efd9ad4e"
PR_IDENTITY_MANIFEST = "5822263871b4914246a1e380daae766abf98c162b092dc74002c569b7af27007"
PR_IDENTITY_CLOSEOUT = "a5218d6ae86412b9699ba29f597e95069b68450acbab1e726e861d457c4adb03"
PR_IDENTITY_GRANT = "0dd602e87bd79c779877ad92cbcd4c3bfd0771b771f1522bbce68d0ae841253f"
PR_IDENTITY_INPUT = "764f7396f6e038ec87930118c421c19ea8d9df6deeef774c2b774b8a40e8d1de"
PR_IDENTITY_BLOCKER = "B92-LIVE-PR-HEAD-IDENTITY"
PR_IDENTITY_SOURCE_FILES = {
    "stop_ledger": "issue92-ledger-at-review-stop.json",
    "review_report": "independent-review-report.md",
    "review_closeout": "failed-review-closeout.json",
    "review_reservation": "initial-review-reservation.json",
    "review_start": "initial-review-start.json",
    "review_end": "initial-review-end-fail.json",
    "review_startup": "review-startup-observation.json",
    "blocked_status": "final-blocked-status.json",
    "prior_bootstrap": "eight-event-bootstrap-ledger.json",
    "prior_remediation_reservation": "remediation-reservation.json",
    "prior_remediation_end": "remediation-end-pass.json",
    "prior_blocker_resolution": "blocker-resolution.json",
    "prior_verification_reservation": "fresh-verification-reservation.json",
    "prior_verification_start": "fresh-verification-start.json",
    "prior_verification_end": "fresh-verification-end-pass.json",
    "prior_acceptance": "complete-acceptance.json",
    "preparation_start": "pr-identity-design-start.json",
}
PR_IDENTITY_VERIFICATION_FILES = (
    "after-integrity.txt",
    "after-status.json",
    "before-archive-roundtrip.txt",
    "before-status.json",
    "compose-config.log",
    "compose-config.result.txt",
    "diff-check.log",
    "diff-check.result.txt",
    "explanations-eval.log",
    "explanations-eval.result.txt",
    "mypy.log",
    "mypy.result.txt",
    "native-validator.log",
    "native-validator.result.txt",
    "pytest-full.log",
    "pytest-full.result.txt",
    "retrieval-eval.log",
    "retrieval-eval.result.txt",
    "ruff-check.log",
    "ruff-check.result.txt",
    "ruff-format.log",
    "ruff-format.result.txt",
    "static-validator.log",
    "static-validator.result.txt",
    "uv-build.log",
    "uv-build.result.txt",
)
PR_IDENTITY_CLOSEOUT_FILES = {
    "source_manifest": "source-manifest.json",
    "proposal": "design-proposal.md",
    "challenge_input": "challenge-input.json",
    "challenged_supplemental": "challenged-supplemental.json",
    "completed_supplemental": "completed-supplemental.json",
    "challenge_result": "challenge-result.json",
    "challenge_report": "challenge-result.md",
    "coordinator_decision": "coordinator-decision.json",
}
STAGE_FIXTURE_ARCHIVE = Path("docs/workflow/history/issue-92-stage-fixture-repair-v1")
STAGE_FIXTURE_STOP = "f3e67a49ac9ee5df4ed9ec6ff0fd4573c813fe3e8f6dee0329d2ba37d16ca32d"
STAGE_FIXTURE_STOP_RAW = "574af94846f38a4c5865b8c5f47141dd4bf4e53867334658a9522af73294015c"
STAGE_FIXTURE_CONTENT = "e8bffb9f4841d4af9d80c1af471d7bcde7cd786b173bf6119ac927cbe162019a"
STAGE_FIXTURE_PROPOSAL = "2fef66708e07eb7366b4f2c80360426030004ec5fae5100c442eb3c5c4b2f947"
STAGE_FIXTURE_MANIFEST = "54b6afa3afa54b2eaba81f469da285c54c7658d90c6a97abfb2855a95b4e271c"
STAGE_FIXTURE_CLOSEOUT = "9662aae856187b67bb8ba24ba4c12080aeb5f9a92d8a7dbd63c6dcbec6d3f393"
STAGE_FIXTURE_GRANT = "2009a082e76a0109fa18f2f2ba20315edbe623ead262682903b1675583278208"
STAGE_FIXTURE_INPUT = "d36cf3b360228d3b38cefd082d642691cd6346d48cff4642d5d4689b6fbdec07"
STAGE_FIXTURE_BLOCKER = "B92-LIVE-STAGE-FIXTURE-ASSUMPTION"
STAGE_FIXTURE_ANCHOR = (
    "human-approved-stage-aware-fixture-repair-2026-10-09-after-third-verification-failure"
)
STAGE_FIXTURE_SOURCE_FILES = {
    "stop_ledger": "stop-ledger.json",
    "preparation_start": "preparation-start.json",
    "before_integrity": "verification/before-integrity.json",
    "before_status": "verification/before-status.json",
    "current_status": "verification/current-status.json",
    "verification_summary": "verification/summary.json",
    "ruff_check": "verification/ruff-check.log",
    "ruff_format": "verification/ruff-format.log",
    "mypy": "verification/mypy.log",
    "pytest": "verification/pytest-full.log",
}
STAGE_FIXTURE_CLOSEOUT_FILES = PR_IDENTITY_CLOSEOUT_FILES.copy()
RECOVERY_SOURCE_FILES = {
    "stop_ledger": "issue92-ledger-at-stop.json",
    "bootstrap_ledger": "issue92-bootstrap-ledger.json",
    "failure_handoff": "issue92-verification-failure-handoff.md",
    "original_reservation": "issue92-reservation.json",
    "original_dispatch": "issue92-dispatch-observation.json",
    "capacity_resume": "issue92-capacity-resume.json",
    "blocked_status": "issue92-final-blocked-status.json",
    "original_user_approval": "user-finite-approval.json",
    "recovery_start": "recovery-design-start.json",
}
RECOVERY_CLOSEOUT_FILES = {
    "source_manifest": "source-manifest.json",
    "proposal": "design-proposal.md",
    "challenge_input": "challenge-input.json",
    "challenged_supplemental": "challenged-supplemental.json",
    "completed_supplemental": "completed-supplemental.json",
    "challenge_result": "challenge-result.json",
    "challenge_report": "challenge-result.md",
    "coordinator_decision": "coordinator-decision.json",
}
ISSUE23_DIGEST = "edb0ea490e463a75cbb92696e1400c2ad8f32e939ae9fb905db132cb27e0baac"
ISSUE83_DIGEST = "b46ec791f25f51f7e022d00e6a654e0429e59b59a874500247f7f974c60664f9"
ISSUE23_RAW_SHA256 = "724087c8856d412e98070c8e677ff37e3c17638bd188c11e38c722f7329267b0"
ISSUE83_RAW_SHA256 = "0a975b01eb0a5732eecbccfca0de99ff0a952a9787c2af15b6870c08097f248c"
INHERITED_REMAINDER_COUNTS = dict.fromkeys(
    ("implementation", "initial_review", "remediation", "final_review", "design_reset"), 4
)
INHERITED_REMAINDER_COUNTS["initial_review"] = 3
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


def normalized_evidence(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", text(value)).split()).casefold()


def strict_json(raw: bytes) -> object:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(Invalid("nonfinite JSON")),
        )
    except (UnicodeError, ValueError, TypeError) as exc:
        raise Invalid(f"invalid archived JSON: {exc}") from exc


def remainder_sources(root: Path) -> tuple[dict, dict, dict, dict, dict, dict]:
    """Recognize the single frozen Issue84 source set, not an adoption API."""
    folder = root / REMAINDER_ARCHIVE
    if (folder / "closeout-manifest.json").is_symlink() or (
        folder / "finite-disposition-92.json"
    ).is_symlink():
        raise Invalid("Issue84 archived manifest/grant must be literal files")
    manifest_raw = (folder / "closeout-manifest.json").read_bytes()
    manifest = strict_json(manifest_raw)
    if digest(manifest) != REMAINDER_MANIFEST:
        raise Invalid("Issue84 closeout manifest differs from approved instance")
    keys(
        manifest,
        {
            "schema",
            "repo",
            "source_issue",
            "frozen_capsule",
            "proposal_digest",
            "challenge_input_digest",
            "sources",
            "coordinator_decision",
        },
    )
    if (
        manifest["schema"],
        manifest["repo"],
        manifest["source_issue"],
        manifest["proposal_digest"],
    ) != ("issue84-remainder-closeout-v1", REMAINDER_REPO, 84, REMAINDER_PROPOSAL):
        raise Invalid("Issue84 closeout identity mismatch")
    fixed_names = {
        "L84",
        "H",
        "R",
        "S0",
        "D1",
        "C1",
        "E1",
        "failure_handoff",
        "D2",
        "challenge_input",
        "challenged_supplemental",
        "completed_supplemental",
        "C2",
        "E2",
    }
    sources = keys(manifest["sources"], fixed_names)
    archived = {}
    for name, descriptor in sources.items():
        descriptor = keys(descriptor, {"path", "kind", "raw_sha256", "canonical_sha256"})
        path = (
            REMAINDER_ARCHIVE
            / {
                "L84": "issue-84.json",
                "H": "correction-journal.json",
                "R": "last-recovery-journal.json",
                "S0": "supplemental-S0.json",
                "D1": "design-proposal-D1.md",
                "C1": "challenge-result-C1.md",
                "E1": "coordinator-arbitration-E1.md",
                "failure_handoff": "last-recovery-failure-handoff.md",
                "D2": "design-proposal-D2.md",
                "challenge_input": "challenge-input-C2.json",
                "challenged_supplemental": "supplemental-C2-input.json",
                "completed_supplemental": "supplemental-completed.json",
                "C2": "challenge-result-C2.md",
                "E2": "coordinator-arbitration-E2.md",
            }[name]
        )
        if descriptor["path"] != path.as_posix():
            raise Invalid("Issue84 source selector changed")
        if (root / path).is_symlink():
            raise Invalid("Issue84 archived source must be a literal file")
        raw = (root / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha(descriptor["raw_sha256"]):
            raise Invalid(f"Issue84 archived source {name} changed")
        if descriptor["kind"] == "json":
            archived[name] = strict_json(raw)
            if digest(archived[name]) != sha(descriptor["canonical_sha256"]):
                raise Invalid(f"Issue84 source {name} canonical digest changed")
        elif descriptor["kind"] == "text" and descriptor["canonical_sha256"] is None:
            archived[name] = raw.decode("utf-8")
        else:
            raise Invalid("Issue84 source kind mismatch")
    if (
        not archived["C2"].find("Outcome: CHALLENGE_PASS") >= 0
        or not archived["E2"].find("Approve the complete parameterized D2 technical contract") >= 0
    ):
        raise Invalid("Issue84 independent challenge or coordinator approval absent")
    challenge = keys(
        archived["challenge_input"],
        {
            "schema",
            "proposal_digest",
            "frozen_capsule",
            "fixed_sources",
            "supplemental_prefix_digest",
            "supplemental_event_count",
        },
    )
    if (
        challenge["schema"],
        challenge["proposal_digest"],
        challenge["supplemental_prefix_digest"],
        challenge["supplemental_event_count"],
    ) != (
        "issue84-d2-challenge-input-v1",
        REMAINDER_PROPOSAL,
        digest(archived["challenged_supplemental"]),
        13,
    ):
        raise Invalid("Issue84 challenge input differs from challenged snapshot")
    s0, challenged, completed = (
        archived[name] for name in ("S0", "challenged_supplemental", "completed_supplemental")
    )
    if not (
        len(s0["events"]) == 11
        and len(challenged["events"]) == 13
        and len(completed["events"]) == 15
    ):
        raise Invalid("Issue84 supplemental reservation history incomplete")
    if (
        challenged["events"][:11] != s0["events"]
        or completed["events"][:13] != challenged["events"]
    ):
        raise Invalid("Issue84 supplemental prefix edited")
    if [event["type"] for event in completed["events"][13:]] != [
        "phase_end",
        "coordinator_decision",
    ]:
        raise Invalid("Issue84 supplemental closeout contains unapproved work")
    if (
        completed["events"][4]["outcome"],
        completed["events"][6]["outcome"],
        completed["events"][11]["outcome"],
        completed["events"][13]["outcome"],
        completed["events"][14]["outcome"],
    ) != ("blocked", "fail", "DESIGN_READY", "CHALLENGE_PASS", "approved"):
        raise Invalid("Issue84 supplemental failed/pass outcomes changed")
    if completed["events"][8]["D1_seconds"] != 3441 or completed["events"][8]["C1_seconds"] != 479:
        raise Invalid("Issue84 supplemental elapsed audit changed")
    if (
        manifest["challenge_input_digest"] != digest(challenge)
        or manifest["coordinator_decision"]["outcome"] != "approved"
    ):
        raise Invalid("Issue84 closeout decision mismatch")
    ledger, journal, recovery = (archived[name] for name in ("L84", "H", "R"))
    if len(ledger["events"]) != 62 or ledger["events"][61]["type"] != "correction_delivery":
        raise Invalid("Issue84 complete historical ledger missing")
    if any(
        ledger["events"][61]["data"][key] != journal[key]
        for key in ("historical_import", "transcript")
    ):
        raise Invalid("Issue84 correction journal double representation differs")
    native = [
        event["data"]["phase"] for event in ledger["events"][:61] if event["type"] == "phase_start"
    ]
    imported = [item["phase"] for item in journal["historical_import"]["phases"]]
    hmap = {
        "H7": "challenge",
        "H8": "implementation",
        "H9": "verification",
        "H10": "initial_review",
    }
    starts = [event for event in journal["transcript"] if event["type"] == "phase_start"]
    if [event["data"]["slot"] for event in starts] != list(hmap):
        raise Invalid("Issue84 H reservation sequence changed")
    imported += list(hmap.values())
    rstarts = recovery["bootstrap"]["reservation"]["events"] + [
        event for event in recovery["transcript"] if event["type"] == "phase_start"
    ]
    rphases = [event["data"]["phase"] for event in rstarts]
    totals = {key: sum(phase == key for phase in native + imported + rphases) for key in COUNTS}
    if (
        totals != INHERITED_REMAINDER_COUNTS
        or sum(phase == "verification" for phase in native + imported + rphases) != 7
    ):
        raise Invalid("Issue84 inherited reservation accounting differs")
    if len(recovery["transcript"]) != 11 or recovery["transcript"][-1]["data"]["outcome"] != "fail":
        raise Invalid("Issue84 failed last recovery missing")
    grant = strict_json((folder / "finite-disposition-92.json").read_bytes())
    if digest(grant) != REMAINDER_GRANT:
        raise Invalid("Issue92 user grant changed")
    return manifest, grant, ledger, journal, recovery, completed


def inherited_identities(value: object) -> set[str]:
    result: set[str] = set()

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key in {"authority", "authorization"} and isinstance(child, dict):
                    for identity in ("evidence", "anchor"):
                        if isinstance(child.get(identity), str) and child[identity].strip():
                            result.add(normalized_evidence(child[identity]))
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return result


def recovery_sources(root: Path) -> tuple[dict, dict, dict, dict, dict]:
    """Read the one pinned noncircular recovery package, including original sources."""
    remainder_sources(root)
    folder = root / RECOVERY_ARCHIVE
    if folder.is_symlink() or not folder.is_dir():
        raise Invalid("Issue92 recovery archive must be a literal directory")

    def read_descriptor(name: str, filename: str, descriptor: object) -> object:
        item = keys(descriptor, {"path", "kind", "raw_sha256", "canonical_sha256"})
        relative = RECOVERY_ARCHIVE / filename
        if item["path"] != relative.as_posix():
            raise Invalid(f"Issue92 recovery source selector changed: {name}")
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise Invalid(f"Issue92 recovery source must be a literal file: {name}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha(item["raw_sha256"]):
            raise Invalid(f"Issue92 recovery source bytes changed: {name}")
        if item["kind"] == "json":
            decoded = strict_json(raw)
            if digest(decoded) != sha(item["canonical_sha256"]):
                raise Invalid(f"Issue92 recovery source canonical digest changed: {name}")
            return decoded
        if item["kind"] == "text" and item["canonical_sha256"] is None:
            try:
                return raw.decode("utf-8")
            except UnicodeError as exc:
                raise Invalid("Issue92 recovery text is not UTF-8") from exc
        raise Invalid(f"Issue92 recovery source kind mismatch: {name}")

    manifest_path = folder / "source-manifest.json"
    closeout_path = folder / "closeout-manifest.json"
    grant_path = folder / "finite-grant.json"
    if any(
        path.is_symlink() or not path.is_file()
        for path in (manifest_path, closeout_path, grant_path)
    ):
        raise Invalid("Issue92 recovery manifest, closeout and grant must be literal files")
    manifest = strict_json(manifest_path.read_bytes())
    closeout = strict_json(closeout_path.read_bytes())
    grant = strict_json(grant_path.read_bytes())
    if (digest(manifest), digest(closeout), digest(grant)) != (
        RECOVERY_MANIFEST,
        RECOVERY_CLOSEOUT,
        RECOVERY_GRANT,
    ):
        raise Invalid("Issue92 recovery manifest, closeout or grant differs from approved instance")
    keys(
        manifest,
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "failed_content",
            "original_manifest_digest",
            "original_grant_digest",
            "sources",
        },
    )
    if (
        manifest["schema"] != "issue92-recovery-sources-v1"
        or manifest["repo"] != REMAINDER_REPO
        or integer(manifest["issue"], 1) != REMAINDER_ISSUE
        or manifest["capsule"] != RECOVERY_CAPSULE_REF
        or manifest["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or manifest["failed_content"] != RECOVERY_FAILED_CONTENT
        or manifest["original_manifest_digest"] != REMAINDER_MANIFEST
        or manifest["original_grant_digest"] != REMAINDER_GRANT
    ):
        raise Invalid("Issue92 recovery source manifest identity mismatch")
    source_map = keys(manifest["sources"], set(RECOVERY_SOURCE_FILES))
    sources = {
        name: read_descriptor(name, filename, source_map[name])
        for name, filename in RECOVERY_SOURCE_FILES.items()
    }
    stop = sources["stop_ledger"]
    bootstrap = sources["bootstrap_ledger"]
    if (
        digest(stop) != RECOVERY_STOP
        or digest(bootstrap) != RECOVERY_BOOTSTRAP
        or len(stop["events"]) != 6
        or len(bootstrap["events"]) != 2
        or stop["events"][:2] != bootstrap["events"]
        or stop["events"][4]["data"]["outcome"] != "fail"
        or stop["events"][5]["data"]["id"] != RECOVERY_BLOCKER
    ):
        raise Invalid("Issue92 exact stopped/bootstrap histories differ")
    keys(
        closeout,
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "source_manifest_digest",
            "proposal_digest",
            "challenge_input_digest",
            "sources",
        },
    )
    if (
        closeout["schema"] != "issue92-recovery-closeout-v1"
        or closeout["repo"] != REMAINDER_REPO
        or integer(closeout["issue"], 1) != REMAINDER_ISSUE
        or closeout["capsule"] != RECOVERY_CAPSULE_REF
        or closeout["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or closeout["source_manifest_digest"] != RECOVERY_MANIFEST
        or closeout["proposal_digest"] != RECOVERY_PROPOSAL
    ):
        raise Invalid("Issue92 recovery closeout identity mismatch")
    closeout_map = keys(closeout["sources"], set(RECOVERY_CLOSEOUT_FILES))
    closed = {
        name: read_descriptor(name, filename, closeout_map[name])
        for name, filename in RECOVERY_CLOSEOUT_FILES.items()
    }
    if closed["source_manifest"] != manifest or digest(closed["proposal"]) != RECOVERY_PROPOSAL:
        raise Invalid("Issue92 recovery proposal or source manifest differs")
    challenge_input = keys(
        closed["challenge_input"],
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "proposal_digest",
            "source_manifest_digest",
            "supplemental_prefix_digest",
            "supplemental_event_count",
        },
    )
    challenged = closed["challenged_supplemental"]
    completed = closed["completed_supplemental"]
    if (
        challenge_input["schema"] != "issue92-recovery-challenge-input-v1"
        or challenge_input["repo"] != REMAINDER_REPO
        or integer(challenge_input["issue"], 1) != REMAINDER_ISSUE
        or challenge_input["capsule"] != RECOVERY_CAPSULE_REF
        or challenge_input["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or challenge_input["proposal_digest"] != RECOVERY_PROPOSAL
        or challenge_input["source_manifest_digest"] != RECOVERY_MANIFEST
        or challenge_input["supplemental_prefix_digest"] != digest(challenged)
        or integer(challenge_input["supplemental_event_count"], 1) != 3
        or closeout["challenge_input_digest"] != digest(challenge_input)
        or completed["events"][:3] != challenged["events"]
        or len(challenged["events"]) != 3
        or [event["type"] for event in completed["events"][3:]]
        != ["phase_end", "coordinator_decision"]
    ):
        raise Invalid("Issue92 recovery challenge snapshot differs")
    events = completed["events"]
    if [event["type"] for event in events] != [
        "phase_start",
        "phase_end",
        "phase_start",
        "phase_end",
        "coordinator_decision",
    ] or any(
        timestamp(events[index]["at"]) > timestamp(events[index + 1]["at"])
        for index in range(len(events) - 1)
    ):
        raise Invalid("Issue92 recovery supplemental phases or times changed")
    if (
        (
            events[0]["reservation"],
            events[0]["phase"],
            events[0]["session"],
            events[0]["role"],
            events[0]["model"],
            events[0]["effort"],
        )
        != (
            "R92D1",
            "design_revision",
            "/root/issue92_recovery_design",
            "design_architect",
            "gpt-6-astra",
            "high",
        )
        or (events[1]["reservation"], events[1]["session"], events[1]["outcome"])
        != ("R92D1", events[0]["session"], "DESIGN_READY")
        or (
            events[2]["reservation"],
            events[2]["phase"],
            events[2]["session"],
            events[2]["role"],
            events[2]["model"],
            events[2]["effort"],
        )
        != (
            "R92C1",
            "challenge",
            "/root/issue92_recovery_challenge",
            "code_reviewer",
            "gpt-6-sol",
            "high",
        )
        or (events[3]["reservation"], events[3]["session"], events[3]["outcome"])
        != ("R92C1", events[2]["session"], "CHALLENGE_PASS")
        or events[4]["outcome"] != "approved"
        or events[1]["proposal_digest"] != RECOVERY_PROPOSAL
        or events[2]["proposal_digest"] != RECOVERY_PROPOSAL
        or events[3]["proposal_digest"] != RECOVERY_PROPOSAL
    ):
        raise Invalid("Issue92 recovery supplemental reservation/outcome changed")
    result = keys(
        closed["challenge_result"],
        {
            "schema",
            "reservation",
            "session",
            "role",
            "model",
            "effort",
            "proposal_digest",
            "challenge_input_digest",
            "outcome",
            "evidence",
        },
    )
    decision = keys(
        closed["coordinator_decision"],
        {
            "schema",
            "authority",
            "proposal_digest",
            "challenge_input_digest",
            "challenge_result_digest",
            "outcome",
            "evidence",
        },
    )
    if (
        result["schema"] != "issue92-recovery-challenge-result-v1"
        or result["reservation"] != "R92C1"
        or (result["role"], result["model"], result["effort"])
        != ("code_reviewer", "gpt-6-sol", "high")
        or result["session"] != completed["events"][3]["session"]
        or result["outcome"] != "CHALLENGE_PASS"
        or result["proposal_digest"] != RECOVERY_PROPOSAL
        or result["challenge_input_digest"] != digest(challenge_input)
        or decision["schema"] != "issue92-recovery-coordinator-decision-v1"
        or decision["outcome"] != "approved"
        or decision["proposal_digest"] != RECOVERY_PROPOSAL
        or decision["challenge_input_digest"] != digest(challenge_input)
        or decision["challenge_result_digest"] != digest(result)
        or completed["events"][3]["outcome"] != "CHALLENGE_PASS"
        or completed["events"][4]["outcome"] != "approved"
    ):
        raise Invalid("Issue92 recovery challenge or coordinator approval absent")
    authority(decision["authority"], "coordinator")
    keys(
        grant,
        {
            "schema",
            "repo",
            "issue",
            "authority",
            "authority_anchor",
            "at",
            "capsule",
            "original_grant_digest",
            "stop_ledger_digest",
            "failed_content",
            "proposal_digest",
            "closeout_digest",
            "owner",
            "count_deltas",
            "supplemental_deltas",
            "review_disposition",
            "publication",
            "bootstrap_exception",
            "seconds",
            "merging",
            "reason",
        },
    )
    authority(grant["authority"], "user")
    text(grant["authority_anchor"])
    grant_at = timestamp(grant["at"])
    if (
        grant["schema"] != "issue92-single-recovery-grant-v1"
        or grant["repo"] != REMAINDER_REPO
        or integer(grant["issue"], 1) != REMAINDER_ISSUE
        or grant["capsule"] != RECOVERY_CAPSULE_REF
        or grant["original_grant_digest"] != REMAINDER_GRANT
        or grant["stop_ledger_digest"] != RECOVERY_STOP
        or grant["failed_content"] != RECOVERY_FAILED_CONTENT
        or grant["proposal_digest"] != RECOVERY_PROPOSAL
        or grant["closeout_digest"] != RECOVERY_CLOSEOUT
        or grant["owner"]
        != {
            "role": "implementation_worker",
            "model": "gpt-6-sol",
            "effort": "medium",
            "session": RECOVERY_OWNER,
        }
        or {k: integer(v) for k, v in keys(grant["count_deltas"], set(COUNTS)).items()}
        != {**dict.fromkeys(COUNTS, 0), "remediation": 1}
        or {
            k: integer(v)
            for k, v in keys(
                grant["supplemental_deltas"],
                {
                    "verification",
                    "design",
                    "challenge",
                    "design_revision",
                },
            ).items()
        }
        != {"verification": 1, "design": 0, "challenge": 0, "design_revision": 0}
        or grant["review_disposition"]
        != "retain-unused-initial-review-after-single-pre-review-repair"
        or integer(grant["seconds"]) != 0
        or grant["merging"] is not False
        or grant["bootstrap_exception"] != "append-one-recovery-and-one-remediation-start"
    ):
        raise Invalid("Issue92 finite recovery grant differs")
    publication = keys(
        grant["publication"],
        {
            "mode",
            "original_grant_digest",
            "additional_count",
            "total_count",
            "repo",
            "primary_issue",
            "head",
            "base",
            "excluded_prs",
            "actual_saved_delivery_check_runs",
        },
    )
    if publication != {
        "mode": "retain-original-unused-one-new-pr",
        "original_grant_digest": REMAINDER_GRANT,
        "additional_count": 0,
        "total_count": 1,
        "repo": REMAINDER_REPO,
        "primary_issue": REMAINDER_ISSUE,
        "head": "codex/issue-92-issue84-remainder",
        "base": "main",
        "excluded_prs": [85],
        "actual_saved_delivery_check_runs": 1,
    }:
        raise Invalid("Issue92 recovery publication grant differs")
    if grant_at < timestamp(completed["events"][-1]["at"]):
        raise Invalid("Issue92 recovery grant predates approval")
    old_identities = inherited_identities(
        {
            "original": remainder_sources(root),
            "stop": stop,
            "sources": sources,
            "completed": completed,
            "decision": decision,
        }
    )
    if normalized_evidence(grant["authority"]["evidence"]) in old_identities or (
        normalized_evidence(grant["authority_anchor"]) in old_identities
    ):
        raise Invalid("Issue92 recovery grant reuses prior authority")
    return grant, closeout, manifest, stop, completed


def initialize_remainder(state: State, data: dict, root: Path) -> None:
    marker = keys(
        data["issue84_remainder"],
        {"version", "source_issue", "history_manifest_digest", "proposal_digest", "grant_digest"},
    )
    if marker != {
        "version": "issue84-remainder-inheritance-v1",
        "source_issue": 84,
        "history_manifest_digest": REMAINDER_MANIFEST,
        "proposal_digest": REMAINDER_PROPOSAL,
        "grant_digest": REMAINDER_GRANT,
    } or (state.repo, state.issue, state.policy) != (
        REMAINDER_REPO,
        REMAINDER_ISSUE,
        "owner-led-v1",
    ):
        raise Invalid("unapproved Issue84 remainder bootstrap")
    _manifest, grant, ledger, journal, recovery, supplemental = remainder_sources(root)
    keys(
        grant,
        {
            "schema",
            "repo",
            "source_issue",
            "target_issue",
            "authority",
            "authority_anchor",
            "proposal_digest",
            "closeout_digest",
            "execution_capsule_digest",
            "owner",
            "counts",
            "supplemental",
            "seconds",
            "publication",
            "bootstrap_exception",
            "reason",
        },
    )
    authority(grant["authority"], "user")
    if (
        grant["schema"],
        grant["repo"],
        grant["source_issue"],
        grant["target_issue"],
        grant["proposal_digest"],
        grant["closeout_digest"],
        grant["execution_capsule_digest"],
        grant["seconds"],
        grant["bootstrap_exception"],
    ) != (
        "issue84-remainder-finite-disposition-v1",
        REMAINDER_REPO,
        84,
        92,
        REMAINDER_PROPOSAL,
        REMAINDER_MANIFEST,
        REMAINDER_CAPSULE,
        0,
        True,
    ):
        raise Invalid("Issue92 finite grant identity mismatch")
    if keys(grant["counts"], set(COUNTS)) != {
        "implementation": 1,
        "initial_review": 1,
        "remediation": 0,
        "final_review": 0,
        "design_reset": 0,
    }:
        raise Invalid("Issue92 count grant differs from finite authority")
    if keys(grant["supplemental"], {"verification", "design", "challenge", "design_revision"}) != {
        "verification": 1,
        "design": 0,
        "challenge": 0,
        "design_revision": 0,
    }:
        raise Invalid("Issue92 supplemental grant differs from finite authority")
    if keys(grant["publication"], {"mode", "repo", "primary_issue", "count", "excluded_prs"}) != {
        "mode": "one-new-pr",
        "repo": REMAINDER_REPO,
        "primary_issue": 92,
        "count": 1,
        "excluded_prs": [85],
    }:
        raise Invalid("Issue92 publication grant differs from finite authority")
    if (
        state.capsule is None
        or digest(state.capsule) != REMAINDER_CAPSULE
        or state.capsule["authorization"] != grant["authority"]
        or state.capsule["owner"] != grant["owner"]
    ):
        raise Invalid("Issue92 execution capsule differs from grant")
    identities = inherited_identities([ledger, journal, recovery, supplemental])
    if (
        normalized_evidence(grant["authority"]["evidence"]) in identities
        or normalized_evidence(grant["authority_anchor"]) in identities
    ):
        raise Invalid("Issue92 grant authority reused from historical lineage")
    state.authorization_history.update(identities)
    state.authorization_history.add(normalized_evidence(grant["authority_anchor"]))
    state.inherited_counts = INHERITED_REMAINDER_COUNTS.copy()
    state.counts = INHERITED_REMAINDER_COUNTS.copy()
    state.limits = {key: state.counts[key] + grant["counts"][key] for key in COUNTS}
    historical_starts = [
        event["data"] for event in ledger["events"][:61] if event["type"] == "phase_start"
    ]
    historical_starts += journal["historical_import"]["phases"]
    historical_starts += [
        {
            **event["data"],
            "phase": {
                "H7": "challenge",
                "H8": "implementation",
                "H9": "verification",
                "H10": "initial_review",
            }[event["data"]["slot"]],
        }
        for event in journal["transcript"]
        if event["type"] == "phase_start"
    ]
    historical_starts += [event["data"] for event in recovery["bootstrap"]["reservation"]["events"]]
    historical_starts += [
        event["data"] for event in recovery["transcript"] if event["type"] == "phase_start"
    ]
    state.historical_reservations = historical_starts + [
        event for event in supplemental["events"] if event["type"] == "phase_start"
    ]
    state.historical_outcomes = [
        {"source": "L84", "session": event["data"]["session"], "outcome": event["data"]["outcome"]}
        for event in ledger["events"][:61]
        if event["type"] == "phase_end"
    ]
    h_ends = {
        event["data"]["slot"]: event["data"]
        for event in journal["transcript"]
        if event["type"] == "phase_end"
    }
    if set(h_ends) != {"H6", "H7", "H8", "H9", "H10"}:
        raise Invalid("Issue84 H6-H10 completion set incomplete")
    state.historical_outcomes += [
        {
            "source": "H",
            "slot": item["slot"],
            "session": item["session"],
            "imported_outcome": item["outcome"],
            "outcome": h_ends["H6"]["outcome"] if item["slot"] == "H6" else item["outcome"],
        }
        for item in journal["historical_import"]["phases"]
    ]
    if (
        next(item for item in journal["historical_import"]["phases"] if item["slot"] == "H6")[
            "session"
        ]
        != h_ends["H6"]["session"]
    ):
        raise Invalid("Issue84 H6 completion session mismatch")
    h_starts = {
        event["data"]["slot"]: event["data"]
        for event in journal["transcript"]
        if event["type"] == "phase_start"
    }
    for slot in ("H7", "H8", "H9", "H10"):
        if h_starts[slot]["session"] != h_ends[slot]["session"]:
            raise Invalid("Issue84 H start/end session mismatch")
        state.historical_outcomes.append(
            {
                "source": "H",
                "slot": slot,
                "session": h_ends[slot]["session"],
                "outcome": h_ends[slot]["outcome"],
            }
        )
    state.historical_outcomes += [
        {
            "source": "R",
            "slot": event["data"].get("slot"),
            "session": event["data"]["session"],
            "outcome": event["data"]["outcome"],
        }
        for event in recovery["transcript"]
        if event["type"] == "phase_end"
    ]
    state.historical_outcomes += [
        {
            "source": "supplemental",
            "reservation": event["reservation"],
            "session": event["session"],
            "outcome": event["outcome"],
        }
        for event in supplemental["events"]
        if event["type"] == "phase_end"
    ]
    state.historical_findings = [
        {"source": "L84", "id": event["data"]["id"]}
        for event in ledger["events"][:61]
        if event["type"] == "blocker"
    ] + [
        {"source": "R5", "id": item["id"], "result": item["result"]}
        for item in recovery["transcript"][-1]["data"]["observations"]
    ]
    if not any(
        item["id"] == "B85-EXTERNAL-JOURNAL-FILE-RACE" and item.get("result") == "fail"
        for item in state.historical_findings
    ):
        raise Invalid("Issue84 failed recovery finding disappeared")
    for start in historical_starts:
        if start.get("phase") in {"implementation", "remediation", "verification"}:
            state.write_authors.add(text(start["session"]))
    for item in journal["historical_import"]["phases"]:
        state.write_authors.update(item.get("write_authors", []))
    if (
        not {
            "/root",
            "/root/issue84_implementation",
            "/root/issue84_implementation_correction",
            "/root/pr85_status_correction",
            "/root/pr85_redelivery_implementation",
            "/root/pr85_last_recovery_implementation",
        }
        <= state.write_authors
    ):
        raise Invalid("Issue84 historical write authors incomplete")
    if grant["owner"]["session"] in state.write_authors or grant["owner"]["session"] in {
        "/root/issue84_correction_design",
        "/root/issue84_correction_challenge",
    }:
        raise Invalid("Issue92 execution owner must be fresh after the imported lineage")
    state.historical_delivery_history = [
        {"repo": REMAINDER_REPO, "pr": 85, "content": ledger["events"][-2]["data"]["content"]},
        {"repo": REMAINDER_REPO, "pr": 85, "content": ledger["events"][-1]["data"]["content"]},
    ]
    if [item["content"] for item in state.historical_delivery_history] != [
        "f9ffcec169e992a677214253f486e022203785fac2a54184be5cb4198b6fc6f7",
        "7d680f302d12007e99a51f3d8540e7acd35b3e4420c6495116ee07dff2c1c45d",
    ]:
        raise Invalid("Issue84 historical PR85 bindings changed")
    state.remainder = True
    state.design_ref = state.challenge_ref = state.approved_ref = capsule_ref(state.capsule)
    state.challenge_ok = state.ready = True
    state.design_session = "/root/issue84_correction_design"
    state.challenge_session = "/root/issue84_correction_challenge"


def pr_identity_sources(root: Path) -> tuple[dict, dict, dict, dict, dict]:
    """Validate the one immutable post-review source and authority package."""
    original_sources = remainder_sources(root)
    prior_sources = recovery_sources(root)
    folder = root / PR_IDENTITY_ARCHIVE
    if folder.is_symlink() or not folder.is_dir():
        raise Invalid("Issue92 PR identity archive must be a literal directory")

    def read(name: str, filename: str, descriptor: object) -> object:
        item = keys(descriptor, {"path", "kind", "raw_sha256", "canonical_sha256"})
        relative = PR_IDENTITY_ARCHIVE / filename
        if item["path"] != relative.as_posix() or ".." in Path(filename).parts:
            raise Invalid(f"Issue92 PR identity selector changed: {name}")
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise Invalid(f"Issue92 PR identity source must be a literal file: {name}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha(item["raw_sha256"]):
            raise Invalid(f"Issue92 PR identity source bytes changed: {name}")
        if item["kind"] == "json":
            value = strict_json(raw)
            if digest(value) != sha(item["canonical_sha256"]):
                raise Invalid(f"Issue92 PR identity source digest changed: {name}")
            return value
        if item["kind"] == "text" and item["canonical_sha256"] is None:
            try:
                return raw.decode("utf-8")
            except UnicodeError as exc:
                raise Invalid(f"Issue92 PR identity text is not UTF-8: {name}") from exc
        raise Invalid(f"Issue92 PR identity source kind changed: {name}")

    if any(
        (folder / name).is_symlink()
        for name in ("source-manifest.json", "closeout-manifest.json", "finite-grant.json")
    ):
        raise Invalid("Issue92 PR identity package must contain literal files")
    manifest = strict_json((folder / "source-manifest.json").read_bytes())
    closeout = strict_json((folder / "closeout-manifest.json").read_bytes())
    grant = strict_json((folder / "finite-grant.json").read_bytes())
    if (digest(manifest), digest(closeout), digest(grant)) != (
        PR_IDENTITY_MANIFEST,
        PR_IDENTITY_CLOSEOUT,
        PR_IDENTITY_GRANT,
    ):
        raise Invalid("Issue92 PR identity pinned package digest changed")
    keys(
        manifest,
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "failed_content",
            "stop_ledger_digest",
            "original_manifest_digest",
            "original_grant_digest",
            "prior_recovery_manifest_digest",
            "prior_recovery_closeout_digest",
            "prior_recovery_grant_digest",
            "sources",
        },
    )
    if (
        manifest["schema"] != "issue92-pr-identity-sources-v1"
        or manifest["repo"] != REMAINDER_REPO
        or integer(manifest["issue"], 1) != REMAINDER_ISSUE
        or manifest["capsule"] != RECOVERY_CAPSULE_REF
        or manifest["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or manifest["failed_content"] != PR_IDENTITY_CONTENT
        or manifest["stop_ledger_digest"] != PR_IDENTITY_STOP
        or manifest["original_manifest_digest"] != REMAINDER_MANIFEST
        or manifest["original_grant_digest"] != REMAINDER_GRANT
        or manifest["prior_recovery_manifest_digest"] != RECOVERY_MANIFEST
        or manifest["prior_recovery_closeout_digest"] != RECOVERY_CLOSEOUT
        or manifest["prior_recovery_grant_digest"] != RECOVERY_GRANT
    ):
        raise Invalid("Issue92 PR identity manifest binding changed")
    filenames = {
        **PR_IDENTITY_SOURCE_FILES,
        **{
            f"verification/{name}": f"verification/{name}"
            for name in PR_IDENTITY_VERIFICATION_FILES
        },
    }
    source_map = keys(manifest["sources"], set(filenames))
    sources = {name: read(name, filename, source_map[name]) for name, filename in filenames.items()}
    stop = sources["stop_ledger"]
    if (
        len(stop["events"]) != 16
        or digest(stop) != PR_IDENTITY_STOP
        or source_map["stop_ledger"]["raw_sha256"] != PR_IDENTITY_STOP_RAW
        or sources["prior_bootstrap"]["events"] != stop["events"][:8]
    ):
        raise Invalid("Issue92 PR identity frozen sixteen-event stop changed")
    for name, index in {
        "prior_remediation_end": 8,
        "prior_blocker_resolution": 9,
        "prior_verification_start": 10,
        "prior_verification_end": 11,
        "prior_acceptance": 12,
        "review_start": 13,
        "review_end": 14,
    }.items():
        if sources[name] != stop["events"][index]:
            raise Invalid(f"Issue92 PR identity event source mismatch: {name}")
    if (
        stop["events"][14]["data"]["outcome"] != "fail"
        or stop["events"][15]["data"]["id"] != PR_IDENTITY_BLOCKER
        or sources["review_closeout"]["report_sha256"] != source_map["review_report"]["raw_sha256"]
        or sources["review_closeout"]["content"] != PR_IDENTITY_CONTENT
        or sources["review_closeout"]["outcome"] != "BLOCKED_FOR_DECISION"
        or sources["review_reservation"]["content"] != PR_IDENTITY_CONTENT
        or sources["review_reservation"]["session"] != stop["events"][13]["data"]["session"]
        or sources["review_startup"]["session"] != stop["events"][13]["data"]["session"]
        or sources["blocked_status"]["issue92_recovery_stage"] != "failed"
        or sources["blocked_status"]["content"] != PR_IDENTITY_CONTENT
    ):
        raise Invalid("Issue92 PR identity failed-review history changed")
    counts_at_stop = {
        "implementation": 5,
        "initial_review": 4,
        "remediation": 5,
        "final_review": 4,
        "design_reset": 4,
    }
    review = sources["review_reservation"]
    review_closeout = sources["review_closeout"]
    prepared = sources["preparation_start"]
    if (
        review["at"] != stop["events"][13]["at"]
        or review["consumed_counts"] != counts_at_stop
        or review["grant_digest"] != RECOVERY_GRANT
        or review_closeout["counts"] != counts_at_stop
        or review_closeout["limits"] != counts_at_stop
        or review_closeout["review_start"] != stop["events"][13]["at"]
        or review_closeout["review_end"] != stop["events"][14]["at"]
        or review_closeout["review_session"] != review["session"]
        or review_closeout["blocker"] != PR_IDENTITY_BLOCKER
        or review_closeout["startup_wait_included"] is not True
        or review_closeout["measured_review_seconds"]
        != int(
            (
                timestamp(stop["events"][14]["at"]) - timestamp(stop["events"][13]["at"])
            ).total_seconds()
        )
        or sources["review_startup"]["reservation_at"] != review["at"]
        or not (
            timestamp(review["at"])
            <= timestamp(sources["review_startup"]["at"])
            <= timestamp(stop["events"][14]["at"])
        )
        or sources["prior_remediation_reservation"]["grant_digest"] != RECOVERY_GRANT
        or sources["prior_remediation_reservation"]["phase"] != "remediation"
        or sources["prior_remediation_reservation"]["consumed_counts"]["remediation"] != 5
        or sources["prior_verification_reservation"]["content"] != PR_IDENTITY_CONTENT
        or sources["prior_verification_reservation"]["local_verification_starts"] != 2
        or sources["prior_verification_reservation"]["local_verification_limit"] != 2
        or sources["prior_verification_reservation"]["at"] != stop["events"][10]["at"]
        or sources["verification/before-status.json"]["content"] != PR_IDENTITY_CONTENT
        or sources["verification/after-status.json"]["content"] != PR_IDENTITY_CONTENT
        or any(
            "exit=0" not in sources[f"verification/{name}"]
            for name in PR_IDENTITY_VERIFICATION_FILES
            if name.endswith(".result.txt")
        )
        or prepared["source"]["ledger_digest"] != PR_IDENTITY_STOP
        or prepared["source"]["ledger_raw_sha256"] != PR_IDENTITY_STOP_RAW
        or prepared["source"]["event_count"] != 16
        or prepared["source"]["content"] != PR_IDENTITY_CONTENT
        or prepared["preserved_state"]["recovery_stage"] != "failed"
        or prepared["preserved_state"]["counts"] != counts_at_stop
        or prepared["events"][0]["reservation"] != "R92PD1"
        or prepared["events"][0]["gate"]["exit_code"] != 1
    ):
        raise Invalid("Issue92 PR identity reservation/verification source history changed")
    keys(
        closeout,
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "source_manifest_digest",
            "proposal_digest",
            "challenge_input_digest",
            "sources",
        },
    )
    if (
        closeout["schema"] != "issue92-pr-identity-closeout-v1"
        or closeout["repo"] != REMAINDER_REPO
        or integer(closeout["issue"], 1) != REMAINDER_ISSUE
        or closeout["capsule"] != RECOVERY_CAPSULE_REF
        or closeout["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or closeout["source_manifest_digest"] != PR_IDENTITY_MANIFEST
        or closeout["proposal_digest"] != PR_IDENTITY_PROPOSAL
        or closeout["challenge_input_digest"] != PR_IDENTITY_INPUT
    ):
        raise Invalid("Issue92 PR identity closeout binding changed")
    closed_map = keys(closeout["sources"], set(PR_IDENTITY_CLOSEOUT_FILES))
    closed = {
        name: read(name, filename, closed_map[name])
        for name, filename in PR_IDENTITY_CLOSEOUT_FILES.items()
    }
    if (
        closed["source_manifest"] != manifest
        or digest(closed["proposal"]) != PR_IDENTITY_PROPOSAL
        or digest(closed["challenge_input"]) != PR_IDENTITY_INPUT
    ):
        raise Invalid("Issue92 PR identity source/proposal/input changed")
    challenged = closed["challenged_supplemental"]
    completed = closed["completed_supplemental"]
    input_value = keys(
        closed["challenge_input"],
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "proposal_digest",
            "source_manifest_digest",
            "supplemental_prefix_digest",
            "supplemental_event_count",
        },
    )
    if (
        input_value["schema"] != "issue92-pr-identity-challenge-input-v1"
        or input_value["repo"] != REMAINDER_REPO
        or integer(input_value["issue"], 1) != REMAINDER_ISSUE
        or input_value["capsule"] != RECOVERY_CAPSULE_REF
        or input_value["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or input_value["proposal_digest"] != PR_IDENTITY_PROPOSAL
        or input_value["source_manifest_digest"] != PR_IDENTITY_MANIFEST
        or input_value["supplemental_prefix_digest"] != digest(challenged)
        or integer(input_value["supplemental_event_count"], 1) != 3
        or completed["events"][:3] != challenged["events"]
        or len(challenged["events"]) != 3
        or {key: value for key, value in completed.items() if key != "events"}
        != {key: value for key, value in challenged.items() if key != "events"}
    ):
        raise Invalid("Issue92 PR identity challenged prefix changed")
    events = completed["events"]
    if (
        len(events) != 5
        or [item["type"] for item in events]
        != ["phase_start", "phase_end", "phase_start", "phase_end", "coordinator_decision"]
        or any(timestamp(a["at"]) > timestamp(b["at"]) for a, b in itertools.pairwise(events))
        or (
            events[0]["reservation"],
            events[0]["session"],
            events[0]["role"],
            events[0]["model"],
            events[0]["effort"],
        )
        != ("R92PD1", "/root/issue92_pr_identity_design", "design_architect", "gpt-6-astra", "high")
        or (events[1]["reservation"], events[1]["outcome"], events[1]["proposal_digest"])
        != ("R92PD1", "DESIGN_READY", PR_IDENTITY_PROPOSAL)
        or (
            events[2]["reservation"],
            events[2]["session"],
            events[2]["role"],
            events[2]["model"],
            events[2]["effort"],
        )
        != ("R92PC1", "/root/issue92_pr_identity_challenge", "code_reviewer", "gpt-6-sol", "high")
        or (events[3]["reservation"], events[3]["outcome"], events[3]["proposal_digest"])
        != ("R92PC1", "CHALLENGE_PASS", PR_IDENTITY_PROPOSAL)
        or events[4]["outcome"] != "approved"
    ):
        raise Invalid("Issue92 PR identity supplemental phase history changed")
    result = keys(
        closed["challenge_result"],
        {
            "schema",
            "reservation",
            "session",
            "role",
            "model",
            "effort",
            "proposal_digest",
            "challenge_input_digest",
            "outcome",
            "evidence",
        },
    )
    decision = keys(
        closed["coordinator_decision"],
        {
            "schema",
            "authority",
            "proposal_digest",
            "challenge_input_digest",
            "challenge_result_digest",
            "outcome",
            "evidence",
        },
    )
    if (
        result["schema"] != "issue92-pr-identity-challenge-result-v1"
        or result["reservation"] != "R92PC1"
        or result["session"] != events[2]["session"]
        or result["outcome"] != "CHALLENGE_PASS"
        or events[3]["session"] != result["session"]
        or events[3]["challenge_result_digest"] != digest(result)
        or result["proposal_digest"] != PR_IDENTITY_PROPOSAL
        or result["challenge_input_digest"] != PR_IDENTITY_INPUT
        or decision["schema"] != "issue92-pr-identity-coordinator-decision-v1"
        or decision["proposal_digest"] != PR_IDENTITY_PROPOSAL
        or decision["challenge_input_digest"] != PR_IDENTITY_INPUT
        or decision["challenge_result_digest"] != digest(result)
        or decision["outcome"] != "approved"
        or events[4]["authority"] != decision["authority"]
        or events[4]["decision_digest"] != digest(decision)
    ):
        raise Invalid("Issue92 PR identity challenge/decision changed")
    keys(
        grant,
        {
            "schema",
            "repo",
            "issue",
            "authority",
            "authority_anchor",
            "at",
            "capsule",
            "original_grant_digest",
            "prior_recovery_grant_digest",
            "stop_ledger_digest",
            "failed_content",
            "source_manifest_digest",
            "proposal_digest",
            "closeout_digest",
            "owner",
            "count_deltas",
            "supplemental_deltas",
            "review_disposition",
            "publication",
            "bootstrap_exception",
            "seconds",
            "merging",
            "reason",
        },
    )
    authority(grant["authority"], "user")
    if (
        grant["schema"] != "issue92-pr-identity-repair-grant-v1"
        or grant["repo"] != REMAINDER_REPO
        or integer(grant["issue"], 1) != REMAINDER_ISSUE
        or grant["capsule"] != RECOVERY_CAPSULE_REF
        or grant["original_grant_digest"] != REMAINDER_GRANT
        or grant["prior_recovery_grant_digest"] != RECOVERY_GRANT
        or grant["stop_ledger_digest"] != PR_IDENTITY_STOP
        or grant["failed_content"] != PR_IDENTITY_CONTENT
        or grant["source_manifest_digest"] != PR_IDENTITY_MANIFEST
        or grant["proposal_digest"] != PR_IDENTITY_PROPOSAL
        or grant["closeout_digest"] != PR_IDENTITY_CLOSEOUT
        or grant["owner"]
        != {
            "role": "implementation_worker",
            "model": "gpt-6-sol",
            "effort": "medium",
            "session": RECOVERY_OWNER,
        }
        or keys(grant["count_deltas"], set(COUNTS))
        != {
            "implementation": 0,
            "initial_review": 0,
            "remediation": 1,
            "final_review": 1,
            "design_reset": 0,
        }
        or keys(
            grant["supplemental_deltas"], {"verification", "design", "challenge", "design_revision"}
        )
        != {"verification": 1, "design": 0, "challenge": 0, "design_revision": 0}
        or any(type(value) is not int for value in grant["count_deltas"].values())
        or any(type(value) is not int for value in grant["supplemental_deltas"].values())
        or grant["review_disposition"]
        != "one-final-review-after-failed-initial-review-and-counted-repair"
        or grant["bootstrap_exception"]
        != "append-one-pr-identity-disposition-and-one-remediation-start"
        or type(grant["seconds"]) is not int
        or grant["seconds"] != 0
        or grant["merging"] is not False
        or timestamp(grant["at"]) < timestamp(events[-1]["at"])
    ):
        raise Invalid("Issue92 PR identity finite grant changed")
    publication = keys(
        grant["publication"],
        {
            "mode",
            "original_grant_digest",
            "prior_recovery_grant_digest",
            "additional_count",
            "total_count",
            "repo",
            "primary_issue",
            "head",
            "base",
            "excluded_prs",
            "actual_saved_delivery_check_runs",
            "additional_actual_saved_delivery_check_runs",
        },
    )
    if publication != {
        "mode": "retain-original-unused-one-new-pr",
        "original_grant_digest": REMAINDER_GRANT,
        "prior_recovery_grant_digest": RECOVERY_GRANT,
        "additional_count": 0,
        "total_count": 1,
        "repo": REMAINDER_REPO,
        "primary_issue": 92,
        "head": "codex/issue-92-issue84-remainder",
        "base": "main",
        "excluded_prs": [85],
        "actual_saved_delivery_check_runs": 1,
        "additional_actual_saved_delivery_check_runs": 0,
    } or any(
        type(publication[key]) is not int
        for key in (
            "additional_count",
            "total_count",
            "primary_issue",
            "actual_saved_delivery_check_runs",
            "additional_actual_saved_delivery_check_runs",
        )
    ):
        raise Invalid("Issue92 PR identity publication grant changed")
    consumed = inherited_identities([original_sources, prior_sources, sources, completed])
    new_evidence = normalized_evidence(grant["authority"]["evidence"])
    new_anchor = normalized_evidence(grant["authority_anchor"])
    if new_evidence == new_anchor or new_evidence in consumed or new_anchor in consumed:
        raise Invalid("Issue92 PR identity authority reuses prior source identity")
    return grant, closeout, manifest, stop, completed


def stage_fixture_sources(root: Path) -> tuple[dict, dict, dict, dict, dict]:
    """Read the sole pinned stage-fixture repair package and earlier source chain."""
    original = remainder_sources(root)
    recovery = recovery_sources(root)
    previous = pr_identity_sources(root)
    folder = root / STAGE_FIXTURE_ARCHIVE
    if folder.is_symlink() or not folder.is_dir():
        raise Invalid("Issue92 stage fixture archive must be a literal directory")
    expected_files = {
        *STAGE_FIXTURE_SOURCE_FILES.values(),
        *STAGE_FIXTURE_CLOSEOUT_FILES.values(),
        "closeout-manifest.json",
        "finite-grant.json",
    }
    actual_files = set()
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise Invalid("Issue92 stage fixture archive may not contain symlinks")
        if path.is_file():
            actual_files.add(path.relative_to(folder).as_posix())
    if actual_files != expected_files:
        raise Invalid("Issue92 stage fixture archive membership changed")

    def document(name: str, filename: str, descriptor: object) -> object:
        item = keys(descriptor, {"path", "kind", "raw_sha256", "canonical_sha256"})
        relative = STAGE_FIXTURE_ARCHIVE / filename
        if item["path"] != relative.as_posix() or ".." in Path(filename).parts:
            raise Invalid(f"Issue92 stage fixture selector changed: {name}")
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise Invalid(f"Issue92 stage fixture source must be literal: {name}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha(item["raw_sha256"]):
            raise Invalid(f"Issue92 stage fixture raw source changed: {name}")
        if item["kind"] == "json":
            decoded = strict_json(raw)
            if digest(decoded) != sha(item["canonical_sha256"]):
                raise Invalid(f"Issue92 stage fixture JSON source changed: {name}")
            return decoded
        if item["kind"] == "text" and item["canonical_sha256"] is None:
            try:
                return raw.decode("utf-8")
            except UnicodeError as exc:
                raise Invalid(f"Issue92 stage fixture text source is not UTF-8: {name}") from exc
        raise Invalid(f"Issue92 stage fixture source kind changed: {name}")

    primary_files = ("source-manifest.json", "closeout-manifest.json", "finite-grant.json")
    if any((folder / name).is_symlink() or not (folder / name).is_file() for name in primary_files):
        raise Invalid("Issue92 stage fixture package requires literal manifest and grant")
    manifest = strict_json((folder / primary_files[0]).read_bytes())
    closeout = strict_json((folder / primary_files[1]).read_bytes())
    grant = strict_json((folder / primary_files[2]).read_bytes())
    if (digest(manifest), digest(closeout), digest(grant)) != (
        STAGE_FIXTURE_MANIFEST,
        STAGE_FIXTURE_CLOSEOUT,
        STAGE_FIXTURE_GRANT,
    ):
        raise Invalid("Issue92 stage fixture pinned package digest changed")
    keys(
        manifest,
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "failed_content",
            "stop_ledger_digest",
            "prior_grant_digest",
            "prior_closeout_digest",
            "sources",
        },
    )
    if (
        manifest["schema"] != "issue92-stage-fixture-sources-v1"
        or manifest["repo"] != REMAINDER_REPO
        or integer(manifest["issue"], 1) != REMAINDER_ISSUE
        or manifest["capsule"] != RECOVERY_CAPSULE_REF
        or manifest["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or manifest["failed_content"] != STAGE_FIXTURE_CONTENT
        or manifest["stop_ledger_digest"] != STAGE_FIXTURE_STOP
        or manifest["prior_grant_digest"] != PR_IDENTITY_GRANT
        or manifest["prior_closeout_digest"] != PR_IDENTITY_CLOSEOUT
    ):
        raise Invalid("Issue92 stage fixture source manifest binding changed")
    source_map = keys(manifest["sources"], set(STAGE_FIXTURE_SOURCE_FILES))
    sources = {
        name: document(name, filename, source_map[name])
        for name, filename in STAGE_FIXTURE_SOURCE_FILES.items()
    }
    stop = sources["stop_ledger"]
    summary = sources["verification_summary"]
    before = sources["before_status"]
    current = sources["current_status"]
    integrity = sources["before_integrity"]
    if (
        len(stop["events"]) != 23
        or digest(stop) != STAGE_FIXTURE_STOP
        or source_map["stop_ledger"]["raw_sha256"] != STAGE_FIXTURE_STOP_RAW
        or stop["events"][:16] != previous[3]["events"]
        or stop["events"][16]["type"] != "issue92_pr_identity_repair"
        or stop["events"][20]["data"]["phase"] != "verification"
        or stop["events"][21]["data"]["outcome"] != "fail"
        or stop["events"][22]["data"]["id"] != STAGE_FIXTURE_BLOCKER
        or stop["events"][22]["data"]["criterion"] != "AC84VERIFY"
        or summary["failure"] != "completed gate pytest-full failed"
        or len(summary["gates"]) != 4
        or [(item["name"], item["exit_code"]) for item in summary["gates"]]
        != [("ruff-check", 0), ("ruff-format", 0), ("mypy", 0), ("pytest-full", 1)]
        or summary["gates"][3]["duration_ms"] != 499775
        or summary["before"]["content"] != STAGE_FIXTURE_CONTENT
        or summary["before"]["event_count"] != 21
        or summary["before"]["stage"] != "verifying"
        or summary["before"]["local_verification_starts"] != 3
        or summary["before"]["local_verification_limit"] != 3
        or before != summary["before"]
        or current["stage"] != "verifying"
        or current["event_count"] != 21
        or current["content"] != STAGE_FIXTURE_CONTENT
        or integrity != summary["before_integrity"]
        or integrity["archive_files"] != 89
        or integrity["git_blob_roundtrip_mismatches"] != []
        or integrity["primary_matches"] is not True
        or "1 failed, 1509 passed, 47 skipped" not in sources["pytest"]
        or "test_issue92_actual_saved_recovery_and_portable_baselines" not in sources["pytest"]
        or summary.get("after") is not None
        or summary.get("after_integrity") is not None
    ):
        raise Invalid("Issue92 stage fixture failed verification evidence changed")
    prep = sources["preparation_start"]
    if (
        prep["schema"] != "issue92-stage-fixture-preparation-v1"
        or prep["issue"] != 92
        or prep["repo"] != REMAINDER_REPO
        or prep["capsule"] != RECOVERY_CAPSULE_REF
        or prep["stopped_content"] != STAGE_FIXTURE_CONTENT
        or prep["stop_ledger_digest"] != STAGE_FIXTURE_STOP
        or prep["authority_anchor"] != STAGE_FIXTURE_ANCHOR
        or prep["native_gate"]["exit_code"] != 1
        or len(prep["events"]) != 1
        or prep["events"][0]["data"]["reservation"] != "R92SD1"
    ):
        raise Invalid("Issue92 stage fixture preparation source changed")
    keys(
        closeout,
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "source_manifest_digest",
            "proposal_digest",
            "challenge_input_digest",
            "sources",
        },
    )
    if (
        closeout["schema"] != "issue92-stage-fixture-closeout-v1"
        or closeout["repo"] != REMAINDER_REPO
        or integer(closeout["issue"], 1) != 92
        or closeout["capsule"] != RECOVERY_CAPSULE_REF
        or closeout["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or closeout["source_manifest_digest"] != STAGE_FIXTURE_MANIFEST
        or closeout["proposal_digest"] != STAGE_FIXTURE_PROPOSAL
        or closeout["challenge_input_digest"] != STAGE_FIXTURE_INPUT
    ):
        raise Invalid("Issue92 stage fixture closeout binding changed")
    closeout_map = keys(closeout["sources"], set(STAGE_FIXTURE_CLOSEOUT_FILES))
    closed = {
        name: document(name, filename, closeout_map[name])
        for name, filename in STAGE_FIXTURE_CLOSEOUT_FILES.items()
    }
    if (
        closed["source_manifest"] != manifest
        or digest(closed["proposal"]) != STAGE_FIXTURE_PROPOSAL
        or digest(closed["challenge_input"]) != STAGE_FIXTURE_INPUT
    ):
        raise Invalid("Issue92 stage fixture source/proposal/input changed")
    challenged = closed["challenged_supplemental"]
    completed = closed["completed_supplemental"]
    input_value = keys(
        closed["challenge_input"],
        {
            "schema",
            "repo",
            "issue",
            "capsule",
            "original_capsule",
            "proposal_digest",
            "source_manifest_digest",
            "supplemental_prefix_digest",
            "supplemental_event_count",
        },
    )
    if (
        input_value["schema"] != "issue92-stage-fixture-challenge-input-v1"
        or input_value["repo"] != REMAINDER_REPO
        or integer(input_value["issue"], 1) != 92
        or input_value["capsule"] != RECOVERY_CAPSULE_REF
        or input_value["original_capsule"] != RECOVERY_ORIGINAL_CAPSULE
        or input_value["proposal_digest"] != STAGE_FIXTURE_PROPOSAL
        or input_value["source_manifest_digest"] != STAGE_FIXTURE_MANIFEST
        or input_value["supplemental_prefix_digest"] != digest(challenged)
        or integer(input_value["supplemental_event_count"], 1) != 3
        or len(challenged["events"]) != 3
        or completed["events"][:3] != challenged["events"]
        or {key: value for key, value in completed.items() if key != "events"}
        != {key: value for key, value in challenged.items() if key != "events"}
        or challenged["events"][0] != prep["events"][0]
    ):
        raise Invalid("Issue92 stage fixture challenge prefix changed")
    events = completed["events"]
    if (
        len(events) != 5
        or [item["type"] for item in events]
        != ["phase_start", "phase_end", "phase_start", "phase_end", "coordinator_decision"]
        or any(timestamp(a["at"]) > timestamp(b["at"]) for a, b in itertools.pairwise(events))
    ):
        raise Invalid("Issue92 stage fixture supplemental order changed")
    start, design_end, challenge_start, challenge_end, approval = (e["data"] for e in events)
    result = keys(
        closed["challenge_result"],
        {
            "schema",
            "reservation",
            "session",
            "role",
            "model",
            "effort",
            "proposal_digest",
            "challenge_input_digest",
            "outcome",
            "evidence",
        },
    )
    decision = keys(
        closed["coordinator_decision"],
        {
            "schema",
            "authority",
            "proposal_digest",
            "challenge_input_digest",
            "challenge_result_digest",
            "outcome",
            "evidence",
        },
    )
    if (
        (start["reservation"], start["session"], start["role"], start["model"], start["effort"])
        != (
            "R92SD1",
            "/root/issue92_stage_fixture_design",
            "design_architect",
            "gpt-6-astra",
            "high",
        )
        or (design_end["reservation"], design_end["session"], design_end["outcome"])
        != ("R92SD1", start["session"], "DESIGN_READY")
        or design_end["proposal_digest"] != STAGE_FIXTURE_PROPOSAL
        or (
            challenge_start["reservation"],
            challenge_start["session"],
            challenge_start["role"],
            challenge_start["model"],
            challenge_start["effort"],
        )
        != ("R92SC1", "/root/issue92_stage_fixture_challenge", "code_reviewer", "gpt-6-sol", "high")
        or challenge_start["proposal_digest"] != STAGE_FIXTURE_PROPOSAL
        or challenge_start["source_manifest_digest"] != STAGE_FIXTURE_MANIFEST
        or (challenge_end["reservation"], challenge_end["session"], challenge_end["outcome"])
        != ("R92SC1", challenge_start["session"], "CHALLENGE_PASS")
        or challenge_end["challenge_input_digest"] != STAGE_FIXTURE_INPUT
        or challenge_end["challenge_result_digest"] != digest(result)
        or challenge_end["report_raw_sha256"] != closeout_map["challenge_report"]["raw_sha256"]
        or result["schema"] != "issue92-stage-fixture-challenge-result-v1"
        or result["session"] != challenge_start["session"]
        or result["outcome"] != "CHALLENGE_PASS"
        or result["proposal_digest"] != STAGE_FIXTURE_PROPOSAL
        or result["challenge_input_digest"] != STAGE_FIXTURE_INPUT
        or decision["schema"] != "issue92-stage-fixture-coordinator-decision-v1"
        or decision["proposal_digest"] != STAGE_FIXTURE_PROPOSAL
        or decision["challenge_input_digest"] != STAGE_FIXTURE_INPUT
        or decision["challenge_result_digest"] != digest(result)
        or decision["outcome"] != "approved"
        or approval["decision_digest"] != digest(decision)
        or approval["authority"] != decision["authority"]
    ):
        raise Invalid("Issue92 stage fixture technical approval changed")
    keys(
        grant,
        {
            "schema",
            "repo",
            "issue",
            "authority",
            "authority_anchor",
            "at",
            "capsule",
            "original_grant_digest",
            "prior_recovery_grant_digest",
            "prior_pr_identity_grant_digest",
            "stop_ledger_digest",
            "failed_content",
            "source_manifest_digest",
            "proposal_digest",
            "closeout_digest",
            "owner",
            "count_deltas",
            "supplemental_deltas",
            "review_disposition",
            "publication",
            "bootstrap_exception",
            "seconds",
            "merging",
            "reason",
        },
    )
    authority(grant["authority"], "user")
    if (
        grant["schema"] != "issue92-stage-fixture-repair-grant-v1"
        or grant["repo"] != REMAINDER_REPO
        or integer(grant["issue"], 1) != 92
        or grant["capsule"] != RECOVERY_CAPSULE_REF
        or grant["original_grant_digest"] != REMAINDER_GRANT
        or grant["prior_recovery_grant_digest"] != RECOVERY_GRANT
        or grant["prior_pr_identity_grant_digest"] != PR_IDENTITY_GRANT
        or grant["stop_ledger_digest"] != STAGE_FIXTURE_STOP
        or grant["failed_content"] != STAGE_FIXTURE_CONTENT
        or grant["source_manifest_digest"] != STAGE_FIXTURE_MANIFEST
        or grant["proposal_digest"] != STAGE_FIXTURE_PROPOSAL
        or grant["closeout_digest"] != STAGE_FIXTURE_CLOSEOUT
        or grant["authority_anchor"] != STAGE_FIXTURE_ANCHOR
        or {key: grant["authority"][key] for key in ("name", "evidence")} != prep["authority"]
        or grant["authority_anchor"] != prep["authority_anchor"]
        or grant["owner"]
        != {
            "role": "implementation_worker",
            "model": "gpt-6-sol",
            "effort": "medium",
            "session": RECOVERY_OWNER,
        }
        or keys(grant["count_deltas"], set(COUNTS))
        != {
            "implementation": 0,
            "initial_review": 0,
            "remediation": 1,
            "final_review": 0,
            "design_reset": 0,
        }
        or keys(
            grant["supplemental_deltas"],
            {
                "verification",
                "design",
                "challenge",
                "design_revision",
            },
        )
        != {"verification": 1, "design": 0, "challenge": 0, "design_revision": 0}
        or any(type(value) is not int for value in grant["count_deltas"].values())
        or any(type(value) is not int for value in grant["supplemental_deltas"].values())
        or grant["review_disposition"] != "conserve-unused-final-review-after-stage-fixture-repair"
        or grant["publication"] != previous[0]["publication"]
        or grant["bootstrap_exception"]
        != "append-one-stage-fixture-disposition-and-one-remediation-start"
        or type(grant["seconds"]) is not int
        or grant["seconds"] != 0
        or grant["merging"] is not False
        or timestamp(grant["at"]) < timestamp(events[-1]["at"])
    ):
        raise Invalid("Issue92 stage fixture finite grant changed")
    consumed = inherited_identities([original, recovery, previous, stop])
    evidence = normalized_evidence(grant["authority"]["evidence"])
    anchor = normalized_evidence(grant["authority_anchor"])
    if evidence == anchor or evidence in consumed or anchor in consumed:
        raise Invalid("Issue92 stage fixture approval reused before this package")
    return grant, closeout, manifest, stop, completed


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
    split_pool: dict | None = None
    splits: dict = field(default_factory=dict)
    extension_authorizations: set[str] = field(default_factory=set)
    policy: str = "timed-v1"
    predecessor: bool = False
    authorization_history: set[str] = field(default_factory=set)
    delivery_history: list[dict] = field(default_factory=list)
    pending_repair: bool = False
    verification_repair_count: int | None = None
    inherited_counts: dict = field(default_factory=lambda: dict.fromkeys(COUNTS, 0))
    remainder: bool = False
    historical_delivery_history: list[dict] = field(default_factory=list)
    historical_reservations: list[dict] = field(default_factory=list)
    historical_outcomes: list[dict] = field(default_factory=list)
    historical_findings: list[dict] = field(default_factory=list)
    publication_target: dict | None = None
    lineage_transition: bool = False
    ancestor_split_remaining_seconds: int | None = None
    historical_timed_debt_seconds: int | None = None
    local_verification_starts: int = 0
    local_verification_limit: int = 1
    issue92_recovery_ref: dict | None = None
    issue92_recovery_stage: str = "absent"
    issue92_recovery_failure: str | None = None
    issue92_recovery_supplemental: list[dict] = field(default_factory=list)
    issue92_review_disposition: str | None = None
    issue92_pr_identity_ref: dict | None = None
    issue92_pr_identity_stage: str = "absent"
    issue92_pr_identity_failure: dict | None = None
    issue92_pr_identity_supplemental: list[dict] = field(default_factory=list)
    issue92_stage_fixture_ref: dict | None = None
    issue92_stage_fixture_stage: str = "absent"
    issue92_stage_fixture_failure: dict | None = None
    issue92_stage_fixture_supplemental: list[dict] = field(default_factory=list)

    def elapsed(self, now: datetime) -> int:
        if self.last is not None and now < self.last:
            raise Invalid("time predates recorded history")
        extra = int((now - self.last).total_seconds()) if self.clock_running and self.last else 0
        return self.elapsed_seconds + extra

    def gate(self, operation: str, now: datetime, *, allow_bootstrap: bool = False) -> None:
        if not self.capsule and not allow_bootstrap:
            raise Invalid("complete frozen capsule binding required")
        if self.delivered or self.split_remaining is not None or self.split_pool is not None:
            raise Invalid("terminal ticket; explicit user decision required")
        if self.remainder and operation in {
            "planning",
            "design",
            "challenge",
            "design_reset",
        }:
            raise Invalid("Issue92 finite grant has no allowance for this phase")
        if (
            self.remainder
            and operation == "final_review"
            and (
                not self.issue92_pr_identity_ref
                or (
                    self.issue92_stage_fixture_stage != "verified"
                    if self.issue92_stage_fixture_ref
                    else self.issue92_pr_identity_stage != "verified"
                )
                or self.blockers
                or self.pending_repair
                or self.counts["initial_review"] != 4
                or self.counts["final_review"] != 4
            )
        ):
            raise Invalid("Issue92 final review requires fresh certified PR identity repair")
        if self.remainder and operation == "remediation" and self.issue92_recovery_ref is None:
            raise Invalid("Issue92 finite grant has no allowance for this phase")
        if (
            self.remainder
            and operation == "remediation"
            and not (
                self.issue92_recovery_stage == "repair_pending"
                or self.issue92_pr_identity_stage == "repair_pending"
                or self.issue92_stage_fixture_stage == "repair_pending"
            )
        ):
            raise Invalid("Issue92 single recovery remediation already consumed")
        if (
            self.remainder
            and operation == "verification"
            and self.local_verification_starts >= self.local_verification_limit
        ):
            raise Invalid("Issue92 verification reservation exhausted")
        if (
            self.remainder
            and self.issue92_recovery_ref
            and operation == "verification"
            and not (
                self.issue92_recovery_stage == "repaired"
                or self.issue92_pr_identity_stage == "repaired"
                or self.issue92_stage_fixture_stage == "repaired"
            )
        ):
            raise Invalid("Issue92 fresh verification requires resolved repair")
        if (
            self.remainder
            and self.issue92_recovery_stage == "failed"
            and not self.issue92_pr_identity_ref
        ):
            raise Invalid("Issue92 completed recovery failure stops further phases")
        if self.issue92_pr_identity_stage == "failed" and not self.issue92_stage_fixture_ref:
            raise Invalid("Issue92 completed PR identity repair failure stops further phases")
        if self.issue92_stage_fixture_stage == "failed":
            raise Invalid("Issue92 completed stage fixture repair failure stops further phases")
        if (
            self.issue92_pr_identity_ref
            and not self.issue92_stage_fixture_ref
            and operation == "verification"
            and (
                self.issue92_pr_identity_stage != "repaired"
                or self.blockers
                or self.pending_repair
                or self.counts["remediation"] != 6
            )
        ):
            raise Invalid("Issue92 verification requires resolved sixth remediation")
        if (
            self.issue92_stage_fixture_ref
            and operation == "verification"
            and (
                self.issue92_stage_fixture_stage != "repaired"
                or self.blockers
                or self.pending_repair
                or self.counts["remediation"] != 7
            )
        ):
            raise Invalid("Issue92 verification requires resolved seventh remediation")
        if self.policy == "timed-v1" and self.elapsed(now) >= self.budget_seconds:
            raise Invalid("active-time budget exhausted; stop for user decision")
        if operation == "delivery":
            if not self.clock_running:
                raise Invalid("explicit coordination resume required before delivery")
            if (
                self.active
                or self.suspended
                or self.blockers
                or self.final_failed
                or self.pending_repair
            ):
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
            if self.issue92_stage_fixture_ref and self.issue92_stage_fixture_stage != "reviewed":
                raise Invalid("Issue92 stage fixture delivery requires clean current final review")
            if (
                self.issue92_recovery_ref
                and not self.issue92_stage_fixture_ref
                and self.issue92_recovery_stage != "reviewed"
                and self.issue92_pr_identity_stage != "reviewed"
            ):
                raise Invalid("Issue92 recovery delivery requires clean current review")
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
        if self.issue92_pr_identity_ref and operation == "initial_review":
            raise Invalid("Issue92 failed initial review cannot be reopened")
        if (
            self.remainder
            and self.issue92_recovery_ref
            and operation == "initial_review"
            and (
                self.issue92_recovery_stage != "verified"
                or self.counts["initial_review"] != 3
                or self.counts["final_review"] != 4
                or self.blockers
                or self.pending_repair
            )
        ):
            raise Invalid("Issue92 conserved initial review requires repaired verified content")
        if self.policy == "owner-led-v1" and operation == "remediation" and not self.author_session:
            raise Invalid("remediation requires completed implementation")
        if operation == "remediation" and not (
            self.initial_failed
            or self.pending_repair
            or (self.policy == "owner-led-v1" and self.blockers)
        ):
            raise Invalid("remediation requires initial review findings")
        if operation == "final_review" and not self.remediated:
            raise Invalid("final review requires completed remediation")
        if (
            self.policy == "owner-led-v1"
            and operation == "remediation"
            and self.verification_repair_count is not None
            and not self.blockers
        ):
            raise Invalid("failed verification requires frozen-criterion blocker")
        if (
            self.policy == "owner-led-v1"
            and operation == "verification"
            and self.verification_repair_count is not None
            and (
                self.counts["remediation"] < self.verification_repair_count
                or not self.remediated
                or self.blockers
            )
        ):
            raise Invalid("failed verification requires completed bounded remediation")
        if self.policy == "owner-led-v1" and operation in {"initial_review", "final_review"}:
            if (
                operation == "initial_review"
                and self.counts["remediation"] > self.inherited_counts["remediation"]
                and not (self.remainder and self.issue92_recovery_stage == "verified")
            ):
                raise Invalid("remediation requires final review")
            if (
                not self.verified
                or not self.accepted
                or not self.verified_content
                or self.verified_content != self.acceptance_content
            ):
                raise Invalid("review requires current matching verification and acceptance")


def replay(
    value: dict, now: datetime, *, predecessors: dict[int, dict] | None = None, root: Path = ROOT
) -> State:
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
            if (
                state.delivered
                and not (state.policy == "owner-led-v1" and kind == "continuation")
                and kind != "policy_transition"
            ) or (
                (state.split_remaining is not None or state.split_pool is not None)
                and kind != "split"
            ):
                raise Invalid("terminal history cannot be reopened")
            state.elapsed_seconds = state.elapsed(at)
            state.last = at
            if (
                state.issue92_recovery_stage == "repair_pending"
                and index > 6
                and not (
                    kind == "phase_start"
                    and isinstance(data, dict)
                    and data.get("phase") == "remediation"
                )
            ):
                raise Invalid("Issue92 recovery requires immediate ordinary remediation start")
            if (
                state.issue92_pr_identity_stage == "repair_pending"
                and index > 16
                and not (
                    kind == "phase_start"
                    and isinstance(data, dict)
                    and data.get("phase") == "remediation"
                )
            ):
                raise Invalid("Issue92 PR identity repair requires immediate remediation start")
            if (
                state.issue92_stage_fixture_stage == "repair_pending"
                and index > 23
                and not (
                    kind == "phase_start"
                    and isinstance(data, dict)
                    and data.get("phase") == "remediation"
                )
            ):
                raise Invalid("Issue92 stage fixture repair requires immediate remediation start")
            if (
                state.issue92_recovery_stage == "failed"
                and kind
                not in {
                    "blocker",
                    "charge",
                    "coordination_pause",
                    "coordination_resume",
                    "issue92_pr_identity_repair",
                }
                and state.issue92_pr_identity_ref is None
            ):
                raise Invalid("Issue92 completed recovery failure stops substantive events")
            if (
                state.issue92_pr_identity_stage == "failed"
                and kind
                not in {
                    "blocker",
                    "charge",
                    "coordination_pause",
                    "coordination_resume",
                    "issue92_stage_fixture_repair",
                }
                and state.issue92_stage_fixture_ref is None
            ):
                raise Invalid(
                    "Issue92 completed PR identity repair failure stops substantive events"
                )
            if state.issue92_stage_fixture_stage == "failed" and kind not in {
                "blocker",
                "charge",
                "coordination_pause",
                "coordination_resume",
            }:
                raise Invalid(
                    "Issue92 completed stage fixture repair failure stops substantive events"
                )
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
            expected_initial = initial_fields if bootstrap else initial_fields | {"capsule"}
            if not bootstrap and isinstance(data, dict) and data.get("policy") == "owner-led-v1":
                expected_initial = expected_initial | {"policy"}
            remainder = isinstance(data, dict) and "issue84_remainder" in data
            if remainder:
                expected_initial.add("issue84_remainder")
            data = keys(data, expected_initial)
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
            state.policy = data.get("policy", "timed-v1")
            if not bootstrap:
                if data["adoption"] is not None:
                    raise Invalid(
                        "future adoption forbidden; only approved Issue73 bootstrap exists"
                    )
                state.capsule = capsule(data["capsule"], state)
                if state.capsule["generation"] != 1:
                    raise Invalid("future initialization starts at capsule generation one")
                state.approved_owner = state.capsule["owner"]
                state.authorization_history.add(
                    normalized_evidence(state.capsule["authorization"]["evidence"])
                )
                if remainder:
                    if data["adoption"] is not None or data["predecessor"] is not None:
                        raise Invalid("Issue92 bootstrap cannot adopt or split")
                    initialize_remainder(state, data, root)
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
                state.predecessor = True
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
                    root=root,
                )
                if parent_state.repo != repo or issue not in parent_state.splits:
                    raise Invalid("predecessor did not allocate this successor")
                allocation = parent_state.splits[issue]
                if parent_state.policy == "owner-led-v1":
                    if (
                        state.policy != "owner-led-v1"
                        or allocation["successor_capsule"] != capsule_ref(state.capsule)
                        or allocation["authority"] != state.capsule["authorization"]
                    ):
                        raise Invalid("owner-led successor policy/capsule mismatch")
                    state.inherited_counts = allocation["counts"].copy()
                    state.authorization_history.update(allocation["authorizations"])
                    state.design_ref = state.challenge_ref = state.approved_ref = None
                else:
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
            state.authorization_history.add(
                normalized_evidence(state.capsule["authorization"]["evidence"])
            )
            state.design_ref = state.challenge_ref = state.approved_ref = capsule_ref(state.capsule)
            state.accepted = state.verified = state.reviewed = False
            if state.active:
                state.active["capsule"] = capsule_ref(state.capsule)
        elif kind == "issue92_recovery":
            data = keys(
                data,
                {
                    "version",
                    "authority",
                    "authority_anchor",
                    "capsule",
                    "prefix_digest",
                    "grant_digest",
                    "closeout_digest",
                    "proposal_digest",
                    "reason",
                },
            )
            authority(data["authority"], "user")
            require_capsule(data["capsule"], state)
            text(data["authority_anchor"])
            text(data["reason"])
            grant, _closeout, _manifest, stop, supplemental = recovery_sources(root)
            if (
                index != 6
                or state.issue != REMAINDER_ISSUE
                or state.repo != REMAINDER_REPO
                or not state.remainder
                or state.policy != "owner-led-v1"
                or value["events"][:6] != stop["events"]
                or digest({"schema": 1, "events": value["events"][:6]}) != RECOVERY_STOP
                or data["version"] != "issue92-single-recovery-v1"
                or data["prefix_digest"] != RECOVERY_STOP
                or data["grant_digest"] != RECOVERY_GRANT
                or data["closeout_digest"] != RECOVERY_CLOSEOUT
                or data["proposal_digest"] != RECOVERY_PROPOSAL
                or data["authority"] != grant["authority"]
                or data["authority_anchor"] != grant["authority_anchor"]
                or at < timestamp(grant["at"])
                or at < timestamp(supplemental["events"][-1]["at"])
                or state.counts
                != {
                    "implementation": 5,
                    "initial_review": 3,
                    "remediation": 4,
                    "final_review": 4,
                    "design_reset": 4,
                }
                or state.limits
                != {
                    "implementation": 5,
                    "initial_review": 4,
                    "remediation": 4,
                    "final_review": 4,
                    "design_reset": 4,
                }
                or state.local_verification_starts != 1
                or state.local_verification_limit != 1
                or state.active
                or state.suspended
                or state.author_session != RECOVERY_OWNER
                or state.approved_owner != grant["owner"]
                or state.publication_target is not None
                or state.verified
                or state.accepted
                or state.reviewed
                or state.delivered
                or state.verification_repair_count != 5
                or set(state.blockers) != {RECOVERY_BLOCKER}
                or state.blockers[RECOVERY_BLOCKER]["required_remediation"] != 5
            ):
                raise Invalid("Issue92 recovery requires exact stopped failed history")
            excluded = {normalized_evidence(item) for item in state.write_authors}
            excluded.update(
                {
                    normalized_evidence(RECOVERY_OWNER),
                    normalized_evidence(state.design_session),
                    normalized_evidence(state.challenge_session),
                }
            )
            design_session = supplemental["events"][0]["session"]
            challenge_session = supplemental["events"][2]["session"]
            if (
                normalized_evidence(design_session) in excluded
                or normalized_evidence(challenge_session) in excluded
                or normalized_evidence(design_session) == normalized_evidence(challenge_session)
            ):
                raise Invalid("Issue92 recovery challenge lacks independent session")
            identity = normalized_evidence(data["authority"]["evidence"])
            anchor = normalized_evidence(data["authority_anchor"])
            if (
                identity == anchor
                or identity in state.authorization_history
                or anchor in state.authorization_history
            ):
                raise Invalid("Issue92 recovery authority already consumed")
            state.authorization_history.update({identity, anchor})
            state.limits["remediation"] = 5
            state.local_verification_limit = 2
            state.pending_repair = True
            state.issue92_recovery_ref = {
                "grant_digest": RECOVERY_GRANT,
                "proposal_digest": RECOVERY_PROPOSAL,
                "closeout_digest": RECOVERY_CLOSEOUT,
            }
            state.issue92_recovery_stage = "repair_pending"
            state.issue92_recovery_supplemental = [
                {
                    "reservation": event.get("reservation"),
                    "type": event["type"],
                    "outcome": event.get("outcome"),
                    "session": event.get("session"),
                }
                for event in supplemental["events"]
                if event["type"] in {"phase_start", "phase_end"}
            ]
            state.issue92_review_disposition = grant["review_disposition"]
        elif kind == "issue92_pr_identity_repair":
            data = keys(
                data,
                {
                    "version",
                    "authority",
                    "authority_anchor",
                    "capsule",
                    "prefix_digest",
                    "grant_digest",
                    "source_manifest_digest",
                    "closeout_digest",
                    "proposal_digest",
                    "reason",
                },
            )
            authority(data["authority"], "user")
            require_capsule(data["capsule"], state)
            text(data["authority_anchor"])
            text(data["reason"])
            grant, _closeout, _manifest, stop, supplemental = pr_identity_sources(root)
            if (
                index != 16
                or state.issue != REMAINDER_ISSUE
                or state.repo != REMAINDER_REPO
                or not state.remainder
                or state.policy != "owner-led-v1"
                or value["events"][:16] != stop["events"]
                or digest({"schema": 1, "events": value["events"][:16]}) != PR_IDENTITY_STOP
                or data["version"] != "issue92-pr-identity-repair-v1"
                or data["prefix_digest"] != PR_IDENTITY_STOP
                or data["grant_digest"] != PR_IDENTITY_GRANT
                or data["source_manifest_digest"] != PR_IDENTITY_MANIFEST
                or data["closeout_digest"] != PR_IDENTITY_CLOSEOUT
                or data["proposal_digest"] != PR_IDENTITY_PROPOSAL
                or data["authority"] != grant["authority"]
                or data["authority_anchor"] != grant["authority_anchor"]
                or at < timestamp(grant["at"])
                or at < timestamp(supplemental["events"][-1]["at"])
                or state.counts
                != {
                    "implementation": 5,
                    "initial_review": 4,
                    "remediation": 5,
                    "final_review": 4,
                    "design_reset": 4,
                }
                or state.limits
                != {
                    "implementation": 5,
                    "initial_review": 4,
                    "remediation": 5,
                    "final_review": 4,
                    "design_reset": 4,
                }
                or state.local_verification_starts != 2
                or state.local_verification_limit != 2
                or not state.initial_failed
                or state.final_failed
                or state.issue92_recovery_stage != "failed"
                or state.issue92_recovery_failure != "initial_review"
                or state.verified_content != PR_IDENTITY_CONTENT
                or state.acceptance_content != PR_IDENTITY_CONTENT
                or not state.verified
                or not state.accepted
                or state.reviewed
                or state.delivered
                or state.active
                or state.suspended
                or state.publication_target is not None
                or state.delivery_history
                or state.author_session != RECOVERY_OWNER
                or state.approved_owner != grant["owner"]
                or state.issue92_pr_identity_ref is not None
                or set(state.blockers) != {PR_IDENTITY_BLOCKER}
                or state.blockers[PR_IDENTITY_BLOCKER]["required_remediation"] != 6
            ):
                raise Invalid("Issue92 PR identity repair requires exact failed-review stop")
            identity = normalized_evidence(data["authority"]["evidence"])
            anchor = normalized_evidence(data["authority_anchor"])
            if (
                identity == anchor
                or identity in state.authorization_history
                or anchor in state.authorization_history
            ):
                raise Invalid("Issue92 PR identity repair authority already consumed")
            state.authorization_history.update({identity, anchor})
            state.limits["remediation"] = 6
            state.limits["final_review"] = 5
            state.local_verification_limit = 3
            state.verified = state.accepted = state.reviewed = state.remediated = False
            state.verified_content = state.acceptance_content = state.review_content = None
            state.pending_repair = True
            state.issue92_pr_identity_ref = {
                "grant_digest": PR_IDENTITY_GRANT,
                "proposal_digest": PR_IDENTITY_PROPOSAL,
                "closeout_digest": PR_IDENTITY_CLOSEOUT,
            }
            state.issue92_pr_identity_stage = "repair_pending"
            state.issue92_pr_identity_supplemental = [
                {
                    "reservation": item.get("reservation"),
                    "type": item["type"],
                    "outcome": item.get("outcome"),
                    "session": item.get("session"),
                }
                for item in supplemental["events"]
                if item["type"] in {"phase_start", "phase_end"}
            ]
        elif kind == "issue92_stage_fixture_repair":
            data = keys(
                data,
                {
                    "version",
                    "authority",
                    "authority_anchor",
                    "capsule",
                    "prefix_digest",
                    "grant_digest",
                    "source_manifest_digest",
                    "closeout_digest",
                    "proposal_digest",
                    "reason",
                },
            )
            authority(data["authority"], "user")
            require_capsule(data["capsule"], state)
            text(data["authority_anchor"])
            text(data["reason"])
            grant, _closeout, _manifest, stop, supplemental = stage_fixture_sources(root)
            if (
                index != 23
                or state.issue != REMAINDER_ISSUE
                or state.repo != REMAINDER_REPO
                or not state.remainder
                or state.policy != "owner-led-v1"
                or value["events"][:23] != stop["events"]
                or digest({"schema": 1, "events": value["events"][:23]}) != STAGE_FIXTURE_STOP
                or data["version"] != "issue92-stage-fixture-repair-v1"
                or data["prefix_digest"] != STAGE_FIXTURE_STOP
                or data["grant_digest"] != STAGE_FIXTURE_GRANT
                or data["source_manifest_digest"] != STAGE_FIXTURE_MANIFEST
                or data["closeout_digest"] != STAGE_FIXTURE_CLOSEOUT
                or data["proposal_digest"] != STAGE_FIXTURE_PROPOSAL
                or data["authority"] != grant["authority"]
                or data["authority_anchor"] != grant["authority_anchor"]
                or at < timestamp(grant["at"])
                or at < timestamp(supplemental["events"][-1]["at"])
                or state.counts
                != {
                    "implementation": 5,
                    "initial_review": 4,
                    "remediation": 6,
                    "final_review": 4,
                    "design_reset": 4,
                }
                or state.limits
                != {
                    "implementation": 5,
                    "initial_review": 4,
                    "remediation": 6,
                    "final_review": 5,
                    "design_reset": 4,
                }
                or state.local_verification_starts != 3
                or state.local_verification_limit != 3
                or not state.initial_failed
                or state.final_failed
                or state.issue92_recovery_stage != "failed"
                or state.issue92_recovery_failure != "initial_review"
                or state.issue92_pr_identity_stage != "failed"
                or state.issue92_pr_identity_failure != {"phase": "verification", "event_index": 22}
                or state.verification_repair_count != 7
                or state.verified
                or state.accepted
                or state.reviewed
                or state.delivered
                or state.verified_content
                or state.acceptance_content
                or state.review_content
                or state.active
                or state.suspended
                or state.publication_target is not None
                or state.delivery_history
                or state.author_session != RECOVERY_OWNER
                or state.approved_owner != grant["owner"]
                or state.issue92_stage_fixture_ref is not None
                or set(state.blockers) != {STAGE_FIXTURE_BLOCKER}
                or state.blockers[STAGE_FIXTURE_BLOCKER]["required_remediation"] != 7
            ):
                raise Invalid(
                    "Issue92 stage fixture repair requires exact failed-verification stop"
                )
            evidence = normalized_evidence(data["authority"]["evidence"])
            anchor = normalized_evidence(data["authority_anchor"])
            if (
                evidence == anchor
                or evidence in state.authorization_history
                or anchor in state.authorization_history
            ):
                raise Invalid("Issue92 stage fixture authority already consumed")
            state.authorization_history.update({evidence, anchor})
            state.limits["remediation"] = 7
            state.local_verification_limit = 4
            state.verified = state.accepted = state.reviewed = state.remediated = False
            state.verified_content = state.acceptance_content = state.review_content = None
            state.pending_repair = True
            state.issue92_stage_fixture_ref = {
                "grant_digest": STAGE_FIXTURE_GRANT,
                "proposal_digest": STAGE_FIXTURE_PROPOSAL,
                "closeout_digest": STAGE_FIXTURE_CLOSEOUT,
            }
            state.issue92_stage_fixture_stage = "repair_pending"
            state.issue92_stage_fixture_supplemental = [
                {
                    "reservation": item["data"].get("reservation"),
                    "type": item["type"],
                    "outcome": item["data"].get("outcome"),
                    "session": item["data"].get("session"),
                }
                for item in supplemental["events"]
                if item["type"] in {"phase_start", "phase_end"}
            ]
        elif kind == "phase_start":
            historical = bootstrap and index < BOOTSTRAP_EVENTS
            expected = {"phase", "session", "role"}
            if not historical:
                expected.add("capsule")
                if data.get("phase") in {"initial_review", "final_review", "verification"}:
                    expected.add("content")
                if state.policy == "owner-led-v1" and data.get("phase") == "design_reset":
                    expected.update({"criterion", "reason"})
            data = keys(data, expected)
            phase, session = text(data["phase"]), text(data["session"])
            if state.policy == "owner-led-v1" and phase == "design_reset":
                if data["criterion"] not in {*state.invariants, *state.acceptance}:
                    raise Invalid("design reset requires frozen criterion")
                text(data["reason"])
            state.gate(phase, at, allow_bootstrap=historical)
            if not historical:
                require_capsule(data["capsule"], state)
                if "content" in data:
                    sha(data["content"])
                if (
                    state.policy == "owner-led-v1"
                    and phase in {"initial_review", "final_review"}
                    and (
                        data["content"] != state.verified_content
                        or data["content"] != state.acceptance_content
                    )
                ):
                    raise Invalid("review reservation differs from verified accepted content")
            if data["role"] not in ROLES[phase]:
                raise Invalid("phase role mismatch")
            if phase == "design_reset" and session in state.sessions:
                raise Invalid("design reset requires a fresh architect session")
            review_exclusions = {state.design_session, *state.write_authors}
            if state.remainder:
                review_exclusions.add(state.challenge_session)
                review_exclusions.update(
                    item["session"]
                    for item in state.historical_reservations
                    if item.get("phase") in {"design", "design_reset", "challenge"}
                    and isinstance(item.get("session"), str)
                )
                review_exclusions.update(
                    item["session"]
                    for item in state.issue92_recovery_supplemental
                    if item["type"] == "phase_start" and item.get("session")
                )
                review_exclusions.update(
                    item["session"]
                    for item in state.issue92_pr_identity_supplemental
                    if item["type"] == "phase_start" and item.get("session")
                )
                review_exclusions.update(
                    item["session"]
                    for item in state.issue92_stage_fixture_supplemental
                    if item["type"] == "phase_start" and item.get("session")
                )
            if phase in {"challenge", "initial_review", "final_review"} and (
                normalized_evidence(session)
                in {normalized_evidence(item) for item in review_exclusions if item}
                if state.remainder
                else session in review_exclusions
            ):
                raise Invalid("independent read-only session required")
            if (
                state.issue92_pr_identity_ref
                and phase == "final_review"
                and (
                    normalized_evidence(session)
                    in {normalized_evidence(item) for item in state.sessions}
                )
            ):
                raise Invalid("independent read-only session required")
            if phase in {"implementation", "remediation", "verification"} and session in {
                state.design_session,
                state.challenge_session,
            }:
                raise Invalid("separate write-capable session required")
            if session in state.sessions and state.sessions[session] != data["role"]:
                raise Invalid("role change requires a fresh separate session")
            state.sessions[session] = data["role"]
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
            if state.remainder and phase == "verification":
                state.local_verification_starts += 1
            if state.issue92_recovery_ref and not state.issue92_pr_identity_ref:
                if phase == "remediation":
                    state.issue92_recovery_stage = "repairing"
                elif phase == "verification":
                    state.issue92_recovery_stage = "verifying"
                elif phase == "initial_review":
                    state.issue92_recovery_stage = "reviewing"
            if state.issue92_pr_identity_ref and not state.issue92_stage_fixture_ref:
                if phase == "remediation":
                    state.issue92_pr_identity_stage = "repairing"
                elif phase == "verification":
                    state.issue92_pr_identity_stage = "verifying"
                elif phase == "final_review":
                    state.issue92_pr_identity_stage = "reviewing"
            if state.issue92_stage_fixture_ref:
                if phase == "remediation":
                    state.issue92_stage_fixture_stage = "repairing"
                elif phase == "verification":
                    state.issue92_stage_fixture_stage = "verifying"
                elif phase == "final_review":
                    state.issue92_stage_fixture_stage = "reviewing"
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
                if state.policy == "owner-led-v1":
                    state.acceptance_content = state.verified_content = state.review_content = None
            if state.policy == "owner-led-v1" and phase == "verification":
                state.verified = state.accepted = state.reviewed = False
                state.verified_content = state.acceptance_content = state.review_content = None
            if state.policy == "owner-led-v1" and phase == "remediation":
                state.remediated = False
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
            state.authorization_history.add(
                normalized_evidence(revised["authorization"]["evidence"])
            )
            state.active["capsule"] = capsule_ref(revised)
        elif kind == "owner_handoff":
            if state.remainder:
                raise Invalid("Issue92 grant forbids owner replacement")
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
            if state.lineage_transition:
                data = keys(data, {"session", "authority", "capsule", "reason"})
                authority(data["authority"], "user")
                require_capsule(data["capsule"], state)
                text(data["reason"])
                identity = normalized_evidence(data["authority"]["evidence"])
                if identity in state.authorization_history:
                    raise Invalid("Issue83 resume needs distinct finite user authority")
                state.authorization_history.add(identity)
            else:
                data = keys(data, {"session"})
            if state.active or not state.suspended or data["session"] != state.suspended["session"]:
                raise Invalid("no matching interrupted session")
            if (
                (state.policy == "timed-v1" and state.elapsed(at) >= state.budget_seconds)
                or state.delivered
                or state.split_remaining is not None
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
                if (
                    state.issue92_recovery_ref
                    and not state.issue92_pr_identity_ref
                    and phase
                    in {
                        "remediation",
                        "verification",
                        "initial_review",
                    }
                ):
                    if data["outcome"] == "fail":
                        state.issue92_recovery_stage = "failed"
                        state.issue92_recovery_failure = phase
                    else:
                        state.issue92_recovery_stage = {
                            "remediation": "repaired",
                            "verification": "verified",
                            "initial_review": "reviewed",
                        }[phase]
                if (
                    state.issue92_pr_identity_ref
                    and not state.issue92_stage_fixture_ref
                    and phase
                    in {
                        "remediation",
                        "verification",
                        "final_review",
                    }
                ):
                    if data["outcome"] == "fail":
                        state.issue92_pr_identity_stage = "failed"
                        state.issue92_pr_identity_failure = {
                            "phase": phase,
                            "event_index": index + 1,
                        }
                    else:
                        state.issue92_pr_identity_stage = {
                            "remediation": "repaired",
                            "verification": "verified",
                            "final_review": "reviewed",
                        }[phase]
                if state.issue92_stage_fixture_ref and phase in {
                    "remediation",
                    "verification",
                    "final_review",
                }:
                    if data["outcome"] == "fail":
                        state.issue92_stage_fixture_stage = "failed"
                        state.issue92_stage_fixture_failure = {
                            "phase": phase,
                            "event_index": index + 1,
                        }
                    else:
                        state.issue92_stage_fixture_stage = {
                            "remediation": "repaired",
                            "verification": "verified",
                            "final_review": "reviewed",
                        }[phase]
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
            ):
                raise Invalid("coordination pause/resume requires nonterminal between-phase state")
            running = kind == "coordination_resume"
            if state.clock_running == running:
                raise Invalid("duplicate coordination pause/resume")
            if running and state.policy == "timed-v1" and state.elapsed(at) >= state.budget_seconds:
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
            if state.policy == "owner-led-v1" and (
                not state.verified or data["content"] != state.verified_content
            ):
                raise Invalid("acceptance requires current matching verification")
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
            if state.issue92_stage_fixture_ref and (
                data["id"] != STAGE_FIXTURE_BLOCKER
                or state.issue92_stage_fixture_stage != "repaired"
                or state.counts["remediation"] != 7
            ):
                raise Invalid("Issue92 stage fixture blocker requires seventh successful repair")
            if (
                state.issue92_pr_identity_ref
                and not state.issue92_stage_fixture_ref
                and (
                    data["id"] != PR_IDENTITY_BLOCKER
                    or state.issue92_pr_identity_stage != "repaired"
                    or state.counts["remediation"] != 6
                )
            ):
                raise Invalid("Issue92 PR identity blocker requires sixth successful repair")
            if (
                state.issue92_recovery_ref
                and not state.issue92_pr_identity_ref
                and (
                    data["id"] != RECOVERY_BLOCKER
                    or state.issue92_recovery_stage != "repaired"
                    or state.counts["remediation"] != 5
                )
            ):
                raise Invalid("Issue92 blocker resolution requires successful single repair")
            if (
                not state.remediated
                or state.counts["remediation"] < state.blockers[data["id"]]["required_remediation"]
            ):
                raise Invalid("blocker resolution requires completed remediation evidence")
            del state.blockers[data["id"]]
        elif kind == "policy_transition":
            data = keys(data, {"policy", "authority", "capsule", "reason"})
            authority(data["authority"], "user")
            text(data["reason"])
            require_capsule(data["capsule"], state)
            if (
                data["policy"] != "owner-led-v1"
                or state.policy != "timed-v1"
                or state.active
                or state.suspended
                or state.predecessor
                or state.splits
                or state.split_remaining is not None
            ):
                raise Invalid("invalid owner-led policy transition")
            normalized = normalized_evidence(data["authority"]["evidence"])
            capsule_authority = normalized_evidence(state.capsule["authorization"]["evidence"])
            if normalized in state.authorization_history and normalized != capsule_authority:
                raise Invalid("policy transition authorization already consumed")
            state.policy = "owner-led-v1"
            state.authorization_history.update(
                normalized_evidence(item) for item in state.extension_authorizations
            )
            state.authorization_history.add(normalized)
        elif kind == "lineage_policy_transition":
            data = keys(
                data,
                {
                    "policy",
                    "authority",
                    "capsule",
                    "prefix_digest",
                    "predecessor",
                    "time_barrier",
                    "reason",
                },
            )
            authority(data["authority"], "user")
            require_capsule(data["capsule"], state)
            text(data["reason"])
            parent_ref = keys(data["predecessor"], {"issue", "events", "digest"})
            if (
                state.issue != 83
                or state.repo != REMAINDER_REPO
                or index != 9
                or digest({"schema": 1, "events": value["events"][:9]}) != ISSUE83_DIGEST
                or data["prefix_digest"] != ISSUE83_DIGEST
                or parent_ref != {"issue": 23, "events": 10, "digest": ISSUE23_DIGEST}
                or data["policy"] != "owner-led-v1"
                or data["time_barrier"] != "B83-EXHAUSTED"
                or state.policy != "timed-v1"
                or not predecessors
                or 23 not in predecessors
            ):
                raise Invalid("lineage transition is restricted to exact Issue23/83 pair")
            parent = predecessors[23]
            if len(parent["events"]) != 10 or digest(parent) != ISSUE23_DIGEST:
                raise Invalid("Issue23 complete historical prefix changed")
            parent_state = replay(parent, at, root=root)
            if (
                parent_state.split_remaining != 5
                or set(parent_state.splits) != {83}
                or parent_state.splits[83]["seconds"] != 6051
            ):
                raise Invalid("Issue23 retained five timed seconds changed")
            reservation = value["events"][6]
            if (
                reservation["type"] != "phase_start"
                or state.active is not None
                or state.suspended != {**reservation["data"], "at": reservation["at"]}
                or state.suspended["phase"] != "implementation"
                or state.suspended["session"] != "/root/issue83_implementation"
                or state.clock_running
                or state.counts["implementation"] != 1
                or state.limits["implementation"] != 1
                or state.author_session is not None
                or state.verified
                or state.accepted
                or state.reviewed
                or state.delivered
                or value["events"][7]["type"] != "phase_end"
                or value["events"][7]["data"]["outcome"] != "interrupted"
                or "B83-EXHAUSTED" not in state.blockers
            ):
                raise Invalid("Issue83 retained suspended reservation changed")
            state.authorization_history.update(inherited_identities(parent))
            normalized = normalized_evidence(data["authority"]["evidence"])
            if normalized in state.authorization_history:
                raise Invalid("lineage transition authority already consumed")
            state.authorization_history.add(normalized)
            state.policy = "owner-led-v1"
            state.lineage_transition = True
            state.ancestor_split_remaining_seconds = parent_state.split_remaining
            state.historical_timed_debt_seconds = max(0, state.elapsed(at) - state.budget_seconds)
        elif kind == "continuation":
            if state.remainder:
                raise Invalid("Issue92 grant forbids continuation")
            data = keys(data, {"authority", "capsule", "counts", "reason"})
            authority(data["authority"], "user")
            require_capsule(data["capsule"], state)
            text(data["reason"])
            counts = keys(data["counts"], set(COUNTS))
            deltas = {phase: integer(delta) for phase, delta in counts.items()}
            normalized = normalized_evidence(data["authority"]["evidence"])
            if normalized in state.authorization_history:
                raise Invalid("continuation authorization already consumed")
            if (
                state.policy != "owner-led-v1"
                or state.active
                or state.suspended
                or state.predecessor
                or state.splits
                or state.split_remaining is not None
                or not state.author_session
                or not state.ready
                or not deltas["remediation"]
                or (
                    (
                        state.review_required
                        or state.counts["initial_review"]
                        or state.counts["final_review"]
                    )
                    and not deltas["final_review"]
                )
            ):
                raise Invalid("invalid finite continuation")
            state.authorization_history.add(normalized)
            for phase, delta in deltas.items():
                state.limits[phase] += delta
            state.delivered = False
            state.verified = state.accepted = state.reviewed = state.remediated = False
            state.verified_content = state.acceptance_content = state.review_content = None
            state.final_failed = False
            state.pending_repair = True
        elif kind == "extension":
            if state.remainder:
                raise Invalid("Issue92 grant forbids extension")
            data = keys(data, {"authority", "seconds", "counts", "reason"})
            authority(data["authority"], "user")
            authorization = evidence_key(data["authority"]["evidence"])
            normalized = normalized_evidence(data["authority"]["evidence"])
            if authorization in state.extension_authorizations or (
                state.policy == "owner-led-v1" and normalized in state.authorization_history
            ):
                raise Invalid("finite extension authorization already consumed")
            text(data["reason"])
            seconds = integer(data["seconds"])
            counts = keys(data["counts"], set(COUNTS))
            deltas = {k: integer(v) for k, v in counts.items()}
            if state.policy == "owner-led-v1" and (seconds != 0 or not any(deltas.values())):
                raise Invalid("owner-led extension requires count grant and zero seconds")
            if (
                state.active
                or state.delivered
                or state.split_remaining is not None
                or not (seconds or any(deltas.values()))
            ):
                raise Invalid("invalid extension or terminal/active ticket")
            state.budget_seconds += seconds
            state.extension_authorizations.add(authorization)
            state.authorization_history.add(normalized)
            for phase, delta in deltas.items():
                state.limits[phase] += delta
            if state.final_failed:
                if not deltas["final_review"] or not deltas["remediation"]:
                    raise Invalid(
                        "failed final review extension must bound remediation and final review"
                    )
                state.final_failed = False
                state.remediated = False
                if state.policy == "owner-led-v1":
                    state.verified = state.accepted = state.reviewed = False
                    state.verified_content = state.acceptance_content = state.review_content = None
                    state.pending_repair = True
        elif kind == "charge":
            data = keys(data, {"authority", "seconds", "evidence"})
            authority(data["authority"], "coordinator")
            text(data["evidence"])
            state.elapsed_seconds += integer(data["seconds"], 1)
        elif kind == "split":
            if state.remainder:
                raise Invalid("Issue92 grant forbids split")
            if state.policy == "owner-led-v1":
                data = keys(
                    data,
                    {"authority", "capsule", "successor", "successor_capsule", "counts", "reason"},
                )
                authority(data["authority"], "user")
                require_capsule(data["capsule"], state)
                successor = integer(data["successor"], 1)
                child_ref = keys(data["successor_capsule"], {"id", "generation", "digest"})
                text(child_ref["id"])
                integer(child_ref["generation"], 1)
                sha(child_ref["digest"])
                text(data["reason"])
                allocated = {
                    key: integer(value) for key, value in keys(data["counts"], set(COUNTS)).items()
                }
                identity = normalized_evidence(data["authority"]["evidence"])
                if (
                    identity in state.authorization_history
                    or state.active
                    or state.suspended
                    or state.delivered
                    or state.blockers
                    or state.final_failed
                    or state.pending_repair
                    or successor in state.splits
                    or successor == state.issue
                    or not any(allocated.values())
                ):
                    raise Invalid("invalid owner-led split or reused authority")
                if state.split_pool is None:
                    state.split_pool = {
                        key: state.limits[key] - state.counts[key] for key in COUNTS
                    }
                    if any(value < 0 for value in state.split_pool.values()):
                        raise Invalid("negative owner-led allowance pool")
                    state.clock_running = False
                if any(allocated[key] > state.split_pool[key] for key in COUNTS):
                    raise Invalid("successor allocations exceed remaining counts")
                for key in COUNTS:
                    state.split_pool[key] -= allocated[key]
                state.authorization_history.add(identity)
                state.splits[successor] = {
                    "authority": data["authority"],
                    "counts": state.counts.copy(),
                    "limits": {key: state.counts[key] + allocated[key] for key in COUNTS},
                    "allocation": allocated,
                    "successor_capsule": child_ref,
                    "extensions": sorted(state.extension_authorizations),
                    "authors": sorted(state.write_authors),
                    "sessions": state.sessions.copy(),
                    "authorizations": sorted(state.authorization_history),
                }
                state.last = at
                continue
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
                "seconds": seconds,
                "counts": state.counts.copy(),
                "limits": state.limits.copy(),
                "extensions": sorted(state.extension_authorizations),
                "authors": sorted(state.write_authors),
                "sessions": state.sessions.copy(),
            }
        elif kind == "publication_target":
            data = keys(data, {"repo", "pr", "grant_digest", "evidence"})
            if (
                not state.remainder
                or state.publication_target is not None
                or not state.reviewed
                or state.active
                or state.suspended
            ):
                raise Invalid("Issue92 publication target requires one clean review")
            if state.issue92_stage_fixture_ref and (
                state.issue92_stage_fixture_stage != "reviewed"
                or state.pending_repair
                or state.blockers
                or not state.verified
                or not state.accepted
                or state.review_content != state.verified_content
                or state.acceptance_content != state.verified_content
            ):
                raise Invalid(
                    "Issue92 stage fixture target requires current certified final review"
                )
            if (
                state.issue92_pr_identity_ref
                and not state.issue92_stage_fixture_ref
                and (
                    state.issue92_pr_identity_stage != "reviewed"
                    or state.pending_repair
                    or state.blockers
                    or not state.verified
                    or not state.accepted
                    or state.review_content != state.verified_content
                    or state.acceptance_content != state.verified_content
                )
            ):
                raise Invalid("Issue92 PR identity target requires current certified final review")
            if (
                state.issue92_recovery_ref
                and not state.issue92_pr_identity_ref
                and (
                    state.issue92_recovery_stage != "reviewed"
                    or state.pending_repair
                    or state.blockers
                    or not state.verified
                    or not state.accepted
                    or state.review_content != state.verified_content
                    or state.acceptance_content != state.verified_content
                )
            ):
                raise Invalid("Issue92 recovered target requires current certified content")
            if (
                data["repo"] != REMAINDER_REPO
                or integer(data["pr"], 1) == 85
                or data["grant_digest"] != REMAINDER_GRANT
            ):
                raise Invalid("Issue92 publication target differs from finite grant")
            text(data["evidence"])
            state.publication_target = {"repo": data["repo"], "pr": data["pr"]}
        elif kind == "delivery":
            data = keys(data, {"evidence", "pr", "repo", "content", "capsule"})
            text(data["evidence"])
            integer(data["pr"], 1)
            require_capsule(data["capsule"], state)
            if data["repo"] != state.repo or sha(data["content"]) != state.verified_content:
                raise Invalid("delivery identity/content mismatch")
            if state.remainder and state.publication_target != {
                "repo": data["repo"],
                "pr": data["pr"],
            }:
                raise Invalid("Issue92 delivery requires its new publication target")
            if state.delivery_history and (data["repo"], data["pr"]) != (
                state.delivery_history[0]["repo"],
                state.delivery_history[0]["pr"],
            ):
                raise Invalid("continuation must use original repository and PR")
            state.gate("delivery", at)
            state.delivered = True
            if state.issue92_stage_fixture_ref:
                state.issue92_stage_fixture_stage = "delivered"
            elif state.issue92_pr_identity_ref:
                state.issue92_pr_identity_stage = "delivered"
            elif state.issue92_recovery_ref:
                state.issue92_recovery_stage = "delivered"
            state.delivery_binding = {
                "pr": data["pr"],
                "repo": data["repo"],
                "content": data["content"],
            }
            state.delivery_history.append(state.delivery_binding.copy())
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
        if state.policy == "owner-led-v1":
            state.verification_repair_count = (
                None if outcome == "pass" else state.counts["remediation"] + 1
            )
    elif phase == "initial_review":
        state.reviewed = outcome == "pass"
        state.initial_failed = outcome != "pass"
        state.review_content = (
            state.active.get("content") if outcome == "pass" and state.active else None
        )
    elif phase == "remediation":
        state.remediated = outcome == "pass"
        if state.policy == "owner-led-v1" and outcome == "pass":
            state.pending_repair = False
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


def lineage_audit(ledgers: dict[int, dict], root: Path, now: datetime) -> None:
    """Conserve current sibling grants irrespective of append order."""
    parent_of: dict[int, int] = {}
    allocations: dict[int, int] = {}
    for issue, value in ledgers.items():
        initial = value["events"][0]["data"]
        predecessor = initial.get("predecessor")
        if predecessor is not None:
            parent = integer(predecessor["issue"], 1)
            if parent not in ledgers or parent == issue:
                raise Invalid("missing or cyclic predecessor")
            parent_of[issue] = parent
        for event in value["events"]:
            if event["type"] == "split":
                successor = integer(event["data"]["successor"], 1)
                if successor in allocations:
                    raise Invalid("duplicate successor allocation across lineages")
                allocations[successor] = issue
    for issue in parent_of:
        visited = {issue}
        cursor = issue
        while cursor in parent_of:
            cursor = parent_of[cursor]
            if cursor in visited:
                raise Invalid("cyclic ticket lineage")
            visited.add(cursor)

    def lineage(issue: int) -> int:
        while issue in parent_of:
            issue = parent_of[issue]
        return issue

    consumed: dict[int, dict[str, tuple[int, int, str]]] = {}
    for issue, value in ledgers.items():
        root_issue = lineage(issue)
        identities = consumed.setdefault(root_issue, {})
        for index, event in enumerate(value["events"]):
            kind = event["type"]
            data = event["data"]
            if kind == "initialize":
                auth = data.get("capsule", {}).get("authorization")
                if not auth:
                    continue
                if issue in parent_of:
                    # The successor capsule can cite its own allocated split grant.
                    continue
                identities.setdefault(
                    normalized_evidence(auth["evidence"]), (issue, index, "initial")
                )
                continue
            if kind not in {
                "split",
                "extension",
                "continuation",
                "policy_transition",
                "lineage_policy_transition",
                "issue92_recovery",
                "issue92_pr_identity_repair",
                "issue92_stage_fixture_repair",
            }:
                continue
            auth = data["authority"]
            key = normalized_evidence(auth["evidence"])
            prior = identities.get(key)
            initial_policy = value["events"][0]["data"].get("policy", "timed-v1")
            transitioned = any(
                earlier["type"] in {"policy_transition", "lineage_policy_transition"}
                for earlier in value["events"][:index]
            )
            historical_timed = (
                initial_policy == "timed-v1" and not transitioned and kind in {"split", "extension"}
            )
            if prior and not (
                (historical_timed and prior[2] in {"timed", "initial"})
                or (kind == "policy_transition" and prior == (issue, 0, "initial"))
            ):
                raise Invalid("approval evidence reused in whole ticket lineage")
            identities[key] = (issue, index, "timed" if historical_timed else kind)
            anchor = (
                data.get("authority_anchor")
                if kind
                in {
                    "issue92_recovery",
                    "issue92_pr_identity_repair",
                    "issue92_stage_fixture_repair",
                }
                else auth.get("anchor")
            )
            if anchor:
                normalized_anchor = normalized_evidence(anchor)
                previous_anchor = identities.get(normalized_anchor)
                if previous_anchor and (not historical_timed or previous_anchor[2] != "timed"):
                    raise Invalid("authority anchor reused in whole ticket lineage")
                identities[normalized_anchor] = (
                    issue,
                    index,
                    "timed" if historical_timed else kind,
                )
    # The pinned exhausted source is claimable by exactly the designated target.
    claims = [
        issue
        for issue, value in ledgers.items()
        if "issue84_remainder" in value["events"][0]["data"]
    ]
    if claims and claims != [REMAINDER_ISSUE]:
        raise Invalid("Issue84 exhausted source claimed by another ticket")
    recoveries = [
        issue
        for issue, value in ledgers.items()
        for event in value["events"]
        if event["type"] == "issue92_recovery"
    ]
    if recoveries and recoveries != [REMAINDER_ISSUE]:
        raise Invalid("Issue92 recovery marker claimed outside its one ledger")
    pr_repairs = [
        issue
        for issue, value in ledgers.items()
        for event in value["events"]
        if event["type"] == "issue92_pr_identity_repair"
    ]
    if pr_repairs and pr_repairs != [REMAINDER_ISSUE]:
        raise Invalid("Issue92 PR identity marker claimed outside its one ledger")
    fixture_repairs = [
        issue
        for issue, value in ledgers.items()
        for event in value["events"]
        if event["type"] == "issue92_stage_fixture_repair"
    ]
    if fixture_repairs and fixture_repairs != [REMAINDER_ISSUE]:
        raise Invalid("Issue92 stage fixture marker claimed outside its one ledger")
    for issue, value in ledgers.items():
        replay(
            value,
            now,
            predecessors={key: item for key, item in ledgers.items() if key != issue},
            root=root,
        )


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
    lineage_audit(ledgers, root, now)
    return ledgers


def ledger_bytes(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted((root / DIRECTORY).glob("*.json"))}


def working_bytes(root: Path, issue: int) -> dict[str, str]:
    """Raw bytes and membership for the cooperating writer's final race check."""
    names = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root
        )
        .decode()
        .split("\0")
    )
    excluded = f"{DIRECTORY.as_posix()}/issue-{issue}.json"
    observed = {}
    for name in sorted(set(names) - {""}):
        if name == excluded or (
            name.startswith(f"{DIRECTORY.as_posix()}/")
            and (name.endswith(".lock") or name.endswith(".tmp"))
        ):
            continue
        path = root / name
        if path.is_symlink():
            data = os.readlink(path).encode()
            kind = "symlink"
        elif path.is_file():
            data = path.read_bytes()
            kind = "file"
        else:
            kind, data = "missing", b""
        observed[name] = f"{kind}:{hashlib.sha256(data).hexdigest()}"
    return observed


def append(
    root: Path, issue: int, event: dict, now: datetime, source_path: Path | None = None
) -> State:
    """One writer, lock, validate candidate, atomic replace; never rewrite prior events."""
    path = root / DIRECTORY / f"issue-{integer(issue, 1)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = root / DIRECTORY / ".repository.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0), 0o600)
    except FileExistsError as exc:
        raise Invalid("another writer or abandoned lock; coordinator must inspect") from exc
    try:
        lock_token = os.urandom(16)
        os.write(fd, lock_token)
        os.fsync(fd)
        os.close(fd)
        event = json.loads(json.dumps(event, allow_nan=False), object_pairs_hook=unique)
        source_bytes = source_path.read_bytes() if source_path is not None else None
        if source_bytes is not None:
            source_event = json.loads(
                source_bytes.decode("utf-8"),
                object_pairs_hook=unique,
                parse_constant=lambda _: (_ for _ in ()).throw(Invalid("nonfinite JSON")),
            )
            if digest(source_event) != digest(event):
                raise Invalid("event source differs from supplied event")
        original_files = ledger_bytes(root)
        if event.get("type") == "lineage_policy_transition" and (
            issue != 83
            or any(
                hashlib.sha256(original_files.get(f"issue-{number}.json", b"")).hexdigest()
                != expected
                for number, expected in ((23, ISSUE23_RAW_SHA256), (83, ISSUE83_RAW_SHA256))
            )
        ):
            raise Invalid("Issue23/83 raw retained histories differ from exact transition sources")
        original_content = content_digest(root, issue)
        original_working = working_bytes(root, issue)
        ledgers = read_all(root)
        if issue not in ledgers and (
            not isinstance(event, dict)
            or event.get("type") != "initialize"
            or not isinstance(event.get("data"), dict)
            or event["data"].get("policy") != "owner-led-v1"
        ):
            raise Invalid("new ticket creation requires explicit owner-led-v1 policy")
        value = ledgers.get(issue, {"schema": 1, "events": []})
        if event.get("type") == "publication_target" and issue == REMAINDER_ISSUE:
            prior = replay(
                value, now, predecessors={k: v for k, v in ledgers.items() if k != issue}, root=root
            )
            if prior.issue92_recovery_ref and (
                prior.verified_content != original_content
                or prior.acceptance_content != original_content
                or prior.review_content != original_content
            ):
                raise Invalid("Issue92 recovered publication target differs from current content")
        if (
            event.get("type") == "phase_start"
            and event.get("data", {}).get("phase")
            in {
                "initial_review",
                "final_review",
                "verification",
            }
            and event["data"].get("content") != original_content
        ):
            raise Invalid("phase reservation does not match current repository content")
        if event.get("type") in {"phase_end", "acceptance", "delivery"} and value["events"]:
            prior = replay(
                value, now, predecessors={k: v for k, v in ledgers.items() if k != issue}, root=root
            )
            expected = event.get("data", {}).get("content")
            if (
                event["type"] == "phase_end"
                and event.get("data", {}).get("outcome") == "pass"
                and prior.active
                and prior.active["phase"] in {"initial_review", "final_review", "verification"}
            ):
                expected = prior.active.get("content")
            if expected is not None and expected != original_content:
                raise Invalid("repository content changed after recorded verification/review")
        candidate = {"schema": 1, "events": [*value["events"], event]}
        state = replay(
            candidate, now, predecessors={k: v for k, v in ledgers.items() if k != issue}, root=root
        )
        lineage_audit({**ledgers, issue: candidate}, root, now)
        if state.issue != issue:
            raise Invalid("requested issue differs from initialized issue")
        expected_temp = (json.dumps(candidate, indent=2, allow_nan=False) + "\n").encode("utf-8")
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, delete=False, suffix=".tmp"
        ) as target:
            target.write(expected_temp)
            target.flush()
            os.fsync(target.fileno())
            temp = Path(target.name)
        try:
            current_working = working_bytes(root, issue)
            current_source = source_path.read_bytes() if source_path is not None else None
            current_content = content_digest(root, issue)
            current_temp = temp.read_bytes()
            current_ledgers = ledger_bytes(root)
            if (
                current_source != source_bytes
                or current_ledgers != original_files
                or current_temp != expected_temp
                or current_content != original_content
                or current_working != original_working
            ):
                raise Invalid("append input changed before atomic replace")
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        return state
    finally:
        if lock.exists() and lock.read_bytes() == lock_token:
            lock.unlink()


def check_prefix(
    root: Path, base: str, ledgers: dict[int, dict], now: datetime | None = None
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
    checked_at = now or datetime.now(UTC)
    for issue in ledgers.keys() - originals.keys():
        initial = ledgers[issue]["events"][0]["data"]
        state = replay(
            ledgers[issue],
            checked_at,
            predecessors={key: value for key, value in ledgers.items() if key != issue},
            root=root,
        )
        if initial.get("policy", "timed-v1") != "owner-led-v1":
            exact_pair = (
                issue in {23, 83}
                and 23 in ledgers
                and 83 in ledgers
                and len(ledgers[23]["events"]) == 10
                and digest(ledgers[23]) == ISSUE23_DIGEST
                and len(ledgers[83]["events"]) >= 10
                and digest({"schema": 1, "events": ledgers[83]["events"][:9]}) == ISSUE83_DIGEST
                and ledgers[83]["events"][9]["type"] == "lineage_policy_transition"
                and state.repo == REMAINDER_REPO
            )
            if exact_pair:
                continue
            raise Invalid("new ledger introduction requires current owner-led-v1 policy")
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
    root: Path = ROOT,
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
        ledgers[issue],
        now,
        predecessors={k: v for k, v in ledgers.items() if k != issue},
        root=root,
    )
    if state.repo != event["repository"]["full_name"]:
        raise Invalid("PR repository differs from ledger")
    if state.remainder and (
        pr["head"]["ref"] != f"codex/issue-{REMAINDER_ISSUE}-issue84-remainder"
        or pr["head"].get("repo", {}).get("full_name") != REMAINDER_REPO
        or pr["base"]["ref"] != "main"
        or pr["base"].get("repo", {}).get("full_name") != state.repo
        or state.publication_target != {"repo": state.repo, "pr": event["number"]}
        or integer(event["number"], 1) == 85
        or timestamp(pr["created_at"]) <= timestamp(ledgers[issue]["events"][0]["at"])
        or (
            state.issue92_recovery_ref
            and timestamp(pr["created_at"]) <= timestamp(ledgers[issue]["events"][6]["at"])
        )
        or (
            state.issue92_pr_identity_ref
            and timestamp(pr["created_at"]) <= timestamp(ledgers[issue]["events"][16]["at"])
        )
        or (
            state.issue92_stage_fixture_ref
            and timestamp(pr["created_at"]) <= timestamp(ledgers[issue]["events"][23]["at"])
        )
    ):
        raise Invalid("Issue92 publication PR identity differs from finite grant")
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
    """Compare complete queued/live PR identity, then use the validated live snapshot."""

    def mapping(value: object, label: str) -> dict:
        if not isinstance(value, dict):
            raise Invalid(f"{label} must be an object")
        return value

    def repo_name(value: object) -> str:
        if not isinstance(value, str) or not re.fullmatch(
            r"[^/\s\x00-\x1f\x7f]+/[^/\s\x00-\x1f\x7f]+", value
        ):
            raise Invalid("PR repository full_name is malformed")
        return value

    def identity(pr: object, label: str) -> dict:
        item = mapping(pr, label)
        timestamp(item.get("created_at"))
        for side in ("head", "base"):
            part = mapping(item.get(side), f"{label} {side}")
            sha_value = part.get("sha")
            if not isinstance(sha_value, str) or not re.fullmatch(
                r"(?:[0-9a-f]{40}|[0-9a-f]{64})", sha_value
            ):
                raise Invalid(f"{label} {side} SHA is malformed")
            ref = part.get("ref")
            if not isinstance(ref, str) or not re.fullmatch(r"[^\s\x00-\x1f\x7f]+", ref):
                raise Invalid(f"{label} {side} ref is malformed")
            repo_name(mapping(part.get("repo"), f"{label} {side} repo").get("full_name"))
        if "body" in item and item["body"] is not None and not isinstance(item["body"], str):
            raise Invalid(f"{label} body is malformed")
        return item

    queued = mapping(event, "queued PR event")
    number = integer(queued.get("number"), 1)
    repository = repo_name(mapping(queued.get("repository"), "event repository").get("full_name"))
    recorded = identity(queued.get("pull_request"), "queued PR")
    live = identity(metadata, "live PR")
    if integer(live.get("number"), 1) != number or (
        "number" in recorded and integer(recorded["number"], 1) != number
    ):
        raise Invalid("queued PR event has stale PR number or identity")
    if recorded["created_at"] != live["created_at"]:
        raise Invalid("queued PR event has stale creation time")
    for side in ("head", "base"):
        for key in ("sha", "ref"):
            if recorded[side][key] != live[side][key]:
                raise Invalid(f"queued PR event has stale {side} {key}")
        if recorded[side]["repo"]["full_name"] != live[side]["repo"]["full_name"]:
            raise Invalid(f"queued PR event has stale {side} repository")
    if live["base"]["repo"]["full_name"] != repository:
        raise Invalid("queued PR event has stale base repository identity")
    return {**queued, "pull_request": {**live, "body": live.get("body")}}


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
            append(args.root, args.issue, event, now, source_path=args.event)
        else:
            ledgers = validate_all(args.root, now)
            changed = (
                check_prefix(args.root, args.base, ledgers, now)
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
                    root=args.root,
                )
                if args.command == "status":
                    print(
                        json.dumps(
                            {
                                "capsule": capsule_ref(state.capsule) if state.capsule else None,
                                "content": content_digest(args.root, args.issue),
                                "owner": state.approved_owner,
                                "policy": state.policy,
                                "counts": state.counts,
                                "inherited_counts": state.inherited_counts,
                                "local_counts": {
                                    phase: state.counts[phase] - state.inherited_counts[phase]
                                    for phase in COUNTS
                                },
                                "limits": state.limits,
                                "remaining_counts": {
                                    phase: state.limits[phase] - state.counts[phase]
                                    for phase in COUNTS
                                },
                                "elapsed_seconds": state.elapsed(now),
                                "remaining_seconds": (
                                    state.budget_seconds - state.elapsed(now)
                                    if state.policy == "timed-v1"
                                    else None
                                ),
                                "active_phase": state.active["phase"] if state.active else None,
                                "verified": state.verified,
                                "reviewed": state.reviewed,
                                "accepted": state.accepted,
                                "pending_repair": state.pending_repair,
                                "delivered": state.delivered,
                                "delivery_binding": state.delivery_binding,
                                "delivery_history": state.delivery_history,
                                "historical_delivery_history": state.historical_delivery_history,
                                "historical_reservation_count": len(state.historical_reservations),
                                "historical_outcomes": state.historical_outcomes,
                                "historical_findings": state.historical_findings,
                                "local_verification_starts": state.local_verification_starts,
                                "local_verification_limit": state.local_verification_limit,
                                "issue92_recovery_ref": state.issue92_recovery_ref,
                                "issue92_recovery_stage": state.issue92_recovery_stage,
                                "issue92_recovery_failure": state.issue92_recovery_failure,
                                "issue92_recovery_supplemental": (
                                    state.issue92_recovery_supplemental
                                ),
                                "issue92_review_disposition": state.issue92_review_disposition,
                                "issue92_pr_identity_ref": state.issue92_pr_identity_ref,
                                "issue92_pr_identity_stage": state.issue92_pr_identity_stage,
                                "issue92_pr_identity_failure": state.issue92_pr_identity_failure,
                                "issue92_pr_identity_supplemental": (
                                    state.issue92_pr_identity_supplemental
                                ),
                                "issue92_stage_fixture_ref": state.issue92_stage_fixture_ref,
                                "issue92_stage_fixture_stage": state.issue92_stage_fixture_stage,
                                "issue92_stage_fixture_failure": (
                                    state.issue92_stage_fixture_failure
                                ),
                                "issue92_stage_fixture_supplemental": (
                                    state.issue92_stage_fixture_supplemental
                                ),
                                "publication_target": state.publication_target,
                                "retired": state.split_remaining is not None
                                or state.split_pool is not None,
                                "split_remaining_seconds": state.split_remaining,
                                "split_remaining_counts": state.split_pool,
                                "suspended_phase": state.suspended["phase"]
                                if state.suspended
                                else None,
                                "timing_barrier_transitioned": state.lineage_transition,
                                "ancestor_split_remaining_seconds": (
                                    state.ancestor_split_remaining_seconds
                                ),
                                "historical_timed_debt_seconds": (
                                    state.historical_timed_debt_seconds
                                ),
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
                changed = check_prefix(
                    args.root, event["pull_request"]["base"]["sha"], ledgers, now
                )
                body = event["pull_request"].get("body") or ""
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
                        root=args.root,
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
