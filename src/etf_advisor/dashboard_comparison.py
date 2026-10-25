"""Pure, field-attributed comparison of already validated review evidence."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from etf_advisor.data.research_quality import field_max_age
from etf_advisor.data.vanguard import PROVIDER as ISSUER_PROVIDER
from etf_advisor.encoding import document_schema, strict_json

COMPARISON_FIELDS = (
    ("expense_ratio_pct", "Expense ratio"),
    ("average_daily_volume", "Average daily volume"),
    ("category", "Category"),
    ("benchmark", "Benchmark"),
    ("top_holdings", "Top holdings"),
    ("sector_exposures", "Sector exposures"),
    ("geography_exposures", "Geography exposures"),
    ("top_10_concentration_pct", "Top-ten concentration"),
)
_NUMERIC = {"expense_ratio_pct", "average_daily_volume", "top_10_concentration_pct"}
_EXPOSURES = {"top_holdings", "sector_exposures", "geography_exposures"}


def comparison_rows(bundle: dict[str, Any], selected_ids: list[str]) -> list[dict[str, str]]:
    """Project selected field facts without changing evidence or checkpoint content."""

    candidates = {item["document_id"]: item for item in bundle["candidates"]}
    if len(selected_ids) != len(set(selected_ids)) or any(
        document_id not in candidates for document_id in selected_ids
    ):
        raise ValueError("Comparison selection must use unique validated candidates.")
    rows: list[dict[str, str]] = []
    for document_id in selected_ids:
        candidate = candidates[document_id]
        metadata = candidate["metadata"]
        try:
            fields = strict_json(metadata["field_provenance_json"])
            schema = document_schema(metadata)
        except (KeyError, TypeError, ValueError):
            fields = {}
            schema = 1
        for name, label in COMPARISON_FIELDS:
            field = fields.get(name) if isinstance(fields, dict) else None
            rows.append(_field_row(bundle, candidate, field, name, label, schema))
    return rows


def _field_row(
    bundle: dict[str, Any],
    candidate: dict[str, Any],
    field: Any,
    name: str,
    label: str,
    schema: int,
) -> dict[str, str]:
    row = {
        "Symbol": candidate["symbol"],
        "Field": label,
        "Value": "Unavailable",
        "Unit": "—",
        "Status": "missing provenance",
        "Source": "—",
        "Source URL": "—",
        "Observed (UTC)": "—",
    }
    if not isinstance(field, dict):
        return row
    unit = field.get("unit")
    provider = field.get("provider")
    url = field.get("source_url")
    observed = field.get("observed_at")
    if isinstance(unit, str) and unit:
        row["Unit"] = unit
    if isinstance(provider, str) and provider:
        row["Source"] = provider
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        row["Source URL"] = url
    if isinstance(observed, str) and observed:
        row["Observed (UTC)"] = observed
    if "—" in (row["Unit"], row["Source"], row["Source URL"], row["Observed (UTC)"]):
        return row

    reason = field.get("missing_reason")
    value = field.get("value")
    if reason is not None or value is None:
        row["Status"] = str(reason or "not reported")
        return row
    try:
        observed_at = datetime.fromisoformat(row["Observed (UTC)"].replace("Z", "+00:00"))
        checked_at = datetime.fromisoformat(bundle["checked_at"].replace("Z", "+00:00"))
        health = bundle["health"]
        if observed_at.tzinfo is None or checked_at.tzinfo is None:
            return row
        tolerance = (
            timedelta(0)
            if provider == ISSUER_PROVIDER
            else timedelta(minutes=health["future_tolerance_minutes"])
        )
        max_age = field_max_age(
            symbol=candidate["symbol"],
            field_name=name,
            provider=row["Source"],
            source_url=row["Source URL"],
            observed_at=observed_at,
            default=timedelta(hours=health["max_age_hours"]),
        )
        if observed_at > checked_at + tolerance:
            row["Status"] = "future observation"
            return row
        if checked_at - observed_at > max_age:
            row["Status"] = "stale observation"
            return row
    except (KeyError, TypeError, ValueError, OverflowError):
        return row

    flat = candidate["metadata"].get(name)
    if name not in _EXPOSURES and flat is not None and flat != value:
        row["Status"] = "conflicting evidence"
        return row
    if name == "category" and candidate.get("category") not in (None, value):
        row["Status"] = "conflicting evidence"
        return row
    try:
        row["Value"] = _display_value(value, name, schema)
    except (TypeError, ValueError, KeyError):
        row["Status"] = "unsupported evidence"
        return row
    row["Status"] = "supported"
    return row


def _display_value(value: Any, name: str, schema: int) -> str:
    if name in _NUMERIC:
        if schema == 2 and not isinstance(value, str):
            raise ValueError("Schema-2 number lacks its exact token.")
        if type(value) not in {str, int, float}:
            raise ValueError("Unsupported numeric value.")
        return str(value)
    if name in _EXPOSURES:
        if not isinstance(value, list):
            raise ValueError("Unsupported exposure collection.")
        result = []
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise ValueError("Unsupported exposure.")
            weight = item["weight_pct_token"] if schema == 2 else item["weight_pct"]
            detail = f"{item['name']}: {weight}%"
            if schema == 2:
                detail += f" (source decimal {item['source_weight_pct_decimal']})"
            result.append(detail)
        return "; ".join(result) if result else "Reported empty list"
    if not isinstance(value, str):
        raise ValueError("Unsupported text value.")
    return value
