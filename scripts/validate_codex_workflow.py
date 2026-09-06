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
        ROOT / ".codex/agents/design-architect.toml": {
            "name": "design_architect",
            "model": "gpt-6-astra",
            "model_reasoning_effort": "high",
            "sandbox_mode": "read-only",
        },
        ROOT / ".codex/agents/implementation-worker.toml": {
            "name": "implementation_worker",
            "model": "gpt-6-astra",
            "model_reasoning_effort": "medium",
            "sandbox_mode": "workspace-write",
        },
    }

    for path, expectations in agent_expectations.items():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise SystemExit(f"{path}: invalid custom-agent TOML: {exc}") from exc
        for key, expected in expectations.items():
            require_equal(data, key, expected, path)

    config_path = ROOT / ".codex/config.toml"
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(f"{config_path}: invalid project Codex TOML: {exc}") from exc
    agents = config.get("agents")
    if not isinstance(agents, dict):
        raise SystemExit(f"{config_path}: missing [agents] table")
    require_equal(agents, "enabled", True, config_path)
    require_equal(agents, "default_subagent_model", "gpt-6-astra", config_path)
    require_equal(agents, "default_subagent_reasoning_effort", "medium", config_path)
    require_equal(agents, "max_concurrent_threads_per_session", 2, config_path)

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
