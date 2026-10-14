# Issue 103 arbitration A103-1

Coordinator `/root`, 2026-10-14. Primary decision: contract clarification.
Dispatch hold is recorded as elapsed audit time, not an offline coordination pause.

## Frozen criterion and evidence

Capsule `issue-103-yahoo-catalogue` generation1 digest
`552e8871276002b83388d4b8867bbdae0d27e543f831194a41faf857ca440b83`.
Relevant INV103-3/4 and AC103-3/5 require exact listing identity, retained validated
direct additions, deduplicated counts, immutable versioning and prior-version safety.
Architect `/root/issue103_design` returned DESIGN_READY in
`docs/iterations/024-issue103-catalogue-design.md`. Independent challenge
`/root/issue103_challenge` returned FAIL: contract ambiguity, not implementation defect.

Scenario: directly add VWCE.DE, then a full refresh enumerates the same listing tuple
with changed name or currency. Handoff retains direct observations, replaces discovery,
and rejects conflicting refreshed identity, but leaves overlap representation, conflict
fields, combined count and selected search observation underspecified. Identity tuple
is explicit; that alone does not choose authority among overlapping observations.
No implementation exists, so no expected-versus-actual runtime defect is claimed.

## Classification and accountable decision

Contract ambiguity: one reading rejects a complete refresh for changed optional
metadata; another stores two differing current records for one identity. Their effects
on publication, retention and search differ. Coordinator agrees this material
acceptance uncertainty needs a separate architect clarification rather than an owner
making a persistence choice. No new acceptance criterion or scope is authorized.

Rejected: silently waive failed challenge; infer financial correctness from cache;
drop direct provenance; broaden to research/eligibility; replace implementation owner;
grant/reset phase limits. No participant disagreement about the need to clarify is
currently recorded. Reviewer reported no other design blocker.

## Reservation, allowance and closure

Challenge reservation ends truthfully FAIL. Implementation, initial review, remediation,
final review and design reset each have one remaining default slot before reset start.
Coordinator uses the permitted single design_reset against INV103-4, in a fresh
read-only design_architect session `/root/issue103_design_reset`; native check and
reservation precede dispatch. Reset advances capsule generation without changing
frozen definitions or clearing consumption.

Observable closure: architect supplies one deterministic rule table for same-identity
overlap, changed optional observations, actual identity conflict, retained provenance,
combined listing count and returned search observation. Rules preserve original direct
observation times and prior usable cache on genuine conflict. Independent challenge
of that table must pass against INV103-3/4 and AC103-3/5 on the same capsule generation;
coordinator approval then permits the unchanged owner implementation gate.
Closure ends this episode, not ticket acceptance. New evidence revises this episode;
repeated assertions without evidence refer to its decision. No automatic further reset.

## Closure outcome

2026-10-14: separate reset architect supplied deterministic two-component observation
rules; capsule generation2 digest
`b9c97b4c7f067883a8752c7b8846b9cb63c85ca5848c926e3567542074b7a234`.
Fresh independent `/root/issue103_challenge2` code_reviewer/gpt-6-sol/high returned PASS
against all frozen criteria. A103-1 focused closure is satisfied: direct/discovered
overlap fixture has exact provenance preservation, whole-discovered authority, no
backfill, union counts, omission retention and exchange-conflict preservation rules.
Coordinator approves this handoff; next gate is native implementation check/reservation
for unchanged owner `/root/issue103_owner`. Initial failed challenge remains history.
Consumed reset1; remaining implementation1/initial_review1/remediation1/final_review1,
design_reset0. Episode closed; acceptance and delivery remain outstanding.

# Episode A103-2: post-delivery PR feedback

Opened 2026-10-14 by coordinator `/root` after user `fix them` accepted the concrete
three-comment repair recommendation and finite remediation1/final_review1 continuation.
Frozen capsule remains generation2 digest
`b9c97b4c7f067883a8752c7b8846b9cb63c85ca5848c926e3567542074b7a234`;
original delivered content was
`b1a4a37edd78408b8de883c2966cb04c4ab9e0fb415127c7967d81ce5abee8d5`, PR108.

Trigger: new material evidence revisits publication cleanup and evidence validation
after substantive repair and final review. A103-1 overlap decision remains closed.
No active phase to interrupt. Dispatch hold is audit coordination, not an offline pause.
Consumed counts remain1 each; the explicit continuation adds only one remediation and
one final review. Design reset and implementation receive no grant.

| Evidence and concern | Frozen IDs | Classification / concrete expected and actual path |
|---|---|---|
| PR108 comment4271295262; service failure returns | INV103-4, AC103-5 | Demonstrated metadata defect: CAS loser labels captured parent active_version after a winner changes pointer. Correctly label attempted parent or read validated current pointer without overwriting winner. |
| PR108 comment4271295283; store cleanup after commit | INV103-4, AC103-5 | Demonstrated recovery/visibility defect: one transient owned lock unlink failure is suppressed; lock remains and subsequent writes time out. Prior repair correctly preserves committed publication success, but did not retry or expose cleanup failure. |
| PR108 comment4271295296; nested report/page validation | INV103-2, AC103-2/5 | Demonstrated schema defect: correctly digested payload can omit source_version/rejected_count and embed arbitrary extra/raw page fields. Existing identity-link repair is valid but insufficient for exact allowlisted schemas. |

