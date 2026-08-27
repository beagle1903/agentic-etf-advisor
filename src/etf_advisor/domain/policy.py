"""Deterministic, illustrative policy calculations for the review workflow."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from etf_advisor.domain.profile import InvestmentObjective, InvestorProfile, RiskTolerance

type AllocationBands = dict[str, list[int]]

POLICY_BANDS: Final[dict[RiskTolerance, AllocationBands]] = {
    RiskTolerance.CONSERVATIVE: {
        "growth_assets_pct": [20, 45],
        "defensive_assets_pct": [55, 80],
    },
    RiskTolerance.MODERATE: {
        "growth_assets_pct": [45, 70],
        "defensive_assets_pct": [30, 55],
    },
    RiskTolerance.AGGRESSIVE: {
        "growth_assets_pct": [70, 95],
        "defensive_assets_pct": [5, 30],
    },
}

_CENT = Decimal("0.01")
_HUNDRED = Decimal("100")


class TargetAllocation(BaseModel):
    """A percentage split selected inside the configured policy band."""

    model_config = ConfigDict(extra="forbid")

    growth_assets_pct: float = Field(ge=0, le=100)
    defensive_assets_pct: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_total(self) -> TargetAllocation:
        if abs(self.growth_assets_pct + self.defensive_assets_pct - 100.0) > 1e-6:
            raise ValueError("Target allocation percentages must total 100.")
        return self


class CashFlowAllocation(BaseModel):
    """A cent-rounded arithmetic split of one USD cash-flow amount."""

    model_config = ConfigDict(extra="forbid")

    total_usd: float = Field(ge=0)
    growth_assets_usd: float = Field(ge=0)
    defensive_assets_usd: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> CashFlowAllocation:
        if abs(self.growth_assets_usd + self.defensive_assets_usd - self.total_usd) > 0.005:
            raise ValueError("Cash-flow allocation amounts must total the input amount.")
        return self


class PolicyCalculation(BaseModel):
    """JSON-safe policy output that remains explicit about its limitations."""

    model_config = ConfigDict(extra="forbid")

    risk_tolerance: RiskTolerance
    objective: InvestmentObjective
    horizon_years: int = Field(ge=1)
    max_drawdown_pct: float = Field(gt=0, le=100)
    excluded_sectors: list[str]
    allocation_bands: AllocationBands
    target_allocation: TargetAllocation
    initial_investment_usd: CashFlowAllocation
    recurring_monthly_usd: CashFlowAllocation
    notes: list[str]

    @model_validator(mode="after")
    def validate_target_within_bands(self) -> PolicyCalculation:
        growth_band = self.allocation_bands.get("growth_assets_pct")
        defensive_band = self.allocation_bands.get("defensive_assets_pct")
        if growth_band is None or defensive_band is None or len(growth_band) != 2:
            raise ValueError("Policy allocation bands must include two growth bounds.")
        if len(defensive_band) != 2:
            raise ValueError("Policy allocation bands must include two defensive bounds.")
        growth_target = self.target_allocation.growth_assets_pct
        defensive_target = self.target_allocation.defensive_assets_pct
        if not growth_band[0] <= growth_target <= growth_band[1]:
            raise ValueError("Growth target must remain inside the configured policy band.")
        if not defensive_band[0] <= defensive_target <= defensive_band[1]:
            raise ValueError("Defensive target must remain inside the configured policy band.")
        return self


def calculate_policy(profile: InvestorProfile) -> PolicyCalculation:
    """Calculate an illustrative target and cash-flow split without forecasts or side effects."""

    bands = POLICY_BANDS[profile.risk_tolerance]
    growth_min, growth_max = bands["growth_assets_pct"]
    if profile.objective == InvestmentObjective.INCOME:
        growth_target = float(growth_min)
    elif profile.objective == InvestmentObjective.GROWTH:
        growth_target = float(growth_max)
    else:
        growth_target = (growth_min + growth_max) / 2

    target = TargetAllocation(
        growth_assets_pct=growth_target,
        defensive_assets_pct=100 - growth_target,
    )
    return PolicyCalculation(
        risk_tolerance=profile.risk_tolerance,
        objective=profile.objective,
        horizon_years=profile.horizon_years,
        max_drawdown_pct=profile.max_drawdown_pct,
        excluded_sectors=list(profile.excluded_sectors),
        allocation_bands={name: list(bounds) for name, bounds in bands.items()},
        target_allocation=target,
        initial_investment_usd=_split_cash_flow(
            profile.initial_investment_usd,
            target.growth_assets_pct,
        ),
        recurring_monthly_usd=_split_cash_flow(
            profile.recurring_monthly_usd,
            target.growth_assets_pct,
        ),
        notes=[
            "This is an illustrative policy split, not an ETF recommendation or trade instruction.",
            (
                "The target stays inside the configured risk band and does not forecast returns "
                "or drawdowns."
            ),
            (
                "Market data, source retrieval, fees, liquidity, taxes, and ETF selection remain "
                "separate review steps."
            ),
            (
                "Cash-flow amounts are arithmetic illustrations in USD; no order or external "
                "write is performed."
            ),
        ],
    )


def _split_cash_flow(total_usd: float, growth_pct: float) -> CashFlowAllocation:
    total = Decimal(str(total_usd)).quantize(_CENT, rounding=ROUND_HALF_UP)
    growth = (total * Decimal(str(growth_pct)) / _HUNDRED).quantize(
        _CENT,
        rounding=ROUND_HALF_UP,
    )
    defensive = total - growth
    return CashFlowAllocation(
        total_usd=float(total),
        growth_assets_usd=float(growth),
        defensive_assets_usd=float(defensive),
    )
