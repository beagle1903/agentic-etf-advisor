# Iteration 005: Market-data quality guardrails

- Status: Complete
- Started: 2026-08-27

## Goal

Make source health explicit and fail closed before retrieval-store writes by adding bounded
Yahoo retries, deterministic freshness assessment, and a read-only health command.

## Deliverables

- A deterministic freshness evaluator with an injected health-check timestamp.
- Per-symbol health results that retain the source, URL, observation timestamp, and age.
- Configurable maximum age and future-clock tolerance with stale and future classifications.
- Bounded Yahoo retries with exponential backoff behind an injected sleeper.
- `etf-advisor data-health` for read-only source inspection.
- An ingestion gate that rejects unhealthy observations before opening Chroma or Neo4j.

## Acceptance criteria

- Current, stale, and future-dated observations are classified deterministically without a
  network or wall-clock dependency in the evaluator.
- An unhealthy report exits nonzero and names every rejected symbol and reason.
- `ingest` performs the health check before constructing either retrieval store.
- Transient Yahoo price-history and metadata failures retry up to the configured attempt
  limit; tests do not sleep.
- The health JSON retains source and observation timestamp metadata for every result.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and
  `uv run pytest` pass without network access.
- No credentials, private data, trade execution, or guaranteed-return language is added.

## Configuration boundary

The default freshness window is 120 hours so normal weekends and common US market holidays
do not automatically block a daily close. It is a configurable safety policy, not a claim
that the data is live. Future observations more than five minutes ahead of the check clock
are rejected. Yahoo remains a development-only source.

## Post-merge correction

Review of the merged slice found that the CLI still read the wall clock directly and that
metadata exceptions were converted to empty metadata outside the retry policy. The command
boundary now injects a callable UTC clock and captures it once per health assessment.
Metadata exceptions retry independently and fail closed after exhaustion, while a successful
metadata object with absent fields remains valid. Regression tests cover an exact freshness
boundary, a single clock read, transient metadata recovery, permanent metadata failure, and
legitimately missing fields.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes for 23 source files.
- `uv run pytest` passes offline (39 tests).
- `docker compose config --quiet` passes.
- `uv build` produces the source distribution and wheel.
- A read-only live `data-health --symbols SPY,QQQ` probe reported both Yahoo observations
  current and retained their source URLs and UTC timestamps.
