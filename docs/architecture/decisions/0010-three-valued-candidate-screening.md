# ADR 0010: Use three-valued, source-attributable candidate screening

- Status: Accepted
- Date: 2026-08-31

## Context

The active research snapshot now carries fees, average daily volume, top-ten concentration,
listing and instrument classifications, field-level provenance, and measured sector context.
Those facts are sufficient for deterministic comparison rules, but they are not sufficient to
justify an unexplained ETF ranking or a personalized suitability decision. Missing data and
unsupported exclusion terms also cannot safely become implicit passes.

## Decision

Run a pure candidate-screening stage after freshness-checked retrieval and before explanation or
human review. Every candidate receives the same stable rule sequence for US listing, ETF type,
freshness, expense ratio, average daily volume, top-ten concentration, and requested sector
exclusions. Each rule and candidate resolves to `pass`, `fail`, or `unknown`; a failure takes
precedence over unknown, and unknown takes precedence over pass.

Use explicit, configurable research-policy defaults of a maximum 1.0% expense ratio, minimum
100,000-share average daily volume, maximum 60.0% top-ten concentration, and zero tolerance above
reported weight for a requested sector. These are transparent illustrative filters, not universal
suitability thresholds, forecasts, or personalized advice. Preserve them in the checkpointed
screening result so later reviews remain reproducible.

Read scalar rule values from canonical field provenance and require their flattened metadata
status and value to agree. Require source-linked graph sector weights to agree exactly with the
canonical sector field before applying exclusions. Use a closed provider-sector taxonomy with
documented common aliases; an exclusion outside that taxonomy is `unknown`, not a pass.

Preserve retrieval order and emit stable reason codes plus exact source URLs and observation
timestamps. Do not ask a model to apply rules or rank candidates. Recompute the complete screening
bundle from evidence at the dashboard presentation boundary so a forged or stale checkpoint
cannot change a rule result silently.

## Consequences

- Missing, unsupported, or unavailable evidence stays visible as `unknown`.
- Boundary values are deterministic and independently testable.
- A candidate can fail one rule while retaining the pass or unknown evidence for every other rule.
- The comparison table is auditable but is not yet a portfolio construction or recommendation.
- Changing a default threshold changes an accepted decision boundary and must be reviewed as a
  policy change.
