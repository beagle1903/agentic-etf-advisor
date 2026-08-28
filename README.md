# Agentic ETF Advisor

An educational, source-grounded US ETF portfolio decision-support project built with
LangGraph. The project is designed as a sequence of small, testable vertical slices.

The implemented slices validate an investor profile with human review, calculate an
illustrative policy split, health-check and ingest attributable ETF snapshots, join
Chroma-ranked documents to source-linked Neo4j context, compare the semantic-only and
graph-enriched paths on a deterministic offline evaluation set, and optionally attach a
freshness-checked source-evidence bundle to the review interrupt.

> [!IMPORTANT]
> This project is educational software, not personalized financial, tax, or legal advice.
> It does not execute trades. Market data can be incomplete, delayed, or incorrect.

## Quick start

Requirements: Python 3.12 or 3.13, `uv`, Git, and optionally Docker Desktop.

```powershell
Copy-Item .env.example .env
uv sync
uv run pytest
uv run etf-advisor demo
```

The demo pauses at a LangGraph human-review interrupt and then resumes with an automatic
approval so the complete lifecycle and the review-ready policy calculation are visible from
the terminal.

The policy draft selects a target percentage inside the configured risk band according to
the stated objective and shows cent-rounded arithmetic splits for the initial and recurring
USD amounts. It remains an illustrative policy calculation: it does not select ETFs,
forecast returns or drawdowns, execute trades, or guarantee results.

Install the Iteration 001 data and retrieval integrations:

```powershell
uv sync --extra rag
uv run etf-advisor data-health --symbols SPY,QQQ,VTI,BND
uv run etf-advisor ingest --symbols SPY,QQQ,VTI,BND
uv run etf-advisor search "broad US equity exposure"
```

The read-only health command reports source URLs, observation timestamps, ages, and
freshness classifications. Ingestion rejects stale or future-dated observations before
opening Chroma or Neo4j. Yahoo requests use configurable bounded retries.

The first Chroma ingestion may download its local default embedding model. The ingestion
command prints source IDs, observation timestamps, and Yahoo Finance URLs so retrieved
context remains attributable.

Index the same source documents into the minimal Neo4j relationship graph and join graph
context back to Chroma-ranked results:

```powershell
uv run etf-advisor ingest --symbols SPY,QQQ,VTI,BND --with-graph
uv run etf-advisor hybrid-search "broad US equity exposure"
```

The graph stores ETF, fund-family/provider, category, and source-document nodes. Stable
source document IDs form the join boundary, and a missing graph record is returned as
`graph_context: null` instead of silently fabricating context. Yahoo fund-family metadata is
not presented as a legal issuer.

Run the local workflow with retrieved evidence attached to human review after indexing the
same source bundle:

```powershell
uv run etf-advisor demo --with-evidence --candidate-limit 5
```

The workflow builds a deterministic query from the profile, preserves Chroma's ranking,
validates HTTP(S) source URLs and UTC observation timestamps, recomputes freshness, and
requires source-reported ETF and US-market metadata before review. Missing, malformed,
non-ETF, non-US, stale, or future-dated evidence stops the workflow before the interrupt. The
evidence bundle is research context only; it does not select ETFs, allocate money, or execute
trades.

Run the retrieval baseline without credentials, databases, or network access:

```powershell
uv run etf-advisor evaluate-retrieval
```

The JSON report separates ranking metrics from fund-family/category context metrics. The
initial dataset demonstrates context lift but no ranking lift because graph enrichment
intentionally preserves semantic ordering; it is not evidence to expand the graph schema
yet.

Start the local data services:

```powershell
docker compose up -d chroma neo4j postgres
docker compose ps
```

Chroma is available at `http://localhost:8000`, Neo4j Browser at
`http://localhost:7474` (Bolt at `neo4j://localhost:17687`), and PostgreSQL at
`localhost:5432`. Ports are bound to the local machine only. The Neo4j host port is
remapped because this Windows machine reserves the standard `7687` port.

`yfinance` is used only as a development/research adapter in this phase. Its documentation
states that it is unofficial and intended for personal use, so it is not a production data
licensing decision.

## Repository guide

- `wishlist.md`: raw, user-owned ideas and requests.
- `AGENTS.md`: operating rules for coding agents.
- `docs/product/`: stable product intent and scope.
- `docs/architecture/`: current architecture and immutable decisions.
- `docs/iterations/`: short delivery plans and acceptance criteria.
- `docs/runbooks/`: reproducible operational procedures.
- `src/etf_advisor/`: application code.
- `tests/`: executable behavior and safety checks.

The current delivery contract is in `docs/iterations/007-source-grounded-evidence.md`.

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
