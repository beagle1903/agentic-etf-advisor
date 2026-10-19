"""Bounded ECB EUR/USD reference-rate adapter."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

from etf_advisor.clock import Clock
from etf_advisor.domain.us_eu import FX_URL, FxReferenceObservation, canonical_rate


class FxReferenceProvider(Protocol):
    def fetch_eur_usd(self) -> FxReferenceObservation: ...


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self, request: Request, fp: object, code: int, msg: str, headers: object, newurl: str
    ) -> None:
        return None


def parse_ecb_daily(data: bytes, observed_at: datetime) -> FxReferenceObservation:
    if (
        len(data) > 65_536
        or b"\x00" in data
        or b"<!DOCTYPE" in data.upper()
        or b"<!ENTITY" in data.upper()
    ):
        raise ValueError("ECB response exceeds bound or contains XML declarations.")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError("ECB response is malformed XML.") from exc
    dated = [element for element in root.iter() if "time" in element.attrib]
    if len(dated) != 1:
        raise ValueError("ECB response requires one effective date.")
    try:
        effective = date.fromisoformat(dated[0].attrib["time"])
    except ValueError as exc:
        raise ValueError("ECB effective date is invalid.") from exc
    usd = [element for element in root.iter() if element.attrib.get("currency") == "USD"]
    if len(usd) != 1 or usd[0] not in list(dated[0].iter()) or "rate" not in usd[0].attrib:
        raise ValueError("ECB response requires one USD rate.")
    rate = usd[0].attrib["rate"]
    canonical_rate(rate)
    return FxReferenceObservation(
        status="available",
        effective_date=effective,
        observed_at=observed_at,
        rate_decimal=rate,
        missing_reason=None,
    )


class EcbFxClient:
    """HTTPS one-shot GET with a fixed endpoint and bounded response."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def fetch_eur_usd(self) -> FxReferenceObservation:
        opener = build_opener(_RejectRedirects())
        request = Request(FX_URL, headers={"Accept": "application/xml"})
        try:
            with opener.open(request, timeout=10) as response:
                if response.status != 200 or response.url != FX_URL:
                    raise ValueError("ECB returned an unsupported response.")
                data = response.read(65_537)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ValueError("ECB reference rate unavailable.") from exc
        return parse_ecb_daily(data, self._clock().astimezone(UTC))
