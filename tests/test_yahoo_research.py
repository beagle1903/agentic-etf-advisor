from datetime import UTC, datetime
from typing import ClassVar

import pytest

from etf_advisor.data.yahoo import MarketDataError
from etf_advisor.data.yahoo_research import YahooResearchAdapter
from etf_advisor.research.models import MissingReason
from etf_advisor.research.universe import ResearchUniverse, UniverseMember


class FakeFundsData:
    fund_overview: ClassVar[dict[str, object]] = {
        "categoryName": "Large Blend",
        "family": "Example Funds",
    }
    top_holdings: ClassVar[list[dict[str, object]]] = [
        {"Symbol": "AAA", "Name": "Alpha Corp", "Holding Percent": 0.12},
        {"Symbol": "BBB", "Name": "Beta Corp", "Holding Percent": 0.08},
    ]
    sector_weightings: ClassVar[dict[str, float]] = {
        "technology": 0.3,
        "financial_services": 0.2,
    }


class FakeTicker:
    info: ClassVar[dict[str, object]] = {
        "longName": "Example Broad Market ETF",
        "quoteType": "ETF",
        "market": "us_market",
        "category": "Large Blend",
        "fundFamily": "Example Funds",
        "indexName": "Example Broad Market Index",
        "netExpenseRatio": 0.03,
        "averageDailyVolume10Day": 10_000_000,
        "regularMarketTime": int(datetime(2026, 8, 29, 11, 55, tzinfo=UTC).timestamp()),
    }
    funds_data: ClassVar[FakeFundsData] = FakeFundsData()


def one_member_universe() -> ResearchUniverse:
    return ResearchUniverse(
        universe_id="test-universe",
        universe_version="1.0.0",
        members=[UniverseMember(symbol="spy", role="test role")],
    )


def test_yahoo_research_adapter_builds_rich_field_level_provenance() -> None:
    instants = iter([datetime(2026, 8, 29, 12, 1, tzinfo=UTC)])
    adapter = YahooResearchAdapter(
        clock=lambda: next(instants),
        ticker_factory=lambda symbol: FakeTicker(),
    )

    snapshot = adapter.fetch_snapshot(one_member_universe(), snapshot_version="snapshot-v1")
    record = snapshot.records[0]

    assert record.symbol == "SPY"
    assert record.benchmark.value == "Example Broad Market Index"
    assert record.expense_ratio_pct.value == 0.03
    assert record.average_daily_volume.value == 10_000_000
    assert record.average_daily_volume.unit == "shares_per_day"
    assert record.top_holdings.value is not None
    assert record.top_holdings.value[0].weight_pct == 12
    assert record.sector_exposures.value is not None
    assert record.top_10_concentration_pct.value == 20
    assert record.geography_exposures.value is None
    assert record.geography_exposures.missing_reason == MissingReason.PROVIDER_UNSUPPORTED
    for field in record.research_fields().values():
        assert field.snapshot_version == "snapshot-v1"
        assert field.ingested_at == snapshot.ingested_at
        assert field.observed_at == datetime(2026, 8, 29, 11, 55, tzinfo=UTC)
        assert field.source_url == "https://finance.yahoo.com/quote/SPY/"


def test_yahoo_research_adapter_preserves_tolerable_future_source_timestamp() -> None:
    class FutureTimestampTicker(FakeTicker):
        info: ClassVar[dict[str, object]] = {
            **FakeTicker.info,
            "regularMarketTime": int(datetime(2026, 8, 29, 12, 4, tzinfo=UTC).timestamp()),
        }

    ingested_at = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    adapter = YahooResearchAdapter(
        clock=lambda: ingested_at,
        ticker_factory=lambda symbol: FutureTimestampTicker(),
    )

    snapshot = adapter.fetch_snapshot(one_member_universe(), snapshot_version="snapshot-v1")

    assert snapshot.ingested_at == ingested_at
    assert snapshot.records[0].name.observed_at == datetime(2026, 8, 29, 12, 4, tzinfo=UTC)


def test_yahoo_research_adapter_marks_optional_fund_endpoint_failures() -> None:
    class FailingFundsTicker(FakeTicker):
        @property
        def funds_data(self) -> object:
            raise OSError("fund endpoint unavailable")

    instants = iter([datetime(2026, 8, 29, 12, 1, tzinfo=UTC)])
    adapter = YahooResearchAdapter(
        clock=lambda: next(instants),
        ticker_factory=lambda symbol: FailingFundsTicker(),
    )

    record = adapter.fetch_snapshot(one_member_universe(), snapshot_version="snapshot-v1").records[
        0
    ]

    assert record.top_holdings.missing_reason == MissingReason.SOURCE_ERROR
    assert record.sector_exposures.missing_reason == MissingReason.SOURCE_ERROR
    assert record.top_10_concentration_pct.missing_reason == MissingReason.SOURCE_ERROR


def test_yahoo_research_adapter_rejects_missing_source_observation_timestamp() -> None:
    class MissingTimestampTicker(FakeTicker):
        info: ClassVar[dict[str, object]] = {
            key: value for key, value in FakeTicker.info.items() if key != "regularMarketTime"
        }

    adapter = YahooResearchAdapter(
        clock=lambda: datetime(2026, 8, 29, 12, 1, tzinfo=UTC),
        ticker_factory=lambda symbol: MissingTimestampTicker(),
    )

    with pytest.raises(MarketDataError, match="observation timestamp"):
        adapter.fetch_snapshot(one_member_universe(), snapshot_version="snapshot-v1")


def test_yahoo_research_adapter_retries_missing_timestamp_with_fresh_ticker() -> None:
    class MissingTimestampTicker(FakeTicker):
        info: ClassVar[dict[str, object]] = {
            key: value for key, value in FakeTicker.info.items() if key != "regularMarketTime"
        }

    tickers = iter([MissingTimestampTicker(), FakeTicker()])
    sleeps: list[float] = []
    adapter = YahooResearchAdapter(
        clock=lambda: datetime(2026, 8, 29, 12, 1, tzinfo=UTC),
        ticker_factory=lambda symbol: next(tickers),
        max_attempts=2,
        sleeper=sleeps.append,
    )

    snapshot = adapter.fetch_snapshot(one_member_universe(), snapshot_version="snapshot-v1")

    assert snapshot.records[0].name.value == "Example Broad Market ETF"
    assert sleeps == [0.25]
