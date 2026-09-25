# GPT-6 Codex role routing design

- Status: DESIGN_READY
- Approved: 2026-09-25
- Baseline: `abdd5cac7f190c5912347b000042eaea5627ca45`
- Relationship: Supporting workflow design; this does not replace the completed Iteration 017
  product contract.

## Classification, ownership, and authorization

This is a consequential development-workflow contract change. A separate read-only
`design_architect` session using `gpt-6-astra` at high effort produced the handoff, the coordinator
approved it, and the user explicitly authorized implementation and pull-request delivery on
2026-09-25. A fresh `implementation_worker` session owns the exact approved implementation,
focused tests, self-review, verification, documentation, and delivery.

## Scope and mapping

Update the six pinned project roles to the GPT-6 family while preserving their current reasoning
efforts and access boundaries:

| Role | Model | Effort | Access |
| --- | --- | --- | --- |
| `planning_analyst` | `gpt-6-luna` | medium | read-only |
| `design_architect` | `gpt-6-astra` | high | read-only |
| `bounded_worker` | `gpt-6-luna` | medium | workspace-write |
| `implementation_worker` | `gpt-6-sol` | medium | workspace-write |
| `code_reviewer` | `gpt-6-sol` | high | read-only |
| `implementation_specialist` | `gpt-6-sol` | high | workspace-write |

Only the five model values that differ from the baseline change in the role TOMLs. Active
guidance, validation, focused tests, and a superseding ADR will enforce the same mapping. The
current `design_architect` TOML and `.codex/config.toml` remain unchanged.
The official OpenAI [model catalog](https://developers.openai.com/api/docs/models) and
[latest-model guidance](https://developers.openai.com/api/docs/guides/latest-model) confirm the
selected GPT-6 family IDs and support for the preserved medium and high reasoning efforts.

## Non-goals and invariants

- No application API, graph state, checkpoint, JSON schema, provider, database, dependency,
  financial behavior, trade, or external financial-system write changes.
- No role inventory, description, responsibility, reasoning-effort, sandbox, approval-gate,
  reviewer-authority, sequential-session, or escalation-policy changes.
- Preserve ADR 0018 compatibility: no generic model or effort default, project-level model
  override, default role, concurrency scalar, `max_threads`, or `enabled` setting.
- Preserve optional Luna/low selection for bounded read-only fact gathering as a separate
  exception without design-gate or implementation authority.
- Preserve accepted ADRs and completed iteration documents as historical records.

Affected interfaces are limited to the project-scoped Codex role model values and their static
workflow validator/documentation contract. JSON/state impact is `none`.

## Acceptance and verification

- The five migrated TOMLs, authoritative `AGENTS.md` table, and validator agree on the exact
  mapping above; the architect role remains Astra/high.
- Validation rejects each migrated role when reverted to its former GPT-5.6 model and rejects
  independent corruption or removal of every authoritative routing-table row.
- Existing registration-first, compatibility, instruction-boundary, and documentation checks
  remain intact.
- Run the focused workflow suite, standalone validator, Ruff lint and format check, strict mypy,
  complete offline pytest suite, package build, Docker Compose validation, and `git diff --check`.
- Attempt bounded non-mutating `codex features list`. If the installed CLI remains blocked by the
  unrelated user-global `service_tier = "default"`, report it separately without changing global
  configuration.

## Documentation, risks, and escalation

ADR 0025 supersedes only earlier pinned model assignments and the prohibition on permanent Luna
roles. `AGENTS.md` and `CONTRIBUTING.md` link the current decision. Static validation proves the
repository contract, not fresh-session model availability or live role/sandbox provenance. The
new routing applies to fresh sessions after delivery; this implementation session necessarily
uses the pre-migration routing bootstrap.

Stop and return to the coordinator if implementation would require a role, effort, sandbox,
authority, compatibility, application-state, or external-write contract change; return to the
architect for consequential ambiguity. Concrete unresolved implementation complexity may justify
a fresh `implementation_specialist` session, and high-risk or disputed output may add an
independent `code_reviewer` with a recorded trigger.

## Implementation verification (2026-09-25)

- Focused workflow suite: 234 passed.
- Standalone Codex workflow validator: passed.
- Ruff lint: passed; Ruff format check: all 132 files formatted.
- Strict mypy: passed across 46 source files.
- Complete offline suite: 1,031 passed and 3 skipped in 189.05 seconds.
- Package source and wheel build, Docker Compose configuration, and `git diff --check`: passed.
- Self-review confirmed `.codex/config.toml` and `design-architect.toml` are unchanged, all edits
  remain inside the approved workflow scope, and former active model IDs appear only in negative
  regression fixtures. Historical ADRs and iteration designs remain unchanged.

The bounded non-mutating configuration-load probe used `codex-cli 0.128.0`. `codex features list`
remains blocked by the unrelated user-global `service_tier = "default"` value, which that CLI
reports as `unknown variant default, expected fast or flex`. User-global and project configuration
were not changed. Static repository validation passed; CLI loading, fresh-session model
availability, and actual runtime role/sandbox provenance remain separate claims.
