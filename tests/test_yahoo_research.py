from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import ClassVar

import numpy as np
import pytest

from etf_advisor.data.yahoo import MarketDataError
from etf_advisor.data.yahoo_research import YahooResearchAdapter
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import (
    ScreeningReason,
    ScreeningVerdict,
    screen_candidate_evidence,
)
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.models import ETFResearchRecord, ETFResearchSnapshot, MissingReason
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


def snapshot_with_funds_data(funds_data: object) -> ETFResearchSnapshot:
    class ConfiguredTicker:
        info: ClassVar[dict[str, object]] = FakeTicker.info

        def __init__(self) -> None:
            self.funds_data: object = funds_data

    return YahooResearchAdapter(
        clock=lambda: datetime(2026, 8, 29, 12, 1, tzinfo=UTC),
        ticker_factory=lambda symbol: ConfiguredTicker(),
    ).fetch_snapshot(one_member_universe(), snapshot_version="snapshot-v1")


def record_with_funds_data(funds_data: object) -> ETFResearchRecord:
    return snapshot_with_funds_data(funds_data).records[0]


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


@pytest.mark.parametrize(
    "bad_row",
    [
        None,
        {},
        {"Name": "", "Holding Percent": 0.1},
        {"Name": 123, "Holding Percent": 0.1},
        {"Name": "Broken", "Holding Percent": None},
        {"Name": "Broken", "Holding Percent": True},
        {"Name": "Broken", "Holding Percent": np.bool_(False)},
        {"Name": "Broken", "Holding Percent": np.bool_(True)},
        {"Name": "Broken", "Holding Percent": "unavailable"},
        {"Name": "Broken", "Holding Percent": float("nan")},
        {"Name": "Broken", "Holding Percent": float("inf")},
        {"Name": "Broken", "Holding Percent": -0.01},
        {"Name": "Broken", "Holding Percent": 101},
    ],
)
def test_malformed_holding_row_invalidates_holdings_and_concentration(bad_row: object) -> None:
    funds_data = SimpleNamespace(
        fund_overview=FakeFundsData.fund_overview,
        top_holdings=[FakeFundsData.top_holdings[0], bad_row],
        sector_weightings=FakeFundsData.sector_weightings,
    )

    record = record_with_funds_data(funds_data)

    assert record.top_holdings.value is None
    assert record.top_holdings.missing_reason == MissingReason.SOURCE_ERROR
    assert record.top_10_concentration_pct.value is None
    assert record.top_10_concentration_pct.missing_reason == MissingReason.SOURCE_ERROR
    assert record.sector_exposures.value is not None


@pytest.mark.parametrize("top_holdings", [(), "not-a-collection", {"Name": "Broken"}])
def test_unsupported_holdings_container_is_source_error(top_holdings: object) -> None:
    record = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=top_holdings,
            sector_weightings=FakeFundsData.sector_weightings,
        )
    )

    assert record.top_holdings.missing_reason == MissingReason.SOURCE_ERROR
    assert record.top_10_concentration_pct.missing_reason == MissingReason.SOURCE_ERROR


def test_malformed_eleventh_holding_invalidates_instead_of_understating_concentration() -> None:
    rows = [
        {"Symbol": f"H{index}", "Name": f"Holding {index}", "Holding Percent": 0.05}
        for index in range(10)
    ]
    rows.append({"Symbol": "BAD", "Name": "Broken"})

    record = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=rows,
            sector_weightings=FakeFundsData.sector_weightings,
        )
    )

    assert record.top_holdings.missing_reason == MissingReason.SOURCE_ERROR
    assert record.top_10_concentration_pct.missing_reason == MissingReason.SOURCE_ERROR


def test_holdings_conversion_failure_is_source_error() -> None:
    class BrokenFrame:
        def reset_index(self) -> object:
            return self

        def to_dict(self, *, orient: str) -> object:
            assert orient == "records"
            raise TypeError("raw provider detail must not escape")

    record = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=BrokenFrame(),
            sector_weightings=FakeFundsData.sector_weightings,
        )
    )

    assert record.top_holdings.missing_reason == MissingReason.SOURCE_ERROR
    assert record.top_10_concentration_pct.missing_reason == MissingReason.SOURCE_ERROR


@pytest.mark.parametrize(
    "sector_weightings",
    [
        [("technology", 0.2)],
        {None: 0.2},
        {"": 0.2},
        {"technology": None},
        {"technology": True},
        {"technology": np.bool_(False)},
        {"technology": np.bool_(True)},
        {"technology": "unavailable"},
        {"technology": float("nan")},
        {"technology": float("inf")},
        {"technology": -0.01},
        {"technology": 101},
        {"technology": 0.2, "energy": "unavailable"},
    ],
)
def test_malformed_sector_collection_is_atomic_source_error(
    sector_weightings: object,
) -> None:
    record = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=FakeFundsData.top_holdings,
            sector_weightings=sector_weightings,
        )
    )

    assert record.sector_exposures.value is None
    assert record.sector_exposures.missing_reason == MissingReason.SOURCE_ERROR
    assert record.top_holdings.value is not None


