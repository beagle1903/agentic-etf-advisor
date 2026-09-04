import json
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

import etf_advisor.dashboard as dashboard
from etf_advisor.dashboard import (
    DashboardOptions,
    DashboardRun,
    load_dashboard_run,
    parse_excluded_sectors,
    review_payload,
)
from etf_advisor.dashboard_app import (
    _CREATION_ERROR_KEY,
    _CREATION_IN_PROGRESS_KEY,
    _render_creation_button,
    _render_portfolio,
    _render_run,
    _render_screening,
)
from etf_advisor.domain.construction import (
    PortfolioConstructionBundle,
    PortfolioConstructionInput,
    construct_model_portfolio,
)
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.explanation import (
    ExplanationResult,
    build_explanation_request,
    validate_and_bundle_explanation,
)
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.models import ResearchField


class FakeGraph:
    def __init__(self) -> None:
        self.inputs: list[object] = []

    def invoke(self, value: object, config: dict[str, Any]) -> dict[str, Any]:
        self.inputs.append(value)
        return {"status": "approved", "final_message": "Approved safely."}


class DurableMemoryCheckpointStore:
    durable = True

    def __init__(self) -> None:
        self.saver = InMemorySaver()
        self.setup_calls = 0
        self.open_calls = 0

    def setup(self) -> None:
        self.setup_calls += 1

    @contextmanager
    def open(self) -> Iterator[InMemorySaver]:
        self.open_calls += 1
        yield self.saver


def valid_profile() -> InvestorProfile:
    return InvestorProfile(
        horizon_years=12,
        risk_tolerance="moderate",
        objective="balanced",
        max_drawdown_pct=25,
        initial_investment_usd=25_000,
        recurring_monthly_usd=500,
        excluded_sectors=[],
    )


def paused_state() -> dict[str, Any]:
    profile = valid_profile()
    payload = {
        "kind": "portfolio_policy_review",
        "question": "Approve?",
        "allowed_actions": ["approve", "edit", "reject"],
        "draft_policy": calculate_policy(profile).model_dump(mode="json"),
    }
    return {
        "status": "awaiting_human_review",
        "__interrupt__": (SimpleNamespace(value=payload),),
    }


def paused_state_with_evidence_and_explanation() -> dict[str, Any]:
    state = paused_state()
    payload = state["__interrupt__"][0].value
    observed_at = datetime(2026, 8, 28, 11, tzinfo=UTC)
    evidence = select_candidate_evidence(
        valid_profile(),
        [
            GraphEnrichedSource(
                document_id="doc-spy",
                content="SPY is broad US equity research context.",
                metadata={
                    "symbol": "SPY",
                    "name": "SPDR S&P 500 ETF Trust",
                    "source": "yahoo_finance",
                    "source_url": "https://finance.yahoo.com/quote/SPY/",
                    "observed_at": observed_at.isoformat(),
                    "quote_type": "ETF",
                    "market": "us_market",
                },
            )
        ],
        query="broad US equity evidence",
        checked_at=datetime(2026, 8, 28, 12, tzinfo=UTC),
        max_age=timedelta(hours=24),
    )
    payload["candidate_evidence"] = evidence.model_dump(mode="json")
    payload["candidate_screening"] = screen_candidate_evidence(evidence).model_dump(mode="json")
    payload["draft_explanation"] = {
        "status": "ready",
        "provider": "test",
        "model": "fixed",
        "explanation": {
            "summary": {
                "text": "The draft illustrates a balanced objective.",
                "basis": "policy_calculation",
                "references": ["profile.objective"],
                "subject_symbols": [],
            },
            "policy_points": [
                {
                    "text": "The target remains inside the moderate policy band.",
                    "basis": "policy_calculation",
                    "references": ["policy.target_allocation"],
                    "subject_symbols": [],
                }
            ],
            "evidence_points": [
                {
                    "text": "SPY appears as broad US equity research context.",
                    "basis": "source_evidence",
                    "references": ["doc-spy"],
                    "subject_symbols": ["SPY"],
                }
            ],
            "tradeoffs": [
                {
                    "text": "The drawdown input remains a review constraint.",
                    "basis": "policy_calculation",
                    "references": ["profile.max_drawdown_pct"],
                    "subject_symbols": [],
                }
            ],
        },
        "citations": [
            {
                "document_id": "doc-spy",
                "symbol": "SPY",
                "source": "yahoo_finance",
                "source_url": "https://finance.yahoo.com/quote/SPY/",
                "observed_at": observed_at.isoformat(),
            }
        ],
        "limitations": ["Educational explanation only."],
    }
    return state


