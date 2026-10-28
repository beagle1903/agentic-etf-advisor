# ADR 0043: Audited Issue123 capsule amendment

- Status: Proposed implementation; Issue128 design approved, implementation certification blocked by required type checking. No operational Issue123 amendment.
- Date: 2026-10-28
- Authority: Issue128 generation-2 DESIGN_READY capsule, independent corrected challenge and coordinator approval in [iteration 037](../../iterations/037-issue128-audited-capsule-amendment.md).

## Context

Issue123 has an ordinary, undelivered owner-led capsule for bounded source curation.
ADR 0042 later established a separate curator-assigned Fund identity contract. Its
selection for Issue123 would change a frozen consequential identity criterion. An
ordinary `capsule_update` cannot make that change, and a new ticket would conceal
Issue123's finite counts and blockers.

## Decision

The workflow admits exactly one `capsule_amendment` for the pinned Issue123
generation-2 capsule and original 31-event prefix. Admission binds the complete
preceding event history, current unsplit and nonterminal lifecycle, a fresh named
user authority, and the exact deterministic generation-3 replacement and nine
definition changes recorded in iteration 037. It rejects reuse of both Issue123
historical authorities and the normalized Issue128 governance-task approval.
Replacement authorization is a reference to the event authority and is consumed
once across connected lineage. The event is an audited capsule transition, not a
general patch mechanism.

On success, historical counts, limits, participants, owner, elapsed audit,
blockers, failed outcomes, delivery identity and repair debt remain. Current
design, challenge, approval, implementation, verification, acceptance and review
success bindings are cleared. The target is consequential and unapproved.
No phase count or source attempt is granted. A separate finite user grant, counted
design reset, independent design challenge, coordinator approval, new target work,
bounded remediation, verification, acceptance and independent final review remain
necessary. The original no-publication/no-activation invariant still applies.

## Consequences

The exception is intentionally bound to one exact history and target. Future
contract changes require separate authorization and design. Static validation
checks recorded evidence and content, not real human identity or source truth.
No product schema, financial eligibility, provider interface or live data changes.
