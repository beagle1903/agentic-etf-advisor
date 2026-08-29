from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_research_snapshot import research_snapshot
from typer.testing import CliRunner

import etf_advisor.cli as cli
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.rag.evidence import EvidenceRetrievalError
from etf_advisor.rag.indexing import IndexConsistencyError
from etf_advisor.rag.snapshots import (
    ActiveSnapshotIdentity,
    SnapshotManifest,
    SnapshotPublicationReport,
)
from etf_advisor.research.snapshot_io import persist_research_snapshot


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
    tmp_path: Path,
) -> None:
    snapshot = research_snapshot()
    universe = SimpleNamespace(universe_id="test-universe")

    class FakeAdapter:
        def fetch_snapshot(self, universe: object, *, snapshot_version: str) -> object:
            assert universe is not None
            assert snapshot_version == "snapshot-v1"
            return snapshot

    class FakeGraphStore:
        def __init__(self) -> None:
            self.closed = False

        def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None:
            return None

        def snapshot_digest(self, version: str) -> str | None:
            assert version == "snapshot-v1"
            return None

        def close(self) -> None:
            self.closed = True

    graph_store = FakeGraphStore()
    monkeypatch.setattr(
        cli,
        "system_utc_now",
        lambda: datetime(2026, 8, 29, 12, 5, tzinfo=UTC),
    )
    monkeypatch.setattr(cli, "load_research_universe", lambda path: universe)
    monkeypatch.setattr(cli, "YahooResearchAdapter", lambda **kwargs: FakeAdapter())
    monkeypatch.setattr(cli, "ChromaDocumentStore", lambda **kwargs: "chroma-store")
    monkeypatch.setattr(cli, "Neo4jGraphStore", lambda **kwargs: graph_store)

    def fake_publish(snapshot: object, chroma: object, graph: object) -> SnapshotPublicationReport:
        assert snapshot == research_snapshot()
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
        [
            "publish-research-universe",
            "--snapshot-version",
            "snapshot-v1",
            "--snapshot-file",
            str(tmp_path / "snapshot.json"),
        ],
    )

    assert result.exit_code == 0
    assert '"snapshot_version": "snapshot-v1"' in result.output
    assert '"previous_snapshot_version": "snapshot-v0"' in result.output
    assert graph_store.closed is True


def test_publish_retry_reuses_payload_saved_before_store_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    snapshot = research_snapshot()
    universe = SimpleNamespace(universe_id="test-universe")
    payload_path = tmp_path / "snapshot.json"
    fetch_calls = 0
    publish_calls = 0

    class FakeAdapter:
        def fetch_snapshot(self, universe: object, *, snapshot_version: str) -> object:
            nonlocal fetch_calls
            fetch_calls += 1
            assert universe is not None
            assert snapshot_version == "snapshot-v1"
            return snapshot

    class FakeGraphStore:
        def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None:
            return None

        def snapshot_digest(self, version: str) -> str | None:
            return None

        def close(self) -> None:
            pass

    def fake_publish(*args: object) -> SnapshotPublicationReport:
        nonlocal publish_calls
        publish_calls += 1
        if publish_calls == 1:
            raise IndexConsistencyError("activation acknowledgement lost")
        assert args[0] == snapshot
        return SnapshotPublicationReport(
            snapshot_version="snapshot-v1",
            snapshot_digest=snapshot.content_digest(),
            previous_snapshot_version=None,
            chroma_count=1,
            neo4j_count=1,
        )

    monkeypatch.setattr(
        cli,
        "system_utc_now",
        lambda: datetime(2026, 8, 29, 12, 5, tzinfo=UTC),
    )
    monkeypatch.setattr(cli, "load_research_universe", lambda path: universe)
    monkeypatch.setattr(cli, "YahooResearchAdapter", lambda **kwargs: FakeAdapter())
    monkeypatch.setattr(cli, "ChromaDocumentStore", lambda **kwargs: object())
    monkeypatch.setattr(cli, "Neo4jGraphStore", lambda **kwargs: FakeGraphStore())
    monkeypatch.setattr(cli, "publish_research_snapshot", fake_publish)
    arguments = [
        "publish-research-universe",
        "--snapshot-version",
        "snapshot-v1",
        "--snapshot-file",
        str(payload_path),
    ]

    first = CliRunner().invoke(cli.app, arguments)
    second = CliRunner().invoke(cli.app, arguments)

    assert first.exit_code == 1
    assert second.exit_code == 0
    assert fetch_calls == 1
    assert publish_calls == 2


