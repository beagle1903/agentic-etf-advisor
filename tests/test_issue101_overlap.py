"""Independent controls for the reported-holdings diagnostic."""

import json
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from test_evidence import CHECKED_AT, profile, source
from test_lossless_contract import lossless_snapshot
from test_vanguard import DATE as BND_DATE
from test_vanguard import snapshot as bnd_snapshot

import etf_advisor.dashboard as dashboard
import etf_advisor.dashboard_app as dashboard_app
from etf_advisor.dashboard import DashboardRun
from etf_advisor.dashboard_overlap import display_amount, reported_holdings_overlap
from etf_advisor.encoding import decimal_token, upward
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.models import WeightedExposure


def _rows(*entries: tuple[str | None, str, float]) -> list[dict[str, Any]]:
    return [
        {"symbol": symbol, "name": name, "weight_pct": weight} for symbol, name, weight in entries
    ]


def _fixture(
    left: Any,
    right: Any,
    *,
    providers: tuple[str, str] = ("fixture", "fixture"),
    observed: str = "2026-08-28T11:00:00Z",
) -> dict[str, Any]:
    sources = [source("SPY"), source("VTI")]
    for item, value, provider in zip(sources, (left, right), providers, strict=True):
        field = {
            "value": value,
            "unit": "percent_of_fund",
            "provider": provider,
            "source_url": "https://example.test/holdings",
            "observed_at": observed,
            "ingested_at": "2026-08-28T12:00:00Z",
            "snapshot_version": "fixture-v1",
            "missing_reason": None if value is not None else "not_reported",
        }
        item.metadata["top_holdings_status"] = "available" if value is not None else "not_reported"
        item.metadata["field_provenance_json"] = json.dumps({"top_holdings": field})
    evidence = select_candidate_evidence(
        profile(),
        sources,
        query="reported rows",
        checked_at=CHECKED_AT,
        max_age=timedelta(hours=24),
        limit=2,
    )
    return evidence.model_dump(mode="json")


def _result(bundle: dict[str, Any]) -> dict[str, Any]:
    ids = [candidate["document_id"] for candidate in bundle["candidates"]]
    return reported_holdings_overlap(bundle, *ids)


@pytest.mark.parametrize(
    ("left", "right", "left_sum", "right_sum", "overlap", "matches"),
    [
        (
            _rows(("X", "Holding X", 12.5), ("Y", "Holding Y", 7.5)),
            _rows(("Z", "Holding Z", 15), ("W", "Holding W", 5)),
            20,
            20,
            0,
            0,
        ),
        (
            _rows(("X", "Holding X", 12.5), ("Y", "Holding Y", 7.5)),
            _rows(("X", "Holding X", 12.5), ("Y", "Holding Y", 7.5)),
            20,
            20,
            20,
            2,
        ),
        (
            _rows(("X", "Holding X", 12.5), ("Y", "Holding Y", 7.5), ("Z", "Holding Z", 5)),
            _rows(("X", "Holding X", 10), ("Y", "Holding Y", 12.5), ("W", "Holding W", 7.5)),
            25,
            30,
            Fraction(35, 2),
            2,
        ),
        (_rows(("X", "Holding X", 0)), _rows(("X", "Holding X", 10)), 0, 10, 0, 1),
    ],
)
def test_exact_controls(
    left: Any, right: Any, left_sum: Any, right_sum: Any, overlap: Any, matches: int
) -> None:
    bundle = _fixture(left, right)
    original = deepcopy(bundle)
    result = _result(bundle)
    assert result["status"] == "available", result
    assert result["left"]["row_sum_pp"] == {
        "numerator": str(Fraction(left_sum).numerator),
        "denominator": str(Fraction(left_sum).denominator),
    }
    assert result["right"]["row_sum_pp"] == {
        "numerator": str(Fraction(right_sum).numerator),
        "denominator": str(Fraction(right_sum).denominator),
    }
    assert result["overlap_pp"] == {
        "numerator": str(Fraction(overlap).numerator),
        "denominator": str(Fraction(overlap).denominator),
    }
    assert result["matched_holdings"] == matches
    assert bundle == original
    assert json.loads(json.dumps(result)) == result
    ids = [candidate["document_id"] for candidate in bundle["candidates"]]
    assert reported_holdings_overlap(bundle, ids[1], ids[0])["overlap_pp"] == result["overlap_pp"]


