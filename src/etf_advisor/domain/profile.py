"""Investor-profile inputs used by the advisory workflow."""

from enum import StrEnum
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from etf_advisor.catalogue.research_scope import CatalogueRequestV1

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
    advisory_contract: Literal["us-eu-v1"] | None = None
    base_currency: Literal["USD", "EUR"] | None = None
    initial_investment_usd: float | None = Field(default=None, ge=0, le=MAX_CASH_FLOW_USD)
    recurring_monthly_usd: float | None = Field(default=0, ge=0, le=MAX_CASH_FLOW_USD)
    initial_investment_minor: int | None = Field(
        default=None, ge=0, le=100_000_000_000_000, strict=True
    )
    recurring_monthly_minor: int | None = Field(
        default=None, ge=0, le=100_000_000_000_000, strict=True
    )
    excluded_sectors: list[str] = Field(default_factory=list, max_length=25)
    catalogue_request: CatalogueRequestV1 | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_mixed_money(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        marker = value.get("advisory_contract")
        if "catalogue_request" in value and (
            value["catalogue_request"] is None or marker != "us-eu-v1"
        ):
            raise ValueError("Catalogue request requires an explicit US/EU profile.")
        if marker == "us-eu-v1":
            if "initial_investment_usd" in value or "recurring_monthly_usd" in value:
                raise ValueError("New contract rejects legacy USD cash keys.")
        elif any(
            key in value
            for key in (
                "base_currency",
                "initial_investment_minor",
                "recurring_monthly_minor",
                "advisory_contract",
            )
        ):
            raise ValueError("Legacy profile rejects new-contract fields or marker.")
        return value

    @model_validator(mode="after")
    def validate_money(self) -> "InvestorProfile":
        if self.advisory_contract == "us-eu-v1":
            if (
                self.base_currency is None
                or self.initial_investment_minor is None
                or self.recurring_monthly_minor is None
                or self.initial_investment_usd is not None
                or self.recurring_monthly_usd != 0
            ):
                raise ValueError("New contract requires currency and both minor-unit amounts.")
        elif self.initial_investment_usd is None:
            raise ValueError("Legacy profile requires initial USD cash.")
        if self.advisory_contract is None and self.catalogue_request is not None:
            raise ValueError("Legacy profile rejects catalogue selection.")
        return self

    @model_serializer(mode="wrap")
    def serialize_profile(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.advisory_contract == "us-eu-v1":
            result.pop("initial_investment_usd", None)
            result.pop("recurring_monthly_usd", None)
            if self.catalogue_request is None:
                result.pop("catalogue_request", None)
        else:
            for name in (
                "advisory_contract",
                "base_currency",
                "initial_investment_minor",
                "recurring_monthly_minor",
                "catalogue_request",
            ):
                result.pop(name, None)
        return result
