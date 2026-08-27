"""Investor-profile inputs used by the advisory workflow."""

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

MAX_CASH_FLOW_USD: Final[int] = 1_000_000_000_000


class RiskTolerance(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class InvestmentObjective(StrEnum):
    INCOME = "income"
    BALANCED = "balanced"
    GROWTH = "growth"


class InvestorProfile(BaseModel):
    """A deliberately small profile for the first testable workflow."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    horizon_years: int = Field(ge=1, le=60)
    risk_tolerance: RiskTolerance
    objective: InvestmentObjective
    max_drawdown_pct: float = Field(gt=0, le=100)
    initial_investment_usd: float = Field(ge=0, le=MAX_CASH_FLOW_USD)
    recurring_monthly_usd: float = Field(default=0, ge=0, le=MAX_CASH_FLOW_USD)
    excluded_sectors: list[str] = Field(default_factory=list, max_length=25)