@pytest.mark.parametrize(
    ("left", "right", "reason", "left_sum"),
    [
        (None, _rows(("X", "Holding X", 10)), "not_reported", None),
        ([], _rows(("X", "Holding X", 10)), "empty_holdings", None),
        (_rows(("X", "Alpha", 10)), _rows(("X", "Beta", 8)), "conflicting_holding_identity", "10"),
        (_rows(("X", "Alpha", 10)), _rows(("Y", "Alpha", 8)), "conflicting_holding_identity", "10"),
        (
            _rows(("X", "Holding X", 10), ("X", "Holding X two", 5)),
            _rows(("X", "Holding X", 8)),
            "duplicate_holding_symbol",
            "15",
        ),
        (
            _rows(("X", "Alpha", 10), ("Y", "Alpha", 5)),
            _rows(("Z", "Holding Z", 8)),
            "duplicate_holding_name",
            "15",
        ),
        (_rows((None, "Alpha", 10)), _rows(("X", "Alpha", 8)), "missing_holding_symbol", "10"),
        (
            _rows(("X", "Holding X", 60), ("Y", "Holding Y", 40.00000000000001)),
            _rows(("X", "Holding X", 10)),
            "invalid_holdings",
            None,
        ),
    ],
)
def test_unavailable_never_silently_reduces_overlap(
    left: Any, right: Any, reason: str, left_sum: str | None
) -> None:
    result = _result(_fixture(left, right))
    assert result["status"] == "unavailable"
    assert reason in result["reason_codes"]
    assert result["overlap_pp"] is None
    if left_sum is None:
        assert result["left"]["row_sum_pp"] is None
    else:
        assert result["left"]["row_sum_pp"]["numerator"] == left_sum


def test_provider_namespace_freshness_and_selection() -> None:
    rows = _rows(("X", "Holding X", 10))
    bundle = _fixture(rows, rows, providers=("one", "two"))
    assert "identity_namespace_mismatch" in _result(bundle)["reason_codes"]
    ids = [item["document_id"] for item in bundle["candidates"]]
    with pytest.raises(ValueError, match="distinct"):
        reported_holdings_overlap(bundle, ids[0], ids[0])
    bundle = _fixture(rows, rows, observed="2026-08-27T11:59:59.999999Z")
    assert "stale_holdings" in _result(bundle)["reason_codes"]
    assert _result(bundle)["left"]["row_sum_pp"] is None


@pytest.mark.parametrize(
    ("observed", "expected"),
    [
        ("2026-08-27T12:00:00Z", "available"),
        ("2026-08-28T12:05:00Z", "available"),
        ("2026-08-28T12:05:00.000001Z", "future_holdings"),
    ],
)
def test_ordinary_exact_freshness_boundaries(observed: str, expected: str) -> None:
    rows = _rows(("X", "Holding X", 10))
    result = _result(_fixture(rows, rows, observed=observed))
    if expected == "available":
        assert result["status"] == "available"
    else:
        assert expected in result["reason_codes"]


