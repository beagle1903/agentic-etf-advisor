"""Stage and activate one validated cross-store research snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from etf_advisor.clock import Clock, system_utc_now
from etf_advisor.data.quality import assess_observations
from etf_advisor.encoding import document_fingerprint, validate_document
from etf_advisor.encoding import schema_version as validate_schema_version
from etf_advisor.rag.indexing import IndexConsistencyError
from etf_advisor.rag.models import MetadataValue, RetrievedSource, SourceDocument
from etf_advisor.research.models import ETFResearchSnapshot


class SnapshotGraphStore(Protocol):
    """Graph boundary that owns the authoritative active-snapshot pointer."""

    def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None: ...

    def snapshot_digest(self, snapshot_version: str) -> str | None: ...

    def snapshot_manifest(self, snapshot_version: str) -> SnapshotManifest | None: ...

    def verify_snapshot(self, snapshot_version: str) -> None: ...

    def publish_snapshot(
        self,
        documents: list[SourceDocument],
        *,
        snapshot_version: str,
        universe_id: str,
        universe_version: str,
        snapshot_digest: str,
        expected_prior: ActiveSnapshotIdentity | None = None,
    ) -> int: ...


class SnapshotDocumentStore(Protocol):
    """Semantic store operations needed for staged snapshot verification."""

    def upsert(self, documents: list[SourceDocument]) -> int: ...

    def stage_snapshot(self, documents: list[SourceDocument]) -> int: ...

    def document_records(self, document_ids: list[str]) -> dict[str, RetrievedSource]: ...

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


@dataclass(frozen=True)
class SnapshotManifest:
    """Graph-authoritative document manifest for one immutable snapshot."""

    snapshot_version: str
    snapshot_digest: str
    document_count: int
    document_ids: tuple[str, ...]
    schema_version: int = 1
    fingerprints: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_schema_version(self.schema_version)
        if type(self.document_count) is not int or self.document_count < 1:
            raise ValueError("Snapshot manifest requires an exact document count.")
        if len(self.document_ids) != self.document_count or len(self.document_ids) != len(
            set(self.document_ids)
        ):
            raise ValueError("Snapshot manifest has contradictory membership.")
        if self.schema_version == 2 and set(self.fingerprints) != set(self.document_ids):
            raise ValueError("Schema-2 manifest requires complete authoritative fingerprints.")


@dataclass
class _FieldObservation:
    symbol: str
    source: str
    source_url: str
    observed_at: datetime


def verify_snapshot_documents(
    identity: ActiveSnapshotIdentity,
    document_ids: list[str],
    document_store: SnapshotDocumentStore,
    *,
    manifest: SnapshotManifest | None = None,
    expected_documents: list[SourceDocument] | None = None,
) -> int:
    """Verify exact identity metadata for a complete semantic-store manifest."""

    if not document_ids or len(document_ids) != len(set(document_ids)):
        raise IndexConsistencyError("Snapshot document manifest is empty or contains duplicates.")
    if manifest is not None and manifest.fingerprints:
        records = document_store.document_records(document_ids)
        if set(records) != set(document_ids) or set(manifest.fingerprints) != set(document_ids):
            raise IndexConsistencyError("Snapshot fingerprint manifest is incomplete.")
        for document_id, record in records.items():
            if (
                record.metadata.get("snapshot_version") != identity.snapshot_version
                or record.metadata.get("snapshot_digest") != identity.snapshot_digest
            ):
                raise IndexConsistencyError("Snapshot record identity differs.")
            version = validate_document(
                document_id,
                record.content,
                record.metadata,
                expected_fingerprint=manifest.fingerprints[document_id],
            )
            if version != manifest.schema_version:
                raise IndexConsistencyError("Snapshot record schema differs from graph manifest.")
            if (
                document_fingerprint(document_id, record.content, record.metadata)
                != manifest.fingerprints[document_id]
            ):
                raise IndexConsistencyError("Snapshot canonical document fingerprint differs.")
        return len(document_ids)
    if expected_documents is not None:
        records = document_store.document_records(document_ids)
        expected = {document.document_id: document for document in expected_documents}
        if set(records) != set(expected) or set(records) != set(document_ids):
            raise IndexConsistencyError("Snapshot canonical document membership differs.")
        for document_id, record in records.items():
            if (
                record.content != expected[document_id].content
                or record.metadata != expected[document_id].chroma_metadata()
            ):
                raise IndexConsistencyError("Snapshot canonical document readback differs.")
        return len(document_ids)
    missing_document_ids = document_store.missing_document_ids(document_ids)
    if missing_document_ids:
        raise IndexConsistencyError(
            f"Chroma is missing {len(missing_document_ids)} active snapshot document(s)."
        )
    stored_metadata = document_store.document_metadatas(document_ids)
    invalid_document_ids = [
        document_id
        for document_id in document_ids
        if stored_metadata.get(document_id, {}).get("snapshot_version") != identity.snapshot_version
        or stored_metadata.get(document_id, {}).get("snapshot_digest") != identity.snapshot_digest
    ]
    if invalid_document_ids:
        raise IndexConsistencyError(
            f"Chroma identity verification failed for {len(invalid_document_ids)} "
            "snapshot document(s)."
        )
    return len(document_ids)


def publish_research_snapshot(
    snapshot: ETFResearchSnapshot,
    chroma_store: SnapshotDocumentStore,
    neo4j_store: SnapshotGraphStore,
    *,
    clock: Clock = system_utc_now,
    max_age: timedelta = timedelta(hours=120),
    future_tolerance: timedelta = timedelta(minutes=5),
) -> SnapshotPublicationReport:
    """Stage Chroma first, then atomically activate the graph snapshot.

    Content-addressed document IDs keep every staged candidate snapshot intact. Neo4j performs graph
    writes and the active-pointer change in one explicit transaction, so staged Chroma records
    remain unreachable when graph publication fails.
    """

    snapshot = ETFResearchSnapshot.model_validate(snapshot.model_dump(mode="json"))
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
    if previous_identity == ActiveSnapshotIdentity(snapshot.snapshot_version, digest):
        manifest_method = neo4j_store.snapshot_manifest
        manifest = manifest_method(snapshot.snapshot_version)
        if manifest is None or set(manifest.document_ids) != set(document_ids):
            raise IndexConsistencyError("Active retry manifest differs from supplied payload.")
        chroma_count = verify_snapshot_documents(
            previous_identity,
            document_ids,
            chroma_store,
            manifest=manifest,
            expected_documents=documents if not manifest.fingerprints else None,
        )
        verify = neo4j_store.verify_snapshot
        verify(snapshot.snapshot_version)
        if neo4j_store.active_snapshot_identity() != previous_identity:
            raise IndexConsistencyError("Active snapshot changed during verification.")
        return SnapshotPublicationReport(
            snapshot.snapshot_version,
            digest,
            snapshot.snapshot_version,
            chroma_count,
            len(documents),
            True,
        )
    observations = [
        _FieldObservation(
            f"{record.symbol}.{name}", field.provider, field.source_url, field.observed_at
        )
        for record in snapshot.records
        for name, field in record.research_fields().items()
    ]
    assess_observations(
        observations, checked_at=clock(), max_age=max_age, future_tolerance=future_tolerance
    ).require_healthy()
    chroma_count = chroma_store.stage_snapshot(documents)
    if chroma_count != len(documents):
        raise IndexConsistencyError("Chroma did not stage the complete research snapshot.")
    verify_snapshot_documents(
        ActiveSnapshotIdentity(snapshot.snapshot_version, digest),
        document_ids,
        chroma_store,
        expected_documents=documents,
    )
    neo4j_count = neo4j_store.publish_snapshot(
        documents,
        snapshot_version=snapshot.snapshot_version,
        universe_id=snapshot.universe_id,
        universe_version=snapshot.universe_version,
        snapshot_digest=digest,
        expected_prior=previous_identity,
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
