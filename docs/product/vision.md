# Product vision

## Goal

Build an educational US ETF portfolio decision-support system that combines current
market data, source-grounded retrieval, relationship-aware graph context, deterministic
risk controls, and explicit human review.

## Intended user experience

1. A user supplies goals, horizon, risk tolerance, constraints, and portfolio context.
2. The system identifies missing or conflicting information.
3. Retrieval supplies attributable ETF facts and relevant relationship context.
4. Deterministic calculations produce candidate allocation ranges.
5. An LLM explains evidence and trade-offs without inventing facts.
6. The user reviews and can approve, edit, or reject the draft.

## Phase-one scope

- US-listed ETFs only.
- A simple dashboard.
- Read-only market and reference data.
- Chroma for unstructured source chunks.
- Neo4j for ETF, issuer, category, holding, sector, and exposure relationships.
- Ollama Cloud or OpenRouter behind a provider interface.
- LangSmith tracing and offline evaluations when credentials are available.

## Non-goals

- Brokerage connectivity or trade execution.
- Guaranteed returns, price forecasts, or autonomous financial decisions.
- Tax, legal, or jurisdiction-specific advice.
- High-frequency or intraday trading.
- Production redistribution of Yahoo Finance data.

## Success criteria

- Every material claim can be traced to a retrieved source or deterministic calculation.
- Stale or missing market data is visible and blocks unsupported conclusions.
- The graph can pause and resume reliably at review boundaries.
- Retrieval and recommendation quality are covered by a small curated evaluation set.
- Retrieval evaluation reports semantic ranking quality and graph-context contribution
  separately, so graph expansion requires measured value rather than architectural intent.
- Every iteration produces a runnable artifact and automated tests.
