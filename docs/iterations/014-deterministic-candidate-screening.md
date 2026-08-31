# Iteration 014: Deterministic candidate screening

- Status: Complete
- Started: 2026-08-31
- Completed: 2026-08-31

## Goal

Turn retrieved ETF research into an auditable eligibility and comparison stage without delegating
financial rules, missing-data interpretation, or candidate ranking to a model.

## Deliverables

- A pure, configurable screening policy for fees, liquidity, concentration, and sector-exposure
  tolerance.
- Stable per-rule and per-candidate `pass`, `fail`, and `unknown` results with reason codes.
- Exact field-level citations for every evidence-backed judgment.
- Revalidation of scalar metadata against canonical field provenance and graph sector weights
  against their source field.
- A checkpointed screening bundle between evidence retrieval and optional explanation generation.
- A fail-closed dashboard contract that recomputes screening before rendering.
- A human-review comparison table with rule details and source links.

## Acceptance criteria

- Source-reported US listing, ETF type, and freshness are retained as explicit deterministic
  checks rather than assumed by the comparison UI.
- Expense ratio values at or below 1.0% pass; average daily volume at or above 100,000 shares
  passes; top-ten concentration at or below 60.0% passes.
- Values on every boundary are covered by tests, and configurable policy values can change those
  judgments without changing retrieval order.
- Requested supported-sector exposure above the configured tolerance fails; missing sector
  evidence and unsupported exclusion terms are unknown rather than passes.
- A supported-sector failure takes precedence when another requested exclusion is unsupported;
  unsupported terms remain explicitly unresolved in the same rule result.
- Missing fee, liquidity, or concentration evidence is unknown with an attributable missing
  reason.
- Conflicting canonical provenance, flattened metadata, graph context, or persisted screening
  blocks the workflow before explanation and human review.
- Screening output remains JSON-serializable and preserves candidate order, source URL,
  observation timestamp, stable reason code, observed value, and threshold.
- The dashboard labels thresholds as illustrative research filters and does not present screening
  as suitability, ranking, forecast, recommendation, or trade instruction.
- Ruff, formatting, mypy, the offline test suite, packaging, and Docker Compose validation pass.

## Verification

- `uv run pytest` passes all 206 offline tests.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes in strict mode.
- `uv build` produces the source and wheel artifacts.
- `docker compose config --quiet` passes.
- `git diff --check` passes.
