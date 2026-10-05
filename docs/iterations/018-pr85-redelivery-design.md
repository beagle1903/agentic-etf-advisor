# PR85 append-only correction delivery design

Date: 2026-10-05. Issue84 / PR85. Status: BLOCKED_FOR_DECISION; challenge failed.

Authorization: burha replied "go on" to the proposal to prepare a separate design
for recording corrected delivery evidence. The earlier explicit one-off exception
and quota-conservation request remain in force. This reservation permits one
read-only design and one independent challenge, sequentially. It is not an
implementation allowance, counter reset, or automatic renewal of a terminal ticket.

Classification: consequential development-governance / replay / delivery binding.
Architect: design_architect / gpt-6-astra / high,
`/root/pr85_redelivery_design`, read-only.
Rationale: Issue84 is delivered and its source-content binding must not be reused
for changed source. Original events, counters and independent review must survive.
Independent challenge: code_reviewer / gpt-6-sol / high, separate read-only session.
Implementation owner if subsequently approved: implementation_worker /
gpt-6-sol / medium; not started or authorized by this reservation.

The coordinator ran the required Issue84 design-reset dispatch check. It rejected
with `terminal ticket; explicit user decision required`. As explicitly approved,
the supplemental exception records this read-only design reservation without
altering the original ledger or claiming that an ordinary phase gate passed.

## Scope and constraints for the architect

Design the smallest safe append-only way to bind the already reviewed status fix
and any required narrowly scoped governance changes to the original PR85 identity.
Compare a bounded correction record with reopening a delivered ticket; prefer no
general automatic reopening, new-issue quota escape, CI bypass or overwritten
delivery event. The architect must state whether the available authorization is
sufficient for its actual design and enumerate any further explicit decision.

Preserve original Issue84 JSON byte-for-byte at design time and all original events
in any proposed eventual append. Preserve counters and approval identities,
immutable merge-base history, the original repository/PR identity, and fresh
verification/acceptance/independent-review content equality. Do not reuse the
status-only review to certify subsequently changed governance code.

Non-goals: product/authentication work, providers/services, live databases,
financial changes, CI privileges, role routing, trade execution, new quota budgets.
Possible affected interfaces: workflow append/replay/check/CI and status JSON.
Application graph JSON/state impact: none. Ledger impact: proposal must specify
exact event(s), append validation, consumed attempts, and stop conditions.

Architect handoff must include full scope, non-goals, invariant and acceptance
definitions, owner/model/effort, authorization, interfaces and JSON impact,
verification, docs/ADR requirements, risks and escalation triggers. Freeze and
hash the resulting proposal before independent challenge. Coordinator approval
must bind the same digest. No source/test/CI edits before an approved capsule.

## Sequential phases and interruption record

1. Read-only design: COMPLETE; `/root/pr85_redelivery_design` returned
   DESIGN_READY, explicitly contingent on the further user decision below.
2. Independent challenge: COMPLETE, CHALLENGE_FAIL; `/root/pr85_redelivery_challenge`,
   code_reviewer / gpt-6-sol / high, read-only. Required Issue84 challenge check
   rejected as terminal; the explicit supplemental design/challenge exception
   records the actual reservation without inventing an engine-approved phase.
3. Coordinator decision: approval WITHHELD for the challenged digest; unresolved
   consequential ambiguity must not pass to a write-capable owner.
4. Implementation / verification / independent review / publication: not started.

Resume worktree: `C:/Users/burha/.codex/worktrees/cycle-bounded-workflow/agents-lab`.
Branch: `codex/cycle-bounded-workflow`, local status-fix commit `771ba59`.
Remote PR head at reservation: `6e695144871fce97d3c711f8e430d5524782b8bc`.
The original correction passed 115 focused tests and independent scoped review.
Its handoff is `018-issue-84-pr85-status-correction.md`; do not redo those steps
unless related content changes. Primary authentication checkout is unrelated.
On quota interruption, resume the current reserved phase from this document,
preserve every completed result, and do not start additional attempts.

## Frozen proposal and architect result

The complete proposal is `018-pr85-correction-delivery-capsule.json`.
Canonical SHA256: `e21925dd0c39c9642d29798fc0353bcb6135182c5c470ae23f647316f5233473`.
Selected future owner session `/root/pr85_redelivery_implementation` is recorded
for digest stability only; it is not started or authorized.

The architect recommends one `correction_delivery` certificate after the exact
original 61-event Issue84 prefix. It preserves original terminal state, counts,
capsule and delivery binding and records supplemental authorizations and actual
phase history. It needs fresh governance verification, acceptance and independent
review of identical final content. The current status-only review cannot certify it.
Only original repository/Issue84/PR85 is eligible, and any later event rejects.

Original canonical prefix digest and consumed counts were independently read back
and match the frozen proposal. This differs from the original ledger's file-byte
checksum; neither original event content nor bytes have been modified.

Further user decision required: approve this exact pinned certificate mechanism,
bootstrap reservation/import exception, one governance implementation and one
independent code review. No remediation, final-review retry or additional design
reset would be available. The architect states that the existing "go on" reply
authorizes design/challenge, not this broader implementation.

## Independent challenge result and concrete failure scenario

CHALLENGE_FAIL binds the exact canonical proposal digest above.
Finding maps to I84CYCLES / AC85C-BOUND and I84GATES / AC85C-EVIDENCE.
The proposal describes a strict versioned event but does not freeze its actual
JSON keys/types, required phase records, deterministic ordering predicates,
normalized authority identities, or how the supplemental reservations/outcomes
are checked against the imported event. Implementation could omit a failed or
interrupted reservation or reuse approval evidence while importing a final
certificate that asserts successful implementation/review. Choosing the schema
and those validation rules only after challenge would not bind the challenged
contract to actual implementation.

The reviewer made no edits and gave no implementation or design authorization.
The rejected proposal is retained unchanged, including its canonical digest, for
audit. Do not mutate its frozen JSON or call it challenged/approved.

## Interruption and next decision

No governance implementation session has started; no code, test, CI, original
ledger event or counter was changed in this design attempt. No source was pushed.
The original status correction remains local commit `771ba59`, with its existing
115-test and independent scoped-review evidence. The remote PR85 source still
contains the status bug. These documents will be saved in a separate local commit.

Both authorized read-only phases are consumed. The proposed implementation/review
allowances were never granted or consumed. A quota reset or another session must
not create a fresh design or challenge automatically.

Required explicit decision before more design: one additional finite design
revision and one separate independent challenge, with no implementation or code
review allowance yet. If granted, the architect must create a new proposal digest
that contains the exact certificate schema and deterministic validation matrix:

- Complete exact fields/types and allowed event/phase variants.
- Required reservations/outcomes for every known supplemental phase, including
  failed/interrupted work; transcript anchor and omissions detection.
- Pause/resume/session continuity, ordering, stop-after-failure and allowance checks.
- Normalized unique approval evidence checked against original and supplemental
  histories, and distinct author/session roles with full reviewer independence.
- Capsule/approval/challenge/content/acceptance/PR binding and atomic append checks.
- Positive and adversarial fixtures proving each rejection predicate.

After that revision, freeze its complete digest, obtain the separately authorized
challenge, and record coordinator decision. Only a clean complete challenged
proposal may be presented for the specific governance implementation allowance.
The project rule is explicit: "unresolved challenge ... means
BLOCKED_FOR_DECISION". No active agent is authorized to continue automatically.
