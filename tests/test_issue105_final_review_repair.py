"""Frozen final-review regressions for Yahoo session lifetime."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from etf_advisor.data.reference_facts import LocalReferenceFacts
from etf_advisor.data.yahoo_budget import YAHOO_SESSION_LOCK, YahooBudgetError, YahooRequestBudget
from etf_advisor.data.yahoo_research import YahooCatalogueResearchCollector, YahooResearchAdapter


@pytest.mark.parametrize("attempt_fails", [False, True])
@pytest.mark.parametrize("preexisting", [False, True])
def test_catalogue_attempt_does_not_poison_later_ordinary_yahoo_research(
    monkeypatch: pytest.MonkeyPatch, attempt_fails: bool, preexisting: bool
) -> None:
    import curl_cffi.requests
    import yfinance as yf
    from test_issue105_catalogue import _isin
    from test_us_eu_contract import _record
    from yfinance.data import SingletonMeta, YfData

    with YAHOO_SESSION_LOCK:
        original_instances = dict(SingletonMeta._instances)
        original_state = {cls: dict(vars(instance)) for cls, instance in original_instances.items()}
        if not preexisting:
            SingletonMeta._instances.pop(YfData, None)
        prior_session = YfData()._session if preexisting else None
        now = datetime(2026, 10, 24, 8, tzinfo=UTC)
        budget = YahooRequestBudget(deadline=60.0, max_requests=1, monotonic=lambda: 0.0)
        catalogue_sessions = []
        network_calls = []

        def offline_request(self, method, url, **kwargs):
            network_calls.append((self, method, url))
            return SimpleNamespace(content=b"offline")

        def fake_fetch(self, symbol):
            ticker = self._ticker_factory(symbol)
            catalogue_sessions.append(ticker._data._session)
            if attempt_fails:
                budget.before_request()
                budget.before_request()
            return SimpleNamespace(info={"exchange": "PCX"}, top_holdings=object())

        monkeypatch.setattr(curl_cffi.requests.Session, "request", offline_request)
        monkeypatch.setattr(YahooResearchAdapter, "_fetch_one", fake_fetch)
        monkeypatch.setattr(
            YahooResearchAdapter,
            "_build_record",
            lambda self, raw, *, snapshot_version, ingested_at: _record(
                "BND", "PCX", "USD", "Large Blend", _isin(999)
            ),
        )
        try:
            collector = YahooCatalogueResearchCollector()
            listing = SimpleNamespace(symbol="BND", exchange="PCX")
            if attempt_fails:
                with pytest.raises(YahooBudgetError):
                    collector.collect(
                        listing,
                        "catalogue-test",
                        LocalReferenceFacts({}),
                        budget,
                        clock=lambda: now,
                    )
                assert budget.breached
            else:
                assert (
                    collector.collect(
                        listing,
                        "catalogue-test",
                        LocalReferenceFacts({}),
                        budget,
                        clock=lambda: now,
                    ).symbol
                    == "BND"
                )
            assert len(catalogue_sessions) == 1
            assert catalogue_sessions[0] is not prior_session
            ordinary = YahooResearchAdapter(clock=lambda: now)._ticker_factory("SPY")
            assert isinstance(ordinary, yf.Ticker)
            if preexisting:
                assert ordinary._data._session is prior_session
            else:
                assert ordinary._data._session is not catalogue_sessions[0]
            assert (
                ordinary._data._session.request("GET", "https://example.invalid").content
                == b"offline"
            )
            assert len(network_calls) == 1
        finally:
            SingletonMeta._instances.clear()
            SingletonMeta._instances.update(original_instances)
            for cls, state in original_state.items():
                original_instances[cls].__dict__.clear()
                original_instances[cls].__dict__.update(state)
