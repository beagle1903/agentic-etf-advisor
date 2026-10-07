# Owner-led workflow and standard finite continuation

Issue86. Consequential governance classification. User authorization: thread:01a10c3f-947b-7d22-9a62-18be591c6074/message:01a1123f-1708-7ea3-9b87-c691f8a161fa; user continue then authorizes separate permanent owner-led workflow/standard finite continuation issue after agreeing scope; not Issue84 retry.

Bootstrap capsule 94b135a551b96d9e2af8a8321488aac343d5d5d38c8bc9e661d9bf7e2bfafbc8. Initialized before phases under existing ADR0026 gate. Default finite limits preserved during bootstrap; new policy transition must be explicit, retain counters, and keep elapsed audit data. Separate design/challenge preceded coordinator approval. Owner: /root/owner_workflow_implementation, implementation_worker gpt-6-sol medium; same owner handles bounded same-scope remediation. Roles/models unchanged. Implementation started after its ordinary gate and reservation.

New branch from main; PR85 and all Issue23/83/84 history/work remain untouched and suspended. This issue changes workflow policy, not delivery of prior stopped tickets.

Implementation scope: `scripts/ticket_workflow.py` adds strict `owner-led-v1` dispatch,
an explicit one-way `policy_transition`, finite `continuation`, ordered historical
delivery bindings, current certification invalidation and same-owner remediation.
Atomic append rereads actual on-disk event, ledger set/bytes, temporary candidate and
repository content immediately before replacement. The existing `timed-v1` path
and historical ledger events remain replayable. Tests construct immutable fixtures,
exercise real saved delivery and two continuations, and mutate actual files between
append snapshots. New ADR 0033 and the role, contributor and template instructions
record the policy boundary. Product and graph/checkpoint state are unaffected.

Focused implementation self-check: `uv run pytest tests/test_ticket_workflow.py -q`
passed 97 tests; `uv run ruff check scripts/ticket_workflow.py
tests/test_ticket_workflow.py` passed after formatting. One fixture originally used a
non-Git temporary directory; it was updated to initialize Git because final append
now captures repository content even during initialization. No historic ledger was
edited for this correction. Static instruction fixtures pass 240 tests;
`scripts/validate_codex_workflow.py` and `git diff --check` pass. A later Ruff
SIM102 style self-check was corrected within this implementation reservation.
Full verification, independent review and final saved
delivery publication evidence will be recorded after their normal reservations.

Separate read-only design and challenge PASS; coordinator approved 2026-10-06T17:38:41Z under full scoped user authorization. Normative handoff LF-normalized SHA256 `7ecb43cfaaca150ae5ffe1f270b7a41d72b125259f1812ff9a5ac7dd35ea954c`; raw Windows CRLF SHA256 `2a5f54b6f4c3c3723fbfceaf8148ebce62d51800c7e0b212c75e9546acbc00fb` differs only by line endings. Capsule unchanged. Ordinary coordination resume after postdelivery continuation remains required. Implementation owner stays /root/owner_workflow_implementation; no model upgrade or ticket-specific exception.
