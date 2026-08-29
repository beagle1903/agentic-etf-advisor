from test_research_snapshot import research_snapshot

from etf_advisor.rag.indexing import IndexConsistencyError
from etf_advisor.rag.models import SourceDocument
from etf_advisor.rag.snapshots import publish_research_snapshot


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
        self.active_version: str | None = "snapshot-v0"
        self.existing_digest = existing_digest
        self.fail = fail
        self.publish_calls = 0

    def active_snapshot_version(self) -> str | None:
        return self.active_version

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
        self.active_version = snapshot_version
        return len(documents)


def test_snapshot_publication_stages_then_activates_one_version() -> None:
    chroma = FakeChromaStore()
    graph = FakeSnapshotGraphStore()

    report = publish_research_snapshot(research_snapshot(), chroma, graph)

    assert report.previous_snapshot_version == "snapshot-v0"
    assert report.snapshot_version == "snapshot-v1"
    assert report.chroma_count == report.neo4j_count == 1
    assert graph.active_version == "snapshot-v1"
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
    assert graph.active_version == "snapshot-v0"


def test_graph_failure_leaves_previous_snapshot_active() -> None:
    graph = FakeSnapshotGraphStore(fail=True)

    try:
        publish_research_snapshot(research_snapshot(), FakeChromaStore(), graph)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected graph publication failure")

    assert graph.active_version == "snapshot-v0"


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
    assert graph.active_version == "snapshot-v0"


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
    assert graph.active_version == "snapshot-v0"
