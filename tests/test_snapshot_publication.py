from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from typing import Any
from uuid import uuid4

import pytest
from test_research_snapshot import research_snapshot

from etf_advisor.data.quality import MarketDataQualityError
from etf_advisor.rag.chroma_store import (
    BLOCKED_VISIBILITY_VALUE,
    LEGACY_VISIBILITY_KEY,
    ChromaDocumentStore,
)
from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.indexing import IndexConsistencyError
from etf_advisor.rag.models import RetrievedSource, SourceDocument
from etf_advisor.rag.snapshots import (
    ActiveSnapshotIdentity,
)
from etf_advisor.rag.snapshots import (
    publish_research_snapshot as _publish_research_snapshot,
)


def publish_research_snapshot(snapshot: Any, chroma: Any, graph: Any) -> Any:
    return _publish_research_snapshot(snapshot, chroma, graph, clock=lambda: snapshot.ingested_at)


class FakeChromaStore:
    def __init__(self, *, missing: bool = False, corrupt_metadata: bool = False) -> None:
        self.missing = missing
        self.corrupt_metadata = corrupt_metadata
        self.documents: list[SourceDocument] = []
        self.upsert_calls = 0

    def upsert(self, documents: list[SourceDocument]) -> int:
        self.upsert_calls += 1
        self.documents = documents
        return len(documents)

    def stage_snapshot(self, documents: list[SourceDocument]) -> int:
        return self.upsert(documents)

    def missing_document_ids(self, document_ids: list[str]) -> list[str]:
        return document_ids if self.missing else []

    def document_metadatas(
        self, document_ids: list[str]
    ) -> dict[str, dict[str, str | int | float | bool]]:
        metadata = {document.document_id: document.chroma_metadata() for document in self.documents}
        if self.corrupt_metadata:
            metadata[document_ids[0]]["snapshot_digest"] = "wrong-digest"
        return metadata

    def document_records(self, document_ids: list[str]) -> dict[str, RetrievedSource]:
        if self.missing:
            return {}
        metadata = self.document_metadatas(document_ids)
        return {
            document.document_id: RetrievedSource(
                document_id=document.document_id,
                content=document.content,
                metadata=metadata[document.document_id],
            )
            for document in self.documents
            if document.document_id in document_ids
        }


class FakeSnapshotGraphStore:
    def __init__(self, *, fail: bool = False, existing_digest: str | None = None) -> None:
        self.active_identity: ActiveSnapshotIdentity | None = ActiveSnapshotIdentity(
            "snapshot-v0", "previous-digest"
        )
        self.existing_digest = existing_digest
        self.fail = fail
        self.publish_calls = 0

    def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None:
        return self.active_identity

    def snapshot_digest(self, snapshot_version: str) -> str | None:
        return self.existing_digest

    def publish_snapshot(
        self,
        documents: list[SourceDocument],
        *,
        snapshot_version: str,
        universe_id: str,
        universe_version: str,
        snapshot_digest: str,
        expected_prior: ActiveSnapshotIdentity | None = None,
    ) -> int:
        self.publish_calls += 1
        if self.fail:
            raise RuntimeError("graph transaction failed")
        assert universe_id == "test-universe"
        assert universe_version == "1.0.0"
        assert snapshot_digest
        self.active_identity = ActiveSnapshotIdentity(snapshot_version, snapshot_digest)
        return len(documents)


def test_snapshot_publication_stages_then_activates_one_version() -> None:
    chroma = FakeChromaStore()
    graph = FakeSnapshotGraphStore()

    report = publish_research_snapshot(research_snapshot(), chroma, graph)

    assert report.previous_snapshot_version == "snapshot-v0"
    assert report.snapshot_version == "snapshot-v1"
    assert report.chroma_count == report.neo4j_count == 1
    assert graph.active_identity == ActiveSnapshotIdentity("snapshot-v1", report.snapshot_digest)
    assert chroma.documents[0].metadata["snapshot_version"] == "snapshot-v1"


def test_chroma_readback_failure_leaves_previous_graph_snapshot_active() -> None:
    graph = FakeSnapshotGraphStore()

    try:
        publish_research_snapshot(research_snapshot(), FakeChromaStore(missing=True), graph)
    except IndexConsistencyError:
        pass
    else:
        raise AssertionError("Expected snapshot readback failure")

    assert graph.publish_calls == 0
    assert graph.active_identity == ActiveSnapshotIdentity("snapshot-v0", "previous-digest")


