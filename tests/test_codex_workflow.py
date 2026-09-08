"""Exercise the workflow command against isolated repository fixtures."""

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
    for relative in (".codex", ".github"):
        shutil.copytree(SOURCE / relative, root / relative)
    shutil.copyfile(SOURCE / "AGENTS.md", root / "AGENTS.md")
    shutil.copyfile(SOURCE / "CONTRIBUTING.md", root / "CONTRIBUTING.md")
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


def reject(root: Path, marker: str) -> None:
    result = run_validator(root)
    assert result.returncode == 1
    assert marker in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_valid_from_another_cwd(repository: Path) -> None:
    result = run_validator(repository)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Codex ticket workflow configuration is valid.\n"
    assert not result.stderr


def test_original_scalar_config(repository: Path) -> None:
    (repository / ".codex/config.toml").write_text(
        '[agents]\nenabled = true\ndefault_subagent_model = "gpt-6-astra"\n'
        'default_subagent_reasoning_effort = "medium"\nmax_concurrent_threads_per_session = 2\n',
        encoding="utf-8",
    )
    reject(repository, "prohibited")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("entry", ["missing", "scalar"])
def test_role_table_required(repository: Path, role: str, entry: str) -> None:
    path = repository / ".codex/config.toml"
    name = role.replace("-", "_")
    text = path.read_text(encoding="utf-8")
    sections = [section for section in text.split("[agents.") if section.strip()]
    text = "".join("[agents." + part for part in sections if not part.startswith(name + "]"))
    if entry == "scalar":
        text = f"[agents]\n{name} = true\n" + text
    path.write_text(text, encoding="utf-8")
    reject(repository, f"missing [agents.{name}] table")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("key", ["description", "config_file"])
@pytest.mark.parametrize("value", [None, '""', "true", "42", "[]", '"wrong"'])
def test_registration_fields(repository: Path, role: str, key: str, value: str | None) -> None:
    path = repository / ".codex/config.toml"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    active = False
    for index, line in enumerate(lines):
        if line.startswith("["):
            active = line.strip() == f"[agents.{role.replace('-', '_')}]"
        elif active and line.startswith(key + " ="):
            lines[index] = "" if value is None else f"{key} = {value}\n"
    path.write_text("".join(lines), encoding="utf-8")
    reject(repository, f"{key} must be")


@pytest.mark.parametrize("role", ROLES)
def test_swapped_paths(repository: Path, role: str) -> None:
    other = next(item for item in ROLES if item != role)
    replace(repository / ".codex/config.toml", f"agents/{role}.toml", f"agents/{other}.toml")
    reject(repository, "config_file must be")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("damage", ["missing", "malformed", "encoding", "swapped"])
def test_role_file_load(repository: Path, role: str, damage: str) -> None:
    path = repository / f".codex/agents/{role}.toml"
    if damage == "missing":
        path.unlink()
    elif damage == "malformed":
        path.write_text("[invalid", encoding="utf-8")
    elif damage == "encoding":
        path.write_bytes(b"\xff")
    else:
        other = next(item for item in ROLES if item != role)
        shutil.copyfile(repository / f".codex/agents/{other}.toml", path)
    reject(repository, "name must be" if damage == "swapped" else "invalid custom-agent TOML")


@pytest.mark.parametrize(
    "scalar",
    [
        "enabled = false",
        'default_subagent_model = "gpt-6-astra"',
        'default_subagent_reasoning_effort = "medium"',
        "max_concurrent_threads_per_session = 2",
        "max_threads = 2",
        'default_role = "implementation_worker"',
    ],
)
def test_removed_scalar_rejected(repository: Path, scalar: str) -> None:
    path = repository / ".codex/config.toml"
    path.write_text(f"[agents]\n{scalar}\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    reject(repository, "prohibited by repository compatibility policy")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "key", ["name", "description", "model", "model_reasoning_effort", "sandbox_mode"]
)
def test_role_contract_drift(repository: Path, role: str, key: str) -> None:
    path = repository / f".codex/agents/{role}.toml"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text(
        "".join(f'{key} = "drift"\n' if line.startswith(key + " =") else line for line in lines),
        encoding="utf-8",
    )
    reject(repository, f"{key} must be")


