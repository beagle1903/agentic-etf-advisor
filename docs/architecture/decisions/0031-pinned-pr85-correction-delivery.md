# ADR 0031: Pinned PR85 correction delivery

- Status: Accepted for the generation-2, user-approved one-off correction.
- Date: 2026-10-05.
- Preserves: ADR 0026 immutable history/content binding and ADR 0030 cycle limits.

PR85's status-display correction changed repository content after Issue84's
delivery. The original 61-event ticket and its PR/content binding cannot certify
that new content. A separate architect design, independent challenge, user
authorization and coordinator approval froze one complete generation-2 capsule
and fixed supplemental history.

One `correction_delivery` event may follow only the exact delivered Issue84
prefix. It imports the pinned historical reservations, including the failed
generation-1 challenge and failed in-attempt formatting check. A digest chain
binds subsequent supplemental events. It requires the distinct A4 authorization,
coordinator approval, one implementation, one verification, acceptance and one
independent review. Pauses retain reservations; a failed completed phase cannot
be replaced. The independent review seals the audit prefix through acceptance
and the final repository content. The certificate changes neither the original
ticket's counts nor its original delivery binding.

Prospective validation compares the candidate to the external append-only
journal and current repository content. Atomic append repeats those checks under
the writer lock and recomputes content immediately before replacement. PR
validation selects the correction binding exclusively when present, for the
same repository, PR85 and Primary issue #84. The status projection reports
supplemental and aggregate counts under a nullable `correction` field.

The scope is this exact certificate and PR. It does not authorize a generic
post-delivery reopening mechanism, another attempt, changed CI privileges,
or Issue83 product work. The historical import records unknown phase timestamps
without inventing them. Static checks cannot authenticate an unrecorded real
session or a fabricated conversation reference; the coordinator and reviewer
must assess those anchors against actual evidence. Any failed substantive
phase or changed final content returns to explicit user decision.
