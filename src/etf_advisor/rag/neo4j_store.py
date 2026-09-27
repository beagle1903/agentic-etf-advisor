"""Minimal Neo4j index for attributable ETF relationship context."""

from __future__ import annotations

import importlib
import json
from collections.abc import Iterable, Mapping
from typing import Any, cast

from etf_advisor.encoding import (
    FINGERPRINT_KEY,
    decode_exposures,
    document_fingerprint,
    document_schema,
    schema_version,
    strict_json,
    validate_document,
)
from etf_advisor.rag.models import GraphContext, SectorExposure, SourceDocument
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity, SnapshotManifest
from etf_advisor.research.models import ETFResearchRecord, ETFResearchSnapshot

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
            weight_pct: sector_exposure.weight_pct,
            weight_pct_token: sector_exposure.weight_pct_token
        } END
     ) WHERE item IS NOT NULL] AS sector_exposures
RETURN document_id AS source_document_id,
       etf.symbol AS symbol,
       coalesce(source.name, etf.name) AS etf_name,
       fund_family.name AS fund_family,
       category.name AS category,
       source.sector_exposures_status AS sector_exposures_status,
       coalesce(source.field_provenance_schema_version, 1) AS schema_version,
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
OPTIONAL MATCH (snapshot)-[edge:CONTAINS]->(source)
RETURN snapshot.digest AS snapshot_digest,
       snapshot.document_count AS document_count,
       coalesce(snapshot.schema_version, 1) AS schema_version,
       snapshot.manifest_json AS manifest_json,
       collect(CASE WHEN edge IS NULL THEN null ELSE {
          document_id: source.document_id, labels: labels(source),
          snapshot_version: source.snapshot_version, snapshot_digest: source.snapshot_digest,
          fingerprint: source.document_fingerprint, immutable_json: source.immutable_json
       } END) AS children
"""

_LOCK_CATALOG = """
MERGE (catalog:ResearchCatalog {id: 'active'})
SET catalog.publication_lock = coalesce(catalog.publication_lock, 0) + 1
RETURN catalog.id AS catalog_id
"""

_GENERIC_WRITE_GUARD = """
MATCH (catalog:ResearchCatalog {id: 'active'})
OPTIONAL MATCH (catalog)-[active:ACTIVE_SNAPSHOT]->()
RETURN count(active) AS active_count
"""

_CREATE_SNAPSHOT = """
CREATE (snapshot:ResearchSnapshot {version: $snapshot_version, digest: $snapshot_digest,
    universe_id: $universe_id, universe_version: $universe_version,
    document_count: $expected_count, schema_version: $schema_version,
    manifest_json: $manifest_json})
WITH snapshot
UNWIND $documents AS document
CREATE (source:SourceDocument {document_id: document.document_id})
SET source += document.properties
MERGE (etf:ETF {symbol: document.symbol})
MERGE (etf)-[:DESCRIBED_BY]->(source)
CREATE (snapshot)-[:CONTAINS]->(source)
FOREACH (_ IN CASE WHEN document.fund_family_name IS NULL THEN [] ELSE [1] END |
    MERGE (family:FundFamily {name: document.fund_family_name})
    CREATE (source)-[:REPORTS_FUND_FAMILY]->(family))
FOREACH (_ IN CASE WHEN document.category_name IS NULL THEN [] ELSE [1] END |
    MERGE (category:Category {name: document.category_name})
    CREATE (source)-[:REPORTS_CATEGORY]->(category))
FOREACH (exposure IN document.sector_exposures |
    MERGE (sector:Sector {name: exposure.name})
    CREATE (source)-[reported:REPORTS_SECTOR_EXPOSURE]->(sector)
    SET reported.weight_pct = exposure.weight_pct,
        reported.weight_pct_token = exposure.weight_pct_token)
