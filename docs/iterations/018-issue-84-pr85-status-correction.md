# PR85 status correction: approved one-off exception

Date: 2026-10-05. Issue: #84. PR: #85.

User authorization: after the coordinator explained that Issue84's delivered ledger
rejects reopening, burha explicitly approved the narrowly scoped workflow exception:
"ok I approve. we have %30 left, divide the task and document the possible
interruption if required."

Preserve `docs/workflow/tickets/issue-84.json` in full. Do not reset its counters,
rewrite delivery evidence, invent new issue numbers, or relax workflow enforcement.
The required pre-dispatch remediation check was run and rejected with
"terminal ticket; explicit user decision required". This supplemental record is
the user-approved exception for a finite correction attempt outside that terminal
ledger, not a claim that its original delivery binds changed content.

## DESIGN_READY capsule

Classification: mechanical, architecture-determined output correction.
Owner: bounded_worker / gpt-6-luna / medium, separate sequential session.
Rationale: the established split pool already tracks conserved remaining attempts;
the CLI display should read that value. No allocation or replay contract changes.
Authorization: direct user approval quoted above; one correction attempt, one
verification sequence and one independent review. No automatic renewal.
Scope: `scripts/ticket_workflow.py` status `remaining_counts`, focused regressions
in `tests/test_ticket_workflow.py`, and this evidence/handoff record.
Non-goals: changes to ledger schema, replay, gates, allocation, historical events,
CI privileges, role routing, application/authentication/financial code.
Invariant: I84SPLIT; status reports the predecessor's unallocated pool.
Interfaces: existing status JSON `remaining_counts`; shape and keys unchanged.
JSON/state impact: none to persistent ledger or application graph state; only
the existing status field's values change after cycle splits.
Acceptance: AC84SPLIT; unsplit status equals limits minus counts; after one or
multiple cycle splits status equals the remaining pool, including an all-zero
pool; over-allocation is still rejected.
Verification: CLI-level regression, focused ticket-workflow tests, Ruff lint and
format, both workflow validators, diff check, independent review.
Documentation: this correction record, exception in issue/PR bodies, final evidence.
Risks: original delivered ledger binds old content; changing source or this record
invalidates that binding. The existing CI delivery check cannot certify the patch
under the terminal ledger. Do not claim successful redelivery or weaken the check.
Escalation trigger: any need to change replay, delivery or CI contracts requires a
separate consequential design decision; stop this correction at a reviewable patch.

## Sequential reservations and interruption handoff

1. Correction: COMPLETE; `/root/pr85_status_correction`, bounded_worker /
   gpt-6-luna / medium. Source uses the split pool when non-None, including zero.
   CLI regressions exercise unsplit, intermediate, multiple and exhausted pools.
2. Verification: COMPLETE; 115 focused ticket tests passed; targeted Ruff lint and
   formatting, both workflow validators and diff check passed. Existing
   over-allocation regression remains unchanged. No product suite rerun required.
3. Independent review: PASS; `/root/pr85_status_review`, code_reviewer /
   gpt-6-sol / high, read-only. Trigger: substantive PR feedback and already
   consequential workflow ticket. The final-review pre-dispatch check was run
   and rejected as terminal; the same explicitly approved exception applies.
   No concrete I84SPLIT / AC84SPLIT defect or test gap found; replay and
   over-allocation enforcement are unchanged. Reviewer ran no tests and changed
   no files; implementation checks above supply test evidence.
4. PR publication: blocked until the new content can pass the original delivery
   binding without rewriting history or expanding the approved display-only scope.

Worktree: `C:/Users/burha/.codex/worktrees/cycle-bounded-workflow/agents-lab`.
Branch: `codex/cycle-bounded-workflow`; starting HEAD `6e69514`.
Primary authentication checkout has unrelated edits and must remain untouched.
On quota interruption, inspect this record and `git status` first. Resume only the
reserved phase; retain completed evidence and all original ticket history. Stop
after a failed independent review or a contract blocker; no new correction loop.

## Original ledger and publication blocker evidence

Original ledger is unchanged from HEAD. SHA256:
`ec8f6eae8144a76372f979b122f20cb5d8f6cd7aa024e64114c28fd45ca2cf1b`.
The exception is recorded in both Issue84 and PR85 bodies.
Direct `check_pr` evaluation of PR85's identity with current local content rejects
with `delivered ledger belongs to another PR or different content`. This is the
same content-binding check CI uses. This is a delivery blocker, not a failing
status regression. No ledger history, gate or CI rule has been changed.

## Resume point: BLOCKED_FOR_DECISION, correction complete

The reviewed source SHA256 is
`8ed738d2ba1e700b69b351f3d08fd039402e97cc00f2362d1d38a1cc5845cd6c`;
the reviewed test SHA256 is
`715ca6178031196a57b9e0f1182cc8502e66fb49ceb711e26acc2c44ba65f805`.
Review binds these two files; the final documentation update records its outcome.
The required delivery check also rejected the terminal ticket. The correction
will be saved as a local commit, without push or redelivery claims. PR85's body
records the approved exception but its remote source still contains the bug.

Remaining decision: authorizing a separate consequential design for append-only
post-delivery correction evidence and its CI binding, or leaving this patch local.
The current display-only authorization does not silently change those contracts.
Resume from this document and the local correction commit; do not repeat the
implementation or focused tests unless source changes. The original ticket's
events and consumed attempts must remain intact. Quota interruption grants no
additional phase allowance. No agent remains authorized to continue automatically.
