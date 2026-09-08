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
                "Bounded worker for approved mechanical changes, unit tests, and "
                "straightforward review fixes."
            ),
            "model": "gpt-5.6-terra",
            "model_reasoning_effort": "medium",
            "sandbox_mode": "workspace-write",
        },
        "agents/implementation-worker.toml": {
            "name": "implementation_worker",
            "description": (
                "Implementation worker for approved normal engineering and routine CI/CD work."
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
                "recorded approved DESIGN_READY",
                "stop and report the missing gate",
                "Implement only the approved scope",
                "focused tests",
                "verification gates",
            )
        )
        role_markers = {
            "planning_analyst": (
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
                "do not issue a design gate or independently authorize",
                "design_architect",
            ),
            "bounded_worker": (
                "approved mechanical changes",
                "implementation_specialist",
                "design_architect",
            ),
            "implementation_worker": (
                "routine CI/CD",
                "implementation_specialist",
                "design_architect",
            ),
            "implementation_specialist": (
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
            "detailed task matrix is authoritative",
            "DESIGN_READY",
            "gpt-6-astra",
            "Design phase",
            "Implementation phase",
        ),
    )
    require_markers(
        ROOT / ".github/PULL_REQUEST_TEMPLATE.md",
        (
            "Design handoff",
            "Approval:",
            "role / model / effort",
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
                "Design handoff:",
                "Approval:",
                "role / model / effort",
                "Escalations:",
                "DESIGN_READY",
                "separate sequential session",
            ),
        )
    print("Codex ticket workflow configuration is valid.")


if __name__ == "__main__":
    main()
