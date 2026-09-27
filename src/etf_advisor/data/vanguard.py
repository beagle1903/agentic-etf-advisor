"""Bounded, replaceable official BND holdings boundary and exact pure parser."""

from __future__ import annotations

import http.client
import json
import re
import socket
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from threading import Event, Lock, Thread, Timer
from typing import Any, Protocol

from etf_advisor.encoding import decimal_token, upward
from etf_advisor.research.models import WeightedExposure

BND_URL = "https://advisors.vanguard.com/investments/products/api/funds/0928/holdings/latest"
PROVIDER = "vanguard_advisors"
MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 25_000


class IssuerSourceError(ValueError):
    """A sanitized official-source failure; raw transport/content never escapes."""


class _ConnectionSetupTimeout(TimeoutError):
    """The caller's connection wait budget expired, rather than a socket error."""


@dataclass(frozen=True)
class IssuerHoldings:
    observed_at: datetime
    holdings: list[WeightedExposure]
    concentration: float
    row_count: int
    placeholders: int
    blank_percentages: int
    negative_percentages: int


class IssuerHoldingsClient(Protocol):
    def fetch(self) -> IssuerHoldings: ...


class StreamingResponse(Protocol):
    status: int

    def getheader(self, name: str) -> str | None: ...

    def read(self, amount: int) -> bytes: ...

    def close(self) -> None: ...


class HoldingsTransport(Protocol):
    def open(
        self, *, connect_timeout: float, read_timeout: float, deadline: float
    ) -> StreamingResponse: ...


class DeadlineTimer(Protocol):
    def start(self) -> None: ...

    def cancel(self) -> None: ...


def _timer(seconds: float, callback: Callable[[], None]) -> DeadlineTimer:
    timer = Timer(seconds, callback)
    timer.daemon = True
    return timer


def _connect(timeout: float) -> http.client.HTTPSConnection:
    """Bound caller latency even when a resolver ignores the socket timeout.

    Only the worker owns the connection until successful handoff. Abandonment
    transfers cleanup to the worker; it never sends an HTTP request.
    """
    completed = Event()
    ownership = Lock()
    abandoned = False
    connection: http.client.HTTPSConnection | None = None
    failure: Exception | None = None

    def discard(candidate: http.client.HTTPSConnection) -> None:
        with suppress(OSError, http.client.HTTPException):
            candidate.close()

    def setup() -> None:
        nonlocal connection, failure
        candidate: http.client.HTTPSConnection | None = None
        error: Exception | None = None
        try:
            candidate = http.client.HTTPSConnection("advisors.vanguard.com", timeout=timeout)
            candidate.connect()
        except Exception as caught:
            error = caught
        with ownership:
            if not abandoned and error is None:
                connection = candidate
                candidate = None  # Ownership transfers to the caller.
            else:
                failure = error
            completed.set()
        if candidate is not None:
            discard(candidate)

    started = time.monotonic()
    Thread(target=setup, daemon=True, name="vanguard-connect").start()
    ready = completed.wait(max(0, timeout - (time.monotonic() - started)))
    with ownership:
        if not ready or time.monotonic() - started >= timeout:
            abandoned = True
            if connection is not None:
                # Setup won the handoff race, but the caller's budget expired.
                Thread(target=discard, args=(connection,), daemon=True).start()
            raise _ConnectionSetupTimeout("issuer_connect_timeout")
        if failure is not None:
            raise failure
        if connection is None:
            raise OSError("connection unavailable")
        return connection


class _HTTPSResponse:
    def __init__(
        self,
        connection: http.client.HTTPSConnection,
        response: http.client.HTTPResponse,
        timer: DeadlineTimer,
        expired: Event,
    ):
        self.connection = connection
        self.response = response
        self.status = response.status
        self.timer = timer
        self.expired = expired

    def getheader(self, name: str) -> str | None:
        return self.response.getheader(name)

    def read(self, amount: int) -> bytes:
        try:
            result = self.response.read(amount)
        except (OSError, http.client.HTTPException):
            if self.expired.is_set():
                raise IssuerSourceError("issuer_elapsed_limit") from None
            raise
        if self.expired.is_set():
            raise IssuerSourceError("issuer_elapsed_limit")
        return result

    def close(self) -> None:
        self.timer.cancel()
        try:
            self.response.close()
        finally:
            self.connection.close()


