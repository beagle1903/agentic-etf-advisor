"""Streamlit presentation for the local, human-reviewed ETF policy workflow."""

from __future__ import annotations

import hashlib
from collections.abc import MutableMapping
from importlib import import_module
from typing import Any

from etf_advisor.dashboard import (
    DashboardOptions,
    DashboardRun,
    delete_saved_review,
    inspect_saved_review_lifecycle,
    load_dashboard_run,
    parse_excluded_sectors,
    review_payload,
    start_dashboard_run,
)

_CREATION_IN_PROGRESS_KEY = "review_creation_in_progress"
_CREATION_ERROR_KEY = "review_creation_error"
_SELECTED_REVIEW_KEY = "selected_review_token"
_CREATION_ERROR_MESSAGE = (
    "The workflow could not create a review draft. Check the local services and "
    "provider configuration, then try again."
)


def main() -> None:
    """Render the local dashboard without importing Streamlit in base installations."""

    st = import_module("streamlit")

    st.set_page_config(page_title="Agentic ETF Advisor", page_icon="📊", layout="wide")
    st.title("Agentic ETF Advisor")
    st.caption(
        "Educational decision support with deterministic policy calculations and explicit "
        "human review. No recommendation or trade is produced."
    )

    query_token = str(st.query_params.get("review", "")).strip()
    if (
        "dashboard_run" not in st.session_state
        and query_token
        and st.session_state.get("restore_attempted_token") != query_token
    ):
        _restore_saved_run(st, query_token)

    with st.sidebar:
        st.header("Saved review")
        resume_token = st.text_input(
            "Review token",
            value=query_token,
            help=(
                "Restores one PostgreSQL-backed local review. "
                "The token does not authenticate a user."
            ),
        )
        if st.button("Restore saved review"):
            _restore_saved_run(st, resume_token)

        st.header("Investor profile")
        horizon_years = st.number_input("Horizon (years)", 1, 60, 12)
        risk_tolerance = st.selectbox(
            "Risk tolerance", ["conservative", "moderate", "aggressive"], index=1
        )
        objective = st.selectbox("Objective", ["income", "balanced", "growth"], index=1)
        max_drawdown_pct = st.number_input(
            "Maximum tolerable drawdown (%)", 0.1, 100.0, 25.0, step=0.5
        )
        initial_investment_usd = st.number_input(
            "Initial amount (USD)", 0.0, 1_000_000_000_000.0, 25_000.0, step=500.0
        )
        recurring_monthly_usd = st.number_input(
            "Recurring monthly amount (USD)",
            0.0,
            1_000_000_000_000.0,
            500.0,
            step=50.0,
        )
        excluded_sectors = st.text_input(
            "Excluded sectors", help="Optional comma-separated research constraints."
        )
        with_evidence = st.checkbox(
            "Attach local source evidence",
            help="Requires indexed Chroma and Neo4j data.",
        )
        with_explanation = st.checkbox(
            "Generate grounded explanation",
            disabled=not with_evidence,
            help="Requires source evidence and a configured provider.",
        )
        durable_checkpoint = st.checkbox(
            "Keep review in local PostgreSQL",
            help="Requires the checkpoint extra and the local PostgreSQL service.",
        )
        candidate_limit = st.slider("Evidence candidates", 1, 10, 5)
        _render_creation_button(st)

    if st.session_state.get(_CREATION_IN_PROGRESS_KEY, False):
        profile: dict[str, object] = {
            "horizon_years": int(horizon_years),
            "risk_tolerance": risk_tolerance,
            "objective": objective,
            "max_drawdown_pct": float(max_drawdown_pct),
            "initial_investment_usd": float(initial_investment_usd),
            "recurring_monthly_usd": float(recurring_monthly_usd),
            "excluded_sectors": parse_excluded_sectors(excluded_sectors),
        }
        try:
            st.session_state["dashboard_run"] = start_dashboard_run(
                profile,
                DashboardOptions(
                    with_evidence=with_evidence,
                    with_explanation=with_explanation if with_evidence else False,
                    durable_checkpoint=durable_checkpoint,
                    candidate_limit=candidate_limit,
                ),
            )
            run = st.session_state["dashboard_run"]
            st.session_state.pop(_CREATION_ERROR_KEY, None)
            if run.durable:
                st.query_params["review"] = run.thread_id
                st.session_state[_SELECTED_REVIEW_KEY] = run.thread_id
            else:
                st.query_params.pop("review", None)
                st.session_state.pop(_SELECTED_REVIEW_KEY, None)
        except Exception:
            st.session_state.pop("dashboard_run", None)
            st.session_state[_CREATION_ERROR_KEY] = _CREATION_ERROR_MESSAGE
        finally:
            st.session_state[_CREATION_IN_PROGRESS_KEY] = False
        st.rerun()

    creation_error = st.session_state.get(_CREATION_ERROR_KEY)
    if isinstance(creation_error, str):
        st.error(creation_error)

    run = st.session_state.get("dashboard_run")
    if not isinstance(run, DashboardRun):
        st.info("Complete the profile to create a local review draft.")
        selected = st.session_state.get(_SELECTED_REVIEW_KEY)
        if isinstance(selected, str) and selected:
            _render_saved_lifecycle_selection(st, selected)
        _render_safety_boundary(st, durable=False)
        return

    _render_run(st, run)
    _render_safety_boundary(st, durable=run.durable)


