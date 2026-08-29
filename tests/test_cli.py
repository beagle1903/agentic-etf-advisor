import pytest
from typer.testing import CliRunner

import etf_advisor.cli as cli
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.rag.evidence import EvidenceRetrievalError
from etf_advisor.rag.snapshots import SnapshotPublicationReport


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


def test_publish_research_universe_wires_versioned_snapshot_and_closes_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAdapter:
        def fetch_snapshot(self, universe: object, *, snapshot_version: str) -> str:
            assert universe == "curated-universe"
            assert snapshot_version == "snapshot-v1"
            return "validated-snapshot"

    class FakeGraphStore:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    graph_store = FakeGraphStore()
    monkeypatch.setattr(cli, "load_research_universe", lambda path: "curated-universe")
    monkeypatch.setattr(cli, "YahooResearchAdapter", lambda **kwargs: FakeAdapter())
    monkeypatch.setattr(cli, "ChromaDocumentStore", lambda **kwargs: "chroma-store")
    monkeypatch.setattr(cli, "Neo4jGraphStore", lambda **kwargs: graph_store)

    def fake_publish(snapshot: object, chroma: object, graph: object) -> SnapshotPublicationReport:
        assert snapshot == "validated-snapshot"
        assert chroma == "chroma-store"
        assert graph is graph_store
        return SnapshotPublicationReport(
            snapshot_version="snapshot-v1",
            snapshot_digest="abc123",
            previous_snapshot_version="snapshot-v0",
            chroma_count=6,
            neo4j_count=6,
        )

    monkeypatch.setattr(cli, "publish_research_snapshot", fake_publish)

    result = CliRunner().invoke(
        cli.app,
        ["publish-research-universe", "--snapshot-version", "snapshot-v1"],
    )

    assert result.exit_code == 0
    assert '"snapshot_version": "snapshot-v1"' in result.output
    assert '"previous_snapshot_version": "snapshot-v0"' in result.output
    assert graph_store.closed is True