def test_graph_failure_leaves_previous_snapshot_active() -> None:
    graph = FakeSnapshotGraphStore(fail=True)

    try:
        publish_research_snapshot(research_snapshot(), FakeChromaStore(), graph)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected graph publication failure")

    assert graph.active_identity == ActiveSnapshotIdentity("snapshot-v0", "previous-digest")


def test_chroma_digest_mismatch_leaves_previous_graph_snapshot_active() -> None:
    graph = FakeSnapshotGraphStore()

    try:
        publish_research_snapshot(
            research_snapshot(), FakeChromaStore(corrupt_metadata=True), graph
        )
    except IndexConsistencyError:
        pass
    else:
        raise AssertionError("Expected staged metadata verification failure")

    assert graph.publish_calls == 0
    assert graph.active_identity == ActiveSnapshotIdentity("snapshot-v0", "previous-digest")


def test_complete_chroma_content_is_rechecked_before_graph_mutation() -> None:
    class MutatedReadback(FakeChromaStore):
        def document_records(self, document_ids: list[str]) -> dict[str, RetrievedSource]:
            records = super().document_records(document_ids)
            first = records[document_ids[0]]
            records[document_ids[0]] = first.model_copy(
                update={"content": first.content + " forged"}
            )
            return records

    graph = FakeSnapshotGraphStore()
    with pytest.raises(IndexConsistencyError):
        publish_research_snapshot(research_snapshot(), MutatedReadback(), graph)
    assert graph.publish_calls == 0
    assert graph.active_identity == ActiveSnapshotIdentity("snapshot-v0", "previous-digest")


@pytest.mark.parametrize("existing", [False, True])
def test_api_new_and_inactive_snapshot_require_fresh_fields_before_staging(existing: bool) -> None:
    from datetime import timedelta

    snapshot = research_snapshot()
    chroma = FakeChromaStore()
    graph = FakeSnapshotGraphStore(existing_digest=snapshot.content_digest() if existing else None)
    with pytest.raises(MarketDataQualityError):
        _publish_research_snapshot(
            snapshot, chroma, graph, clock=lambda: snapshot.ingested_at + timedelta(days=100)
        )
    assert chroma.upsert_calls == graph.publish_calls == 0


def test_existing_version_with_different_content_is_rejected_before_staging() -> None:
    chroma = FakeChromaStore()
    graph = FakeSnapshotGraphStore(existing_digest="different-digest")

    try:
        publish_research_snapshot(research_snapshot(), chroma, graph)
    except ValueError as exc:
        assert "already exists with different content" in str(exc)
    else:
        raise AssertionError("Expected immutable-version rejection")

    assert chroma.upsert_calls == 0
    assert graph.publish_calls == 0
    assert graph.active_identity == ActiveSnapshotIdentity("snapshot-v0", "previous-digest")


