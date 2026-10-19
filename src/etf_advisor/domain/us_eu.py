"""Frozen US/EU listing and currency facts (Issue 104)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any, Final, Literal, cast

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from etf_advisor.catalogue.mapping import EXCHANGE_MAP

ADVISORY_CONTRACT = "us-eu-v1"
FX_URL: Final = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
_RATE = re.compile(r"(?:0\.[0-9]*[1-9]|[1-9][0-9]*(?:\.[0-9]*[1-9])?)\Z")
_GROUP = re.compile(r"[A-Za-z][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._:-]*\Z")


def listing_region(exchange: str) -> Literal["US", "EU"] | None:
    entry = EXCHANGE_MAP.get(exchange)
    return cast(Literal["US", "EU"], entry[1]) if entry is not None else None


def contract_fields(marker: Literal["us-eu-v1"] | None) -> dict[str, Any]:
    """Omit the marker completely for exact legacy wire compatibility."""
    return {"advisory_contract": marker} if marker is not None else {}


def valid_isin(value: str) -> bool:
    if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value) is None:
        return False
    expanded = "".join(str(ord(c) - 55) if c.isalpha() else c for c in value)
    digits = [int(c) for c in expanded]
    total = sum(
        sum(divmod(digit * (2 if (len(digits) - index) % 2 == 0 else 1), 10))
        for index, digit in enumerate(digits)
    )
    return total % 10 == 0


def valid_group_id(value: str) -> bool:
    return _GROUP.fullmatch(value) is not None


def canonical_rate(value: str) -> Decimal:
    if not isinstance(value, str) or _RATE.fullmatch(value) is None:
        raise ValueError("ECB rate must be canonical plain decimal.")
    try:
        rate = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("ECB rate is invalid.") from exc
    if not Decimal("0.000001") <= rate <= Decimal("1000000"):
        raise ValueError("ECB rate is outside supported bounds.")
    exponent = rate.as_tuple().exponent
    assert isinstance(exponent, int)
    if len(rate.as_tuple().digits) > 18 or max(0, -exponent) > 10:
        raise ValueError("ECB rate exceeds supported precision.")
    return rate


class FxReferenceObservation(BaseModel):
    """One attributable ECB rate or an explicit unavailable result."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["available", "missing"]
    provider: Literal["ecb"] = "ecb"
    source_url: Literal["https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"] = FX_URL
    effective_date: date | None
    observed_at: datetime
    base_currency: Literal["EUR"] = "EUR"
    quote_currency: Literal["USD"] = "USD"
    rate_decimal: str | None
    missing_reason: Literal["not_requested", "source_unavailable"] | None

    @field_validator("observed_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("FX observation requires a UTC-aware timestamp.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def complete_status(self) -> FxReferenceObservation:
        if self.status == "available":
            if (
                self.effective_date is None
                or self.rate_decimal is None
                or self.missing_reason is not None
            ):
                raise ValueError("Available FX requires date and rate.")
            canonical_rate(self.rate_decimal)
            if self.observed_at.date() < self.effective_date:
                raise ValueError("FX observation precedes effective date.")
        elif (
            self.effective_date is not None
            or self.rate_decimal is not None
            or self.missing_reason is None
        ):
            raise ValueError("Missing FX requires a missing reason only.")
        return self

    def validate_at(self, checked_at: datetime) -> str | None:
        if self.status != "available":
            return "fx_missing"
        assert self.effective_date is not None
        if self.effective_date > checked_at.date():
            return "fx_future"
        if self.observed_at > checked_at + timedelta(minutes=5):
            return "fx_future"
        if checked_at - datetime.combine(self.effective_date, time.min, tzinfo=UTC) > timedelta(
            hours=120
        ):
            return "fx_stale"
        return None

    def identity(self) -> str:
        return hashlib.sha256(
            json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def convert_minor(amount: int, source: str, target: str, rate_text: str) -> int:
    if type(amount) is not int or amount < 0 or {source, target} != {"USD", "EUR"}:
        raise ValueError(
            "Conversion requires nonnegative minor units and different USD/EUR currencies."
        )
    rate = Fraction(canonical_rate(rate_text))
    exact = Fraction(amount) * (rate if source == "EUR" and target == "USD" else 1 / rate)
    # Exact rational half-up, independent of the ambient Decimal context.
    return (2 * exact.numerator + exact.denominator) // (2 * exact.denominator)
