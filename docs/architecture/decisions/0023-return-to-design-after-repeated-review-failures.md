# ADR 0023: Return repeated review failures to design

- Status: Accepted
- Date: 2026-09-15
- Supersedes: ADR 0022 only for repeated implementation-review remediation.

## Context

Independent review can expose a missed edge case that the implementation owner can repair within
an approved capsule. Repeated related findings are different: they show that the design's grammar,
state model, interface boundary, or acceptance matrix is incomplete. Continuing to alternate
example-driven patches and review creates implementation-review ping-pong, increases regression
risk, and spends verification effort without stabilizing the contract.

Issue #49 demonstrated this failure mode. Successive explanation-safety matcher fixes traded false
negatives for false positives and then introduced nearby bypasses. Escalating implementation effort
did not replace the need to revisit the design boundary.

## Decision

One routine review-remediation cycle may remain with the authorized implementation owner when the
finding fits the approved capsule. After two consecutive implementation-review cycles fail for
related reasons, the coordinator must stop implementation and review activity.

The work returns to a fresh read-only `design_architect` session. That session reassesses the
failure pattern, contract boundaries, non-goals, invariants, and a finite acceptance/rejection
matrix. The coordinator records and approves a revised `DESIGN_READY` capsule before any
write-capable role resumes. The reset may retain, replace, or discard the uncommitted approach;
that choice belongs to the revised design rather than another implementation patch.

An `implementation_specialist` remains appropriate for demonstrable execution complexity, but
specialist escalation does not waive this design reset. A reviewer still reports findings and
cannot authorize implementation or contract changes. Any one-off exception requires explicit user
approval and must be recorded in the issue and pull request.

## Consequences

- Review remains capable of catching one bounded defect without forcing unnecessary redesign.
- Related repeated failures become evidence about the design, not an invitation to patch more
  examples.
- The coordinator must distinguish related contract failures from unrelated isolated findings and
  record that judgment.
- A design reset adds a deliberate pause, but bounds review-remediation loops and reduces the risk
  of shipping a brittle consequential contract.
- Existing role registrations, model and effort settings, sandbox boundaries, JSON-state rules,
  and ADR 0018 compatibility constraints are unchanged.
