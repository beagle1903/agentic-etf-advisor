from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from etf_advisor.encoding import document_fingerprint
from etf_advisor.rag.models import SourceDocument
from etf_advisor.rag.neo4j_store import Neo4jGraphStore, Neo4jUnavailable, _expected_facts
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity, SnapshotManifest


class FakeResult:
    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self.records = records or []


class FakeDriver:
    def __init__(self) -> None:
        self.upsert_parameters: list[dict[str, Any]] = []
        self.upsert_queries: list[str] = []
        self.snapshot_parameters: list[dict[str, Any]] = []
        self.active_snapshot: str | None = None
        self.snapshot_digest: str | None = None
        self.closed = False
        self.rows: list[dict[str, Any]] = []
        self.manifest: dict[str, Any] | None = None
        self.commits = 0

    def session(self, **kwargs: Any) -> FakeDriver:
        return self

    def __enter__(self) -> FakeDriver:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def begin_transaction(self) -> FakeDriver:
        return self

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass

    def run(self, query: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        if "RETURN count(active) AS active_count" in query:
            return [{"active_count": int(self.active_snapshot is not None)}]
        if "CREATE (snapshot:ResearchSnapshot" in query:
            self.snapshot_parameters.append(parameters)
            self.rows = parameters["documents"]
            self.manifest = {
                "snapshot_digest": parameters["snapshot_digest"],
                "schema_version": parameters["schema_version"],
                "document_count": len(self.rows),
                "manifest_json": parameters["manifest_json"],
                "children": [
                    {
                        "document_id": row["document_id"],
                        "labels": ["SourceDocument"],
                        "snapshot_version": parameters["snapshot_version"],
                        "snapshot_digest": parameters["snapshot_digest"],
                        "fingerprint": row["properties"]["document_fingerprint"],
                        "immutable_json": row["properties"]["immutable_json"],
                    }
                    for row in self.rows
                ],
            }
            return [{"published_count": len(self.rows)}]
        if "snapshot.document_count AS document_count" in query:
            return [self.manifest] if self.manifest else []
        if "properties(source) AS properties" in query:
            return [
                {
                    "properties": row["properties"],
                    "facts": [json.loads(item) for item in _expected_facts(row, active=False)],
                }
                for row in self.rows
                if row["document_id"] == parameters["document_id"]
            ]
        if "etf.symbol AS symbol, etf.name AS name" in query:
            return [
                {
                    "symbol": row["symbol"],
                    "name": row["etf_name"],
                    "facts": [json.loads(item) for item in _expected_facts(row, active=True)],
                }
                for row in self.rows
            ]
        if "CREATE (catalog)-[:ACTIVE_SNAPSHOT]" in query:
            self.active_snapshot = parameters["snapshot_version"]
            assert self.manifest is not None
            self.snapshot_digest = self.manifest["snapshot_digest"]
        return self.execute_query(query, database_="neo4j", parameters_=parameters).records

    def execute_query(self, query: str, **kwargs: Any) -> FakeResult:
        assert kwargs["database_"] == "neo4j"
        parameters = kwargs["parameters_"]
        if "MERGE (etf:ETF" in query:
            self.upsert_queries.append(query)
            self.upsert_parameters.append(parameters)
        if "RETURN published_count" in query:
            self.snapshot_parameters.append(parameters)
            self.active_snapshot = str(parameters["snapshot_version"])
            self.snapshot_digest = str(parameters["snapshot_digest"])
            return FakeResult([{"published_count": len(parameters["documents"])}])
        if "RETURN snapshot.version AS snapshot_version" in query:
            if self.active_snapshot is None:
                return FakeResult()
            return FakeResult(
                [
                    {
                        "snapshot_version": self.active_snapshot,
                        "snapshot_digest": self.snapshot_digest,
                    }
                ]
            )
        if "snapshot.document_count AS document_count" in query:
            if self.manifest is not None:
                return FakeResult([self.manifest])
            if self.snapshot_digest is None or self.active_snapshot is None:
                return FakeResult()
            return FakeResult(
                [
                    {
                        "snapshot_digest": self.snapshot_digest,
                        "document_count": 1,
                        "document_ids": ["research:snapshot-v1:abc123:spy"],
                    }
                ]
            )
        if "RETURN snapshot.digest AS snapshot_digest" in query:
            if self.snapshot_digest is None:
                return FakeResult()
            return FakeResult([{"snapshot_digest": self.snapshot_digest}])
        if "RETURN source.document_id AS document_id" in query:
            return FakeResult([{"document_id": "doc-spy"}])
        if "RETURN document_id AS source_document_id" in query:
            return FakeResult(
                [
                    {
                        "source_document_id": "doc-spy",
                        "symbol": "SPY",
                        "etf_name": "SPDR S&P 500 ETF Trust",
                        "fund_family": "State Street Global Advisors",
                        "category": "Large Blend",
                        "sector_exposures_status": "available",
                        "sector_exposures": [{"name": "technology", "weight_pct": 37.4}],
                    }
                ]
            )
        return FakeResult()

    def close(self) -> None:
        self.closed = True


def test_neo4j_store_upserts_provenance_and_reads_relationship_context() -> None:
    driver = FakeDriver()
    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=driver)
    document = SourceDocument(
        document_id="doc-spy",
        symbol="SPY",
        title="SPY snapshot",
        content="Source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 26, 20, 0, tzinfo=UTC),
        metadata={
            "name": "SPDR S&P 500 ETF Trust",
            "fund_family": "State Street Global Advisors",
            "category": "Large Blend",
        },
    )

    assert store.upsert([document]) == 1
    parameters = driver.upsert_parameters[0]
    assert parameters["document_id"] == "doc-spy"
    assert parameters["source_url"] == "https://finance.yahoo.com/quote/SPY/"
    assert parameters["observed_at"] == "2026-08-26T20:00:00+00:00"
    assert parameters["fund_family_name"] == "State Street Global Advisors"
    upsert_query = driver.upsert_queries[0]
    assert "DELETE stale_source_relationship" in upsert_query
    assert "DELETE stale_etf_relationship" in upsert_query
    assert "(source)-[:REPORTS_FUND_FAMILY]->(fund_family)" in upsert_query

    contexts = store.find_contexts(["doc-spy", "doc-missing"])
    assert contexts["doc-spy"].category == "Large Blend"
    assert store.missing_document_ids(["doc-spy", "doc-missing"]) == ["doc-missing"]

    store.close()
    assert driver.closed is True