class HTTPSHoldingsTransport:
    """Fixed host/path, TLS validation and no redirect handling."""

    def __init__(
        self,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        timer_factory: Callable[[float, Callable[[], None]], DeadlineTimer] = _timer,
    ):
        self.monotonic = monotonic
        self.timer_factory = timer_factory

    def open(
        self, *, connect_timeout: float, read_timeout: float, deadline: float
    ) -> StreamingResponse:
        remaining = deadline - self.monotonic()
        if remaining <= 0:
            raise IssuerSourceError("issuer_elapsed_limit")
        expired = Event()
        connection: http.client.HTTPSConnection | None = None
        connected_socket: socket.socket | None = None

        def abort() -> None:
            expired.set()
            # Retain the actual socket: HTTPResponse may own it after Connection detaches.
            stream = connected_socket
            if stream is None and connection is not None:
                stream = connection.sock
            if stream is not None:
                with suppress(OSError):
                    stream.shutdown(socket.SHUT_RDWR)

        timer = self.timer_factory(remaining, abort)
        timer.start()
        try:
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                raise IssuerSourceError("issuer_elapsed_limit")
            try:
                connection = _connect(min(connect_timeout, remaining))
            except _ConnectionSetupTimeout:
                if remaining <= connect_timeout:
                    raise IssuerSourceError("issuer_elapsed_limit") from None
                raise
            if connection.sock is None:
                raise OSError("connection unavailable")
            connected_socket = connection.sock
            if expired.is_set() or self.monotonic() >= deadline:
                abort()
                raise IssuerSourceError("issuer_elapsed_limit")
            connection.sock.settimeout(read_timeout)
            connection.request(
                "GET",
                "/investments/products/api/funds/0928/holdings/latest",
                headers={"Accept": "application/json", "Accept-Encoding": "identity"},
            )
            response = connection.getresponse()
            if expired.is_set():
                response.close()
                raise IssuerSourceError("issuer_elapsed_limit")
            return _HTTPSResponse(connection, response, timer, expired)
        except Exception:
            timer.cancel()
            if connection is not None:
                connection.close()
            if expired.is_set() or self.monotonic() >= deadline:
                raise IssuerSourceError("issuer_elapsed_limit") from None
            raise


class VanguardHoldingsClient:
    def __init__(
        self,
        *,
        transport: HoldingsTransport | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.transport = transport or HTTPSHoldingsTransport(monotonic=monotonic)
        self.monotonic = monotonic

    def fetch(self) -> IssuerHoldings:
        started = self.monotonic()
        for attempt in range(3):
            response: StreamingResponse | None = None
            try:
                if self.monotonic() - started >= 90:
                    raise IssuerSourceError("issuer_elapsed_limit")
                response = self.transport.open(
                    connect_timeout=5, read_timeout=10, deadline=started + 90
                )
                if response.status in {429, 500, 502, 503, 504}:
                    if attempt < 2:
                        continue
                    raise IssuerSourceError("issuer_unavailable")
                if response.status != 200:
                    raise IssuerSourceError("issuer_http_status")
                if response.getheader("Content-Encoding") not in {None, "identity"}:
                    raise IssuerSourceError("issuer_content_encoding")
                body = bytearray()
                while True:
                    if self.monotonic() - started >= 90:
                        raise IssuerSourceError("issuer_elapsed_limit")
                    chunk = response.read(min(65536, MAX_BYTES + 1 - len(body)))
                    if self.monotonic() - started >= 90:
                        raise IssuerSourceError("issuer_elapsed_limit")
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise IssuerSourceError("issuer_byte_limit")
                result = parse_holdings(bytes(body))
                if self.monotonic() - started >= 90:
                    raise IssuerSourceError("issuer_elapsed_limit")
                return result
            except IssuerSourceError:
                raise
            except (OSError, http.client.HTTPException):
                if attempt == 2:
                    raise IssuerSourceError("issuer_unavailable") from None
            finally:
                if response is not None:
                    with suppress(OSError, http.client.HTTPException):
                        response.close()
        raise IssuerSourceError("issuer_unavailable")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IssuerSourceError("issuer_duplicate_key")
        result[key] = value
    return result


def _number(value: Any) -> Decimal:
    if not isinstance(value, str) or len(value) > 100:
        raise IssuerSourceError("issuer_numeric")
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]{1,3})?", value) is None:
        raise IssuerSourceError("issuer_numeric")
    parsed = Decimal(value)
    if not parsed.is_finite() or abs(parsed.adjusted()) > 100:
        raise IssuerSourceError("issuer_numeric")
    return parsed


