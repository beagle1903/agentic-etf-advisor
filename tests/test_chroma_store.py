from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from etf_advisor.rag.chroma_store import (
    BLOCKED_VISIBILITY_VALUE,
    LEGACY_VISIBILITY_KEY,
    LEGACY_VISIBILITY_PREPARING,
    LEGACY_VISIBILITY_SCHEMA_KEY,
    LEGACY_VISIBILITY_SCHEMA_VERSION,
    LEGACY_VISIBILITY_VALUE,
    ChromaDocumentStore,
    ChromaLegacyVisibilityError,
)
from etf_advisor.rag.models import SourceDocument


class FakeCollection:
    def __init__(
        self,
        rows: dict[str, dict[str, Any]] | None = None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.rows = rows or {}
        self.metadata = (
            {LEGACY_VISIBILITY_SCHEMA_KEY: LEGACY_VISIBILITY_SCHEMA_VERSION}
            if metadata is None
            else metadata
        )
        self.query_payload: dict[str, Any] = {}
        self.upsert_payload: dict[str, Any] = {}
        self.update_calls: list[list[str]] = []
        self.query_rows: list[str] | None = None

    def upsert(self, **kwargs: Any) -> None:
        self.upsert_payload = kwargs
        for index, document_id in enumerate(kwargs["ids"]):
            existing = self.rows.get(document_id, {})
            # Deliberately model Chroma metadata replacement. Merge-specific safety is tested
            # by pre-populating snapshot metadata before a legacy upsert.
            self.rows[document_id] = {
                "document": kwargs["documents"][index],
                "metadata": dict(kwargs["metadatas"][index]),
                "distance": existing.get("distance", 0.1),
            }

    def update(self, **kwargs: Any) -> None:
        self.update_calls.append(list(kwargs["ids"]))
        for index, document_id in enumerate(kwargs["ids"]):
            self.rows[document_id]["metadata"] = dict(kwargs["metadatas"][index])

    def modify(self, *, metadata: dict[str, Any]) -> None:
        self.metadata = dict(metadata)

    def count(self) -> int:
        return len(self.rows)

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_payload = kwargs
        ids = self.query_rows if self.query_rows is not None else list(self.rows)
        where = kwargs.get("where")
        if where is not None:
            key, value = next(iter(where.items()))
            ids = [item for item in ids if self.rows[item]["metadata"].get(key) == value]
        ids = ids[: kwargs["n_results"]]
        return {
            "ids": [ids],
            "documents": [[self.rows[item]["document"] for item in ids]],
            "metadatas": [[self.rows[item]["metadata"] for item in ids]],
            "distances": [[self.rows[item].get("distance", 0.1) for item in ids]],
        }

    def get(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("ids") is not None:
            requested = kwargs["ids"]
            if isinstance(requested, str):
                requested = [requested]
            ids = [document_id for document_id in requested if document_id in self.rows]
        else:
            offset = kwargs.get("offset") or 0
            limit = kwargs.get("limit")
            ordered = list(self.rows)
            ids = ordered[offset : offset + limit if limit is not None else None]
        result: dict[str, Any] = {"ids": ids}
        if kwargs.get("include") == ["metadatas"]:
            result["metadatas"] = [self.rows[item]["metadata"] for item in ids]
        return result


class FakeClient:
    def __init__(self, collection: FakeCollection | None = None) -> None:
        self.collection = collection or FakeCollection()
        self.get_calls = 0

    def get_or_create_collection(self, **kwargs: Any) -> FakeCollection:
        assert kwargs["name"] == "test_sources"
        assert kwargs["metadata"] == {
            LEGACY_VISIBILITY_SCHEMA_KEY: LEGACY_VISIBILITY_SCHEMA_VERSION
        }
        return self.collection

    def get_collection(self, **kwargs: Any) -> FakeCollection:
        assert kwargs["name"] == "test_sources"
        self.get_calls += 1
        return self.collection


def source_document(
    document_id: str = "doc-1", *, metadata: dict[str, str] | None = None
) -> SourceDocument:
    return SourceDocument(
        document_id=document_id,
        symbol="SPY",
        title="SPY snapshot",
        content=f"ETF source content {document_id}",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 26, tzinfo=UTC),
        metadata=metadata or {},
    )


def row(metadata: dict[str, Any], *, content: str = "ETF source content") -> dict[str, Any]:
    return {"document": content, "metadata": metadata, "distance": 0.12}


def test_chroma_store_upserts_adapter_marker_and_returns_public_provenance() -> None:
    client = FakeClient()
    store = ChromaDocumentStore(client=client, collection_name="test_sources")

    assert store.upsert([source_document()]) == 1
    assert client.collection.upsert_payload["ids"] == ["doc-1"]
    assert (
        client.collection.upsert_payload["metadatas"][0][LEGACY_VISIBILITY_KEY]
        == LEGACY_VISIBILITY_VALUE
    )

    results = store.search("broad market")

    assert results[0].document_id == "doc-1"
    assert results[0].metadata["source"] == "yahoo_finance"
    assert LEGACY_VISIBILITY_KEY not in results[0].metadata
    assert results[0].distance == 0.1
    assert store.missing_document_ids(["doc-1", "missing-doc"]) == ["missing-doc"]


@pytest.mark.parametrize("snapshot_key", ["snapshot_version", "snapshot_digest"])
def test_chroma_store_classifies_snapshot_key_presence_as_blocked(snapshot_key: str) -> None:
    client = FakeClient()
    store = ChromaDocumentStore(client=client, collection_name="test_sources")

    store.upsert([source_document(metadata={snapshot_key: ""})])

    assert (
        client.collection.upsert_payload["metadatas"][0][LEGACY_VISIBILITY_KEY]
        == BLOCKED_VISIBILITY_VALUE
    )


def test_chroma_store_rejects_reserved_caller_marker_before_writing() -> None:
    store = ChromaDocumentStore(client=FakeClient(), collection_name="test_sources")

    with pytest.raises(ValueError, match="reserved"):
        store.upsert([source_document(metadata={LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE})])


def test_chroma_store_rejects_legacy_overwrite_of_existing_snapshot_metadata() -> None:
    collection = FakeCollection(
        {"doc-1": row({"snapshot_version": "snapshot-v1", "symbol": "SPY"})}
    )
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    with pytest.raises(ChromaLegacyVisibilityError, match="existing Chroma metadata"):
        store.upsert([source_document()])

    assert collection.upsert_payload == {}


@pytest.mark.parametrize(
    "fault",
    ["missing", "nonmapping", "duplicate", "unexpected"],
)
def test_legacy_upsert_rejects_malformed_existing_metadata_readback(fault: str) -> None:
    class MalformedReadbackCollection(FakeCollection):
        def get(self, **kwargs: Any) -> dict[str, Any]:
            if kwargs.get("include") == []:
                if fault == "unexpected":
                    return {"ids": ["other"]}
                return {"ids": ["doc-1"]}
            if fault == "missing":
                return {"ids": [], "metadatas": []}
            if fault == "nonmapping":
                return {"ids": ["doc-1"], "metadatas": [None]}
            if fault == "duplicate":
                return {
                    "ids": ["doc-1", "doc-1"],
                    "metadatas": [{"symbol": "SPY"}, {"symbol": "SPY"}],
                }
            raise AssertionError("unexpected metadata readback after unexpected ID")

    collection = MalformedReadbackCollection({"doc-1": row({"symbol": "SPY"})})
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    with pytest.raises(ChromaLegacyVisibilityError, match="Chroma"):
        store.upsert([source_document()])

    assert collection.upsert_payload == {}


def test_unversioned_search_is_k_bounded_and_uses_exact_legacy_filter() -> None:
    collection = FakeCollection(
        {
            "legacy-1": row({LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE, "symbol": "SPY"}),
            "staged": row(
                {
                    LEGACY_VISIBILITY_KEY: BLOCKED_VISIBILITY_VALUE,
                    "snapshot_version": "v1",
                }
            ),
            "legacy-2": row({LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE, "symbol": "QQQ"}),
        }
    )
    # The collection count is intentionally huge: it must never become n_results.
    collection.count = lambda: 50_000  # type: ignore[method-assign]
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    results = store.search_unversioned("broad market", limit=2)

    assert [result.document_id for result in results] == ["legacy-1", "legacy-2"]
    assert collection.query_payload["n_results"] == 2
    assert collection.query_payload["where"] == {LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE}
    assert all(LEGACY_VISIBILITY_KEY not in result.metadata for result in results)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "ids": [["doc-1"]],
                "documents": [[]],
                "metadatas": [[{LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE}]],
                "distances": [[0.1]],
            },
            "contradictory lengths",
        ),
        (
            {
                "ids": [["doc-1", "doc-1"]],
                "documents": [["one", "one"]],
                "metadatas": [
                    [
                        {LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE},
                        {LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE},
                    ]
                ],
                "distances": [[0.1, 0.1]],
            },
            "duplicate",
        ),
        (
            {
                "ids": [["doc-1", "doc-2"]],
                "documents": [["one", "two"]],
                "metadatas": [
                    [
                        {LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE},
                        {LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE},
                    ]
                ],
                "distances": [[0.1, 0.2]],
            },
            "requested limit",
        ),
    ],
)
def test_query_rejects_truncated_duplicate_or_oversized_single_row_response(
    payload: dict[str, Any], message: str
) -> None:
    collection = FakeCollection()
    collection.query = lambda **kwargs: payload  # type: ignore[method-assign]
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    with pytest.raises(ChromaLegacyVisibilityError, match=message):
        store.search_unversioned("broad market", limit=1)


