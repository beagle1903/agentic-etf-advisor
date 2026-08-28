from datetime import UTC, datetime
from typing import ClassVar

import pytest

from etf_advisor.data.yahoo import MarketDataError, YahooFinanceAdapter


class FakeRow:
    def __getitem__(self, key: str) -> float:
        if key != "Close":
            raise KeyError(key)
        return 512.34


class FakeIloc:
    def __getitem__(self, index: int) -> FakeRow:
        if index != -1:
            raise IndexError(index)
        return FakeRow()


class FakeHistory:
    empty: ClassVar[bool] = False
    iloc: ClassVar[FakeIloc] = FakeIloc()
    index: ClassVar[list[datetime]] = [datetime(2026, 8, 26, 20, 0, tzinfo=UTC)]


class FakeTicker:
    info: ClassVar[dict[str, object]] = {
        "longName": "Fake Broad Market ETF",
        "currency": "USD",
        "quoteType": "ETF",
        "market": "us_market",
        "category": "Large Blend",
        "fundFamily": "Example Funds",
        "netExpenseRatio": 0.03,
        "longBusinessSummary": "A test-only source description.",
    }

    def history(self, **kwargs: object) -> FakeHistory:
        assert kwargs == {"period": "5d", "interval": "1d", "auto_adjust": False}
        return FakeHistory()


def test_yahoo_adapter_normalizes_and_preserves_provenance() -> None:
    adapter = YahooFinanceAdapter(ticker_factory=lambda symbol: FakeTicker())

    observation = adapter.fetch(["spy", "SPY"])[0]
    document = adapter.to_source_document(observation)

    assert observation.symbol == "SPY"
    assert observation.close_price == 512.34
    assert observation.observed_at.tzinfo == UTC
    assert observation.expense_ratio_pct == 0.03
    assert observation.market == "us_market"
    assert document.document_id.startswith("yahoo-finance:spy:")
    assert document.chroma_metadata()["source_url"] == "https://finance.yahoo.com/quote/SPY/"
    assert document.chroma_metadata()["expense_ratio_pct"] == 0.03
    assert document.chroma_metadata()["quote_type"] == "ETF"
    assert document.chroma_metadata()["market"] == "us_market"
    assert "Latest reported close: 512.34 USD" in document.content
    assert "Expense ratio: 0.03%" in document.content


def test_yahoo_adapter_converts_annual_report_expense_ratio_fraction() -> None:
    class AnnualReportFallbackTicker(FakeTicker):
        info: ClassVar[dict[str, object]] = {
            **FakeTicker.info,
            "netExpenseRatio": None,
            "annualReportExpenseRatio": 0.0003,
        }

    adapter = YahooFinanceAdapter(ticker_factory=lambda symbol: AnnualReportFallbackTicker())

    observation = adapter.fetch(["SPY"])[0]
    document = adapter.to_source_document(observation)

    assert observation.expense_ratio_pct == pytest.approx(0.03)
    assert document.chroma_metadata()["expense_ratio_pct"] == pytest.approx(0.03)
    assert "Expense ratio: 0.03%" in document.content


def test_yahoo_adapter_prefers_net_expense_ratio_percentage_points() -> None:
    class BothExpenseRatiosTicker(FakeTicker):
        info: ClassVar[dict[str, object]] = {
            **FakeTicker.info,
            "netExpenseRatio": 0.03,
            "annualReportExpenseRatio": 0.0004,
        }

    adapter = YahooFinanceAdapter(ticker_factory=lambda symbol: BothExpenseRatiosTicker())

    assert adapter.fetch(["SPY"])[0].expense_ratio_pct == 0.03


def test_yahoo_adapter_fails_closed_when_history_is_empty() -> None:
    class EmptyTicker(FakeTicker):
        class EmptyHistory:
            empty = True

        def history(self, **kwargs: object) -> EmptyHistory:
            return self.EmptyHistory()

    adapter = YahooFinanceAdapter(
        ticker_factory=lambda symbol: EmptyTicker(),
        max_attempts=1,
    )

    with pytest.raises(MarketDataError, match="no price history"):
        adapter.fetch(["SPY"])


def test_yahoo_adapter_retries_transient_failures_with_injected_sleeper() -> None:
    attempts = 0
    delays: list[float] = []

    def flaky_factory(symbol: str) -> FakeTicker:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OSError("temporary upstream failure")
        return FakeTicker()

    adapter = YahooFinanceAdapter(
        ticker_factory=flaky_factory,
        max_attempts=3,
        retry_backoff_seconds=0.5,
        sleeper=delays.append,
    )

    assert adapter.fetch(["SPY"])[0].symbol == "SPY"
    assert attempts == 3
    assert delays == [0.5, 1.0]


def test_yahoo_adapter_reports_exhausted_attempt_count() -> None:
    delays: list[float] = []

    def failing_factory(symbol: str) -> FakeTicker:
        raise OSError("upstream unavailable")

    adapter = YahooFinanceAdapter(
        ticker_factory=failing_factory,
        max_attempts=2,
        retry_backoff_seconds=0.25,
        sleeper=delays.append,
    )

    with pytest.raises(MarketDataError, match=r"after 2 attempt\(s\)"):
        adapter.fetch(["SPY"])
    assert delays == [0.25]


def test_yahoo_adapter_retries_transient_metadata_failures() -> None:
    metadata_attempts = 0
    delays: list[float] = []

    class FlakyMetadataTicker(FakeTicker):
        @property
        def info(self) -> dict[str, object]:
            nonlocal metadata_attempts
            metadata_attempts += 1
            if metadata_attempts < 3:
                raise OSError("temporary metadata failure")
            return FakeTicker.info

    adapter = YahooFinanceAdapter(
        ticker_factory=lambda symbol: FlakyMetadataTicker(),
        max_attempts=3,
        retry_backoff_seconds=0.5,
        sleeper=delays.append,
    )

    observation = adapter.fetch(["SPY"])[0]

    assert observation.category == "Large Blend"
    assert observation.fund_family == "Example Funds"
    assert metadata_attempts == 3
    assert delays == [0.5, 1.0]


def test_yahoo_adapter_fails_closed_when_metadata_retries_are_exhausted() -> None:
    delays: list[float] = []

    class FailingMetadataTicker(FakeTicker):
        @property
        def info(self) -> dict[str, object]:
            raise OSError("metadata unavailable")

    adapter = YahooFinanceAdapter(
        ticker_factory=lambda symbol: FailingMetadataTicker(),
        max_attempts=2,
        retry_backoff_seconds=0.25,
        sleeper=delays.append,
    )

    with pytest.raises(MarketDataError, match=r"metadata failed.*after 2 attempt\(s\)"):
        adapter.fetch(["SPY"])
    assert delays == [0.25]


def test_yahoo_adapter_accepts_successful_metadata_with_absent_fields() -> None:
    class MissingMetadataTicker(FakeTicker):
        info: ClassVar[dict[str, object]] = {}

    adapter = YahooFinanceAdapter(
        ticker_factory=lambda symbol: MissingMetadataTicker(),
        sleeper=lambda delay: None,
    )

    observation = adapter.fetch(["SPY"])[0]

    assert observation.name == "SPY"
    assert observation.category is None
    assert observation.fund_family is None
    assert observation.expense_ratio_pct is None
