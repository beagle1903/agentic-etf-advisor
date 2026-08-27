# Iteration 000: Foundation and approval lifecycle

- Status: Complete
- Started: 2026-08-27

## Goal

Create a reproducible project foundation and prove that a LangGraph workflow can validate
input, pause for review, and resume safely without model or data-provider credentials.

## Deliverables

- Python package and locked dependency set.
- Deterministic investor-profile and policy-draft nodes.
- Human review interrupt with approve and reject behavior.
- Automated unit tests and CI workflow.
- Docker Compose services for Chroma, Neo4j, and PostgreSQL.
- Product, architecture, ADR, iteration, and runbook documentation hierarchy.
- Root `AGENTS.md` and a small Cursor project rule.

## Acceptance criteria

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run pytest` passes.
- `uv run etf-advisor demo` pauses and resumes successfully.
- `docker compose config` validates.
- The Git repository uses `main` and contains no credentials.

## Deferred to iteration 001

- Curated ETF source ingestion.
- Chroma retrieval with provenance.
- Minimal Neo4j ETF schema and graph enrichment.
- Provider adapters and embeddings.
- LangSmith dataset and retrieval evaluation.
- Dashboard rendering of the review interrupt.
- Cursor hooks, added only after the repeated command and cross-platform behavior are clear.

## Verification evidence

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed.
- `uv run mypy`: passed for nine source files.
- `uv run pytest`: five tests passed.
- `uv run etf-advisor demo`: paused at human review and resumed after approval.
- `docker compose config --quiet`: passed.
- Chroma, Neo4j, and PostgreSQL reached healthy container status on Docker Desktop.
- Chroma `/api/v2/heartbeat` returned a heartbeat payload.
- `docker build --tag agentic-etf-advisor:dev .`: passed.
- Neo4j Bolt uses host port `17687` because Windows reserves the standard port on this machine.
