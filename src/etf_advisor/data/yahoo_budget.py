"""Actual HTTP limits for one explicit catalogue research attempt.

yfinance 1.7 shares its transport singleton between Ticker and screener calls.
Callers hold ``YAHOO_SESSION_LOCK`` over the complete yfinance operation.
"""

from __future__ import annotations

import importlib
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

YAHOO_SESSION_LOCK = threading.RLock()


@contextmanager
def restore_yahoo_data_session() -> Iterator[None]:
    """Keep one budgeted Ticker attempt from replacing yfinance's shared session.

    The caller holds YAHOO_SESSION_LOCK for the complete attempt. yfinance 1.7.0
    ignores ``session=None`` on later Tickers, so both transport and its
    session-specific authentication state must be restored on every exit.
    """
    data = importlib.import_module("yfinance.data").YfData()
    fields = (
        "_session",
        "_cookie",
        "_crumb",
        "_cookie_strategy",
        "_logged_in",
        "fundamentals_use_chunked",
    )
    previous = {name: getattr(data, name) for name in fields}
    try:
        yield
    finally:
        with data._cookie_lock:
            for name, value in previous.items():
                setattr(data, name, value)


class YahooBudgetError(RuntimeError):
    pass


@dataclass
class YahooRequestBudget:
    deadline: float
    max_requests: int = 12
    request_timeout: float = 10.0
    max_response_bytes: int = 2 * 1024 * 1024
    requests: int = 0
    breached: bool = False
    monotonic: Callable[[], float] = time.monotonic

    def check(self) -> None:
        if self.breached:
            raise YahooBudgetError("yahoo_budget_breached")
        if self.monotonic() >= self.deadline:
            self.breached = True
            raise YahooBudgetError("yahoo_deadline_exceeded")

    def before_request(self) -> float:
        self.check()
        if self.requests >= self.max_requests:
            self.breached = True
            raise YahooBudgetError("yahoo_request_limit_exceeded")
        self.requests += 1
        return min(self.request_timeout, self.deadline - self.monotonic())


def bounded_yahoo_session(budget: YahooRequestBudget) -> Any:
    """Use curl's receive callback so oversized bodies never fully materialize."""
    yf = importlib.import_module("yfinance")
    if yf.__version__ != "1.7.0":
        raise YahooBudgetError("unreviewed_yfinance_version")
    base: Any = importlib.import_module("curl_cffi.requests").Session

    class BoundedSession(base):  # type: ignore[misc]
        def request(self, method: Any, url: str, **kwargs: Any) -> Any:
            timeout = budget.before_request()
            if "content_callback" in kwargs or kwargs.get("stream"):
                budget.breached = True
                raise YahooBudgetError("unsupported_yahoo_transport_option")
            original = kwargs.pop("timeout", timeout)
            try:
                kwargs["timeout"] = min(float(original), timeout)
            except (TypeError, ValueError) as exc:
                budget.breached = True
                raise YahooBudgetError("invalid_yahoo_timeout") from exc
            chunks: list[bytes] = []
            total = 0

            def receive(chunk: bytes) -> int:
                nonlocal total
                total += len(chunk)
                if total > budget.max_response_bytes or budget.monotonic() >= budget.deadline:
                    budget.breached = True
                    return 0
                chunks.append(chunk)
                return len(chunk)

            try:
                response = super().request(method, url, content_callback=receive, **kwargs)
            except Exception as exc:
                if budget.breached:
                    raise YahooBudgetError("yahoo_receive_limit_exceeded") from exc
                raise
            budget.check()
            response.content = b"".join(chunks)
            return response

    return BoundedSession(impersonate="chrome")
