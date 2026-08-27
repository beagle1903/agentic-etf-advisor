"""Yahoo Finance development adapter with explicit provenance."""

from __future__ import annotations

import importlib
import math
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from typing import Any, cast

from etf_advisor.data.models import ETFObservation
from etf_advisor.rag.models import SourceDocument


class MarketDataError(RuntimeError):
    """Raised when a required market-data observation cannot be trusted."""


class YahooFinanceAdapter:
    """Fetch a small, timestamped snapshot for user-supplied symbols."""

    def __init__(self, ticker_factory: Callable[[str], Any] | None = None) -> None:
        self._ticker_factory = ticker_factory or self._load_ticker_factory()

    @staticmethod
    def _load_ticker_factory() -> Callable[[str], Any]:
        try:
            yfinance = importlib.import_module("yfinance")
        except ImportError as exc:
            raise MarketDataError(
                "Yahoo ingestion requires the optional 'rag' dependencies. Run: uv sync --extra rag"
            ) from exc
        return cast(Callable[[str], Any], yfinance.Ticker)

    def fetch(self, symbols: Sequence[str]) -> list[ETFObservation]:
        normalized_symbols = _normalize_symbols(symbols)
        if not normalized_symbols:
            raise MarketDataError("At least one ETF symbol is required.")

        observations: list[ETFObservation] = []
        for symbol in normalized_symbols:
            observations.append(self._fetch_one(symbol))
        return observations

    def fetch_source_documents(self, symbols: Sequence[str]) -> list[SourceDocument]:
        return [self.to_source_document(observation) for observation in self.fetch(symbols)]

    @staticmethod
    def to_source_document(observation: ETFObservation) -> SourceDocument:
        observed_at = observation.observed_at.astimezone(UTC)
        timestamp = observed_at.strftime("%Y%m%dT%H%M%SZ")
        document_id = f"yahoo-finance:{observation.symbol.lower()}:{timestamp}"
        observation_text = [
            f"Instrument symbol: {observation.symbol}",
            f"Instrument name: {observation.name}",
            f"Latest reported close: {observation.close_price:g}"
            + (f" {observation.currency}" if observation.currency else ""),
            f"Observation timestamp (UTC): {observed_at.isoformat().replace('+00:00', 'Z')}",
            f"Quote type: {observation.quote_type or 'not reported'}",
            f"Category: {observation.category or 'not reported'}",
            f"Fund family: {observation.fund_family or 'not reported'}",
            f"Expense ratio: {observation.expense_ratio_pct:g}%"
            if observation.expense_ratio_pct is not None
            else "Expense ratio: not reported",
        ]
        if observation.description:
            observation_text.append(f"Description: {observation.description}")
        observation_text.append(f"Source: Yahoo Finance ({observation.source_url})")

        metadata: dict[str, str | int | float | bool] = {
            "symbol": observation.symbol,
            "source": observation.source,
            "source_url": observation.source_url,
            "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
            "document_type": "market_snapshot",
        }
        if observation.currency:
            metadata["currency"] = observation.currency
        if observation.category:
            metadata["category"] = observation.category
        if observation.expense_ratio_pct is not None:
            metadata["expense_ratio_pct"] = observation.expense_ratio_pct

        return SourceDocument(
            document_id=document_id,
            symbol=observation.symbol,
            title=f"{observation.symbol} Yahoo Finance market snapshot",
            content="\n".join(observation_text),
            source=observation.source,
            source_url=observation.source_url,
            observed_at=observed_at,
            document_type="market_snapshot",
            metadata=metadata,
        )

    def _fetch_one(self, symbol: str) -> ETFObservation:
        try:
            ticker = self._ticker_factory(symbol)
            history = ticker.history(period="5d", interval="1d", auto_adjust=False)
        except Exception as exc:
            raise MarketDataError(f"Yahoo Finance request failed for {symbol}: {exc}") from exc

        close_price, observed_at = _latest_close(history, symbol)
        info = _safe_info(ticker)
        expense_ratio_pct = _first_percentage(
            info.get("netExpenseRatio"),
            info.get("annualReportExpenseRatio"),
        )
        return ETFObservation(
            symbol=symbol,
            name=_first_text(info.get("longName"), info.get("shortName"), default=symbol),
            close_price=close_price,
            currency=_optional_text(info.get("currency")),
            observed_at=observed_at,
            source_url=f"https://finance.yahoo.com/quote/{symbol}/",
            quote_type=_optional_text(info.get("quoteType")),
            category=_optional_text(info.get("category")),
            fund_family=_optional_text(info.get("fundFamily")),
            expense_ratio_pct=expense_ratio_pct,
            description=_optional_text(info.get("longBusinessSummary"), max_length=4000) or "",
        )


def _normalize_symbols(symbols: Sequence[str]) -> list[str]:
    result: list[str] = []
    for symbol in symbols:
        normalized = symbol.strip().upper()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _safe_info(ticker: Any) -> dict[str, Any]:
    try:
        info = ticker.info
    except Exception:
        return {}
    return dict(info) if isinstance(info, dict) else {}


def _latest_close(history: Any, symbol: str) -> tuple[float, datetime]:
    if getattr(history, "empty", False):
        raise MarketDataError(f"Yahoo Finance returned no price history for {symbol}.")
    try:
        last_row = history.iloc[-1]
        close_price = float(last_row["Close"])
        observed_at = _as_utc_datetime(history.index[-1])
    except (KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
        raise MarketDataError(f"Yahoo Finance returned an unusable snapshot for {symbol}.") from exc
    if not math.isfinite(close_price) or close_price < 0:
        raise MarketDataError(f"Yahoo Finance returned an invalid close for {symbol}.")
    return close_price, observed_at


def _as_utc_datetime(value: Any) -> datetime:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time())
    if not isinstance(value, datetime):
        raise TypeError("observation index is not date-like")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_text(value: Any, max_length: int = 200) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:max_length] or None


def _first_text(*values: Any, default: str) -> str:
    for value in values:
        text = _optional_text(value)
        if text:
            return text
    return default


def _first_percentage(*values: Any) -> float | None:
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed) and 0 <= parsed <= 100:
            return parsed
    return None