def test_actual_script_entry_selection_and_limit_text(monkeypatch: pytest.MonkeyPatch) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    from test_dashboard import paused_state_with_portfolio_and_explanation

    state = paused_state_with_portfolio_and_explanation()
    fixture = _fixture(_rows(("X", "Holding X", 10)), _rows(("X", "Holding X", 8)))
    before = deepcopy({key: value for key, value in state.items() if key != "__interrupt__"})
    actual_review_payload = dashboard.review_payload

    def review_with_fixture(state_value: dict[str, Any]) -> dict[str, Any]:
        result = actual_review_payload(state_value)
        result["candidate_evidence"] = fixture
        return result

    def fake_start(*args: Any, **kwargs: Any) -> DashboardRun:
        return DashboardRun(
            graph=None, config={"configurable": {"thread_id": "overlap-fixture"}}, state=state
        )

    monkeypatch.setattr(dashboard, "start_dashboard_run", fake_start)
    monkeypatch.setattr(dashboard, "review_payload", review_with_fixture)
    app = testing.AppTest.from_file(str(Path(dashboard_app.__file__))).run(timeout=60)
    next(item for item in app.sidebar.button if item.label == "Create review draft").click()
    app.run(timeout=60)
    assert not app.exception
    picker = next(
        item
        for item in app.multiselect
        if item.label == "Choose two candidates for reported-holdings overlap"
    )
    assert any("Reported holdings only; lists may be partial" in item.value for item in app.caption)
    assert any(
        "Choose two candidates to compare reported holdings" in item.value for item in app.info
    )
    ids = [candidate["document_id"] for candidate in fixture["candidates"]]
    picker.set_value([ids[0]])
    app.run(timeout=60)
    assert not app.exception
    assert any(
        "Choose two candidates to compare reported holdings" in item.value for item in app.info
    )
    picker = next(
        item
        for item in app.multiselect
        if item.label == "Choose two candidates for reported-holdings overlap"
    )
    picker.set_value(ids)
    app.run(timeout=60)
    assert not app.exception
    assert any("Reported overlap:" in str(item.value) for item in app.markdown)
    assert {key: value for key, value in state.items() if key != "__interrupt__"} == before
    fixture = _fixture(_rows(("X", "Holding X", 0)), _rows(("Y", "Holding Y", 8)))
    app.run(timeout=60)
    picker = next(
        item
        for item in app.multiselect
        if item.label == "Choose two candidates for reported-holdings overlap"
    )
    picker.set_value([candidate["document_id"] for candidate in fixture["candidates"]])
    app.run(timeout=60)
    assert not app.exception
    assert any("No overlap among these reported identities" in item.value for item in app.info)
    fixture = _fixture(_rows(("X", "Alpha", 10)), _rows(("X", "Beta", 8)))
    app.run(timeout=60)
    picker = next(
        item
        for item in app.multiselect
        if item.label == "Choose two candidates for reported-holdings overlap"
    )
    picker.set_value([candidate["document_id"] for candidate in fixture["candidates"]])
    app.run(timeout=60)
    assert not app.exception
    assert any("conflicting_holding_identity" in item.value for item in app.warning)
    assert (
        sum("Reported-row weight sum; identity unresolved" in item.value for item in app.caption)
        == 2
    )
    fixture = _fixture(
        _rows(("X", "Holding X", 10)),
        _rows(("X", "Holding X", 8)),
        observed="2026-08-27T11:59:59.999999Z",
    )
    app.run(timeout=60)
    picker = next(
        item
        for item in app.multiselect
        if item.label == "Choose two candidates for reported-holdings overlap"
    )
    picker.set_value([candidate["document_id"] for candidate in fixture["candidates"]])
    app.run(timeout=60)
    assert not app.exception
    assert any("stale_holdings" in item.value for item in app.warning)
    assert {key: value for key, value in state.items() if key != "__interrupt__"} == before


def test_half_up_and_subresolution() -> None:
    assert display_amount({"numerator": "1", "denominator": "2000000"}) == "<0.000001"
    assert display_amount({"numerator": "1", "denominator": "3000000"}) == "<0.000001"
    assert display_amount({"numerator": "3", "denominator": "5000000"}) == "<0.000001"
    assert display_amount({"numerator": "9", "denominator": "10000000"}) == "<0.000001"
    assert display_amount({"numerator": "1", "denominator": "1000000"}) == "≈ 0.000001"
    assert display_amount({"numerator": "3", "denominator": "2000000"}) == "≈ 0.000002"


