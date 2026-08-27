from datetime import UTC, datetime

import pytest

from etf_advisor.rag.indexing import IndexConsistencyError, index_documents
from etf_advisor.rag.models import SourceDocument


def source_document() -> SourceDocument:
    return SourceDocument(
        document_id="doc-spy",
        symbol="SPY",
        title="SPY snapshot",
        content="Source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


class FakeStore:
    def __init__(self, missing: list[str] | None = None) -> None:
        self.missing = missing or []
        self.upsert_count = 0

    def upsert(self, documents: list[SourceDocument]) -> int:
        self.upsert_count += 1
        return len(documents)

    def missing_document_ids(self, document_ids: list[str]) -> list[str]:
        return [document_id for document_id in document_ids if document_id in self.missing]


def test_dual_store_index_verifies_both_writes() -> None:
    chroma = FakeStore()
    neo4j = FakeStore()

    report = index_documents([source_document()], chroma, neo4j)

    assert report.chroma_count == 1
    assert report.neo4j_count == 1
    assert chroma.upsert_count == 1
    assert neo4j.upsert_count == 1


def test_index_fails_before_graph_write_when_chroma_readback_is_missing() -> None:
    chroma = FakeStore(missing=["doc-spy"])
    neo4j = FakeStore()

    with pytest.raises(IndexConsistencyError, match="Chroma did not retain"):
        index_documents([source_document()], chroma, neo4j)

    assert neo4j.upsert_count == 0


def test_index_fails_when_graph_readback_is_missing() -> None:
    with pytest.raises(IndexConsistencyError, match="Neo4j did not retain"):
        index_documents([source_document()], FakeStore(), FakeStore(missing=["doc-spy"]))