RETURN count(source) AS published_count
"""

_REPLACE_PROJECTION = """
MATCH (etf:ETF)
OPTIONAL MATCH (etf)-[old:IN_FUND_FAMILY|IN_CATEGORY|ISSUED_BY|HAS_SECTOR_EXPOSURE]->()
DELETE old
WITH count(*) AS cleared
UNWIND $documents AS document
MATCH (etf:ETF {symbol: document.symbol})
SET etf.name = document.etf_name
FOREACH (_ IN CASE WHEN document.fund_family_name IS NULL THEN [] ELSE [1] END |
    MERGE (family:FundFamily {name: document.fund_family_name})
    CREATE (etf)-[:IN_FUND_FAMILY]->(family))
FOREACH (_ IN CASE WHEN document.category_name IS NULL THEN [] ELSE [1] END |
    MERGE (category:Category {name: document.category_name})
    CREATE (etf)-[:IN_CATEGORY]->(category))
FOREACH (exposure IN document.sector_exposures |
    MERGE (sector:Sector {name: exposure.name})
    CREATE (etf)-[active:HAS_SECTOR_EXPOSURE]->(sector)
    SET active.weight_pct = exposure.weight_pct,
        active.weight_pct_token = exposure.weight_pct_token)
RETURN count(etf) AS projected_count
"""

_SOURCE_FACTS = """
MATCH (source:SourceDocument {document_id: $document_id})
OPTIONAL MATCH (source)-[
    edge:REPORTS_FUND_FAMILY|REPORTS_CATEGORY|REPORTS_ISSUER|REPORTS_SECTOR_EXPOSURE
]->(target)
RETURN properties(source) AS properties,
       collect(CASE WHEN edge IS NULL THEN null ELSE {
         type: type(edge), name: target.name, labels: labels(target),
         weight_pct: edge.weight_pct, weight_pct_token: edge.weight_pct_token
       } END) AS facts
"""

_PROJECTION_FACTS = """
MATCH (etf:ETF)
OPTIONAL MATCH (etf)-[edge:IN_FUND_FAMILY|IN_CATEGORY|ISSUED_BY|HAS_SECTOR_EXPOSURE]->(target)
RETURN etf.symbol AS symbol, etf.name AS name,
       collect(CASE WHEN edge IS NULL THEN null ELSE {
         type: type(edge), name: target.name, labels: labels(target),
         weight_pct: edge.weight_pct, weight_pct_token: edge.weight_pct_token
       } END) AS facts
"""

_ACTIVATE = """
MATCH (catalog:ResearchCatalog {id: 'active'}),
      (snapshot:ResearchSnapshot {version: $snapshot_version})
OPTIONAL MATCH (catalog)-[old:ACTIVE_SNAPSHOT]->()
DELETE old
CREATE (catalog)-[:ACTIVE_SNAPSHOT]->(snapshot)
RETURN snapshot.version AS snapshot_version
"""

_LEGACY_SNAPSHOT = """
MATCH (snapshot:ResearchSnapshot {version: $snapshot_version})-[:CONTAINS]->(source:SourceDocument)
OPTIONAL MATCH (etf:ETF)-[:DESCRIBED_BY]->(source)
RETURN snapshot.universe_id AS universe_id, snapshot.universe_version AS universe_version,
       source.field_provenance_json AS field_provenance_json, etf.symbol AS symbol
