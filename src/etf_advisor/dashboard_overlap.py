"""Pure, conservative overlap of two attributed reported-holdings lists."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from fractions import Fraction
from typing import Any

from etf_advisor.data.research_quality import field_max_age, is_issuer_field, validate_issuer_pair
from etf_advisor.data.vanguard import PROVIDER as ISSUER_PROVIDER
from etf_advisor.encoding import decimal_value, decode_exposures, document_schema, strict_json
from etf_advisor.rag.evidence import CandidateEvidenceBundle
from etf_advisor.research.models import MissingReason, ResearchField, WeightedExposure

REASONS = (
    "invalid_evidence",
    "diagnostic_limit_exceeded",
    "missing_provenance",
    *(item.value for item in MissingReason),
    "empty_holdings",
    "invalid_holdings",
    "conflicting_provenance",
    "stale_holdings",
    "future_holdings",
    "missing_holding_symbol",
    "duplicate_holding_symbol",
    "duplicate_holding_name",
    "conflicting_holding_identity",
    "identity_namespace_mismatch",
)


def _reasons(values: set[str]) -> list[str]:
    return [reason for reason in REASONS if reason in values]


def exact_amount(value: Fraction | None) -> dict[str, str] | None:
    if value is None:
        return None
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def display_amount(value: dict[str, str] | None) -> str:
    """Round nonnegative rational percentage points half up at six places."""
    if value is None:
        return "Unavailable"
    numerator, denominator = int(value["numerator"]), int(value["denominator"])
    if numerator > 0 and numerator * 1_000_000 < denominator:
        return "<0.000001"
    scaled = (numerator * 2_000_000 + denominator) // (2 * denominator)
    return f"≈ {scaled // 1_000_000}.{scaled % 1_000_000:06d}"


def _side(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": candidate["document_id"],
        "symbol": candidate["symbol"],
        "status": "unavailable",
        "reason_codes": [],
        "count": None,
        "row_sum_pp": None,
        "provider": None,
        "source_url": None,
        "observed_at": None,
        "ingested_at": None,
        "field_snapshot_version": None,
    }


def _invalid(left_id: str, right_id: str, reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "reason_codes": [reason],
        "checked_at": None,
        "snapshot_version": None,
        "snapshot_digest": None,
        "left": _side({"document_id": left_id, "symbol": None}),
        "right": _side({"document_id": right_id, "symbol": None}),
        "overlap_pp": None,
        "matched_holdings": None,
    }


def _identity(item: dict[str, Any]) -> tuple[str | None, str | None]:
    symbol, name = item.get("symbol"), item.get("name")
    if not isinstance(name, str):
        raise ValueError("invalid_holdings")
    name = name.strip()
    if not 1 <= len(name) <= 300 or not name.isprintable():
        raise ValueError("invalid_holdings")
    if symbol is None:
        return None, " ".join(name.split()).casefold()
    if not isinstance(symbol, str):
        raise ValueError("invalid_holdings")
    symbol = symbol.strip()
    if not 1 <= len(symbol) <= 24 or any(ord(char) < 33 or ord(char) > 126 for char in symbol):
        raise ValueError("invalid_holdings")
    return symbol.upper(), " ".join(name.split()).casefold()


def _read_side(
    bundle: dict[str, Any], candidate: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, tuple[str, Fraction]]]:
    side = _side(candidate)
    reasons: set[str] = set()
    identities: dict[str, tuple[str, Fraction]] = {}
    metadata = candidate["metadata"]
    raw = metadata.get("field_provenance_json")
    if not isinstance(raw, str):
        reasons.add("missing_provenance")
        side["reason_codes"] = _reasons(reasons)
        return side, identities
    try:
        raw_bytes = raw.encode("utf-8")
    except UnicodeEncodeError:
        side["reason_codes"] = ["invalid_holdings"]
        return side, identities
    if len(raw_bytes) > 1_048_576:
        reasons.add("diagnostic_limit_exceeded")
        side["reason_codes"] = _reasons(reasons)
        return side, identities
    try:
        fields = strict_json(raw)
        if not isinstance(fields, dict) or not isinstance(fields.get("top_holdings"), dict):
            raise ValueError("missing_provenance")
        wire = fields["top_holdings"]
        values = wire.get("value")
        schema = document_schema(metadata)
        if values is not None and (not isinstance(values, list) or len(values) > 1000):
            raise ValueError(
                "diagnostic_limit_exceeded" if isinstance(values, list) else "invalid_holdings"
            )
        if wire.get("unit") != "percent_of_fund":
            raise ValueError("invalid_holdings")
        # Validate the complete consumed field independently of the document validator's
        # schema-1 early return. Schema-2 decoding precedes issuer-pair validation.
        decoded = decode_exposures(values) if schema == 2 and values is not None else values
        field = ResearchField[list[WeightedExposure]].model_validate({**wire, "value": decoded})
        if (
            metadata.get("snapshot_version") is not None
            and field.snapshot_version != metadata["snapshot_version"]
        ):
            raise ValueError("conflicting_provenance")
        expected_status = (
            "available" if field.missing_reason is None else field.missing_reason.value
        )
        if metadata.get("top_holdings_status") != expected_status:
            raise ValueError("conflicting_provenance")
        if any(
            isinstance(value, dict) and value.get("provider") == ISSUER_PROVIDER
            for value in fields.values()
        ):
            pair: dict[str, ResearchField[Any]] = {}
            for name, pair_wire in fields.items():
                if isinstance(pair_wire, dict):
                    pair_value = pair_wire.get("value")
                    if (
                        schema == 2
                        and name in {"top_holdings", "sector_exposures", "geography_exposures"}
                        and pair_value is not None
                    ):
                        pair_value = decode_exposures(pair_value)
                    pair[name] = ResearchField[Any].model_validate(
                        {**pair_wire, "value": pair_value}
                    )
            validate_issuer_pair(candidate["symbol"], pair)
        side.update(
            {
                "provider": field.provider,
                "source_url": field.source_url,
                "observed_at": field.observed_at.isoformat().replace("+00:00", "Z"),
                "ingested_at": field.ingested_at.isoformat().replace("+00:00", "Z"),
                "field_snapshot_version": field.snapshot_version,
            }
        )
        if field.missing_reason is not None:
            reasons.add(field.missing_reason.value)
            side["reason_codes"] = _reasons(reasons)
            return side, identities
        assert isinstance(values, list)
        side["count"] = len(values)
        if not values:
            reasons.add("empty_holdings")
        total = Fraction(0)
        symbols: set[str] = set()
        names: set[str] = set()
        for item in values:
            if not isinstance(item, dict):
                raise ValueError("invalid_holdings")
            if schema == 1:
                if set(item) - {"name", "symbol", "weight_pct"}:
                    raise ValueError("invalid_holdings")
                number = item.get("weight_pct")
                if type(number) is int:
                    amount = Fraction(number)
                elif type(number) is float and math.isfinite(number):
                    amount = Fraction.from_float(number)
                else:
                    raise ValueError("invalid_holdings")
            else:
                if set(item) - {"name", "symbol", "weight_pct_token", "source_weight_pct_decimal"}:
                    raise ValueError("invalid_holdings")
                amount = Fraction(decimal_value(item.get("source_weight_pct_decimal")))
            if not 0 <= amount <= 100:
                raise ValueError("invalid_holdings")
            total += amount
            symbol_key, name_key = _identity(item)
            assert name_key is not None
            if symbol_key is None:
                reasons.add("missing_holding_symbol")
            elif symbol_key in symbols:
                reasons.add("duplicate_holding_symbol")
            if name_key in names:
                reasons.add("duplicate_holding_name")
            names.add(name_key)
            if symbol_key is not None:
                symbols.add(symbol_key)
                identities[symbol_key] = (name_key, amount)
        if total > 100:
            raise ValueError("invalid_holdings")
        checked_at = datetime.fromisoformat(bundle["checked_at"].replace("Z", "+00:00"))
        observed_at = field.observed_at
        if (
            is_issuer_field(
                symbol=candidate["symbol"],
                field_name="top_holdings",
                provider=field.provider,
                source_url=field.source_url,
                observed_at=observed_at,
            )
            or field.provider == ISSUER_PROVIDER
        ):
            tolerance = timedelta(0)
        else:
            tolerance = timedelta(minutes=bundle["health"]["future_tolerance_minutes"])
        age = field_max_age(
            symbol=candidate["symbol"],
            field_name="top_holdings",
            provider=field.provider,
            source_url=field.source_url,
            observed_at=observed_at,
            default=timedelta(hours=bundle["health"]["max_age_hours"]),
        )
        if observed_at > checked_at + tolerance:
            reasons.add("future_holdings")
        if checked_at - observed_at > age:
            reasons.add("stale_holdings")
        if (
            "future_holdings" not in reasons
            and "stale_holdings" not in reasons
            and "empty_holdings" not in reasons
        ):
            side["row_sum_pp"] = exact_amount(total)
            side["status"] = "available" if not reasons else "unavailable"
        side["reason_codes"] = _reasons(reasons)
        return side, identities
    except Exception as exc:
        # Keep untrusted exception details out of the JSON/UI surface.
        reason = str(exc) if type(exc) is ValueError and str(exc) in REASONS else "invalid_holdings"
        side.update(
            {
                "status": "unavailable",
                "reason_codes": [reason],
                "count": None,
                "row_sum_pp": None,
                "provider": None,
                "source_url": None,
                "observed_at": None,
                "ingested_at": None,
                "field_snapshot_version": None,
            }
        )
        return side, {}


def reported_holdings_overlap(
    bundle: dict[str, Any], left_id: str, right_id: str
) -> dict[str, Any]:
    """Compare exact reported rows without changing source evidence or graph state."""
    if not isinstance(bundle, dict) or not isinstance(bundle.get("candidates"), list):
        return _invalid(left_id, right_id, "invalid_evidence")
    ids = [item.get("document_id") for item in bundle["candidates"] if isinstance(item, dict)]
    if left_id == right_id or left_id not in ids or right_id not in ids:
        raise ValueError("Overlap selection requires two distinct validated document IDs.")
    if len(bundle["candidates"]) > 100:
        return _invalid(left_id, right_id, "diagnostic_limit_exceeded")
    for candidate in bundle["candidates"]:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("metadata"), dict):
            return _invalid(left_id, right_id, "invalid_evidence")
        raw = candidate["metadata"].get("field_provenance_json")
        if isinstance(raw, str):
            try:
                raw_bytes = raw.encode("utf-8")
            except UnicodeEncodeError:
                return _invalid(left_id, right_id, "invalid_evidence")
            if len(raw_bytes) > 1_048_576:
                return _invalid(left_id, right_id, "diagnostic_limit_exceeded")
    try:
        detached = json.loads(json.dumps(bundle, allow_nan=False))
        if detached != bundle:
            return _invalid(left_id, right_id, "invalid_evidence")
        validated = CandidateEvidenceBundle.model_validate(detached).model_dump(mode="json")
    except (TypeError, ValueError):
        return _invalid(left_id, right_id, "invalid_evidence")
    candidates = {item["document_id"]: item for item in validated["candidates"]}
    left, left_keys = _read_side(validated, candidates[left_id])
    right, right_keys = _read_side(validated, candidates[right_id])
    reasons = set(left["reason_codes"] + right["reason_codes"])
    if (
        left["provider"] is not None
        and right["provider"] is not None
        and left["provider"] != right["provider"]
    ):
        reasons.add("identity_namespace_mismatch")
    for symbol, (name, _) in left_keys.items():
        if symbol in right_keys and right_keys[symbol][0] != name:
            reasons.add("conflicting_holding_identity")
        if symbol not in right_keys and any(
            other_name == name for other_name, _ in right_keys.values()
        ):
            reasons.add("conflicting_holding_identity")
    for symbol, (name, _) in right_keys.items():
        if symbol not in left_keys and any(
            other_name == name for other_name, _ in left_keys.values()
        ):
            reasons.add("conflicting_holding_identity")
    overlap: Fraction | None = None
    matches: int | None = None
    if not reasons:
        shared = left_keys.keys() & right_keys.keys()
        overlap = sum((min(left_keys[key][1], right_keys[key][1]) for key in shared), Fraction(0))
        matches = len(shared)
        left_sum = left["row_sum_pp"]
        right_sum = right["row_sum_pp"]
        assert left_sum is not None and right_sum is not None
        assert (
            0
            <= overlap
            <= min(
                Fraction(int(left_sum["numerator"]), int(left_sum["denominator"])),
                Fraction(int(right_sum["numerator"]), int(right_sum["denominator"])),
            )
            <= 100
        )
    return {
        "status": "available" if not reasons else "unavailable",
        "reason_codes": _reasons(reasons),
        "checked_at": validated["checked_at"],
        "snapshot_version": validated["snapshot_version"],
        "snapshot_digest": validated["snapshot_digest"],
        "left": left,
        "right": right,
        "overlap_pp": exact_amount(overlap),
        "matched_holdings": matches,
    }