def test_schema1_binary64_exact_sum_and_limits() -> None:
    rows = _rows(("X", "Holding X", 0.1), ("Y", "Holding Y", 0.2))
    bundle = _fixture(rows, rows)
    expected = Fraction.from_float(0.1) + Fraction.from_float(0.2)
    result = _result(bundle)
    assert result["overlap_pp"] == {
        "numerator": str(expected.numerator),
        "denominator": str(expected.denominator),
    }
    assert result["overlap_pp"] == {
        "numerator": "10808639105689191",
        "denominator": "36028797018963968",
    }
    too_many = _fixture(
        _rows(*[(f"H{index}", f"Holding {index}", 0.0) for index in range(1001)]), rows
    )
    assert "diagnostic_limit_exceeded" in _result(too_many)["reason_codes"]
    oversized = _fixture(rows, rows)
    oversized["candidates"][0]["metadata"]["field_provenance_json"] += " " * 1_048_576
    oversized_result = _result(oversized)
    assert oversized_result["reason_codes"] == ["diagnostic_limit_exceeded"]
    assert oversized_result["left"]["provider"] is None
    assert oversized_result["right"]["row_sum_pp"] is None


@pytest.mark.parametrize("bad", [True, "10", -1])
def test_schema1_rejects_non_numeric_and_invalid_weights(bad: Any) -> None:
    left = [{"symbol": "X", "name": "Holding X", "weight_pct": bad}]
    result = _result(_fixture(left, _rows(("X", "Holding X", 8))))
    assert result["status"] == "unavailable"
    assert "invalid_holdings" in result["reason_codes"]
    assert result["left"]["row_sum_pp"] is None
    assert result["right"]["row_sum_pp"] == {"numerator": "8", "denominator": "1"}


def test_corrupt_late_row_never_keeps_prefix_overlap() -> None:
    left = [
        *_rows(("X", "Holding X", 10)),
        {"symbol": "Y", "name": "Holding Y", "weight_pct": "bad"},
    ]
    result = _result(_fixture(left, _rows(("X", "Holding X", 8))))
    assert result["status"] == "unavailable"
    assert result["overlap_pp"] is None
    assert result["left"]["row_sum_pp"] is None
    assert result["right"]["row_sum_pp"] == {"numerator": "8", "denominator": "1"}


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite_source_payload_never_becomes_partial_overlap(bad: float) -> None:
    bundle = _fixture(_rows(("X", "Holding X", 10)), _rows(("X", "Holding X", 8)))
    raw = json.loads(bundle["candidates"][0]["metadata"]["field_provenance_json"])
    raw["top_holdings"]["value"][0]["weight_pct"] = bad
    bundle["candidates"][0]["metadata"]["field_provenance_json"] = json.dumps(raw)
    result = _result(bundle)
    assert result["status"] == "unavailable"
    assert result["overlap_pp"] is None


def test_duplicate_json_keys_and_provenance_conflict_fail_closed() -> None:
    rows = _rows(("X", "Holding X", 10))
    bundle = _fixture(rows, rows)
    raw = bundle["candidates"][0]["metadata"]["field_provenance_json"]
    bundle["candidates"][0]["metadata"]["field_provenance_json"] = raw.replace(
        '"unit": "percent_of_fund"', '"unit": "percent_of_fund", "unit": "percent_of_fund"'
    )
    assert _result(bundle)["status"] == "unavailable"
    bundle = _fixture(rows, rows)
    # Source-level field version is distinct from the published local-synthetic
    # version, but an explicit published metadata version cannot disagree.
    bundle["candidates"][0]["metadata"]["snapshot_version"] = "wrong"
    assert _result(bundle)["status"] == "unavailable"


