# ADR 0022: Quota-efficient Codex workflow

- Status: Accepted
- Date: 2026-09-14
- Supersedes: ADR 0020 only for mandatory routine phase separation and task-by-task routing.
- Preserves: ADR 0018 compatibility constraints, all six role registrations, pinned role
  settings, read-only boundaries, and consequential design approval.

## Context

Applying separate planning, implementation, test, and review sessions to every issue repeatedly
pays repository-orientation and handoff costs. That overhead can prevent an otherwise routine issue
from closing within the shared Codex quota without materially improving its risk controls.

The approved [quota-efficient workflow design](../../iterations/017-quota-efficient-codex-workflow-design.md)
classifies work by potential impact. It retains independent design and review where mistakes are
costly while allowing one authorized owner to finish routine work coherently.

## Decision

Every issue records a complete `DESIGN_READY` capsule before implementation edits. The capsule
contains classification, owner role/model/effort, rationale, authorization, scope, non-goals,
invariants, affected interfaces, JSON/state impact, acceptance criteria, focused verification,
documentation needs, risks, and escalation triggers.

Mechanical, low-risk, architecture-determined work belongs to `bounded_worker`. Ordinary features
and bugs within established contracts belong to `implementation_worker`. In one authorized
session, either owner may author and record the capsule, implement its scope, add focused tests,
self-review, run verification, and document limitations. A planning or independent-review session
is not a routine prerequisite.

Consequential financial eligibility, safety, authentication, persistence/replay, security, or
architecture contracts require a separate read-only `design_architect` handoff and coordinator
approval before a write-capable role starts. Review findings cannot authorize implementation or
contract changes. Missing, incomplete, unapproved, blocked, or out-of-scope capsules fail closed.

High-risk or disputed output adds `code_reviewer` with a recorded trigger and findings.
Demonstrably difficult implementation may move to `implementation_specialist` only for concrete
complexity, unresolved failure, concurrency, migration risk, or consequential ambiguity. Multiple
files, integration tests, or unfamiliarity alone are not escalation evidence. A role or effort
change is recorded and begins a fresh separate sequential session. Architectural ambiguity returns
to `design_architect`. `planning_analyst` remains available for explicitly requested read-only
discovery and planning without becoming a prerequisite.

All six registrations, exact models and efforts, sandbox boundaries, and relative configuration
paths remain unchanged except for descriptions that state the new routine ownership. ADR 0018's
compatibility policy still prohibits agent enablement/default/concurrency scalars, default roles,
generic model/effort defaults, and project-level model overrides. Required dependent phases remain
sequential and no automatic model router is introduced.

## Consequences and verification

Routine issues normally use one implementation session, reducing repeated orientation and handoff
cost while keeping the capsule, focused tests, self-review, and standard gates. Consequential,
high-risk, disputed, or demonstrably difficult work still pays for stronger independent controls.
The main risk is understating impact to classify consequential work as routine, so active role
instructions, contribution guidance, issue/PR templates, validator markers, and negative fixtures
all preserve the impact-based boundary.

Static validation verifies configuration and textual contract markers, not semantic compliance,
live-session provenance, CLI compatibility, or measured quota savings. Those remain separate
claims and must be reported as such. This decision changes no product behavior, graph schema,
checkpoint, provider, database, finance policy, JSON state, or external financial-write boundary.
