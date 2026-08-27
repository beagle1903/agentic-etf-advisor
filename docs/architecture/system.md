# System architecture

## Current shape

The system is a LangGraph workflow with explicit boundaries between orchestration,
deterministic finance logic, retrieval, model providers, and presentation.

```text
Dashboard / API
      |
      v
LangGraph workflow ----> durable checkpoints (PostgreSQL)
      |
      +----> market-data adapter (Yahoo/yfinance for development)
      |
      +----> Chroma: source chunks and semantic retrieval
      |
      +----> Neo4j: ETF/entity relationships and graph enrichment
      |
      +----> provider adapter: Ollama Cloud or OpenRouter
      |
      +----> LangSmith: traces, datasets, and evaluations
      |
      v
Human review interrupt -> final explanation
```

## Retrieval responsibilities

- Chroma stores chunked, attributable unstructured material such as ETF descriptions,
  methodology documents, and research notes.
- Neo4j stores normalized entities and relationships. Graph records reference source IDs
  rather than silently duplicating the source of truth.
- Hybrid retrieval merges semantic candidates with graph neighborhoods, then reranks and
  applies freshness and source-quality checks.

The first implemented Neo4j projection uses `ETF`, `Issuer`, `Category`, and
`SourceDocument` nodes. ETF relationships provide the reusable entity graph, while each
source document also links directly to the issuer and category it reported. Hybrid search
therefore joins on the stable source document ID and cannot silently apply a relationship
observed by a different snapshot. Chroma distance remains the ordering signal until a later
evaluation demonstrates useful graph-aware reranking.

## Workflow stages

1. Validate the investor profile.
2. Clarify missing or contradictory constraints.
3. Fetch and validate timestamped market/reference data.
4. Retrieve unstructured and graph context.
5. Calculate deterministic portfolio constraints and candidate ranges.
6. Draft a source-grounded explanation.
7. Run rule-based and evaluation guardrails.
8. Pause for human review.
9. Finalize, revise, or reject.

## State and side effects

Graph state must remain JSON-serializable. Network calls, clock reads, model calls, and
database writes are wrapped as explicit tasks or adapters so replay after an interrupt is
predictable. Development tests use an in-memory checkpointer; multi-user environments use
PostgreSQL-backed checkpoints.

## Data-source boundary

`yfinance` is suitable for research and personal development, but it is unofficial and its
own documentation says Yahoo data is intended for personal use. Before any public hosted
product, replace or license the market-data source and review redistribution terms.
