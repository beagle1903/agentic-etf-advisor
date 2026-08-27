from datetime import UTC, datetime
from typing import Any

from etf_advisor.rag.models import SourceDocument
from etf_advisor.rag.neo4j_store import Neo4jGraphStore


class FakeResult:
    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self.records = records or []


class FakeDriver:
    def __init__(self) -> None:
        self.upsert_parameters: list[dict[str, Any]] = []
        self.upsert_queries: list[str] = []
        self.closed = False

    def execute_query(self, query: str, **kwargs: Any) -> FakeResult:
        assert kwargs["database_"] == "neo4j"
        parameters = kwargs["parameters_"]
        if "MERGE (etf:ETF" in query:
            self.upsert_queries.append(query)
            self.upsert_parameters.append(parameters)
        if "RETURN source.document_id AS document_id" in query:
            return FakeResult([{"document_id": "doc-spy"}])
        if "RETURN document_id AS source_document_id" in query:
            return FakeResult(
                [
                    {
                        "source_document_id": "doc-spy",
                        "symbol": "SPY",
                        "etf_name": "SPDR S&P 500 ETF Trust",
                        "issuer": "State Street Global Advisors",
                        "category": "Large Blend",
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
    assert parameters["issuer_name"] == "State Street Global Advisors"
    assert "(source)-[:REPORTS_ISSUER]->(issuer)" in driver.upsert_queries[0]

    contexts = store.find_contexts(["doc-spy", "doc-missing"])
    assert contexts["doc-spy"].category == "Large Blend"
    assert store.missing_document_ids(["doc-spy", "doc-missing"]) == ["doc-missing"]

    store.close()
    assert driver.closed is True