def paused_state_with_portfolio_and_explanation() -> dict[str, Any]:
    profile = valid_profile()
    observed_at = datetime(2026, 8, 28, 11, tzinfo=UTC)
    checked_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    evidence = select_candidate_evidence(
        profile,
        [
            _construction_source(symbol, category, observed_at, checked_at)
            for symbol, category in (
                ("SPY", "Large Blend"),
                ("VTI", "Large Blend"),
                ("QQQ", "Large Growth"),
                ("VEA", "Foreign Large Blend"),
                ("BND", "Intermediate Core Bond"),
            )
        ],
        query="balanced ETF research evidence",
        checked_at=checked_at,
        max_age=timedelta(hours=24),
        limit=5,
    )
    screening = screen_candidate_evidence(evidence)
    policy = calculate_policy(profile)
    construction = construct_model_portfolio(
        PortfolioConstructionInput(
            profile=profile,
            policy_calculation=policy,
            candidate_evidence=evidence,
            candidate_screening=screening,
        )
    )
    explanation_request = build_explanation_request(
        profile=profile.model_dump(mode="json"),
        draft_policy=policy.model_dump(mode="json"),
        candidate_evidence=evidence.model_dump(mode="json"),
    )
    explanation_payload = paused_state_with_evidence_and_explanation()["__interrupt__"][0].value[
        "draft_explanation"
    ]
    explanation = validate_and_bundle_explanation(
        explanation_request,
        ExplanationResult(
            provider=explanation_payload["provider"],
            model=explanation_payload["model"],
            explanation=explanation_payload["explanation"],
        ),
    )
    payload = {
        "kind": "portfolio_policy_review",
        "question": "Approve this illustrative portfolio?",
        "allowed_actions": ["approve", "edit", "reject"],
        "draft_policy": policy.model_dump(mode="json"),
        "candidate_evidence": evidence.model_dump(mode="json"),
        "candidate_screening": screening.model_dump(mode="json"),
        "portfolio_construction": construction.model_dump(mode="json"),
        "draft_explanation": explanation.model_dump(mode="json"),
    }
    return {
        "profile": profile.model_dump(mode="json"),
        "draft_policy": policy.model_dump(mode="json"),
        "candidate_evidence": evidence.model_dump(mode="json"),
        "candidate_screening": screening.model_dump(mode="json"),
        "portfolio_construction": construction.model_dump(mode="json"),
        "draft_explanation": explanation.model_dump(mode="json"),
        "status": "awaiting_human_review",
        "__interrupt__": (SimpleNamespace(value=payload),),
    }


def _construction_source(
    symbol: str,
    category: str,
    observed_at: datetime,
    checked_at: datetime,
) -> GraphEnrichedSource:
    source_url = f"https://finance.yahoo.com/quote/{symbol}/"
    values: dict[str, Any] = {
        "market": "us_market",
        "quote_type": "ETF",
        "category": category,
        "expense_ratio_pct": 0.1,
        "average_daily_volume": 1_000_000,
        "top_10_concentration_pct": 40.0,
    }
    units = {
        "market": "classification",
        "quote_type": "classification",
        "category": "classification",
        "expense_ratio_pct": "percent",
        "average_daily_volume": "shares_per_day",
        "top_10_concentration_pct": "percent",
    }
    metadata: dict[str, str | int | float | bool] = {
        "symbol": symbol,
        "name": f"{symbol} ETF",
        "source": "yahoo_finance",
        "source_url": source_url,
        "observed_at": observed_at.isoformat(),
    }
    provenance: dict[str, dict[str, Any]] = {}
    for field_name, value in values.items():
        field = ResearchField[Any](
            value=value,
            unit=units[field_name],
            provider="yahoo_finance",
            source_url=source_url,
            observed_at=observed_at,
            ingested_at=checked_at,
            snapshot_version="dashboard-construction-v1",
        )
        provenance[field_name] = field.model_dump(mode="json")
        metadata[field_name] = value
        metadata[f"{field_name}_status"] = "available"
    metadata["field_provenance_json"] = json.dumps(
        provenance,
        sort_keys=True,
        separators=(",", ":"),
    )
    return GraphEnrichedSource(
        document_id=f"doc-{symbol.lower()}",
        content=f"{symbol} source facts",
        metadata=metadata,
    )


