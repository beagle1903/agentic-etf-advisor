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
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in text]
    if missing:
        joined = ", ".join(repr(marker) for marker in missing)
        raise SystemExit(f"{path}: missing required workflow markers: {joined}")


def main() -> None:
    agent_expectations = {
        "agents/design-architect.toml": {
            "name": "design_architect",
            "description": (
                "Read-only high-effort design agent used before every ticket implementation."
            ),
            "model": "gpt-6-astra",
            "model_reasoning_effort": "high",
            "sandbox_mode": "read-only",
        },
        "agents/implementation-worker.toml": {
            "name": "implementation_worker",
            "description": (
                "Medium-effort implementation agent that executes an approved ticket design."
            ),
            "model": "gpt-6-astra",
            "model_reasoning_effort": "medium",
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
    ):
        if key in agents:
            raise SystemExit(
                f"{config_path}: {key} is prohibited by repository compatibility policy"
            )

    # Validate all registrations before opening any referenced role file.
    for config_file, expectations in agent_expectations.items():
        name = expectations["name"]
        registration = agents.get(name)
        if not isinstance(registration, dict):
            raise SystemExit(f"{config_path}: missing [agents.{name}] table")
        require_equal(registration, "description", expectations["description"], config_path)
        require_equal(registration, "config_file", config_file, config_path)

    for expectations in agent_expectations.values():
        registration = agents[expectations["name"]]
        path = config_path.parent / registration["config_file"]
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise SystemExit(f"{path}: invalid custom-agent TOML: {exc}") from exc
        for key, expected in expectations.items():
            require_equal(data, key, expected, path)

    require_markers(
        ROOT / "AGENTS.md",
        (
            "design_architect",
            "implementation_worker",
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
            "design_architect",
            "implementation_worker",
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
            ("execution-workflow", "design_architect", "implementation_worker"),
        )
    print("Codex ticket workflow configuration is valid.")


if __name__ == "__main__":
    main()
