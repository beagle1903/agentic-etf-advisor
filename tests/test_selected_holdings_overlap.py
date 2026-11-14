"""Selected-draft presentation reuses conservative pair results without I/O/state writes."""

import json
import socket
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from test_dashboard import _construction_source, valid_profile
from test_issue101_overlap import _fixture, _rows

import etf_advisor.dashboard as dashboard
import etf_advisor.dashboard_app as dashboard_app
from etf_advisor.dashboard import DashboardRun, review_payload
from etf_advisor.dashboard_overlap import selected_reported_holdings_overlaps
from etf_advisor.graph.revision import validate_revision_state
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.evidence import CandidateEvidenceBundle, select_candidate_evidence

CHECKED = datetime(2026, 8, 28, 12, tzinfo=UTC)


def _evidence() -> dict[str, Any]:
    sources = []
    for symbol, category, rows in (
        ("SPY", "Large Blend", _rows(("X", "Holding X", 10))),
        ("VTI", "Large Blend", _rows(("X", "Holding X", 8))),
        ("QQQ", "Large Growth", _rows(("Y", "Holding Y", 7))),
        ("VEA", "Foreign Large Blend", None),
        ("IVV", "Large Blend", _rows(("X", "Holding X", 6))),
        ("BND", "Intermediate Core Bond", _rows(("X", "Different identity", 5))),
    ):
        item = _construction_source(symbol, category, CHECKED - timedelta(hours=1), CHECKED)
        fields = json.loads(item.metadata["field_provenance_json"])
        fields["top_holdings"] = {
            "value": rows,
            "unit": "percent_of_fund",
            "provider": "yahoo_finance",
            "source_url": f"https://example.test/{symbol}/holdings",
            "observed_at": "2026-08-28T11:00:00Z",
            "ingested_at": "2026-08-28T12:00:00Z",
            "snapshot_version": "dashboard-construction-v1",
            "missing_reason": None if rows is not None else "not_reported",
        }
        item.metadata["field_provenance_json"] = json.dumps(fields)
        item.metadata["top_holdings_status"] = "available" if rows is not None else "not_reported"
        sources.append(item)
    return select_candidate_evidence(
        valid_profile(),
        sources,
        query="selected pairs",
        checked_at=CHECKED,
        max_age=timedelta(hours=24),
        limit=6,
    ).model_dump(mode="json")


def test_exact_selected_membership_order_and_five_position_bound() -> None:
    evidence = _evidence()
    before = deepcopy(evidence)
    # Exclude the first-ranked candidate; preserve actual draft order by ID.
    ids = ["doc-bnd", "doc-ivv", "doc-vea", "doc-qqq", "doc-vti"]
    results = selected_reported_holdings_overlaps(evidence, ids)
    assert [(r["left"]["document_id"], r["right"]["document_id"]) for r in results] == [
        ("doc-bnd", "doc-ivv"),
        ("doc-bnd", "doc-vea"),
        ("doc-bnd", "doc-qqq"),
        ("doc-bnd", "doc-vti"),
        ("doc-ivv", "doc-vea"),
        ("doc-ivv", "doc-qqq"),
        ("doc-ivv", "doc-vti"),
        ("doc-vea", "doc-qqq"),
        ("doc-vea", "doc-vti"),
        ("doc-qqq", "doc-vti"),
    ]
    assert evidence == before
    assert selected_reported_holdings_overlaps(evidence, []) == []
    assert selected_reported_holdings_overlaps(evidence, [ids[0]]) == []
    with pytest.raises(ValueError, match="at most five"):
        selected_reported_holdings_overlaps(
            evidence, [c["document_id"] for c in evidence["candidates"]]
        )
    for invalid in ([ids[0], ids[0]], ["SPY", ids[0]], ["unknown"]):
        with pytest.raises(ValueError, match="distinct selected evidence document IDs"):
            selected_reported_holdings_overlaps(evidence, invalid)


@pytest.mark.parametrize(
    ("left", "right", "expected", "reason"),
    [
        ("doc-spy", "doc-vti", "8", None),
        ("doc-spy", "doc-qqq", "0", None),
        ("doc-spy", "doc-vea", None, "not_reported"),
        ("doc-spy", "doc-bnd", None, "conflicting_holding_identity"),
    ],
)
def test_partial_zero_and_unavailable_remain_exact(
    left: str, right: str, expected: str | None, reason: str | None
) -> None:
    (result,) = selected_reported_holdings_overlaps(_evidence(), [left, right])
    assert result["overlap_pp"] == (
        {"numerator": expected, "denominator": "1"} if expected is not None else None
    )
    assert result["status"] == ("available" if reason is None else "unavailable")
    assert result["reason_codes"] == ([] if reason is None else [reason])
    assert result["left"]["row_sum_pp"] == {"numerator": "10", "denominator": "1"}
    assert result["left"]["source_url"] == "https://example.test/SPY/holdings"
    assert result["left"]["observed_at"] == "2026-08-28T11:00:00Z"
    assert result["checked_at"] == "2026-08-28T12:00:00Z"


@pytest.mark.parametrize(
    ("observed", "reason"),
    [("2026-08-27T11:59:59Z", "stale_holdings"), ("2026-08-28T12:05:01Z", "future_holdings")],
)
def test_selected_pairs_keep_saved_freshness_limitations(observed: str, reason: str) -> None:
    rows = _rows(("X", "Holding X", 10))
    evidence = _fixture(rows, rows, observed=observed)
    (result,) = selected_reported_holdings_overlaps(
        evidence, [candidate["document_id"] for candidate in evidence["candidates"]]
    )
    assert result["overlap_pp"] is None
    assert reason in result["reason_codes"]


