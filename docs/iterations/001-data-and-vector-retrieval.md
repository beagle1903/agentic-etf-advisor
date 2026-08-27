# Iteration 001: Live source ingestion and vector retrieval

- Status: Complete
- Started: 2026-08-27

## Goal

Create the first real data path: fetch a small timestamped ETF snapshot from Yahoo Finance,
convert it into an attributable source document, store it in Chroma, and retrieve it with a
natural-language query.

## Deliverables

- Normalized `ETFObservation` model with UTC observation timestamps.
- Yahoo Finance adapter with fail-closed behavior for missing or invalid price history.
- Stable document IDs and source metadata for Chroma.
- Chroma HTTP document store with upsert and semantic search operations.
- `etf-advisor ingest` and `etf-advisor search` commands.
- Offline tests using fake market-data and Chroma clients.

## Acceptance criteria

- `uv sync --extra rag` installs the data/retrieval dependencies.
- `uv run pytest` passes without network access.
- `uv run etf-advisor ingest --symbols SPY,QQQ` upserts timestamped source documents when
  Yahoo Finance and Chroma are available.
- `uv run etf-advisor search "broad US equity exposure"` returns document IDs, distances,
  source URLs, and observation timestamps.
- Missing price history fails the ingestion instead of producing an ungrounded document.
- `.env` remains ignored and no secret values are logged.

## Verification

- `git check-ignore -v .env` confirms the repository-level `.gitignore` rule.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes.
- `uv run pytest` passes (8 tests).
- Live `ingest --symbols SPY,QQQ` upserted two documents into local Chroma on 2026-08-27.
- Live `search "broad US equity exposure"` retrieved both documents with provenance metadata.
- Docker Compose services Chroma, Neo4j, and Postgres report healthy.

## Post-completion correction

Yahoo Finance reports `netExpenseRatio` in percentage points. The ingestion contract now
names this value `expense_ratio_pct`, renders an explicit `%` sign, and stores the same
unit-bearing field name in Chroma metadata. Regression tests prevent future conversion or
display ambiguity.

The existing SPY and QQQ records were re-ingested under their stable document IDs. A live
retrieval check confirmed `0.0945%` for SPY and `0.18%` for QQQ in both the rendered source
content and `expense_ratio_pct` metadata.

## Data-quality boundary

`yfinance` is an unofficial development adapter and is not a production market-data license.
The resulting documents are snapshots, not guaranteed live quotes. The next data-quality
slice should add freshness thresholds, retries, source health reporting, and a licensed or
explicitly permitted production provider.

## Deferred to iteration 002

- Minimal Neo4j ETF entity/relationship schema.
- Graph enrichment of Chroma candidates.
- Consistency checks between graph records and source documents.
- Human-review rendering in the dashboard.
