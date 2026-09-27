"""Join semantic candidates to source-linked Neo4j neighborhoods."""

from typing import Any, Protocol

from etf_advisor.encoding import ResearchIntegrityError, document_fingerprint, validate_document
from etf_advisor.rag.models import (
    GraphContext,
    GraphEnrichedSource,
    RetrievedSource,
)
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity


class SemanticStore(Protocol):
    def search(
        self,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedSource]: ...

    def search_unversioned(
        self,
        query: str,
        limit: int = 5,
    ) -> list[RetrievedSource]: ...


class RelationshipStore(Protocol):
    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]: ...

    def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None: ...


class HybridRetriever:
    """Enrich Chroma-ranked results without changing their semantic ordering."""

    def __init__(
        self, semantic_store: SemanticStore, relationship_store: RelationshipStore
    ) -> None:
        self._semantic_store = semantic_store
        self._relationship_store = relationship_store

    def search(self, query: str, limit: int = 5) -> list[GraphEnrichedSource]:
        active_snapshot = self._relationship_store.active_snapshot_identity()
        if active_snapshot is None:
            semantic_results = self._semantic_store.search_unversioned(query, limit=limit)
        else:
            semantic_results = self._semantic_store.search(
                query,
                limit=limit,
                where={
                    "$and": [
                        {"snapshot_version": active_snapshot.snapshot_version},
                        {"snapshot_digest": active_snapshot.snapshot_digest},
                    ]
                },
            )
            schema2 = any(
                result.metadata.get("field_provenance_schema_version") == 2
                for result in semantic_results
            )
            manifest_method = getattr(self._relationship_store, "snapshot_manifest", None)
            if schema2 or manifest_method is not None:
                if manifest_method is None:
                    raise ResearchIntegrityError("manifest_integrity")
                manifest = manifest_method(active_snapshot.snapshot_version)
                if manifest is None or manifest.snapshot_digest != active_snapshot.snapshot_digest:
                    raise ResearchIntegrityError("manifest_integrity")
                fingerprints = manifest.fingerprints
                if manifest.schema_version == 1 and not fingerprints:
                    document_loader = getattr(self._relationship_store, "snapshot_documents", None)
                    if document_loader is None:
                        raise ResearchIntegrityError("document_integrity")
                    documents = document_loader(active_snapshot.snapshot_version)
                    fingerprints = {
                        document.document_id: document_fingerprint(
                            document.document_id, document.content, document.chroma_metadata()
                        )
                        for document in documents
                    }
                for result in semantic_results:
                    if result.document_id not in fingerprints:
                        raise ResearchIntegrityError("manifest_integrity")
                    if (
                        validate_document(
                            result.document_id,
                            result.content,
                            result.metadata,
                            expected_fingerprint=fingerprints[result.document_id],
                        )
                        != manifest.schema_version
                    ):
                        raise ResearchIntegrityError("schema_encoding")
                    if (
                        document_fingerprint(result.document_id, result.content, result.metadata)
                        != fingerprints[result.document_id]
                    ):
                        raise ResearchIntegrityError("document_integrity")
            if self._relationship_store.active_snapshot_identity() != active_snapshot:
                raise ResearchIntegrityError("projection_integrity")
        contexts = self._relationship_store.find_contexts(
            [result.document_id for result in semantic_results]
        )
        if self._relationship_store.active_snapshot_identity() != active_snapshot:
            raise ResearchIntegrityError("projection_integrity")
        return [
            GraphEnrichedSource(
                **result.model_dump(),
                graph_context=contexts.get(result.document_id),
            )
            for result in semantic_results
        ]
