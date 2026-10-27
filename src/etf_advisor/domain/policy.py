"""Deterministic, illustrative policy calculations for the review workflow."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from etf_advisor.domain.profile import InvestmentObjective, InvestorProfile, RiskTolerance
from etf_advisor.domain.us_eu import contract_fields
from etf_advisor.encoding import AdvisoryWireModel

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


class MinorCashAllocation(BaseModel):
    """Exact base-currency cash in integer minor units."""

    model_config = ConfigDict(extra="forbid")
    currency: Literal["USD", "EUR"]
    total_minor: int = Field(ge=0, strict=True)
    growth_minor: int = Field(ge=0, strict=True)
    defensive_minor: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def reconcile(self) -> MinorCashAllocation:
        if self.growth_minor + self.defensive_minor != self.total_minor:
            raise ValueError("Minor-unit cash sleeves must reconcile exactly.")
        return self


class PolicyCalculation(AdvisoryWireModel):
    """JSON-safe policy output that remains explicit about its limitations."""

    legacy_extension_fields = frozenset(
        {"base_currency", "initial_investment", "recurring_monthly"}
    )
    new_forbidden_fields = frozenset({"initial_investment_usd", "recurring_monthly_usd"})

    model_config = ConfigDict(extra="forbid")

    risk_tolerance: RiskTolerance
    objective: InvestmentObjective
    horizon_years: int = Field(ge=1)
    max_drawdown_pct: float = Field(gt=0, le=100)
    excluded_sectors: list[str]
    allocation_bands: AllocationBands
    target_allocation: TargetAllocation
    advisory_contract: Literal["us-eu-v1"] | None = None
    identity_contract: Literal["curator-fund-v1"] | None = None
    base_currency: Literal["USD", "EUR"] | None = None
    initial_investment_usd: CashFlowAllocation | None = None
    recurring_monthly_usd: CashFlowAllocation | None = None
    initial_investment: MinorCashAllocation | None = None
    recurring_monthly: MinorCashAllocation | None = None
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
        if self.advisory_contract == "us-eu-v1":
            if (
                self.base_currency is None
                or self.initial_investment is None
                or self.recurring_monthly is None
                or self.initial_investment_usd is not None
                or self.recurring_monthly_usd is not None
            ):
                raise ValueError("New policy requires exact new-contract cash only.")
            if (
                self.initial_investment.currency != self.base_currency
                or self.recurring_monthly.currency != self.base_currency
            ):
                raise ValueError("Policy cash currency differs from base currency.")
        elif (
            self.base_currency is not None
            or self.initial_investment is not None
            or self.recurring_monthly is not None
            or self.initial_investment_usd is None
            or self.recurring_monthly_usd is None
        ):
            raise ValueError("Legacy policy rejects new-contract cash.")
        return self

    @model_serializer(mode="wrap")
    def serialize_policy(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.identity_contract is None:
            result.pop("identity_contract", None)
        if self.advisory_contract == "us-eu-v1":
            result.pop("initial_investment_usd", None)
            result.pop("recurring_monthly_usd", None)
        else:
            for name in (
                "advisory_contract",
                "base_currency",
                "initial_investment",
                "recurring_monthly",
            ):
                result.pop(name, None)
        return result


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
    new_contract = profile.advisory_contract == "us-eu-v1"
    return PolicyCalculation(
        risk_tolerance=profile.risk_tolerance,
        objective=profile.objective,
        horizon_years=profile.horizon_years,
        max_drawdown_pct=profile.max_drawdown_pct,
        excluded_sectors=list(profile.excluded_sectors),
        allocation_bands={name: list(bounds) for name, bounds in bands.items()},
        target_allocation=target,
        **contract_fields(profile.advisory_contract),
        **({"identity_contract": profile.identity_contract} if profile.identity_contract else {}),
        **(
            {
                "base_currency": profile.base_currency,
                "initial_investment": _split_minor_cash(
                    profile.initial_investment_minor,
                    profile.base_currency,
                    target.growth_assets_pct,
                ),
                "recurring_monthly": _split_minor_cash(
                    profile.recurring_monthly_minor, profile.base_currency, target.growth_assets_pct
                ),
            }
            if new_contract
            else {
                "initial_investment_usd": _split_cash_flow(
                    profile.initial_investment_usd, target.growth_assets_pct
                ),
                "recurring_monthly_usd": _split_cash_flow(
                    profile.recurring_monthly_usd, target.growth_assets_pct
                ),
            }
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
                "Cash-flow amounts are arithmetic illustrations in "
                f"{profile.base_currency if new_contract else 'USD'}; no order or external "
                "write is performed."
            ),
        ],
    )


def _split_cash_flow(total_usd: float | None, growth_pct: float) -> CashFlowAllocation:
    assert total_usd is not None
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


def _split_minor_cash(
    total: int | None, currency: Literal["USD", "EUR"] | None, growth_pct: float
) -> MinorCashAllocation:
    assert total is not None and currency is not None
    growth = int(
        (Decimal(total) * Decimal(str(growth_pct)) / Decimal(100)).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )
    return MinorCashAllocation(
        currency=currency, total_minor=total, growth_minor=growth, defensive_minor=total - growth
    )
