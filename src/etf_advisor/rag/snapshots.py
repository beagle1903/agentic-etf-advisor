"""Stage and activate one validated cross-store research snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from etf_advisor.rag.indexing import IndexConsistencyError
from etf_advisor.rag.models import MetadataValue, SourceDocument
from etf_advisor.research.models import ETFResearchSnapshot


class SnapshotGraphStore(Protocol):
    """Graph boundary that owns the authoritative active-snapshot pointer."""

    def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None: ...

    def snapshot_digest(self, snapshot_version: str) -> str | None: ...

    def publish_snapshot(
        self,
        documents: list[SourceDocument],
        *,
        snapshot_version: str,
        universe_id: str,
        universe_version: str,
        snapshot_digest: str,
    ) -> int: ...


class SnapshotDocumentStore(Protocol):
    """Semantic store operations needed for staged snapshot verification."""

    def upsert(self, documents: list[SourceDocument]) -> int: ...

    def missing_document_ids(self, document_ids: list[str]) -> list[str]: ...

    def document_metadatas(
        self, document_ids: list[str]
    ) -> dict[str, dict[str, MetadataValue]]: ...


@dataclass(frozen=True)
class SnapshotPublicationReport:
    snapshot_version: str
    snapshot_digest: str
    previous_snapshot_version: str | None
    chroma_count: int
    neo4j_count: int
    already_active: bool = False


@dataclass(frozen=True)
class ActiveSnapshotIdentity:
    """Graph-authoritative identity used to scope cross-store retrieval."""

    snapshot_version: str
    snapshot_digest: str


def publish_research_snapshot(
    snapshot: ETFResearchSnapshot,
    chroma_store: SnapshotDocumentStore,
    neo4j_store: SnapshotGraphStore,
) -> SnapshotPublicationReport:
    """Stage Chroma first, then atomically activate the graph snapshot.

    Content-addressed document IDs keep every staged candidate snapshot intact. Neo4j performs graph
    writes and the active-pointer change in one query transaction, so staged Chroma records
    remain unreachable when graph publication fails.
    """

    documents = snapshot.to_source_documents()
    document_ids = [document.document_id for document in documents]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("Research snapshot document IDs must be unique.")

    digest = snapshot.content_digest()
    previous_identity = neo4j_store.active_snapshot_identity()
    existing_digest = neo4j_store.snapshot_digest(snapshot.snapshot_version)
    if existing_digest is not None and existing_digest != digest:
        raise ValueError(
            "The requested snapshot version already exists with different content. "
            "Use a new snapshot version."
        )
    chroma_count = chroma_store.upsert(documents)
    if chroma_count != len(documents):
        raise IndexConsistencyError("Chroma did not stage the complete research snapshot.")
    missing_from_chroma = chroma_store.missing_document_ids(document_ids)
    if missing_from_chroma:
        raise IndexConsistencyError(
            f"Chroma did not retain {len(missing_from_chroma)} staged snapshot document(s)."
        )

    staged_metadata = chroma_store.document_metadatas(document_ids)
    invalid_staged_ids = [
        document_id
        for document_id in document_ids
        if staged_metadata.get(document_id, {}).get("snapshot_version") != snapshot.snapshot_version
        or staged_metadata.get(document_id, {}).get("snapshot_digest") != digest
    ]
    if invalid_staged_ids:
        raise IndexConsistencyError(
            f"Chroma metadata verification failed for {len(invalid_staged_ids)} "
            "staged snapshot document(s)."
        )
    neo4j_count = neo4j_store.publish_snapshot(
        documents,
        snapshot_version=snapshot.snapshot_version,
        universe_id=snapshot.universe_id,
        universe_version=snapshot.universe_version,
        snapshot_digest=digest,
    )
    if neo4j_count != len(documents):
        raise IndexConsistencyError("Neo4j did not publish the complete research snapshot.")
    if neo4j_store.active_snapshot_identity() != ActiveSnapshotIdentity(
        snapshot_version=snapshot.snapshot_version,
        snapshot_digest=digest,
    ):
        raise IndexConsistencyError("Neo4j did not activate the validated research snapshot.")

    return SnapshotPublicationReport(
        snapshot_version=snapshot.snapshot_version,
        snapshot_digest=digest,
        previous_snapshot_version=(
            previous_identity.snapshot_version if previous_identity is not None else None
        ),
        chroma_count=chroma_count,
        neo4j_count=neo4j_count,
    )