def test_unpaired_surrogate_provenance_is_fixed_unavailable() -> None:
    rows = _rows(("X", "Holding X", 10))
    bundle = _fixture(rows, rows)
    bundle["candidates"][0]["metadata"]["field_provenance_json"] = "\ud800"
    result = _result(bundle)
    assert result["reason_codes"] == ["invalid_evidence"]
    assert result["left"]["row_sum_pp"] is None


def _schema2_bundle(weights: tuple[str, ...]) -> dict[str, Any]:
    snapshot = lossless_snapshot(symbols=("SPY", "VTI"))
    for record in snapshot.records:
        record.top_holdings.value = [
            WeightedExposure(
                name=f"Holding {index}",
                symbol=f"H{index}",
                weight_pct=upward(Decimal(weight)),
                source_weight_pct_decimal=decimal_token(Decimal(weight)),
            )
            for index, weight in enumerate(weights)
        ]
        record.top_10_concentration_pct.value = upward(sum(map(Decimal, weights)))
    docs = snapshot.to_source_documents()
    evidence = select_candidate_evidence(
        profile(),
        [
            GraphEnrichedSource(
                document_id=doc.document_id, content=doc.content, metadata=doc.chroma_metadata()
            )
            for doc in docs
        ],
        query="schema2 proof",
        checked_at=snapshot.ingested_at,
        max_age=timedelta(hours=24),
        limit=2,
    )
    return evidence.model_dump(mode="json")


@pytest.mark.parametrize(
    ("weights", "expected"),
    [
        (("1e-1", "2e-1"), Fraction(3, 10)),
        (("10000000000000001e-17",), Fraction(10000000000000001, 100000000000000000)),
    ],
)
def test_schema2_exact_decimal_proofs(weights: tuple[str, ...], expected: Fraction) -> None:
    bundle = _schema2_bundle(weights)
    result = _result(bundle)
    assert result["status"] == "available", result
    assert result["overlap_pp"] == {
        "numerator": str(expected.numerator),
        "denominator": str(expected.denominator),
    }
    if weights == ("10000000000000001e-17",):
        mutated = deepcopy(bundle)
        source = mutated["candidates"][0]["metadata"]["field_provenance_json"]
        assert "0.10000000000000002" in source
        mutated["candidates"][0]["metadata"]["field_provenance_json"] = source.replace(
            "0.10000000000000002", "0.1"
        )
        assert _result(mutated)["status"] == "unavailable"


def _bnd_bundle(delta: timedelta) -> dict[str, Any]:
    snapshot, _ = bnd_snapshot()
    check = BND_DATE + delta
    record = snapshot.records[0]
    for field in record.research_fields().values():
        if field.provider != "vanguard_advisors":
            field.observed_at = check
    other = record.model_copy(deep=True)
    other.symbol = "VTI"
    for field in other.research_fields().values():
        field.provider = "yahoo_finance"
        field.source_url = "https://example.test/vti"
        field.observed_at = check
    snapshot.records.append(other)
    docs = snapshot.to_source_documents()
    result = select_candidate_evidence(
        profile(),
        [
            GraphEnrichedSource(
                document_id=doc.document_id, content=doc.content, metadata=doc.chroma_metadata()
            )
            for doc in docs
        ],
        query="official bnd rows",
        checked_at=check,
        max_age=timedelta(hours=120),
        limit=2,
    )
    return result.model_dump(mode="json")


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (timedelta(hours=1080), "duplicate_holding_symbol"),
        (timedelta(hours=1080, microseconds=1), "stale_holdings"),
        (timedelta(microseconds=-1), "future_holdings"),
    ],
)
def test_official_bnd_rows_and_exact_age_boundary(delta: timedelta, expected: str) -> None:
    bundle = _bnd_bundle(delta)
    result = _result(bundle)
    assert result["status"] == "unavailable", result
    assert expected in result["reason_codes"]
    assert result["left"]["count"] == 10
    if expected == "duplicate_holding_symbol":
        assert result["left"]["row_sum_pp"] is not None
    else:
        assert result["left"]["row_sum_pp"] is None
