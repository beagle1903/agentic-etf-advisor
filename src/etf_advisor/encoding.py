"""Strict, JSON-safe numeric encodings shared by publication and consumption."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from decimal import Decimal
from fractions import Fraction
from typing import Any, Self

from pydantic import BaseModel

NUMERIC_FIELDS = {"expense_ratio_pct", "average_daily_volume", "top_10_concentration_pct"}
EXPOSURE_FIELDS = {"top_holdings", "sector_exposures", "geography_exposures"}
FINGERPRINT_KEY = "document_fingerprint"
LEGACY_KEY = "etf_advisor_legacy_visibility"
_DECIMAL = re.compile(r"(?:0e0|[1-9][0-9]{0,1099}e(?:0|-?[1-9][0-9]*))\Z")


class StrictWireModel(BaseModel):
    """Reject duplicate object keys before typed wire/state validation."""

    @classmethod
    def model_validate_json(cls, json_data: str | bytes | bytearray, **kwargs: Any) -> Self:
        text = json_data if isinstance(json_data, str) else bytes(json_data).decode("utf-8")
        return cls.model_validate(strict_json(text), **kwargs)


class ResearchIntegrityError(ValueError):
    """Fixed diagnostics contain no rejected source data."""

    def __init__(self, code: str = "numeric_provenance") -> None:
        self.code = code
        super().__init__(
            f"Research evidence failed {code} validation. Republish validated evidence."
        )


def integrity_diagnostic(error: Exception) -> dict[str, str]:
    allowed = {
        "schema_encoding",
        "numeric_provenance",
        "document_integrity",
        "manifest_integrity",
        "projection_integrity",
        "retrieval_unavailable",
    }
    code = getattr(error, "code", None)
    if code not in allowed:
        errors = getattr(error, "errors", None)
        if callable(errors):
            for item in errors(include_url=False):
                candidate = getattr(item.get("ctx", {}).get("error"), "code", None)
                if candidate in allowed:
                    code = candidate
                    break
    if code not in allowed:
        code = "schema_encoding"
    if code == "retrieval_unavailable":
        return {
            "code": code,
            "message": "Source evidence retrieval failed. Check local stores and retry explicitly.",
        }
    return {
        "code": code,
        "message": f"Research evidence failed {code} validation. Republish validated evidence.",
    }


def schema_version(value: object) -> int:
    if value is None:
        raise ResearchIntegrityError("schema_encoding")
    if type(value) is not int or value not in (1, 2):
        raise ResearchIntegrityError("schema_encoding")
    return value


def strict_json(text: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ResearchIntegrityError("schema_encoding")
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=_reject_constant)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ResearchIntegrityError("schema_encoding") from exc


def _reject_constant(value: str) -> None:
    raise ResearchIntegrityError("numeric_provenance")


def binary_token(value: float) -> str:
    if type(value) is not float or not math.isfinite(value):
        raise ResearchIntegrityError()
    return repr(value)


def binary_value(value: object, *, maximum: float | None = None) -> float:
    if not isinstance(value, str):
        raise ResearchIntegrityError()
    try:
        number = float(value)
    except ValueError as exc:
        raise ResearchIntegrityError() from exc
    if not math.isfinite(number) or repr(number) != value or number < 0:
        raise ResearchIntegrityError()
    if maximum is not None and number > maximum:
        raise ResearchIntegrityError()
    return number


def decimal_token(value: Decimal) -> str:
    if not value.is_finite() or value < 0 or value > 100:
        raise ResearchIntegrityError()
    _sign, digits, exponent = value.as_tuple()
    if not any(digits):
        return "0e0"
    coefficient = "".join(str(digit) for digit in digits).lstrip("0")
    assert isinstance(exponent, int)
    while coefficient.endswith("0"):
        coefficient = coefficient[:-1]
        exponent += 1
    token = f"{coefficient}e{exponent}"
    decimal_value(token)
    return token


def decimal_value(value: object) -> Decimal:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ResearchIntegrityError()
    coefficient, exponent_text = value.split("e")
    if len(exponent_text) > 5:
        raise ResearchIntegrityError()
    exponent = int(exponent_text)
    if not -1100 <= exponent <= 2 or (coefficient != "0" and coefficient.endswith("0")):
        raise ResearchIntegrityError()
    parsed = Decimal(value)
    if parsed > 100:
        raise ResearchIntegrityError()
    return parsed


def upward(value: Decimal | Fraction) -> float:
    exact = Fraction(value)
    result = float(exact)
    if Fraction.from_float(result) < exact:
        result = math.nextafter(result, math.inf)
    return result


def decode_exposures(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ResearchIntegrityError()
    result: list[dict[str, Any]] = []
    total = Fraction(0)
    for item in value:
        if not isinstance(item, dict) or set(item) - {
            "name",
            "symbol",
            "weight_pct_token",
            "source_weight_pct_decimal",
        }:
            raise ResearchIntegrityError()
        exact = decimal_value(item.get("source_weight_pct_decimal"))
        number = binary_value(item.get("weight_pct_token"), maximum=100)
        if (
            not (exact == 0 and number == 0)
            and binary_token(upward(exact)) != item["weight_pct_token"]
        ):
            raise ResearchIntegrityError()
        total += Fraction(exact)
        result.append(
            {
                "name": item.get("name"),
                "symbol": item.get("symbol"),
                "weight_pct": number,
                "source_weight_pct_decimal": item["source_weight_pct_decimal"],
            }
        )
    if total > 100:
        raise ResearchIntegrityError()
    return result


def encode_fields(fields: dict[str, Any]) -> dict[str, Any]:
    result = {name: dict(field) for name, field in fields.items()}
    for name, field in result.items():
        value = field.get("value")
        if value is None:
            continue
        if name in NUMERIC_FIELDS:
            field["value"] = binary_token(float(value))
        elif name in EXPOSURE_FIELDS:
            field["value"] = [
                {
                    "name": item["name"],
                    "symbol": item.get("symbol"),
                    "weight_pct_token": binary_token(float(item["weight_pct"])),
                    "source_weight_pct_decimal": item.get("source_weight_pct_decimal"),
                }
                for item in value
            ]
            decode_exposures(field["value"])
    return result


def decode_fields(fields: object) -> dict[str, Any]:
    if not isinstance(fields, dict):
        raise ResearchIntegrityError()
    result: dict[str, Any] = {}
    for name, raw in fields.items():
        if not isinstance(raw, dict):
            raise ResearchIntegrityError()
        field = dict(raw)
        value = field.get("value")
        if value is not None and name in NUMERIC_FIELDS:
            field["value"] = binary_value(
                value, maximum=None if name == "average_daily_volume" else 100
            )
        elif value is not None and name in EXPOSURE_FIELDS:
            field["value"] = decode_exposures(value)
        result[name] = field
    return result


def document_fingerprint(document_id: str, content: str, metadata: Mapping[str, object]) -> str:
    retained = {
        key: value for key, value in metadata.items() if key not in {FINGERPRINT_KEY, LEGACY_KEY}
    }
    if any(type(value) not in {str, int, float, bool} for value in retained.values()):
        raise ResearchIntegrityError("document_integrity")
    try:
        encoded = json.dumps(
            {"document_id": document_id, "content": content, "metadata": retained},
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ResearchIntegrityError("document_integrity") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def document_schema(metadata: Mapping[str, object]) -> int:
    version = schema_version(metadata.get("field_provenance_schema_version", 1))
    if version == 1 and (
        FINGERPRINT_KEY in metadata or metadata.get("numeric_encoding") is not None
    ):
        raise ResearchIntegrityError("schema_encoding")
    if version == 2 and metadata.get("numeric_encoding") != "binary64-text-v1":
        raise ResearchIntegrityError("schema_encoding")
    if version == 1:
        raw = metadata.get("field_provenance_json")
        if isinstance(raw, str):
            reject_schema2_fields(strict_json(raw))
    return version


def reject_schema2_fields(fields: object) -> None:
    if not isinstance(fields, dict):
        raise ResearchIntegrityError("schema_encoding")
    for name, field in fields.items():
        if not isinstance(field, dict):
            raise ResearchIntegrityError("schema_encoding")
        value = field.get("value")
        if name in NUMERIC_FIELDS and value is not None and type(value) not in {float, int}:
            raise ResearchIntegrityError("schema_encoding")
        if name in EXPOSURE_FIELDS and isinstance(value, list):
            for item in value:
                if (
                    not isinstance(item, dict)
                    or "weight_pct_token" in item
                    or "source_weight_pct_decimal" in item
                ):
                    raise ResearchIntegrityError("schema_encoding")


def validate_document(
    document_id: str,
    content: str,
    metadata: Mapping[str, object],
    *,
    expected_fingerprint: str | None = None,
) -> int:
    version = document_schema(metadata)
    if version == 1:
        return version
    digest = metadata.get("snapshot_digest")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ResearchIntegrityError("document_integrity")
    expected_id = (
        f"research:{metadata.get('snapshot_version')}:{metadata.get('snapshot_digest')}:"
        f"{str(metadata.get('symbol')).lower()}"
    )
    if document_id != expected_id:
        raise ResearchIntegrityError("document_integrity")
    actual = document_fingerprint(document_id, content, metadata)
    if metadata.get(FINGERPRINT_KEY) != actual or (
        expected_fingerprint is not None and actual != expected_fingerprint
    ):
        raise ResearchIntegrityError("document_integrity")
    raw = metadata.get("field_provenance_json")
    if not isinstance(raw, str):
        raise ResearchIntegrityError()
    wire = strict_json(raw)
    decoded = decode_fields(wire)
    # Local import avoids the model -> codec dependency cycle.
    from etf_advisor.research.models import ETFResearchRecord, _render_field

    record = ETFResearchRecord.model_validate({"symbol": metadata.get("symbol"), **decoded})
    fields = record.research_fields()
    if (
        metadata.get("symbol") != record.symbol
        or metadata.get("source") != record.name.provider
        or metadata.get("source_url") != record.name.source_url
        or metadata.get("observed_at")
        != max(field.observed_at for field in fields.values()).isoformat().replace("+00:00", "Z")
        or any(field.ingested_at != record.name.ingested_at for field in fields.values())
        or metadata.get("ingested_at") != record.name.ingested_at.isoformat().replace("+00:00", "Z")
    ):
        raise ResearchIntegrityError()
    expected_wire = encode_fields(
        {name: field.model_dump(mode="json") for name, field in fields.items()}
    )
    if raw != json.dumps(expected_wire, sort_keys=True, separators=(",", ":")):
        raise ResearchIntegrityError()
    units = {
        "expense_ratio_pct": "percent",
        "average_daily_volume": "shares_per_day",
        "top_10_concentration_pct": "percent",
        **{name: "percent_of_fund" for name in EXPOSURE_FIELDS},
    }
    for name, unit in units.items():
        if fields[name].unit != unit:
            raise ResearchIntegrityError()
    holdings = wire["top_holdings"]["value"]
    concentration = wire["top_10_concentration_pct"]["value"]
    if holdings is not None and concentration is not None:
        exact = sum(
            (Fraction(decimal_value(item["source_weight_pct_decimal"])) for item in holdings[:10]),
            start=Fraction(0),
        )
        if binary_token(upward(exact)) != concentration:
            raise ResearchIntegrityError()
    lines = [
        f"ETF symbol: {record.symbol}",
        f"Research snapshot: {metadata.get('snapshot_version')}",
        f"Curated universe: {metadata.get('universe_id')} ({metadata.get('universe_version')})",
    ]
    for name, field in fields.items():
        status = "available" if field.missing_reason is None else field.missing_reason.value
        if metadata.get(f"{name}_status") != status or field.snapshot_version != metadata.get(
            "snapshot_version"
        ):
            raise ResearchIntegrityError()
        if field.value is None:
            if name in metadata:
                raise ResearchIntegrityError()
        elif name not in EXPOSURE_FIELDS and metadata.get(name) != wire[name]["value"]:
            raise ResearchIntegrityError()
        lines.append(_render_field(name, field))
    if content != "\n".join(lines):
        raise ResearchIntegrityError("document_integrity")
    return version
