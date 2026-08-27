from typing import ClassVar

from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.models import GraphContext, RetrievedSource


class FakeSemanticStore:
    results: ClassVar[list[RetrievedSource]] = [
        RetrievedSource(
            document_id="doc-spy",
            content="SPY source",
            metadata={"source": "yahoo_finance", "symbol": "SPY"},
            distance=0.1,
        ),
        RetrievedSource(
            document_id="doc-missing",
            content="Unlinked source",
            metadata={"source": "example", "symbol": "ABC"},
            distance=0.2,
        ),
    ]

    def search(self, query: str, limit: int = 5) -> list[RetrievedSource]:
        assert query == "broad market"
        assert limit == 2
        return self.results


class FakeRelationshipStore:
    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]:
        assert document_ids == ["doc-spy", "doc-missing"]
        return {
            "doc-spy": GraphContext(
                source_document_id="doc-spy",
                symbol="SPY",
                etf_name="SPDR S&P 500 ETF Trust",
                issuer="State Street Global Advisors",
                category="Large Blend",
            )
        }


def test_hybrid_search_preserves_ranking_and_exposes_missing_context() -> None:
    results = HybridRetriever(FakeSemanticStore(), FakeRelationshipStore()).search(
        "broad market", limit=2
    )

    assert [result.document_id for result in results] == ["doc-spy", "doc-missing"]
    assert results[0].graph_context is not None
    assert results[0].graph_context.issuer == "State Street Global Advisors"
    assert results[1].graph_context is None
