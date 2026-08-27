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
    assert document.document_id.startswith("yahoo-finance:spy:")
    assert document.chroma_metadata()["source_url"] == "https://finance.yahoo.com/quote/SPY/"
    assert document.chroma_metadata()["expense_ratio_pct"] == 0.03
    assert "Latest reported close: 512.34 USD" in document.content
    assert "Expense ratio: 0.03%" in document.content


def test_yahoo_adapter_fails_closed_when_history_is_empty() -> None:
    class EmptyTicker(FakeTicker):
        class EmptyHistory:
            empty = True

        def history(self, **kwargs: object) -> EmptyHistory:
            return self.EmptyHistory()

    adapter = YahooFinanceAdapter(ticker_factory=lambda symbol: EmptyTicker())

    with pytest.raises(MarketDataError, match="no price history"):
        adapter.fetch(["SPY"])
