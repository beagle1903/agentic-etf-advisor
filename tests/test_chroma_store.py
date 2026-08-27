from datetime import UTC, datetime
from typing import Any

from etf_advisor.rag.chroma_store import ChromaDocumentStore
from etf_advisor.rag.models import SourceDocument


class FakeCollection:
    def __init__(self) -> None:
        self.upsert_payload: dict[str, Any] = {}

    def upsert(self, **kwargs: Any) -> None:
        self.upsert_payload = kwargs

    def query(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["query_texts"] == ["broad market"]
        return {
            "ids": [["doc-1"]],
            "documents": [["ETF source content"]],
            "metadatas": [[{"symbol": "SPY", "source": "yahoo_finance"}]],
            "distances": [[0.12]],
        }


class FakeClient:
    def __init__(self) -> None:
        self.collection = FakeCollection()

    def get_or_create_collection(self, name: str) -> FakeCollection:
        assert name == "test_sources"
        return self.collection


def test_chroma_store_upserts_and_returns_provenance() -> None:
    client = FakeClient()
    store = ChromaDocumentStore(client=client, collection_name="test_sources")
    document = SourceDocument(
        document_id="doc-1",
        symbol="SPY",
        title="SPY snapshot",
        content="ETF source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert store.upsert([document]) == 1
    assert client.collection.upsert_payload["ids"] == ["doc-1"]

    results = store.search("broad market")

    assert results[0].document_id == "doc-1"
    assert results[0].metadata["source"] == "yahoo_finance"
    assert results[0].distance == 0.12
