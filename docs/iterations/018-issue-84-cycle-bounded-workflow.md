# Issue 84: cycle-bounded development governance

Status: implementation in progress; frozen capsule and acceptance IDs are in
`docs/workflow/tickets/issue-84.json`. The user requested that finite workflow
limits count review, design reset and reimplementation cycles, rather than
completion time. After the first implementation exposed a retained-history CI
gap, the user authorized exactly one additional design reset and implementation
attempt, without extra review attempts or minutes. A separate corrected architect
handoff, independent challenge and coordinator approval bind capsule generation 3.

This slice changes only the workflow engine, static checks, tests, templates and
guidance. New tickets use `cycles-v1`; historical prefixes remain immutable.
Explicit transitions and split allocations preserve counted history. The exact
Issue83 timing blocker waiver does not imply product verification or delivery.

The CI introduction rule accepts the exact retained Issue23 ten-event design
ledger and Issue83 nine-event successor prefix together only for Primary issue
#83. Issue83's next event must be a valid explicit `policy_transition` with the
fixed prefix digest and exact timing-blocker waiver. The parent remains retired
with one successor; later Issue83 events follow ordinary phase, content, review
and delivery gates. Issue84's independently pinned bootstrap is the other narrow
historical introduction. Focused tests replay the retained histories and reject
altered parents, changed child prefixes, missing or misplaced transitions,
different waivers and wrong PR primary identity.

Verification and independent review evidence are recorded in the ticket ledger
after the final content is ready. This governance ticket changes no authentication
or financial product code.
