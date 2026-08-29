from datetime import UTC, datetime
from typing import Any

from etf_advisor.rag.chroma_store import ChromaDocumentStore
from etf_advisor.rag.models import SourceDocument


class FakeCollection:
    def __init__(self) -> None:
        self.upsert_payload: dict[str, Any] = {}

    def upsert(self, **kwargs: Any) -> None:
        self.upsert_payload = kwargs

    def count(self) -> int:
        return 1

    def query(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["query_texts"] == ["broad market"]
        return {
            "ids": [["doc-1"]],
            "documents": [["ETF source content"]],
            "metadatas": [[{"symbol": "SPY", "source": "yahoo_finance"}]],
            "distances": [[0.12]],
        }

    def get(self, **kwargs: Any) -> dict[str, Any]:
        ids = [document_id for document_id in kwargs["ids"] if document_id == "doc-1"]
        if kwargs["include"] == ["metadatas"]:
            return {
                "ids": ids,
                "metadatas": [
                    {"snapshot_version": "snapshot-v1", "snapshot_digest": "abc123"} for _ in ids
                ],
            }
        assert kwargs["include"] == []
        return {"ids": ids}


class FakeClient:
    def __init__(self) -> None:
        self.collection = FakeCollection()

    def get_or_create_collection(self, name: str) -> FakeCollection:
        assert name == "test_sources"
        return self.collection

    def get_collection(self, name: str) -> FakeCollection:
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
    assert store.missing_document_ids(["doc-1", "missing-doc"]) == ["missing-doc"]
    assert store.document_metadatas(["doc-1", "missing-doc"]) == {
        "doc-1": {"snapshot_version": "snapshot-v1", "snapshot_digest": "abc123"}
    }


def test_chroma_store_unversioned_search_excludes_inactive_snapshot_documents() -> None:
    class MixedCollection(FakeCollection):
        def count(self) -> int:
            return 3

        def query(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs["n_results"] == 3
            return {
                "ids": [["staged", "legacy-1", "legacy-2"]],
                "documents": [["staged", "legacy one", "legacy two"]],
                "metadatas": [
                    [
                        {
                            "symbol": "SPY",
                            "snapshot_version": "snapshot-v1",
                            "snapshot_digest": "digest-v1",
                        },
                        {"symbol": "QQQ"},
                        {"symbol": "VTI"},
                    ]
                ],
                "distances": [[0.01, 0.02, 0.03]],
            }

    client = FakeClient()
    client.collection = MixedCollection()
    store = ChromaDocumentStore(client=client, collection_name="test_sources")

    results = store.search_unversioned("broad market", limit=2)

    assert [result.document_id for result in results] == ["legacy-1", "legacy-2"]


def test_chroma_store_can_open_existing_collection_without_creating_it() -> None:
    class ExistingOnlyClient(FakeClient):
        def get_or_create_collection(self, name: str) -> FakeCollection:
            raise AssertionError("verification must not create a collection")

    store = ChromaDocumentStore(
        client=ExistingOnlyClient(),
        collection_name="test_sources",
        create_if_missing=False,
    )

    assert store.search("broad market")[0].document_id == "doc-1"