def test_neo4j_store_clears_relationships_when_metadata_disappears() -> None:
    driver = FakeDriver()
    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=driver)
    document = SourceDocument(
        document_id="doc-spy",
        symbol="SPY",
        title="SPY snapshot",
        content="Source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 26, 20, 0, tzinfo=UTC),
    )

    store.upsert([document])

    parameters = driver.upsert_parameters[0]
    assert parameters["fund_family_name"] is None
    assert parameters["category_name"] is None
    query = driver.upsert_queries[0]
    assert query.index("DELETE stale_source_relationship") < query.index(
        "FOREACH (_ IN CASE WHEN $fund_family_name"
    )


@pytest.mark.parametrize("symbol", ["SPY", "OTHER"])
def test_generic_graph_upsert_rejects_active_catalog_without_projection_writes(symbol: str) -> None:
    driver = FakeDriver()
    driver.active_snapshot, driver.snapshot_digest = "active", "digest"
    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=driver)
    document = SourceDocument(
        document_id="ordinary",
        symbol=symbol,
        title="ordinary",
        content="ordinary",
        source="test",
        source_url="https://example.com",
        observed_at=datetime(2026, 9, 26, tzinfo=UTC),
    )
    with pytest.raises(Neo4jUnavailable) as blocked:
        store.upsert([document])
    assert blocked.value.code == "projection_integrity"
    assert driver.upsert_parameters == []
    assert driver.commits == 0


def test_neo4j_store_rejects_ambiguous_legacy_context() -> None:
    class DuplicateContextDriver(FakeDriver):
        def execute_query(self, query: str, **kwargs: Any) -> FakeResult:
            if "RETURN document_id AS source_document_id" in query:
                context = {
                    "source_document_id": "doc-spy",
                    "symbol": "SPY",
                    "etf_name": "SPDR S&P 500 ETF Trust",
                    "fund_family": "State Street Global Advisors",
                    "category": "Large Blend",
                }
                return FakeResult([context, context])
            return super().execute_query(query, **kwargs)

    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=DuplicateContextDriver())

    with pytest.raises(Neo4jUnavailable, match="multiple relationship contexts"):
        store.find_contexts(["doc-spy"])


