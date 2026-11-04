"""Offline checks against the pinned curl transport's real body admission path."""

from __future__ import annotations

import gzip
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from etf_advisor.data.yahoo_budget import (
    YahooBudgetError,
    YahooRequestBudget,
    bounded_yahoo_session,
)


@contextmanager
def local_server() -> Iterator[str]:
    cap = 32_768

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            pass

        def do_GET(self) -> None:
            path = self.path
            if path == "/slow":
                time.sleep(0.2)
            if path.startswith("/redirect/"):
                self.send_response(302)
                self.send_header("Location", path.removeprefix("/redirect"))
                self.send_header("Content-Length", "10")
                self.end_headers()
                self.wfile.write(b"redirected")
                return
            oversized = path.endswith("/over")
            body = b"A" * (cap + int(oversized))
            compressed = "gzip" in path
            if compressed:
                body = gzip.compress(body)
            chunked = "chunked" in path
            self.send_response(200)
            if compressed:
                self.send_header("Content-Encoding", "gzip")
            if chunked:
                self.send_header("Transfer-Encoding", "chunked")
            elif "unknown" not in path:
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                if chunked:
                    for offset in range(0, len(body), 4096):
                        piece = body[offset : offset + 4096]
                        self.wfile.write(f"{len(piece):x}\r\n".encode() + piece + b"\r\n")
                    self.wfile.write(b"0\r\n\r\n")
                else:
                    self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # The native size abort closes the loopback connection.

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize(
    "path",
    [
        "/known",
        "/unknown",
        "/chunked",
        "/gzip",
        "/chunked-gzip",
        "/redirect/known",
        "/redirect/gzip",
    ],
)
@pytest.mark.parametrize("oversized", [False, True])
def test_native_limit_caps_delivery(
    path: str, oversized: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    curl = pytest.importorskip("curl_cffi")
    pytest.importorskip("yfinance")
    base = curl.requests.Session
    original = base.request
    received = [0]

    def count_delivery(self: object, method: str, url: str, **kwargs: object) -> object:
        callback = kwargs["content_callback"]

        def counted(chunk: bytes) -> int:
            received[0] += len(chunk)
            return callback(chunk)  # type: ignore[operator]

        kwargs["content_callback"] = counted
        return original(self, method, url, **kwargs)

    monkeypatch.setattr(base, "request", count_delivery)
    budget = YahooRequestBudget(deadline=time.monotonic() + 15, max_response_bytes=32_768)
    with local_server() as root:
        session = bounded_yahoo_session(budget)
        url = f"{root}{path}/{'over' if oversized else 'exact'}"
        if oversized:
            with pytest.raises(YahooBudgetError, match="yahoo_receive_limit_exceeded"):
                session.request("GET", url)
            assert budget.breached
            with pytest.raises(YahooBudgetError, match="yahoo_budget_breached"):
                session.request("GET", url)
        else:
            assert session.request("GET", url).content == b"A" * 32_768
        assert received[0] <= 32_768


@pytest.mark.parametrize("cap", [0, -1, True, 2**63, 1.5])
def test_invalid_native_cap_fails_before_request(cap: object) -> None:
    pytest.importorskip("curl_cffi")
    pytest.importorskip("yfinance")
    budget = YahooRequestBudget(deadline=time.monotonic() + 10, max_response_bytes=cap)  # type: ignore[arg-type]
    with pytest.raises(YahooBudgetError, match="invalid_yahoo_response_limit"):
        bounded_yahoo_session(budget)
    assert budget.requests == 0


def test_runtime_gate_and_owned_options(monkeypatch: pytest.MonkeyPatch) -> None:
    curl = pytest.importorskip("curl_cffi")
    pytest.importorskip("yfinance")
    budget = YahooRequestBudget(deadline=time.monotonic() + 15, max_response_bytes=32_768)
    original_version = curl.__curl_version__
    monkeypatch.setattr(curl, "__curl_version__", "libcurl/8.19.0-IMPERSONATE")
    with pytest.raises(YahooBudgetError, match="unreviewed_curl_transport"):
        bounded_yahoo_session(budget)
    assert budget.requests == 0
    monkeypatch.setattr(curl, "__curl_version__", "  ")
    with pytest.raises(YahooBudgetError, match="unreviewed_curl_transport"):
        bounded_yahoo_session(budget)
    monkeypatch.setattr(curl, "__curl_version__", original_version)

    with local_server() as root:
        session = bounded_yahoo_session(budget)
        session.curl_options.clear()
        session.debug = True
        assert session.request("GET", f"{root}/known/exact").content == b"A" * 32_768
        assert session.curl_options[curl.CurlOpt.MAXFILESIZE_LARGE] == 32_768
        assert session.debug is False
        session.retry.count = 1
        with pytest.raises(YahooBudgetError, match="unsupported_yahoo_retry_policy"):
            session.request("GET", f"{root}/known/exact")
        assert budget.breached
        assert budget.requests == 1


def test_changed_cap_is_applied_to_next_request() -> None:
    curl = pytest.importorskip("curl_cffi")
    pytest.importorskip("yfinance")
    budget = YahooRequestBudget(deadline=time.monotonic() + 15, max_response_bytes=32_768)
    with local_server() as root:
        session = bounded_yahoo_session(budget)
        assert session.request("GET", f"{root}/known/exact").content == b"A" * 32_768
        budget.max_response_bytes = 1024
        with pytest.raises(YahooBudgetError, match="yahoo_receive_limit_exceeded"):
            session.request("GET", f"{root}/known/exact")
        assert session.curl_options[curl.CurlOpt.MAXFILESIZE_LARGE] == 1024
        assert budget.breached


def test_timeout_and_unsupported_callback_are_bounded() -> None:
    pytest.importorskip("curl_cffi")
    pytest.importorskip("yfinance")
    budget = YahooRequestBudget(
        deadline=time.monotonic() + 5,
        request_timeout=0.05,
        max_response_bytes=32_768,
    )
    with local_server() as root:
        session = bounded_yahoo_session(budget)
        with pytest.raises(Exception, match=r"(timeout|Timeout|timed out)"):
            session.request("GET", f"{root}/slow")
        assert budget.requests == 1
        with pytest.raises(YahooBudgetError, match="unsupported_yahoo_transport_option"):
            session.request("GET", f"{root}/known/exact", content_callback=lambda _: 0)
        assert budget.breached


def test_deadline_aborts_callback_and_sticks(monkeypatch: pytest.MonkeyPatch) -> None:
    curl = pytest.importorskip("curl_cffi")
    pytest.importorskip("yfinance")
    base = curl.requests.Session
    original = base.request
    received: list[int] = []
    aborted = [False]

    def count_delivery(self: object, method: str, url: str, **kwargs: object) -> object:
        callback = kwargs["content_callback"]

        def counted(chunk: bytes) -> int:
            assert not aborted[0]
            received.append(len(chunk))
            result = callback(chunk)  # type: ignore[operator]
            if result != len(chunk):
                aborted[0] = True
            return result

        kwargs["content_callback"] = counted
        return original(self, method, url, **kwargs)

    monkeypatch.setattr(base, "request", count_delivery)
    calls = [0]

    def clock() -> float:
        calls[0] += 1
        return 0 if calls[0] <= 3 else 2

    budget = YahooRequestBudget(deadline=1, max_response_bytes=32_768, monotonic=clock)
    with (
        local_server() as root,
        pytest.raises(YahooBudgetError, match="yahoo_receive_limit_exceeded"),
    ):
        bounded_yahoo_session(budget).request("GET", f"{root}/chunked/exact")
    assert budget.breached
    assert aborted[0]
    assert received
