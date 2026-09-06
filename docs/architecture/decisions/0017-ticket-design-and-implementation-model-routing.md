# ADR 0017: Separate ticket design and implementation model roles

- Status: Accepted
- Date: 2026-09-06

## Context

Design decisions and implementation work have different reasoning needs. Allowing one
unspecified agent to perform both phases makes the boundary difficult to review and can spend
high-effort reasoning on routine code changes. The repository also needs a repeatable handoff
that survives a task or session boundary.

## Decision

Every issue-backed work item follows two sequential phases:

1. `design_architect` performs read-only repository and issue analysis with `gpt-6-astra` at
   `high` reasoning effort.
2. After a recorded `DESIGN_READY` handoff, `implementation_worker` performs the approved
   implementation with `gpt-6-astra` at `medium` reasoning effort.

The design handoff records scope, non-goals, invariants, affected interfaces, state and
serialization implications, acceptance criteria, focused tests, documentation needs, and
unresolved risks. It is stored in the issue, canonical iteration document, or a dedicated
design document under `docs/iterations/`.

Project-scoped Codex agent files pin both model and reasoning effort. Unspecified subagents
default to Astra at medium effort, and the project limits concurrent subagent threads to two to
avoid unnecessary token use. Architectural ambiguity returns to the design role; the
implementation role does not silently redesign the contract.

## Consequences

- Every implementation has a reviewable design checkpoint and explicit acceptance contract.
- High-effort reasoning is reserved for design and targeted architectural escalation.
- Medium-effort implementation remains capable of tool use, coding, testing, and verification.
- Separate agent sessions make model and effort selection visible and repeatable.
- CI can validate the pinned role configuration and required handoff markers, but provenance of
  an individual manually selected task still depends on using the configured agents and recording
  the roles in the pull request.
- This process adds a short design gate to small tickets; an explicit one-off exception must be
  recorded in the issue and pull request.
