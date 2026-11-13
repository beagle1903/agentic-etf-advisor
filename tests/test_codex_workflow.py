"""Focused checks for prospective Codex presets and declared assignments."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1]
PRESETS = ("astra", "sol", "luna")
ASSIGNMENTS = {
    "planning_analyst": ("discovery", ["inspect", "report"]),
    "design_architect": ("design", ["inspect", "report"]),
    "code_reviewer": ("review", ["inspect", "report"]),
    "bounded_worker": ("implementation", ["inspect", "edit", "run_checks"]),
    "implementation_worker": ("remediation", ["inspect", "edit", "run_checks"]),
    "implementation_specialist": ("verification", ["inspect", "run_checks"]),
}


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(SOURCE / ".codex", root / ".codex")
    (root / "scripts").mkdir()
    shutil.copyfile(
        SOURCE / "scripts/validate_codex_workflow.py", root / "scripts/validate_codex_workflow.py"
    )
    return root


def run_validator(
    root: Path, declaration: object | None = None
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(root / "scripts/validate_codex_workflow.py")]
    if declaration is not None:
        path = root / "declaration.json"
        path.write_text(json.dumps(declaration), encoding="utf-8")
        command += ["--declaration", str(path)]
    return subprocess.run(command, cwd=root.parent, capture_output=True, text=True, check=False)


def reject(root: Path, expected: str, declaration: object | None = None) -> None:
    result = run_validator(root, declaration)
    assert result.returncode != 0
    assert expected in result.stderr
    assert "Traceback" not in result.stderr


def declaration(assignment: str = "implementation_worker") -> dict[str, object]:
    activity, actions = ASSIGNMENTS[assignment]
    return {
        "preset": "luna",
        "model": "gpt-6-luna",
        "effort": "medium",
        "assignment": assignment,
        "activity": activity,
        "permitted_actions": actions,
        "scope": "synthetic files",
        "acceptance": "specified output",
        "rationale": "bounded task",
        "authorization_ref": "issue-109-approved",
        "participant_ref": "writer-1",
        "owner_ref": "writer-1",
        "prior_authors": {"implementation": ["writer-1"], "remediation": [], "verification": []},
        "consequential": True,
        "coordinator_approval_ref": "approved-design",
        "inherited_access": "danger-full-access",
        "restriction_kind": "instruction-only",
    }


def test_exact_presets_without_docs_or_ledgers_from_other_cwd(repository: Path) -> None:
    result = run_validator(repository)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Codex preset configuration is valid.\n"


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("field", ["name", "description", "model", "model_reasoning_effort"])
def test_preset_drift(repository: Path, preset: str, field: str) -> None:
    path = repository / f".codex/agents/{preset}.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        "".join(
            f'{field} = "drift"\n' if line.startswith(f"{field} =") else line
            for line in text.splitlines(keepends=True)
        ),
        encoding="utf-8",
    )
    reject(repository, f"{field} must be")


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("damage", ["missing", "malformed", "swapped"])
def test_preset_file_failure(repository: Path, preset: str, damage: str) -> None:
    path = repository / f".codex/agents/{preset}.toml"
    if damage == "missing":
        path.unlink()
        reject(repository, "preset inventory")
    elif damage == "malformed":
        path.write_text("[broken", encoding="utf-8")
        reject(repository, "invalid TOML")
    else:
        other = next(item for item in PRESETS if item != preset)
        shutil.copyfile(repository / f".codex/agents/{other}.toml", path)
        reject(repository, "name must be")


def test_extra_file_and_registration_rejected(repository: Path) -> None:
    extra = repository / ".codex/agents/extra.toml"
    extra.write_text('name = "extra"', encoding="utf-8")
    reject(repository, "preset inventory")
    extra.unlink()
    config = repository / ".codex/config.toml"
    config.write_text(config.read_text(encoding="utf-8") + "\n[agents.extra]\n", encoding="utf-8")
    reject(repository, "preset registrations")


@pytest.mark.parametrize("damage", ["bad_path", "missing_registration", "extra_field"])
def test_registration_failure(repository: Path, damage: str) -> None:
    config = repository / ".codex/config.toml"
    text = config.read_text(encoding="utf-8")
    if damage == "bad_path":
        text = text.replace("agents/sol.toml", "agents/sol.tom")
        expected = "config_file must be"
    elif damage == "missing_registration":
        text = text[: text.index("[agents.luna]")]
        expected = "preset registrations"
    else:
        text = text.replace("[agents.sol]", '[agents.sol]\nsandbox_mode = "read-only"')
        expected = "unexpected registration fields"
    config.write_text(text, encoding="utf-8")
    reject(repository, expected)


@pytest.mark.parametrize("field", ["sandbox_mode", "enabled"])
def test_forbidden_preset_field(repository: Path, field: str) -> None:
    path = repository / ".codex/agents/astra.toml"
    path.write_text(path.read_text(encoding="utf-8") + f"\n{field} = true\n", encoding="utf-8")
    reject(repository, "unexpected or missing preset fields")


@pytest.mark.parametrize("scalar", ["enabled = true", "max_threads = 2", 'default_role = "sol"'])
def test_forbidden_agent_scalar(repository: Path, scalar: str) -> None:
    config = repository / ".codex/config.toml"
    config.write_text(
        "[agents]\n" + scalar + "\n" + config.read_text(encoding="utf-8"), encoding="utf-8"
    )
    reject(repository, "prohibited")


@pytest.mark.parametrize("override", ['model = "gpt-6-luna"', 'model_reasoning_effort = "max"'])
def test_project_override(repository: Path, override: str) -> None:
    config = repository / ".codex/config.toml"
    config.write_text(override + "\n" + config.read_text(encoding="utf-8"), encoding="utf-8")
    reject(repository, "project-level overrides")


@pytest.mark.parametrize("preset", PRESETS)
def test_instructions_required(repository: Path, preset: str) -> None:
    path = repository / f".codex/agents/{preset}.toml"
    text = path.read_text(encoding="utf-8").split("developer_instructions")[0]
    path.write_text(text + 'developer_instructions = " "\n', encoding="utf-8")
    reject(repository, "developer_instructions must be nonempty")


@pytest.mark.parametrize("assignment", ASSIGNMENTS)
def test_six_assignments_are_independent_of_preset(repository: Path, assignment: str) -> None:
    record = declaration(assignment)
    if assignment == "code_reviewer":
        record["participant_ref"] = "reviewer-2"
    if assignment == "design_architect":
        record["participant_ref"] = "designer-2"
    assert run_validator(repository, record).returncode == 0
    record.update(preset="astra", model="gpt-6-astra", effort="high")
    assert run_validator(repository, record).returncode == 0


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"activity": "review"}, "assignment/activity incompatible"),
        ({"permitted_actions": ["inspect", "inspect"]}, "permitted_actions"),
        ({"authorization_ref": " "}, "authorization_ref"),
        ({"owner_ref": "another"}, "writer participant_ref"),
        ({"coordinator_approval_ref": None}, "coordinator_approval_ref"),
        ({"restriction_kind": "sandbox"}, "restriction_kind"),
        ({"inherited_access": "sandboxed"}, "inherited_access"),
        ({"consequential": "true"}, "consequential must be boolean"),
        ({"permitted_actions": ["deliver"]}, "delivery_responsibility"),
    ],
)
def test_invalid_declarations(repository: Path, change: dict[str, object], error: str) -> None:
    record = declaration()
    record.update(change)
    reject(repository, error, record)


def test_no_write_assignment_even_with_full_access(repository: Path) -> None:
    record = declaration("code_reviewer")
    record["participant_ref"] = "reviewer-2"
    record["permitted_actions"] = ["inspect", "edit"]
    reject(repository, "no-write assignment", record)


def test_consequential_design_separate_from_owner(repository: Path) -> None:
    record = declaration("design_architect")
    reject(repository, "consequential design participant must differ", record)


def test_optional_references_present_must_be_nonblank(repository: Path) -> None:
    record = declaration("planning_analyst")
    record["coordinator_approval_ref"] = None
    reject(repository, "coordinator_approval_ref must be nonblank", record)
    del record["coordinator_approval_ref"]
    record["design_author_ref"] = None
    reject(repository, "design_author_ref must be nonblank", record)


def test_verification_cannot_edit_but_writer_can_deliver_when_assigned(repository: Path) -> None:
    record = declaration("implementation_worker")
    record.update(activity="verification", permitted_actions=["inspect", "edit"])
    reject(repository, "verification cannot edit", record)
    record.update(
        activity="implementation",
        permitted_actions=["inspect", "deliver"],
        delivery_responsibility=True,
    )
    assert run_validator(repository, record).returncode == 0


@pytest.mark.parametrize("phase", ["implementation", "remediation", "verification"])
def test_review_independent_of_each_prior_author(repository: Path, phase: str) -> None:
    record = declaration("code_reviewer")
    record["participant_ref"] = "reviewer-2"
    record["prior_authors"][phase].append("reviewer-2")
    reject(repository, "review participant must be independent", record)


def test_review_requires_writer_and_distinct_owner(repository: Path) -> None:
    record = declaration("code_reviewer")
    record["participant_ref"] = "reviewer-2"
    record["prior_authors"] = {"implementation": [], "remediation": [], "verification": []}
    reject(repository, "review requires", record)
    record["prior_authors"]["implementation"] = ["other-writer"]
    record["participant_ref"] = "writer-1"
    reject(repository, "review participant must be independent", record)


def test_optional_challenge_requires_distinct_designer(repository: Path) -> None:
    record = declaration("code_reviewer")
    record.update(
        activity="challenge", participant_ref="challenger", design_author_ref="challenger"
    )
    reject(repository, "challenge requires distinct", record)
    record["design_author_ref"] = "designer"
    assert run_validator(repository, record).returncode == 0


def test_malformed_json_and_type_are_clean_cli_errors(repository: Path) -> None:
    path = repository / "bad.json"
    path.write_text("{", encoding="utf-8")
    command = [
        sys.executable,
        str(repository / "scripts/validate_codex_workflow.py"),
        "--declaration",
        str(path),
    ]
    result = subprocess.run(command, cwd=repository.parent, capture_output=True, text=True)
    assert result.returncode != 0 and "invalid declaration" in result.stderr
    assert "Traceback" not in result.stderr
    reject(repository, "declaration must be a JSON object", [1, 2])


def test_ci_keeps_offline_checks_without_ledger_gate() -> None:
    workflow = (SOURCE / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for command in (
        "uv sync --frozen",
        "scripts/validate_codex_workflow.py",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run pytest",
    ):
        assert command in workflow
    for token in ("scripts/ticket_workflow.py ci", "GITHUB_TOKEN", "fetch-depth: 0"):
        assert token not in workflow
