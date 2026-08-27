# Iteration 006: Deterministic policy calculation

- Status: Complete
- Started: 2026-08-27

## Goal

Turn the existing risk-band policy draft into a deterministic, review-ready calculation
that uses the stated objective to choose an illustrative target split and shows how the
user's initial and recurring USD amounts would divide arithmetically.

This is the highest-value next slice because it implements the workflow's deterministic
calculation stage without adding an LLM, a provider credential, a live-store dependency, or
an unmeasured graph expansion. It keeps the existing human-review boundary in place.

## Deliverables

- A pure `calculate_policy` domain function with validated, JSON-safe output.
- Objective-sensitive target percentages selected inside the existing risk-tolerance bands.
- Cent-rounded initial-investment and recurring-monthly splits whose components preserve
  their respective totals.
- Profile validation that rejects non-finite or excessively large cash amounts before
  decimal quantization.
- The existing graph `draft_policy` node wired to the calculation without adding a new
  top-level state field.
- Offline regression tests for all risk/objective combinations, cash-flow rounding, zero
  amounts, safety notes, and workflow serialization.

## Acceptance criteria

- Income selects the lower growth bound, growth selects the upper bound, and balanced
  selects the midpoint for every supported risk tolerance.
- Growth and defensive targets total 100% and remain inside their configured bands.
- Initial and recurring USD splits are rounded to cents and sum to the displayed total,
  including when an amount is zero.
- Cash-flow inputs must be finite and no greater than one trillion USD; unsupported values
  stop at profile validation instead of aborting the policy node.
- The paused human-review state contains only JSON-serializable calculation values and
  still supports the existing approve/reject lifecycle.
- The calculation has no network, database, model-provider, wall-clock, or external-write
  dependency.
- The output explicitly remains an illustrative policy calculation: it does not select
  ETFs, forecast returns or drawdowns, execute trades, or imply guaranteed results.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and `uv run pytest`
  pass without network access.

## Deferred

- Source-grounded ETF candidate selection and live evidence in the workflow.
- LLM/provider adapters and generated explanations.
- Dashboard rendering of the review interrupt.
- Graph-schema expansion, graph-aware reranking, and overlap calculations until evaluation
  demonstrates measured value.

## Review correction

PR review found that unbounded nonnegative floats allowed `1e26` and positive infinity to
reach `Decimal.quantize()`, which raised `decimal.InvalidOperation` inside the policy node.
Both cash-flow fields now require finite values from zero through one trillion USD. This cap
keeps cent quantization inside the default decimal precision while leaving ample headroom
for the educational workflow. Regression tests cover non-finite values, the reported large
value, the maximum accepted boundary, and workflow fail-closed behavior.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes for 24 source files.
- `uv run pytest` passes offline (60 tests).
- `uv run etf-advisor demo` shows the calculated target and cent-rounded cash-flow splits,
  pauses at human review, and resumes after approval.
- `uv run etf-advisor evaluate-retrieval` remains deterministic with zero ranking delta and
  unchanged graph-context lift.
- `docker compose config --quiet` passes.
- `uv build` produces the source distribution and wheel.
