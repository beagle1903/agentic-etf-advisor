"""Opt-in disposable contract coverage against PostgreSQL, Neo4j, and Chroma."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Event
from typing import Any
from uuid import uuid4

import pytest
from pydantic import SecretStr
from test_checkpoint_lifecycle import Time, invoke, start
from test_lossless_contract import lossless_snapshot
from test_research_snapshot import research_snapshot
from test_revision import Adapters
from test_workflow import valid_profile
from typer.testing import CliRunner

from etf_advisor import cli
from etf_advisor.checkpoint import PostgresCheckpointStore
from etf_advisor.dashboard import review_payload
from etf_advisor.encoding import ResearchIntegrityError, document_fingerprint
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.chroma_store import ChromaDocumentStore
from etf_advisor.rag.evidence import HybridCandidateEvidenceRetriever
from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.models import SourceDocument
from etf_advisor.rag.neo4j_store import (
    _LOCK_CATALOG,
    Neo4jGraphStore,
    Neo4jUnavailable,
    _legacy_row,
)
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity, publish_research_snapshot
from etf_advisor.research.snapshot_io import persist_research_snapshot

pytestmark = pytest.mark.real_store

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "compose.integration.yaml"
INTEGRATION_ENABLED = "RUN_REAL_STORE_TESTS"


@dataclass(frozen=True)
class RealStoreEnvironment:
    project: str
    chroma_port: int
    neo4j_port: int
    postgres_port: int

    @property
    def postgres_uri(self) -> str:
        return (
            "postgresql://integration:integration-password@127.0.0.1:"
            f"{self.postgres_port}/integration"
        )


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@pytest.fixture(scope="session")
def real_stores() -> RealStoreEnvironment:
    """Start one isolated Compose project only when the explicit opt-in is set."""

    if os.environ.get(INTEGRATION_ENABLED) != "1":
        pytest.skip(f"set {INTEGRATION_ENABLED}=1 to run disposable real-store tests")
    if shutil.which("docker") is None:
        pytest.fail("Docker Desktop is required for real-store integration tests.")

    environment = RealStoreEnvironment(
        project=f"etf-advisor-contract-{uuid4().hex[:12]}",
        chroma_port=_free_loopback_port(),
        neo4j_port=_free_loopback_port(),
        postgres_port=_free_loopback_port(),
    )
    compose_environment = {
        **os.environ,
        "REAL_STORE_CHROMA_PORT": str(environment.chroma_port),
        "REAL_STORE_NEO4J_PORT": str(environment.neo4j_port),
        "REAL_STORE_POSTGRES_PORT": str(environment.postgres_port),
    }
    command = [
        "docker",
        "compose",
        "--project-name",
        environment.project,
        "--file",
        str(COMPOSE_FILE),
    ]
    try:
        try:
            subprocess.run(
                [*command, "up", "--detach", "--wait", "--wait-timeout", "180"],
                cwd=ROOT,
                env=compose_environment,
                check=True,
                capture_output=True,
                text=True,
                timeout=240,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            pytest.fail(f"Could not start disposable real-store services: {exc}")
        yield environment
    finally:
        subprocess.run(
            [*command, "down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            env=compose_environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )


def test_real_store_start_failure_still_tears_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(INTEGRATION_ENABLED, "1")
    monkeypatch.setattr(shutil, "which", lambda executable: "docker")
    calls: list[list[str]] = []

    def failed_start(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if "up" in command:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", failed_start)

    with pytest.raises(pytest.fail.Exception, match="Could not start"):
        next(real_stores.__wrapped__())

    assert any(command[-3:] == ["down", "--volumes", "--remove-orphans"] for command in calls)


class DeterministicEmbedding:
    """Keep the Chroma contract independent of model downloads or network calls."""

    @staticmethod
    def name() -> str:
        return "issue-52-deterministic"

    @staticmethod
    def get_config() -> dict[str, Any]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> DeterministicEmbedding:
        return DeterministicEmbedding()

    def is_legacy(self) -> bool:
        return False

    def default_space(self) -> str:
        return "l2"

    def supported_spaces(self) -> list[str]:
        return ["l2"]

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(sum(map(ord, text)) % 101)] for text in input]

    def embed_query(self, input: list[str]) -> Any:
        import numpy as np

        return [np.array(vector) for vector in self(input)]


def _document(
    document_id: str,
    symbol: str,
    *,
    snapshot_version: str | None = None,
    snapshot_digest: str | None = None,
) -> SourceDocument:
    metadata: dict[str, Any] = {
        "name": f"{symbol} ETF",
        "fund_family": "Test Funds",
        "category": "Large Blend",
        "field_provenance_schema_version": 1,
        "field_provenance_json": (
            '{"sector_exposures":{"missing_reason":null,'
            '"value":[{"name":"technology","symbol":null,"weight_pct":37.4}]}}'
        ),
        "sector_exposures_status": "available",
    }
    if snapshot_version is not None:
        metadata["snapshot_version"] = snapshot_version
    if snapshot_digest is not None:
        metadata["snapshot_digest"] = snapshot_digest
    return SourceDocument(
        document_id=document_id,
        symbol=symbol,
        title=f"{symbol} research",
        content=f"{symbol} attributable ETF research content",
        source="fixture",
        source_url=f"https://example.test/{symbol}",
        observed_at=datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
        metadata=metadata,
    )


def test_postgres_close_recompile_restore_and_retry_receipt(
    real_stores: RealStoreEnvironment,
) -> None:
    pytest.importorskip("psycopg")
    store = PostgresCheckpointStore(SecretStr(real_stores.postgres_uri), clock=Time())
    store.setup()
    token = str(uuid4())
    adapters = Adapters()
    adapters.fail_retrieval = True

    failed = start(store, token=token, adapters=adapters)
    revision = failed["revision_ledger"]["revisions"][-1]
    receipt = revision["receipts"][-1]
    assert receipt["status"] == "failed"

    adapters.fail_retrieval = False
    retry = invoke(
        store,
        {
            "retry_request": {
                "action": "retry",
                "revision_id": revision["revision_id"],
                "operation_id": receipt["operation_id"],
            }
        },
        token=token,
        adapters=adapters,
    )
    assert retry["status"] == "awaiting_human_review"
    assert adapters.retrieval_calls == 2

    with store.managed(token) as saver:
        restored = build_graph(checkpointer=saver, clock=store.clock, candidate_retriever=adapters)
        restored_state = dict(restored.get_state({"configurable": {"thread_id": token}}).values)
    receipts = restored_state["revision_ledger"]["revisions"][-1]["receipts"]
    assert [item["operation_id"] for item in receipts] == [
        receipt["operation_id"],
        receipts[-1]["operation_id"],
    ]
    assert receipts[-1]["operation_id"] != receipt["operation_id"]
    assert receipts[-1]["status"] == "succeeded"


def test_neo4j_immutable_activation_failure_preserves_previous_pointer(
    real_stores: RealStoreEnvironment,
) -> None:
    store = Neo4jGraphStore(
        f"bolt://127.0.0.1:{real_stores.neo4j_port}",
        ("neo4j", "integration-password"),
    )
    try:
        first = _document(
            "snapshot-v1-spy", "SPY", snapshot_version="snapshot-v1", snapshot_digest="d1"
        )
        assert (
            store.publish_snapshot(
                [first],
                snapshot_version="snapshot-v1",
                universe_id="integration",
                universe_version="1",
                snapshot_digest="d1",
            )
            == 1
        )
        assert store.active_snapshot_identity() == ActiveSnapshotIdentity("snapshot-v1", "d1")

        conflicting = _document(
            "snapshot-v1-qqq", "QQQ", snapshot_version="snapshot-v1", snapshot_digest="d2"
        )
        with pytest.raises(Neo4jUnavailable, match="CAS"):
            store.publish_snapshot(
                [conflicting],
                snapshot_version="snapshot-v1",
                universe_id="integration",
                universe_version="1",
                snapshot_digest="d2",
            )
        assert store.active_snapshot_identity() == ActiveSnapshotIdentity("snapshot-v1", "d1")
        assert store.snapshot_digest("snapshot-v1") == "d1"
    finally:
        store.close()


def test_chroma_filters_exact_identity_and_hides_inactive_staging(
    real_stores: RealStoreEnvironment,
) -> None:
    store = ChromaDocumentStore(
        host="127.0.0.1",
        port=real_stores.chroma_port,
        collection_name=f"contract-{uuid4().hex}",
        embedding_function=DeterministicEmbedding(),
    )
    legacy = _document("legacy-spy", "SPY")
    active = _document(
        "snapshot-v1-qqq", "QQQ", snapshot_version="snapshot-v1", snapshot_digest="d1"
    )
    inactive = _document(
        "snapshot-v2-vti", "VTI", snapshot_version="snapshot-v2", snapshot_digest="d2"
    )
    assert store.upsert([legacy, active, inactive]) == 3

    active_results = store.search(
        "ETF research",
        limit=5,
        where={"$and": [{"snapshot_version": "snapshot-v1"}, {"snapshot_digest": "d1"}]},
    )
    assert [result.document_id for result in active_results] == [active.document_id]

    class NoActiveSnapshot:
        def active_snapshot_identity(self) -> None:
            return None

        def find_contexts(self, document_ids: list[str]) -> dict[str, object]:
            return {}

    legacy_results = HybridRetriever(store, NoActiveSnapshot()).search("ETF research", limit=5)
    assert [result.document_id for result in legacy_results] == [legacy.document_id]


def _lossless_stores(
    real_stores: RealStoreEnvironment,
) -> tuple[ChromaDocumentStore, Neo4jGraphStore]:
    return (
        ChromaDocumentStore(
            host="127.0.0.1",
            port=real_stores.chroma_port,
            collection_name=f"lossless-{uuid4().hex}",
            embedding_function=DeterministicEmbedding(),
        ),
        Neo4jGraphStore(
            f"bolt://127.0.0.1:{real_stores.neo4j_port}", ("neo4j", "integration-password")
        ),
    )


def test_lossless_real_chroma_graph_postgres_reopen_dashboard(
    real_stores: RealStoreEnvironment,
) -> None:
    chroma, graph_store = _lossless_stores(real_stores)
    snapshot = lossless_snapshot(f"lossless-{uuid4().hex}")
    try:
        publish_research_snapshot(snapshot, chroma, graph_store, clock=lambda: snapshot.ingested_at)
        documents = snapshot.to_source_documents()
        read = chroma.document_records([document.document_id for document in documents])
        assert all(
            record.metadata["top_10_concentration_pct"] == "46.272379900000004"
            for record in read.values()
        )
        retriever = HybridCandidateEvidenceRetriever(
            HybridRetriever(chroma, graph_store),
            clock=lambda: snapshot.ingested_at,
            max_age=timedelta(hours=24),
        )
        store = PostgresCheckpointStore(
            SecretStr(real_stores.postgres_uri), clock=lambda: snapshot.ingested_at
        )
        store.setup()
        token = str(uuid4())
        with store.managed(token, create=True) as saver:
            graph = build_graph(
                checkpointer=saver, clock=store.clock, candidate_retriever=retriever
            )
            state = dict(
                graph.invoke({"profile": valid_profile()}, {"configurable": {"thread_id": token}})
            )
        assert state["status"] == "awaiting_human_review", state.get("errors")
        with store.managed(token) as saver:
            reopened = build_graph(
                checkpointer=saver, clock=store.clock, candidate_retriever=retriever
            )
            restored_snapshot = reopened.get_state({"configurable": {"thread_id": token}})
            restored = dict(restored_snapshot.values)
            restored["__interrupt__"] = tuple(
                interrupt for task in restored_snapshot.tasks for interrupt in task.interrupts
            )
        payload = review_payload(restored)
        assert payload["candidate_evidence"] is not None
        assert all(
            candidate["metadata"]["top_10_concentration_pct"] == "46.272379900000004"
            for candidate in payload["candidate_evidence"]["candidates"]
        )
        graph_store.verify_snapshot(snapshot.snapshot_version)
    finally:
        graph_store.close()


@pytest.mark.parametrize("damage", ["content", "recomputed_content", "valid_metadata"])
def test_real_schema2_mutated_chroma_blocks_before_evidence(
    real_stores: RealStoreEnvironment,
    damage: str,
) -> None:
    chroma, graph = _lossless_stores(real_stores)
    snapshot = lossless_snapshot(f"mutation-{uuid4().hex}")
    try:
        publish_research_snapshot(snapshot, chroma, graph, clock=lambda: snapshot.ingested_at)
        document = snapshot.to_source_documents()[0]
        changed = document.content + " forged"
        metadata = document.chroma_metadata()
        if damage == "recomputed_content":
            metadata["document_fingerprint"] = document_fingerprint(
                document.document_id, changed, metadata
            )
        elif damage == "valid_metadata":
            record = snapshot.records[0].model_copy(deep=True)
            record.name.value = "Semantically valid competing name"
            competing = snapshot._to_source_document(record, digest=snapshot.content_digest())
            changed, metadata = competing.content, competing.chroma_metadata()
        chroma._collection.update(
            ids=[document.document_id], documents=[changed], metadatas=[metadata]
        )
        with pytest.raises(ResearchIntegrityError):
            HybridRetriever(chroma, graph).search("ETF evidence", limit=5)
    finally:
        graph.close()


@pytest.mark.parametrize("schema", [1, 2, "historical-1"])
@pytest.mark.parametrize("with_payload", [False, True])
def test_actual_cli_stale_active_retry_verifies_without_writes(
    real_stores: RealStoreEnvironment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    schema: int | str,
    with_payload: bool,
) -> None:
    chroma, graph = _lossless_stores(real_stores)
    version = f"retry-{uuid4().hex}"
    if schema == 2:
        snapshot = lossless_snapshot(version)
    else:
        snapshot = research_snapshot().model_copy(deep=True)
        snapshot.snapshot_version = version
        for field in snapshot.records[0].research_fields().values():
            field.snapshot_version = version
    try:
        publish_research_snapshot(snapshot, chroma, graph, clock=lambda: snapshot.ingested_at)
        if schema == "historical-1":
            # Reproduce the pre-schema-2 persisted graph shape, without repairing it.
            graph._execute(
                "MATCH (s:ResearchSnapshot {version: $version}) "
                "REMOVE s.manifest_json, s.schema_version",
                {"version": version},
            )
            for document in snapshot.to_source_documents():
                graph._execute(
                    "MATCH (s:SourceDocument {document_id: $id}) SET s = $properties",
                    {"id": document.document_id, "properties": _legacy_row(document)["properties"]},
                )
        payload_path = tmp_path / "retry.json"
        if with_payload:
            persist_research_snapshot(snapshot, payload_path)
        monkeypatch.setattr(
            cli,
            "Neo4jGraphStore",
            lambda **kwargs: Neo4jGraphStore(
                f"bolt://127.0.0.1:{real_stores.neo4j_port}", ("neo4j", "integration-password")
            ),
        )
        monkeypatch.setattr(cli, "ChromaDocumentStore", lambda **kwargs: chroma)
        monkeypatch.setattr(
            cli, "system_utc_now", lambda: snapshot.ingested_at + timedelta(days=100)
        )
        monkeypatch.setattr(
            cli,
            "YahooResearchAdapter",
            lambda **kwargs: pytest.fail("active retry refetched provider"),
        )
        monkeypatch.setattr(
            chroma, "stage_snapshot", lambda *args: pytest.fail("active retry staged records")
        )
        monkeypatch.setattr(
            Neo4jGraphStore,
            "publish_snapshot",
            lambda *args, **kwargs: pytest.fail("active retry wrote graph"),
        )
        result = CliRunner().invoke(
            cli.app,
            [
                "publish-research-universe",
                "--snapshot-version",
                version,
                "--snapshot-file",
                str(payload_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert '"already_active": true' in result.output
    finally:
        graph.close()


@pytest.mark.parametrize("active", [True, False])
@pytest.mark.parametrize(
    "damage", ["foreign", "wrong_label", "null_id", "duplicate", "missing", "extra"]
)
def test_real_exact_manifest_enumerates_all_contains_children(
    real_stores: RealStoreEnvironment,
    active: bool,
    damage: str,
) -> None:
    chroma, graph = _lossless_stores(real_stores)
    snapshot = lossless_snapshot(f"manifest-{uuid4().hex}")
    try:
        publish_research_snapshot(snapshot, chroma, graph, clock=lambda: snapshot.ingested_at)
        if not active:
            replacement = lossless_snapshot(f"replacement-{uuid4().hex}")
            publish_research_snapshot(
                replacement, chroma, graph, clock=lambda: replacement.ingested_at
            )
        parameters = {
            "version": snapshot.snapshot_version,
            "document_id": snapshot.to_source_documents()[0].document_id,
        }
        if damage == "duplicate":
            query = (
                "MATCH (s:ResearchSnapshot {version:$version})-[:CONTAINS]->"
                "(d {document_id:$document_id}) CREATE (s)-[:CONTAINS]->(d)"
            )
        elif damage == "missing":
            query = (
                "MATCH (s:ResearchSnapshot {version:$version})-[r:CONTAINS]->"
                "(d {document_id:$document_id}) DELETE r"
            )
        elif damage == "wrong_label":
            query = (
                "MATCH (s:ResearchSnapshot {version:$version}) "
                "CREATE (d:Foreign {document_id:'foreign'}) CREATE (s)-[:CONTAINS]->(d)"
            )
        elif damage == "null_id":
            query = (
                "MATCH (s:ResearchSnapshot {version:$version}) "
                "CREATE (d:SourceDocument) CREATE (s)-[:CONTAINS]->(d)"
            )
        elif damage == "extra":
            parameters["digest"] = snapshot.content_digest()
            query = (
                "MATCH (s:ResearchSnapshot {version:$version}) "
                "CREATE (d:SourceDocument {document_id:$version, snapshot_version:$version, "
                "snapshot_digest:$digest}) CREATE (s)-[:CONTAINS]->(d)"
            )
        else:
            query = (
                "MATCH (s:ResearchSnapshot {version:$version}) "
                "CREATE (d:SourceDocument {document_id:$version}) CREATE (s)-[:CONTAINS]->(d)"
            )
        graph._execute(query, parameters)
        with pytest.raises((Neo4jUnavailable, ValueError)):
            graph.snapshot_manifest(snapshot.snapshot_version)
    finally:
        graph.close()


def test_real_postwrite_failure_rolls_back_and_cas_fails(real_stores: RealStoreEnvironment) -> None:
    chroma, graph = _lossless_stores(real_stores)
    previous = graph.active_snapshot_identity()
    snapshot = lossless_snapshot(f"rollback-{uuid4().hex}")
    original = graph._verify_projection
    try:

        def fail_after_writes(*args: Any, **kwargs: Any) -> None:
            raise Neo4jUnavailable("injected semantic failure")

        graph._verify_projection = fail_after_writes
        with pytest.raises(Neo4jUnavailable, match="injected semantic failure"):
            publish_research_snapshot(snapshot, chroma, graph, clock=lambda: snapshot.ingested_at)
        fresh = Neo4jGraphStore(
            f"bolt://127.0.0.1:{real_stores.neo4j_port}", ("neo4j", "integration-password")
        )
        try:
            assert fresh.active_snapshot_identity() == previous
            assert fresh.snapshot_digest(snapshot.snapshot_version) is None
            assert fresh.missing_document_ids(
                [document.document_id for document in snapshot.to_source_documents()]
            ) == [document.document_id for document in snapshot.to_source_documents()]
            if previous is not None:
                fresh.verify_snapshot(previous.snapshot_version)
        finally:
            fresh.close()
        graph._verify_projection = original
        with pytest.raises(Neo4jUnavailable, match="CAS"):
            graph.publish_snapshot(
                snapshot.to_source_documents(),
                snapshot_version=snapshot.snapshot_version,
                snapshot_digest=snapshot.content_digest(),
                universe_id=snapshot.universe_id,
                universe_version=snapshot.universe_version,
                expected_prior=None,
            )
        assert graph.snapshot_digest(snapshot.snapshot_version) is None
    finally:
        graph.close()


def test_real_a_b_a_reactivation_and_shrinking_universe_preserve_sources(
    real_stores: RealStoreEnvironment,
) -> None:
    chroma, graph = _lossless_stores(real_stores)
    first = lossless_snapshot(f"history-a-{uuid4().hex}")
    second = lossless_snapshot(f"history-b-{uuid4().hex}", symbols=("QQQ",))
    try:
        publish_research_snapshot(first, chroma, graph, clock=lambda: first.ingested_at)
        first_manifest = graph.snapshot_manifest(first.snapshot_version)
        publish_research_snapshot(second, chroma, graph, clock=lambda: second.ingested_at)
        graph.verify_snapshot(first.snapshot_version)
        graph.verify_snapshot(second.snapshot_version)
        assert graph.snapshot_manifest(first.snapshot_version) == first_manifest
        publish_research_snapshot(first, chroma, graph, clock=lambda: first.ingested_at)
        graph.verify_snapshot(first.snapshot_version)
        graph.verify_snapshot(second.snapshot_version)
        assert graph.snapshot_manifest(first.snapshot_version) == first_manifest
    finally:
        graph.close()


def test_real_lost_commit_acknowledgement_is_uncertain_and_readonly_retry_verifies(
    real_stores: RealStoreEnvironment,
) -> None:
    chroma, graph = _lossless_stores(real_stores)
    snapshot = lossless_snapshot(f"ack-{uuid4().hex}")
    actual_driver = graph._driver

    class LostAcknowledgement:
        def __init__(self, target: Any) -> None:
            self.target = target

        def __getattr__(self, name: str) -> Any:
            return getattr(self.target, name)

        def commit(self) -> None:
            self.target.commit()
            raise OSError("injected lost acknowledgement")

    class Session:
        def __init__(self, target: Any) -> None:
            self.target = target

        def __enter__(self) -> Any:
            self.target.__enter__()
            return self

        def __exit__(self, *args: Any) -> Any:
            return self.target.__exit__(*args)

        def begin_transaction(self) -> LostAcknowledgement:
            return LostAcknowledgement(self.target.begin_transaction())

    class Driver:
        def __getattr__(self, name: str) -> Any:
            return getattr(actual_driver, name)

        def session(self, **kwargs: Any) -> Session:
            return Session(actual_driver.session(**kwargs))

    graph._driver = Driver()
    try:
        with pytest.raises(Neo4jUnavailable, match="acknowledgement is uncertain"):
            publish_research_snapshot(snapshot, chroma, graph, clock=lambda: snapshot.ingested_at)
        graph._driver = actual_driver
        assert graph.active_snapshot_identity() == ActiveSnapshotIdentity(
            snapshot.snapshot_version, snapshot.content_digest()
        )
        retry = publish_research_snapshot(
            snapshot, chroma, graph, clock=lambda: snapshot.ingested_at + timedelta(days=100)
        )
        assert retry.already_active
    finally:
        graph.close()


def test_real_separate_client_same_id_staging_never_overwrites(
    real_stores: RealStoreEnvironment,
) -> None:
    chroma, graph = _lossless_stores(real_stores)
    second = ChromaDocumentStore(
        host="127.0.0.1",
        port=real_stores.chroma_port,
        collection_name=chroma._collection_name,
        embedding_function=DeterministicEmbedding(),
    )
    document = lossless_snapshot(f"race-{uuid4().hex}").to_source_documents()[0]
    competing_snapshot = lossless_snapshot(document.metadata["snapshot_version"])
    competing_snapshot.records[0].name.value = "Competing source fact"
    conflicting = competing_snapshot.to_source_documents()[0]
    conflicting.document_id = document.document_id
    conflicting.metadata["snapshot_digest"] = document.metadata["snapshot_digest"]
    conflicting.metadata["document_fingerprint"] = document_fingerprint(
        conflicting.document_id, conflicting.content, conflicting.chroma_metadata()
    )
    barrier = Barrier(2)
    first_read, second_read = chroma.document_records, second.document_records

    def read_at_barrier(reader: Any, ids: list[str], *, require_all: bool = True) -> Any:
        result = reader(ids, require_all=require_all)
        if not require_all:
            barrier.wait(timeout=10)
        return result

    chroma.document_records = lambda ids, **kwargs: read_at_barrier(first_read, ids, **kwargs)
    second.document_records = lambda ids, **kwargs: read_at_barrier(second_read, ids, **kwargs)

    def stage(store: ChromaDocumentStore, candidate: SourceDocument) -> bool:
        try:
            store.stage_snapshot([candidate])
            return True
        except ValueError:
            return False
        except RuntimeError:
            return False

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = [
                future.result()
                for future in [
                    pool.submit(stage, chroma, document),
                    pool.submit(stage, second, conflicting),
                ]
            ]
        assert sum(outcomes) == 1
        chroma.document_records = first_read
        second.document_records = second_read
        stored = chroma.document_records([document.document_id])[document.document_id]
        accepted = document if stored.content == document.content else conflicting
        assert stored.content == accepted.content
        assert chroma.stage_snapshot([accepted]) == second.stage_snapshot([accepted]) == 1
    finally:
        graph.close()


def _ordinary_document(symbol: str) -> SourceDocument:
    return SourceDocument(
        document_id=f"ordinary-{uuid4().hex}",
        symbol=symbol,
        title="ordinary source",
        content="ordinary source",
        source="fixed-test",
        source_url="https://example.com/source",
        observed_at=datetime(2026, 9, 26, tzinfo=UTC),
        metadata={
            "name": "Competing ordinary name",
            "fund_family": "Competing family",
            "category": "Competing category",
        },
    )


@pytest.mark.parametrize("symbol", ["QQQ", "OTHER"])
def test_real_active_research_blocks_generic_indexing_atomically(
    real_stores: RealStoreEnvironment,
    symbol: str,
) -> None:
    chroma, graph = _lossless_stores(real_stores)
    snapshot = lossless_snapshot(f"generic-guard-{uuid4().hex}")
    first, second = _ordinary_document(symbol), _ordinary_document("DIFFERENT")
    try:
        publish_research_snapshot(snapshot, chroma, graph, clock=lambda: snapshot.ingested_at)
        identity = graph.active_snapshot_identity()
        with pytest.raises(Neo4jUnavailable) as blocked:
            graph.upsert([first, second])
        assert blocked.value.code == "projection_integrity"
        assert graph.missing_document_ids([first.document_id, second.document_id]) == [
            first.document_id,
            second.document_id,
        ]
        assert graph.active_snapshot_identity() == identity
        graph.verify_snapshot(snapshot.snapshot_version)
    finally:
        graph.close()


@pytest.mark.parametrize("first_writer", ["publication", "generic"] * 3)
def test_real_generic_index_and_publication_serialize_on_catalog_lock(
    real_stores: RealStoreEnvironment,
    first_writer: str,
) -> None:
    chroma, graph = _lossless_stores(real_stores)
    generic = Neo4jGraphStore(
        f"bolt://127.0.0.1:{real_stores.neo4j_port}", ("neo4j", "integration-password")
    )
    snapshot = lossless_snapshot(f"generic-race-{uuid4().hex}", symbols=("RACE",))
    ordinary = _ordinary_document("RACE")
    release = Event()
    generic_rolled_back = Event()
    attempted = {name: Event() for name in ("publication", "generic")}
    acquired = {name: Event() for name in ("publication", "generic")}

    class Transaction:
        def __init__(self, target: Any, writer: str) -> None:
            self.target, self.writer = target, writer

        def __getattr__(self, name: str) -> Any:
            return getattr(self.target, name)

        def rollback(self) -> None:
            self.target.rollback()
            if self.writer == "generic":
                generic_rolled_back.set()

        def run(self, query: str, parameters: Any) -> Any:
            if query != _LOCK_CATALOG:
                return self.target.run(query, parameters)
            attempted[self.writer].set()
            rows = list(self.target.run(query, parameters))
            acquired[self.writer].set()
            if self.writer == first_writer:
                assert release.wait(timeout=20), "test did not release catalog lock"
            return rows

    class Session:
        def __init__(self, target: Any, writer: str) -> None:
            self.target, self.writer = target, writer

        def __enter__(self) -> Any:
            self.target.__enter__()
            return self

        def __exit__(self, *args: Any) -> Any:
            return self.target.__exit__(*args)

        def begin_transaction(self) -> Transaction:
            return Transaction(self.target.begin_transaction(), self.writer)

    class Driver:
        def __init__(self, target: Any, writer: str) -> None:
            self.target, self.writer = target, writer

        def __getattr__(self, name: str) -> Any:
            return getattr(self.target, name)

        def session(self, **kwargs: Any) -> Session:
            return Session(self.target.session(**kwargs), self.writer)

    try:
        graph.ensure_schema()
        graph._execute("MATCH (:ResearchCatalog {id:'active'})-[r:ACTIVE_SNAPSHOT]->() DELETE r")
        graph.ensure_schema = lambda: None
        generic.ensure_schema = lambda: None
        graph._driver = Driver(graph._driver, "publication")
        generic._driver = Driver(generic._driver, "generic")

        def write(writer: str) -> bool:
            if writer == "publication":
                publish_research_snapshot(
                    snapshot, chroma, graph, clock=lambda: snapshot.ingested_at
                )
                return True
            try:
                return generic.upsert([ordinary]) == 1
            except Neo4jUnavailable as error:
                if error.code != "projection_integrity":
                    assert error.code == "retrieval_unavailable"
                    assert str(error) == "Generic graph indexing failed; confirmed rollback."
                    assert (
                        getattr(error.__context__, "code", None)
                        == "Neo.TransientError.Transaction.DeadlockDetected"
                    )
                return False

        second_writer = "generic" if first_writer == "publication" else "publication"
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(write, first_writer)
            try:
                assert acquired[first_writer].wait(timeout=10)
                second = pool.submit(write, second_writer)
                assert attempted[second_writer].wait(timeout=10)
                assert not acquired[second_writer].wait(timeout=0.25)
            finally:
                release.set()
            assert first.result(timeout=20)
            assert second.result(timeout=20) == (first_writer == "generic")
        if first_writer == "publication":
            assert generic_rolled_back.is_set()
        verifier = Neo4jGraphStore(
            f"bolt://127.0.0.1:{real_stores.neo4j_port}", ("neo4j", "integration-password")
        )
        try:
            assert verifier.active_snapshot_identity() == ActiveSnapshotIdentity(
                snapshot.snapshot_version, snapshot.content_digest()
            )
            verifier.verify_snapshot(snapshot.snapshot_version)
            assert verifier.missing_document_ids([ordinary.document_id]) == (
                [ordinary.document_id] if first_writer == "publication" else []
            )
            with pytest.raises(Neo4jUnavailable) as blocked:
                verifier.upsert([ordinary])
            assert blocked.value.code == "projection_integrity"
        finally:
            verifier.close()
    finally:
        release.set()
        graph.close()
        generic.close()