def _render_creation_button(st: Any) -> None:
    """Render a submission control that locks before review creation begins."""

    creation_in_progress = bool(st.session_state.get(_CREATION_IN_PROGRESS_KEY, False))
    st.button(
        "Create review draft",
        type="primary",
        disabled=creation_in_progress,
        on_click=_request_review_creation,
        args=(st.session_state,),
    )
    if creation_in_progress:
        st.caption("Creating review draft…")


def _request_review_creation(session_state: MutableMapping[str, Any]) -> None:
    """Queue one creation run and clear any error from the previous attempt."""

    if session_state.get(_CREATION_IN_PROGRESS_KEY, False):
        return
    session_state[_CREATION_IN_PROGRESS_KEY] = True
    session_state.pop(_CREATION_ERROR_KEY, None)


def _restore_saved_run(st: Any, review_token: str) -> None:
    """Restore an exact durable thread while keeping database details out of the UI."""

    token = review_token.strip()
    st.session_state["restore_attempted_token"] = token
    st.session_state[_SELECTED_REVIEW_KEY] = token
    if token:
        st.query_params["review"] = token
    else:
        st.query_params.pop("review", None)
    try:
        run = load_dashboard_run(token)
    except Exception:
        st.session_state.pop("dashboard_run", None)
        st.error(
            "The saved review could not be restored. Check the token, checkpoint dependency, "
            "and local PostgreSQL service."
        )
        return
    st.session_state["dashboard_run"] = run
    st.query_params["review"] = run.thread_id


