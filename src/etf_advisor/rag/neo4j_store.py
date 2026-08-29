"""Minimal Neo4j index for attributable ETF relationship context."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import Any, cast

from etf_advisor.rag.models import GraphContext, SourceDocument

_CONSTRAINTS = (
    "CREATE CONSTRAINT etf_symbol IF NOT EXISTS FOR (etf:ETF) REQUIRE etf.symbol IS UNIQUE",
    "CREATE CONSTRAINT fund_family_name IF NOT EXISTS "
    "FOR (fund_family:FundFamily) REQUIRE fund_family.name IS UNIQUE",
    "CREATE CONSTRAINT category_name IF NOT EXISTS "
    "FOR (category:Category) REQUIRE category.name IS UNIQUE",
    "CREATE CONSTRAINT source_document_id IF NOT EXISTS "
    "FOR (source:SourceDocument) REQUIRE source.document_id IS UNIQUE",
    "CREATE CONSTRAINT research_snapshot_version IF NOT EXISTS "
    "FOR (snapshot:ResearchSnapshot) REQUIRE snapshot.version IS UNIQUE",
    "CREATE CONSTRAINT research_catalog_id IF NOT EXISTS "
    "FOR (catalog:ResearchCatalog) REQUIRE catalog.id IS UNIQUE",
)

_UPSERT_DOCUMENT = """
MERGE (etf:ETF {symbol: $symbol})
SET etf.name = $etf_name
MERGE (source:SourceDocument {document_id: $document_id})
SET source.source = $source,
    source.source_url = $source_url,
    source.observed_at = datetime($observed_at),
    source.document_type = $document_type
MERGE (etf)-[:DESCRIBED_BY]->(source)
WITH etf, source
OPTIONAL MATCH (source)-[
    stale_source_relationship:REPORTS_FUND_FAMILY|REPORTS_CATEGORY|REPORTS_ISSUER
]->()
DELETE stale_source_relationship
WITH DISTINCT etf, source
OPTIONAL MATCH (etf)-[stale_etf_relationship:IN_FUND_FAMILY|IN_CATEGORY|ISSUED_BY]->()
DELETE stale_etf_relationship
WITH DISTINCT etf, source
FOREACH (_ IN CASE WHEN $fund_family_name IS NULL THEN [] ELSE [1] END |
    MERGE (fund_family:FundFamily {name: $fund_family_name})
    MERGE (etf)-[:IN_FUND_FAMILY]->(fund_family)
    MERGE (source)-[:REPORTS_FUND_FAMILY]->(fund_family)
)
FOREACH (_ IN CASE WHEN $category_name IS NULL THEN [] ELSE [1] END |
    MERGE (category:Category {name: $category_name})
    MERGE (etf)-[:IN_CATEGORY]->(category)
    MERGE (source)-[:REPORTS_CATEGORY]->(category)
)
"""

_FIND_CONTEXTS = """
UNWIND $document_ids AS document_id
MATCH (etf:ETF)-[:DESCRIBED_BY]->(source:SourceDocument {document_id: document_id})
OPTIONAL MATCH (source)-[:REPORTS_FUND_FAMILY]->(fund_family:FundFamily)
OPTIONAL MATCH (source)-[:REPORTS_CATEGORY]->(category:Category)
RETURN document_id AS source_document_id,
       etf.symbol AS symbol,
       etf.name AS etf_name,
       fund_family.name AS fund_family,
       category.name AS category
ORDER BY source_document_id
"""

_FIND_EXISTING_IDS = """
MATCH (source:SourceDocument)
WHERE source.document_id IN $document_ids
RETURN source.document_id AS document_id
"""

_PUBLISH_SNAPSHOT = """
MERGE (snapshot:ResearchSnapshot {version: $snapshot_version})
ON CREATE SET snapshot.universe_id = $universe_id,
    snapshot.universe_version = $universe_version,
    snapshot.digest = $snapshot_digest
WITH snapshot
WHERE snapshot.universe_id = $universe_id
  AND snapshot.universe_version = $universe_version
  AND snapshot.digest = $snapshot_digest
