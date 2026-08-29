"""Join semantic candidates to source-linked Neo4j neighborhoods."""

from typing import Any, Protocol

from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, RetrievedSource
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
        contexts = self._relationship_store.find_contexts(
            [result.document_id for result in semantic_results]
        )
        return [
            GraphEnrichedSource(
                **result.model_dump(),
                graph_context=contexts.get(result.document_id),
            )
            for result in semantic_results
        ]