def test_prepared_staged_only_collection_returns_no_legacy_results() -> None:
    collection = FakeCollection(
        {
            "staged": row(
                {
                    LEGACY_VISIBILITY_KEY: BLOCKED_VISIBILITY_VALUE,
                    "snapshot_digest": "digest-v1",
                }
            )
        }
    )
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    assert store.search_unversioned("broad market") == []


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({}, "not prepared"),
        ({LEGACY_VISIBILITY_SCHEMA_KEY: "1"}, "not prepared"),
        ({LEGACY_VISIBILITY_SCHEMA_KEY: True}, "not prepared"),
        ({LEGACY_VISIBILITY_SCHEMA_KEY: LEGACY_VISIBILITY_PREPARING}, "in progress"),
    ],
)
def test_unversioned_search_fails_closed_on_unready_collection(
    metadata: dict[str, Any], message: str
) -> None:
    collection = FakeCollection({}, metadata=metadata)
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    with pytest.raises(ChromaLegacyVisibilityError, match=message):
        store.search_unversioned("broad market")


def test_unversioned_search_reads_readiness_fresh_each_time() -> None:
    ready = FakeCollection({"legacy": row({LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE})})
    client = FakeClient(ready)
    store = ChromaDocumentStore(client=client, collection_name="test_sources")
    client.collection = FakeCollection(ready.rows, metadata={})

    with pytest.raises(ChromaLegacyVisibilityError, match="not prepared"):
        store.search_unversioned("broad market")

    assert client.get_calls == 1


