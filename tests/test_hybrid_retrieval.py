from typing import Any, ClassVar

import pytest
from pydantic import ValidationError

from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.models import GraphContext, RetrievedSource
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity


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

    def search(
        self,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedSource]:
        assert query == "broad market"
        assert limit == 2
        assert where is not None
        return self.results

    def search_unversioned(self, query: str, limit: int = 5) -> list[RetrievedSource]:
        assert query == "broad market"
        assert limit == 2
        return self.results


class FakeRelationshipStore:
    def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None:
        return None

    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]:
        assert document_ids == ["doc-spy", "doc-missing"]
        return {
            "doc-spy": GraphContext(
                source_document_id="doc-spy",
                symbol="SPY",
                etf_name="SPDR S&P 500 ETF Trust",
                fund_family="State Street Global Advisors",
                category="Large Blend",
            )
        }


def test_hybrid_search_preserves_ranking_and_exposes_missing_context() -> None:
    results = HybridRetriever(FakeSemanticStore(), FakeRelationshipStore()).search(
        "broad market", limit=2
    )

    assert [result.document_id for result in results] == ["doc-spy", "doc-missing"]
    assert results[0].graph_context is not None
    assert results[0].graph_context.fund_family == "State Street Global Advisors"
    assert results[1].graph_context is None


def test_hybrid_search_scopes_semantic_candidates_to_active_snapshot() -> None:
    class ActiveRelationshipStore(FakeRelationshipStore):
        def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None:
            return ActiveSnapshotIdentity("snapshot-v2", "digest-v2")

    class SnapshotSemanticStore(FakeSemanticStore):
        def search(
            self,
            query: str,
            limit: int = 5,
            where: dict[str, Any] | None = None,
        ) -> list[RetrievedSource]:
            assert where == {
                "$and": [
                    {"snapshot_version": "snapshot-v2"},
                    {"snapshot_digest": "digest-v2"},
                ]
            }
            return self.results[:limit]

    results = HybridRetriever(SnapshotSemanticStore(), ActiveRelationshipStore()).search(
        "broad market", limit=2
    )

    assert [result.document_id for result in results] == ["doc-spy", "doc-missing"]


def test_hybrid_search_never_exposes_staged_documents_without_an_active_snapshot() -> None:
    class LegacyOnlySemanticStore(FakeSemanticStore):
        def search(self, *args: object, **kwargs: object) -> list[RetrievedSource]:
            raise AssertionError("unfiltered search must not run without an active snapshot")

        def search_unversioned(self, query: str, limit: int = 5) -> list[RetrievedSource]:
            return self.results[:limit]

    results = HybridRetriever(LegacyOnlySemanticStore(), FakeRelationshipStore()).search(
        "broad market", limit=2
    )

    assert [result.document_id for result in results] == ["doc-spy", "doc-missing"]


def test_graph_context_rejects_unsupported_issuer_claims() -> None:
    with pytest.raises(ValidationError, match="issuer"):
        GraphContext.model_validate(
            {
                "source_document_id": "doc-spy",
                "symbol": "SPY",
                "etf_name": "SPDR S&P 500 ETF Trust",
                "issuer": "State Street Global Advisors",
                "category": "Large Blend",
            }
        )