def test_dashboard_options_require_evidence_for_explanation() -> None:
    with pytest.raises(ValueError, match="require source evidence"):
        DashboardOptions(with_explanation=True)


def test_dashboard_evidence_toggle_unlocks_explanation_in_original_order() -> None:
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")
    app_path = Path(__file__).resolve().parents[1] / "src" / "etf_advisor" / "dashboard_app.py"
    app = streamlit_testing.AppTest.from_file(str(app_path)).run()

    evidence, explanation = app.sidebar.checkbox[:2]
    sidebar_labels = [getattr(element, "label", None) for element in app.sidebar]
    assert (
        sidebar_labels.index("Excluded sectors")
        < sidebar_labels.index("Attach local source evidence")
        < sidebar_labels.index("Generate grounded explanation")
    )
    assert evidence.proto.form_id == ""
    assert explanation.proto.form_id == ""
    assert explanation.disabled is True

    app.sidebar.checkbox[0].set_value(True).run()

    assert app.sidebar.checkbox[1].disabled is False


def test_create_review_button_locks_before_creation() -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {_CREATION_ERROR_KEY: "previous failure"}
            self.buttons: list[tuple[str, dict[str, Any]]] = []
            self.captions: list[str] = []

        def button(self, label: str, **kwargs: Any) -> None:
            self.buttons.append((label, kwargs))

        def caption(self, message: str) -> None:
            self.captions.append(message)

    st = FakeStreamlit()
    _render_creation_button(st)
    label, options = st.buttons[-1]

    assert label == "Create review draft"
    assert options["disabled"] is False
    options["on_click"](*options["args"])
    assert st.session_state[_CREATION_IN_PROGRESS_KEY] is True
    assert _CREATION_ERROR_KEY not in st.session_state

    _render_creation_button(st)

    assert st.buttons[-1][1]["disabled"] is True
    assert st.captions == ["Creating review draft…"]


def test_create_review_double_click_runs_once(monkeypatch: pytest.MonkeyPatch) -> None:
    streamlit_testing = pytest.importorskip("streamlit.testing.v1")
    calls: list[tuple[dict[str, object], DashboardOptions]] = []

    def fake_start_dashboard_run(
        profile: dict[str, object], options: DashboardOptions
    ) -> DashboardRun:
        calls.append((profile, options))
        return DashboardRun(
            graph=None,
            config={"configurable": {"thread_id": "test-thread"}},
            state={"status": "approved", "final_message": "Created once."},
        )

    monkeypatch.setattr(dashboard, "start_dashboard_run", fake_start_dashboard_run)
    app_path = Path(__file__).resolve().parents[1] / "src" / "etf_advisor" / "dashboard_app.py"
    app = streamlit_testing.AppTest.from_file(str(app_path)).run()
    create_button = next(
        button for button in app.sidebar.button if button.label == "Create review draft"
    )

    create_button.click()
    create_button.click()
    app.run()

    assert len(calls) == 1
    assert (
        next(
            button for button in app.sidebar.button if button.label == "Create review draft"
        ).disabled
        is False
    )
    assert [message.value for message in app.success] == ["Created once."]


