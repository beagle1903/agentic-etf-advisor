"""Validate the project-scoped Codex ticket workflow contract."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_equal(data: dict[str, object], key: str, expected: object, path: Path) -> None:
    actual = data.get(key)
    if actual != expected:
        raise SystemExit(f"{path}: {key} must be {expected!r}, got {actual!r}")


def require_markers(path: Path, markers: tuple[str, ...]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SystemExit(f"{path}: unreadable workflow document: {exc}") from exc
    missing = [marker for marker in markers if marker not in text]
    if missing:
        joined = ", ".join(repr(marker) for marker in missing)
        raise SystemExit(f"{path}: missing required workflow markers: {joined}")


def main() -> None:
    agent_expectations = {
        "agents/planning-analyst.toml": {
            "name": "planning_analyst",
            "description": (
                "Read-only analyst for discovery, planning, and "
                "architecture-determined low-risk designs."
            ),
            "model": "gpt-5.6-terra",
            "model_reasoning_effort": "medium",
            "sandbox_mode": "read-only",
        },
        "agents/design-architect.toml": {
            "name": "design_architect",
            "description": (
                "Read-only architect for consequential contracts, architecture, "
                "and difficult unresolved problems."
            ),
            "model": "gpt-6-astra",
            "model_reasoning_effort": "high",
            "sandbox_mode": "read-only",
        },
        "agents/bounded-worker.toml": {
            "name": "bounded_worker",
            "description": (
                "Bounded worker owning authorized mechanical work from design capsule "
                "through verification."
            ),
            "model": "gpt-5.6-terra",
            "model_reasoning_effort": "medium",
            "sandbox_mode": "workspace-write",
        },
        "agents/implementation-worker.toml": {
            "name": "implementation_worker",
            "description": (
                "Implementation worker owning authorized ordinary work from design capsule "
                "through verification."
            ),
            "model": "gpt-5.6-sol",
            "model_reasoning_effort": "medium",
            "sandbox_mode": "workspace-write",
        },
        "agents/code-reviewer.toml": {
            "name": "code_reviewer",
            "description": (
                "Read-only reviewer for substantive correctness, dependencies, and "
                "test-gap analysis."
            ),
            "model": "gpt-5.6-sol",
            "model_reasoning_effort": "high",
            "sandbox_mode": "read-only",
        },
        "agents/implementation-specialist.toml": {
            "name": "implementation_specialist",
            "description": (
                "Implementation specialist for approved cross-cutting work, "
                "debugging, and integration tests."
            ),
            "model": "gpt-5.6-sol",
            "model_reasoning_effort": "high",
            "sandbox_mode": "workspace-write",
        },
    }

    config_path = ROOT / ".codex/config.toml"
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(f"{config_path}: invalid project Codex TOML: {exc}") from exc
    agents = config.get("agents")
    if not isinstance(agents, dict):
        raise SystemExit(f"{config_path}: missing [agents] table")
    for key in (
        "enabled",
        "default_subagent_model",
        "default_subagent_reasoning_effort",
        "max_concurrent_threads_per_session",
        "max_threads",
        "default_role",
    ):
        if key in agents:
            raise SystemExit(
                f"{config_path}: {key} is prohibited by repository compatibility policy"
            )

    for key in ("model", "model_reasoning_effort"):
        if key in config:
            raise SystemExit(f"{config_path}: project-level overrides are prohibited: {key}")
    extra_roles = set(agents) - {item["name"] for item in agent_expectations.values()}
    if extra_roles:
        raise SystemExit(f"{config_path}: unexpected role registrations: {sorted(extra_roles)}")

    # Validate all registrations before opening any referenced role file.
    for config_file, expectations in agent_expectations.items():
        name = expectations["name"]
        registration = agents.get(name)
        if not isinstance(registration, dict):
            raise SystemExit(f"{config_path}: missing [agents.{name}] table")
        require_equal(registration, "description", expectations["description"], config_path)
        require_equal(registration, "config_file", config_file, config_path)
        if set(registration) != {"description", "config_file"}:
            raise SystemExit(f"{config_path}: unexpected registration fields for {name}")

    expected_paths = {config_path.parent / item for item in agent_expectations}
    extra_paths = set((config_path.parent / "agents").rglob("*.toml")) - expected_paths
    if extra_paths:
        raise SystemExit(f"{config_path}: unexpected role files")

    for expectations in agent_expectations.values():
        registration = agents[expectations["name"]]
        path = config_path.parent / registration["config_file"]
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise SystemExit(f"{path}: invalid custom-agent TOML: {exc}") from exc
        for key, expected in expectations.items():
            require_equal(data, key, expected, path)
        if set(data) != {*expectations, "developer_instructions"}:
            raise SystemExit(f"{path}: unexpected or missing role fields")
        instructions = data.get("developer_instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            raise SystemExit(f"{path}: developer_instructions must be nonempty text")
        common = (
            "Read AGENTS.md",
            "active iteration",
            "JSON-serializable",
            "side-effect boundaries",
            "Do not silently redesign",
            "separate sequential session",
            "Do not execute trades or external financial writes",
        )
        boundary = (
            ("Do not edit source", "execute mutating commands")
            if expectations["sandbox_mode"] == "read-only"
            else (
                "DESIGN_READY",
                "Consequential financial",
                "coordinator approval",
                "stop and report",
                "focused tests",
                "verification gates",
            )
        )
        role_markers = {
            "planning_analyst": (
                "not a routine prerequisite",
                "low-risk solution fully determined by existing architecture",
                "consequential contracts require design_architect",
                "code_reviewer",
                "DESIGN_BLOCKED",
                "records and approves",
            ),
            "design_architect": (
                "consequential contracts",
                "DESIGN_BLOCKED",
                "records and approves",
            ),
            "code_reviewer": (
                "high-risk or disputed output",
                (
                    "do not issue a design gate or independently authorize implementation "
                    "or contract changes"
                ),
                "design_architect",
            ),
            "bounded_worker": (
                "mechanical, low-risk",
                "same session",
                "capsule must precede edits",
                "self-review",
                "multiple files or unfamiliarity alone are not sufficient",
                "implementation_specialist",
                "design_architect",
            ),
            "implementation_worker": (
                "authorized ordinary work",
                "same session",
                "capsule must precede edits",
                "self-review",
                "routine CI/CD",
                "multiple files, integration tests, or unfamiliarity",
                "implementation_specialist",
                "design_architect",
            ),
            "implementation_specialist": (
                "recorded escalation trigger",
                "Multiple files, integration tests, or unfamiliarity alone",
                "Distributed systems, nondeterminism",
                "design_architect",
            ),
        }
        missing = [
            marker
            for marker in (*common, *boundary, *role_markers[expectations["name"]])
            if marker not in instructions
        ]
        if missing:
            raise SystemExit(f"{path}: missing instruction boundaries: {missing}")

    require_markers(
        ROOT / "AGENTS.md",
        (
            "design_architect",
            "implementation_worker",
            "planning_analyst",
            "bounded_worker",
            "code_reviewer",
            "implementation_specialist",
            "separate sequential session",
            "classification table is authoritative",
            "DESIGN_READY",
            "gpt-6-astra",
            "Classify by impact",
            "Complete routine work in one session",
            "Escalate from evidence",
            "Record the design capsule",
            "before implementation edits",
            "only a separate read-only `design_architect` session",
            "Review findings cannot authorize implementation or contract changes",
            "Multiple files, integration tests, or unfamiliarity alone do not require escalation",
        ),
    )
    require_markers(
        ROOT / ".github/PULL_REQUEST_TEMPLATE.md",
        (
            "Classification:",
            "Design handoff",
            "Authorization:",
            "Owner role / model / effort",
            "Separate architect approval:",
            "Routine work used one owner session",
            "Consequential work had a separate `design_architect` handoff",
            "Self-review and focused tests",
            "reviewer findings did not authorize changes",
            "Static workflow validation:",
            "Live-session provenance:",
            "Codex CLI compatibility:",
            "Measured quota savings:",
            "Escalations:",
            "DESIGN_READY",
            "separate sequential session",
        ),
    )
    require_markers(
        ROOT / "CONTRIBUTING.md",
        (
            "DESIGN_READY",
            "planning_analyst",
            "implementation_specialist",
            "separate sequential session",
            "actual routing evidence",
            "one authorized session",
            "before implementation edits",
            "Review findings cannot authorize implementation or contract changes",
            "multiple files, integration tests, or unfamiliarity alone are insufficient",
        ),
    )
    for template_name in (
        "work-item.yml",
        "bug.yml",
        "verification.yml",
        "iteration.yml",
    ):
        require_markers(
            ROOT / ".github/ISSUE_TEMPLATE" / template_name,
            (
                "execution-workflow",
                "Classification:",
                "Owner role / model / effort:",
                "User authorization:",
                "Design handoff:",
                "Capsule:",
                "Routine execution: one owner session",
                (
                    "Consequential approval: separate design_architect handoff and "
                    "coordinator approval"
                ),
                "Independent review: high-risk/disputed trigger and findings",
                "Escalations:",
                "DESIGN_READY",
                "separate sequential session",
                "capsule precedes implementation edits",
                "reviewer findings do not authorize changes",
            ),
        )
    print("Codex ticket workflow configuration is valid.")


if __name__ == "__main__":
    main()