def _render_run(st: Any, run: DashboardRun) -> None:
    state = run.state
    status = state.get("status", "unknown")
    if run.durable:
        st.caption("Durable local review token — keep it private to this development machine.")
        st.code(run.thread_id)
        st.session_state[_SELECTED_REVIEW_KEY] = run.thread_id

    lifecycle: dict[str, Any] = {"status": "unmanaged"}
    history: dict[str, Any] | None = None
    managed_revision = run.checkpoint_store is not None and "revision_ledger" in state
    if managed_revision:
        lifecycle = _render_lifecycle_status(st, run)
        try:
            history = run.audit()
        except ValueError:
            st.error(
                "The saved audit history failed validation. Review and retry controls are disabled."
            )
        if history is not None:
            _render_audit_history(st, history)

        if run.submission_outcome_unknown:
            st.warning(
                "The previous submission outcome is unknown. Refresh this exact thread before "
                "submitting another action."
            )
        if st.button("Refresh exact thread", key=f"refresh-{_widget_scope(run.thread_id)}"):
            try:
                run.refresh()
            except Exception:
                st.error(
                    "The exact thread could not be refreshed. No workflow action was submitted."
                )
                return
            st.rerun()

    if status == "awaiting_human_review":
        try:
            payload = review_payload(state)
        except ValueError:
            st.error("The workflow returned an invalid review contract.")
        else:
            st.subheader("Human review")
            st.write(payload["question"])
            _render_policy(st, payload["draft_policy"])
            if "portfolio_construction" in payload:
                _render_portfolio(st, payload["portfolio_construction"])
            if "candidate_screening" in payload:
                _render_screening(st, payload["candidate_screening"])
            if "candidate_evidence" in payload:
                _render_evidence(st, payload["candidate_evidence"])
            if "draft_explanation" in payload:
                _render_explanation(st, payload["draft_explanation"])
            if managed_revision and history is not None and not run.submission_outcome_unknown:
                _render_decision_form(st, run, payload)

    elif status == "approved":
        st.success(state.get("final_message", "Review approved."))
    elif status == "needs_revision":
        st.warning(state.get("final_message", "The draft needs revision."))
    else:
        st.error("The workflow stopped before human review.")
        errors = [
            *state.get("validation_errors", []),
            *state.get("evidence_errors", []),
            *state.get("screening_errors", []),
            *state.get("construction_errors", []),
            *state.get("explanation_errors", []),
        ]
        if errors:
            has_provider_diagnostic = any(
                isinstance(error, dict) and error.get("provider") and error.get("code")
                for error in errors
            )
            has_contract_diagnostic = any(
                isinstance(error, dict)
                and error.get("type") == "explanation_contract"
                and error.get("code")
                for error in errors
            )
            if has_provider_diagnostic:
                st.caption(
                    "Provider diagnostics are redacted: credentials, prompts, source content, "
                    "and raw model responses are not displayed."
                )
            if has_contract_diagnostic:
                st.caption(
                    "Explanation contract diagnostics identify only the failed local validation "
                    "rule; generated text and raw model responses are not displayed."
                )
            st.json(errors)
        retry = _retry_target(history) if history is not None else None
        if retry is not None and not run.submission_outcome_unknown:
            _render_retry_control(st, run, retry)

    if run.durable and managed_revision:
        _render_delete_control(st, run.thread_id, lifecycle)
    elif managed_revision:
        _render_memory_discard(st, run)


def _render_policy(st: Any, policy: dict[str, Any]) -> None:
    st.subheader("Illustrative policy")
    target = policy["target_allocation"]
    growth = float(target["growth_assets_pct"])
    defensive = float(target["defensive_assets_pct"])
    first, second, third = st.columns(3)
    first.metric("Growth assets", f"{growth:.1f}%")
    second.metric("Defensive assets", f"{defensive:.1f}%")
    third.metric("Maximum drawdown input", f"{policy['max_drawdown_pct']:.1f}%")

    st.dataframe(
        [
            _cash_flow_row("Initial", policy["initial_investment_usd"]),
            _cash_flow_row("Monthly", policy["recurring_monthly_usd"]),
        ],
        hide_index=True,
        width="stretch",
    )
    bands = policy["allocation_bands"]
    st.dataframe(
        [
            {
                "Policy sleeve": "Growth assets",
                "Illustrative band": _pct_band(bands["growth_assets_pct"]),
                "Selected target": f"{growth:.2f}%",
            },
            {
                "Policy sleeve": "Defensive assets",
                "Illustrative band": _pct_band(bands["defensive_assets_pct"]),
                "Selected target": f"{defensive:.2f}%",
            },
        ],
        hide_index=True,
        width="stretch",
    )
    with st.expander("Policy notes"):
        for note in policy["notes"]:
            st.text(note)


def _cash_flow_row(label: str, allocation: dict[str, Any]) -> dict[str, str]:
    return {
        "Cash flow": label,
        "Total": _usd(allocation["total_usd"]),
        "Growth": _usd(allocation["growth_assets_usd"]),
        "Defensive": _usd(allocation["defensive_assets_usd"]),
    }


def _render_evidence(st: Any, bundle: dict[str, Any]) -> None:
    st.subheader("Source evidence")
    st.caption(f"Freshness checked at {bundle['checked_at']} · Query: {bundle['query']}")
    for warning in bundle.get("warnings", []):
        st.warning(warning)
    for candidate in bundle["candidates"]:
        with st.expander(f"{candidate['symbol']} · {candidate['name']}"):
            left, right = st.columns(2)
            left.write(f"Category: {candidate.get('category') or 'Not reported'}")
            left.write(f"Fund family/provider: {candidate.get('fund_family') or 'Not reported'}")
            right.write(f"Source: {candidate['source']}")
            right.write(f"Observed: {candidate['observed_at']}")
            st.text(candidate["content"])
            st.link_button("Open source", candidate["source_url"])


