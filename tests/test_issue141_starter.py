"""Synthetic starter contracts; no provider, registry or retrieval-store access."""

from __future__ import annotations

import json
import sys
from contextlib import nullcontext
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import etf_advisor.dashboard as dashboard
import etf_advisor.dashboard_app as dashboard_app
import etf_advisor.research.us_starter as starter
from etf_advisor.checkpoint import MemoryCheckpointStore
from etf_advisor.dashboard import DashboardOptions, review_payload
from etf_advisor.data.quality import assess_observations
from etf_advisor.data.yahoo_research import YahooResearchAdapter, _ExposureCollection, _RawResearch
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.rag.evidence import CandidateEvidenceBundle, PreparedStarterEvidenceRetriever
from etf_advisor.research.models import ETFResearchSnapshot, WeightedExposure

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def _stub_yfinance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep collector contract tests independent of the optional rag extra."""
    monkeypatch.setitem(sys.modules, "yfinance", ModuleType("yfinance"))


def _synthetic_artifact(tmp_path: Path) -> starter.StarterArtifact:
    holdings = _ExposureCollection(
        values=[
            WeightedExposure(
                name="Synthetic holding",
                symbol="SYN",
                weight_pct=10.0,
                source_weight_pct_decimal="1e1",
            )
        ],
        exact_weights=(Decimal("10"),),
    )
    adapter = YahooResearchAdapter(clock=lambda: NOW, ticker_factory=lambda _: None, max_attempts=1)
    outcomes = []
    records = []
    for index, symbol in enumerate(starter.starter_universe().symbols):
        category = "Intermediate Core Bond" if index >= 16 else "Large Blend"
        raw = _RawResearch(
            symbol=symbol,
            info={
                "symbol": symbol,
                "exchange": "PCX",
                "currency": "USD",
                "quoteType": "ETF",
                "market": "us_market",
                "longName": f"Synthetic {symbol}",
                "category": category,
                "fundFamily": "Synthetic",
                "netExpenseRatio": 0.1,
                "averageDailyVolume10Day": 200000,
            },
            fund_overview=None,
            fund_overview_error=False,
            top_holdings=holdings,
            top_holdings_error=False,
            sector_exposures=None,
            sector_exposures_error=False,
            observed_at=NOW,
        )
        records.append(adapter._build_record(raw, snapshot_version="us-starter-1", ingested_at=NOW))
        listing = starter.StarterListingProof(
            provider="yahoo_finance",
            symbol=symbol,
            exchange="PCX",
            quote_type="ETF",
            market="us_market",
            currency="USD",
            source_url=f"https://finance.yahoo.com/quote/{symbol}/",
            observed_at=NOW,
            collected_at=NOW,
        )
        outcomes.append(
            starter.StarterOutcome(
                symbol=symbol,
                status="collected",
                reason="synthetic_fixture",
                listing=listing,
                duplicate_group=f"yahoo_finance:PCX:{symbol}",
            )
        )
    snapshot = ETFResearchSnapshot(
        schema_version=2,
        snapshot_version="us-starter-1",
        universe_id="us-starter",
        universe_version="1",
        ingested_at=NOW,
        records=records,
    )
    plain = dict(
        schema="us-starter-artifact-v1",
        universe_id="us-starter",
        universe_version="1",
        universe_digest=starter.universe_digest(),
        members=starter.starter_universe().symbols,
        prepared_at=NOW.isoformat().replace("+00:00", "Z"),
        outcomes=[item.model_dump(mode="json") for item in outcomes],
        duplicate_assertions=[],
        snapshot=snapshot.model_dump(mode="json"),
    )
    artifact = starter.StarterArtifact.model_validate({**plain, "digest": starter._digest(plain)})
    path = tmp_path / f"{artifact.digest}.json"
    path.write_bytes(starter._canonical(artifact.model_dump(mode="json")))
    assert starter.StarterArtifact.load(path) == artifact
    return artifact


def _profile(artifact: starter.StarterArtifact) -> dict[str, object]:
    return dict(
        horizon_years=12,
        risk_tolerance="moderate",
        objective="balanced",
        max_drawdown_pct=25,
        initial_investment_usd=25000,
        recurring_monthly_usd=500,
        excluded_sectors=[],
        starter_request=starter.StarterRequestV1(
            schema="us-starter-request-v1",
            universe_digest=artifact.universe_digest,
            artifact_digest=artifact.digest,
        ).model_dump(mode="json"),
    )


def test_starter_profile_is_distinct_and_legacy_bytes_stay_absent() -> None:
    legacy = InvestorProfile.model_validate({key: value for key, value in _profile_stub().items()})
    assert "starter_request" not in legacy.model_dump(mode="json")
    for extra in (
        {"starter_request": None},
        {"starter_request": {}, "advisory_contract": "us-eu-v1"},
        {"starter_request": {}, "base_currency": "USD"},
    ):
        with pytest.raises(ValueError):
            InvestorProfile.model_validate({**_profile_stub(), **extra})


def _profile_stub() -> dict[str, object]:
    return dict(
        horizon_years=12,
        risk_tolerance="moderate",
        objective="balanced",
        max_drawdown_pct=25,
        initial_investment_usd=25000,
        recurring_monthly_usd=500,
        excluded_sectors=[],
    )


def test_starter_artifact_exact_identity_and_tamper(tmp_path: Path) -> None:
    artifact = _synthetic_artifact(tmp_path)
    payload = artifact.model_dump(mode="json")
    for mutation in (
        lambda p: p["outcomes"][0]["listing"].__setitem__("symbol", "WRONG"),
        lambda p: p["outcomes"][0]["listing"].__setitem__("exchange", "LSE"),
        lambda p: p["outcomes"][0].__setitem__("duplicate_group", "yahoo_finance:PCX:IVV"),
        lambda p: p["outcomes"].reverse(),
        lambda p: p.pop("schema"),
        lambda p: p["snapshot"]["records"][0].__setitem__("symbol", "WRONG"),
    ):
        changed = deepcopy(payload)
        mutation(changed)
        changed["digest"] = starter._digest(
            {key: val for key, val in changed.items() if key != "digest"}
        )
        with pytest.raises(ValueError):
            starter.StarterArtifact.model_validate(changed)


def test_normal_backend_full_pool_review_and_offline_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = _synthetic_artifact(tmp_path)
    original = PreparedStarterEvidenceRetriever
    monkeypatch.setattr(
        dashboard,
        "PreparedStarterEvidenceRetriever",
        lambda request, **kw: original(request, root=tmp_path, **kw),
    )
    monkeypatch.setattr(dashboard, "system_utc_now", lambda: NOW + timedelta(hours=1))
    monkeypatch.setattr(dashboard, "ChromaDocumentStore", lambda **_: pytest.fail("Chroma used"))
    monkeypatch.setattr(dashboard, "Neo4jGraphStore", lambda **_: pytest.fail("Neo4j used"))
    run = dashboard.start_dashboard_run(
        _profile(artifact), DashboardOptions(with_evidence=True, candidate_limit=10)
    )
    assert run.state["status"] == "awaiting_human_review"
    evidence = run.state["candidate_evidence"]
    construction = run.state["portfolio_construction"]
    assert len(evidence["candidates"]) == 20
    assert len(construction["starter_selection"]["dispositions"]) == 20
    assert len(construction["starter_selection"]["shortlist_ids"]) == 10
    assert len(construction["draft"]["positions"]) == 5
    review_payload(run.state)
    monkeypatch.setattr(Path, "read_bytes", lambda self: pytest.fail("offline file read"))
    monkeypatch.setattr(Path, "read_text", lambda self, **kw: pytest.fail("offline file read"))
    monkeypatch.setattr(dashboard, "system_utc_now", lambda: pytest.fail("offline clock read"))
    review_payload(run.state)
    for mutate in (
        lambda s: s["profile"].pop("starter_request"),
        lambda s: s["candidate_evidence"].pop("starter_context"),
        lambda s: s["candidate_evidence"]["starter_context"]["artifact"]["outcomes"][0][
            "listing"
        ].__setitem__("currency", "EUR"),
        lambda s: s["portfolio_construction"]["starter_selection"].pop("shortlist_ids"),
    ):
        state = deepcopy(run.state)
        mutate(state)
        with pytest.raises(ValueError):
            review_payload(state)


def test_starter_rejects_even_matching_graph_context(tmp_path: Path) -> None:
    artifact = _synthetic_artifact(tmp_path)
    profile = InvestorProfile.model_validate(_profile(artifact))
    assert profile.starter_request is not None
    retriever = PreparedStarterEvidenceRetriever(
        profile.starter_request,
        root=tmp_path,
        clock=lambda: NOW + timedelta(hours=1),
        max_age=timedelta(hours=120),
        future_tolerance=timedelta(minutes=5),
    )
    payload = retriever.retrieve(profile, limit=10).model_dump(mode="json")
    candidate = payload["candidates"][0]
    candidate["graph_context"] = dict(
        source_document_id=candidate["document_id"],
        schema_version=2,
        symbol=candidate["symbol"],
        etf_name=candidate["name"],
        fund_family=candidate["fund_family"],
        category=candidate["category"],
        sector_exposures_status="not_reported",
        sector_exposures=[],
    )
    with pytest.raises(ValueError, match="unsourced graph context"):
        CandidateEvidenceBundle.model_validate(payload)


def test_source_gate_uses_production_category_normalization(tmp_path: Path) -> None:
    import etf_advisor.data.starter_collection as collection
    from etf_advisor.research.models import ETFResearchRecord

    artifact = _synthetic_artifact(tmp_path)
    assert artifact.snapshot is not None
    record = artifact.snapshot.records[-1]
    changed = ETFResearchRecord.model_validate(
        record.model_copy(
            update={
                "category": record.category.model_copy(
                    update={"value": "  intermediate   CORE bond  "}
                )
            }
        ).model_dump(mode="python")
    )
    assert collection._classify(changed, NOW + timedelta(hours=1))[0] == "eligible_defensive"


def test_saved_starter_reload_uses_embedded_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = _synthetic_artifact(tmp_path)

    class DurableMemoryStore(MemoryCheckpointStore):
        durable = True

    store = DurableMemoryStore(clock=lambda: NOW + timedelta(hours=1))
    original = PreparedStarterEvidenceRetriever
    monkeypatch.setattr(
        dashboard,
        "PreparedStarterEvidenceRetriever",
        lambda request, **kw: original(request, root=tmp_path, **kw),
    )
    monkeypatch.setattr(dashboard, "PostgresCheckpointStore", lambda *args, **kw: store)
    monkeypatch.setattr(dashboard, "system_utc_now", lambda: NOW + timedelta(hours=1))
    created = dashboard.start_dashboard_run(
        _profile(artifact),
        DashboardOptions(with_evidence=True, candidate_limit=10, durable_checkpoint=True),
    )
    assert created.state["status"] == "awaiting_human_review"
    monkeypatch.setattr(Path, "read_bytes", lambda self: pytest.fail("offline file read"))
    monkeypatch.setattr(Path, "read_text", lambda self, **kw: pytest.fail("offline file read"))
    monkeypatch.setattr(dashboard, "system_utc_now", lambda: pytest.fail("source clock read"))
    monkeypatch.setattr(
        dashboard,
        "PreparedStarterEvidenceRetriever",
        lambda *args, **kw: pytest.fail("source retriever initialized"),
    )
    restored = dashboard.load_dashboard_run(created.thread_id, checkpoint_store=store)
    assert restored.state["candidate_evidence"] == created.state["candidate_evidence"]
    assert restored.state["portfolio_construction"] == created.state["portfolio_construction"]
    review_payload(restored.state)


def test_streamlit_collect_button_uses_fresh_root_without_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")
    import etf_advisor.data.starter_collection as source_gate

    calls: list[Path] = []

    def fake_run(root: Path) -> Path:
        calls.append(root)
        root.mkdir(parents=True)
        path = root / "pass.json"
        path.write_text('{"status":"complete"}', encoding="utf-8")
        return path

    monkeypatch.setattr(source_gate, "run_pass", fake_run)
    monkeypatch.setattr(starter, "prepare_from_pass", lambda path: path)
    monkeypatch.setattr(starter, "ARTIFACT_ROOT", tmp_path / "empty")
    app_path = Path(__file__).resolve().parents[1] / "src/etf_advisor/dashboard_app.py"
    app = streamlit_testing.AppTest.from_file(str(app_path)).run(timeout=30)
    next(item for item in app.sidebar.selectbox if item.label == "Advisory scope").set_value(
        "Curated US starter"
    ).run(timeout=30)
    next(
        item for item in app.sidebar.button if item.label == "Collect current starter data"
    ).click().run(timeout=30)
    assert len(calls) == 1
    assert calls[0].parent == Path(".artifacts/issue141-source-runs")
    assert not app.error


def test_starter_preparation_selects_exact_second_artifact_with_same_display_minute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _synthetic_artifact(tmp_path)
    plain = first.model_dump(mode="json", exclude={"digest"})
    plain["prepared_at"] = (NOW + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    second = starter.StarterArtifact.model_validate({**plain, "digest": starter._digest(plain)})
    (tmp_path / f"{second.digest}.json").write_bytes(
        starter._canonical(second.model_dump(mode="json"))
    )
    monkeypatch.setattr(dashboard_app, "ARTIFACT_ROOT", tmp_path)

    class Picker:
        def caption(self, _: str) -> None:
            pass

        def button(self, _: str) -> bool:
            return False

        def selectbox(self, _: str, options: list[str], *, format_func: object) -> str:
            assert set(options) == {first.digest, second.digest}
            assert options[0] != options[1]
            labels = [format_func(option) for option in options]  # type: ignore[operator]
            assert all(
                "Collected 20/20 · prepared 2026-11-05 12:00 UTC" in label for label in labels
            )
            assert labels[0] != labels[1]
            return second.digest

    request = dashboard_app._render_starter_preparation(Picker())
    assert request is not None
    assert request.artifact_digest == second.digest
    assert request.artifact_digest != first.digest


@pytest.mark.parametrize("scenario", ["stale", "future", "mixed"])
def test_starter_counts_show_current_health_before_historical_pass(
    tmp_path: Path, scenario: str
) -> None:
    artifact = _synthetic_artifact(tmp_path)
    payload = artifact.model_dump(mode="json")
    outcomes = payload["outcomes"]
    if scenario == "mixed":
        outcomes[-2]["status"] = "failed"
        outcomes[-2]["reason"] = "source_error"
        outcomes[-1]["status"] = "unattempted"
        outcomes[-1]["reason"] = "pass_stopped"
    check = NOW + timedelta(days=10) if scenario == "stale" else NOW - timedelta(hours=1)
    if scenario == "mixed":
        check = NOW + timedelta(hours=1)
    if scenario == "mixed":
        observations = []
        for index, outcome in enumerate(outcomes):
            if outcome["status"] != "collected":
                continue
            observed = NOW - timedelta(days=6) if index == 0 else NOW
            observations.append(
                SimpleNamespace(
                    symbol=outcome["symbol"],
                    source="yahoo_finance",
                    source_url=f"https://finance.yahoo.com/quote/{outcome['symbol']}/",
                    observed_at=observed,
                )
            )
        health = assess_observations(
            observations, checked_at=check, max_age=timedelta(hours=120)
        ).model_dump(mode="json")
    else:
        request = InvestorProfile.model_validate(_profile(artifact)).starter_request
        assert request is not None
        bundle = PreparedStarterEvidenceRetriever(
            request,
            root=tmp_path,
            clock=lambda: check,
            max_age=timedelta(hours=120),
            future_tolerance=timedelta(minutes=5),
        ).retrieve(InvestorProfile.model_validate(_profile(artifact)), limit=10)
        assert bundle.status == "blocked"
        health = bundle.health.model_dump(mode="json")
    state = {
        "candidate_evidence": {
            "status": "blocked",
            "starter_context": {"artifact": payload},
            "health": health,
        },
        "candidate_screening": (
            {"candidates": [{"symbol": outcomes[0]["symbol"], "verdict": "fail"}]}
            if scenario == "mixed"
            else {}
        ),
        "portfolio_construction": {},
    }

    class Display:
        def __init__(self) -> None:
            self.counts: dict[str, int] = {}
            self.rows: list[dict[str, str]] = []

        def subheader(self, _: str) -> None:
            pass

        def write(self, value: dict[str, int]) -> None:
            self.counts = value

        def dataframe(self, rows: list[dict[str, str]], *, hide_index: bool) -> None:
            assert hide_index
            self.rows = rows

        def caption(self, _: str) -> None:
            pass

    display = Display()
    dashboard_app._render_starter_counts(display, state)
    assert len(display.rows) == 20
    assert display.counts["screened"] == 0
    assert display.counts["eligible"] == 0
    assert not any("existing_category_and_thresholds_pass" in row["Reason"] for row in display.rows)
    if scenario == "mixed":
        assert display.counts["excluded"] == 3
        assert display.counts["not_screened"] == 17
        assert display.rows[0]["Source"] == "stale"
        assert "hours old" in display.rows[0]["Reason"]
        assert display.rows[1]["Reason"] == "Not screened: source bundle blocked"
        assert display.rows[-2]["Reason"] == "source_error"
        assert display.rows[-1]["Reason"] == "pass_stopped"
    else:
        assert display.counts["excluded"] == 20
        assert display.counts["not_screened"] == 0
        assert {row["Source"] for row in display.rows} == {scenario}
        assert all("observation is" in row["Reason"] for row in display.rows)


def test_starter_counts_keep_ready_screening_and_shortlist_reasons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = _synthetic_artifact(tmp_path)
    original = PreparedStarterEvidenceRetriever
    monkeypatch.setattr(
        dashboard,
        "PreparedStarterEvidenceRetriever",
        lambda request, **kw: original(request, root=tmp_path, **kw),
    )
    monkeypatch.setattr(dashboard, "system_utc_now", lambda: NOW + timedelta(hours=1))
    run = dashboard.start_dashboard_run(
        _profile(artifact), DashboardOptions(with_evidence=True, candidate_limit=10)
    )
    assert run.state["status"] == "awaiting_human_review"
    counts: list[dict[str, int]] = []
    rows: list[list[dict[str, str]]] = []
    display = SimpleNamespace(
        subheader=lambda _: None,
        write=counts.append,
        dataframe=lambda value, **_: rows.append(value),
        caption=lambda _: None,
    )
    dashboard_app._render_starter_counts(display, run.state)
    screening = run.state["candidate_screening"]["candidates"]
    dispositions = run.state["portfolio_construction"]["starter_selection"]["dispositions"]
    assert counts[0]["requested"] == counts[0]["screened"] == 20
    assert counts[0]["eligible"] == sum(item["verdict"] == "pass" for item in screening)
    assert counts[0]["excluded"] == sum(item["verdict"] != "pass" for item in screening)
    assert counts[0]["not_screened"] == 0
    by_symbol = {row["Fund"]: row for row in rows[0]}
    for item in dispositions:
        assert by_symbol[item["symbol"]]["Reason"] == item["reason"]
        assert by_symbol[item["symbol"]]["Source"] == "current"


@pytest.mark.parametrize(
    "bad_field,bad_value,reason",
    [
        ("symbol", "ALIAS", "returned_symbol_mismatch"),
        ("exchange", "LSE", "unmapped_us_exchange"),
        ("quoteType", "EQUITY", "non_us_etf_identity"),
        ("market", "gb_market", "non_us_etf_identity"),
        ("currency", "EUR", "non_usd_quote_currency"),
    ],
)
def test_collector_checks_returned_listing_before_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_field: str,
    bad_value: str,
    reason: str,
) -> None:
    import etf_advisor.data.starter_collection as collection

    _stub_yfinance(monkeypatch)

    monkeypatch.setattr(collection, "bounded_yahoo_session", lambda budget: object())
    monkeypatch.setattr(collection, "restore_yahoo_data_session", nullcontext)
    monkeypatch.setattr(
        collection, "_classify", lambda record, checked_at: ("eligible_growth", "fixture")
    )

    class FakeAdapter:
        def __init__(self, **kwargs: object) -> None:
            pass

        def _fetch_one(self, symbol: str) -> SimpleNamespace:
            info = dict(
                symbol=symbol, exchange="PCX", quoteType="ETF", market="us_market", currency="USD"
            )
            if symbol == "BND":
                info[bad_field] = bad_value
            return SimpleNamespace(info=info, observed_at=NOW)

        def _build_record(self, raw: object, **kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(model_dump=lambda **_: {"fixture": True})

    monkeypatch.setattr(collection, "YahooResearchAdapter", FakeAdapter)
    path = collection.run_pass(tmp_path / "fresh-run")
    state = json.loads(path.read_text(encoding="utf-8"))
    assert len(state["outcomes"]) == 20
    assert state["outcomes"][0]["symbol"] == "BND"
    assert state["outcomes"][0]["status"] == "failed"
    assert state["outcomes"][0]["reason"] == reason
    assert state["outcomes"][0]["requests"] <= 12
    assert state["status"] == "blocked_no_eligible_defensive"
    assert sum(item["status"] == "unattempted" for item in state["outcomes"]) == 16
    with pytest.raises(ValueError, match="already_exists"):
        collection.run_pass(path.parent)


def test_collector_terminal_transport_stop_retains_unattempted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import etf_advisor.data.starter_collection as collection
    from etf_advisor.data.yahoo_budget import YahooBudgetError

    _stub_yfinance(monkeypatch)

    def blocked(_: object) -> object:
        raise YahooBudgetError("unreviewed_curl_transport")

    monkeypatch.setattr(collection, "bounded_yahoo_session", blocked)
    monkeypatch.setattr(collection, "restore_yahoo_data_session", nullcontext)
    path = collection.run_pass(tmp_path / "terminal-run")
    state = json.loads(path.read_text(encoding="utf-8"))
    assert state["status"] == "transport_blocked"
    assert state["outcomes"][0]["reason"] == "unreviewed_curl_transport"
    assert sum(item["status"] == "unattempted" for item in state["outcomes"]) == 19


def test_collector_authentication_failure_stops_without_raw_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import etf_advisor.data.starter_collection as collection

    _stub_yfinance(monkeypatch)

    class ProviderFailure(Exception):
        response = SimpleNamespace(status_code=401)

    class FakeAdapter:
        def __init__(self, **kwargs: object) -> None:
            pass

        def _fetch_one(self, symbol: str) -> None:
            raise ProviderFailure("raw provider body must not be saved")

    monkeypatch.setattr(collection, "bounded_yahoo_session", lambda budget: object())
    monkeypatch.setattr(collection, "restore_yahoo_data_session", nullcontext)
    monkeypatch.setattr(collection, "YahooResearchAdapter", FakeAdapter)
    path = collection.run_pass(tmp_path / "auth-run")
    raw = path.read_text(encoding="utf-8")
    state = json.loads(raw)
    assert state["status"] == "transport_blocked"
    assert state["outcomes"][0]["reason"] == "provider_authentication_failure"
    assert "raw provider body" not in raw
    assert sum(item["status"] == "unattempted" for item in state["outcomes"]) == 19
