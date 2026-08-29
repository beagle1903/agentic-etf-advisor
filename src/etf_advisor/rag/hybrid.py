"""Join semantic candidates to source-linked Neo4j neighborhoods."""

from typing import Any, Protocol

from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, RetrievedSource


class SemanticStore(Protocol):
    def search(
        self,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedSource]: ...


class RelationshipStore(Protocol):
    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]: ...

    def active_snapshot_version(self) -> str | None: ...


class HybridRetriever:
    """Enrich Chroma-ranked results without changing their semantic ordering."""

    def __init__(
        self, semantic_store: SemanticStore, relationship_store: RelationshipStore
    ) -> None:
        self._semantic_store = semantic_store
        self._relationship_store = relationship_store

    def search(self, query: str, limit: int = 5) -> list[GraphEnrichedSource]:
        snapshot_version = self._relationship_store.active_snapshot_version()
        where = {"snapshot_version": snapshot_version} if snapshot_version is not None else None
        semantic_results = self._semantic_store.search(query, limit=limit, where=where)
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
