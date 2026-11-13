"""Validate project model presets and optional declared dispatches."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESETS = {
    "astra": ("Astra model preset for separately assigned project work.", "gpt-6-astra", "high"),
    "sol": ("Sol model preset for separately assigned project work.", "gpt-6.1-sol", "medium"),
    "luna": ("Luna model preset for separately assigned project work.", "gpt-6-luna", "medium"),
}
NO_WRITE = {"planning_analyst", "design_architect", "code_reviewer"}
WRITERS = {"bounded_worker", "implementation_worker", "implementation_specialist"}
ACTIONS = {"inspect", "report", "edit", "run_checks", "deliver"}
ACTIVITIES = {
    "planning_analyst": {"discovery"},
    "design_architect": {"design"},
    "code_reviewer": {"review", "challenge"},
    "bounded_worker": {"implementation", "remediation", "verification"},
    "implementation_worker": {"implementation", "remediation", "verification"},
    "implementation_specialist": {"implementation", "remediation", "verification"},
}
REQUIRED_DECLARATION = {
    "preset",
    "model",
    "effort",
    "assignment",
    "activity",
    "permitted_actions",
    "scope",
    "acceptance",
    "rationale",
    "authorization_ref",
    "participant_ref",
    "owner_ref",
    "prior_authors",
    "consequential",
    "inherited_access",
    "restriction_kind",
}
OPTIONAL_DECLARATION = {"coordinator_approval_ref", "design_author_ref", "delivery_responsibility"}


def load_toml(path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(f"{path}: invalid TOML: {exc}") from exc


def require(data: dict[str, object], key: str, expected: object, path: Path) -> None:
    if data.get(key) != expected:
        raise SystemExit(f"{path}: {key} must be {expected!r}, got {data.get(key)!r}")


def validate_config() -> None:
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
    if set(agents) != set(PRESETS):
        raise SystemExit(f"{config_path}: preset registrations must be exactly {sorted(PRESETS)}")

    preset_dir = config_path.parent / "agents"
    expected_files = {f"{name}.toml" for name in PRESETS}
    actual_files = {path.relative_to(preset_dir).as_posix() for path in preset_dir.rglob("*.toml")}
    if actual_files != expected_files:
        raise SystemExit(f"{preset_dir}: preset inventory must be exactly {sorted(expected_files)}")

    for name, (description, model, effort) in PRESETS.items():
        registration = agents[name]
        if not isinstance(registration, dict):
            raise SystemExit(f"{config_path}: missing [agents.{name}] table")
        if set(registration) != {"description", "config_file"}:
            raise SystemExit(f"{config_path}: unexpected registration fields for {name}")
        require(registration, "description", description, config_path)
        require(registration, "config_file", f"agents/{name}.toml", config_path)
        path = preset_dir / f"{name}.toml"
        preset = load_toml(path)
        expected = {
            "name": name,
            "description": description,
            "model": model,
            "model_reasoning_effort": effort,
        }
        if set(preset) != {*expected, "developer_instructions"}:
            raise SystemExit(f"{path}: unexpected or missing preset fields")
        for key, value in expected.items():
            require(preset, key, value, path)
        instructions = preset["developer_instructions"]
        if not isinstance(instructions, str) or not instructions.strip():
            raise SystemExit(f"{path}: developer_instructions must be nonempty text")


def nonblank(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonblank text")
    return value.strip()


def validate_declaration(data: object) -> None:
    """Check a declaration's internal consistency, not its truth or live permissions."""
    if not isinstance(data, dict):
        raise ValueError("declaration must be a JSON object")
    missing = REQUIRED_DECLARATION - data.keys()
    extra = data.keys() - REQUIRED_DECLARATION - OPTIONAL_DECLARATION
    if missing or extra:
        raise ValueError(
            f"declaration fields invalid: missing={sorted(missing)}, extra={sorted(extra)}"
        )

    preset = nonblank(data["preset"], "preset")
    if preset not in PRESETS:
        raise ValueError("unknown preset")
    _, model, effort = PRESETS[preset]
    if data["model"] != model or data["effort"] != effort:
        raise ValueError("model/effort do not match preset")
    assignment = nonblank(data["assignment"], "assignment")
    activity = nonblank(data["activity"], "activity")
    if activity not in ACTIVITIES.get(assignment, set()):
        raise ValueError("assignment/activity incompatible")
    for key in ("scope", "acceptance", "rationale", "authorization_ref"):
        nonblank(data[key], key)
    participant = nonblank(data["participant_ref"], "participant_ref")
    owner = nonblank(data["owner_ref"], "owner_ref")
    if not isinstance(data["consequential"], bool):
        raise ValueError("consequential must be boolean")
    access = nonblank(data["inherited_access"], "inherited_access")
    if access not in {"danger-full-access", "workspace-write", "read-only", "unknown"}:
        raise ValueError("inherited_access is unsupported")
    if data["restriction_kind"] != "instruction-only":
        raise ValueError("restriction_kind must be instruction-only")

    actions = data["permitted_actions"]
    if (
        not isinstance(actions, list)
        or not actions
        or any(not isinstance(x, str) for x in actions)
        or len(set(actions)) != len(actions)
        or not set(actions) <= ACTIONS
    ):
        raise ValueError("permitted_actions must be a nonempty distinct allowed-action list")
    if assignment in NO_WRITE and not set(actions) <= {"inspect", "report"}:
        raise ValueError("no-write assignment permits inspect/report only")
    if activity == "verification" and "edit" in actions:
        raise ValueError("verification cannot edit")
    delivery = data.get("delivery_responsibility", False)
    if not isinstance(delivery, bool):
        raise ValueError("delivery_responsibility must be boolean")
    if "deliver" in actions and (assignment not in WRITERS or not delivery):
        raise ValueError("deliver requires explicit writer delivery_responsibility")
    if delivery and assignment not in WRITERS:
        raise ValueError("delivery_responsibility requires writer assignment")
    if assignment in WRITERS and participant != owner:
        raise ValueError("writer participant_ref must match owner_ref")
    if assignment == "design_architect" and data["consequential"] and participant == owner:
        raise ValueError("consequential design participant must differ from owner_ref")

    authors = data["prior_authors"]
    if not isinstance(authors, dict) or set(authors) != {
        "implementation",
        "remediation",
        "verification",
    }:
        raise ValueError("prior_authors requires implementation/remediation/verification arrays")
    normalized: dict[str, list[str]] = {}
    for phase, refs in authors.items():
        if not isinstance(refs, list):
            raise ValueError(f"prior_authors.{phase} must be an array")
        normalized[phase] = [nonblank(ref, f"prior_authors.{phase}") for ref in refs]

    if "coordinator_approval_ref" in data:
        nonblank(data["coordinator_approval_ref"], "coordinator_approval_ref")
    if data["consequential"] and assignment in WRITERS and "coordinator_approval_ref" not in data:
        raise ValueError("consequential writer requires coordinator_approval_ref")
    design_author = None
    if "design_author_ref" in data:
        design_author = nonblank(data["design_author_ref"], "design_author_ref")
    if activity == "challenge" and (design_author is None or design_author == participant):
        raise ValueError("challenge requires distinct design_author_ref")
    if activity == "review":
        if not normalized["implementation"] and not normalized["remediation"]:
            raise ValueError("review requires an implementation/remediation author")
        prior = {ref for refs in normalized.values() for ref in refs}
        if participant == owner or participant in prior:
            raise ValueError("review participant must be independent of owner and prior authors")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--declaration", type=Path, help="optional JSON dispatch declaration")
    args = parser.parse_args()
    validate_config()
    if args.declaration is not None:
        try:
            declaration = json.loads(args.declaration.read_text(encoding="utf-8"))
            validate_declaration(declaration)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise SystemExit(f"{args.declaration}: invalid declaration: {exc}") from exc
        print("Codex dispatch declaration is internally consistent (declaration only).")
    else:
        print("Codex preset configuration is valid.")


if __name__ == "__main__":
    main()
