"""Minimal Neo4j index for attributable ETF relationship context."""

from __future__ import annotations

import importlib
import json
from collections.abc import Iterable, Mapping
from typing import Any, cast

from etf_advisor.rag.models import GraphContext, SectorExposure, SourceDocument
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity, SnapshotManifest

_CONSTRAINTS = (
    "CREATE CONSTRAINT etf_symbol IF NOT EXISTS FOR (etf:ETF) REQUIRE etf.symbol IS UNIQUE",
    "CREATE CONSTRAINT fund_family_name IF NOT EXISTS "
    "FOR (fund_family:FundFamily) REQUIRE fund_family.name IS UNIQUE",
    "CREATE CONSTRAINT category_name IF NOT EXISTS "
    "FOR (category:Category) REQUIRE category.name IS UNIQUE",
    "CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (sector:Sector) REQUIRE sector.name IS UNIQUE",
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
OPTIONAL MATCH (source)-[
    sector_exposure:REPORTS_SECTOR_EXPOSURE
]->(sector:Sector)
WITH document_id, etf, source, fund_family, category,
     [item IN collect(
        CASE WHEN sector IS NULL THEN null ELSE {
            name: sector.name,
            weight_pct: sector_exposure.weight_pct
        } END
     ) WHERE item IS NOT NULL] AS sector_exposures
RETURN document_id AS source_document_id,
       etf.symbol AS symbol,
       etf.name AS etf_name,
       fund_family.name AS fund_family,
       category.name AS category,
       source.sector_exposures_status AS sector_exposures_status,
       sector_exposures
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
    snapshot.digest = $snapshot_digest,
    snapshot.document_count = $expected_count
WITH snapshot
WHERE snapshot.universe_id = $universe_id
  AND snapshot.universe_version = $universe_version
  AND snapshot.digest = $snapshot_digest
SET snapshot.document_count = coalesce(snapshot.document_count, $expected_count)
WITH snapshot
WHERE snapshot.document_count = $expected_count
UNWIND $documents AS document
MERGE (etf:ETF {symbol: document.symbol})
SET etf.name = document.etf_name
MERGE (source:SourceDocument {document_id: document.document_id})
SET source.source = document.source,
    source.source_url = document.source_url,
    source.observed_at = datetime(document.observed_at),
    source.document_type = document.document_type,
    source.snapshot_version = $snapshot_version,
    source.snapshot_digest = $snapshot_digest,
    source.field_provenance_schema_version = document.field_provenance_schema_version,
    source.field_provenance_json = document.field_provenance_json,
    source.sector_exposures_status = document.sector_exposures_status
MERGE (etf)-[:DESCRIBED_BY]->(source)
MERGE (snapshot)-[:CONTAINS]->(source)
WITH snapshot, etf, source, document
OPTIONAL MATCH (source)-[
    stale_source_relationship:REPORTS_FUND_FAMILY|REPORTS_CATEGORY|REPORTS_ISSUER|
        REPORTS_SECTOR_EXPOSURE
]->()
DELETE stale_source_relationship
WITH DISTINCT snapshot, etf, source, document
OPTIONAL MATCH (etf)-[
    stale_etf_relationship:IN_FUND_FAMILY|IN_CATEGORY|ISSUED_BY|HAS_SECTOR_EXPOSURE
]->()
DELETE stale_etf_relationship
WITH DISTINCT snapshot, etf, source, document
FOREACH (_ IN CASE WHEN document.fund_family_name IS NULL THEN [] ELSE [1] END |
    MERGE (fund_family:FundFamily {name: document.fund_family_name})
    MERGE (etf)-[:IN_FUND_FAMILY]->(fund_family)
    MERGE (source)-[:REPORTS_FUND_FAMILY]->(fund_family)
)
FOREACH (_ IN CASE WHEN document.category_name IS NULL THEN [] ELSE [1] END |
    MERGE (category:Category {name: document.category_name})
    MERGE (etf)-[:IN_CATEGORY]->(category)
    MERGE (source)-[:REPORTS_CATEGORY]->(category)
)
FOREACH (sector_exposure IN document.sector_exposures |
    MERGE (sector:Sector {name: sector_exposure.name})
    MERGE (source)-[reported:REPORTS_SECTOR_EXPOSURE]->(sector)
    SET reported.weight_pct = sector_exposure.weight_pct
    MERGE (etf)-[has_exposure:HAS_SECTOR_EXPOSURE]->(sector)
    SET has_exposure.weight_pct = sector_exposure.weight_pct
)
WITH DISTINCT snapshot
MATCH (snapshot)-[:CONTAINS]->(published_source:SourceDocument)
WHERE published_source.snapshot_version = $snapshot_version
  AND published_source.snapshot_digest = $snapshot_digest
WITH snapshot, count(DISTINCT published_source) AS published_count
WHERE published_count = $expected_count
MERGE (catalog:ResearchCatalog {id: 'active'})
OPTIONAL MATCH (catalog)-[previous:ACTIVE_SNAPSHOT]->(:ResearchSnapshot)
DELETE previous
MERGE (catalog)-[:ACTIVE_SNAPSHOT]->(snapshot)
RETURN published_count
"""

_ACTIVE_SNAPSHOT_IDENTITY = """
MATCH (:ResearchCatalog {id: 'active'})-[:ACTIVE_SNAPSHOT]->(snapshot:ResearchSnapshot)
RETURN snapshot.version AS snapshot_version, snapshot.digest AS snapshot_digest
"""

_SNAPSHOT_DIGEST = """
MATCH (snapshot:ResearchSnapshot {version: $snapshot_version})
RETURN snapshot.digest AS snapshot_digest
"""

_SNAPSHOT_MANIFEST = """
MATCH (snapshot:ResearchSnapshot {version: $snapshot_version})
OPTIONAL MATCH (snapshot)-[:CONTAINS]->(source:SourceDocument)
WHERE source.snapshot_version = snapshot.version
  AND source.snapshot_digest = snapshot.digest
RETURN snapshot.digest AS snapshot_digest,
       snapshot.document_count AS document_count,
       collect(source.document_id) AS document_ids
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
        symbols = [document.symbol for document in documents]
        if len(symbols) != len(set(symbols)):
            raise ValueError("Research snapshot symbols must be unique.")
        rows: list[dict[str, Any]] = []
        for document in documents:
            metadata = document.chroma_metadata()
            if metadata.get("snapshot_version") != snapshot_version:
                raise ValueError("Every graph document must match the published snapshot version.")
            if metadata.get("snapshot_digest") != snapshot_digest:
                raise ValueError("Every graph document must match the published snapshot digest.")
            sector_status, sector_exposures = _sector_projection(metadata)
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
                    "field_provenance_schema_version": metadata.get(
                        "field_provenance_schema_version"
                    ),
                    "field_provenance_json": metadata.get("field_provenance_json"),
                    "sector_exposures_status": sector_status,
                    "sector_exposures": sector_exposures,
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

    def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None:
        """Return the graph-authoritative identity used to scope hybrid retrieval."""

        records = list(self._execute(_ACTIVE_SNAPSHOT_IDENTITY))
        if not records:
            return None
        if len(records) != 1:
            raise Neo4jUnavailable("Neo4j returned multiple active research snapshots.")
        data = _record_data(records[0])
        version = data.get("snapshot_version")
        digest = data.get("snapshot_digest")
        if not isinstance(version, str) or not version.strip():
            raise Neo4jUnavailable("Neo4j returned an invalid active snapshot version.")
        if not isinstance(digest, str) or not digest.strip():
            raise Neo4jUnavailable("Neo4j returned an invalid active snapshot digest.")
        return ActiveSnapshotIdentity(snapshot_version=version, snapshot_digest=digest)

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

    def snapshot_manifest(self, snapshot_version: str) -> SnapshotManifest | None:
        """Return the immutable graph manifest needed to verify the semantic store."""

        records = list(self._execute(_SNAPSHOT_MANIFEST, {"snapshot_version": snapshot_version}))
        if not records:
            return None
        if len(records) != 1:
            raise Neo4jUnavailable("Neo4j returned duplicate research snapshot manifests.")
        data = _record_data(records[0])
        digest = data.get("snapshot_digest")
        document_count = data.get("document_count")
        raw_document_ids = data.get("document_ids")
        if not isinstance(digest, str) or not digest.strip():
            raise Neo4jUnavailable("Neo4j returned an invalid research snapshot digest.")
        if not isinstance(document_count, int) or document_count < 1:
            raise Neo4jUnavailable(
                "The active snapshot has no verifiable document count; retry with its "
                "canonical payload."
            )
        if not isinstance(raw_document_ids, list) or any(
            not isinstance(document_id, str) or not document_id.strip()
            for document_id in raw_document_ids
        ):
            raise Neo4jUnavailable("Neo4j returned an invalid research snapshot manifest.")
        document_ids = tuple(str(document_id) for document_id in raw_document_ids)
        if len(document_ids) != document_count or len(document_ids) != len(set(document_ids)):
            raise Neo4jUnavailable(
                "Neo4j research snapshot manifest does not match its published document count."
            )
        return SnapshotManifest(
            snapshot_version=snapshot_version,
            snapshot_digest=digest,
            document_count=document_count,
            document_ids=document_ids,
        )

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


def _sector_projection(
    metadata: Mapping[str, object],
) -> tuple[str, list[dict[str, str | float]]]:
    """Validate and project canonical sector provenance into graph rows."""

    allowed_statuses = {
        "available",
        "not_reported",
        "source_error",
        "provider_unsupported",
        "not_applicable",
    }
    status = _optional_string(metadata.get("sector_exposures_status"))
    if status not in allowed_statuses:
        raise ValueError("Snapshot sector exposure status is missing or invalid.")
    raw_provenance = metadata.get("field_provenance_json")
    if not isinstance(raw_provenance, str) or not raw_provenance.strip():
        raise ValueError("Snapshot field provenance JSON is required for sector projection.")
    try:
        provenance = json.loads(raw_provenance)
    except json.JSONDecodeError as exc:
        raise ValueError("Snapshot field provenance JSON is invalid.") from exc
    if not isinstance(provenance, dict):
        raise ValueError("Snapshot field provenance must be a JSON object.")
    sector_field = provenance.get("sector_exposures")
    if not isinstance(sector_field, dict):
        raise ValueError("Snapshot field provenance must include sector exposures.")

    value = sector_field.get("value")
    missing_reason = sector_field.get("missing_reason")
    if status != "available":
        if value is not None or missing_reason != status:
            raise ValueError("Snapshot sector exposure status conflicts with field provenance.")
        return status, []
    if missing_reason is not None or not isinstance(value, list) or not value:
        raise ValueError("Available sector exposure provenance must contain a non-empty list.")

    exposures: list[SectorExposure] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Sector exposure provenance entries must be JSON objects.")
        exposures.append(
            SectorExposure.model_validate(
                {"name": item.get("name"), "weight_pct": item.get("weight_pct")}
            )
        )
    names = [exposure.name.casefold() for exposure in exposures]
    if len(names) != len(set(names)):
        raise ValueError("Snapshot sector exposure names must be unique after normalization.")
    exposures.sort(key=lambda item: (-item.weight_pct, item.name.casefold()))
    return status, [
        {"name": exposure.name, "weight_pct": exposure.weight_pct} for exposure in exposures
    ]


def _record_data(record: Any) -> dict[str, Any]:
    if hasattr(record, "data"):
        return dict(record.data())
    return dict(record)