@pytest.mark.parametrize("schema", [1, 2])
def test_graph_read_rejects_duplicate_numeric_relationship_encoding(schema: int) -> None:
    class DuplicateNumericDriver(FakeDriver):
        def execute_query(self, query: str, **kwargs: Any) -> FakeResult:
            if "RETURN document_id AS source_document_id" in query:
                return FakeResult(
                    [
                        {
                            "source_document_id": "doc-spy",
                            "schema_version": schema,
                            "symbol": "SPY",
                            "etf_name": "ETF",
                            "sector_exposures_status": "available",
                            "sector_exposures": [
                                {
                                    "name": "technology",
                                    "weight_pct": 37.4,
                                    "weight_pct_token": "37.4",
                                }
                            ],
                        }
                    ]
                )
            return super().execute_query(query, **kwargs)

    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=DuplicateNumericDriver())
    with pytest.raises(Neo4jUnavailable) as raised:
        store.find_contexts(["doc-spy"])
    assert raised.value.code == "schema_encoding"


def test_neo4j_store_publishes_and_activates_snapshot_in_explicit_transaction() -> None:
    driver = FakeDriver()
    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=driver)
    document = SourceDocument(
        document_id="research:snapshot-v1:abc123:spy",
        symbol="SPY",
        title="SPY research snapshot",
        content="Source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
        metadata={
            "snapshot_version": "snapshot-v1",
            "snapshot_digest": "abc123",
            "name": "SPDR S&P 500 ETF Trust",
            "fund_family": "State Street Global Advisors",
            "category": "Large Blend",
            "field_provenance_schema_version": 1,
            "field_provenance_json": (
                '{"sector_exposures":{"missing_reason":null,'
                '"value":[{"name":"technology","symbol":null,'
                '"weight_pct":37.4}]}}'
            ),
            "sector_exposures_status": "available",
        },
    )

    count = store.publish_snapshot(
        [document],
        snapshot_version="snapshot-v1",
        universe_id="core",
        universe_version="1.0.0",
        snapshot_digest="abc123",
    )

    assert count == 1
    assert store.active_snapshot_identity() == ActiveSnapshotIdentity("snapshot-v1", "abc123")
    assert store.snapshot_digest("snapshot-v1") == "abc123"
    assert store.snapshot_manifest("snapshot-v1") == SnapshotManifest(
        snapshot_version="snapshot-v1",
        snapshot_digest="abc123",
        document_count=1,
        document_ids=("research:snapshot-v1:abc123:spy",),
        fingerprints={
            document.document_id: document_fingerprint(
                document.document_id, document.content, document.chroma_metadata()
            )
        },
    )
    parameters = driver.snapshot_parameters[0]
    assert parameters["expected_count"] == 1
    assert parameters["documents"][0]["category_name"] == "Large Blend"
    assert parameters["documents"][0]["sector_exposures_status"] == "available"
    assert parameters["documents"][0]["sector_exposures"] == [
        {"name": "technology", "weight_pct": 37.4}
    ]
    assert parameters["documents"][0]["field_provenance_schema_version"] == 1
    assert parameters["documents"][0]["field_provenance_json"] == (
        '{"sector_exposures":{"missing_reason":null,'
        '"value":[{"name":"technology","symbol":null,"weight_pct":37.4}]}}'
    )
    assert driver.commits == 1


def test_neo4j_snapshot_publish_preserves_explicit_missing_sector_status() -> None:
    driver = FakeDriver()
    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=driver)
    document = SourceDocument(
        document_id="research:snapshot-v1:abc123:bnd",
        symbol="BND",
        title="BND research snapshot",
        content="Source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/BND/",
        observed_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
        metadata={
            "snapshot_version": "snapshot-v1",
            "snapshot_digest": "abc123",
            "field_provenance_schema_version": 1,
            "field_provenance_json": (
                '{"sector_exposures":{"missing_reason":"not_reported","value":null}}'
            ),
            "sector_exposures_status": "not_reported",
        },
    )

    assert (
        store.publish_snapshot(
            [document],
            snapshot_version="snapshot-v1",
            universe_id="core",
            universe_version="1.0.0",
            snapshot_digest="abc123",
        )
        == 1
    )
    row = driver.snapshot_parameters[0]["documents"][0]
    assert row["sector_exposures_status"] == "not_reported"
    assert row["sector_exposures"] == []


