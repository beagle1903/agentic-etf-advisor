# Agentic ETF Advisor

An educational, source-grounded US ETF portfolio decision-support project built with
LangGraph. The project is designed as a sequence of small, testable vertical slices.

The implemented slices validate an investor profile with human review, ingest attributable
ETF snapshots, join Chroma-ranked documents to source-linked Neo4j context, and compare the
semantic-only and graph-enriched paths on a deterministic offline evaluation set.

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
approval so the complete lifecycle is visible from the terminal.

Install the Iteration 001 data and retrieval integrations:

```powershell
uv sync --extra rag
uv run etf-advisor ingest --symbols SPY,QQQ,VTI,BND
uv run etf-advisor search "broad US equity exposure"
```

The first Chroma ingestion may download its local default embedding model. The ingestion
command prints source IDs, observation timestamps, and Yahoo Finance URLs so retrieved
context remains attributable.

Index the same source documents into the minimal Neo4j relationship graph and join graph
context back to Chroma-ranked results:

```powershell
uv run etf-advisor ingest --symbols SPY,QQQ,VTI,BND --with-graph
uv run etf-advisor hybrid-search "broad US equity exposure"
```

The graph stores ETF, issuer, category, and source-document nodes. Stable source document
IDs form the join boundary, and a missing graph record is returned as `graph_context: null`
instead of silently fabricating context.

Run the retrieval baseline without credentials, databases, or network access:

```powershell
uv run etf-advisor evaluate-retrieval
```

The JSON report separates ranking metrics from issuer/category context metrics. The initial
dataset demonstrates context lift but no ranking lift because graph enrichment intentionally
preserves semantic ordering; it is not evidence to expand the graph schema yet.

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

The current delivery contract is in `docs/iterations/003-retrieval-evaluation-baseline.md`.

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
