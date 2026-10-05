# ADR 0030: Cycle-bounded ticket lifetime

- Status: Accepted
- Date: 2026-10-04
- Supersedes: ADR 0026 elapsed-time exhaustion and time-allocation split rules only.
- Preserves: ADR 0026 immutable history, frozen capsule, counted phase limits,
  independent design/review, content binding, delivery and PR checks.
- ADR 0029 is reserved for the separate authentication work.

The user clarified that finite development governance should bound repeated
review, design reset and reimplementation cycles, rather than completion time.
New ledgers therefore declare `cycles-v1` at initialization. The default five
counted phase limits remain one each. Starting a phase reserves its attempt;
pausing and resuming retains that reservation. Quota waits, open-phase elapsed
time and audit timestamps do not exhaust cycle-only work. A failed final review,
an exhausted required attempt or an unresolved substantive blocker still stops
the ticket for a user decision.

Schema-1 histories without a policy replay as `timed-v1` without rewriting any
event. A named user may append a transition bound to the exact preceding ledger
digest. It retains capsule, attempts, author/session history, phase reservation,
approvals, review and verification flags, content bindings and substantive blockers.
It does not resume a suspended phase. Only the exact recorded Issue83
`B83-EXHAUSTED` timing blocker can be waived, and that grants no acceptance or
verification claim. New append initialization and new CI ledger introductions
require `cycles-v1` regardless of event date. CI accepts two pinned historical
introductions only: the exact Issue84 bootstrap on Primary issue #84, and the
retained Issue23 design plus Issue83 successor on Primary issue #83. The latter
requires Issue23's entire ten-event history and Issue83's nine-event prefix
unchanged, followed immediately by a valid explicit cycle transition with the
exact recorded timing-blocker waiver. Later Issue83 events follow ordinary
replay and delivery gates; no historical approval or new attempt is inferred.

A cycle split allocates a positive, complete map of remaining counted attempts.
Sibling allocations subtract component-wise from one predecessor pool. Successors
inherit consumed counters, author/session history and used approvals, and their
limits equal inherited consumption plus allocated remainder. Timed splits remain
valid for historical replay only. A legacy timed descendant can migrate only when
each ancestor has a single successor; a later historical sibling invalidates that
lineage. The same restrictions apply to descendants of cycle successors.

This changes development governance only. It does not affect application graph
state, financial decisions, persistence, authentication, providers, role routing,
or credential handling. Evidence records are not cryptographic authorization or
a runtime agent kill switch.