def _render_screening(st: Any, bundle: dict[str, Any]) -> None:
    st.subheader("Deterministic candidate screening")
    policy = bundle["policy"]
    st.caption(
        "Illustrative research filters — not suitability thresholds or an ETF ranking. "
        f"Expense ratio ≤ {policy['max_expense_ratio_pct']:g}%, "
        f"average daily volume ≥ {policy['min_average_daily_volume']:g}, "
        f"top-ten concentration ≤ {policy['max_top_10_concentration_pct']:g}%."
    )
    st.dataframe(
        [
            {
                "Symbol": candidate["symbol"],
                "Result": candidate["verdict"],
                "Failed rules": ", ".join(
                    rule["reason_code"] for rule in candidate["rules"] if rule["verdict"] == "fail"
                )
                or "—",
                "Unknown rules": ", ".join(
                    rule["reason_code"]
                    for rule in candidate["rules"]
                    if rule["verdict"] == "unknown"
                )
                or "—",
            }
            for candidate in bundle["candidates"]
        ],
        hide_index=True,
        width="stretch",
    )
    for candidate in bundle["candidates"]:
        with st.expander(f"{candidate['symbol']} screening details"):
            for rule in candidate["rules"]:
                st.write(f"{rule['criterion']}: {rule['verdict']} · {rule['reason_code']}")
                st.caption(rule["message"])
                if rule.get("unresolved_exclusions"):
                    st.caption("Unresolved exclusions: " + ", ".join(rule["unresolved_exclusions"]))
                citation = rule.get("citation")
                if citation:
                    st.link_button(
                        f"Source · {citation['field_name']} · {citation['observed_at']}",
                        citation["source_url"],
                    )


def _render_portfolio(st: Any, bundle: dict[str, Any]) -> None:
    st.subheader("Illustrative model portfolio")
    st.caption(
        "Deterministically constructed from the validated policy and source evidence. "
        "The model and dashboard do not select instruments or change allocations. This is "
        "not a recommendation, suitability decision, forecast, guarantee, or trade instruction."
    )
    draft = bundle["draft"]
    policy = bundle["policy"]
    first, second, third, fourth = st.columns(4)
    first.metric("Total weight", _bps(draft["total_weight_bps"]))
    second.metric("Positions", str(len(draft["positions"])))
    third.metric("Initial total", _usd_cents(draft["initial_total_cents"]))
    fourth.metric("Monthly total", _usd_cents(draft["recurring_total_cents"]))

    st.dataframe(
        [
            {
                "Symbol": position["symbol"],
                "Sleeve": position["sleeve"],
                "Source category": position["source_category"],
                "Weight": _bps(position["weight_bps"]),
                "Initial": _usd_cents(position["initial_usd_cents"]),
                "Monthly": _usd_cents(position["recurring_usd_cents"]),
                "Deterministic reason": position["reason_code"],
            }
            for position in draft["positions"]
        ],
        hide_index=True,
        width="stretch",
    )

    with st.expander("Construction constraints and validation"):
        st.dataframe(
            [
                {
                    "Constraint": "Position count",
                    "Configured rule": f"{policy['min_positions']} to {policy['max_positions']}",
                },
                {
                    "Constraint": "Position weight",
                    "Configured rule": (
                        f"{_bps(policy['min_position_weight_bps'])} to "
                        f"{_bps(policy['max_position_weight_bps'])}"
                    ),
                },
                {
                    "Constraint": "Maximum one source category",
                    "Configured rule": _bps(policy["max_category_weight_bps"]),
                },
                {
                    "Constraint": "Weight precision",
                    "Configured rule": _bps(policy["weight_precision_bps"]),
                },
            ],
            hide_index=True,
            width="stretch",
        )
        st.dataframe(
            [
                {
                    "Validation check": check["name"],
                    "Outcome": "pass" if check["passed"] else "fail",
                    "Reason": check.get("reason_code") or "—",
                    "Details": check["message"],
                }
                for check in bundle["validation"]["checks"]
            ],
            hide_index=True,
            width="stretch",
        )

    for position in draft["positions"]:
        with st.expander(f"{position['symbol']} allocation evidence"):
            st.write(f"Deterministic reason: {position['reason_code']}")
            st.write(f"Policy reference: {position['policy_reference']}")
            st.write(f"Source category: {position['source_category']}")
            st.write(f"Source: {position['source']}")
            st.write(f"Observed: {position['observed_at']}")
            st.caption("Screening evidence: " + ", ".join(position["screening_reason_codes"]))
            st.link_button("Open attributable source", position["source_url"])

    excluded = bundle["excluded_candidates"]
    if excluded:
        with st.expander("Excluded candidate audit"):
            st.dataframe(
                [
                    {
                        "Symbol": candidate["symbol"],
                        "Screening result": candidate["screening_verdict"],
                        "Exclusion reason": candidate["reason_code"],
                        "Screening reasons": ", ".join(candidate["screening_reason_codes"]) or "—",
                    }
                    for candidate in excluded
                ],
                hide_index=True,
                width="stretch",
            )
    else:
        st.caption("No candidate-local exclusions were needed for this deterministic draft.")


