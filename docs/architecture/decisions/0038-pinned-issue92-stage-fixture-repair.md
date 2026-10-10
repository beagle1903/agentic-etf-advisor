# ADR 0038: Pinned Issue92 stage-aware fixture repair

Status: Accepted for the exact Issue92 finite disposition approved on 2026-10-09.

## Context

The third content-bound Issue92 verification failed the full offline suite:
1 failed, 1,509 passed and 47 skipped. An actual-saved-ledger test assumed
`repairing` for every ledger with at least 18 events. The valid 21-event
verification start reported `verifying`. The failure was recorded at event 22,
and event 23 added `B92-LIVE-STAGE-FIXTURE-ASSUMPTION` against `AC84VERIFY`.
The prior failed recovery and failed PR-identity verification remain history.

## Decision

The separately approved, independently challenged R92SD1 handoff grants one
same-owner stage-aware test repair. Its immutable 23-event stop, ten source
descriptors, eight closeout descriptors and exact grant bind event 24
`issue92_stage_fixture_repair`; the ordinary event 25 starts remediation 7.
The disposition grants exactly one fourth local verification and preserves
the unused independent final-review limit of five. No prior failed stage,
count, author, authority, capsule, content or publication binding is reset.

Actual-ledger tests calculate expected stages, active/suspended reservations,
counts, limits and certification from saved event facts. Historical 2-, 6-,
16-, 18- and 23-event fixtures are immutable and independent of the current
ledger tail. Native replay validates the actual saved 25-event bootstrap and
all archived source bytes before the repair can complete. Completed failure
stops further phases for a separate finite user decision.

The original single new-PR permission and one actual-saved-delivery check
sequence remain conserved. Issue92 PR creation must follow this latest grant
and event 24 while retaining the exact queued/live identity and content checks
from ADR 0037. This decision changes workflow governance only; product graph
state, financial side effects and actual Issue23/83 work remain outside scope.
