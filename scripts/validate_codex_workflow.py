"""Validate the pinned project Codex role configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = {
    "planning_analyst": (
        "planning-analyst",
        "Read-only analyst for discovery, planning, and architecture-determined low-risk designs.",
        "gpt-6-luna",
        "medium",
        "read-only",
    ),
    "design_architect": (
        "design-architect",
        "Read-only architect for consequential contracts, architecture, "
        "and difficult unresolved problems.",
        "gpt-6-astra",
        "high",
        "read-only",
    ),
    "bounded_worker": (
        "bounded-worker",
        "Bounded worker owning authorized mechanical work from design capsule "
        "through verification.",
        "gpt-6-luna",
        "medium",
        "workspace-write",
    ),
    "implementation_worker": (
        "implementation-worker",
        "Implementation worker owning authorized ordinary work from design capsule "
        "through verification.",
        "gpt-6-sol",
        "medium",
        "workspace-write",
    ),
    "code_reviewer": (
        "code-reviewer",
        "Read-only reviewer for substantive correctness, dependencies, and test-gap analysis.",
        "gpt-6-sol",
        "high",
        "read-only",
    ),
    "implementation_specialist": (
        "implementation-specialist",
        "Implementation specialist for demonstrably difficult work with an evidence-backed "
        "escalation trigger.",
        "gpt-6-sol",
        "high",
        "workspace-write",
    ),
}


def load_toml(path: Path) -> dict[str, object]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(f"{path}: invalid TOML: {exc}") from exc
    return data


def require(data: dict[str, object], key: str, expected: object, path: Path) -> None:
    if data.get(key) != expected:
        raise SystemExit(f"{path}: {key} must be {expected!r}, got {data.get(key)!r}")


def main() -> None:
    config_path = ROOT / ".codex/config.toml"
    config = load_toml(config_path)
    for key in ("model", "model_reasoning_effort"):
        if key in config:
            raise SystemExit(f"{config_path}: project-level overrides are prohibited: {key}")
    agents = config.get("agents")
    if not isinstance(agents, dict):
        raise SystemExit(f"{config_path}: missing [agents] table")
    forbidden = {
        "enabled",
        "default_subagent_model",
        "default_subagent_reasoning_effort",
        "max_concurrent_threads_per_session",
        "max_threads",
        "default_role",
    }
    for key in forbidden & agents.keys():
        raise SystemExit(f"{config_path}: {key} is prohibited by repository compatibility policy")
    if set(agents) != set(ROLES):
        raise SystemExit(f"{config_path}: role registrations must be exactly {sorted(ROLES)}")

    role_dir = config_path.parent / "agents"
    expected_files = {f"{values[0]}.toml" for values in ROLES.values()}
    actual_files = {path.relative_to(role_dir).as_posix() for path in role_dir.rglob("*.toml")}
    if actual_files != expected_files:
        raise SystemExit(f"{role_dir}: role inventory must be exactly {sorted(expected_files)}")

    for name, (filename, description, model, effort, access) in ROLES.items():
        registration = agents[name]
        if not isinstance(registration, dict):
            raise SystemExit(f"{config_path}: missing [agents.{name}] table")
        if set(registration) != {"description", "config_file"}:
            raise SystemExit(f"{config_path}: unexpected registration fields for {name}")
        require(registration, "description", description, config_path)
        require(registration, "config_file", f"agents/{filename}.toml", config_path)
        path = role_dir / f"{filename}.toml"
        role = load_toml(path)
        expected = {
            "name": name,
            "description": description,
            "model": model,
            "model_reasoning_effort": effort,
            "sandbox_mode": access,
        }
        if set(role) != {*expected, "developer_instructions"}:
            raise SystemExit(f"{path}: unexpected or missing role fields")
        for key, value in expected.items():
            require(role, key, value, path)
        instructions = role["developer_instructions"]
        if not isinstance(instructions, str) or not instructions.strip():
            raise SystemExit(f"{path}: developer_instructions must be nonempty text")
    print("Codex role configuration is valid.")


if __name__ == "__main__":
    main()
