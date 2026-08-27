import json

import pytest

from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile


def profile(
    *,
    risk_tolerance: str,
    objective: str,
    initial: float = 10_000,
    recurring: float = 333.33,
) -> InvestorProfile:
    return InvestorProfile(
        horizon_years=15,
        risk_tolerance=risk_tolerance,
        objective=objective,
        max_drawdown_pct=30,
        initial_investment_usd=initial,
        recurring_monthly_usd=recurring,
        excluded_sectors=["tobacco"],
    )


@pytest.mark.parametrize(
    ("risk_tolerance", "objective", "expected_growth_pct"),
    [
        ("conservative", "income", 20.0),
        ("conservative", "balanced", 32.5),
        ("conservative", "growth", 45.0),
        ("moderate", "income", 45.0),
        ("moderate", "balanced", 57.5),
        ("moderate", "growth", 70.0),
        ("aggressive", "income", 70.0),
        ("aggressive", "balanced", 82.5),
        ("aggressive", "growth", 95.0),
    ],
)
def test_objective_selects_target_inside_risk_band(
    risk_tolerance: str,
    objective: str,
    expected_growth_pct: float,
) -> None:
    calculation = calculate_policy(
        profile(risk_tolerance=risk_tolerance, objective=objective),
    )

    target = calculation.target_allocation
    growth_band = calculation.allocation_bands["growth_assets_pct"]
    defensive_band = calculation.allocation_bands["defensive_assets_pct"]
    assert target.growth_assets_pct == expected_growth_pct
    assert target.defensive_assets_pct == 100 - expected_growth_pct
    assert growth_band[0] <= target.growth_assets_pct <= growth_band[1]
    assert defensive_band[0] <= target.defensive_assets_pct <= defensive_band[1]


def test_cash_flow_rounding_preserves_each_total() -> None:
    calculation = calculate_policy(profile(risk_tolerance="moderate", objective="balanced"))

    assert calculation.initial_investment_usd.model_dump() == {
        "total_usd": 10_000.0,
        "growth_assets_usd": 5_750.0,
        "defensive_assets_usd": 4_250.0,
    }
    assert calculation.recurring_monthly_usd.model_dump() == {
        "total_usd": 333.33,
        "growth_assets_usd": 191.66,
        "defensive_assets_usd": 141.67,
    }


def test_zero_cash_flows_are_explicit_and_json_serializable() -> None:
    calculation = calculate_policy(
        profile(
            risk_tolerance="conservative",
            objective="income",
            initial=0,
            recurring=0,
        ),
    )

    payload = calculation.model_dump(mode="json")
    assert payload["initial_investment_usd"] == {
        "total_usd": 0.0,
        "growth_assets_usd": 0.0,
        "defensive_assets_usd": 0.0,
    }
    assert json.loads(json.dumps(payload)) == payload


def test_profile_constraints_and_safety_notes_are_retained() -> None:
    calculation = calculate_policy(profile(risk_tolerance="moderate", objective="growth"))

    assert calculation.horizon_years == 15
    assert calculation.max_drawdown_pct == 30
    assert calculation.excluded_sectors == ["tobacco"]
    assert any("does not forecast returns" in note for note in calculation.notes)
    assert any("no order" in note for note in calculation.notes)
