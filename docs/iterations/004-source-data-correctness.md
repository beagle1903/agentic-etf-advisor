# Iteration 004: Source-data correctness follow-up

- Status: Complete
- Started: 2026-08-27

## Goal

Correct three post-merge review findings before expanding the graph or relying on its
financial metadata: normalize Yahoo's fallback expense-ratio units, replace stale graph
relationships on re-upsert, and stop presenting fund-family metadata as a legal issuer.

## Deliverables

- Separate normalization for Yahoo `netExpenseRatio` percentage points and
  `annualReportExpenseRatio` decimal fractions.
- Source and ETF relationship replacement on every Neo4j upsert, including missing metadata.
- `FundFamily` graph nodes and `fund_family` retrieval context in place of unsupported issuer
  claims.
- A version-2 retrieval fixture and documentation aligned with the corrected graph contract.
- Offline regression tests for fallback conversion, relationship removal, and ambiguous
  legacy context.

## Acceptance criteria

- An annual-report fallback of `0.0003` is stored and rendered as `0.03%`.
- `netExpenseRatio` remains the preferred percentage-point field when both values exist.
- Re-upserting a stable source ID removes obsolete fund-family and category relationships
  before recreating only the currently reported values.
- Hybrid retrieval exposes `fund_family`, never infers `issuer` from Yahoo `fundFamily`, and
  rejects duplicate legacy contexts rather than choosing one arbitrarily.
- The packaged evaluation remains deterministic and scores fund-family/category accuracy.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and
  `uv run pytest` pass without network access.
- No credentials, private data, trade execution, or guaranteed-return language is added.

## Data migration

Re-ingesting a source removes legacy `REPORTS_ISSUER` and `ISSUED_BY` relationships for its
ETF. Existing development databases may retain orphaned `Issuer` nodes and the old issuer
constraint; they are no longer queried or exposed. A fresh development graph or explicit
cleanup can remove those unused artifacts.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes for 42 files.
- `uv run mypy` passes for 21 source files.
- `uv run pytest` passes (26 tests) without network access.
- `uv run etf-advisor evaluate-retrieval` reports dataset version 2 with unchanged MRR of
  `0.875`, graph-context recall of `1.0`, and fund-family/category field accuracy of `1.0`.
- `docker compose config --quiet` passes and the local Chroma, Neo4j, and PostgreSQL services
  are healthy.
- Live SPY/QQQ graph re-ingestion succeeds with two fund-family links and zero legacy issuer
  relationships. A synthetic same-ID upsert verified changed and missing metadata, then
  removed all synthetic records.
- `uv build` succeeds for both the source distribution and wheel.
