from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

from test_research_snapshot import research_snapshot

from etf_advisor.rag.indexing import IndexConsistencyError
from etf_advisor.rag.models import SourceDocument
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity, publish_research_snapshot


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

    def missing_document_ids(self, document_ids: list[str]) -> list[str]:
        return document_ids if self.missing else []

    def document_metadatas(
        self, document_ids: list[str]
    ) -> dict[str, dict[str, str | int | float | bool]]:
        metadata = {document.document_id: document.chroma_metadata() for document in self.documents}
        if self.corrupt_metadata:
            metadata[document_ids[0]]["snapshot_digest"] = "wrong-digest"
        return metadata


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
