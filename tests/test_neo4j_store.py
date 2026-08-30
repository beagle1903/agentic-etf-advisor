from datetime import UTC, datetime
from typing import Any

import pytest

from etf_advisor.rag.models import SourceDocument
from etf_advisor.rag.neo4j_store import Neo4jGraphStore, Neo4jUnavailable
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


def test_neo4j_store_publishes_and_activates_snapshot_in_one_query() -> None:
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
    snapshot_query = next(query for query in driver.upsert_queries if "ResearchSnapshot" in query)
    assert "ON CREATE SET snapshot.universe_id" in snapshot_query
    assert "AND snapshot.digest = $snapshot_digest" in snapshot_query
    assert "snapshot.document_count = $expected_count" in snapshot_query
    assert "source.snapshot_digest = $snapshot_digest" in snapshot_query
    assert "source.field_provenance_json = document.field_provenance_json" in snapshot_query
    assert "DELETE stale_etf_relationship" in snapshot_query
    assert "MERGE (etf)-[:IN_FUND_FAMILY]->(fund_family)" in snapshot_query
    assert "MERGE (etf)-[:IN_CATEGORY]->(category)" in snapshot_query
    assert "MERGE (source)-[reported:REPORTS_SECTOR_EXPOSURE]->(sector)" in snapshot_query
    assert "MERGE (etf)-[has_exposure:HAS_SECTOR_EXPOSURE]->(sector)" in snapshot_query
    assert "count(DISTINCT published_source) AS published_count" in snapshot_query
    assert snapshot_query.index("WHERE published_count") < snapshot_query.index("ACTIVE_SNAPSHOT")


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
