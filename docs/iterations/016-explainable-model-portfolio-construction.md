# Iteration 016: Explainable model-portfolio construction

- Status: In progress
- Created: 2026-09-01
- Tracking issue: https://github.com/beagle1903/agentic-etf-advisor/issues/21

## Goal

Turn deterministic policy ranges and screened, source-attributable ETF candidates into an
illustrative portfolio draft that a human can inspect, edit, approve, or reject without asking a
model to make eligibility, allocation, or suitability decisions.

## Deliverables

- A JSON-serializable portfolio-construction input, policy, draft, and validation result.
- A pure deterministic construction boundary over the validated profile, policy calculation,
  ready evidence, and candidate-screening bundle.
- Explicit configurable limits for position count, minimum and maximum weights, allocation bands,
  diversification, and exclusions.
- Exact preservation of percentage and cash totals using deterministic rounding rules.
- Stable per-position reasons that identify the user constraint served and the supporting source.
- Fail-closed handling for missing, stale, contradictory, failed, or unresolved required evidence.
- Human-review and dashboard presentation of weights, cash amounts, constraints, evidence,
  uncertainty, and validation outcomes.
- Offline regression coverage for construction, validation, graph-state persistence, safety, and
  presentation behavior.

## Acceptance criteria

- Only candidates that satisfy the iteration's explicit deterministic eligibility policy may
  enter the portfolio draft; a model cannot override screening or allocation rules.
- Construction produces weights totaling exactly 100% and initial and recurring cash allocations
  that reconcile exactly to the corresponding policy totals.
- Every position satisfies the configured minimum and maximum weight, position-count,
  diversification, allocation-band, and exclusion rules.
- Every included ETF has a stable deterministic reason, source document ID, source URL, and
  observation timestamp supporting its material facts.
- Missing or stale required evidence, an unresolved required constraint, contradictory persisted
  state, or an infeasible constraint set stops before human review with a stable reason.
- The LLM remains optional and may explain only the validated portfolio, evidence, and trade-offs;
  it cannot select instruments, change weights, repair invalid output, or decide suitability.
- The dashboard presents the result as an educational illustration and never as a forecast,
  guaranteed return, personalized recommendation, trade instruction, or brokerage action.
- Graph state remains JSON-serializable and all nondeterministic calls or side effects remain behind
  explicit replaceable interfaces.
- Boundary values, infeasible inputs, rounding, missing evidence, tampered persisted state, and
  human-review presentation are covered by deterministic tests.
- Ruff, formatting, mypy, the full offline test suite, packaging, Docker Compose validation, and
  any explicitly approved manual or live verification complete successfully.

## Planned work items

