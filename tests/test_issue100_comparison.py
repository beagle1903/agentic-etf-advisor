"""Issue 100 comparison remains an attributed, read-only UI projection."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from test_dashboard import paused_state_with_portfolio_and_explanation

import etf_advisor.dashboard as dashboard
import etf_advisor.dashboard_app as dashboard_app
from etf_advisor.dashboard import DashboardRun
from etf_advisor.dashboard_comparison import comparison_rows
from etf_advisor.data.vanguard import BND_URL, PROVIDER


def _field(value: Any, unit: str, *, observed: str = "2026-10-24T12:00:00Z") -> dict[str, Any]:
    return {
        "value": value,
        "unit": unit,
        "provider": "fixture_provider",
        "source_url": "https://example.test/field",
        "observed_at": observed,
        "missing_reason": None if value is not None else "not_reported",
    }


def _bundle(schema: int = 1) -> dict[str, Any]:
    fields = {
        "expense_ratio_pct": _field("0.10000000000000002" if schema == 2 else 0.1, "percent"),
        "average_daily_volume": _field("0.0" if schema == 2 else 0, "shares_per_day"),
        "category": _field("Large Blend", "classification"),
        "benchmark": _field("Index A", "classification"),
        "top_holdings": _field(
            [
                {
                    "name": "Holding A",
                    **(
                        {
                            "weight_pct_token": "12.300000000000002",
                            "source_weight_pct_decimal": "12.3",
                        }
                        if schema == 2
                        else {"weight_pct": 12.3}
                    ),
                }
            ],
            "percent_of_fund",
        ),
        "sector_exposures": _field(None, "percent_of_fund"),
        "geography_exposures": _field([], "percent_of_fund"),
        "top_10_concentration_pct": _field(
            "12.300000000000002" if schema == 2 else 12.3, "percent"
        ),
    }
    metadata: dict[str, Any] = {
        "field_provenance_json": json.dumps(fields),
        "expense_ratio_pct": fields["expense_ratio_pct"]["value"],
        "average_daily_volume": fields["average_daily_volume"]["value"],
        "category": "Large Blend",
        "benchmark": "Index A",
        "top_10_concentration_pct": fields["top_10_concentration_pct"]["value"],
    }
    if schema == 2:
        metadata.update(
            {"field_provenance_schema_version": 2, "numeric_encoding": "binary64-text-v1"}
        )
    return {
        "checked_at": "2026-10-24T13:00:00Z",
        "health": {"max_age_hours": 24, "future_tolerance_minutes": 5},
        "candidates": [
            {
                "document_id": "research:fixture:cspx.as",
                "symbol": "CSPX.AS",
                "category": "Large Blend",
                "metadata": metadata,
            },
            {
                "document_id": "research:fixture:vwce.de",
                "symbol": "VWCE.DE",
                "category": "Large Blend",
                "metadata": deepcopy(metadata),
            },
        ],
    }


@pytest.mark.parametrize("schema", [1, 2])
def test_exact_field_values_gaps_zero_and_arbitrary_membership(schema: int) -> None:
    bundle = _bundle(schema)
    before = deepcopy(bundle)
    selected = [bundle["candidates"][1]["document_id"], bundle["candidates"][0]["document_id"]]
    rows = comparison_rows(bundle, selected)
    assert len(rows) == 16
    assert [row["Symbol"] for row in rows[::8]] == ["VWCE.DE", "CSPX.AS"]
    assert rows[1]["Value"] == ("0.0" if schema == 2 else "0")
    assert rows[1]["Status"] == "supported"
    assert rows[5]["Value"] == "Unavailable" and rows[5]["Status"] == "not_reported"
    assert rows[0]["Source"] == "fixture_provider"
    assert rows[0]["Source URL"] == "https://example.test/field"
    assert rows[0]["Observed (UTC)"] == "2026-10-24T12:00:00Z"
    assert rows[0]["Unit"] == "percent"
    if schema == 2:
        assert rows[0]["Value"] == "0.10000000000000002"
        assert "12.300000000000002% (source decimal 12.3)" in rows[4]["Value"]
    else:
        assert rows[0]["Value"] == "0.1"
        assert "source decimal" not in rows[4]["Value"]
    assert bundle == before
    with pytest.raises(ValueError, match="validated candidates"):
        comparison_rows(bundle, ["SPY"])


def test_missing_stale_future_conflict_and_absent_provenance_are_not_facts() -> None:
    bundle = _bundle()
    fields = json.loads(bundle["candidates"][0]["metadata"]["field_provenance_json"])
    fields["expense_ratio_pct"]["observed_at"] = "2026-10-22T12:00:00Z"
    fields["average_daily_volume"]["observed_at"] = "2026-10-25T12:00:00Z"
    fields["category"]["value"] = "Different category"
    fields["benchmark"]["source_url"] = ""
    del fields["top_holdings"]
    bundle["candidates"][0]["metadata"]["field_provenance_json"] = json.dumps(fields)
    rows = comparison_rows(bundle, [bundle["candidates"][0]["document_id"]])
    assert [row["Status"] for row in rows[:5]] == [
        "stale observation",
        "future observation",
        "conflicting evidence",
        "missing provenance",
        "missing provenance",
    ]
    assert all(row["Value"] == "Unavailable" for row in rows[:5])


def test_official_bnd_pair_uses_existing_monthly_window_and_zero_future_tolerance() -> None:
    bundle = _bundle(2)
    candidate = bundle["candidates"][0]
    candidate["symbol"] = "BND"
    fields = json.loads(candidate["metadata"]["field_provenance_json"])
    for name in ("top_holdings", "top_10_concentration_pct"):
        fields[name]["provider"] = PROVIDER
        fields[name]["source_url"] = BND_URL
        fields[name]["observed_at"] = "2026-09-24T00:00:00Z"
    candidate["metadata"]["field_provenance_json"] = json.dumps(fields)
    rows = comparison_rows(bundle, [candidate["document_id"]])
    assert rows[4]["Status"] == rows[7]["Status"] == "supported"
    assert rows[0]["Status"] == "supported"
    fields["top_holdings"]["observed_at"] = "2026-08-01T00:00:00Z"
    fields["top_10_concentration_pct"]["observed_at"] = "2026-08-01T00:00:00Z"
    candidate["metadata"]["field_provenance_json"] = json.dumps(fields)
    rows = comparison_rows(bundle, [candidate["document_id"]])
    assert rows[4]["Status"] == rows[7]["Status"] == "stale observation"
    fields["top_holdings"]["observed_at"] = "2026-10-24T13:01:00Z"
    fields["top_10_concentration_pct"]["observed_at"] = "2026-10-24T13:01:00Z"
    candidate["metadata"]["field_provenance_json"] = json.dumps(fields)
    rows = comparison_rows(bundle, [candidate["document_id"]])
    assert rows[4]["Status"] == rows[7]["Status"] == "future observation"


def test_actual_streamlit_script_renders_selection_and_limits_without_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    state = paused_state_with_portfolio_and_explanation()
    before = deepcopy({key: value for key, value in state.items() if key != "__interrupt__"})
    calls = 0

    def fake_start(*args: Any, **kwargs: Any) -> DashboardRun:
        nonlocal calls
        calls += 1
        return DashboardRun(
            graph=None,
            config={"configurable": {"thread_id": "comparison-fixture"}},
            state=state,
        )

    monkeypatch.setattr(dashboard, "start_dashboard_run", fake_start)
    app = testing.AppTest.from_file(str(Path(dashboard_app.__file__))).run(timeout=60)
    next(button for button in app.sidebar.button if button.label == "Create review draft").click()
    app.run(timeout=60)
    assert not app.exception
    chooser = next(
        (item for item in app.multiselect if item.label == "Choose candidates to compare"),
        None,
    )
    assert chooser is not None, (
        [item.value for item in app.error],
        [item.value for item in app.warning],
        [item.value for item in app.info],
        type(app.session_state["dashboard_run"]).__name__,
        calls,
    )
    ids = [item["document_id"] for item in state["candidate_evidence"]["candidates"]]
    chooser.set_value([ids[4], ids[0]])
    app.run(timeout=60)
    assert not app.exception
    assert any("Source coverage is not eligibility" in item.value for item in app.caption)
    assert any("BND" in str(item.value) and "SPY" in str(item.value) for item in app.dataframe)
    assert calls == 1
    assert {key: value for key, value in state.items() if key != "__interrupt__"} == before