def parse_holdings(body: bytes) -> IssuerHoldings:
    """Validate every scoped row before selecting exactly ten by market value."""
    if len(body) > MAX_BYTES:
        raise IssuerSourceError("issuer_byte_limit")
    try:
        payload = json.loads(
            body,
            object_pairs_hook=_object,
            parse_int=str,
            parse_float=str,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(payload, dict):
            raise ValueError()
        date = payload["latestEffectiveDate"]
        if not isinstance(date, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) is None:
            raise ValueError()
        observed_at = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
        if set(payload) != {"latestEffectiveDate", date} or not isinstance(payload[date], dict):
            raise ValueError()
        ranked: list[tuple[Decimal, int, int, str, str | None, Decimal | None]] = []
        count = placeholders = blanks = negatives = 0
        for collection_rank, collection in enumerate(("fixedIncome", "shortTermReserves")):
            rows = payload[date][collection]
            if not isinstance(rows, list):
                raise ValueError()
            count += len(rows)
            if count > MAX_ROWS:
                raise IssuerSourceError("issuer_row_limit")
            for index, row in enumerate(rows):
                if not isinstance(row, dict):
                    raise ValueError()
                name = row.get("holdingName")
                if not isinstance(name, str) or not name.strip() or len(name) > 300:
                    raise ValueError()
                percentage = row["percentOfFunds"]
                market = row["marketValue"]
                if percentage == "" and market == "" and row.get("faceAmount") == "":
                    placeholders += 1
                    blanks += 1
                    continue
                market_value = _number(market)
                weight = None if percentage == "" else _number(percentage)
                blanks += weight is None
                negatives += weight is not None and weight < 0
                ticker = row.get("ticker")
                if ticker == "":
                    ticker = None
                if ticker is not None and (
                    not isinstance(ticker, str) or not ticker.strip() or len(ticker) > 24
                ):
                    raise ValueError()
                ranked.append((market_value, collection_rank, index, name, ticker, weight))
        ranked.sort(key=lambda row: (-Fraction(row[0]), row[1], row[2]))
        if len(ranked) < 10:
            raise ValueError()
        selected = ranked[:10]
        weights: list[Decimal] = []
        holdings: list[WeightedExposure] = []
        for market, _, _, name, ticker, weight in selected:
            if market < 0 or weight is None or not 0 <= weight <= 100:
                raise ValueError()
            weights.append(weight)
            holdings.append(
                WeightedExposure(
                    name=name,
                    symbol=ticker,
                    weight_pct=upward(weight),
                    source_weight_pct_decimal=decimal_token(weight),
                )
            )
        total = sum((Fraction(weight) for weight in weights), start=Fraction(0))
        if total > 100:
            raise ValueError()
        return IssuerHoldings(
            observed_at, holdings, upward(total), count, placeholders, blanks, negatives
        )
    except IssuerSourceError:
        raise
    except (ValueError, KeyError, TypeError, ArithmeticError, UnicodeError, RecursionError):
        raise IssuerSourceError("issuer_shape") from None
