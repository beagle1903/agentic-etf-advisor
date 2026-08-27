import pytest
from pydantic import ValidationError

from etf_advisor.domain.profile import InvestorProfile


def test_profile_rejects_zero_horizon() -> None:
    with pytest.raises(ValidationError):
        InvestorProfile.model_validate(
            {
                "horizon_years": 0,
                "risk_tolerance": "moderate",
                "objective": "balanced",
                "max_drawdown_pct": 20,
                "initial_investment_usd": 1_000,
            }
        )


def test_profile_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        InvestorProfile.model_validate(
            {
                "horizon_years": 10,
                "risk_tolerance": "moderate",
                "objective": "balanced",
                "max_drawdown_pct": 20,
                "initial_investment_usd": 1_000,
                "secret_override": True,
            }
        )
