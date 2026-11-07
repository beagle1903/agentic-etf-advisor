"""One terminally recorded, bounded Issue 141 source-feasibility pass.

The output is ignored local evidence. It is not a publication or a review artifact.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from etf_advisor.catalogue.mapping import US_EXCHANGES
from etf_advisor.data.research_quality import assess_research_fields
from etf_advisor.data.vanguard import VanguardHoldingsClient
from etf_advisor.data.yahoo_budget import (
    YAHOO_SESSION_LOCK,
    YahooRequestBudget,
    bounded_yahoo_session,
    restore_yahoo_data_session,
)
from etf_advisor.data.yahoo_research import YahooResearchAdapter
from etf_advisor.domain.construction import (
    DEFAULT_CONSTRUCTION_POLICY,
    PortfolioSleeve,
    _normalize_category,
)
from etf_advisor.research.models import ETFResearchSnapshot
from etf_advisor.research.us_starter import starter_universe

ROOT = Path(".artifacts/issue141-source-pass")
PASS = ROOT / "pass.json"
SYMBOLS = (
    "BND",
    "AGG",
    "SCHZ",
    "SPAB",
    "SPY",
    "IVV",
    "VOO",
    "VTI",
    "ITOT",
    "SCHB",
    "QQQ",
    "VUG",
    "SCHG",
    "IWF",
    "VEA",
    "IEFA",
    "SCHF",
    "VWO",
    "IEMG",
    "SCHE",
)

_SAFE_FAILURES = frozenset(
    {
        "returned_symbol_mismatch",
        "unmapped_us_exchange",
        "non_us_etf_identity",
        "non_usd_quote_currency",
        "unreviewed_yfinance_version",
        "unreviewed_curl_transport",
        "yahoo_budget_breached",
        "yahoo_deadline_exceeded",
        "yahoo_request_limit_exceeded",
        "yahoo_receive_limit_exceeded",
        "unsupported_yahoo_retry_policy",
        "unsupported_yahoo_transport_option",
        "invalid_yahoo_response_limit",
        "invalid_yahoo_timeout",
    }
)


def _safe_reason(exc: Exception) -> str:
    if _authentication_failure(exc):
        return "provider_authentication_failure"
    code = str(exc)
    return code if code in _SAFE_FAILURES else type(exc).__name__


def _authentication_failure(exc: Exception) -> bool:
    current: BaseException | None = exc
    while current is not None:
        response = getattr(current, "response", None)
        if getattr(response, "status_code", None) in {401, 403}:
            return True
        current = current.__cause__
    return False


def _write(state: dict[str, Any], pass_path: Path) -> None:
    pass_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = pass_path.with_suffix(".tmp")
    with temporary.open("x", encoding="utf-8") as target:
        json.dump(state, target, sort_keys=True, separators=(",", ":"), allow_nan=False)
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, pass_path)


def _classify(record: Any, checked_at: datetime) -> tuple[str, str]:
    fields = record.research_fields()
    snapshot = ETFResearchSnapshot(
        schema_version=2,
        snapshot_version=record.name.snapshot_version,
        universe_id="us-starter",
        universe_version="1",
        ingested_at=record.name.ingested_at,
        records=[record],
    )
    health = assess_research_fields(
        snapshot,
        checked_at=checked_at,
        max_age=timedelta(hours=120),
        future_tolerance=timedelta(minutes=5),
    )
    if not health.healthy:
        return "excluded", "stale_or_future_source_field"
    for name in (
        "expense_ratio_pct",
        "average_daily_volume",
        "top_10_concentration_pct",
        "category",
    ):
        if fields[name].value is None:
            return "excluded", f"missing_{name}:{fields[name].missing_reason}"
    if fields["expense_ratio_pct"].value > 1.0:
        return "excluded", "expense_ratio_above_1_pct"
    if fields["average_daily_volume"].value < 100_000:
        return "excluded", "average_volume_below_100000"
    if fields["top_10_concentration_pct"].value > 60.0:
        return "excluded", "top_10_concentration_above_60_pct"
    category = fields["category"].value
    normalized = _normalize_category(category)
    if normalized in {
        _normalize_category(item)
        for item in DEFAULT_CONSTRUCTION_POLICY.category_sleeves[PortfolioSleeve.DEFENSIVE]
    }:
        return "eligible_defensive", "existing_category_and_thresholds_pass"
    if normalized in {
        _normalize_category(item)
        for item in DEFAULT_CONSTRUCTION_POLICY.category_sleeves[PortfolioSleeve.GROWTH]
    }:
        return "eligible_growth", "existing_category_and_thresholds_pass"
    return "excluded", "unsupported_category"


def run_pass(root: Path) -> Path:
    """One explicit bounded preparation; an existing or crashed root is never restarted."""
    pass_path = root / "pass.json"
    if root.exists():
        raise ValueError("starter_source_run_already_exists")
    root.mkdir(parents=True, exist_ok=False)
    universe = starter_universe()
    if set(universe.symbols) != set(SYMBOLS) or len(universe.symbols) != 20:
        raise SystemExit("Starter universe mismatch")
    started = time.monotonic()
    deadline = started + 900
    state: dict[str, Any] = {
        "schema": "issue141-source-pass-v1",
        "started_at": datetime.now(UTC).isoformat(),
        "universe": universe.model_dump(mode="json"),
        "status": "running",
        "outcomes": [],
    }
    _write(state, pass_path)
    try:
        yf = importlib.import_module("yfinance")
        for index, symbol in enumerate(SYMBOLS):
            if index == 4 and not any(
                item.get("assessment") == "eligible_defensive" for item in state["outcomes"]
            ):
                state["status"] = "blocked_no_eligible_defensive"
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                state["status"] = "whole_pass_deadline"
                break
            budget = YahooRequestBudget(
                deadline=min(deadline, time.monotonic() + (90 if symbol == "BND" else 45))
            )
            outcome: dict[str, Any] = {
                "symbol": symbol,
                "status": "started",
                "started_at": datetime.now(UTC).isoformat(),
            }
            state["outcomes"].append(outcome)
            _write(state, pass_path)
            try:
                with YAHOO_SESSION_LOCK, restore_yahoo_data_session():
                    session = bounded_yahoo_session(budget)

                    def ticker_factory(name: str, bound_session: Any = session) -> Any:
                        return yf.Ticker(name, session=bound_session)

                    adapter = YahooResearchAdapter(
                        clock=lambda: datetime.now(UTC),
                        ticker_factory=ticker_factory,
                        max_attempts=1,
                        issuer_client=VanguardHoldingsClient(deadline=budget.deadline)
                        if symbol == "BND" and remaining >= 90
                        else None,
                    )
                    raw = adapter._fetch_one(symbol)
                    budget.check()
                    info = raw.info
                    if info.get("symbol") != symbol:
                        raise ValueError("returned_symbol_mismatch")
                    if info.get("exchange") not in US_EXCHANGES:
                        raise ValueError("unmapped_us_exchange")
                    if info.get("quoteType") != "ETF" or info.get("market") != "us_market":
                        raise ValueError("non_us_etf_identity")
                    if info.get("currency") != "USD":
                        raise ValueError("non_usd_quote_currency")
                    checked_at = datetime.now(UTC)
                    record = adapter._build_record(
                        raw, snapshot_version="issue141-source-pass", ingested_at=checked_at
                    )
                    budget.check()
                assessment, reason = _classify(record, checked_at)
                outcome.update(
                    status="collected",
                    assessment=assessment,
                    reason=reason,
                    exchange=info["exchange"],
                    provider="yahoo_finance",
                    quote_type="ETF",
                    market="us_market",
                    currency="USD",
                    source_url=f"https://finance.yahoo.com/quote/{symbol}/",
                    observed_at=raw.observed_at.isoformat(),
                    collected_at=checked_at.isoformat(),
                    record=record.model_dump(mode="json"),
                )
            except Exception as exc:
                outcome.update(status="failed", assessment="excluded", reason=_safe_reason(exc))
                if budget.breached:
                    outcome["budget_breached"] = True
            outcome["requests"] = budget.requests
            outcome["completed_at"] = datetime.now(UTC).isoformat()
            _write(state, pass_path)
            if budget.breached or outcome.get("reason") in {
                "unreviewed_yfinance_version",
                "unreviewed_curl_transport",
                "unsupported_yahoo_retry_policy",
                "unsupported_yahoo_transport_option",
                "invalid_yahoo_response_limit",
                "invalid_yahoo_timeout",
                "provider_authentication_failure",
            }:
                state["status"] = "transport_blocked"
                break
        else:
            state["status"] = "complete"
    except ImportError:
        state["status"] = "transport_blocked"
    finally:
        attempted = {item["symbol"] for item in state["outcomes"]}
        for symbol in SYMBOLS:
            if symbol not in attempted:
                state["outcomes"].append(
                    {
                        "symbol": symbol,
                        "status": "unattempted",
                        "assessment": "unattempted",
                        "reason": state["status"],
                    }
                )
        state["finished_at"] = datetime.now(UTC).isoformat()
        state["elapsed_seconds"] = round(time.monotonic() - started, 3)
        _write(state, pass_path)
    return pass_path


def main() -> None:
    pass_path = run_pass(ROOT)
    state = json.loads(pass_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "status": state["status"],
                "outcomes": [
                    {
                        key: item.get(key)
                        for key in ("symbol", "status", "assessment", "reason", "requests")
                    }
                    for item in state["outcomes"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