@pytest.mark.parametrize(
    "forged_metadata",
    [
        {LEGACY_VISIBILITY_KEY: BLOCKED_VISIBILITY_VALUE},
        {
            LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE,
            "snapshot_version": "snapshot-v1",
        },
    ],
)
def test_unversioned_search_rejects_contradictory_returned_rows(
    forged_metadata: dict[str, Any],
) -> None:
    collection = FakeCollection({"forged": row(forged_metadata)})
    collection.query_rows = ["forged"]
    # Simulate a backend returning a row that does not satisfy the equality predicate.
    original_query = collection.query

    def query_without_filter(**kwargs: Any) -> dict[str, Any]:
        kwargs.pop("where", None)
        return original_query(**kwargs)

    collection.query = query_without_filter  # type: ignore[method-assign]
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    with pytest.raises(ChromaLegacyVisibilityError, match="Chroma returned"):
        store.search_unversioned("broad market")


def test_preparation_preview_and_apply_classify_mixed_collection_in_bounded_pages() -> None:
    collection = FakeCollection(
        {
            "legacy": row({"symbol": "SPY"}),
            "staged": row({"symbol": "QQQ", "snapshot_version": "v1", "snapshot_digest": "d1"}),
            "version-only": row({"symbol": "VTI", "snapshot_version": "v2"}),
            "digest-only": row({"symbol": "BND", "snapshot_digest": "d2"}),
            "forged": row({"symbol": "DIA", LEGACY_VISIBILITY_KEY: BLOCKED_VISIBILITY_VALUE}),
        },
        metadata={},
    )
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    preview = store.prepare_legacy_visibility(page_size=2)

    assert (preview.total_documents, preview.legacy_documents, preview.blocked_documents) == (
        5,
        2,
        3,
    )
    assert preview.pages == 3
    assert preview.applied is False
    assert preview.ready is False
    assert collection.update_calls == []
    assert collection.metadata == {}

    applied = store.prepare_legacy_visibility(apply=True, page_size=2)

    assert applied.applied is True
    assert applied.ready is True
    assert collection.update_calls == [
        ["legacy", "staged"],
        ["version-only", "digest-only"],
        ["forged"],
    ]
    assert collection.rows["legacy"]["metadata"][LEGACY_VISIBILITY_KEY] == LEGACY_VISIBILITY_VALUE
    assert collection.rows["forged"]["metadata"][LEGACY_VISIBILITY_KEY] == LEGACY_VISIBILITY_VALUE
    assert collection.rows["staged"]["metadata"][LEGACY_VISIBILITY_KEY] == BLOCKED_VISIBILITY_VALUE
    assert collection.metadata[LEGACY_VISIBILITY_SCHEMA_KEY] == LEGACY_VISIBILITY_SCHEMA_VERSION


