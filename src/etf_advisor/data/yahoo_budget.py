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
    """Have the pinned native transport admit body bytes before Python receives them."""
    yf = importlib.import_module("yfinance")
    if yf.__version__ != "1.7.0":
        raise YahooBudgetError("unreviewed_yfinance_version")
    curl = importlib.import_module("curl_cffi")
    native_version = getattr(curl, "__curl_version__", "")
    native_tokens = native_version.split() if isinstance(native_version, str) else []
    if (
        curl.__version__ != "0.16.2"
        or not native_tokens
        or native_tokens[0] != "libcurl/8.21.0-IMPERSONATE"
    ):
        raise YahooBudgetError("unreviewed_curl_transport")
    curl_write_error = int(importlib.import_module("curl_cffi.curl").CURL_WRITEFUNC_ERROR)

    def native_options(cap: int) -> dict[Any, Any]:
        if isinstance(cap, bool) or not isinstance(cap, int) or not 0 < cap < 2**63:
            raise YahooBudgetError("invalid_yahoo_response_limit")
        return {
            curl.CurlOpt.MAXFILESIZE_LARGE: cap,
            curl.CurlOpt.HEADER: 0,
            curl.CurlOpt.VERBOSE: 0,
            curl.CurlOpt.HTTP_CONTENT_DECODING: 1,
            curl.CurlOpt.HTTP_TRANSFER_DECODING: 1,
            curl.CurlOpt.PROTOCOLS_STR: b"http,https",
            curl.CurlOpt.REDIR_PROTOCOLS_STR: b"http,https",
        }

    initial_options = native_options(budget.max_response_bytes)
    base: Any = importlib.import_module("curl_cffi.requests").Session

    class BoundedSession(base):  # type: ignore[misc]
        def request(self, method: Any, url: str, **kwargs: Any) -> Any:
            if self.retry.count != 0:
                budget.breached = True
                raise YahooBudgetError("unsupported_yahoo_retry_policy")
            self.debug = False
            cap = budget.max_response_bytes
            self.curl_options = native_options(cap)
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
                if total > cap or budget.monotonic() >= budget.deadline:
                    budget.breached = True
                    return curl_write_error
                chunks.append(chunk)
                return len(chunk)

            try:
                response = super().request(method, url, content_callback=receive, **kwargs)
            except Exception as exc:
                if isinstance(exc, curl.CurlError) and exc.code == 63:
                    budget.breached = True
                if budget.breached:
                    raise YahooBudgetError("yahoo_receive_limit_exceeded") from exc
                raise
            budget.check()
            response.content = b"".join(chunks)
            return response

    return BoundedSession(impersonate="chrome", retry=0, debug=False, curl_options=initial_options)
