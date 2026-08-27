# Agentic ETF Advisor

An educational, source-grounded US ETF portfolio decision-support project built with
LangGraph. The project is designed as a sequence of small, testable vertical slices.

The first slice validates an investor profile, drafts a deterministic policy range,
pauses for human review, and only then finalizes the result. Live ETF retrieval, model
providers, GraphRAG, and the dashboard are intentionally introduced in later slices.

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

The current delivery contract is in `docs/iterations/002-neo4j-graph-retrieval.md`.

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