def test_empty_collection_can_be_prepared_and_rerun() -> None:
    collection = FakeCollection({}, metadata={})
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    first = store.prepare_legacy_visibility(apply=True, page_size=2)
    second = store.prepare_legacy_visibility(apply=True, page_size=2)

    assert first.total_documents == second.total_documents == 0
    assert first.pages == second.pages == 0
    assert collection.metadata[LEGACY_VISIBILITY_SCHEMA_KEY] == LEGACY_VISIBILITY_SCHEMA_VERSION
    assert store.search_unversioned("broad market") == []


def test_failed_preparation_readback_stays_unready() -> None:
    class BrokenReadbackCollection(FakeCollection):
        broken = True

        def update(self, **kwargs: Any) -> None:
            if self.broken:
                self.update_calls.append(list(kwargs["ids"]))
            else:
                super().update(**kwargs)

    collection = BrokenReadbackCollection({"legacy": row({"symbol": "SPY"})})
    store = ChromaDocumentStore(client=FakeClient(collection), collection_name="test_sources")

    with pytest.raises(ChromaLegacyVisibilityError, match="did not retain"):
        store.prepare_legacy_visibility(apply=True, page_size=1)

    assert collection.metadata[LEGACY_VISIBILITY_SCHEMA_KEY] == LEGACY_VISIBILITY_PREPARING
    with pytest.raises(ChromaLegacyVisibilityError, match="in progress"):
        store.search_unversioned("broad market")

    collection.broken = False
    report = store.prepare_legacy_visibility(apply=True, page_size=1)
    assert report.ready is True
    assert collection.metadata[LEGACY_VISIBILITY_SCHEMA_KEY] == LEGACY_VISIBILITY_SCHEMA_VERSION


def test_chroma_store_can_open_existing_collection_without_creating_it() -> None:
    class ExistingOnlyClient(FakeClient):
        def get_or_create_collection(self, **kwargs: Any) -> FakeCollection:
            raise AssertionError("verification must not create a collection")

    store = ChromaDocumentStore(
        client=ExistingOnlyClient(),
        collection_name="test_sources",
        create_if_missing=False,
    )

    assert store.search("broad market") == []


def test_embedded_chroma_equality_filter_and_metadata_updates_match_contract() -> None:
    chromadb = pytest.importorskip("chromadb")
    from chromadb.api.types import EmbeddingFunction

    class DeterministicEmbedding(EmbeddingFunction[list[str]]):
        def __init__(self) -> None:
            pass

        @staticmethod
        def name() -> str:
            return "issue-51-deterministic"

        @staticmethod
        def get_config() -> dict[str, Any]:
            return {}

        @staticmethod
        def build_from_config(config: dict[str, Any]) -> DeterministicEmbedding:
            return DeterministicEmbedding()

        def __call__(self, input: list[str]) -> list[list[float]]:
            return [[float(len(text)), float(sum(map(ord, text)) % 101)] for text in input]

    client = chromadb.EphemeralClient()
    collection_name = f"issue_51_{uuid4().hex}"
    store = ChromaDocumentStore(
        client=client,
        collection_name=collection_name,
        embedding_function=DeterministicEmbedding(),
    )
    store.upsert(
        [
            source_document("legacy"),
            source_document("staged", metadata={"snapshot_version": "v1", "snapshot_digest": "d1"}),
        ]
    )

    results = store.search_unversioned("ETF source", limit=2)

    assert [result.document_id for result in results] == ["legacy"]
    assert LEGACY_VISIBILITY_KEY not in results[0].metadata
    store.prepare_legacy_visibility(apply=True, page_size=1)
    metadata = store.document_metadatas(["legacy", "staged"])
    assert metadata["legacy"][LEGACY_VISIBILITY_KEY] == LEGACY_VISIBILITY_VALUE
    assert metadata["staged"][LEGACY_VISIBILITY_KEY] == BLOCKED_VISIBILITY_VALUE
