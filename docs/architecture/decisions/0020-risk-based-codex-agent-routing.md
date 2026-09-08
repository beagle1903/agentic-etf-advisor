# ADR 0020: Risk-based Codex agent routing

- Status: Accepted
- Date: 2026-09-08
- Supersedes: Fixed model/role routing in ADRs 0017 and 0018; preserves the recorded design
  gate, separate sessions, and ADR 0018 compatibility constraints.

## Context

Fixed Astra routing spends the same model tier on routine implementation and consequential
design. The approved [design handoff](../../iterations/017-codex-agent-routing-design.md)
introduces explicit selection based on ambiguity and risk.

## Decision

Register six roles with exact descriptions, relative configuration paths, pinned model and effort,
and bounded instructions. AGENTS.md holds the authoritative task matrix.

| Role | Model / effort | Sandbox |
| --- | --- | --- |
| planning_analyst | gpt-5.6-terra / medium | read-only |
| design_architect | gpt-6-astra / high | read-only |
| bounded_worker | gpt-5.6-terra / medium | workspace-write |
| implementation_worker | gpt-5.6-sol / medium | workspace-write |
| code_reviewer | gpt-5.6-sol / high | read-only |
| implementation_specialist | gpt-5.6-sol / high | workspace-write |

Only architecture-determined low-risk designs may use planning_analyst. Consequential financial,
safety, authentication, persistence/replay, security, and architectural contracts require
design_architect regardless of diff size. Unclear dependencies or acceptance criteria go to
code_reviewer; architectural ambiguity goes to design_architect. Review findings do not authorize
implementation. Every write-capable role requires a recorded and approved DESIGN_READY handoff.

Normal implementation uses implementation_worker, mechanical work uses bounded_worker, and complex
implementation, integration tests, and substantive remediation use implementation_specialist.
The coordinator records role, model, effort, rationale, and escalations. Changes in role or effort
start a separate sequential session. Dependent phases do not run in parallel.

Luna/low remains an explicit option only for bounded read-only fact gathering, without design-gate
or implementation authority. No permanent Luna role, GPT-5.5 default, routine extreme effort,
autonomous routing, generic-agent default, project model override, or concurrency scalar is added.

## Consequences and verification

Static validation rejects inventory and contract drift, extra settings, and absent instruction
or documentation boundaries. Isolated fixtures run the command from another directory and cover
malformed files, role/path swaps, prohibited defaults, and missing gates. Marker checks are a
regression guard, not semantic proof that every instruction is followed.

Live-session role/model/sandbox provenance and model availability remain distinct from static
validation and local CLI configuration loading. The coordinator retains session evidence in the
PR. No product behavior, JSON graph state, checkpoint, provider, database, or financial-write
boundary changes.

This bootstrap uses the pre-migration design_architect Astra/high and implementation_worker
Astra/medium contracts. Fresh sessions use the new routing after delivery. Verification results
and CLI limitations are recorded in the linked design document.
