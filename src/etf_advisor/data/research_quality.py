"""One pure per-field freshness policy for publication and downstream replay."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from etf_advisor.data.quality import MarketDataHealthReport, assess_observations
from etf_advisor.data.vanguard import BND_URL, PROVIDER
from etf_advisor.research.models import ETFResearchSnapshot, ResearchField

ISSUER_FIELDS = frozenset({"top_holdings", "top_10_concentration_pct"})


def field_max_age(
    *,
    symbol: str,
    field_name: str,
    provider: str,
    source_url: str,
    observed_at: datetime,
    default: timedelta,
) -> timedelta:
    if is_issuer_field(
        symbol=symbol,
        field_name=field_name,
        provider=provider,
        source_url=source_url,
        observed_at=observed_at,
    ):
        return timedelta(hours=1080)
    return default


def is_issuer_field(
    *, symbol: str, field_name: str, provider: str, source_url: str, observed_at: datetime
) -> bool:
    return (
        symbol == "BND"
        and field_name in ISSUER_FIELDS
        and provider == PROVIDER
        and source_url == BND_URL
        and observed_at.hour == 0
        and observed_at.minute == 0
        and observed_at.second == 0
        and observed_at.microsecond == 0
        and observed_at.utcoffset() == timedelta(0)
    )


def validate_issuer_pair(symbol: str, fields: dict[str, ResearchField[Any]]) -> None:
    pair = [fields.get(name) for name in sorted(ISSUER_FIELDS)]
    if not any(item is not None and item.provider == PROVIDER for item in fields.values()):
        return
    if symbol != "BND" or any(
        item is None
        or item.provider != PROVIDER
        or item.source_url != BND_URL
        or item.missing_reason is not None
        for item in pair
    ):
        raise ValueError("issuer_provenance_pair")
    first, second = pair
    assert first is not None and second is not None
    holdings = fields["top_holdings"].value
    if not isinstance(holdings, list) or len(holdings) != 10:
        raise ValueError("issuer_holdings_count")
    if (
        first.observed_at != second.observed_at
        or first.ingested_at != second.ingested_at
        or first.snapshot_version != second.snapshot_version
        or field_max_age(
            symbol=symbol,
            field_name="top_holdings",
            provider=first.provider,
            source_url=first.source_url,
            observed_at=first.observed_at,
            default=timedelta(hours=120),
        )
        != timedelta(hours=1080)
        or any(
            item.provider == PROVIDER for name, item in fields.items() if name not in ISSUER_FIELDS
        )
    ):
        raise ValueError("issuer_provenance_pair")


def assess_research_fields(
    snapshot: ETFResearchSnapshot,
    *,
    checked_at: datetime,
    max_age: timedelta,
    future_tolerance: timedelta,
) -> MarketDataHealthReport:
    results = []
    for record in snapshot.records:
        fields = record.research_fields()
        validate_issuer_pair(record.symbol, fields)
        for name, field in fields.items():
            applied = field_max_age(
                symbol=record.symbol,
                field_name=name,
                provider=field.provider,
                source_url=field.source_url,
                observed_at=field.observed_at,
                default=max_age,
            )
            # ResearchField supplies the source boundary via this small detached projection.
            observation = SimpleNamespace(
                symbol=f"{record.symbol}.{name}",
                source=field.provider,
                source_url=field.source_url,
                observed_at=field.observed_at,
            )
            report = assess_observations(
                [observation],
                checked_at=checked_at,
                max_age=applied,
                future_tolerance=timedelta(0) if field.provider == PROVIDER else future_tolerance,
            )
            for result in report.observations:
                if field.provider == PROVIDER:
                    result.message += "; applied issuer window 1080 hours"
            results.extend(report.observations)
    return MarketDataHealthReport(
        checked_at=checked_at,
        max_age_hours=max_age.total_seconds() / 3600,
        future_tolerance_minutes=future_tolerance.total_seconds() / 60,
        healthy=bool(results) and all(item.status == "current" for item in results),
        observations=results,
    )
