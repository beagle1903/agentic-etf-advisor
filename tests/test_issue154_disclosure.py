"""Context disclosure without changing financial or historical saved contracts."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from langgraph.types import Interrupt
from test_checkpoint_lifecycle import Store
from test_dashboard_revision_controls import Time, _run
from test_explanation import _generated, _request
from test_policy import profile
from test_revision import Adapters

from etf_advisor.cli import _print_state
from etf_advisor.dashboard import load_dashboard_run, review_payload
from etf_advisor.dashboard_app import _render_explanation, _render_policy
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.explanation.provider import LangChainExplanationGenerator
from etf_advisor.presentation import (
    ALLOCATION_CONTEXT_NOTICE,
    DRAWDOWN_CONTEXT_HELP,
    EXPLANATION_CONTEXT_NOTICE,
    HORIZON_CONTEXT_HELP,
)

FIXTURE = Path(__file__).parent / "fixtures" / "issue154-pre-change.json"
APP = Path(__file__).parents[1] / "src" / "etf_advisor" / "dashboard_app.py"


@pytest.mark.parametrize(
    "risk,targets",
    [
        ("conservative", [20, 32.5, 45]),
        ("moderate", [45, 57.5, 70]),
        ("aggressive", [70, 82.5, 95]),
    ],
)
@pytest.mark.parametrize("horizon,drawdown", [(1, 0.1), (60, 100), (1, 5), (60, 90)])
def test_context_boundaries_preserve_targets_and_cash(
    risk: str, targets: list[float], horizon: int, drawdown: float
) -> None:
    for objective, target in zip(["income", "balanced", "growth"], targets, strict=True):
        baseline = calculate_policy(profile(risk_tolerance=risk, objective=objective))
        inputs = profile(risk_tolerance=risk, objective=objective).model_dump(mode="json")
        inputs.update(horizon_years=horizon, max_drawdown_pct=drawdown)
        result = calculate_policy(InvestorProfile.model_validate(inputs))
        assert result.target_allocation.growth_assets_pct == target
        assert result.target_allocation.defensive_assets_pct == 100 - target
        assert result.allocation_bands == baseline.allocation_bands
        assert result.initial_investment_usd == baseline.initial_investment_usd
        assert result.recurring_monthly_usd == baseline.recurring_monthly_usd
        assert result.notes == baseline.notes
        assert result.horizon_years == horizon
        assert result.max_drawdown_pct == drawdown


class Display:
    """Capture display calls while passing the original mutable artifact directly."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def __getattr__(self, name: str) -> Any:
        def capture(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, args))
            if name == "columns":
                return [self] * args[0]
            return self

        return capture

    def __enter__(self) -> "Display":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


@pytest.mark.parametrize("kind", ["policy", "explanation"])
def test_pre_change_saved_review_restores_renders_and_approves_offline(kind: str) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["provenance"]["commit"] == "abfbf0eeeef8404237ce3d6d1e2359639b3aa820"
    saved = fixture[kind]
    store = Store(clock=Time())
    token = saved["config"]["configurable"]["thread_id"]
    with store.open() as saver:
        config = saver.put(
            saved["config"],
            saved["checkpoint"],
            saved["metadata"],
            saved["checkpoint"]["channel_versions"],
        )
        for task, channel, values in saved["pending_writes"]:
            saver.put_writes(config, [(channel, [Interrupt(**item) for item in values])], task)
        store.write_metadata(saver, token, saved["lifecycle"])
    # No adapters attached: restoration, local validation and approval must be offline.
    run = load_dashboard_run(token, checkpoint_store=store)
    payload = review_payload(run.state)
    assert payload is not None
    before = deepcopy(run.state)
    serialized = json.dumps(payload, sort_keys=True)
    display = Display()
    _render_policy(display, payload["draft_policy"])
    assert ("info", (ALLOCATION_CONTEXT_NOTICE,)) in display.calls
    assert ("text", (ALLOCATION_CONTEXT_NOTICE,)) in display.calls
    if kind == "explanation":
        explanation = payload["draft_explanation"]
        assert "review constraint" in json.dumps(explanation)
        _render_explanation(display, explanation)
        notice = display.calls.index(("info", (EXPLANATION_CONTEXT_NOTICE,)))
        summary = display.calls.index(("text", (explanation["explanation"]["summary"]["text"],)))
        assert notice < summary
    assert json.dumps(payload, sort_keys=True) == serialized
    assert run.state == before
    completed = run.resume("approve")
    assert completed["status"] == "approved"
    assert completed["draft_policy"] == saved["checkpoint"]["channel_values"]["draft_policy"]
    assert completed.get("draft_explanation") == saved["checkpoint"]["channel_values"].get(
        "draft_explanation"
    )