Primary accountable decision: narrow repair by implementation_worker/gpt-6-sol/medium
within frozen contracts; no new architecture/reset or catalogue schema/mapping change.
Reproduce before fixes and add focused regressions. Source inspection establishes
paths; no executed reproduction is claimed until the owner performs it.

Closure condition: failure metadata never mislabels captured parent as current active;
bounded retry releases a transiently failing *currently owned* publication lock so the
next writer can proceed; persistent cleanup failure is explicit while retaining truthful
committed-version outcome; exact required nested keys and types reject missing/extra
evidence on construction and readback. Never delete someone else's or purported stale
lock, roll back a committed winner, silently erase failures, replace locking architecture,
add eligibility/ranking behavior, or grant unlimited repair attempts. Persistent OS denial
cannot be promised to recover automatically. Escalate a genuine incompatible contract
reading rather than broaden this closure condition.

Rejected alternatives: dismiss new evidence because CI/final review passed; incorrectly
claim prior version remains after commit; silently steal stale locks; redesign storage;
reset prior history/counters. No participant disagreement yet; independent final review
must verify closure on corrected content. Completion of arbitration is not acceptance.

The earlier live child-agent session is unavailable in the current turn. Record an
explicit fresh same-role owner_handoff to `/root/issue103_pr_repair_owner`, retaining
implementation_worker/gpt-6-sol/medium, classified ownership and frozen capsule. This is
session recovery, not replacement due to disagreement. Native preflight/reservation
must precede that owner's repair dispatch. Original delivery and every author remain
in immutable ordered evidence; fresh reviewer excludes old and new write authors.
Later outcomes use the excluded native ledger once documentation is certified.

## A103-2 new material evidence and accountable revision

2026-10-14: the authorized owner reproduced the three PR findings before repair
(10 failing cases), and the repaired content passed full1555/48 plus focused38/1
and required gates on digest
`683948435c04e758afb5eef6e298319a50a51f6eef01b0db7f7c040cbdb28a44`.
Fresh verification and acceptance bound that digest. Independent final reviewer
`/root/issue103_pr_review` nevertheless returned FAIL: new lock-acquisition regression.
This section records a later evidence revision; it does not claim certification
of the resulting changed documentation or turn the failed review into a pass.

New B103-LOCK-ACQUIRE-STAT, INV103-4 / AC103-5: after exclusive lock creation,
the added `os.fstat(fd)` is outside the release finally and precedes descriptor close.
A transient OSError at that step produces store_io_error but strands fd/lock;
the next cooperating publisher times out. This is a demonstrated control-flow defect,
not persistent denial of cleanup, preference or new scope. Reviewer did not execute
fault injection; the future owner must reproduce the path explicitly.

The original three reviewed paths appear closed. Reviewer does not classify external
stat/unlink replacement interference as a cooperating-writer defect. No consensus
handoff, storage redesign or automatic reset is authorized by this finding.

Accountable revision: explicit stop. Current final review has ended truthfully FAIL;
all authorized remediation/final review slots are consumed. Preserve this repair as
clearly labelled WIP on original PR108 in draft. Do not deliver, merge, change owners
because of disagreement, or append another grant from the already-used `fix them`.

Proposed next bounded closure, only after distinct explicit user authority: one
remediation and one final review for exception-safe acquisition cleanup. An injected
fstat failure after exclusive creation must close the descriptor, release only its
known-owned lock, preserve active pointer, return a controlled failure and permit the
next cooperating writer. Focused regression, required gates, fresh same-content
verification/acceptance and independent final review then precede redelivery PR108.
No new frozen criterion, design reset, financial change or next child is requested.

## A103-2 distinct user authorization to resume narrow repair

2026-10-14 user `ok approved` accepted the explained scope: one additional remediation
and one final review for B103-LOCK-ACQUIRE-STAT, not merge/new scope/design reset.
The coordinator records a distinct native continuation with exactly those count deltas.
The prior failed final review remains failed and original PR108 delivery remains history.
Primary decision now resumes narrow repair against the existing observable acquisition
closure above; no acceptance condition is changed. Remaining before reservation:
remediation1/final_review1, implementation0/initial_review0/design_reset0.

The prior live repair agent is unavailable after the blocked turn. An explicit fresh
same-role handoff to `/root/issue103_lock_repair_owner` preserves implementation_worker /
gpt-6-sol / medium and frozen capsule generation2. Session recovery is not replacement
due to disagreement. Native remediation check and reservation must precede dispatch.
Owner must reproduce transient acquisition metadata failure, fix exception-safe fd and
known-owned lock cleanup, add focused regression proving prior pointer preservation
and next cooperating publication, complete gates and freeze content. Independent review
must verify closure before original PR108 can be redelivered. No extra lock architecture
or hypothetical unlimited OS recovery is required. Later outcomes use native ledger
evidence once documentation is certified.