def test_actual_ready_and_detached_review_render_without_calls_or_state_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    evidence = _evidence()

    class Retriever:
        calls = 0

        def retrieve(self, *args: Any, **kwargs: Any) -> Any:
            self.calls += 1
            return CandidateEvidenceBundle.model_validate(deepcopy(evidence))

    retriever = Retriever()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=retriever,
        candidate_limit=6,
        clock=lambda: CHECKED,
    )
    config = {"configurable": {"thread_id": "selected-pairs-fixture"}}
    state = graph.invoke({"profile": valid_profile().model_dump(mode="json")}, config)
    assert state["status"] == "awaiting_human_review", state
    before = json.dumps({k: v for k, v in state.items() if k != "__interrupt__"}, sort_keys=True)
    payload = review_payload(state)
    assert [p["document_id"] for p in payload["portfolio_construction"]["draft"]["positions"]] == [
        "doc-spy",
        "doc-vti",
        "doc-qqq",
        "doc-vea",
        "doc-bnd",
    ]
    assert retriever.calls == 1

    forbidden_calls = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        forbidden_calls.append(True)
        raise AssertionError("Review rendering called a provider, store, runtime or network")

    monkeypatch.setattr(Retriever, "retrieve", forbidden)
    monkeypatch.setattr(InMemorySaver, "get_tuple", forbidden)
    monkeypatch.setattr(InMemorySaver, "put", forbidden)
    monkeypatch.setattr(graph, "invoke", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    run = DashboardRun(graph=graph, config=config, state=state)
    monkeypatch.setattr(dashboard, "start_dashboard_run", lambda *a, **kw: run)
    app = testing.AppTest.from_file(str(Path(dashboard_app.__file__))).run(timeout=60)
    next(b for b in app.sidebar.button if b.label == "Create review draft").click()
    app.run(timeout=60)

    def assert_display() -> list[dict[str, Any]]:
        assert not app.exception
        assert forbidden_calls == []
        (table,) = [d.value for d in app.dataframe if "Pair" in d.value.columns]
        assert table["Pair"].tolist() == [
            "SPY / VTI",
            "SPY / QQQ",
            "SPY / VEA",
            "SPY / BND",
            "VTI / QQQ",
            "VTI / VEA",
            "VTI / BND",
            "QQQ / VEA",
            "QQQ / BND",
            "VEA / BND",
        ]
        assert table.iloc[0]["Overlap (pp)"] == "≈ 8.000000"
        assert table.iloc[1]["Overlap (pp)"] == "≈ 0.000000"
        assert table.iloc[2]["Overlap (pp)"] == "Unavailable"
        assert table.iloc[2]["Limitations"] == "not_reported"
        assert table.iloc[3]["Limitations"] == "conflicting_holding_identity"
        assert any("lists may be partial" in c.value for c in app.caption)
        assert any("do not establish independent risk" in c.value for c in app.caption)
        assert any("2026-08-28T12:00:00Z" in c.value for c in app.caption)
        assert any("https://example.test/SPY/holdings" in c.value for c in app.caption)
        results = [json.loads(item.value) for item in app.json]
        selected = [r for r in results if isinstance(r, dict) and "overlap_pp" in r]
        assert len(selected) == 10
        assert selected[0]["matched_holdings"] == 1
        assert selected[0]["right"]["row_sum_pp"] == {"numerator": "8", "denominator": "1"}
        return selected

    first = assert_display()
    assert (
        json.dumps({k: v for k, v in state.items() if k != "__interrupt__"}, sort_keys=True)
        == before
    )
    restored = json.loads(before)
    validate_revision_state(restored, "selected-pairs-fixture")
    restored["__interrupt__"] = (
        SimpleNamespace(value=json.loads(json.dumps(state["__interrupt__"][0].value))),
    )
    assert review_payload(restored) == payload
    app.session_state["dashboard_run"] = DashboardRun(graph=None, config=config, state=restored)
    app.run(timeout=60)
    assert assert_display() == first
    assert (
        json.dumps({k: v for k, v in restored.items() if k != "__interrupt__"}, sort_keys=True)
        == before
    )
    # The original manual tool still accepts unselected IVV without changing the automatic table.
    next(
        m
        for m in app.multiselect
        if m.label == "Choose two candidates for reported-holdings overlap"
    ).set_value(["doc-ivv", "doc-spy"])
    app.run(timeout=60)
    assert not app.exception
    (table,) = [d.value for d in app.dataframe if "Pair" in d.value.columns]
    assert table["Pair"].tolist()[0] == "SPY / VTI"
    assert len(table) == 10
    assert (
        json.dumps({k: v for k, v in restored.items() if k != "__interrupt__"}, sort_keys=True)
        == before
    )
    assert retriever.calls == 1
    assert forbidden_calls == []


def test_display_limit_does_not_truncate_larger_draft() -> None:
    testing = pytest.importorskip("streamlit.testing.v1")

    def render(evidence: dict) -> None:
        import streamlit as st

        from etf_advisor.dashboard_app import _render_selected_holdings_overlap

        _render_selected_holdings_overlap(
            st, evidence, {"draft": {"positions": evidence["candidates"]}}
        )

    evidence = _evidence()
    before = deepcopy(evidence)
    app = testing.AppTest.from_function(render, args=(evidence,)).run(timeout=60)
    assert not app.exception
    assert any("at most five selected positions" in w.value for w in app.warning)
    assert not app.dataframe
    assert evidence == before