def test_current_provider_messages_clarify_context_without_changing_saved_payload() -> None:
    captured: list[Any] = []

    class Model:
        def invoke(self, messages: Any) -> Any:
            captured.append(messages)
            return _generated()

    generator = LangChainExplanationGenerator(
        Model(), provider="test", model_name="fixed", structured_method="function_calling"
    )
    generator.generate(_request())
    system = captured[0][0][1]
    assert "risk tolerance and objective only" in system
    assert "context for human review only" in system
    assert "Never describe them as changing the target, an enforced drawdown limit" in system
    assert "fits the stated horizon or is suitable" in system
    payload = json.loads(captured[0][1][1].split("INPUT_JSON:\n", 1)[1])
    assert payload == json.loads(FIXTURE.read_text(encoding="utf-8"))["provider_input"]


def test_cli_notice_is_outside_unchanged_json_and_omits_ledger(capsys: Any) -> None:
    state = {
        "draft_policy": {"saved": "unchanged"},
        "draft_explanation": {"saved": "text"},
        "revision_ledger": {"thread_id": "private-token"},
    }
    before = deepcopy(state)
    _print_state("Review", state)
    output = capsys.readouterr().out
    prefix, payload = output.split("{", 1)
    assert ALLOCATION_CONTEXT_NOTICE in prefix
    assert EXPLANATION_CONTEXT_NOTICE in prefix
    assert json.loads("{" + payload) == {k: v for k, v in state.items() if k != "revision_ledger"}
    assert "private-token" not in output
    assert state == before


def test_rendered_forms_disclose_context_and_keep_widget_keys_and_ranges() -> None:
    app_test = pytest.importorskip("streamlit.testing.v1")
    app = app_test.AppTest.from_file(str(APP))
    run = _run()
    app.session_state["dashboard_run"] = run
    app.run(timeout=20)
    assert not app.exception
    assert HORIZON_CONTEXT_HELP in [c.value for c in app.caption]
    assert DRAWDOWN_CONTEXT_HELP in [c.value for c in app.caption]
    initial_h = next(n for n in app.number_input if n.label == "Horizon (years)")
    initial_d = next(n for n in app.number_input if n.label == "Maximum tolerable drawdown (%)")
    initial_ids = (initial_h.id, initial_d.id)
    assert (initial_h.min, initial_h.max) == (1, 60)
    assert (initial_d.min, initial_d.max) == (0.1, 100)
    assert ALLOCATION_CONTEXT_NOTICE in [i.value for i in app.info]
    assert ALLOCATION_CONTEXT_NOTICE in [t.value for t in app.text]
    assert "Horizon input (context only)" in [m.label for m in app.metric]
    assert "Tolerable drawdown input (context only)" in [m.label for m in app.metric]
    next(r for r in app.radio if r.label == "Decision").set_value("Edit")
    app.run(timeout=20)
    next(m for m in app.multiselect if m.label == "Typed feedback").set_value(["profile"])
    app.run(timeout=20)
    revised_h = next(
        n for n in app.number_input if n.label == "Revised horizon (years; context only)"
    )
    revised_d = next(n for n in app.number_input if n.label.startswith("Revised maximum tolerable"))
    assert revised_h.key.endswith("-h")
    assert revised_d.key.endswith("-drawdown")
    assert revised_h.proto.help == HORIZON_CONTEXT_HELP
    assert revised_d.proto.help == DRAWDOWN_CONTEXT_HELP
    assert (revised_h.min, revised_h.max) == (1, 60)
    assert (revised_d.min, revised_d.max) == (0.1, 100)
    assert initial_ids == tuple(
        next(n for n in app.number_input if n.label == label).id
        for label in ["Horizon (years)", "Maximum tolerable drawdown (%)"]
    )


@pytest.mark.parametrize("patch", [{"horizon_years": 1}, {"max_drawdown_pct": 5}])
def test_context_only_profile_revisions_keep_existing_invalidation_and_calls(
    patch: dict[str, Any],
) -> None:
    adapters = Adapters()
    run = _run(adapters=adapters)
    parent = deepcopy(run.state["draft_policy"])
    assert (adapters.retrieval_calls, adapters.provider_calls) == (1, 1)
    child = run.resume(
        "edit",
        "Review revised context.",
        disposition="revise",
        feedback_items=[{"kind": "profile", "patch": patch}],
    )
    assert child["status"] == "awaiting_human_review"
    assert child["draft_policy"]["target_allocation"] == parent["target_allocation"]
    assert child["draft_policy"]["initial_investment_usd"] == parent["initial_investment_usd"]
    assert (adapters.retrieval_calls, adapters.provider_calls) == (2, 2)
    assert len(child["revision_ledger"]["revisions"]) == 2
    assert all(child["profile"][key] == value for key, value in patch.items())