def _render_explanation(st: Any, bundle: dict[str, Any]) -> None:
    st.subheader("Grounded explanation")
    st.caption(f"Provider: {bundle['provider']} · Model: {bundle['model']}")
    explanation = bundle["explanation"]
    _render_statement(st, "Summary", explanation["summary"])
    for title, key in (
        ("Policy points", "policy_points"),
        ("Evidence points", "evidence_points"),
        ("Trade-offs", "tradeoffs"),
    ):
        st.write(title)
        for statement in explanation[key]:
            _render_statement(st, None, statement)
    with st.expander("Citations and limitations"):
        for citation in bundle["citations"]:
            st.link_button(
                f"{citation['symbol']} · {citation['source']} · {citation['observed_at']}",
                citation["source_url"],
            )
        for limitation in bundle["limitations"]:
            st.text(limitation)


def _render_statement(st: Any, title: str | None, statement: dict[str, Any]) -> None:
    if title:
        st.write(title)
    st.text(statement["text"])
    st.caption(
        f"Grounding: {statement['basis']} · References: {', '.join(statement['references'])}"
    )


def _render_decision_form(st: Any, run: DashboardRun, payload: dict[str, Any]) -> None:
    revision_id = payload.get("revision_id")
    if not isinstance(revision_id, str):
        st.error("The review is missing its revision identity.")
        return
    inputs = run.state["revision_ledger"]["revisions"][-1]["inputs"]
    widget = f"review-{_widget_scope(run.thread_id)}-{revision_id}"
    label = st.radio(
        "Decision",
        ["Approve", "Edit", "Reject"],
        horizontal=True,
        key=f"{widget}-action",
    )
    disposition = None
    if label == "Edit":
        disposition = "revise"
    elif label == "Reject":
        disposition = st.radio(
            "Reject outcome",
            ["Revise", "Close"],
            horizontal=True,
            key=f"{widget}-disposition",
        ).lower()
    selected: list[str] = []
    if disposition == "revise":
        selected = st.multiselect(
            "Typed feedback",
            [
                "profile",
                "evidence",
                "screening_policy",
                "construction_policy",
                "explanation",
            ],
            help="Select one or more explicit change classes. The workflow chooses routing.",
            key=f"{widget}-classes",
        )
    with st.form(widget):
        note = ""
        form_values: dict[str, Any] = {}
        if label != "Approve":
            note = st.text_area(
                "Reviewer note",
                help=(
                    "Required audit context. Free text never selects a rerun stage or mutates "
                    "financial inputs."
                ),
                key=f"{widget}-note",
            )
        if disposition == "revise":
            form_values = _render_feedback_fields(st, widget, selected, inputs)
        submitted = st.form_submit_button("Submit decision")
    if not submitted:
        return
    try:
        feedback_items = _build_feedback_items(selected, form_values)
        run.resume(
            label.lower(),
            note,
            disposition=disposition,
            feedback_items=feedback_items,
            expected_revision_id=revision_id,
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error(
            "The app could not confirm that the saved review resumed. Check PostgreSQL, "
            "then restore the token before submitting another decision."
        )
        return
    st.rerun()


def _render_feedback_fields(
    st: Any, widget: str, selected: list[str], inputs: dict[str, Any]
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    profile = inputs["profile"]
    if "profile" in selected:
        st.caption("Profile feedback uses complete validated inputs; only explicit fields change.")
        values["profile"] = {
            "horizon_years": int(
                st.number_input(
                    "Revised horizon (years)",
                    1,
                    60,
                    int(profile["horizon_years"]),
                    key=widget + "-h",
                )
            ),
            "risk_tolerance": st.selectbox(
                "Revised risk tolerance",
                ["conservative", "moderate", "aggressive"],
                index=["conservative", "moderate", "aggressive"].index(profile["risk_tolerance"]),
                key=widget + "-risk",
            ),
            "objective": st.selectbox(
                "Revised objective",
                ["income", "balanced", "growth"],
                index=["income", "balanced", "growth"].index(profile["objective"]),
                key=widget + "-objective",
            ),
            "max_drawdown_pct": float(
                st.number_input(
                    "Revised maximum drawdown (%)",
                    0.1,
                    100.0,
                    float(profile["max_drawdown_pct"]),
                    key=widget + "-drawdown",
                )
            ),
            "initial_investment_usd": float(
                st.number_input(
                    "Revised initial amount (USD)",
                    0.0,
                    1_000_000_000_000.0,
                    float(profile["initial_investment_usd"]),
                    key=widget + "-initial",
                )
            ),
            "recurring_monthly_usd": float(
                st.number_input(
                    "Revised monthly amount (USD)",
                    0.0,
                    1_000_000_000_000.0,
                    float(profile["recurring_monthly_usd"]),
                    key=widget + "-monthly",
                )
            ),
            "excluded_sectors": parse_excluded_sectors(
                st.text_input(
                    "Revised excluded sectors",
                    value=", ".join(profile["excluded_sectors"]),
                    key=widget + "-sectors",
                )
            ),
        }
    if "evidence" in selected:
        values["evidence"] = {
            "candidate_limit": int(
                st.slider(
                    "Revised evidence candidates",
                    1,
                    10,
                    int(inputs["candidate_limit"]),
                    key=widget + "-candidates",
                )
            )
        }
    if "screening_policy" in selected:
        policy = inputs["screening_policy"]
        values["screening_policy"] = {
            "max_expense_ratio_pct": float(
                st.number_input(
                    "Maximum expense ratio (%)",
                    0.0,
                    100.0,
                    float(policy["max_expense_ratio_pct"]),
                    key=widget + "-expense",
                )
            ),
            "min_average_daily_volume": float(
                st.number_input(
                    "Minimum average daily volume",
                    0.0,
                    value=float(policy["min_average_daily_volume"]),
                    key=widget + "-volume",
                )
            ),
            "max_top_10_concentration_pct": float(
                st.number_input(
                    "Maximum top-ten concentration (%)",
                    0.0,
                    100.0,
                    float(policy["max_top_10_concentration_pct"]),
                    key=widget + "-concentration",
                )
            ),
            "excluded_sector_weight_tolerance_pct": float(
                st.number_input(
                    "Excluded-sector tolerance (%)",
                    0.0,
                    100.0,
                    float(policy["excluded_sector_weight_tolerance_pct"]),
                    key=widget + "-sector-tolerance",
                )
            ),
        }
    if "construction_policy" in selected:
        policy = inputs["construction_policy"]
        values["construction_policy"] = {
            name: int(
                st.number_input(
                    label,
                    minimum,
                    maximum,
                    int(policy[name]),
                    key=f"{widget}-{name}",
                )
            )
            for name, label, minimum, maximum in (
                ("max_candidate_pool_size", "Maximum candidate pool", 1, 10),
                ("min_positions", "Minimum positions", 1, 50),
                ("max_positions", "Maximum positions", 1, 50),
                ("min_position_weight_bps", "Minimum position weight (bps)", 0, 10_000),
                ("max_position_weight_bps", "Maximum position weight (bps)", 0, 10_000),
                ("max_category_weight_bps", "Maximum category weight (bps)", 0, 10_000),
                ("weight_precision_bps", "Weight precision (bps)", 1, 10_000),
            )
        }
        st.caption("The existing source-category sleeve mapping is preserved.")
    if "explanation" in selected:
        values["explanation"] = {
            "instruction": st.text_area(
                "Revised explanation instruction",
                value=inputs.get("explanation_instruction", ""),
                key=widget + "-instruction",
            )
        }
    return values


def _build_feedback_items(selected: list[str], values: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for kind in selected:
        value = values.get(kind, {})
        if kind == "profile":
            items.append({"kind": kind, "patch": value})
        elif kind == "evidence":
            items.append({"kind": kind, "refresh": True, **value})
        elif kind in {"screening_policy", "construction_policy"}:
            items.append({"kind": kind, "patch": value})
        elif kind == "explanation":
            items.append({"kind": kind, "instruction": value.get("instruction", "")})
    return items


def _render_lifecycle_status(st: Any, run: DashboardRun) -> dict[str, Any]:
    try:
        status = run.lifecycle()
    except Exception:
        status = {"status": "failure"}
    label = status["status"]
    if label == "active" and "lifecycle" in status:
        lifecycle = status["lifecycle"]
        if run.durable:
            st.caption(
                f"Durable retention: active · effective interval "
                f"{lifecycle['retention_days']} days · expires {lifecycle['expires_at']}"
            )
        else:
            st.caption(
                "Process-local state: active · discard, browser-session loss, or process loss "
                "has no recovery promise."
            )
    elif label == "expired":
        st.warning(
            "This exact durable review has expired. Restoration is blocked; deletion remains "
            "available."
        )
    elif label == "legacy":
        st.warning("This exact review has no managed lifecycle metadata. Restoration is blocked.")
    elif label in {"failure", "not_found"}:
        st.warning("Lifecycle status is unavailable for this exact review.")
    return status


def _render_audit_history(st: Any, history: dict[str, Any]) -> None:
    with st.expander("Revision and operation history"):
        for revision in history["revisions"]:
            st.write(f"Revision {revision['sequence']} · {revision['status']}")
            st.caption(
                " · ".join(
                    part
                    for part in (
                        f"ID {revision['revision_id']}",
                        f"Parent {revision.get('parent_revision_id') or 'root'}",
                        "Children " + (", ".join(revision["child_revision_ids"]) or "none"),
                    )
                )
            )
            plan = revision.get("plan")
            if plan:
                st.caption(
                    f"Restart {plan['restart_stage']} · feedback "
                    f"{', '.join(plan['feedback_classes'])} · invalidates "
                    f"{', '.join(plan['invalidated'])}"
                )
            if revision.get("snapshot"):
                snapshot = revision["snapshot"]
                st.caption(f"Source snapshot {snapshot['version']} · digest {snapshot['digest']}")
            decision = revision.get("decision")
            if decision:
                st.write(
                    f"Decision: {decision['action']}"
                    + (f" / {decision['disposition']}" if decision.get("disposition") else "")
                )
                if decision.get("note"):
                    st.text(decision["note"])
            for receipt in revision["receipts"]:
                st.caption(
                    f"Operation {receipt['stage']} · attempt {receipt['attempt']} · "
                    f"{receipt['status']} · ID {receipt['operation_id']}"
                )


def _retry_target(history: dict[str, Any] | None) -> dict[str, Any] | None:
    if not history or not history["revisions"]:
        return None
    revision = history["revisions"][-1]
    if revision.get("review_decision_id") or not revision["receipts"]:
        return None
    receipt = revision["receipts"][-1]
    same_stage = [item for item in revision["receipts"] if item["stage"] == receipt["stage"]]
    if same_stage[-1] != receipt or receipt["status"] not in {"failed", "started"}:
        return None
    return {
        "revision_id": revision["revision_id"],
        "operation_id": receipt["operation_id"],
        "stage": receipt["stage"],
        "status": receipt["status"],
    }


def _render_retry_control(st: Any, run: DashboardRun, retry: dict[str, Any]) -> None:
    st.warning(
        f"The current {retry['stage']} attempt is {retry['status']}. An explicit retry may "
        "repeat provider or retrieval cost if the prior outcome was ambiguous."
    )
    if st.button(
        "Retry exact operation",
        key=(
            f"retry-{_widget_scope(run.thread_id)}-{retry['revision_id']}-{retry['operation_id']}"
        ),
    ):
        try:
            run.retry(retry["operation_id"], expected_revision_id=retry["revision_id"])
        except ValueError as exc:
            st.error(str(exc))
            return
        except Exception:
            st.error(
                "The app could not confirm the retry outcome. Refresh this exact thread before "
                "submitting another action."
            )
            return
        st.rerun()


def _render_memory_discard(st: Any, run: DashboardRun) -> None:
    with st.expander("Discard process-local review"):
        confirmed = st.checkbox(
            "I understand this process-local review cannot be recovered.",
            key=f"discard-confirm-{_widget_scope(run.thread_id)}",
        )
        if st.button(
            "Discard process-local state",
            disabled=not confirmed,
            key=f"discard-{_widget_scope(run.thread_id)}",
        ):
            try:
                run.discard()
            except ValueError as exc:
                st.error(str(exc))
                return
            st.session_state.pop("dashboard_run", None)
            st.query_params.pop("review", None)
            st.rerun()


def _render_delete_control(st: Any, review_token: str, lifecycle: dict[str, Any]) -> None:
    scope = _widget_scope(review_token)
    with st.expander("Permanently delete exact saved review"):
        st.warning(
            "Deletion permanently removes the complete checkpoint and audit lineage. There is "
            "no backup, tombstone, or recovery promise."
        )
        confirmation_token = st.text_input(
            "Re-enter the exact review token",
            type="password",
            key=f"delete-token-{scope}",
        )
        confirmed = st.checkbox(
            "I confirm permanent whole-thread deletion.", key=f"delete-confirm-{scope}"
        )
        if st.button(
            "Delete complete saved review",
            disabled=not confirmed or not confirmation_token,
            key=f"delete-{scope}-{lifecycle.get('status', 'unknown')}",
        ):
            outcome = delete_saved_review(review_token, confirmation_token, confirmed=confirmed)
            if outcome == "deleted":
                st.session_state.pop("dashboard_run", None)
                st.session_state.pop(_SELECTED_REVIEW_KEY, None)
                st.query_params.pop("review", None)
                st.success("The complete saved review was deleted.")
                st.rerun()
            elif outcome == "not_found":
                st.warning("No saved review was found for that exact token.")
            else:
                st.error("The saved review was not deleted.")


def _render_saved_lifecycle_selection(st: Any, review_token: str) -> None:
    lifecycle = inspect_saved_review_lifecycle(review_token)
    status = lifecycle["status"]
    if status == "active":
        item = lifecycle["lifecycle"]
        st.caption(
            f"Exact-token lifecycle: active · effective interval {item['retention_days']} days · "
            f"expires {item['expires_at']}"
        )
    elif status == "expired":
        item = lifecycle["lifecycle"]
        st.warning(f"This exact review expired at {item['expires_at']}. It may still be deleted.")
    elif status == "legacy":
        st.warning("This exact review has legacy lifecycle state. It may still be deleted.")
    elif status == "not_found":
        st.warning("No saved review was found for that exact token.")
    else:
        st.warning("Lifecycle status could not be inspected for that exact token.")
    _render_delete_control(st, review_token, lifecycle)


def _widget_scope(value: str) -> str:
    """Return a non-capability widget namespace without exposing the review token."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _render_safety_boundary(st: Any, *, durable: bool) -> None:
    st.divider()
    checkpoint_boundary = (
        "PostgreSQL checkpoints survive browser-session loss, but the review token is not "
        "user authentication and this remains a single-user local workflow."
        if durable
        else "The default review checkpoint is local to this browser session and is not durable."
    )
    st.caption(
        "Educational use only. This local phase performs no brokerage connection, trade, "
        "forecast, or external financial-system write. Market data may be delayed or wrong. "
        f"{checkpoint_boundary}"
    )


def _usd(value: float | int | str) -> str:
    return f"${float(value):,.2f}"


def _usd_cents(value: int) -> str:
    return f"${value / 100:,.2f}"


def _bps(value: int) -> str:
    return f"{value / 100:.2f}%"


def _pct_band(values: list[float]) -> str:
    return f"{values[0]:.2f}% to {values[1]:.2f}%"


if __name__ == "__main__":
    main()
