# ADR 0014: Construct model portfolios with deterministic sleeve allocation

- Status: Accepted
- Date: 2026-09-01

## Context

The workflow now produces an illustrative growth/defensive policy target, freshness-checked ETF
evidence, and source-attributable candidate-screening results. Those contracts can support an
illustrative ETF portfolio, but they do not yet define which eligible candidates enter it, how
weights and cash are reconciled, or how an infeasible constraint set stops before human review.

Asking a model to fill those gaps would make eligibility and allocation nondeterministic. Treating
retrieval order as a model ranking would also overstate what the current Chroma ordering proves.
The source contract reports a fund category, but Yahoo's `fundFamily` value is provider context and
must not be presented as a legal issuer or used as an issuer-concentration control.

## Decision

Add a pure portfolio-construction boundary after candidate screening and before optional
explanation generation. Its input revalidates the investor profile, policy calculation, ready
evidence bundle, recomputed screening bundle, and checkpointed construction policy. It performs no
network, clock, database, provider, model, or external-write operation.

Only a candidate whose complete screening verdict is `pass` can enter a draft. A `fail` or
`unknown` candidate remains auditable but is excluded. Missing or unsupported category evidence
excludes that candidate; contradictory category provenance, stale evidence, cross-contract identity
mismatches, or a screening result that differs from recomputation block the entire construction.
Candidate-local exclusions may still yield a draft when the remaining evidence satisfies every
constraint.

Classify eligible candidates into `growth` or `defensive` sleeves through a closed, configurable,
exact category map. Category evidence must be canonically `available`, and its flattened and
provenance values must agree. Normalize categories by trimming, collapsing internal whitespace,
and applying case-insensitive comparison; do not use substring guesses, symbol-based rules, source
prose, or a model. The initial reviewed mapping is:

- growth: `Large Blend`, `Large Growth`, `Foreign Large Blend`, and
  `Diversified Emerging Mkts`;
- defensive: `Intermediate Core Bond`.

An extension to this map is a reviewed policy change. The category value must agree with canonical
field provenance and retains its document ID, source URL, and observation timestamp in every
included position.

Use these illustrative defaults:

| Rule | Default |
| --- | ---: |
| Minimum positions | 3 |
| Maximum positions | 5 |
| Minimum position weight | 5.00% (500 basis points) |
| Maximum position weight | 80.00% (8,000 basis points) |
| Maximum weight in one source-reported category | 80.00% (8,000 basis points) |
| Weight precision | 0.01% (1 basis point) |

These are transparent research-policy controls, not universal suitability thresholds. The
80-percent default intentionally permits the current one-bond research universe to represent the
conservative policy boundary while still requiring at least three positions and limiting any one
category. Category concentration is not described as issuer, security, or economic-risk
diversification.

Build candidate subsets from the upstream retrieval order. A feasible subset must satisfy the
position-count range, contain at least one candidate for every non-zero policy sleeve, and pass all
weight and category limits. Choose the feasible subset with the greatest position count; when more
than one remains, choose the lexicographically earliest tuple of upstream candidate indexes. Keep
that upstream order in the draft. This rule is deterministic tie-breaking, not a claim of expected
performance or model ranking.

Represent weights as integer basis points. Construction does not choose a new point inside the
allocation bands: it revalidates that the existing policy target remains inside its checkpointed
bands, then uses that exact target. The growth and defensive sleeve totals must equal the target
and must themselves total 10,000 basis points. Reject a target that is not exactly representable at
one-basis-point precision. Within each sleeve, divide its basis points equally using integer
quotient and remainder; assign remaining basis points one at a time in upstream order. A subset is
infeasible if the resulting positions or category totals violate a configured boundary.

Represent money as integer USD cents inside the construction calculation. Reconcile initial and
recurring cash independently and within each sleeve so their sleeve totals exactly equal the
already cent-rounded `PolicyCalculation` values. Allocate cents proportionally to position basis
points using the largest-remainder method; ties follow draft order. A non-zero weight may have a
zero-cent allocation when the input cash amount is too small, and a zero total produces zero cents
for every position. Display-only floats or formatted currency never participate in validation.

Every ready position carries its sleeve, normalized source category, weight basis points, initial
and recurring cents, the stable reason `supports_growth_target` or
`supports_defensive_target`, the served policy reference, screening reason codes, document ID,
symbol, source name, source URL, and UTC observation timestamp. The output also retains excluded
candidate reasons without treating them as positions.

Return one JSON-serializable construction bundle with `ready` or `blocked` status, the construction
policy, optional draft, validation checks, and stable errors. The stable exclusion and blocking
reason taxonomy covers:

- invalid or contradictory upstream contracts;
- evidence that is missing, stale, future-dated, or not ready;
- screening mismatch or no passing candidates;
- missing, contradictory, or unsupported category evidence;
- missing sleeve coverage or insufficient eligible candidates;
- infeasible position count, position weight, or category concentration;
- allocation-band mismatch, unsupported allocation precision, or failed weight/cash
  reconciliation; and
- a persisted construction bundle that differs from deterministic recomputation.

The graph checkpoints only JSON-mode model dumps. Each new profile run clears construction state.
The dashboard revalidates the complete upstream contracts and recomputes construction from the
checkpointed policy before rendering a draft, following the existing screening-presentation
boundary. An optional explanation generator may describe only the validated draft, evidence, and
trade-offs; it cannot select candidates, change weights, repair a blocked result, or decide
suitability.

## Consequences

- The same validated inputs and construction policy always produce the same portfolio or the same
  stable blocker without services, credentials, a model, or a wall clock.
- Weight, sleeve, and cash totals are exactly reproducible across checkpoint save and restore.
- A failed or unknown candidate cannot become eligible through allocation, explanation, or UI
  code.
- The initial category map is deliberately narrow. A passing ETF with an unsupported category is
  excluded and can make the constraint set infeasible rather than being guessed into a sleeve.
- The current universe can exercise both sleeves, but the contract does not claim broad portfolio
  coverage, optimized diversification, suitability, forecasts, or trade readiness.
- Future optimization objectives, additional asset classes, issuer controls, overlap limits, or
  licensed data require separately evidenced contract changes rather than silent heuristic drift.
