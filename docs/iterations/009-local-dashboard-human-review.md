# Iteration 009: Local dashboard human review

- Status: Complete
- Started: 2026-08-28

## Goal

Provide a simple local dashboard that collects the phase-one investor profile, renders the exact
LangGraph review interrupt, and resumes the same workflow thread with an explicit human decision.

## Deliverables

- An optional Streamlit dashboard launched through `etf-advisor dashboard`.
- Profile inputs for horizon, risk tolerance, objective, drawdown, cash flows, and exclusions.
- Review rendering for policy calculations and optional evidence and grounded explanations.
- Approve, edit, and reject controls that resume the exact in-memory graph thread.
- Plain-text rendering for untrusted source and generated content plus visible safety boundaries.
- Offline tests for option validation, interrupt validation, decisions, feedback, and launch wiring.

## Acceptance criteria

- A base policy-only run creates and finalizes a review without network, credentials, Chroma, or
  Neo4j.
- The dashboard consumes the workflow interrupt rather than recomputing policy or evidence.
- Only workflow-allowlisted actions are accepted; edit and reject require reviewer feedback.
- Optional evidence retains source URL and observation timestamp, and optional explanations retain
  grounding references, citations, provider identity, and limitations.
- A stopped or malformed workflow cannot be presented as review-ready.
- Dashboard code does not load Streamlit during base CLI or test imports.
- The UI states that it is educational, performs no trade, and loses checkpoints with the local
  browser session.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and `uv run pytest` pass
  without network access.

## Deferred

- PostgreSQL-backed checkpoints, authentication, concurrent users, and cross-session resume.
- Hosted deployment and a licensed market-data redistribution path.
- Semantic entailment scoring and the curated explanation evaluation dataset.
- ETF allocation selection, forecasts, suitability claims, brokerage connections, and trades.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes for 65 files.
- `uv run mypy` passes for 30 source files.
- `uv run pytest` passes offline (114 tests).
- A Streamlit AppTest completes the default form, review interrupt, and approval lifecycle with
  no application exceptions.
- A headless dashboard launch returns `200 ok` from Streamlit's health endpoint.
