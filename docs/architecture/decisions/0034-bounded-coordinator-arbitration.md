# ADR 0034: Bounded coordinator arbitration

- Status: Accepted for Issue #88 implementation
- Date: 2026-10-07
- Preserves: ADR 0026 and ADR 0033 finite ledgers, ADR 0022 owner routing,
  ADR 0025 role pins and all accepted historical records.

## Context

Repeating designer, implementer and reviewer concerns can consume finite sessions
without a coordinator decision. A proposed success condition can also drift beyond
the frozen capsule while appearing to be a review repair. Both cases need an
accountable dispatch decision before another dependent handoff.

## Decision

The coordinator opens one arbitration episode when an underlying concern recurs
after a substantive response, repair or review response, including a reworded
version, or when a requirement, success condition or proposed remedy shifts beyond
or conflicts with the frozen capsule or previous closure condition. A newly
demonstrated defect still receives attention. The coordinator holds dependent
handoffs, records the existing roles' concrete scenarios and evidence against frozen
IDs, current phase and allowances, and classifies each concern as a demonstrated
defect, contract ambiguity, preference or outside scope.

One accountable decision chooses narrow repair, contract clarification, deferral
or explicit stop. It records alternatives, disagreements, rationale and one
observable closure condition with owner, verification and next permitted gate.
Unanimity is unnecessary. A demonstrated defect requires repair and verification
or stop; failed checks and reviews cannot be relabeled. Material uncertainty that
prevents acceptance also stops. Consequential ambiguity follows the existing
separate architect, independent challenge and coordinator approval path.
Same-scope repairs stay with the approved owner. A dispatch hold is not an offline
coordination pause; running phases use the existing truthful interruption/pause
procedure. Investigation requires a permitted checked and reserved phase.

Repeated assertions without new evidence reference the decision. New material
evidence updates the same episode with its effect and accountable revision. The
episode's closure does not replace ticket acceptance or content-bound review.
Arbitration grants no phase slot, automatic design reset, ledger override or owner
change. Exhausted counts, failed final review and serious blockers retain
BLOCKED_FOR_DECISION.

## Record and limits

Use `docs/workflow/templates/coordinator-arbitration.md` outside live ticket JSON.
Finish reviewable records before certification. Later outcomes may use existing
excluded ticket ledger evidence or linked external evidence; editing certified
documentation requires fresh certification. This decision adds no ledger event,
schema, replay, product, finance, provider or graph-state change. Static checks
protect required instruction text and role settings, but cannot prove actual
coordination, independent sessions or authority authenticity.
