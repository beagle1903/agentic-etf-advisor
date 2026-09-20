"""Opt-in disposable contract coverage against PostgreSQL, Neo4j, and Chroma."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from pydantic import SecretStr
from test_checkpoint_lifecycle import Time, invoke, start
from test_revision import Adapters

from etf_advisor.checkpoint import PostgresCheckpointStore
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.chroma_store import ChromaDocumentStore
from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.models import SourceDocument
from etf_advisor.rag.neo4j_store import Neo4jGraphStore, Neo4jUnavailable
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity

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

    try:
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
        with pytest.raises(Neo4jUnavailable, match="prior snapshot remains active"):
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
