# ADR 0002: Human review before advisory finalization

- Status: Accepted
- Date: 2026-08-27

## Context

Portfolio guidance combines user-specific constraints, imperfect data, nondeterministic
model output, and financial risk. A disclaimer alone is not an adequate control.

## Decision

Pause the LangGraph workflow after a complete draft and its evidence/guardrail checks, but
before finalization. The reviewer can approve, edit, or reject. The graph must use durable
checkpointing so review can happen later without replaying completed side effects.

Any future broker, email, file-publishing, or external write action receives its own
separate approval immediately before execution.

## Consequences

- The dashboard must render interrupt payloads and resume commands.
- Review decisions and feedback become auditable graph state.
- Side effects before an interrupt must be idempotent.
- Automated tests must cover approve, edit, reject, and malformed review input.
