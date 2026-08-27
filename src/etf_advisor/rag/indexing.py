"""Coordinate idempotent source indexing and verify each explicit store write."""

from dataclasses import dataclass
from typing import Protocol

from etf_advisor.rag.models import SourceDocument


class WritableDocumentStore(Protocol):
    def upsert(self, documents: list[SourceDocument]) -> int: ...

    def missing_document_ids(self, document_ids: list[str]) -> list[str]: ...


class IndexConsistencyError(RuntimeError):
    """Raised when a store cannot read back an expected stable source ID."""


@dataclass(frozen=True)
class IndexReport:
    chroma_count: int
    neo4j_count: int


def index_documents(
    documents: list[SourceDocument],
    chroma_store: WritableDocumentStore,
    neo4j_store: WritableDocumentStore | None = None,
) -> IndexReport:
    """Upsert one document bundle and verify every requested ID after each write."""

    document_ids = [document.document_id for document in documents]
    chroma_count = chroma_store.upsert(documents)
    missing_from_chroma = chroma_store.missing_document_ids(document_ids)
    if missing_from_chroma:
        raise IndexConsistencyError(
            f"Chroma did not retain {len(missing_from_chroma)} source document(s)."
        )

    neo4j_count = 0
    if neo4j_store is not None:
        neo4j_count = neo4j_store.upsert(documents)
        missing_from_neo4j = neo4j_store.missing_document_ids(document_ids)
        if missing_from_neo4j:
            raise IndexConsistencyError(
                f"Neo4j did not retain {len(missing_from_neo4j)} source document(s)."
            )

    return IndexReport(chroma_count=chroma_count, neo4j_count=neo4j_count)
