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
    _render_run,
    _render_screening,
)
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource


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
    state = paused_state_with_evidence_and_explanation()
    state["__interrupt__"][0].value["candidate_evidence"]["objective"] = "growth"

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_review_payload_recomputes_screening_from_evidence() -> None:
    state = paused_state_with_evidence_and_explanation()
    screening = state["__interrupt__"][0].value["candidate_screening"]
    screening["candidates"][0]["rules"][3]["reason_code"] = "expense_ratio_within_limit"

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_review_payload_requires_explanation_to_have_evidence() -> None:
    state = paused_state_with_evidence_and_explanation()
    state["__interrupt__"][0].value.pop("candidate_evidence")

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


def test_review_payload_rejects_explanation_citation_not_matching_evidence() -> None:
    state = paused_state_with_evidence_and_explanation()
    citation = state["__interrupt__"][0].value["draft_explanation"]["citations"][0]
    citation["source_url"] = "https://example.com/different-source"

    with pytest.raises(ValueError, match="failed contract validation"):
        review_payload(state)


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


@pytest.mark.parametrize("token", ["", "not-a-token", "00000000-0000-1000-8000-000000000000"])
def test_saved_review_requires_an_opaque_version_four_uuid(token: str) -> None:
    with pytest.raises(ValueError, match="Review token"):
        load_dashboard_run(token, checkpoint_store=DurableMemoryCheckpointStore())