@pytest.mark.parametrize(
    ("status", "provenance", "expected_exposures"),
    [
        (
            "source_error",
            '{"sector_exposures":{"missing_reason":"source_error","value":null}}',
            [],
        ),
        (
            "available",
            '{"sector_exposures":{"missing_reason":null,"value":['
            '{"name":"energy","symbol":null,"weight_pct":0.0}]}}',
            [{"name": "energy", "weight_pct": 0.0}],
        ),
    ],
)
def test_neo4j_snapshot_publish_distinguishes_source_error_from_explicit_zero(
    status: str,
    provenance: str,
    expected_exposures: list[dict[str, object]],
) -> None:
    driver = FakeDriver()
    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=driver)
    document = SourceDocument(
        document_id="research:snapshot-v1:abc123:spy",
        symbol="SPY",
        title="SPY research snapshot",
        content="Source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
        metadata={
            "snapshot_version": "snapshot-v1",
            "snapshot_digest": "abc123",
            "field_provenance_schema_version": 1,
            "field_provenance_json": provenance,
            "sector_exposures_status": status,
        },
    )

    assert (
        store.publish_snapshot(
            [document],
            snapshot_version="snapshot-v1",
            universe_id="core",
            universe_version="1.0.0",
            snapshot_digest="abc123",
        )
        == 1
    )

    row = driver.snapshot_parameters[0]["documents"][0]
    assert row["sector_exposures_status"] == status
    assert row["sector_exposures"] == expected_exposures


@pytest.mark.parametrize(
    ("sector_provenance", "error_match"),
    [
        (
            '{"sector_exposures":{"missing_reason":"source_error","value":null}}',
            "Available sector exposure provenance",
        ),
        (
            '{"sector_exposures":{"missing_reason":null,"value":[]}}',
            "non-empty list",
        ),
        (
            '{"sector_exposures":{"missing_reason":null,"value":['
            '{"name":"technology","weight_pct":37.4},'
            '{"name":"Technology","weight_pct":35.0}]}}',
            "unique after normalization",
        ),
    ],
)
def test_neo4j_snapshot_publish_rejects_invalid_sector_provenance(
    sector_provenance: str,
    error_match: str,
) -> None:
    driver = FakeDriver()
    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=driver)
    document = SourceDocument(
        document_id="research:snapshot-v1:abc123:spy",
        symbol="SPY",
        title="SPY research snapshot",
        content="Source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
        metadata={
            "snapshot_version": "snapshot-v1",
            "snapshot_digest": "abc123",
            "field_provenance_schema_version": 1,
            "field_provenance_json": sector_provenance,
            "sector_exposures_status": "available",
        },
    )

    with pytest.raises(ValueError, match=error_match):
        store.publish_snapshot(
            [document],
            snapshot_version="snapshot-v1",
            universe_id="core",
            universe_version="1.0.0",
            snapshot_digest="abc123",
        )

    assert driver.snapshot_parameters == []


def test_neo4j_snapshot_publish_rejects_mixed_versions_before_writing() -> None:
    driver = FakeDriver()
    store = Neo4jGraphStore("neo4j://unused", ("user", "password"), driver=driver)
    document = SourceDocument(
        document_id="research:snapshot-v1:abc123:spy",
        symbol="SPY",
        title="SPY research snapshot",
        content="Source content",
        source="yahoo_finance",
        source_url="https://finance.yahoo.com/quote/SPY/",
        observed_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
        metadata={"snapshot_version": "snapshot-v0", "snapshot_digest": "abc123"},
    )

    with pytest.raises(ValueError, match="match the published snapshot"):
        store.publish_snapshot(
            [document],
            snapshot_version="snapshot-v1",
            universe_id="core",
            universe_version="1.0.0",
            snapshot_digest="abc123",
        )

    assert driver.snapshot_parameters == []


def test_neo4j_snapshot_manifest_requires_persisted_document_count() -> None:
    class LegacyManifestDriver(FakeDriver):
        def execute_query(self, query: str, **kwargs: Any) -> FakeResult:
            if "snapshot.document_count AS document_count" in query:
                return FakeResult(
                    [
                        {
                            "snapshot_digest": "abc123",
                            "document_count": None,
                            "document_ids": ["doc-spy"],
                        }
                    ]
                )
            return super().execute_query(query, **kwargs)

    store = Neo4jGraphStore(
        "neo4j://unused",
        ("user", "password"),
        driver=LegacyManifestDriver(),
    )

    with pytest.raises(Neo4jUnavailable, match="canonical payload"):
        store.snapshot_manifest("snapshot-v1")
