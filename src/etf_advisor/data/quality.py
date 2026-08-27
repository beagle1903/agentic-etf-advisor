"""Deterministic freshness checks for timestamped market observations."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from etf_advisor.data.models import ETFObservation


class MarketDataQualityError(RuntimeError):
    """Raised when observations are unsafe to persist or use."""


class FreshnessStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    FUTURE = "future"


class ObservationHealth(BaseModel):
    """Freshness result with the provenance needed to investigate it."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    source: str
    source_url: str
    observed_at: datetime
    age_hours: float
    status: FreshnessStatus
    message: str


class MarketDataHealthReport(BaseModel):
    """A source-health snapshot produced before retrieval-store writes."""

    model_config = ConfigDict(extra="forbid")

    checked_at: datetime
    max_age_hours: float = Field(gt=0)
    future_tolerance_minutes: float = Field(ge=0)
    healthy: bool
    observations: list[ObservationHealth]

    def require_healthy(self) -> None:
        """Fail closed with enough detail to identify every rejected symbol."""

        failures = [item for item in self.observations if item.status != FreshnessStatus.CURRENT]
        if not self.observations:
            raise MarketDataQualityError("Market-data health check received no observations.")
        if failures:
            details = "; ".join(f"{item.symbol}: {item.message}" for item in failures)
            raise MarketDataQualityError(f"Market-data health check failed: {details}")


def assess_observations(
    observations: Sequence[ETFObservation],
    *,
    checked_at: datetime,
    max_age: timedelta,
    future_tolerance: timedelta = timedelta(minutes=5),
) -> MarketDataHealthReport:
    """Classify observations using an injected clock value for deterministic tests."""

    if checked_at.tzinfo is None:
        raise ValueError("checked_at must be timezone-aware.")
    if max_age <= timedelta(0):
        raise ValueError("max_age must be positive.")
    if future_tolerance < timedelta(0):
        raise ValueError("future_tolerance cannot be negative.")

    results: list[ObservationHealth] = []
    for observation in observations:
        age = checked_at - observation.observed_at
        age_hours = age.total_seconds() / 3600
        if observation.observed_at > checked_at + future_tolerance:
            status = FreshnessStatus.FUTURE
            message = f"observation is {abs(age_hours):.2f} hours ahead of the health-check clock"
        elif age > max_age:
            status = FreshnessStatus.STALE
            message = (
                f"observation is {age_hours:.2f} hours old; "
                f"maximum is {max_age.total_seconds() / 3600:g} hours"
            )
        else:
            status = FreshnessStatus.CURRENT
            message = "observation is within the configured freshness window"

        results.append(
            ObservationHealth(
                symbol=observation.symbol,
                source=observation.source,
                source_url=observation.source_url,
                observed_at=observation.observed_at,
                age_hours=round(age_hours, 6),
                status=status,
                message=message,
            )
        )

    return MarketDataHealthReport(
        checked_at=checked_at,
        max_age_hours=max_age.total_seconds() / 3600,
        future_tolerance_minutes=future_tolerance.total_seconds() / 60,
        healthy=bool(results)
        and all(result.status == FreshnessStatus.CURRENT for result in results),
        observations=results,
    )
