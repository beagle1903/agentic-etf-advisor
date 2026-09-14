# Quota-efficient Codex workflow design

- Status: DESIGN_READY
- Approved: 2026-09-14
- Authorization: User approved implementation after reviewing the proposed risk-tiered workflow.
- Relationship: Supporting workflow design; this does not replace the active Iteration 017
  product contract.

## Goal

Reduce repeated repository orientation, design restatement, and handoff cost while preserving
stronger controls for consequential work. Routine issues should normally complete in one
authorized implementation session within the shared Codex quota.

## Classification and ownership

| Classification | Execution contract |
| --- | --- |
| Mechanical, low-risk, architecture-determined | One `bounded_worker` using `gpt-5.6-terra` at medium effort owns the capsule, implementation, focused tests, self-review, and verification. |
| Ordinary feature or bug within established contracts | One `implementation_worker` using `gpt-5.6-sol` at medium effort owns the same complete sequence. |
| Consequential financial eligibility, safety, authentication, persistence/replay, security, or architecture contract | A separate read-only `design_architect` using `gpt-6-astra` at high effort produces the approved handoff before an `implementation_worker` starts. |
| High-risk or disputed implementation | Add an independent `code_reviewer` using `gpt-5.6-sol` at high effort and record the trigger and findings. |
| Demonstrably difficult implementation | Escalate to `implementation_specialist` using `gpt-5.6-sol` at high effort in a fresh sequential session with a recorded reason. |

Integration tests, multiple touched files, or an unfamiliar file do not alone require a
specialist. Escalation requires concrete complexity, unresolved failure, concurrency, migration
risk, or consequential ambiguity. Routine review fixes remain with the implementation owner when
they fit the approved capsule. `planning_analyst` remains available for explicitly requested
discovery and planning without becoming a routine prerequisite.

## Design capsule

Every issue records a compact `DESIGN_READY` capsule before implementation edits. It contains:

- classification, owner role/model/effort, rationale, and user authorization;
- scope and non-goals;
- invariants, affected interfaces, and JSON/state impact, including an explicit `none` when
  supported;
- acceptance criteria and focused verification;
- documentation needs, risks, and escalation triggers.

For mechanical and ordinary work, the authorized implementation session may author and record
the capsule before its implementation edits. No separate planning agent or repeated user approval
is required. For consequential work, only a separate architect session produces the handoff and
the coordinator must approve it before implementation starts. An incomplete, blocked, or
out-of-scope capsule blocks dependent implementation. Review findings never authorize a contract
change.

## Scope

- Replace unconditional multi-session routing with the classification contract above.
- Keep all six registered roles, pinned models/efforts, sandboxes, and relative config paths.
- Let routine implementation owners perform focused tests and self-review in the same session.
- Make independent review and specialist escalation conditional and evidence-backed.
- Align active instructions, role contracts, contribution guidance, templates, validator rules,
  and focused workflow tests.
- Add a superseding ADR while preserving accepted ADR history.

## Non-goals and invariants

- No application behavior, graph schema, checkpoint, provider, database, finance-policy, JSON
  state, or external financial-write changes.
- No automatic model router, global Codex configuration edits, quota guarantee, parallel dependent
  phases, or silent role/model/effort escalation.
- Preserve JSON-serializable state, replaceable side-effect interfaces, source attribution, and
  separate human approval for future external financial writes.
- Preserve ADR 0018 compatibility: no prohibited agent scalars, default role, generic model/effort
  defaults, project model override, or concurrency cap.
- Preserve read-only role boundaries and the rule that reviewer findings cannot authorize work.

## Affected interfaces and files

- `AGENTS.md` and `CONTRIBUTING.md`
- `.codex/config.toml` and `.codex/agents/*.toml` only where descriptions or responsibility
  boundaries need alignment
- `.github/PULL_REQUEST_TEMPLATE.md` and the four issue templates
- `scripts/validate_codex_workflow.py` and `tests/test_codex_workflow.py`
- A new ADR superseding only mandatory routine phase separation and task-by-task routing

`docs/architecture/system.md` requires no change because this is a development-workflow migration.
Accepted ADRs and the previous routing design remain historical records.

## Acceptance criteria

1. Mechanical and ordinary role instructions permit recording a complete capsule and finishing
   the authorized issue in one session.
2. Every write role retains a consequential-work guard requiring a separate architect handoff and
   coordinator approval.
3. Read-only roles prohibit mutations, and reviewers cannot issue authorization.
4. Routine focused tests and self-review stay with the owner; independent review and specialist
   sessions require recorded triggers.
5. Active guidance and templates use the same tier rules without unconditional routine-session
   contradictions.
6. All six registrations, settings, sandbox boundaries, and ADR 0018 prohibitions remain enforced.
7. Negative fixtures independently cover routine-session permission, capsule ordering,
   consequential gating, reviewer non-authorization, and classification/evidence markers.
8. Existing foreign-working-directory and registration-before-role-file validation coverage stays
   intact.
9. Focused workflow tests, standalone validation, Ruff lint and format, strict mypy, full offline
   tests, package build, Compose validation, and diff checks pass.
10. Static validation, live-session provenance, CLI compatibility, and measured quota savings are
    reported as separate claims.

## Risks and escalation

The primary risk is classifying consequential work as routine to save quota. Classification is
based on potential impact, not diff size. Architectural uncertainty returns to
`design_architect`; difficult implementation may move to `implementation_specialist`; disputed or
high-risk output adds `code_reviewer`. Any role or effort change is recorded and starts a fresh
sequential session.

The second risk is leaving contradictory unconditional gate text in an active surface. Targeted
searches and negative validator fixtures must guard that boundary. Static markers remain regression
checks, not proof of live-session provenance or semantic compliance.

## Migration evidence

This handoff was produced by a read-only `design_architect` session using `gpt-6-astra` at high
effort under the pre-migration workflow. The coordinator approved it based on the user's explicit
2026-09-14 implementation authorization. Implementation uses a fresh `implementation_worker`
session with `gpt-5.6-sol` at medium effort. The pre-existing deletion of
`.cursor/rules/project-quality.mdc` is unrelated and must remain untouched and outside delivery.
