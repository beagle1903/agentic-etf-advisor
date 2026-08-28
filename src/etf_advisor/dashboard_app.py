"""Streamlit presentation for the local, human-reviewed ETF policy workflow."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from etf_advisor.dashboard import (
    DashboardOptions,
    DashboardRun,
    load_dashboard_run,
    parse_excluded_sectors,
    review_payload,
    start_dashboard_run,
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
        with st.form("profile-form"):
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
            started = st.form_submit_button("Create review draft", type="primary")

    if started:
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
            if run.durable:
                st.query_params["review"] = run.thread_id
            else:
                st.query_params.pop("review", None)
        except Exception:
            st.session_state.pop("dashboard_run", None)
            st.error(
                "The workflow could not create a review draft. Check the local services and "
                "provider configuration, then try again."
            )

    run = st.session_state.get("dashboard_run")
    if not isinstance(run, DashboardRun):
        st.info("Complete the profile to create a local review draft.")
        _render_safety_boundary(st, durable=False)
        return

    _render_run(st, run)
    _render_safety_boundary(st, durable=run.durable)


def _restore_saved_run(st: Any, review_token: str) -> None:
    """Restore an exact durable thread while keeping database details out of the UI."""

    token = review_token.strip()
    st.session_state["restore_attempted_token"] = token
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
    if status == "awaiting_human_review":
        try:
            payload = review_payload(state)
        except ValueError:
            st.error("The workflow returned an invalid review contract.")
            return
        st.subheader("Human review")
        st.write(payload["question"])
        _render_policy(st, payload["draft_policy"])
        if "candidate_evidence" in payload:
            _render_evidence(st, payload["candidate_evidence"])
        if "draft_explanation" in payload:
            _render_explanation(st, payload["draft_explanation"])
        _render_decision_form(st, run)
        return

    if status == "approved":
        st.success(state.get("final_message", "Review approved."))
    elif status == "needs_revision":
        st.warning(state.get("final_message", "The draft needs revision."))
    else:
        st.error("The workflow stopped before human review.")
        errors = [
            *state.get("validation_errors", []),
            *state.get("evidence_errors", []),
            *state.get("explanation_errors", []),
        ]
        if errors:
            st.json(errors)


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


def _render_decision_form(st: Any, run: DashboardRun) -> None:
    with st.form("review-decision"):
        label = st.radio("Decision", ["Approve", "Edit", "Reject"], horizontal=True)
        feedback = st.text_area(
            "Reviewer feedback",
            help="Required for Edit and Reject. No external financial system is changed.",
        )
        submitted = st.form_submit_button("Submit decision")
    if not submitted:
        return
    try:
        run.resume(label.lower(), feedback)
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


if __name__ == "__main__":
    main()