UNWIND $documents AS document
MERGE (etf:ETF {symbol: document.symbol})
SET etf.name = document.etf_name
MERGE (source:SourceDocument {document_id: document.document_id})
SET source.source = document.source,
    source.source_url = document.source_url,
    source.observed_at = datetime(document.observed_at),
    source.document_type = document.document_type,
    source.snapshot_version = $snapshot_version
MERGE (etf)-[:DESCRIBED_BY]->(source)
MERGE (snapshot)-[:CONTAINS]->(source)
WITH snapshot, etf, source, document
OPTIONAL MATCH (source)-[
    stale_source_relationship:REPORTS_FUND_FAMILY|REPORTS_CATEGORY|REPORTS_ISSUER
]->()
DELETE stale_source_relationship
WITH DISTINCT snapshot, etf, source, document
FOREACH (_ IN CASE WHEN document.fund_family_name IS NULL THEN [] ELSE [1] END |
    MERGE (fund_family:FundFamily {name: document.fund_family_name})
    MERGE (source)-[:REPORTS_FUND_FAMILY]->(fund_family)
)
FOREACH (_ IN CASE WHEN document.category_name IS NULL THEN [] ELSE [1] END |
    MERGE (category:Category {name: document.category_name})
    MERGE (source)-[:REPORTS_CATEGORY]->(category)
)
WITH snapshot, count(DISTINCT source) AS published_count
WHERE published_count = $expected_count
MERGE (catalog:ResearchCatalog {id: 'active'})
OPTIONAL MATCH (catalog)-[previous:ACTIVE_SNAPSHOT]->(:ResearchSnapshot)
DELETE previous
MERGE (catalog)-[:ACTIVE_SNAPSHOT]->(snapshot)
RETURN published_count
"""

_ACTIVE_SNAPSHOT_VERSION = """
MATCH (:ResearchCatalog {id: 'active'})-[:ACTIVE_SNAPSHOT]->(snapshot:ResearchSnapshot)
RETURN snapshot.version AS snapshot_version
"""

_SNAPSHOT_DIGEST = """
MATCH (snapshot:ResearchSnapshot {version: $snapshot_version})
RETURN snapshot.digest AS snapshot_digest
"""


class Neo4jUnavailable(RuntimeError):
    """Raised when the Neo4j dependency is missing or an operation fails."""


class Neo4jGraphStore:
    """Upsert and retrieve the small graph projection used by hybrid search."""

    def __init__(
        self,
        uri: str,
        auth: tuple[str, str],
        *,
        database: str = "neo4j",
        driver: Any | None = None,
    ) -> None:
        if driver is None:
            try:
                neo4j = importlib.import_module("neo4j")
            except ImportError as exc:
                raise Neo4jUnavailable(
                    "Neo4j retrieval requires the optional 'rag' dependencies. "
                    "Run: uv sync --extra rag"
                ) from exc
            driver = neo4j.GraphDatabase.driver(uri, auth=auth)
        self._driver = driver
        self._database = database

    def close(self) -> None:
        self._driver.close()

    def ensure_schema(self) -> None:
        for statement in _CONSTRAINTS:
            self._execute(statement)

    def upsert(self, documents: list[SourceDocument]) -> int:
        if not documents:
            return 0
        self.ensure_schema()
        for document in documents:
            metadata = document.chroma_metadata()
            self._execute(
                _UPSERT_DOCUMENT,
                {
                    "document_id": document.document_id,
                    "symbol": document.symbol,
                    "etf_name": str(metadata.get("name", document.symbol)),
                    "source": document.source,
                    "source_url": document.source_url,
                    "observed_at": document.observed_at.isoformat(),
                    "document_type": document.document_type,
                    "fund_family_name": _optional_string(metadata.get("fund_family")),
                    "category_name": _optional_string(metadata.get("category")),
                },
            )
        return len(documents)

    def publish_snapshot(
        self,
        documents: list[SourceDocument],
        *,
        snapshot_version: str,
        universe_id: str,
        universe_version: str,
        snapshot_digest: str,
    ) -> int:
        """Write one graph snapshot and change its active pointer in one transaction."""

        if not documents:
            raise ValueError("A research snapshot must contain at least one document.")
        document_ids = [document.document_id for document in documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("Research snapshot document IDs must be unique.")
        rows: list[dict[str, Any]] = []
        for document in documents:
            metadata = document.chroma_metadata()
            if metadata.get("snapshot_version") != snapshot_version:
                raise ValueError("Every graph document must match the published snapshot version.")
            rows.append(
                {
                    "document_id": document.document_id,
                    "symbol": document.symbol,
                    "etf_name": str(metadata.get("name", document.symbol)),
                    "source": document.source,
                    "source_url": document.source_url,
                    "observed_at": document.observed_at.isoformat(),
                    "document_type": document.document_type,
                    "fund_family_name": _optional_string(metadata.get("fund_family")),
                    "category_name": _optional_string(metadata.get("category")),
                }
            )

        self.ensure_schema()
        records = list(
            self._execute(
                _PUBLISH_SNAPSHOT,
                {
                    "snapshot_version": snapshot_version,
                    "universe_id": universe_id,
                    "universe_version": universe_version,
                    "snapshot_digest": snapshot_digest,
                    "expected_count": len(rows),
                    "documents": rows,
                },
            )
        )
        if len(records) != 1:
            raise Neo4jUnavailable(
                "Neo4j did not activate the complete research snapshot; "
                "the prior snapshot remains active."
            )
        published_count = _record_data(records[0]).get("published_count")
        if not isinstance(published_count, int):
            raise Neo4jUnavailable("Neo4j returned an invalid snapshot publication count.")
        return published_count

    def active_snapshot_version(self) -> str | None:
        """Return the graph-authoritative version used to scope hybrid retrieval."""

        records = list(self._execute(_ACTIVE_SNAPSHOT_VERSION))
        if not records:
            return None
        if len(records) != 1:
            raise Neo4jUnavailable("Neo4j returned multiple active research snapshots.")
        value = _record_data(records[0]).get("snapshot_version")
        if not isinstance(value, str) or not value.strip():
            raise Neo4jUnavailable("Neo4j returned an invalid active snapshot version.")
        return value

    def snapshot_digest(self, snapshot_version: str) -> str | None:
        """Return an existing immutable snapshot digest, if this version was published."""

        records = list(self._execute(_SNAPSHOT_DIGEST, {"snapshot_version": snapshot_version}))
        if not records:
            return None
        if len(records) != 1:
            raise Neo4jUnavailable("Neo4j returned duplicate research snapshot versions.")
        value = _record_data(records[0]).get("snapshot_digest")
        if not isinstance(value, str) or not value.strip():
            raise Neo4jUnavailable("Neo4j returned an invalid research snapshot digest.")
        return value

    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]:
        if not document_ids:
            return {}
        records = self._execute(_FIND_CONTEXTS, {"document_ids": document_ids})
        contexts: dict[str, GraphContext] = {}
        for record in records:
            data = _record_data(record)
            context = GraphContext.model_validate(data)
            if context.source_document_id in contexts:
                raise Neo4jUnavailable(
                    "Neo4j returned multiple relationship contexts for source document "
                    f"'{context.source_document_id}'. Re-ingest the affected snapshot."
                )
            contexts[context.source_document_id] = context
        return contexts

    def missing_document_ids(self, document_ids: list[str]) -> list[str]:
        if not document_ids:
            return []
        records = self._execute(_FIND_EXISTING_IDS, {"document_ids": document_ids})
        existing = {str(_record_data(record)["document_id"]) for record in records}
        return [document_id for document_id in document_ids if document_id not in existing]

    def _execute(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Iterable[Any]:
        try:
            result = self._driver.execute_query(
                query,
                parameters_=parameters or {},
                database_=self._database,
            )
        except Exception as exc:
            raise Neo4jUnavailable(
                "Neo4j operation failed; check service health and settings."
            ) from exc
        records = getattr(result, "records", result[0] if isinstance(result, tuple) else result)
        if records is None:
            return []
        return cast(Iterable[Any], records)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _record_data(record: Any) -> dict[str, Any]:
    if hasattr(record, "data"):
        return dict(record.data())
    return dict(record)
