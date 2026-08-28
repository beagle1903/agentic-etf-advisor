import pytest
from typer.testing import CliRunner

import etf_advisor.cli as cli
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.rag.evidence import EvidenceRetrievalError


def test_explanation_demo_requires_evidence() -> None:
    result = CliRunner().invoke(cli.app, ["demo", "--with-explanation"])

    assert result.exit_code == 1
    assert "--with-explanation requires --with-evidence" in result.output


def test_evidence_demo_exits_nonzero_before_review_when_retrieval_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeGraphStore:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FailingEvidenceRetriever:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> object:
            raise EvidenceRetrievalError("source service unavailable")

    graph_store = FakeGraphStore()
    monkeypatch.setattr(cli, "ChromaDocumentStore", lambda **kwargs: object())
    monkeypatch.setattr(cli, "Neo4jGraphStore", lambda **kwargs: graph_store)
    monkeypatch.setattr(cli, "HybridRetriever", lambda *args: object())
    monkeypatch.setattr(cli, "HybridCandidateEvidenceRetriever", FailingEvidenceRetriever)

    result = CliRunner().invoke(cli.app, ["demo", "--with-evidence"])

    assert result.exit_code == 1
    assert "Workflow stopped before human review:" in result.output
    assert "Paused for human review:" not in result.output
    assert "source service unavailable" in result.output
    assert graph_store.closed is True


def test_dashboard_command_reports_missing_optional_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "find_spec", lambda name: None)

    result = CliRunner().invoke(cli.app, ["dashboard"])

    assert result.exit_code == 1
    assert "uv sync --extra dashboard" in result.output


def test_dashboard_command_launches_local_streamlit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], bool]] = []

    class Result:
        returncode = 0

    def fake_run(command: list[str], *, check: bool) -> Result:
        calls.append((command, check))
        return Result()

    monkeypatch.setattr(cli, "find_spec", lambda name: object())
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = CliRunner().invoke(cli.app, ["dashboard", "--port", "8765"])

    assert result.exit_code == 0
    assert calls[0][0][1:4] == ["-m", "streamlit", "run"]
    assert calls[0][0][-6:] == [
        "--server.port",
        "8765",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    assert calls[0][1] is False
