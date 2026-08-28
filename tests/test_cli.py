import pytest
from typer.testing import CliRunner

import etf_advisor.cli as cli
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.rag.evidence import EvidenceRetrievalError


def test_evidence_demo_exits_nonzero_before_review_when_retrieval_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeGraphStore:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FailingEvidenceRetriever:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> object:
            raise EvidenceRetrievalError("source service unavailable")

    graph_store = FakeGraphStore()
    monkeypatch.setattr(cli, "ChromaDocumentStore", lambda **kwargs: object())
    monkeypatch.setattr(cli, "Neo4jGraphStore", lambda **kwargs: graph_store)
    monkeypatch.setattr(cli, "HybridRetriever", lambda *args: object())
    monkeypatch.setattr(cli, "HybridCandidateEvidenceRetriever", FailingEvidenceRetriever)

    result = CliRunner().invoke(cli.app, ["demo", "--with-evidence"])

    assert result.exit_code == 1
    assert "Workflow stopped before human review:" in result.output
    assert "Paused for human review:" not in result.output
    assert "source service unavailable" in result.output
    assert graph_store.closed is True