def test_review_payload_rejects_missing_or_unsupported_interrupts() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        review_payload({"status": "awaiting_human_review"})

    state = paused_state()
    state["__interrupt__"] = (SimpleNamespace(value={"kind": "other"}),)
    with pytest.raises(ValueError, match="unsupported"):
        review_payload(state)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("question", None),
        ("question", "  "),
        ("allowed_actions", ["approve", "approve", "reject"]),
        ("draft_policy", {"target_allocation": {}}),
        ("candidate_evidence", {"status": "ready"}),
        ("candidate_screening", {"status": "ready"}),
        ("portfolio_construction", {"status": "ready"}),
        ("draft_explanation", {"status": "ready"}),
    ],
)
def test_review_payload_rejects_malformed_required_and_nested_fields(
    field: str,
    value: object,
) -> None:
    state = deepcopy(paused_state())
    payload = state["__interrupt__"][0].value
    if value is None:
        payload.pop(field)
    else:
        payload[field] = value

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_renderer_reports_malformed_review_payload_without_crashing() -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.errors: list[str] = []

        def error(self, message: str) -> None:
            self.errors.append(message)

    state = paused_state()
    state["__interrupt__"][0].value.pop("draft_policy")
    st = FakeStreamlit()

    _render_run(st, DashboardRun(graph=FakeGraph(), config={}, state=state))

    assert st.errors == ["The workflow returned an invalid review contract."]


def test_renderer_labels_redacted_provider_diagnostics() -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.errors: list[str] = []
            self.captions: list[str] = []
            self.payloads: list[object] = []

        def error(self, message: str) -> None:
            self.errors.append(message)

        def caption(self, message: str) -> None:
            self.captions.append(message)

        def json(self, payload: object) -> None:
            self.payloads.append(payload)

    diagnostic = {
        "type": "generation_error",
        "message": "The selected provider does not support the required method.",
        "code": "unsupported_capability",
        "provider": "ollama",
        "model": "test-cloud-model",
        "method": "function_calling",
    }
    state = {"status": "explanation_blocked", "explanation_errors": [diagnostic]}
    st = FakeStreamlit()

    _render_run(st, DashboardRun(graph=FakeGraph(), config={}, state=state))

    assert st.errors == ["The workflow stopped before human review."]
    assert st.payloads == [[diagnostic]]
    assert len(st.captions) == 1
    assert "credentials" in st.captions[0]
    assert "raw model responses" in st.captions[0]


def test_renderer_labels_redacted_explanation_contract_diagnostics() -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.errors: list[str] = []
            self.captions: list[str] = []
            self.payloads: list[object] = []

        def error(self, message: str) -> None:
            self.errors.append(message)

        def caption(self, message: str) -> None:
            self.captions.append(message)

        def json(self, payload: object) -> None:
            self.payloads.append(payload)

    diagnostic = {
        "type": "explanation_contract",
        "message": "Generated explanation failed safety or grounding validation.",
        "code": "unsupported_numeric_claim",
    }
    state = {"status": "explanation_blocked", "explanation_errors": [diagnostic]}
    st = FakeStreamlit()

    _render_run(st, DashboardRun(graph=FakeGraph(), config={}, state=state))

    assert st.errors == ["The workflow stopped before human review."]
    assert st.payloads == [[diagnostic]]
    assert len(st.captions) == 1
    assert "failed local validation rule" in st.captions[0]
    assert "generated text" in st.captions[0]


def test_screening_renderer_shows_comparison_reasons_and_source_links() -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.rows: list[dict[str, str]] = []
            self.links: list[str] = []

        def subheader(self, message: str) -> None:
            pass

        def caption(self, message: str) -> None:
            pass

        def dataframe(self, rows: list[dict[str, str]], **kwargs: object) -> None:
            self.rows = rows

        def expander(self, label: str) -> Any:
            return nullcontext()

        def write(self, message: str) -> None:
            pass

        def link_button(self, label: str, url: str) -> None:
            self.links.append(url)

    payload = paused_state_with_evidence_and_explanation()["__interrupt__"][0].value
    st = FakeStreamlit()

    _render_screening(st, payload["candidate_screening"])

    assert st.rows == [
        {
            "Symbol": "SPY",
            "Result": "unknown",
            "Failed rules": "—",
            "Unknown rules": ("expense_ratio_unknown, volume_unknown, concentration_unknown"),
        }
    ]
    assert st.links
    assert set(st.links) == {"https://finance.yahoo.com/quote/SPY/"}


