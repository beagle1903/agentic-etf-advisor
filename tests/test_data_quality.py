import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from typer.testing import CliRunner

import etf_advisor.cli as cli
from etf_advisor.data.models import ETFObservation
from etf_advisor.data.quality import (
    FreshnessStatus,
    MarketDataQualityError,
    assess_observations,
)


def observation(observed_at: datetime) -> ETFObservation:
    return ETFObservation(
        symbol="SPY",
        name="Test ETF",
        close_price=500,
        currency="USD",
        observed_at=observed_at,
        source_url="https://finance.yahoo.com/quote/SPY/",
    )


def test_freshness_report_preserves_source_evidence_and_rejects_stale_data() -> None:
    checked_at = datetime(2026, 8, 27, 12, tzinfo=UTC)
    current = observation(checked_at - timedelta(hours=24))
    stale = observation(checked_at - timedelta(hours=121))

    report = assess_observations(
        [current, stale],
        checked_at=checked_at,
        max_age=timedelta(hours=120),
    )

    assert report.healthy is False
    assert report.observations[0].status == FreshnessStatus.CURRENT
    assert report.observations[1].status == FreshnessStatus.STALE
    assert report.observations[1].source == "yahoo_finance"
    assert report.observations[1].source_url.endswith("/SPY/")
    with pytest.raises(MarketDataQualityError, match=r"SPY.*121\.00 hours old"):
        report.require_healthy()


def test_freshness_report_rejects_observation_too_far_in_future() -> None:
    checked_at = datetime(2026, 8, 27, 12, tzinfo=UTC)

    report = assess_observations(
        [observation(checked_at + timedelta(minutes=6))],
        checked_at=checked_at,
        max_age=timedelta(hours=120),
    )

    assert report.observations[0].status == FreshnessStatus.FUTURE
    with pytest.raises(MarketDataQualityError, match="ahead"):
        report.require_healthy()


def test_freshness_check_requires_injected_aware_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        assess_observations(
            [observation(datetime(2026, 8, 27, tzinfo=UTC))],
            checked_at=datetime(2026, 8, 27),
            max_age=timedelta(hours=120),
        )


def test_data_health_command_reports_without_persisting(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_at = datetime.now(UTC) - timedelta(hours=1)

    class FakeAdapter:
        def fetch(self, symbols: list[str]) -> list[ETFObservation]:
            assert symbols == ["SPY"]
            return [observation(observed_at)]

    monkeypatch.setattr(cli, "_yahoo_adapter", lambda: FakeAdapter())

    result = CliRunner().invoke(cli.app, ["data-health", "--symbols", "SPY"])

    assert result.exit_code == 0
    payload: dict[str, Any] = json.loads(result.stdout)
    assert payload["healthy"] is True
    assert payload["observations"][0]["source_url"].endswith("/SPY/")


def test_data_health_command_exits_nonzero_for_stale_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_at = datetime.now(UTC) - timedelta(days=30)

    class FakeAdapter:
        def fetch(self, symbols: list[str]) -> list[ETFObservation]:
            return [observation(observed_at)]

    monkeypatch.setattr(cli, "_yahoo_adapter", lambda: FakeAdapter())

    result = CliRunner().invoke(cli.app, ["data-health", "--symbols", "SPY"])

    assert result.exit_code == 1
    assert json.loads(result.stdout)["healthy"] is False


def test_ingest_blocks_stale_data_before_opening_a_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_at = datetime.now(UTC) - timedelta(days=30)

    class FakeAdapter:
        def fetch(self, symbols: list[str]) -> list[ETFObservation]:
            return [observation(observed_at)]

    def unexpected_store(**kwargs: object) -> None:
        raise AssertionError("stale observations must be rejected before persistence")

    monkeypatch.setattr(cli, "_yahoo_adapter", lambda: FakeAdapter())
    monkeypatch.setattr(cli, "ChromaDocumentStore", unexpected_store)

    result = CliRunner().invoke(cli.app, ["ingest", "--symbols", "SPY"])

    assert result.exit_code == 1
    assert "Market-data health check failed" in result.stderr
