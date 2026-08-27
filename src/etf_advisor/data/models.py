"""Normalized, timestamped market observations."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ETFObservation(BaseModel):
    """One source observation that can be rendered into a retrievable document."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=200)
    close_price: float = Field(ge=0)
    currency: str | None = Field(default=None, max_length=12)
    observed_at: datetime
    source: str = "yahoo_finance"
    source_url: str
    quote_type: str | None = Field(default=None, max_length=40)
    category: str | None = Field(default=None, max_length=120)
    fund_family: str | None = Field(default=None, max_length=160)
    expense_ratio_pct: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Annual fund expenses expressed in percentage points, not a decimal fraction.",
    )
    description: str = Field(default="", max_length=4000)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
