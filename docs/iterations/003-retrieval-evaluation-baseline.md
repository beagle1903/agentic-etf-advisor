# Iteration 003: Retrieval evaluation baseline

- Status: Complete
- Started: 2026-08-27

## Goal

Measure the current retrieval boundary before expanding the Neo4j schema. Add a small,
source-attributable offline evaluation set and deterministic metrics that compare
semantic-only results with the same results enriched by source-linked graph context.

## Deliverables

- A versioned offline evaluation set with curated ETF source documents, UTC observation
  timestamps, relevance judgments, and expected graph context.
- A reusable evaluator behind retrieval interfaces, with no network or clock dependency.
- Deterministic ranking, attribution, and graph-context metrics plus explicit deltas.
- An `etf-advisor evaluate-retrieval` command that prints a JSON report offline.
- Unit and CLI tests covering scoring, validation, repeatability, and missing graph context.

## Acceptance criteria

- `uv run etf-advisor evaluate-retrieval` runs without credentials, databases, or network
  access and produces the same JSON for the same versioned dataset.
- Both variants report hit rate, recall at K, mean reciprocal rank, and source-attribution
  rate from the same semantic candidate ordering.
- Graph-context recall and field accuracy are scored against explicit issuer and category
  judgments; missing or incorrect context lowers the metrics rather than passing silently.
- Every curated document retains a source URL and a timezone-aware observation timestamp.
- The report distinguishes ranking lift from context lift and does not claim that enrichment
  improves ranking while `HybridRetriever` preserves semantic order.
- Dataset validation rejects unknown document IDs, duplicate IDs, and missing provenance.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and
  `uv run pytest` pass without network access.
- No credentials, private data, trade execution, or guaranteed-return language is added.

## Deferred

- Graph-aware reranking or candidate expansion.
- Holdings, sectors, geographies, benchmarks, and overlap schema.
- LangSmith-hosted datasets and evaluator runs.
- Live Chroma/Neo4j benchmarking and statistical significance testing.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes for 41 files.
- `uv run mypy` passes for 21 source files.
- `uv run pytest` passes (21 tests) without network access.
- Repeated `uv run etf-advisor evaluate-retrieval` output is byte-for-byte stable in the
  CLI regression test.
- The packaged baseline reports semantic and graph-enriched MRR of `0.875`, for zero
  ranking delta; graph-context recall and issuer/category field accuracy improve from
  `0.0` to `1.0`.
- Missing VTI context lowers both graph metrics to `0.6`; an incorrect VTI category lowers
  field accuracy to `0.8`, proving that incomplete or wrong context does not pass silently.
- `docker compose config --quiet` passes.
- `uv build` succeeds, and the wheel contains `evaluation/retrieval_baseline.json`.
