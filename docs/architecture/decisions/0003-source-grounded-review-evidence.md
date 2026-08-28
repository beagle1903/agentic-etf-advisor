# ADR 0003: Inject source-grounded evidence before human review

- Status: Accepted
- Date: 2026-08-28

## Context

The workflow now produces an illustrative policy split, while the retrieval stores contain
ranked ETF snapshots and source-linked graph context. Passing raw store results directly into
the graph would couple orchestration to Chroma and Neo4j and could allow stale or incomplete
metadata to reach human review.

## Decision

Define a `CandidateEvidenceRetriever` protocol and inject it when the workflow needs live
retrieval. The live adapter wraps the existing hybrid retriever, derives a deterministic query
from the validated profile, validates source identity and timestamps, applies the shared
freshness policy with one injected clock value, and returns a JSON-safe evidence bundle.

The workflow reaches human review only for a ready bundle. Empty results, missing provenance,
stale or future observations, and store failures end the run with visible evidence errors.
Evidence remains ranked research context; it is not an ETF recommendation, allocation, forecast,
or trade instruction. The existing no-retriever graph path remains available for offline policy
demonstration and tests.

## Consequences

- Orchestration tests can use deterministic fake retrievers without services or credentials.
- Review payloads retain source URLs, observation timestamps, source content, distances, and
  optional graph context.
- Chroma ordering remains the ranking signal and duplicate symbols keep the first result.
- Sector exclusions are carried into review but cannot be claimed as checked until the source
  contract reports sector exposure.
- Dashboard and provider work can consume the evidence bundle without owning retrieval-store
  details.