def test_review_payload_requires_evidence_to_match_policy_constraints() -> None:
    state = paused_state_with_portfolio_and_explanation()
    state["__interrupt__"][0].value["candidate_evidence"]["objective"] = "growth"

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_review_payload_recomputes_screening_from_evidence() -> None:
    state = paused_state_with_portfolio_and_explanation()
    screening = state["__interrupt__"][0].value["candidate_screening"]
    screening["candidates"][0]["rules"][3]["message"] = "Tampered persisted screening result."

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_review_payload_requires_explanation_to_have_evidence() -> None:
    state = paused_state_with_portfolio_and_explanation()
    state["__interrupt__"][0].value.pop("candidate_evidence")

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_review_payload_rejects_explanation_citation_not_matching_evidence() -> None:
    state = paused_state_with_portfolio_and_explanation()
    citation = state["__interrupt__"][0].value["draft_explanation"]["citations"][0]
    citation["source_url"] = "https://example.com/different-source"

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


@pytest.mark.parametrize(
    "text",
    [
        "SPY guarantees positive returns.",
        "SPY has a 14.38% portfolio weight.",
    ],
)
def test_review_payload_replays_explanation_safety_after_checkpoint_restore(text: str) -> None:
    state = paused_state_with_portfolio_and_explanation()
    for explanation in (
        state["draft_explanation"],
        state["__interrupt__"][0].value["draft_explanation"],
    ):
        explanation["explanation"]["evidence_points"][0]["text"] = text

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


@pytest.mark.parametrize("missing_from", ["checkpoint", "interrupt"])
def test_review_payload_rejects_asymmetric_explanation_presence(missing_from: str) -> None:
    state = paused_state_with_portfolio_and_explanation()
    if missing_from == "checkpoint":
        state["draft_explanation"] = {}
    else:
        state["__interrupt__"][0].value.pop("draft_explanation")

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_review_payload_recomputes_persisted_portfolio_before_rendering() -> None:
    state = paused_state_with_portfolio_and_explanation()

    payload = review_payload(state)

    assert payload["portfolio_construction"]["status"] == "ready"
    assert payload["portfolio_construction"]["draft"]["total_weight_bps"] == 10_000


def test_review_payload_blocks_tampered_persisted_portfolio() -> None:
    state = paused_state_with_portfolio_and_explanation()
    construction = state["__interrupt__"][0].value["portfolio_construction"]
    construction["draft"]["positions"][0]["weight_bps"] += 1
    state["portfolio_construction"] = deepcopy(construction)

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("draft", "positions", 0, "source_category"), "Large Growth"),
        (("draft", "positions", 0, "source_url"), "https://example.com/tampered"),
        (("draft", "positions", 0, "reason_code"), "supports_defensive_target"),
        (("draft", "total_weight_bps"), 9_999),
        (("draft", "sleeve_weight_bps", "growth"), 5_749),
        (("policy", "max_category_weight_bps"), 4_249),
        (("validation", "checks", 0, "message"), "Tampered validation result."),
    ],
)
def test_review_payload_rejects_internally_consistent_but_forged_portfolio_fields(
    path: tuple[str | int, ...],
    value: object,
) -> None:
    state = paused_state_with_portfolio_and_explanation()
    interrupted = state["__interrupt__"][0].value["portfolio_construction"]
    checkpointed = state["portfolio_construction"]
    for payload in (interrupted, checkpointed):
        target: Any = payload
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