@pytest.mark.parametrize(
    "relative,marker",
    [
        ("AGENTS.md", "DESIGN_READY"),
        (".github/PULL_REQUEST_TEMPLATE.md", "Design handoff"),
        *[
            (f".github/ISSUE_TEMPLATE/{name}.yml", "execution-workflow")
            for name in ("work-item", "bug", "verification", "iteration")
        ],
    ],
)
def test_documentation_markers(repository: Path, relative: str, marker: str) -> None:
    replace(repository / relative, marker, "removed-marker")
    reject(repository, "missing required workflow markers")


@pytest.mark.parametrize("content", ["", "agents = true", "[invalid"])
def test_invalid_project_config(repository: Path, content: str) -> None:
    (repository / ".codex/config.toml").write_text(content, encoding="utf-8")
    reject(
        repository, "invalid project Codex TOML" if content == "[invalid" else "missing [agents]"
    )


def test_registration_checked_before_role_file(repository: Path) -> None:
    (repository / ".codex/agents/design-architect.toml").unlink()
    replace(repository / ".codex/config.toml", "agents/implementation-worker.toml", "wrong.toml")
    reject(repository, "config_file must be")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("damage", ["empty", "missing", "scalar", "gate", "session"])
def test_instruction_boundaries(repository: Path, role: str, damage: str) -> None:
    path = repository / f".codex/agents/{role}.toml"
    if damage in {"empty", "missing", "scalar"}:
        text = path.read_text(encoding="utf-8").split("developer_instructions")[0]
        if damage != "missing":
            text += "developer_instructions = " + ('""' if damage == "empty" else "42")
        path.write_text(text, encoding="utf-8")
        reject(repository, "role fields" if damage == "missing" else "nonempty text")
    else:
        marker = (
            "separate sequential session"
            if damage == "session"
            else (
                "Do not edit source"
                if role in {"planning-analyst", "design-architect", "code-reviewer"}
                else "recorded approved DESIGN_READY"
            )
        )
        replace(path, marker, "removed")
        reject(repository, "missing instruction boundaries")


@pytest.mark.parametrize("damage", ["registration", "file", "role-field", "registration-field"])
def test_extra_inventory(repository: Path, damage: str) -> None:
    config = repository / ".codex/config.toml"
    if damage == "file":
        (repository / ".codex/agents/extra.toml").write_text("", encoding="utf-8")
        reject(repository, "unexpected role files")
    elif damage == "role-field":
        path = repository / ".codex/agents/design-architect.toml"
        path.write_text("extra = true\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
        reject(repository, "unexpected or missing role fields")
    else:
        text = config.read_text(encoding="utf-8")
        text += (
            '\n[agents.extra]\ndescription = "extra"\nconfig_file = "extra.toml"\n'
            if damage == "registration"
            else '\nmodel = "gpt-6-astra"\n'
        )
        config.write_text(text, encoding="utf-8")
        reject(
            repository,
            "unexpected role registrations"
            if damage == "registration"
            else "unexpected registration fields",
        )


@pytest.mark.parametrize(
    "override",
    [
        'model = "gpt-6-astra"',
        'model_reasoning_effort = "high"',
    ],
)
def test_project_overrides(repository: Path, override: str) -> None:
    path = repository / ".codex/config.toml"
    path.write_text(override + "\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    reject(repository, "project-level overrides are prohibited")


def test_unrelated_project_settings_allowed(repository: Path) -> None:
    path = repository / ".codex/config.toml"
    path.write_text(
        "[history]\nmax_bytes = 100000\n" + path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    result = run_validator(repository)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Codex ticket workflow configuration is valid.\n"
    assert not result.stderr


@pytest.mark.parametrize("damage", ["missing", "encoding"])
def test_unreadable_document(repository: Path, damage: str) -> None:
    path = repository / "CONTRIBUTING.md"
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(b"\xff")
    reject(repository, "unreadable workflow document")


@pytest.mark.parametrize(
    "relative",
    [
        "CONTRIBUTING.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        *[
            f".github/ISSUE_TEMPLATE/{name}.yml"
            for name in ("work-item", "bug", "verification", "iteration")
        ],
    ],
)
def test_routing_evidence_marker(repository: Path, relative: str) -> None:
    replace(repository / relative, "separate sequential session", "removed")
    reject(repository, "missing required workflow markers")
