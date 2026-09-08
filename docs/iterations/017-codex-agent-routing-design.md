# Codex agent routing design

- Status: DESIGN_READY
- Approved: 2026-09-08
- Baseline: `63434ae8ca9074195f2adc50512e2b6a65de6024`
- Relationship: Supporting workflow design; this does not replace the active Iteration 017
  product contract.

## Goal

Replace fixed two-role model routing with a small, explicit, risk-based set of project Codex
roles. Preserve the recorded design gate, sequential phase boundary, explicit role registration,
and repository compatibility constraints.

## Approved role contract

| Role | Model and effort | Sandbox | Responsibility |
| --- | --- | --- | --- |
| `planning_analyst` | `gpt-5.6-terra`, medium | `read-only` | Discovery, aggregation, subtask planning, and small designs determined by existing architecture |
| `design_architect` | `gpt-6-astra`, high | `read-only` | Architecture, consequential decisions, ambiguous contracts, and difficult review or diagnosis |
| `bounded_worker` | `gpt-5.6-terra`, medium | `workspace-write` | Approved mechanical changes, straightforward unit tests, and straightforward review fixes |
| `implementation_worker` | `gpt-5.6-sol`, medium | `workspace-write` | Normal implementation and routine CI/CD work |
| `code_reviewer` | `gpt-5.6-sol`, high | `read-only` | Substantive code review, dependency review, correctness analysis, and test-gap analysis |
| `implementation_specialist` | `gpt-5.6-sol`, high | `workspace-write` | Cross-cutting implementation, difficult debugging, integration tests, and substantive review remediation |

Luna at low effort may be selected explicitly for bounded, read-only fact gathering. It cannot
issue a design gate or implement a ticket. No permanent Luna role or GPT-5.5 default is added.

## Scope

- Register all six named roles with exact descriptions and relative role-file paths.
- Add the four missing role files and update the two existing contracts.
- Document risk-based selection, escalation, approval, and sequential-session rules.
- Update issue and pull-request templates to record the actual selected role, model, effort,
  design handoff, approval, and escalation evidence.
- Extend static validation and focused tests across the complete role inventory and instruction
  boundaries.
- Add a new ADR for risk-based routing while preserving accepted ADR history.

## Non-goals

- Product behavior, application model providers, financial rules, graph state, checkpoint data,
  live services, global Codex configuration, autonomous routing, or concurrency expansion.
- A general multi-agent framework or a default model for unregistered generic agents.
- Routine use of `xhigh`, `max`, or `ultra` effort.

## Invariants and routing

1. Every issue-backed change or verification task requires a recorded, approved `DESIGN_READY`
   handoff before a write-capable role starts.
2. `planning_analyst` may issue the handoff only when existing architecture fully determines a
   low-risk solution. Financial eligibility, safety, authentication, persistence or replay,
   security, and other consequential contracts require `design_architect` regardless of diff size.
3. Unclear dependencies or acceptance criteria route to `code_reviewer`. Architectural ambiguity
   routes to `design_architect`.
4. Normal implementation uses `implementation_worker`. Cross-cutting work, difficult debugging,
   integration tests, and substantive review remediation use `implementation_specialist`.
5. Straightforward, approved mechanical work may use `bounded_worker`.
6. Review roles return findings; they do not independently authorize implementation.
7. The coordinator records role, model, effort, rationale, and escalations. A role or effort change
   starts a separate sequential session; an agent cannot silently redesign or increase effort.
8. The detailed task matrix is authoritative. The Terra-to-Sol-to-Astra summary is routing
   shorthand, not a mandatory sequence through every role.
9. Preserve ADR 0018 compatibility policy: no `enabled`, generic default model or effort,
   concurrency scalar, `max_threads`, default role, or project-level model override.

## Affected interfaces and files

- `.codex/config.toml` and `.codex/agents/*.toml`
- `AGENTS.md` and `CONTRIBUTING.md`
- `.github/PULL_REQUEST_TEMPLATE.md` and the four issue templates
- `scripts/validate_codex_workflow.py` and `tests/test_codex_workflow.py`
- A new ADR, expected to be `0020-risk-based-codex-agent-routing.md` after confirming the number
  remains available

No product architecture, API, JSON, checkpoint, provider, or database interface changes.

## Acceptance criteria

- The six registrations exactly match this table, resolve independently of current working
  directory, and contain nonempty bounded instructions.
- Every write-capable role requires an approved recorded handoff; every read-only role prohibits
  mutation.
- Low-risk classification and every escalation path are explicit and reviewable.
- No active guidance requires Astra for all implementation or all feature design.
- The validator rejects missing, malformed, swapped, extra, or drifted registrations and role
  files, prohibited defaults and overrides, and missing instruction or documentation boundaries.
- Issue and pull-request templates capture actual routing evidence rather than fixed two-role
  attestations.
- Focused workflow tests, the standalone validator, Ruff lint and format, strict mypy, the full
  offline test suite, build, Compose validation, and diff checks pass.
- A bounded non-mutating local configuration-load check is attempted. Its result is separated from
  model availability and actual-session provenance, and global settings are not modified.

## Bootstrap and risks

This migration is implemented and verified by the roles registered before the migration:
`design_architect` at Astra/high for this design and `implementation_worker` at Astra/medium for
implementation. The new routing applies only to fresh sessions after delivery. The pull request
must record this bootstrap fact.

Static validation cannot prove the model, sandbox, or role used by a live session. Six roles also
increase documentation-drift risk, so the validator must enforce the exact inventory and critical
prompt boundaries. Live CLI loading may remain blocked by the unrelated user-global configuration;
that limitation must be reported without changing global settings.

## Implementation verification (2026-09-08 UTC)

The approved six-role inventory, bounded instructions, routing matrix, templates, and ADR 0020
are implemented. Registration and role-file validation rejects extras, missing/malformed/swapped
contracts, prohibited defaults/overrides, missing approval/escalation boundaries, and absent
routing evidence markers. Fixtures resolve the script independently of the working directory.

- Focused workflow suite: 207 passed.
- Full offline suite: 604 passed in 74.16 seconds.
- Standalone workflow validator, Ruff lint and format (121 files), strict mypy (46 source files),
  package build, Docker Compose validation, and diff checks passed.
- The initial lint/format passes found description-string formatting only; those were corrected
  and both final checks passed.
- Non-mutating configuration-load attempt: PATH CLI is codex-cli 0.128.0.
  `codex features list` failed on the unrelated user-global `service_tier` value:
  `unknown variant default, expected fast or flex`. Global settings were not modified.

Static validation passed; local CLI loading, model availability, and actual runtime role/sandbox
provenance are separate claims and are not established by these tests. Marker checks protect
critical text boundaries but cannot prove semantic compliance with instructions. No live services,
provider requests, product/runtime behavior, or external financial writes were involved.
Coordinator review and pull-request delivery are recorded below; final CI remains pending.

Coordinator review narrowed project-level validation to the prohibited `model` and
`model_reasoning_effort` keys. Unrelated top-level settings remain allowed; a history-table
fixture verifies this boundary alongside explicit override-rejection fixtures.
After this correction, all 207 focused tests, the standalone validator, Ruff lint and format,
and the diff check passed. The full-suite result above predates this narrow validator correction.

## Delivery

- Branch: `codex/refine-subagent-routing`
- Bootstrap implementation commit: `8ed38e764794e6cda2956ae449c1c377ea4555f8`
- Pull request: https://github.com/beagle1903/agentic-etf-advisor/pull/56
- CI: passed in 33 seconds for commit `76fb5a1`:
  https://github.com/beagle1903/agentic-etf-advisor/actions/runs/34256443788
