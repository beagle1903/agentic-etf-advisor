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

## Additional finite design revision approved (2026-10-05)

User authorization in chat 01a10c3f-947b-7d22-9a62-18be591c6074: "ok approved", answering the explicit request for one additional design revision and one independent challenge, with no implementation allowance yet.

Classification remains consequential governance/replay/delivery binding. Scope remains the single pinned PR85 correction certificate; Issue83, original Issue84 history and all consumed counts are preserved. Rejected generation1 capsule remains unchanged. New generation2 must freeze exact JSON schema, complete supplemental-history import, ordering, normalized approval uniqueness, reservations and failure predicates, and adversarial verification matrix.

phase_start: design_reset supplemental revision2; role design_architect / gpt-6-astra / high; session /root/pr85_design_revision2. Dispatch check was executed and rejected terminal state; this explicit supplemental reservation records that rejection truthfully. One read-only design revision reserved; one independent challenge available sequentially. No implementation or code-review allowance. Started by coordinator on 2026-10-05. Quota interruption preserves this reservation.

### Revision2 design outcome and challenge reservation

phase_end: design_reset revision2 PASS (DESIGN_READY), recorded 2026-10-05T13:41:12Z. Actual architect session /root/pr85_design_revision2, agent thread 01a10c43-0fcc-73d2-9127-b52c09e8ccf1. Complete unchanged architect response saved as 018-pr85-correction-delivery-generation2.md; SHA256 a9d60d359ad627f2bd104873e230a8d4cc449df49fb17695e051fd9b5c3f6edd.

Frozen complete capsule: 018-pr85-correction-delivery-capsule-generation2.json, canonical digest 138a10fa473e67274dde59d484510582b7c4ad5d53c79dbb5fa36fb3d241e756. Historical import canonical digest 899985eb7c493e901c8c4a9036772492341718edbe188308acedeb549ea781c1. This mechanical encoding includes the full architect specification; rejected generation1 remains unchanged. No implementation authorization.

phase_start: independent challenge revision2, reserved 2026-10-05T13:41:12Z; session /root/pr85_challenge_revision2; code_reviewer / gpt-6-sol / high, read-only. Required challenge dispatch check rejected terminal state; the user's explicitly approved supplemental reservation applies, and no passed engine gate is claimed. One independent challenge reserved; no further design/challenge attempt automatically available. Challenge binds exactly the frozen generation2 capsule digest above.

### Revision2 challenge capacity interruption

The reserved /root/pr85_challenge_revision2 turn returned infrastructure error: "Selected model is at capacity. Please try a different model." No review finding or completed challenge outcome was produced. Preserve the same session, pinned Sol/high role and reserved challenge attempt; retry its execution without a new allowance, role/model change or phase_start. This is an interruption, not CHALLENGE_FAIL or a replenished attempt.

Recorded H7 interruption boundaries from coordinator transcript:
- pause: 2026-10-05T13:43:00Z, /root/pr85_challenge_revision2, infrastructure capacity result amsg_01a10c4d-b119-76e1-a7ec-7094f41828b1; no substantive outcome.
- resume: 2026-10-05T13:43:27Z, same slot and session, collaboration.followup_task call; same reserved independent challenge and pinned model/effort.
These records must be preserved in any eventual supplemental transcript. No new start, review attempt or model change.

### Revision2 challenge passed; implementation decision pending

phase_end: H7 independent challenge PASS, recorded 2026-10-05T13:49:39Z. Reviewer /root/pr85_challenge_revision2 / code_reviewer / gpt-6-sol / high; actual agent thread 01a10c4c-a03a-7bb3-87ed-6ee2e05b6e41. CHALLENGE_PASS binds exactly capsule digest 138a10fa473e67274dde59d484510582b7c4ad5d53c79dbb5fa36fb3d241e756 and historical import digest 899985eb7c493e901c8c4a9036772492341718edbe188308acedeb549ea781c1. Verified source S1-S4 hashes, original61-event prefix, delivery/PR binding and consumed starts. No concrete frozen-ID failure found. No edits or implementation authorization from reviewer.

Coordinator assessment: the complete schema and deterministic imported-history predicates address the rejected generation1 findings. The reviewed frozen proposal is eligible for the exact next user decision; coordinator approval is not yet appended because the normative grammar requires A4 authorization first. Original terminal ticket, all counts and Issue23/83 histories are unchanged. Both explicitly approved read-only phases are consumed. Implementation has not begun.

Append-only supplemental journal through H7 result: C:/Users/burha/.codex/pr85-correction-journal.json; canonical digest 3e230810a6cfd1cae4a685981eb0b387abe903e5169e7503eed1eb2c8386da7d. It preserves H6 end, H7 reservation, capacity pause/resume and pass outcome with digest chaining. This external journal creates no repository content exclusion. Preserve it on interruption and append only subsequently authorized events.

Required next explicit decision: approve the exact generation2 pinned correction_delivery certificate, historical-import/bootstrap exception and workflow-only implementation in the frozen capsule, granting one implementation, one verification and one independent initial review. Zero additional remediation, final-review retry, design reset or challenge. Failed substantive phase stops for user decision; infrastructure pause retains same reservation. This decision does not resume Issue83 product work or authorize new attempts there. Successful implementation/review/content-bound certification would permit pushing the already reviewed status fix and correction machinery to the original PR85; no old certification may be reused.

No source pushed or redelivery claimed. Resume from this record, unchanged frozen capsule and external journal. Do not repeat completed design/challenge or substitute roles. Status: WAITING_FOR_IMPLEMENTATION_AUTHORIZATION.
