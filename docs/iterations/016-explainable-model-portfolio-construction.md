# Iteration 016: Explainable model-portfolio construction

- Status: Planned
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

- Define the deterministic construction contract and policy defaults.
- Implement portfolio construction and validation.
- Present the draft and its evidence at human review.
- Add allocation, safety, persistence, and presentation evaluation coverage.
- Run the end-to-end acceptance verification and record durable evidence here.

The GitHub tracking issue owns progress and sub-issue relationships. This file remains the
canonical execution contract and will retain the final acceptance and verification evidence.

## Verification

Pending implementation. Record durable results here with the tested commit, commands, redacted
environment details for any external verification, acceptance outcome, and remaining limitations.

## Open design decisions

The contract work item must resolve the deterministic construction heuristic and default
position-count, position-weight, allocation-band, and diversification limits before implementation.
Any consequential architectural choice requires an ADR rather than an undocumented issue comment.
