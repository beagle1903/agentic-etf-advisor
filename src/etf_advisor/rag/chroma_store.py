"""Chroma HTTP client with a small, testable document-store interface."""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from etf_advisor.encoding import validate_document
from etf_advisor.rag.models import MetadataValue, RetrievedSource, SourceDocument

LEGACY_VISIBILITY_KEY = "etf_advisor_legacy_visibility"
LEGACY_VISIBILITY_VALUE = "legacy-v1"
BLOCKED_VISIBILITY_VALUE = "blocked-v1"
LEGACY_VISIBILITY_SCHEMA_KEY = "etf_advisor_legacy_visibility_schema"
LEGACY_VISIBILITY_SCHEMA_VERSION = 1
LEGACY_VISIBILITY_PREPARING = 0
SNAPSHOT_IDENTITY_KEYS = ("snapshot_version", "snapshot_digest")


class ChromaUnavailable(RuntimeError):
    """Raised when Chroma's optional client dependency is not installed."""


class ChromaLegacyVisibilityError(RuntimeError):
    """Raised when legacy visibility cannot be proved safe."""


@dataclass(frozen=True)
class LegacyVisibilityPreparationReport:
    """Bounded preparation result containing counts but no source content."""

    collection_name: str
    total_documents: int
    legacy_documents: int
    blocked_documents: int
    pages: int
    applied: bool
    ready: bool


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
        embedding_function: Any | None = None,
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
        self._collection_name = collection_name
        self._embedding_function = embedding_function
        collection_kwargs: dict[str, Any] = {"name": collection_name}
        if embedding_function is not None:
            collection_kwargs["embedding_function"] = embedding_function
        try:
            if create_if_missing:
                # Chroma applies this metadata only when it creates the collection. Opening an
                # existing collection therefore never certifies legacy visibility implicitly.
                collection_kwargs["metadata"] = {
                    LEGACY_VISIBILITY_SCHEMA_KEY: LEGACY_VISIBILITY_SCHEMA_VERSION
                }
                self._collection = client.get_or_create_collection(**collection_kwargs)
            else:
                self._collection = client.get_collection(**collection_kwargs)
        except Exception as exc:
            raise ChromaUnavailable(
                f"Chroma collection '{collection_name}' is unavailable."
            ) from exc

    def upsert(self, documents: list[SourceDocument]) -> int:
        if not documents:
            return 0
        if any(document.document_id.startswith("research:") for document in documents):
            raise ChromaLegacyVisibilityError("Research IDs require immutable snapshot staging.")

        ids: list[str] = []
        metadatas: list[dict[str, MetadataValue]] = []
        legacy_ids: list[str] = []
        for document in documents:
            metadata = document.chroma_metadata()
            if LEGACY_VISIBILITY_KEY in metadata:
                raise ValueError(f"'{LEGACY_VISIBILITY_KEY}' is reserved for the Chroma adapter.")
            has_snapshot_identity = _has_snapshot_identity(metadata)
            metadata[LEGACY_VISIBILITY_KEY] = (
                BLOCKED_VISIBILITY_VALUE if has_snapshot_identity else LEGACY_VISIBILITY_VALUE
            )
            ids.append(document.document_id)
            metadatas.append(metadata)
            if not has_snapshot_identity:
                legacy_ids.append(document.document_id)

        if len(ids) != len(set(ids)):
            raise ValueError("A Chroma upsert batch cannot contain duplicate document IDs.")

        existing = self._existing_metadatas_for_upsert(legacy_ids)
        converted_ids = [
            document_id
            for document_id in legacy_ids
            if _has_snapshot_identity(existing.get(document_id, {}))
        ]
        if converted_ids:
            raise ChromaLegacyVisibilityError(
                "Legacy upsert rejected because existing Chroma metadata contains snapshot "
                f"identity for {len(converted_ids)} document(s)."
            )

        self._collection.upsert(
            ids=ids,
            documents=[document.content for document in documents],
            metadatas=metadatas,
        )
        return len(documents)

    def stage_snapshot(self, documents: list[SourceDocument]) -> int:
        """Insert immutable records; Chroma add never overwrites a competing accepted ID."""
        expected = {document.document_id: document for document in documents}
        if not expected or len(expected) != len(documents):
            raise ChromaLegacyVisibilityError("Snapshot staging requires unique complete records.")
        for document in documents:
            if not document.document_id.startswith("research:"):
                raise ChromaLegacyVisibilityError("Snapshot staging requires research identities.")
            validate_document(document.document_id, document.content, document.chroma_metadata())
        existing = self.document_records(list(expected), require_all=False)
        for document_id, record in existing.items():
            document = expected[document_id]
            if record.content != document.content or record.metadata != document.chroma_metadata():
                raise ChromaLegacyVisibilityError("Conflicting immutable Chroma document identity.")
        missing = [document for document in documents if document.document_id not in existing]
        if missing:
            self._collection.add(
                ids=[document.document_id for document in missing],
                documents=[document.content for document in missing],
                metadatas=[
                    {**document.chroma_metadata(), LEGACY_VISIBILITY_KEY: BLOCKED_VISIBILITY_VALUE}
                    for document in missing
                ],
            )
        stored = self.document_records(list(expected))
        for document_id, record in stored.items():
            document = expected[document_id]
            if record.content != document.content or record.metadata != document.chroma_metadata():
                raise ChromaLegacyVisibilityError("Immutable Chroma staging readback differs.")
        return len(documents)

    def document_records(
        self, document_ids: list[str], *, require_all: bool = True
    ) -> dict[str, RetrievedSource]:
        """Read exact bounded arrays, rejecting omissions, duplicates and foreign IDs."""
        if not document_ids or len(document_ids) != len(set(document_ids)):
            raise ChromaLegacyVisibilityError("Invalid document readback manifest.")
        result = self._collection.get(ids=document_ids, include=["documents", "metadatas"])
        ids = _strict_readback_ids(result, set(document_ids))
        contents = result.get("documents")
        metadata = result.get("metadatas")
        if (
            not isinstance(contents, list)
            or not isinstance(metadata, list)
            or len(contents) != len(ids)
            or len(metadata) != len(ids)
            or (require_all and set(ids) != set(document_ids))
        ):
            raise ChromaLegacyVisibilityError("Incomplete immutable Chroma readback.")
        records: dict[str, RetrievedSource] = {}
        for index, document_id in enumerate(ids):
            if not isinstance(contents[index], str) or not isinstance(metadata[index], Mapping):
                raise ChromaLegacyVisibilityError("Malformed immutable Chroma record.")
            record = _without_adapter_metadata(
                RetrievedSource(
                    document_id=document_id, content=contents[index], metadata=dict(metadata[index])
                )
            )
            validate_document(record.document_id, record.content, record.metadata)
            records[document_id] = record
        return records

    def search(
        self,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedSource]:
        self._validate_search(query, limit)
        return self._query(query, limit=limit, where=where)

    def search_unversioned(self, query: str, limit: int = 5) -> list[RetrievedSource]:
        """Return a bounded legacy-only result set when no snapshot is active."""

        self._validate_search(query, limit)
        collection = self._fresh_collection()
        _require_legacy_visibility_ready(collection)
        candidates = self._query(
            query,
            limit=limit,
            where={LEGACY_VISIBILITY_KEY: LEGACY_VISIBILITY_VALUE},
            collection=collection,
            strip_adapter_metadata=False,
        )
        for candidate in candidates:
            if candidate.metadata.get(LEGACY_VISIBILITY_KEY) != LEGACY_VISIBILITY_VALUE:
                raise ChromaLegacyVisibilityError(
                    "Chroma returned a contradictory legacy visibility marker."
                )
            if _has_snapshot_identity(candidate.metadata):
                raise ChromaLegacyVisibilityError(
                    "Chroma returned snapshot metadata from the legacy-only query."
                )
        return [_without_adapter_metadata(candidate) for candidate in candidates]

    def prepare_legacy_visibility(
        self, *, apply: bool = False, page_size: int = 100
    ) -> LegacyVisibilityPreparationReport:
        """Preview or apply bounded, metadata-only legacy visibility preparation.

        Callers must quiesce readers and writers before using ``apply=True``. A failed apply
        deliberately leaves readiness in the preparing state so legacy retrieval fails closed.
        """

        if page_size < 1:
            raise ValueError("Preparation page size must be at least 1.")
        collection = self._fresh_collection()
        if apply:
            _set_collection_schema(collection, LEGACY_VISIBILITY_PREPARING)

        initial_count = int(collection.count())
        legacy_count = 0
        blocked_count = 0
        page_count = 0
        seen_ids: set[str] = set()
        offset = 0
        while offset < initial_count:
            ids, metadatas = _metadata_page(collection, limit=page_size, offset=offset)
            if not ids:
                raise ChromaLegacyVisibilityError(
                    "Chroma preparation pagination ended before the initial count was reached."
                )
            if len(ids) != len(metadatas) or any(document_id in seen_ids for document_id in ids):
                raise ChromaLegacyVisibilityError(
                    "Chroma preparation returned incomplete or duplicate metadata rows."
                )
            classified = [_classified_metadata(metadata) for metadata in metadatas]
            legacy_count += sum(
                metadata[LEGACY_VISIBILITY_KEY] == LEGACY_VISIBILITY_VALUE
                for metadata in classified
            )
            blocked_count += sum(
                metadata[LEGACY_VISIBILITY_KEY] == BLOCKED_VISIBILITY_VALUE
                for metadata in classified
            )
            if apply:
                collection.update(ids=ids, metadatas=classified)
                _verify_metadata_page(collection, ids, classified)
            seen_ids.update(ids)
            page_count += 1
            offset += len(ids)

        if len(seen_ids) != initial_count or int(collection.count()) != initial_count:
            raise ChromaLegacyVisibilityError(
                "Chroma collection changed during legacy visibility preparation."
            )
        if apply:
            _validate_prepared_collection(collection, initial_count, page_size)
            _set_collection_schema(collection, LEGACY_VISIBILITY_SCHEMA_VERSION)

        return LegacyVisibilityPreparationReport(
            collection_name=self._collection_name,
            total_documents=initial_count,
            legacy_documents=legacy_count,
            blocked_documents=blocked_count,
            pages=page_count,
            applied=apply,
            ready=apply or _legacy_visibility_ready(collection),
        )

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
        collection: Any | None = None,
        strip_adapter_metadata: bool = True,
    ) -> list[RetrievedSource]:
        kwargs: dict[str, Any] = {"query_texts": [query], "n_results": limit}
        if where:
            kwargs["where"] = where
        result = (collection or self._collection).query(**kwargs)
        ids = _single_query_row(result, "ids")
        contents = _single_query_row(result, "documents")
        metadata = _single_query_row(result, "metadatas")
        distances = _single_query_row(result, "distances")
        lengths = {len(ids), len(contents), len(metadata), len(distances)}
        if len(lengths) != 1:
            raise ChromaLegacyVisibilityError(
                "Chroma returned query arrays with contradictory lengths."
            )
        normalized_ids = [str(document_id) for document_id in ids]
        if len(normalized_ids) != len(set(normalized_ids)):
            raise ChromaLegacyVisibilityError("Chroma returned duplicate query result IDs.")
        if len(ids) > limit:
            raise ChromaLegacyVisibilityError(
                "Chroma returned more query results than the requested limit."
            )
        if any(not isinstance(item, Mapping) for item in metadata):
            raise ChromaLegacyVisibilityError("Chroma returned malformed query result metadata.")
        retrieved: list[RetrievedSource] = []
        for index, document_id in enumerate(normalized_ids):
            source = RetrievedSource(
                document_id=document_id,
                content=str(contents[index]),
                metadata=dict(metadata[index]),
                distance=_as_float(distances[index]),
            )
            retrieved.append(
                _without_adapter_metadata(source) if strip_adapter_metadata else source
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

    def _fresh_collection(self) -> Any:
        try:
            kwargs: dict[str, Any] = {"name": self._collection_name}
            if self._embedding_function is not None:
                kwargs["embedding_function"] = self._embedding_function
            return self._client.get_collection(**kwargs)
        except Exception as exc:
            raise ChromaUnavailable(
                f"Chroma collection '{self._collection_name}' is unavailable."
            ) from exc

    def _existing_metadatas_for_upsert(self, document_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not document_ids:
            return {}
        requested = set(document_ids)
        presence = self._collection.get(ids=document_ids, include=[])
        existing_ids = _strict_readback_ids(presence, requested)
        if not existing_ids:
            return {}

        result = self._collection.get(ids=existing_ids, include=["metadatas"])
        read_ids = _strict_readback_ids(result, set(existing_ids))
        raw_metadatas = result.get("metadatas")
        if not isinstance(raw_metadatas, list) or len(raw_metadatas) != len(read_ids):
            raise ChromaLegacyVisibilityError(
                "Chroma returned incomplete metadata for existing upsert IDs."
            )
        if set(read_ids) != set(existing_ids):
            raise ChromaLegacyVisibilityError(
                "Chroma omitted existing IDs from upsert metadata readback."
            )
        if any(not isinstance(metadata, Mapping) for metadata in raw_metadatas):
            raise ChromaLegacyVisibilityError(
                "Chroma returned malformed metadata for existing upsert IDs."
            )
        return {
            document_id: dict(raw_metadatas[index]) for index, document_id in enumerate(read_ids)
        }


def _metadata_page(
    collection: Any, *, limit: int, offset: int
) -> tuple[list[str], list[dict[str, Any]]]:
    result = collection.get(limit=limit, offset=offset, include=["metadatas"])
    ids = [str(document_id) for document_id in result.get("ids", [])]
    raw_metadatas = list(result.get("metadatas", []))
    metadatas = [dict(metadata) if metadata is not None else {} for metadata in raw_metadatas]
    return ids, metadatas


def _classified_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    classified = dict(metadata)
    classified[LEGACY_VISIBILITY_KEY] = (
        BLOCKED_VISIBILITY_VALUE if _has_snapshot_identity(classified) else LEGACY_VISIBILITY_VALUE
    )
    return classified


def _verify_metadata_page(collection: Any, ids: list[str], expected: list[dict[str, Any]]) -> None:
    result = collection.get(ids=ids, include=["metadatas"])
    read_ids = [str(document_id) for document_id in result.get("ids", [])]
    read_metadatas = list(result.get("metadatas", []))
    actual = {
        document_id: dict(read_metadatas[index])
        for index, document_id in enumerate(read_ids)
        if index < len(read_metadatas) and read_metadatas[index] is not None
    }
    expected_by_id = dict(zip(ids, expected, strict=True))
    if actual != expected_by_id:
        raise ChromaLegacyVisibilityError(
            "Chroma did not retain the prepared legacy visibility metadata."
        )


def _validate_prepared_collection(collection: Any, expected_count: int, page_size: int) -> None:
    seen_ids: set[str] = set()
    offset = 0
    while offset < expected_count:
        ids, metadatas = _metadata_page(collection, limit=page_size, offset=offset)
        if (
            not ids
            or len(ids) != len(metadatas)
            or any(document_id in seen_ids for document_id in ids)
        ):
            raise ChromaLegacyVisibilityError(
                "Chroma final preparation validation returned incomplete metadata rows."
            )
        for metadata in metadatas:
            expected_marker = (
                BLOCKED_VISIBILITY_VALUE
                if _has_snapshot_identity(metadata)
                else LEGACY_VISIBILITY_VALUE
            )
            if metadata.get(LEGACY_VISIBILITY_KEY) != expected_marker:
                raise ChromaLegacyVisibilityError(
                    "Chroma final preparation validation found a contradictory marker."
                )
        seen_ids.update(ids)
        offset += len(ids)
    if len(seen_ids) != expected_count or int(collection.count()) != expected_count:
        raise ChromaLegacyVisibilityError(
            "Chroma collection changed during final preparation validation."
        )


def _set_collection_schema(collection: Any, value: int) -> None:
    metadata = dict(collection.metadata or {})
    metadata[LEGACY_VISIBILITY_SCHEMA_KEY] = value
    collection.modify(metadata=metadata)


def _legacy_visibility_ready(collection: Any) -> bool:
    metadata = collection.metadata or {}
    value = metadata.get(LEGACY_VISIBILITY_SCHEMA_KEY)
    return type(value) is int and value == LEGACY_VISIBILITY_SCHEMA_VERSION


def _require_legacy_visibility_ready(collection: Any) -> None:
    metadata = collection.metadata or {}
    value = metadata.get(LEGACY_VISIBILITY_SCHEMA_KEY)
    if type(value) is int and value == LEGACY_VISIBILITY_PREPARING:
        raise ChromaLegacyVisibilityError(
            "Chroma legacy visibility preparation is in progress or incomplete."
        )
    if not _legacy_visibility_ready(collection):
        raise ChromaLegacyVisibilityError(
            "Chroma legacy visibility is not prepared; run the preparation command first."
        )


def _has_snapshot_identity(metadata: dict[str, Any]) -> bool:
    return any(key in metadata for key in SNAPSHOT_IDENTITY_KEYS)


def _without_adapter_metadata(source: RetrievedSource) -> RetrievedSource:
    metadata = dict(source.metadata)
    metadata.pop(LEGACY_VISIBILITY_KEY, None)
    return source.model_copy(update={"metadata": metadata})


def _single_query_row(result: Any, key: str) -> list[Any]:
    if not isinstance(result, Mapping):
        raise ChromaLegacyVisibilityError("Chroma returned a malformed query response.")
    value = result.get(key)
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], list):
        raise ChromaLegacyVisibilityError(
            f"Chroma returned malformed single-row query '{key}' data."
        )
    return list(value[0])


def _strict_readback_ids(result: Any, requested: set[str]) -> list[str]:
    if not isinstance(result, Mapping) or not isinstance(result.get("ids"), list):
        raise ChromaLegacyVisibilityError("Chroma returned malformed existing-ID readback.")
    ids = [str(document_id) for document_id in result["ids"]]
    if len(ids) != len(set(ids)):
        raise ChromaLegacyVisibilityError("Chroma returned duplicate existing-ID readback rows.")
    if any(document_id not in requested for document_id in ids):
        raise ChromaLegacyVisibilityError("Chroma returned unexpected existing-ID readback rows.")
    return ids


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