def test_interleaved_same_version_publishers_cannot_cross_activate_chroma_content() -> None:
    first = research_snapshot()
    second = first.model_copy(deep=True)
    second.records[0].name.value = "Competing ETF name"

    class RetainingChromaStore(FakeChromaStore):
        def __init__(self) -> None:
            super().__init__()
            self.retained: dict[str, SourceDocument] = {}
            self.lock = Lock()

        def upsert(self, documents: list[SourceDocument]) -> int:
            with self.lock:
                self.retained.update({document.document_id: document for document in documents})
            return len(documents)

        def missing_document_ids(self, document_ids: list[str]) -> list[str]:
            with self.lock:
                return [item for item in document_ids if item not in self.retained]

        def document_metadatas(
            self, document_ids: list[str]
        ) -> dict[str, dict[str, str | int | float | bool]]:
            with self.lock:
                return {
                    item: self.retained[item].chroma_metadata()
                    for item in document_ids
                    if item in self.retained
                }

        def document_records(self, document_ids: list[str]) -> dict[str, RetrievedSource]:
            with self.lock:
                return {
                    item: RetrievedSource(
                        document_id=item,
                        content=self.retained[item].content,
                        metadata=self.retained[item].chroma_metadata(),
                    )
                    for item in document_ids
                    if item in self.retained
                }

    class InterleavedGraphStore(FakeSnapshotGraphStore):
        def __init__(self) -> None:
            super().__init__()
            self.precheck_barrier = Barrier(2)
            self.lock = Lock()
            self.published_digest: str | None = None

        def snapshot_digest(self, snapshot_version: str) -> str | None:
            self.precheck_barrier.wait(timeout=5)
            return None

        def publish_snapshot(
            self,
            documents: list[SourceDocument],
            *,
            snapshot_version: str,
            universe_id: str,
            universe_version: str,
            snapshot_digest: str,
            expected_prior: ActiveSnapshotIdentity | None = None,
        ) -> int:
            with self.lock:
                if self.published_digest is not None:
                    raise ValueError("snapshot version already owns a different digest")
                self.published_digest = snapshot_digest
                self.active_identity = ActiveSnapshotIdentity(snapshot_version, snapshot_digest)
                return len(documents)

    chroma = RetainingChromaStore()
    graph = InterleavedGraphStore()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(publish_research_snapshot, candidate, chroma, graph)
            for candidate in (first, second)
        ]
    outcomes = []
    for future in futures:
        try:
            outcomes.append(future.result())
        except ValueError:
            outcomes.append(None)

    assert sum(outcome is not None for outcome in outcomes) == 1
    assert len(chroma.retained) == 2
    active = graph.active_snapshot_identity()
    assert active is not None
    reachable = [
        document
        for document in chroma.retained.values()
        if document.metadata["snapshot_version"] == active.snapshot_version
        and document.metadata["snapshot_digest"] == active.snapshot_digest
    ]
    assert len(reachable) == 1


def test_failed_first_publication_stays_hidden_until_exact_snapshot_activation() -> None:
    chromadb = pytest.importorskip("chromadb")
    from chromadb.api.types import EmbeddingFunction

    class DeterministicEmbedding(EmbeddingFunction[list[str]]):
        def __init__(self) -> None:
            pass

        @staticmethod
        def name() -> str:
            return "issue-51-publication-boundary"

        @staticmethod
        def get_config() -> dict[str, Any]:
            return {}

        @staticmethod
        def build_from_config(config: dict[str, Any]) -> "DeterministicEmbedding":
            return DeterministicEmbedding()

        def __call__(self, input: list[str]) -> list[list[float]]:
            return [[float(len(text)), float(sum(map(ord, text)) % 101)] for text in input]

    snapshot = research_snapshot()
    documents = snapshot.to_source_documents()
    identity = ActiveSnapshotIdentity(snapshot.snapshot_version, snapshot.content_digest())
    chroma = ChromaDocumentStore(
        client=chromadb.EphemeralClient(),
        collection_name=f"issue_51_publication_{uuid4().hex}",
        embedding_function=DeterministicEmbedding(),
    )

    with pytest.raises(RuntimeError, match="graph transaction failed"):
        publish_research_snapshot(snapshot, chroma, FakeSnapshotGraphStore(fail=True))

    stored = chroma.document_metadatas([documents[0].document_id])
    assert stored[documents[0].document_id][LEGACY_VISIBILITY_KEY] == BLOCKED_VISIBILITY_VALUE

    class RetrievalGraph:
        def __init__(self, active: ActiveSnapshotIdentity | None) -> None:
            self.active = active
            self.requested_ids: list[str] | None = None

        def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None:
            return self.active

        def find_contexts(self, document_ids: list[str]) -> dict[str, object]:
            self.requested_ids = document_ids
            return {}

    inactive_graph = RetrievalGraph(None)
    assert HybridRetriever(chroma, inactive_graph).search("ETF research", limit=5) == []
    assert inactive_graph.requested_ids == []

    active_graph = RetrievalGraph(identity)
    active_results = HybridRetriever(chroma, active_graph).search("ETF research", limit=5)
    assert [result.document_id for result in active_results] == [documents[0].document_id]
    assert active_results[0].metadata["snapshot_version"] == identity.snapshot_version
    assert active_results[0].metadata["snapshot_digest"] == identity.snapshot_digest
    assert LEGACY_VISIBILITY_KEY not in active_results[0].metadata
    assert active_graph.requested_ids == [documents[0].document_id]