@pytest.mark.parametrize(
    ("top_holdings", "sector_weightings"),
    [
        (
            [
                {"Name": "Alpha", "Holding Percent": 60},
                {"Name": "Beta", "Holding Percent": 40.00000000000001},
            ],
            {"technology": 0.6, "energy": 0.4000000000000001},
        ),
        (
            [
                {"Name": "Alpha", "Holding Percent": 0.7},
                {"Name": "Beta", "Holding Percent": 0.31},
            ],
            {"technology": 70, "energy": 31},
        ),
    ],
)
def test_over_100_exposure_totals_are_source_error(
    top_holdings: object,
    sector_weightings: object,
) -> None:
    record = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=top_holdings,
            sector_weightings=sector_weightings,
        )
    )

    assert record.top_holdings.missing_reason == MissingReason.SOURCE_ERROR
    assert record.top_10_concentration_pct.missing_reason == MissingReason.SOURCE_ERROR
    assert record.sector_exposures.missing_reason == MissingReason.SOURCE_ERROR


def test_lossless_exposure_boundaries_classify_and_validate_before_float_conversion() -> None:
    just_over_one = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=[{"Name": "Alpha", "Holding Percent": "1.0000000000000001"}],
            sector_weightings={"technology": "1.0000000000000001"},
        )
    )

    assert just_over_one.top_holdings.value is not None
    assert 1 < just_over_one.top_holdings.value[0].weight_pct < 2
    assert just_over_one.top_10_concentration_pct.value is not None
    assert 1 < just_over_one.top_10_concentration_pct.value < 2
    assert just_over_one.sector_exposures.value is not None
    assert 1 < just_over_one.sector_exposures.value[0].weight_pct < 2

    just_over_individual_maximum = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=[{"Name": "Alpha", "Holding Percent": "100.000000000000001"}],
            sector_weightings={"technology": "100.000000000000001"},
        )
    )
    assert just_over_individual_maximum.top_holdings.missing_reason == MissingReason.SOURCE_ERROR
    assert (
        just_over_individual_maximum.top_10_concentration_pct.missing_reason
        == MissingReason.SOURCE_ERROR
    )
    assert (
        just_over_individual_maximum.sector_exposures.missing_reason == MissingReason.SOURCE_ERROR
    )

    just_over_aggregate_maximum = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=[
                {"Name": "Alpha", "Holding Percent": "50.000000000000001"},
                {"Name": "Beta", "Holding Percent": "50.000000000000001"},
            ],
            sector_weightings={
                "technology": "50.000000000000001",
                "energy": "50.000000000000001",
            },
        )
    )
    assert just_over_aggregate_maximum.top_holdings.missing_reason == MissingReason.SOURCE_ERROR
    assert (
        just_over_aggregate_maximum.top_10_concentration_pct.missing_reason
        == MissingReason.SOURCE_ERROR
    )
    assert just_over_aggregate_maximum.sector_exposures.missing_reason == MissingReason.SOURCE_ERROR


def test_just_over_concentration_limit_stays_above_limit_through_screening() -> None:
    snapshot = snapshot_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=[{"Name": "Alpha", "Holding Percent": "60.000000000000001"}],
            sector_weightings=FakeFundsData.sector_weightings,
        )
    )
    document = snapshot.to_source_documents()[0]
    profile = InvestorProfile(
        horizon_years=15,
        risk_tolerance="moderate",
        objective="growth",
        max_drawdown_pct=30,
        initial_investment_usd=50_000,
        recurring_monthly_usd=1_000,
    )
    evidence = select_candidate_evidence(
        profile,
        [
            GraphEnrichedSource(
                document_id=document.document_id,
                content=document.content,
                metadata=document.chroma_metadata(),
            )
        ],
        query="lossless concentration boundary",
        checked_at=datetime(2026, 8, 29, 12, 1, tzinfo=UTC),
        max_age=timedelta(hours=24),
    )

    candidate = screen_candidate_evidence(evidence).candidates[0]
    concentration_rule = candidate.rules[5]

    assert candidate.verdict == ScreeningVerdict.FAIL
    assert concentration_rule.verdict == ScreeningVerdict.FAIL
    assert concentration_rule.reason_code == ScreeningReason.CONCENTRATION_ABOVE_LIMIT
    assert concentration_rule.observed_value is not None
    assert concentration_rule.observed_value > 60
    assert concentration_rule.citation is not None
    assert concentration_rule.citation.field_name == "top_10_concentration_pct"


def test_valid_exposure_boundaries_preserve_order_zero_units_and_sparse_maps() -> None:
    record = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=[
                {"Symbol": "ZERO", "Name": "Zero", "Holding Percent": 0},
                {"Symbol": "FRACTION", "Name": "Fraction", "Holding Percent": "0.25"},
                {"Symbol": "POINTS", "Name": "Points", "Holding Percent": "75"},
            ],
            sector_weightings={"technology": 0.2, "energy": 0},
        )
    )

    assert record.top_holdings.missing_reason is None
    assert record.top_holdings.value is not None
    assert [item.symbol for item in record.top_holdings.value] == ["ZERO", "FRACTION", "POINTS"]
    assert [item.weight_pct for item in record.top_holdings.value] == [0, 25, 75]
    assert record.top_10_concentration_pct.value == 100
    assert record.sector_exposures.value is not None
    assert [(item.name, item.weight_pct) for item in record.sector_exposures.value] == [
        ("energy", 0),
        ("technology", 20),
    ]


@pytest.mark.parametrize("empty_value", [None, []])
def test_absent_or_empty_holdings_are_not_reported(empty_value: object) -> None:
    record = record_with_funds_data(
        SimpleNamespace(
            fund_overview=FakeFundsData.fund_overview,
            top_holdings=empty_value,
            sector_weightings={},
        )
    )

    assert record.top_holdings.missing_reason == MissingReason.NOT_REPORTED
    assert record.top_10_concentration_pct.missing_reason == MissingReason.NOT_REPORTED
    assert record.sector_exposures.missing_reason == MissingReason.NOT_REPORTED


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
