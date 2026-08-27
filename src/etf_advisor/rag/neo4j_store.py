"""Minimal Neo4j index for attributable ETF relationship context."""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import Any, cast

from etf_advisor.rag.models import GraphContext, SourceDocument

_CONSTRAINTS = (
    "CREATE CONSTRAINT etf_symbol IF NOT EXISTS FOR (etf:ETF) REQUIRE etf.symbol IS UNIQUE",
    "CREATE CONSTRAINT issuer_name IF NOT EXISTS FOR (issuer:Issuer) REQUIRE issuer.name IS UNIQUE",
    "CREATE CONSTRAINT category_name IF NOT EXISTS "
    "FOR (category:Category) REQUIRE category.name IS UNIQUE",
    "CREATE CONSTRAINT source_document_id IF NOT EXISTS "
    "FOR (source:SourceDocument) REQUIRE source.document_id IS UNIQUE",
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
FOREACH (_ IN CASE WHEN $issuer_name IS NULL THEN [] ELSE [1] END |
    MERGE (issuer:Issuer {name: $issuer_name})
    MERGE (etf)-[:ISSUED_BY]->(issuer)
    MERGE (source)-[:REPORTS_ISSUER]->(issuer)
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
OPTIONAL MATCH (source)-[:REPORTS_ISSUER]->(issuer:Issuer)
OPTIONAL MATCH (source)-[:REPORTS_CATEGORY]->(category:Category)
RETURN document_id AS source_document_id,
       etf.symbol AS symbol,
       etf.name AS etf_name,
       issuer.name AS issuer,
       category.name AS category
ORDER BY source_document_id
"""

_FIND_EXISTING_IDS = """
MATCH (source:SourceDocument)
WHERE source.document_id IN $document_ids
RETURN source.document_id AS document_id
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
                    "issuer_name": _optional_string(metadata.get("fund_family")),
                    "category_name": _optional_string(metadata.get("category")),
                },
            )
        return len(documents)

    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]:
        if not document_ids:
            return {}
        records = self._execute(_FIND_CONTEXTS, {"document_ids": document_ids})
        contexts: dict[str, GraphContext] = {}
        for record in records:
            data = _record_data(record)
            context = GraphContext.model_validate(data)
            contexts.setdefault(context.source_document_id, context)
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
