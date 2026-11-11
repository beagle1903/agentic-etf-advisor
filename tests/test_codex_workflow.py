"""Focused regression coverage for project Codex role configuration."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1]
ROLES = (
    "planning-analyst",
    "design-architect",
    "bounded-worker",
    "implementation-worker",
    "code-reviewer",
    "implementation-specialist",
)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(SOURCE / ".codex", root / ".codex")
    (root / "scripts").mkdir()
    shutil.copyfile(
        SOURCE / "scripts/validate_codex_workflow.py",
        root / "scripts/validate_codex_workflow.py",
    )
    return root


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts/validate_codex_workflow.py")],
        cwd=root.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def replace(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    assert old in content
    path.write_text(content.replace(old, new), encoding="utf-8")


def reject(root: Path, expected: str) -> None:
    result = run_validator(root)
    assert result.returncode != 0
    assert expected in result.stderr
    assert "Traceback" not in result.stderr


def test_valid_without_docs_or_ledgers_from_another_cwd(repository: Path) -> None:
    result = run_validator(repository)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Codex role configuration is valid.\n"


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "field", ["name", "description", "model", "model_reasoning_effort", "sandbox_mode"]
)
def test_role_contract_drift(repository: Path, role: str, field: str) -> None:
    path = repository / f".codex/agents/{role}.toml"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text(
        "".join(
            f'{field} = "drift"\n' if line.startswith(f"{field} =") else line for line in lines
        ),
        encoding="utf-8",
    )
    reject(repository, f"{field} must be")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("damage", ["missing", "malformed", "swapped"])
def test_role_file_load(repository: Path, role: str, damage: str) -> None:
    path = repository / f".codex/agents/{role}.toml"
    if damage == "missing":
        path.unlink()
        reject(repository, "role inventory")
    elif damage == "malformed":
        path.write_text("[broken", encoding="utf-8")
        reject(repository, "invalid TOML")
    else:
        other = next(item for item in ROLES if item != role)
        shutil.copyfile(repository / f".codex/agents/{other}.toml", path)
        reject(repository, "name must be")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("field", ["description", "config_file"])
def test_registration_drift(repository: Path, role: str, field: str) -> None:
    path = repository / ".codex/config.toml"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    active = False
    for index, line in enumerate(lines):
        if line.startswith("["):
            active = line.strip() == f"[agents.{role.replace('-', '_')}]"
        elif active and line.startswith(f"{field} ="):
            lines[index] = f'{field} = "wrong"\n'
    path.write_text("".join(lines), encoding="utf-8")
    reject(repository, f"{field} must be")


@pytest.mark.parametrize("role", ROLES)
def test_missing_registration(repository: Path, role: str) -> None:
    path = repository / ".codex/config.toml"
    text = path.read_text(encoding="utf-8")
    heading = f"[agents.{role.replace('-', '_')}]"
    assert heading in text
    start = text.index(heading)
    next_heading = text.find("[agents.", start + len(heading))
    path.write_text(
        text[:start] + (text[next_heading:] if next_heading >= 0 else ""), encoding="utf-8"
    )
    reject(repository, "role registrations")


@pytest.mark.parametrize(
    "scalar",
    [
        "enabled = true",
        'default_subagent_model = "gpt-6-sol"',
        'default_subagent_reasoning_effort = "medium"',
        "max_concurrent_threads_per_session = 2",
        "max_threads = 2",
        'default_role = "implementation_worker"',
    ],
)
def test_forbidden_agent_scalar(repository: Path, scalar: str) -> None:
    path = repository / ".codex/config.toml"
    path.write_text(
        "[agents]\n" + scalar + "\n" + path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    reject(repository, "prohibited")


@pytest.mark.parametrize("override", ['model = "gpt-6-sol"', 'model_reasoning_effort = "high"'])
def test_top_level_override(repository: Path, override: str) -> None:
    path = repository / ".codex/config.toml"
    path.write_text(override + "\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    reject(repository, "project-level overrides")


@pytest.mark.parametrize("damage", ["empty", "missing", "wrong_type"])
def test_instruction_text_required(repository: Path, damage: str) -> None:
    path = repository / ".codex/agents/design-architect.toml"
    text = path.read_text(encoding="utf-8").split("developer_instructions")[0]
    if damage == "empty":
        text += 'developer_instructions = "  "'
    elif damage == "wrong_type":
        text += "developer_instructions = 42"
    path.write_text(text, encoding="utf-8")
    reject(repository, "role fields" if damage == "missing" else "nonempty text")


def test_extra_role_or_file_rejected(repository: Path) -> None:
    path = repository / ".codex/agents/extra.toml"
    path.write_text('name = "extra"', encoding="utf-8")
    reject(repository, "role inventory")
    path.unlink()
    config = repository / ".codex/config.toml"
    config.write_text(config.read_text(encoding="utf-8") + "\n[agents.extra]\n", encoding="utf-8")
    reject(repository, "role registrations")


def test_nested_duplicate_role_file_rejected(repository: Path) -> None:
    nested = repository / ".codex/agents/nested"
    nested.mkdir()
    shutil.copyfile(
        repository / ".codex/agents/design-architect.toml", nested / "design-architect.toml"
    )
    reject(repository, "role inventory")


def test_unrelated_settings_allowed(repository: Path) -> None:
    path = repository / ".codex/config.toml"
    path.write_text(
        "[history]\nmax_bytes = 100000\n" + path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert run_validator(repository).returncode == 0


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