- [x] Define the deterministic construction contract and policy defaults in ADR 0014 (#28).
- [x] Implement portfolio construction and validation (#29).
- [x] Present the draft and its evidence at human review (#30).
- [ ] Add allocation, safety, persistence, and presentation evaluation coverage (#31).
- [ ] Run the end-to-end acceptance verification and record durable evidence here (#32).

The GitHub tracking issue owns progress and sub-issue relationships. This file remains the
canonical execution contract and will retain the final acceptance and verification evidence.

## Accepted construction contract

ADR 0014 defines the implementation boundary for #29. Construction is a pure deterministic stage
over five validated inputs:

1. `InvestorProfile`;
2. `PolicyCalculation`;
3. a ready `CandidateEvidenceBundle`;
4. a `CandidateScreeningBundle` that exactly matches recomputation from that evidence; and
5. the checkpointed `PortfolioConstructionPolicy`.

The stage runs after screening and before optional explanation generation. Its input model is
JSON-serializable, but the graph does not duplicate those four existing upstream payloads inside
the construction result. The new top-level `portfolio_construction` state contains the policy,
optional draft, validation result, excluded-candidate audit records, and stable errors. A new run
clears it together with downstream explanation and review state.

### Policy defaults

| Field | Default | Deterministic meaning |
| --- | ---: | --- |
| `max_candidate_pool_size` | 10 | A larger pool is blocked before subset enumeration. |
| `min_positions` | 3 | A smaller subset is infeasible. |
| `max_positions` | 5 | No more than five ETFs enter the draft. |
| `min_position_weight_bps` | 500 | Every position is at least 5.00%. |
| `max_position_weight_bps` | 8,000 | Every position is at most 80.00%. |
| `max_category_weight_bps` | 8,000 | One normalized source category is at most 80.00%. |
| `weight_precision_bps` | 1 | Weights use integer 0.01% units and total 10,000. |

The closed initial category-to-sleeve map is:

```text
growth    <- Large Blend, Large Growth, Foreign Large Blend,
             Diversified Emerging Mkts
defensive <- Intermediate Core Bond
```

Comparison trims and collapses whitespace and is case-insensitive. It remains exact after that
normalization. The implementation must not infer a sleeve from the ticker, free text, a substring,
fund-family/provider data, or model output. A category-map extension is an explicit reviewed policy
change.

### Eligibility and fail-closed outcomes

The implementation must distinguish candidate-local exclusion from a globally invalid contract:

| Input condition | Required outcome |
| --- | --- |
| Screening verdict `pass` and attributable supported category | Candidate may enter feasibility search. |
| Screening verdict `fail` | Exclude with the existing failing screening reasons. |
| Screening verdict `unknown` | Exclude with the existing unresolved screening reasons. |
| Category missing or unsupported, with otherwise consistent provenance | Exclude the candidate; block only if no feasible subset remains. |
| Category value conflicts with canonical provenance | Block construction as contradictory evidence. |
| Evidence missing, blocked, stale, future-dated, or identity-mismatched | Block construction before subset search. |
| Persisted screening differs from deterministic recomputation | Block construction before subset search. |
| No subset satisfies sleeve, count, weight, and category rules | Block with the stable reason code reached by the ordered feasibility checks. |
| Persisted construction differs from deterministic recomputation | Block presentation and expose no review controls. |

Candidate-local exclusions remain in an audit list and never receive a weight. The complete stage
uses stable codes including `candidate_screening_failed`, `candidate_screening_unknown`,
`category_missing`, `category_unsupported`, `category_provenance_conflict`,
`upstream_contract_mismatch`, `evidence_not_ready`, `screening_recomputation_mismatch`,
`missing_sleeve_coverage`, `insufficient_eligible_candidates`,
`position_constraints_infeasible`, `category_limit_infeasible`,
`allocation_band_mismatch`, `allocation_precision_unsupported`, `weight_reconciliation_failed`,
`cash_reconciliation_failed`, and `persisted_construction_mismatch`.
The bounded implementation also emits `candidate_pool_limit_exceeded` before search when the
checkpointed pool limit is exceeded.

### Selection and allocation algorithm

1. Revalidate and cross-check every upstream payload, confirm the exact target remains inside its
   checkpointed allocation bands, and recompute screening.
2. Retain only passing candidates with supported, source-consistent category evidence.
3. If fewer than `policy.min_positions` candidates remain, block with
   `insufficient_eligible_candidates` before assigning weights.
4. Generate subsets in upstream retrieval order whose size is within the inclusive
   `policy.min_positions` and `policy.max_positions` bounds and that cover every non-zero policy
   sleeve.
5. For each subset, divide the exact growth and defensive target basis points equally within its
   sleeve. Use integer quotient and remainder; award remaining basis points in upstream order.
6. Reject subsets whose positions or normalized category totals exceed any boundary.
7. Choose the feasible subset with the greatest position count. Break a remaining tie by the
   lexicographically earliest tuple of upstream indexes and retain that order in the draft.
8. Reconcile initial and recurring cash separately, sleeve by sleeve, from the cent-rounded policy
   totals. Use proportional integer cents with largest remainders awarded in draft order.
9. Run the full validator over the independently constructed output before returning `ready`.

This is a reproducible tie-breaker over upstream research order, not performance optimization or an
ETF ranking. A target percentage that cannot be represented exactly in integer basis points is
blocked rather than silently rounded.

### Output and validation contract

Each `PortfolioPosition` must retain:

- document ID, symbol, name, source, source URL, and UTC observation timestamp;
- `growth` or `defensive` sleeve and normalized source category;
- integer weight basis points and initial/recurring integer USD cents;
- `supports_growth_target` or `supports_defensive_target`;
- the exact policy target reference served; and
- the candidate's stable screening reason codes.

The independent validation result reports stable pass/fail checks for upstream consistency,
allocation-band consistency, eligibility, sleeve coverage, position count, position weights,
category concentration, weight total, sleeve totals, initial cash, recurring cash, and source
attribution. `ready` requires every check to pass. UI percentages and currency strings are derived
display values and never inputs to validation.

### Deterministic examples for implementation

These examples are acceptance fixtures for #29; ties refer to the shown upstream order.

**Balanced moderate profile**

- Policy target: growth 5,750 basis points, defensive 4,250 basis points.
- Passing candidates: SPY/Large Blend, VTI/Large Blend, QQQ/Large Growth,
  VEA/Foreign Large Blend, BND/Intermediate Core Bond.
- Expected weights: SPY 1,438; VTI 1,438; QQQ 1,437; VEA 1,437; BND 4,250 basis
  points.
- For initial USD 1,000.00, expected cents are 14,380; 14,380; 14,370; 14,370;
  and 42,500.
- For recurring USD 250.00, the policy sleeve totals are growth 14,375 cents and defensive
  10,625 cents. Expected position cents are 3,595; 3,595; 3,593; 3,592; and 10,625.

**Conservative boundary profile**

- Policy target: growth 2,000 basis points and defensive 8,000 basis points.
- With the same five candidates, expected weights are 500 basis points for each growth ETF and
  8,000 for BND.
- The 5.00% minimum position, 80.00% maximum position, and 80.00% category maximum all pass exactly
  at their configured boundaries.

**Infeasible aggressive profile**

- Policy target: growth 9,500 basis points and defensive 500 basis points.
- Passing classified candidates: QQQ/Large Growth and BND/Intermediate Core Bond only.
- Expected result: `blocked` with `insufficient_eligible_candidates` because two candidates are
  below the default `min_positions` value of three. The algorithm assigns no weights, produces no
  draft, and permits no review interrupt.

The model has no role in any example. The #29 implementation loads these values in focused tests
and asserts stable JSON-mode results across repeated calls and checkpointed graph state.

## Verification

The #29 implementation is covered by deterministic unit and workflow tests for the accepted
balanced, conservative-boundary, and infeasible-aggressive examples; configurable limits;
category and screening exclusions; provenance and screening tampering; basis-point and cent
reconciliation; category-field freshness; bounded candidate-pool search; persisted-bundle
recomputation; JSON serialization; state clearing; and fail-closed routing before explanation or
human review. Repository-wide gate results are recorded in the pull request for the tested head.

- `uv run pytest -o addopts=` passes 237 tests; two optional Streamlit tests are skipped.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` reports all 102 files formatted.
- `uv run mypy` passes in strict mode across 41 source files.
- `uv build` produces the source and wheel artifacts.
- `docker compose config --quiet` passes.
- `git diff --check` passes.

The #30 presentation slice adds the ready construction bundle to the human-review interrupt and
recomputes it from the complete upstream state before the dashboard can render or resume. The UI
shows exact position, sleeve, weight, initial-cash, recurring-cash, policy-band, construction-rule,
validation, exclusion, reason, and source-attribution details while retaining explicit educational,
non-advisory language. Missing, malformed, blocked, or deterministically mismatched construction
produces a controlled failure without review controls. Focused tests cover presentation-contract
recomputation and tampering, portfolio rendering, blocked-state rendering, workflow payloads, and
the existing approve, edit, reject, restore, and malformed-payload paths.

Portfolio-aware explanation changes, broader evaluation coverage, and the end-to-end Iteration 016
acceptance record remain assigned to #31 and #32.

## Open design decisions

The initial deterministic heuristic, position-count and weight defaults, category-diversification
limit, category-to-sleeve mapping, and reconciliation rules are resolved by ADR 0014. Future
optimization objectives, additional asset classes, issuer or holdings-overlap controls, tax-aware
allocation, and category-map expansion remain out of scope until supported by explicit evidence
and a reviewed contract change.
