import pytest
from pydantic import ValidationError

from etf_advisor.domain.profile import MAX_CASH_FLOW_USD, InvestorProfile


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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("initial_investment_usd", float("inf")),
        ("initial_investment_usd", float("nan")),
        ("initial_investment_usd", 1e26),
        ("recurring_monthly_usd", float("inf")),
        ("recurring_monthly_usd", float("nan")),
        ("recurring_monthly_usd", 1e26),
    ],
)
def test_profile_rejects_non_quantizable_cash_amounts(field: str, value: float) -> None:
    payload: dict[str, object] = {
        "horizon_years": 10,
        "risk_tolerance": "moderate",
        "objective": "balanced",
        "max_drawdown_pct": 20,
        "initial_investment_usd": 1_000,
        "recurring_monthly_usd": 100,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        InvestorProfile.model_validate(payload)


def test_profile_accepts_maximum_quantizable_cash_amount() -> None:
    profile = InvestorProfile.model_validate(
        {
            "horizon_years": 10,
            "risk_tolerance": "moderate",
            "objective": "balanced",
            "max_drawdown_pct": 20,
            "initial_investment_usd": MAX_CASH_FLOW_USD,
            "recurring_monthly_usd": MAX_CASH_FLOW_USD,
        }
    )

    assert profile.initial_investment_usd == MAX_CASH_FLOW_USD
    assert profile.recurring_monthly_usd == MAX_CASH_FLOW_USD
