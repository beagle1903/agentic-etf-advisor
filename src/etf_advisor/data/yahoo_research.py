"""Yahoo Finance development adapter for the versioned ETF research contract."""

from __future__ import annotations

import importlib
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar, cast

from etf_advisor.clock import Clock
from etf_advisor.data.yahoo import MarketDataError
from etf_advisor.research.models import (
    ETFResearchRecord,
    ETFResearchSnapshot,
    MissingReason,
    ResearchField,
    WeightedExposure,
)
from etf_advisor.research.universe import ResearchUniverse

FieldValue = TypeVar("FieldValue")


@dataclass(frozen=True)
class _RawResearch:
    symbol: str
    info: dict[str, Any]
    fund_overview: dict[str, Any] | None
    fund_overview_error: bool
    top_holdings: list[WeightedExposure] | None
    top_holdings_error: bool
    sector_exposures: list[WeightedExposure] | None
    sector_exposures_error: bool
    observed_at: datetime


class YahooResearchAdapter:
    """Fetch the curated universe without hiding unavailable material fields."""

    provider = "yahoo_finance"

    def __init__(
        self,
        *,
        clock: Clock,
        ticker_factory: Callable[[str], Any] | None = None,
        max_attempts: int = 3,
        retry_backoff_seconds: float = 0.25,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative.")
        self._clock = clock
        self._ticker_factory = ticker_factory or self._load_ticker_factory()
        self._max_attempts = max_attempts
        self._retry_backoff_seconds = retry_backoff_seconds
        self._sleeper = sleeper

    @staticmethod
    def _load_ticker_factory() -> Callable[[str], Any]:
        try:
            yfinance = importlib.import_module("yfinance")
        except ImportError as exc:
            raise MarketDataError(
                "Yahoo research ingestion requires the optional 'rag' dependencies. "
                "Run: uv sync --extra rag"
            ) from exc
        return cast(Callable[[str], Any], yfinance.Ticker)

    def fetch_snapshot(
        self,
        universe: ResearchUniverse,
        *,
        snapshot_version: str,
    ) -> ETFResearchSnapshot:
        """Fetch every curated member and build one internally consistent snapshot."""

        raw_records = [self._fetch_one(symbol) for symbol in universe.symbols]
        ingested_at = self._clock()
        records = [
            self._build_record(raw, snapshot_version=snapshot_version, ingested_at=ingested_at)
            for raw in raw_records
        ]
        return ETFResearchSnapshot(
            snapshot_version=snapshot_version,
            universe_id=universe.universe_id,
            universe_version=universe.universe_version,
            ingested_at=ingested_at,
            records=records,
        )

    def _fetch_one(self, symbol: str) -> _RawResearch:
        ticker = self._retry(
            symbol,
            "metadata",
            lambda: self._ticker_factory(symbol),
        )
        ticker, info, observed_at = self._fetch_info_snapshot(symbol, ticker)

        funds_data: Any | None
        try:
            funds_data = ticker.funds_data
        except Exception:
            funds_data = None

        overview, overview_error = _optional_source_value(
            funds_data,
            "fund_overview",
            _as_mapping,
        )
        holdings, holdings_error = _optional_source_value(
            funds_data,
            "top_holdings",
            _holding_exposures,
        )
        sectors, sectors_error = _optional_source_value(
            funds_data,
            "sector_weightings",
            _sector_exposures,
        )
        return _RawResearch(
            symbol=symbol,
            info=info,
            fund_overview=overview,
            fund_overview_error=overview_error,
            top_holdings=holdings,
            top_holdings_error=holdings_error,
            sector_exposures=sectors,
            sector_exposures_error=sectors_error,
            observed_at=observed_at,
        )

    def _fetch_info_snapshot(
        self,
        symbol: str,
        initial_ticker: Any,
    ) -> tuple[Any, dict[str, Any], datetime]:
        """Retry metadata with a fresh ticker after the initial attempt."""

        for attempt in range(1, self._max_attempts + 1):
            try:
                ticker = initial_ticker if attempt == 1 else self._ticker_factory(symbol)
                info, observed_at = _required_info_snapshot(ticker, symbol)
                return ticker, info, observed_at
            except Exception as exc:
                if attempt == self._max_attempts:
                    raise MarketDataError(
                        f"Yahoo Finance metadata failed for {symbol} after "
                        f"{attempt} attempt(s): {exc}"
                    ) from exc
                self._sleeper(self._retry_backoff_seconds * (2 ** (attempt - 1)))
        raise MarketDataError(f"Yahoo Finance metadata failed for {symbol}.")

    def _retry(
        self,
        symbol: str,
        label: str,
        operation: Callable[[], FieldValue],
    ) -> FieldValue:
        for attempt in range(1, self._max_attempts + 1):
            try:
                return operation()
            except Exception as exc:
                if attempt == self._max_attempts:
                    raise MarketDataError(
                        f"Yahoo Finance {label} failed for {symbol} after "
                        f"{attempt} attempt(s): {exc}"
                    ) from exc
                self._sleeper(self._retry_backoff_seconds * (2 ** (attempt - 1)))
        raise MarketDataError(f"Yahoo Finance {label} failed for {symbol}.")

    def _build_record(
        self,
        raw: _RawResearch,
        *,
        snapshot_version: str,
        ingested_at: datetime,
    ) -> ETFResearchRecord:
        info = raw.info
        overview = raw.fund_overview or {}
        source_url = f"https://finance.yahoo.com/quote/{raw.symbol}/"

        def field(
            value: FieldValue | None,
            unit: str,
            *,
            missing_reason: MissingReason = MissingReason.NOT_REPORTED,
            provider: str = self.provider,
        ) -> ResearchField[FieldValue]:
            return ResearchField[FieldValue](
                value=value,
                unit=unit,
                provider=provider,
                source_url=source_url,
                observed_at=raw.observed_at,
                ingested_at=ingested_at,
                snapshot_version=snapshot_version,
                missing_reason=missing_reason if value is None else None,
            )

        holdings_reason = (
            MissingReason.SOURCE_ERROR if raw.top_holdings_error else MissingReason.NOT_REPORTED
        )
        sectors_reason = (
            MissingReason.SOURCE_ERROR if raw.sector_exposures_error else MissingReason.NOT_REPORTED
        )
        overview_reason = (
            MissingReason.SOURCE_ERROR if raw.fund_overview_error else MissingReason.NOT_REPORTED
        )
        holdings = raw.top_holdings or None
        sector_exposures = raw.sector_exposures or None
        concentration = (
            min(100.0, sum(item.weight_pct for item in holdings[:10])) if holdings else None
        )
        return ETFResearchRecord(
            symbol=raw.symbol,
            name=field(_first_text(info.get("longName"), info.get("shortName")), "text"),
            quote_type=field(_optional_text(info.get("quoteType")), "classification"),
            market=field(_optional_text(info.get("market")), "classification"),
            category=field(
                _first_text(info.get("category"), overview.get("categoryName")),
                "classification",
                missing_reason=overview_reason,
            ),
            fund_family=field(
                _first_text(info.get("fundFamily"), overview.get("family")),
                "text",
                missing_reason=overview_reason,
            ),
            benchmark=field(
                _first_text(info.get("indexName"), info.get("benchmark")),
                "text",
            ),
            expense_ratio_pct=field(_expense_ratio_percentage(info), "percent"),
            average_daily_volume=field(
                _first_number(
                    info.get("averageDailyVolume10Day"),
                    info.get("averageVolume10days"),
                    info.get("averageVolume"),
                ),
                "shares_per_day",
            ),
            top_holdings=field(
                holdings,
                "percent_of_fund",
                missing_reason=holdings_reason,
            ),
            sector_exposures=field(
                sector_exposures,
                "percent_of_fund",
                missing_reason=sectors_reason,
            ),
            geography_exposures=field(
                None,
                "percent_of_fund",
                missing_reason=MissingReason.PROVIDER_UNSUPPORTED,
            ),
            top_10_concentration_pct=field(
                concentration,
                "percent",
                missing_reason=holdings_reason,
                provider="yahoo_finance_derived",
            ),
        )


def _required_info(ticker: Any) -> dict[str, Any]:
    info = ticker.info
    if not isinstance(info, dict):
        raise TypeError("metadata response is not an object")
    return dict(info)


def _required_info_snapshot(ticker: Any, symbol: str) -> tuple[dict[str, Any], datetime]:
    info = _required_info(ticker)
    return info, _source_observed_at(info, symbol)


def _source_observed_at(info: dict[str, Any], symbol: str) -> datetime:
    """Return Yahoo's source-reported quote timestamp for snapshot freshness."""

    epoch_seconds = _number(info.get("regularMarketTime"))
    if epoch_seconds is None or epoch_seconds <= 0:
        raise MarketDataError(
            f"Yahoo Finance metadata did not report a usable observation timestamp for {symbol}."
        )
    try:
        return datetime.fromtimestamp(epoch_seconds, tz=UTC)
    except (OSError, OverflowError, ValueError) as exc:
        raise MarketDataError(
            f"Yahoo Finance metadata reported an invalid observation timestamp for {symbol}."
        ) from exc


def _optional_source_value[FieldValue](
    source: Any | None,
    attribute: str,
    parser: Callable[[Any], FieldValue | None],
) -> tuple[FieldValue | None, bool]:
    if source is None:
        return None, True
    try:
        return parser(getattr(source, attribute)), False
    except Exception:
        return None, True


def _as_mapping(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return dict(value) or None


def _holding_exposures(value: Any) -> list[WeightedExposure] | None:
    if value is None:
        return None
    if isinstance(value, list):
        rows = value
    elif hasattr(value, "reset_index"):
        rows = value.reset_index().to_dict(orient="records")
    else:
        return None

    exposures: list[WeightedExposure] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = _first_text(row.get("Name"), row.get("holdingName"))
        symbol = _first_text(row.get("Symbol"), row.get("symbol"))
        weight = _percentage(row.get("Holding Percent", row.get("holdingPercent")))
        if name is None or weight is None:
            continue
        exposures.append(WeightedExposure(name=name, symbol=symbol, weight_pct=weight))
    return exposures or None


def _sector_exposures(value: Any) -> list[WeightedExposure] | None:
    if not isinstance(value, dict):
        return None
    exposures: list[WeightedExposure] = []
    for name, raw_weight in sorted(value.items(), key=lambda item: str(item[0])):
        weight = _percentage(raw_weight)
        normalized_name = _optional_text(name)
        if normalized_name is not None and weight is not None:
            exposures.append(WeightedExposure(name=normalized_name, weight_pct=weight))
    return exposures or None


def _percentage(value: Any) -> float | None:
    parsed = _number(value)
    if parsed is None or parsed < 0:
        return None
    percentage = parsed * 100 if parsed <= 1 else parsed
    return percentage if percentage <= 100 else None


def _expense_ratio_percentage(info: dict[str, Any]) -> float | None:
    net_expense_ratio = _number(info.get("netExpenseRatio"))
    if net_expense_ratio is not None and 0 <= net_expense_ratio <= 100:
        return net_expense_ratio
    annual_report_fraction = _number(info.get("annualReportExpenseRatio"))
    if annual_report_fraction is None or not 0 <= annual_report_fraction <= 1:
        return None
    return annual_report_fraction * 100


def _first_number(*values: Any) -> float | None:
    for value in values:
        parsed = _number(value)
        if parsed is not None and parsed >= 0:
            return parsed
    return None


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _optional_text(value)
        if text is not None:
            return text
    return None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