ORDER BY symbol
"""


class Neo4jUnavailable(RuntimeError):
    """Raised when the Neo4j dependency is missing or an operation fails."""

    def __init__(self, message: str, *, code: str = "retrieval_unavailable") -> None:
        super().__init__(message)
        self.code = code


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
        if any(document.document_id.startswith("research:") for document in documents):
            raise Neo4jUnavailable("Research identities require immutable snapshot publication.")
        self.ensure_schema()
        with self._driver.session(database=self._database) as session:
            transaction = session.begin_transaction()
            committing = False
            try:
                _run(transaction, _LOCK_CATALOG)
                guard = _run(transaction, _GENERIC_WRITE_GUARD)
                if (
                    len(guard) != 1
                    or type(guard[0].get("active_count")) is not int
                    or guard[0]["active_count"] != 0
                ):
                    raise Neo4jUnavailable(
                        "Generic graph indexing is blocked while research is active. "
                        "Use immutable research publication.",
                        code="projection_integrity",
                    )
                for document in documents:
                    metadata = document.chroma_metadata()
                    _run(
                        transaction,
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
                committing = True
                transaction.commit()
            except Exception as exc:
                if not committing:
                    transaction.rollback()
                    if isinstance(exc, Neo4jUnavailable):
                        raise
                    raise Neo4jUnavailable(
                        "Generic graph indexing failed; confirmed rollback."
                    ) from None
                raise Neo4jUnavailable(
                    "Generic graph indexing acknowledgement is uncertain."
                ) from None
            finally:
                transaction.close()
        return len(documents)

    def publish_snapshot(
        self,
        documents: list[SourceDocument],
        *,
        snapshot_version: str,
        universe_id: str,
        universe_version: str,
        snapshot_digest: str,
        expected_prior: ActiveSnapshotIdentity | None = None,
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
            validate_document(document.document_id, document.content, metadata)
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

        versions = {document_schema(document.chroma_metadata()) for document in documents}
        if len(versions) != 1:
            raise Neo4jUnavailable("Research graph publication cannot mix schemas.")
        version = versions.pop()
        fingerprints: dict[str, str] = {}
        for document, row in zip(documents, rows, strict=True):
            metadata = document.chroma_metadata()
            fingerprint = document_fingerprint(document.document_id, document.content, metadata)
            fingerprints[document.document_id] = fingerprint
            properties = {key: value for key, value in metadata.items() if value is not None}
            properties.update(
                {
                    "document_id": document.document_id,
                    "content": document.content,
                    "document_fingerprint": fingerprint,
                }
            )
            row["properties"] = properties
            row["properties"]["immutable_json"] = _canonical(row)
        self.ensure_schema()
        with self._driver.session(database=self._database) as session:
            transaction = session.begin_transaction()
            committed = False
            try:
                _run(transaction, _LOCK_CATALOG)
                if _identity(_run(transaction, _ACTIVE_SNAPSHOT_IDENTITY)) != expected_prior:
                    raise Neo4jUnavailable(
                        "Research snapshot CAS rejected a changed active identity.",
                        code="projection_integrity",
                    )
                manifest = self._read_manifest(snapshot_version, transaction)
                source_rows = rows
                expected_fingerprints = fingerprints
                if manifest is None:
                    records = _run(
                        transaction,
                        _CREATE_SNAPSHOT,
                        {
                            "snapshot_version": snapshot_version,
                            "snapshot_digest": snapshot_digest,
                            "universe_id": universe_id,
                            "universe_version": universe_version,
                            "schema_version": version,
                            "manifest_json": _canonical(fingerprints),
                            "expected_count": len(rows),
                            "documents": rows,
                        },
                    )
                    if len(records) != 1 or records[0].get("published_count") != len(rows):
                        raise Neo4jUnavailable(
                            "Research snapshot graph creation failed validation."
                        )
                else:
                    legacy_manifest = manifest.schema_version == 1 and not manifest.fingerprints
                    if (
                        manifest.snapshot_digest != snapshot_digest
                        or manifest.schema_version != version
                        or (not legacy_manifest and manifest.fingerprints != fingerprints)
                        or set(manifest.document_ids) != set(document_ids)
                    ):
                        raise Neo4jUnavailable(
                            "Immutable research snapshot conflicts with payload."
                        )
                    if legacy_manifest:
                        source_rows = [_legacy_row(document) for document in documents]
                        expected_fingerprints = {}
                self._verify_sources(source_rows, transaction)
                _run(transaction, _REPLACE_PROJECTION, {"documents": rows})
                self._verify_projection(rows, transaction)
                self._verify_sources(source_rows, transaction)
                validated = self._read_manifest(snapshot_version, transaction)
                if validated is None or validated.fingerprints != expected_fingerprints:
                    raise Neo4jUnavailable(
                        "Research manifest failed precommit validation.", code="manifest_integrity"
                    )
                _run(transaction, _ACTIVATE, {"snapshot_version": snapshot_version})
                if _identity(
                    _run(transaction, _ACTIVE_SNAPSHOT_IDENTITY)
                ) != ActiveSnapshotIdentity(snapshot_version, snapshot_digest):
                    raise Neo4jUnavailable(
                        "Research activation failed precommit validation.",
                        code="projection_integrity",
                    )
                # A commit exception is an uncertain acknowledgement, never a success claim.
                committed = True
                transaction.commit()
            except Exception as exc:
                if not committed:
                    transaction.rollback()
                    if isinstance(exc, Neo4jUnavailable):
                        raise
                    raise Neo4jUnavailable(
                        "Research snapshot transaction failed; confirmed rollback."
                    ) from exc
                raise Neo4jUnavailable(
                    "Research snapshot commit acknowledgement is uncertain. "
                    "Verify exact active identity."
                ) from exc
            finally:
                transaction.close()
        return len(rows)

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

        return self._read_manifest(snapshot_version)

    def _read_manifest(
        self, snapshot_version: str, transaction: Any | None = None
    ) -> SnapshotManifest | None:
        records = (
            _run(transaction, _SNAPSHOT_MANIFEST, {"snapshot_version": snapshot_version})
            if transaction is not None
            else list(self._execute(_SNAPSHOT_MANIFEST, {"snapshot_version": snapshot_version}))
        )
        if not records:
            return None
        if len(records) != 1:
            raise Neo4jUnavailable(
                "Neo4j returned duplicate research snapshot manifests.", code="manifest_integrity"
            )
        data = _record_data(records[0])
        digest = data.get("snapshot_digest")
        document_count = data.get("document_count")
        children = data.get("children")
        version = schema_version(data.get("schema_version", 1))
        if not isinstance(digest, str) or not digest.strip():
            raise Neo4jUnavailable("Neo4j returned an invalid research snapshot digest.")
        if type(document_count) is not int or document_count < 1:
            raise Neo4jUnavailable(
                "The active snapshot has no verifiable document count; retry with its "
                "canonical payload.",
                code="manifest_integrity",
            )
        if not isinstance(children, list) or any(
            not isinstance(child, dict)
            or child.get("labels") != ["SourceDocument"]
            or child.get("snapshot_version") != snapshot_version
            or child.get("snapshot_digest") != digest
            or not isinstance(child.get("document_id"), str)
            or not child.get("document_id")
            for child in children
        ):
            raise Neo4jUnavailable(
                "Neo4j returned an invalid research snapshot manifest.", code="manifest_integrity"
            )
        document_ids = tuple(child["document_id"] for child in children)
        if len(document_ids) != document_count or len(document_ids) != len(set(document_ids)):
            raise Neo4jUnavailable(
                "Neo4j research snapshot manifest does not match its published document count.",
                code="manifest_integrity",
            )
        raw_manifest = data.get("manifest_json")
        if raw_manifest is None and version == 1:
            return SnapshotManifest(snapshot_version, digest, document_count, document_ids)
        if not isinstance(raw_manifest, str):
            raise Neo4jUnavailable(
                "Research manifest lacks immutable fingerprints; no repair is permitted.",
                code="manifest_integrity",
            )
        fingerprints = strict_json(raw_manifest)
        if not isinstance(fingerprints, dict) or set(fingerprints) != set(document_ids):
            raise Neo4jUnavailable(
                "Research manifest fingerprint membership differs.", code="manifest_integrity"
            )
        for child in children:
            if child.get("fingerprint") != fingerprints[child["document_id"]]:
                raise Neo4jUnavailable(
                    "Research source fingerprint differs from its immutable manifest.",
                    code="document_integrity",
                )
            raw = child.get("immutable_json")
            if not isinstance(raw, str):
                raise Neo4jUnavailable(
                    "Research source immutable facts are unavailable.", code="document_integrity"
                )
            _validate_immutable_row(strict_json(raw), fingerprints[child["document_id"]])
        return SnapshotManifest(
            snapshot_version=snapshot_version,
            snapshot_digest=digest,
            document_count=document_count,
            document_ids=document_ids,
            schema_version=version,
            fingerprints=fingerprints,
        )

    def verify_snapshot(self, snapshot_version: str) -> None:
        """Verify immutable source facts and current projection without any writes."""
        manifest = self.snapshot_manifest(snapshot_version)
        if manifest is None:
            raise Neo4jUnavailable("Research snapshot is missing.")
        if manifest.schema_version == 1 and not manifest.fingerprints:
            documents = self.snapshot_documents(snapshot_version)
            legacy_rows = [_legacy_row(document) for document in documents]
            self._verify_sources(legacy_rows)
            if self.active_snapshot_identity() == ActiveSnapshotIdentity(
                snapshot_version, manifest.snapshot_digest
            ):
                self._verify_projection(legacy_rows)
            return
        rows: list[dict[str, Any]] = []
        for document_id in manifest.document_ids:
            records = list(self._execute(_SOURCE_FACTS, {"document_id": document_id}))
            if len(records) != 1:
                raise Neo4jUnavailable("Research immutable source is missing or duplicated.")
            raw = _record_data(records[0]).get("properties", {}).get("immutable_json")
            if not isinstance(raw, str):
                raise Neo4jUnavailable("Research source lacks verifiable immutable facts.")
            row = strict_json(raw)
            if not isinstance(row, dict):
                raise Neo4jUnavailable("Research immutable source encoding is invalid.")
            row["properties"]["immutable_json"] = raw
            rows.append(row)
        self._verify_sources(rows)
        identity = self.active_snapshot_identity()
        if identity == ActiveSnapshotIdentity(snapshot_version, manifest.snapshot_digest):
            self._verify_projection(rows)

    def snapshot_documents(self, snapshot_version: str) -> list[SourceDocument]:
        """Reconstruct old schema-1 canonical documents from retained original source fields."""
        manifest = self.snapshot_manifest(snapshot_version)
        if manifest is None or manifest.schema_version != 1:
            raise Neo4jUnavailable("Legacy canonical reconstruction requires a schema-1 manifest.")
        records = list(self._execute(_LEGACY_SNAPSHOT, {"snapshot_version": snapshot_version}))
        if len(records) != manifest.document_count:
            raise Neo4jUnavailable("Legacy source identities are incomplete or duplicated.")
        research: list[ETFResearchRecord] = []
        universes: set[tuple[str, str]] = set()
        for record in records:
            data = _record_data(record)
            provenance = data.get("field_provenance_json")
            if not isinstance(provenance, str):
                raise Neo4jUnavailable("Legacy source provenance is unavailable.")
            research.append(
                ETFResearchRecord.model_validate(
                    {"symbol": data.get("symbol"), **strict_json(provenance)}
                )
            )
            universe_id, universe_version = data.get("universe_id"), data.get("universe_version")
            if not isinstance(universe_id, str) or not isinstance(universe_version, str):
                raise Neo4jUnavailable("Legacy universe identity is malformed.")
            universes.add((universe_id, universe_version))
        if len(universes) != 1:
            raise Neo4jUnavailable("Legacy universe identity is contradictory.")
        universe_id, universe_version = universes.pop()
        snapshot = ETFResearchSnapshot(
            snapshot_version=snapshot_version,
            universe_id=universe_id,
            universe_version=universe_version,
            ingested_at=research[0].name.ingested_at,
            records=research,
        )
        # Historical schema 1 retained the authoritative digest but not record ordering.
        # Per-document rendering is independent of that ordering and uses the retained identity.
        return [
            snapshot._to_source_document(record, digest=manifest.snapshot_digest)
            for record in research
        ]

    def _verify_sources(self, rows: list[dict[str, Any]], transaction: Any | None = None) -> None:
        for row in rows:
            records = (
                _run(transaction, _SOURCE_FACTS, {"document_id": row["document_id"]})
                if transaction is not None
                else list(self._execute(_SOURCE_FACTS, {"document_id": row["document_id"]}))
            )
            if len(records) != 1:
                raise Neo4jUnavailable(
                    "Immutable source facts are missing or duplicated.", code="document_integrity"
                )
            data = _record_data(records[0])
            properties = data.get("properties")
            if row.get("legacy") and isinstance(properties, dict):
                properties = dict(properties)
                from datetime import datetime

                properties["observed_at"] = datetime.fromisoformat(
                    str(properties.get("observed_at"))
                ).isoformat()
            if properties != row["properties"] or _canonical_facts(
                data.get("facts")
            ) != _expected_facts(row, active=False):
                raise Neo4jUnavailable(
                    "Immutable source semantic verification failed.", code="document_integrity"
                )

    def _verify_projection(
        self, rows: list[dict[str, Any]], transaction: Any | None = None
    ) -> None:
        records = (
            _run(transaction, _PROJECTION_FACTS)
            if transaction is not None
            else list(self._execute(_PROJECTION_FACTS))
        )
        expected = {row["symbol"]: row for row in rows}
        seen: set[str] = set()
        for record in records:
            data = _record_data(record)
            symbol = data.get("symbol")
            if not isinstance(symbol, str):
                raise Neo4jUnavailable(
                    "Malformed active research symbol.", code="projection_integrity"
                )
            if symbol in seen:
                raise Neo4jUnavailable(
                    "Duplicate active research projection.", code="projection_integrity"
                )
            seen.add(symbol)
            facts = _canonical_facts(data.get("facts"))
            row = expected.get(symbol)
            if row is None:
                if facts:
                    raise Neo4jUnavailable(
                        "Obsolete ETF retains active research projection.",
                        code="projection_integrity",
                    )
            elif data.get("name") != row["etf_name"] or facts != _expected_facts(row, active=True):
                raise Neo4jUnavailable(
                    "Active research projection failed semantic verification.",
                    code="projection_integrity",
                )
        if not set(expected).issubset(seen):
            raise Neo4jUnavailable(
                "Active research projection is incomplete.", code="projection_integrity"
            )

    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]:
        if not document_ids:
            return {}
        records = self._execute(_FIND_CONTEXTS, {"document_ids": document_ids})
        contexts: dict[str, GraphContext] = {}
        for record in records:
            data = _record_data(record)
            version = schema_version(data.get("schema_version", 1))
            for exposure in data.get("sector_exposures", []):
                absent_key = "weight_pct" if version == 2 else "weight_pct_token"
                if exposure.get(absent_key) is not None:
                    raise Neo4jUnavailable(
                        "Graph relationship contains contradictory numeric encodings.",
                        code="schema_encoding",
                    )
                exposure.pop(absent_key, None)
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
        provenance = strict_json(raw_provenance)
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
    version = document_schema(metadata)
    if version == 2:
        decode_exposures(value)
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Sector exposure provenance entries must be JSON objects.")
        exposures.append(
            SectorExposure.model_validate(
                {
                    "name": item.get("name"),
                    **(
                        {"weight_pct_token": item.get("weight_pct_token")}
                        if version == 2
                        else {"weight_pct": item.get("weight_pct")}
                    ),
                }
            )
        )
    names = [exposure.name.casefold() for exposure in exposures]
    if len(names) != len(set(names)):
        raise ValueError("Snapshot sector exposure names must be unique after normalization.")
    exposures.sort(key=lambda item: (-item.weight_pct, item.name.casefold()))
    return status, [exposure.model_dump() for exposure in exposures]


def _canonical(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _run(
    transaction: Any, query: str, parameters: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    return [_record_data(record) for record in transaction.run(query, parameters or {})]


def _identity(records: list[dict[str, Any]]) -> ActiveSnapshotIdentity | None:
    if not records:
        return None
    if len(records) != 1:
        raise Neo4jUnavailable("Multiple research active identities.")
    version, digest = records[0].get("snapshot_version"), records[0].get("snapshot_digest")
    if not isinstance(version, str) or not isinstance(digest, str) or not digest:
        raise Neo4jUnavailable("Invalid research active identity.")
    return ActiveSnapshotIdentity(version, digest)


def _canonical_facts(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise Neo4jUnavailable("Malformed research relationship facts.")
    return sorted(_canonical(item) for item in value)


def _expected_facts(row: dict[str, Any], *, active: bool) -> list[str]:
    facts: list[dict[str, Any]] = []
    for key, label, source_type, active_type in (
        ("fund_family_name", "FundFamily", "REPORTS_FUND_FAMILY", "IN_FUND_FAMILY"),
        ("category_name", "Category", "REPORTS_CATEGORY", "IN_CATEGORY"),
    ):
        if row[key] is not None:
            facts.append(
                {
                    "type": active_type if active else source_type,
                    "name": row[key],
                    "labels": [label],
                    "weight_pct": None,
                    "weight_pct_token": None,
                }
            )
    for exposure in row["sector_exposures"]:
        facts.append(
            {
                "type": "HAS_SECTOR_EXPOSURE" if active else "REPORTS_SECTOR_EXPOSURE",
                "name": exposure["name"],
                "labels": ["Sector"],
                "weight_pct": exposure.get("weight_pct"),
                "weight_pct_token": exposure.get("weight_pct_token"),
            }
        )
    return _canonical_facts(facts)


def _validate_immutable_row(row: Any, fingerprint: str) -> None:
    if not isinstance(row, dict) or not isinstance(row.get("properties"), dict):
        raise Neo4jUnavailable("Research immutable source encoding is malformed.")
    properties = row["properties"]
    metadata = {
        key: value
        for key, value in properties.items()
        if key not in {"content", "document_id", "immutable_json"}
    }
    version = schema_version(metadata.get("field_provenance_schema_version", 1))
    if version == 1:
        metadata.pop(FINGERPRINT_KEY, None)
    content = properties.get("content")
    document_id = properties.get("document_id")
    if not isinstance(content, str) or not isinstance(document_id, str):
        raise Neo4jUnavailable("Research immutable document body is unavailable.")
    if document_fingerprint(document_id, content, metadata) != fingerprint:
        raise Neo4jUnavailable("Research immutable document fingerprint differs.")
    validate_document(document_id, content, metadata, expected_fingerprint=fingerprint)
    status, exposures = _sector_projection(metadata)
    expected = {
        "document_id": document_id,
        "symbol": metadata.get("symbol"),
        "etf_name": metadata.get("name", metadata.get("symbol")),
        "source": metadata.get("source"),
        "source_url": metadata.get("source_url"),
        "document_type": metadata.get("document_type"),
        "fund_family_name": _optional_string(metadata.get("fund_family")),
        "category_name": _optional_string(metadata.get("category")),
        "field_provenance_schema_version": metadata.get("field_provenance_schema_version"),
        "field_provenance_json": metadata.get("field_provenance_json"),
        "sector_exposures_status": status,
        "sector_exposures": exposures,
    }
    if any(row.get(key) != value for key, value in expected.items()):
        raise Neo4jUnavailable("Research immutable projection contradicts its source.")


def _legacy_row(document: SourceDocument) -> dict[str, Any]:
    metadata = document.chroma_metadata()
    status, exposures = _sector_projection(metadata)
    return {
        "legacy": True,
        "document_id": document.document_id,
        "symbol": document.symbol,
        "etf_name": metadata.get("name", document.symbol),
        "fund_family_name": _optional_string(metadata.get("fund_family")),
        "category_name": _optional_string(metadata.get("category")),
        "sector_exposures": exposures,
        "properties": {
            "document_id": document.document_id,
            "source": document.source,
            "source_url": document.source_url,
            "observed_at": document.observed_at.isoformat(),
            "document_type": document.document_type,
            "snapshot_version": metadata["snapshot_version"],
            "snapshot_digest": metadata["snapshot_digest"],
            "field_provenance_schema_version": 1,
            "field_provenance_json": metadata["field_provenance_json"],
            "sector_exposures_status": status,
        },
    }


def _record_data(record: Any) -> dict[str, Any]:
    if hasattr(record, "data"):
        return dict(record.data())
    return dict(record)
