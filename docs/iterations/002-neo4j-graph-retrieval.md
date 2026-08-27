# Iteration 002: Source-linked Neo4j retrieval

- Status: Complete
- Started: 2026-08-27

## Goal

Add the smallest useful graph path: index ETF, issuer, category, and source-document
relationships in Neo4j, then attach that context to Chroma-ranked sources through stable
source IDs.

## Deliverables

- Minimal Neo4j constraints and idempotent relationship upserts.
- Shared source IDs and post-write consistency checks across Chroma and Neo4j.
- Graph enrichment that preserves Chroma ranking and exposes missing context explicitly.
- `etf-advisor ingest --with-graph` and `etf-advisor hybrid-search` commands.
- Offline tests using fake Chroma and Neo4j clients.

## Acceptance criteria

- `uv run pytest` passes without network access.
- Repeated graph ingestion does not duplicate ETF, issuer, category, or source nodes.
- Every graph source node retains its source URL and observation timestamp.
- Hybrid search returns Chroma document IDs, distances, provenance metadata, and linked
  ETF relationship context.
- A Chroma result without a matching graph record has `graph_context: null`.
- Ingestion fails rather than claiming success when either store cannot find an expected
  source document ID after its upsert.
- No credentials or private market data are committed or logged.

## Deferred

- Holdings, sectors, geographies, benchmarks, and overlap calculations.
- Graph-aware reranking and measured graph retrieval lift.
- LLM-generated portfolio explanations and provider adapters.
- Dashboard rendering of source evidence and human review.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes for 18 source files.
- `uv run pytest` passes (13 tests) without network access.
- `docker compose config --quiet` passes; Chroma, Neo4j, and PostgreSQL are healthy.
- Live `ingest --symbols SPY,QQQ --with-graph` verified both source IDs in both stores.
- Repeating the same ingestion retained 2 ETFs, 2 source documents, 2 issuers, and 2
  categories for SPY and QQQ.
- Live `hybrid-search "broad US equity exposure" --limit 2` returned both Chroma-ranked
  documents with URLs, UTC observation timestamps, distances, and source-specific Neo4j
  issuer/category context.
