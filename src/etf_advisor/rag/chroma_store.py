"""Chroma HTTP client with a small, testable document-store interface."""

from __future__ import annotations

import importlib
from typing import Any

from etf_advisor.rag.models import RetrievedSource, SourceDocument


class ChromaUnavailable(RuntimeError):
    """Raised when Chroma's optional client dependency is not installed."""


class ChromaDocumentStore:
    """Store and search attributable source documents in a Chroma collection."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "etf_source_documents",
        *,
        client: Any | None = None,
        create_if_missing: bool = True,
    ) -> None:
        if client is None:
            try:
                chromadb = importlib.import_module("chromadb")
            except ImportError as exc:
                raise ChromaUnavailable(
                    "Chroma retrieval requires the optional 'rag' dependencies. "
                    "Run: uv sync --extra rag"
                ) from exc
            client = chromadb.HttpClient(host=host, port=port)
        self._client = client
        try:
            self._collection = (
                client.get_or_create_collection(name=collection_name)
                if create_if_missing
                else client.get_collection(name=collection_name)
            )
        except Exception as exc:
            raise ChromaUnavailable(
                f"Chroma collection '{collection_name}' is unavailable."
            ) from exc

    def upsert(self, documents: list[SourceDocument]) -> int:
        if not documents:
            return 0
        self._collection.upsert(
            ids=[document.document_id for document in documents],
            documents=[document.content for document in documents],
            metadatas=[document.chroma_metadata() for document in documents],
        )
        return len(documents)

    def search(
        self,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedSource]:
        self._validate_search(query, limit)
        return self._query(query, limit=limit, where=where)

    def search_unversioned(self, query: str, limit: int = 5) -> list[RetrievedSource]:
        """Return only legacy documents when no research snapshot is active."""

        self._validate_search(query, limit)
        collection_count = int(self._collection.count())
        if collection_count < 1:
            return []
        candidates = self._query(query, limit=collection_count)
        return [
            candidate
            for candidate in candidates
            if "snapshot_version" not in candidate.metadata
            and "snapshot_digest" not in candidate.metadata
        ][:limit]

    @staticmethod
    def _validate_search(query: str, limit: int) -> None:
        if not query.strip():
            raise ValueError("A non-empty search query is required.")
        if limit < 1:
            raise ValueError("Search limit must be at least 1.")

    def _query(
        self,
        query: str,
        *,
        limit: int,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedSource]:
        kwargs: dict[str, Any] = {"query_texts": [query], "n_results": limit}
        if where:
            kwargs["where"] = where
        result = self._collection.query(**kwargs)
        ids = _first_row(result.get("ids"))
        contents = _first_row(result.get("documents"))
        metadata = _first_row(result.get("metadatas"))
        distances = _first_row(result.get("distances"))
        retrieved: list[RetrievedSource] = []
        for index, document_id in enumerate(ids):
            retrieved.append(
                RetrievedSource(
                    document_id=str(document_id),
                    content=str(contents[index]) if index < len(contents) else "",
                    metadata=dict(metadata[index]) if index < len(metadata) else {},
                    distance=_as_float(distances[index]) if index < len(distances) else None,
                )
            )
        return retrieved

    def missing_document_ids(self, document_ids: list[str]) -> list[str]:
        """Return requested IDs that are absent from the Chroma collection."""

        if not document_ids:
            return []
        result = self._collection.get(ids=document_ids, include=[])
        existing = {str(document_id) for document_id in result.get("ids", [])}
        return [document_id for document_id in document_ids if document_id not in existing]

    def document_metadatas(
        self, document_ids: list[str]
    ) -> dict[str, dict[str, str | int | float | bool]]:
        """Read back scalar metadata for exact staged-snapshot verification."""

        if not document_ids:
            return {}
        result = self._collection.get(ids=document_ids, include=["metadatas"])
        ids = [str(document_id) for document_id in result.get("ids", [])]
        metadatas = list(result.get("metadatas", []))
        return {
            document_id: dict(metadatas[index])
            for index, document_id in enumerate(ids)
            if index < len(metadatas) and metadatas[index] is not None
        }


def _first_row(value: Any) -> list[Any]:
    if not value:
        return []
    first = value[0]
    return list(first) if first else []


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