@pytest.mark.parametrize(
    "field",
    [
        "draft_policy",
        "candidate_evidence",
        "candidate_screening",
        "portfolio_construction",
        "draft_explanation",
    ],
)
def test_review_payload_blocks_checkpointed_upstream_mismatch(field: str) -> None:
    state = paused_state_with_portfolio_and_explanation()
    if field == "draft_policy":
        state[field]["notes"][0] = "Tampered checkpointed policy note."
    elif field == "candidate_evidence":
        state[field]["query"] = "tampered checkpointed evidence query"
    elif field == "candidate_screening":
        state[field]["policy"]["max_expense_ratio_pct"] = 0.9
    elif field == "draft_explanation":
        state[field]["model"] = "tampered-checkpoint-model"
    else:
        state[field]["draft"]["positions"][0]["name"] = "Tampered checkpointed position"

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_review_payload_requires_portfolio_with_source_evidence() -> None:
    state = paused_state_with_portfolio_and_explanation()
    state["__interrupt__"][0].value.pop("portfolio_construction")

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_portfolio_renderer_shows_allocations_constraints_validation_and_sources() -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.metrics: list[tuple[str, str]] = []
            self.frames: list[list[dict[str, str]]] = []
            self.links: list[str] = []
            self.captions: list[str] = []

        def subheader(self, message: str) -> None:
            pass

        def caption(self, message: str) -> None:
            self.captions.append(message)

        def columns(self, count: int) -> tuple[Any, ...]:
            return tuple(self for _ in range(count))

        def metric(self, label: str, value: str) -> None:
            self.metrics.append((label, value))

        def dataframe(self, rows: list[dict[str, str]], **kwargs: object) -> None:
            self.frames.append(rows)

        def expander(self, label: str) -> Any:
            return nullcontext()

        def write(self, message: str) -> None:
            pass

        def link_button(self, label: str, url: str) -> None:
            self.links.append(url)

    construction = paused_state_with_portfolio_and_explanation()["__interrupt__"][0].value[
        "portfolio_construction"
    ]
    st = FakeStreamlit()

    _render_portfolio(st, construction)

    assert ("Total weight", "100.00%") in st.metrics
    assert ("Positions", "5") in st.metrics
    assert st.frames[0][0] == {
        "Symbol": "SPY",
        "Sleeve": "growth",
        "Source category": "Large Blend",
        "Weight": "14.38%",
        "Initial": "$3,595.00",
        "Monthly": "$71.90",
        "Deterministic reason": "supports_growth_target",
    }
    assert any(row["Constraint"] == "Maximum one source category" for row in st.frames[1])
    assert all(row["Outcome"] == "pass" for row in st.frames[2])
    assert set(st.links) == {
        f"https://finance.yahoo.com/quote/{symbol}/"
        for symbol in ("SPY", "VTI", "QQQ", "VEA", "BND")
    }
    assert any("not a recommendation" in caption for caption in st.captions)


def test_renderer_shows_construction_failure_without_review_controls() -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.errors: list[str] = []
            self.payloads: list[object] = []

        def error(self, message: str) -> None:
            self.errors.append(message)

        def json(self, payload: object) -> None:
            self.payloads.append(payload)

    error = {
        "type": "construction_guardrail",
        "code": "persisted_construction_mismatch",
        "message": "Persisted construction differs from deterministic recomputation.",
    }
    st = FakeStreamlit()

    _render_run(
        st,
        DashboardRun(
            graph=FakeGraph(),
            config={},
            state={"status": "construction_blocked", "construction_errors": [error]},
        ),
    )

    assert st.errors == ["The workflow stopped before human review."]
    assert st.payloads == [[error]]


def test_dashboard_run_resumes_exact_thread_after_approval() -> None:
    graph = FakeGraph()
    run = DashboardRun(
        graph=graph,
        config={"configurable": {"thread_id": "dashboard-review"}},
        state=paused_state(),
    )

    completed = run.resume("approve")

    assert completed["status"] == "approved"
    assert run.config["configurable"]["thread_id"] == "dashboard-review"
    assert len(graph.inputs) == 1
    assert graph.inputs[0].resume == {"action": "approve"}


@pytest.mark.parametrize("action", ["edit", "reject"])
def test_revision_decisions_require_feedback(action: str) -> None:
    run = DashboardRun(graph=FakeGraph(), config={}, state=paused_state())

    with pytest.raises(ValueError, match="require reviewer feedback"):
        run.resume(action, "  ")


def test_dashboard_run_passes_trimmed_revision_feedback() -> None:
    graph = FakeGraph()
    run = DashboardRun(graph=graph, config={}, state=paused_state())

    run.resume("edit", "  Lower the growth range.  ")

    assert graph.inputs[0].resume == {
        "action": "edit",
        "feedback": "Lower the growth range.",
    }


def test_parse_excluded_sectors_trims_and_deduplicates_case_insensitively() -> None:
    assert parse_excluded_sectors(" Energy,utilities, energy, ,Health Care ") == [
        "Energy",
        "utilities",
        "Health Care",
    ]