def test_research_snapshot_freshness_uses_source_observation_time() -> None:
    snapshot = research_snapshot()

    report = cli._assess_research_snapshot(
        snapshot,
        clock=lambda: snapshot.ingested_at + timedelta(hours=121),
    )

    assert report.healthy is False
    assert report.observations[0].status == "stale"


def test_publish_rejects_stale_canonical_payload_before_opening_chroma(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    snapshot = research_snapshot()
    payload_path = tmp_path / "snapshot.json"
    persist_research_snapshot(snapshot, payload_path)

    class FakeGraphStore:
        def active_snapshot_identity(self) -> None:
            return None

        def snapshot_digest(self, version: str) -> None:
            return None

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        cli,
        "system_utc_now",
        lambda: snapshot.ingested_at + timedelta(hours=121),
    )
    monkeypatch.setattr(
        cli,
        "load_research_universe",
        lambda path: SimpleNamespace(universe_id=snapshot.universe_id),
    )
    monkeypatch.setattr(cli, "Neo4jGraphStore", lambda **kwargs: FakeGraphStore())
    monkeypatch.setattr(
        cli,
        "ChromaDocumentStore",
        lambda **kwargs: pytest.fail("stale research must not reach Chroma"),
    )

    result = CliRunner().invoke(
        cli.app,
        [
            "publish-research-universe",
            "--snapshot-version",
            snapshot.snapshot_version,
            "--snapshot-file",
            str(payload_path),
        ],
    )

    assert result.exit_code == 1
    assert "Market-data health check failed" in result.output


def test_publish_retry_noops_when_requested_snapshot_is_already_active(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    identity = ActiveSnapshotIdentity("snapshot-v1", "published-digest")

    class FakeChromaStore:
        def missing_document_ids(self, document_ids: list[str]) -> list[str]:
            assert document_ids == ["doc-spy"]
            return []

        def document_metadatas(self, document_ids: list[str]) -> dict[str, dict[str, str]]:
            return {
                "doc-spy": {
                    "snapshot_version": identity.snapshot_version,
                    "snapshot_digest": identity.snapshot_digest,
                }
            }

    class FakeGraphStore:
        def active_snapshot_identity(self) -> ActiveSnapshotIdentity:
            return identity

        def snapshot_digest(self, version: str) -> str:
            assert version == "snapshot-v1"
            return identity.snapshot_digest

        def snapshot_manifest(self, version: str) -> SnapshotManifest:
            return SnapshotManifest(
                snapshot_version=version,
                snapshot_digest=identity.snapshot_digest,
                document_count=1,
                document_ids=("doc-spy",),
            )

        def close(self) -> None:
            pass

    monkeypatch.setattr(cli, "Neo4jGraphStore", lambda **kwargs: FakeGraphStore())
    monkeypatch.setattr(cli, "ChromaDocumentStore", lambda **kwargs: FakeChromaStore())
    monkeypatch.setattr(
        cli,
        "YahooResearchAdapter",
        lambda **kwargs: pytest.fail("an already-active retry must not refetch Yahoo"),
    )

    result = CliRunner().invoke(
        cli.app,
        [
            "publish-research-universe",
            "--snapshot-version",
            "snapshot-v1",
            "--snapshot-file",
            str(tmp_path / "missing.json"),
        ],
    )

    assert result.exit_code == 0
    assert '"already_active": true' in result.output
    assert '"chroma_count": 1' in result.output


def test_publish_retry_fails_when_active_chroma_documents_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    identity = ActiveSnapshotIdentity("snapshot-v1", "published-digest")

    class FakeGraphStore:
        def active_snapshot_identity(self) -> ActiveSnapshotIdentity:
            return identity

        def snapshot_digest(self, version: str) -> str:
            return identity.snapshot_digest

        def snapshot_manifest(self, version: str) -> SnapshotManifest:
            return SnapshotManifest(version, identity.snapshot_digest, 1, ("doc-spy",))

        def close(self) -> None:
            pass

    class MissingChromaStore:
        def missing_document_ids(self, document_ids: list[str]) -> list[str]:
            return list(document_ids)

        def document_metadatas(self, document_ids: list[str]) -> dict[str, dict[str, str]]:
            return {}

    monkeypatch.setattr(cli, "Neo4jGraphStore", lambda **kwargs: FakeGraphStore())
    monkeypatch.setattr(cli, "ChromaDocumentStore", lambda **kwargs: MissingChromaStore())

    result = CliRunner().invoke(
        cli.app,
        [
            "publish-research-universe",
            "--snapshot-version",
            "snapshot-v1",
            "--snapshot-file",
            str(tmp_path / "missing.json"),
        ],
    )

    assert result.exit_code == 1
    assert "Chroma is missing 1 active snapshot document" in result.output
    assert '"already_active": true' not in result.output
