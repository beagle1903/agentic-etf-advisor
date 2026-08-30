# Iteration 013: Measured sector graph context

- Status: Complete
- Started: 2026-08-30

## Goal

Retain the smallest rich graph expansion that demonstrates decision value: source-linked ETF
sector exposures that can support deterministic constraint checks and bounded explanation context
without changing semantic ranking.

## Deliverables

- A normalized `Sector` graph node and weighted `REPORTS_SECTOR_EXPOSURE` relationship from each
  versioned source document.
- A weighted active `HAS_SECTOR_EXPOSURE` projection from the ETF node, replaced atomically with
  every newly activated research snapshot.
- Fail-closed parsing of sector values and explicit missingness from canonical field provenance
  before Neo4j publication starts.
- Hybrid graph context that distinguishes available sector weights from `not_reported`,
  `source_error`, `provider_unsupported`, and `not_applicable` evidence.
- A version-three offline retrieval dataset with source-observed SPY, VTI, and QQQ sector weights
  and an explicit technology-exposure threshold judgment.
- Deterministic sector-context coverage and exact threshold-match metrics for semantic-only versus
  graph-enriched retrieval.
- Structured sector context in the bounded explanation input while exclusion screening remains
  explicitly deferred.

## Acceptance criteria

- Snapshot publication rejects malformed, duplicate, empty-available, or status-conflicting sector
  provenance before a graph transaction is attempted.
- Source-linked sector relationships retain weights in percentage points and old source documents
  remain attributable to their original snapshot.
- Activating a snapshot replaces stale normalized ETF-sector relationships in the same transaction
  as the active pointer.
- Hybrid retrieval returns deterministic normalized sector context and preserves Chroma ordering.
- Missing sector evidence remains explicit and cannot be interpreted as zero exposure or a pass.
- The same offline cases show no ranking delta, full graph sector-context coverage, and an exact
  structured match for the curated technology threshold.
- A wrong sector weight fails the exact-match metric and prevents the evaluator from recommending
  retention.
- Ruff, formatting, mypy, the offline test suite, packaging, and Docker Compose validation pass.

## Measured decision

Sector relationships earn retention because they raise structured sector-context coverage from
`0.0` to `1.0` and exact threshold-match rate from `0.0` to `1.0` on the same versioned candidate
set. Hit rate, recall, and mean reciprocal rank remain unchanged, so this is constraint-context
value rather than a ranking claim.

## Deferred graph expansions

- Geography remains provider-unsupported in the current Yahoo adapter and cannot earn a
  relationship yet.
- Holdings and overlap have no implemented constraint or explanation metric in this slice.
- Benchmark is already source-attributable but has no measured graph-specific consumer.
- These relationships remain in canonical source documents and may be evaluated later; they are
  not retained as graph schema merely because the data exists.

## Verification

- `uv run etf-advisor evaluate-retrieval` reports zero ranking delta, `1.0` sector-context
  coverage lift, and `1.0` exact sector-threshold-match lift.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes.
- `uv run pytest` passes offline.
- `uv build` produces source and wheel artifacts.
- `docker compose config --quiet` passes.

## PR review hardening

- `CandidateEvidence` now revalidates that nested graph context references the same source
  document ID and normalized ETF symbol before persisted, restored, or replacement-retriever
  evidence can reach an explanation provider.
- Regression tests prove that foreign sector weights cannot become numeric support for a cited
  candidate and that a replacement retriever carrying mismatched graph context fails closed.