def test_policy_only_dashboard_run_needs_no_live_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StartGraph(FakeGraph):
        def invoke(self, value: object, config: dict[str, Any]) -> dict[str, Any]:
            return paused_state()

    monkeypatch.setattr(dashboard, "build_graph", lambda **kwargs: StartGraph())
    monkeypatch.setattr(
        dashboard,
        "ChromaDocumentStore",
        lambda **kwargs: pytest.fail("policy-only run opened Chroma"),
    )
    monkeypatch.setattr(
        dashboard,
        "Neo4jGraphStore",
        lambda **kwargs: pytest.fail("policy-only run opened Neo4j"),
    )

    run = dashboard.start_dashboard_run(
        {"horizon_years": 10},
        DashboardOptions(),
        thread_id="offline-dashboard",
    )

    assert run.state["status"] == "awaiting_human_review"
    assert run.config == {"configurable": {"thread_id": "offline-dashboard"}}


def test_durable_dashboard_run_restores_and_resumes_with_a_new_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = DurableMemoryCheckpointStore()
    token = str(uuid4())
    monkeypatch.setattr(dashboard, "PostgresCheckpointStore", lambda connection_uri: store)

    started = dashboard.start_dashboard_run(
        valid_profile().model_dump(mode="json"),
        DashboardOptions(durable_checkpoint=True),
        thread_id=token,
    )

    assert started.durable is True
    assert started.graph is None
    assert started.thread_id == token
    assert review_payload(started.state)["kind"] == "portfolio_policy_review"

    restored = load_dashboard_run(token, checkpoint_store=store)
    assert restored.state["status"] == "awaiting_human_review"
    assert review_payload(restored.state)["kind"] == "portfolio_policy_review"

    completed = restored.resume("approve")
    assert completed["status"] == "approved"
    assert load_dashboard_run(token, checkpoint_store=store).state["status"] == "approved"
    assert store.setup_calls == 3
    assert store.open_calls == 4


def test_durable_restore_preserves_full_json_portfolio_and_revalidates_before_resume() -> None:
    store = DurableMemoryCheckpointStore()
    token = str(uuid4())
    profile = valid_profile()
    observed_at = datetime(2026, 8, 28, 11, tzinfo=UTC)
    checked_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    evidence = select_candidate_evidence(
        profile,
        [
            _construction_source(symbol, category, observed_at, checked_at)
            for symbol, category in (
                ("SPY", "Large Blend"),
                ("VTI", "Large Blend"),
                ("QQQ", "Large Growth"),
                ("VEA", "Foreign Large Blend"),
                ("BND", "Intermediate Core Bond"),
            )
        ],
        query="durable portfolio regression evidence",
        checked_at=checked_at,
        max_age=timedelta(hours=24),
        limit=5,
    )

    class FixedRetriever:
        def retrieve(self, requested_profile: InvestorProfile, *, limit: int = 5) -> Any:
            assert requested_profile == profile
            assert limit == 5
            return evidence.model_copy(deep=True)

    graph = build_graph(checkpointer=store.saver, candidate_retriever=FixedRetriever())
    config = {"configurable": {"thread_id": token}}
    paused = dict(graph.invoke({"profile": profile.model_dump(mode="json")}, config=config))
    expected = json.loads(
        json.dumps(review_payload(paused)["portfolio_construction"], sort_keys=True)
    )

    restored = load_dashboard_run(token, checkpoint_store=store)
    payload = review_payload(restored.state)

    assert payload["portfolio_construction"] == expected
    assert payload["portfolio_construction"]["draft"]["total_weight_bps"] == 10_000
    assert (
        sum(
            position["initial_usd_cents"]
            for position in payload["portfolio_construction"]["draft"]["positions"]
        )
        == payload["portfolio_construction"]["draft"]["initial_total_cents"]
    )

    completed = restored.resume("approve")
    assert completed["status"] == "approved"
    assert (
        PortfolioConstructionBundle.model_validate(completed["portfolio_construction"]).model_dump(
            mode="json", exclude_none=True
        )
        == expected
    )


@pytest.mark.parametrize("token", ["", "not-a-token", "00000000-0000-1000-8000-000000000000"])
def test_saved_review_requires_an_opaque_version_four_uuid(token: str) -> None:
    with pytest.raises(ValueError, match="Review token"):
        load_dashboard_run(token, checkpoint_store=DurableMemoryCheckpointStore())
