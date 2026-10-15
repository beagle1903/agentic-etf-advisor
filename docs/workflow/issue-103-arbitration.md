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

## A103-2 new Linux CI evidence after corrected redelivery

2026-10-14: narrow acquisition repair passed Windows default1556/48, fresh verification,
all-AC acceptance and independent final review on content
`a4d3b467b2af24b9a6d56d65a9c29332009a48952268dc5c1e16210832bbd83e`.
The historical failed review remains failed. Corrected redelivery was recorded and
published as commit3c135ec before final CI completed; it is not a clean CI outcome.
This later document revision is new evidence, not a certification of changed docs.

Actual Linux CI run38611336874 then failed existing
test_replaced_lock_is_not_removed_after_commit (test_catalogue_review_repair.py256):
expected cleanup_error is absent after a replaced lock is accepted/deleted by the
device/inode-only guard. Result1failed1555passed48skipped. The assertion and current
production path establish inode reuse invalidates the assumed identity distinction;
do not dismiss the platform evidence as a Windows pass or skip/weaken the test.

New B103-LINUX-LOCK-IDENTITY under INV103-4 / AC103-5 is a demonstrated defect in
the already-asserted foreign-lock fixture, not a new unlimited external-interference
requirement. Earlier reviewer classification of external stat/unlink interference
did not address this concrete Linux test outcome. Commit success must remain truthful
while cleanup must not remove a replacement lock mistaken for the original.

Accountable revision: explicit stop. PR108 returns to draft/WIP; required CI is failed.
All current counted slots are consumed. Preserve completed acquisition repair and CI
failure in the same original PR and ledger; no automatic reset, new grant, weakened
test, merge or next child. Proposed next bounded closure needs distinct user authority
for one remediation and one final review: robust ownership distinction across inode
reuse (for example an owned marker rather than inode alone), faithful focused regression,
Windows and Linux checks, fresh same-content certification and redelivery PR108. No
locking architecture or catalogue/financial scope expansion is proposed. The new
material platform evidence updates this episode; unanimous agreement is not required.

The proposed native blocker append was rejected with `terminal history cannot be
reopened`; the delivery check also rejects `terminal ticket; explicit user decision
required`. Neither rejection was relabelled successful, no event was appended and no
allowance was consumed or invented. B103-LINUX-LOCK-IDENTITY currently names this
external evidence record; a permitted native continuation must precede its blocker
event and any further repair phase. Original delivered ledger remains immutable.

## A103-2 Linux repair authorization

2026-10-15 user `approved` accepts the narrow proposal: one remediation and one final
review for the Linux inode-reuse defect on original PR108. Distinct native continuation
adds only these finite counts, preserves prior consumption/deliveries and makes the
previously rejected terminal blocker append valid prospectively. The earlier rejection
remains truthful history; no event was backdated or relabelled.

Primary decision resumes narrow repair: strengthen currently owned lock identity across
inode reuse, retain the existing replacement-lock regression and add deterministic reuse
coverage. Verify on Windows and a Linux filesystem before final certification where
available, then fresh acceptance, independent final review and original PR108 redelivery.
Do not weaken/skip the failed test, remove foreign/stale locks, change committed-pointer
truth, redesign locking architecture or expand catalogue/financial contracts. Persistent
metadata/cleanup denial remains a controlled explicit limitation, not an unlimited OS
recovery promise. New marker initialization must retain exception-safe fd/owned-lock
cleanup rather than reintroduce the acquisition leak.

Prior live owner is unavailable in the new turn; explicit same-role recovery handoff to
`/root/issue103_linux_repair_owner` retains implementation_worker/gpt-6-sol/medium and
generation2 frozen capsule. Remaining before reservation: remediation1/final_review1,
other counts0. Native preflight and durable reservation precede dispatch. This is not an
owner replacement due to disagreement. Later closure evidence belongs in the excluded
ledger once documentation is frozen; repeated concerns without new evidence reference
this decision, while genuine new evidence revises this same episode.


## A103-2 new PR evidence during authorized Linux repair

2026-10-15 coordinator refreshed live PR108 threads before dependent handoff and
found three new P2 comments posted 2026-10-14T18:04:15Z. They were absent from the
three-comment repair and subsequent inode-reuse authorization. Current phase is
reserved remediation /root/issue103_linux_repair_owner; counted remaining slots are
remediation0/final_review1/design_reset0. This dispatch hold is not an offline pause.

| Evidence and path | Frozen criterion / expected versus actual | Classification and disposition |
| --- | --- | --- |
| PRRC_kwDOUF1JVc7-xtIF / store.read pointer and blob read_bytes | INV103-4 / AC103-5, controlled unavailable/error at CLI boundary; PermissionError or another OSError escapes read before CLI catches CatalogueError. Source path is store.read -> initial service read -> CatalogueError-only CLI handler. | Demonstrated defect B103-READ-IO; narrow normalization of pointer/blob read failures and focused service/CLI tests required. No implementation authorized by this comment. |
| PRRC_kwDOUF1JVc7-xtIM / validate_catalogue partition counters | INV103-2 / AC103-2/4, evidence must agree with accepted rows; complete report permits arbitrary nonnegative duplicate_count/rejected_count while accepted unique rows and page total match. Existing exact-key/type repair did not constrain these relationships. | Demonstrated defect B103-EVIDENCE-COUNTERS; strict complete-report counter relationships and correctly re-digested tampering tests required. New material evidence extends the existing schema concern. |
| PRRC_kwDOUF1JVc7-xtIA / directory fsync after rename | INV103-4 / AC103-5 handoff promises write/flush/validate blob before atomic pointer replacement and interrupted staging preserves prior catalogue. Requested scenario is host/power failure after successful pointer commit; handoff does not promise filesystem metadata durability across host crash. Current file fsync does not prove directory-entry durability. | Outside frozen power-loss guarantee; defer explicit durability design, platform capability and failure semantics to separately authorized work. No claim of crash-durable publication is made. This does not waive either demonstrated current defect. |

Designer evidence is generation2 handoff Cache/publication and Discovery sections;
owner reports these comments are distinct from the marker repair and has not changed
them; reviewer evidence is the three linked live PR threads above. Coordinator source
consolidation confirms direct read-error path and missing counter relationships; no
new investigation agent or unreserved phase was dispatched. No unanimous agreement
is needed and no missing test is treated as proof of correctness.

Primary accountable decision: explicit delivery stop. Complete the already authorized
Linux marker repair and its verification as WIP, preserving its actual outcomes, then
stop before acceptance/final-review/delivery. Do not spend the one remaining final
review on known unresolved defects. Reject silent inclusion of new fixes in the narrow
Linux grant, ignoring fresh material evidence, automatically granting more phases,
resetting design or claiming clean delivery from Windows/Linux passing suites.

Focused next closure condition: B103-READ-IO and B103-EVIDENCE-COUNTERS must each have
narrow owner repair plus failing-before/passing-after focused evidence against the IDs
above, fresh required verification, all-AC acceptance and the existing independent
final-review gate on identical content. Current owner remains accountable; a further
remediation reservation requires distinct finite user authority. Existing final_review1
remains unused. No merge, new PR, successor issue or broader persistence redesign is
authorized. The Linux defect may close independently, but that does not accept the
ticket or waive the newly demonstrated defects. Later outcomes use native ledger.


## A103-2 read/counter repair authorization

2026-10-15 latest user `approved` accepts one additional remediation for
B103-READ-IO and B103-EVIDENCE-COUNTERS, followed by existing final_review1.
Native continuation candidate was rejected `invalid finite continuation` because
that event requires a new final-review delta; no event was appended. The current
nonterminal blocked ticket instead uses supported extension with seconds0,
remediation1 and all other count deltas0, exactly matching user authority.

Primary accountable decision is narrow repair. Same approved owner session
/root/issue103_linux_repair_owner (implementation_worker/gpt-6-sol/medium) normalizes
pointer/blob read failures to controlled catalogue errors and validates complete
partition counters against accepted rows. Add failing-before/passing-after tests,
including correctly re-digested evidence tampering, then fresh verification,
all-AC acceptance and independent review of identical content. Preserve Linux
ownership-marker repair. Directory power-loss durability remains deferred;
no schema, finance, persistence redesign, merge or next-child scope is added.

Generation2 capsule and original PR108 identity remain unchanged. Native check
and reservation precede owner resumption; after reservation remediation0 and
final_review1 remain. Prior A103-2 focused two-blocker closure condition applies;
this finite grant does not erase outcomes or certify the WIP snapshot.


## A103-2 final-review malformed-container evidence

2026-10-15 independent final reviewer /root/issue103_read_counter_review confirmed
FAIL on verified/accepted content
`acfca72564b650dd83317357c41f5caff0b1943a15d13bf17255a886b8602fc3`.
Read-error and counter repairs passed their before/after regressions, both full
OS suites and required gates; this does not waive the newly demonstrated defect.

B103-COVERAGE-CONTAINER, INV103-4 / AC103-5: a complete active catalogue with exact
coverage keys but `partitions: null`, a recomputed valid digest and matching pointer
reaches `len(coverage["partitions"])` in service.py343. `CatalogueStore.read` raises
raw TypeError through store.py63; CLI handlers catch CatalogueError only. Reviewer
constructed blob/pointer in memory and mocked Path existence/read methods, without
filesystem writes. Expected strict malformed-cache controlled rejection; actual
uncontrolled traceback. This is new material container-shape evidence extending
the existing nested-schema concern, not repetition or a new acceptance criterion.

Primary accountable revision: explicit stop. Record final review FAIL and native
blocker; preserve narrow approved repairs as WIP on original PR108. Remaining
counted remediation0/final_review0/design_reset0. No new dependent handoff, automatic
extension, design reset, silent type-error suppression, delivery or merge. The
coordinator rejects accepting passing suites as proof of absent malformed-input
defects. Earlier directory-durability deferral remains unchanged.

Concrete next closure: approved owner adds a container-type guard before the
coverage partitions length/iteration operation, with correctly re-digested active
blob/readback and CLI negative fixtures proving controlled schema rejection and
no active-pointer mutation. Preserve valid empty partitions, approved complete
reports and existing marker/read/counter behavior. Fresh full required verification,
all-AC acceptance and independent final review must bind the corrected content.
This next repair requires distinct finite user authority for one remediation and
one final review. No such grant is inferred. Later evidence belongs in the excluded
native ledger; this document revision is WIP, not certification of changed content.


## A103-2 malformed-container continuation

2026-10-15 latest user `continue` resumes the immediately proposed narrow repair,
including one remediation and one independent final review. Native continuation
adds exactly those finite counts and clears current certification while preserving
all failed outcomes, historical deliveries and original PR108 identity. No merge,
new issue or design reset is authorized. Prior owner is absent from live inventory;
explicit same-role recovery assigns /root/issue103_container_owner,
implementation_worker/gpt-6-sol/medium, with original generation2 capsule intact.

Accountable decision resumes narrow repair of B103-COVERAGE-CONTAINER under
INV103-4/AC103-5. Guard the complete coverage partitions container before length
or iteration, reject malformed types through existing CatalogueError validation,
and add correctly re-digested active-cache/readback and CLI negative fixtures.
Owner self-review checks adjacent existing nested-container access in this same
validation path to keep the shape rejection consistent; this grants no schema,
financial, provider, directory-durability or persistence architecture redesign.
Preserve valid empty/complete reports, pointer bytes, Linux marker and prior read/
counter repairs. Do not blanket-catch programmer exceptions to mask bad shapes.

The focused closure remains controlled schema rejection, unchanged active pointer
and positive valid-cache coverage, then fresh required verification, all-AC
acceptance and independent final review on identical saved content. Native preflight
and durable reservation precede dispatch. After reservation remediation0/finalreview1
remain; no automatic additional allowance follows. Later outcomes use excluded
ledger evidence once reviewable docs freeze.


## A103-2 consolidated observation-type evidence

2026-10-15 independent /root/issue103_container_review returned final review FAIL
on verified/accepted content
`12c0cd5529abb97a343f74f6e2592f027d9860b7c86a070d618610045e8d50d7`.
The coverage partitions list guard and valid42-empty positive are correct. Both
full suites1571/48, focused38 and all required gates remain actual passes; this
new final-review failure is not relabelled.

B103-EXCHANGE-TYPE, INV103-4 / AC103-5: direct-only or complete discovered catalogue
with observation exchange `[]` or `{}`, a recomputed correct digest and matching
active pointer, raises unhashable-type TypeError at mapping membership in
service.py186. Path-mocked in-memory store read and all three CLI commands confirm
uncaught TypeError instead of controlled CatalogueError schema rejection. Reviewer
consolidated372 JSON-type perturbations across top-level, direct observation,
coverage/report/page fields and found this list/map exchange family as the only
raw exception in that bounded matrix; this is not an exhaustive correctness proof.

New material evidence extends the existing malformed-cache validation concern;
it is not repetition without evidence or an added AC. Primary accountable decision:
explicit stop. Preserve the correct partitions repair as WIP on original PR108,
record final review FAIL and new blocker. Remaining remediation0/finalreview0/
designreset0. Reject blind acceptance based on passing suites, blanket exception
suppression, silent schema redesign, automatic count grants, delivery or merge.

Concrete next closure is one bounded observation-type repair: validate exchange
string type before mapping membership, inspect equivalent type preconditions in
the existing validation boundary, and add correctly re-digested direct/discovered
active-cache list/map exchange negatives through store and all CLI paths, with
valid-cache positives and unchanged pointer. Retain the consolidated malformed-type
matrix where useful to prevent repeated single-field repair cycles. Current same
implementation owner remains accountable; fresh required verification, all-AC
acceptance and independent final review must bind identical corrected content.
This requires distinct finite user authority for one remediation and one final
review. No grant is inferred; no new architecture or financial behavior is proposed.
Directory power-loss durability deferral remains unchanged. Later outcomes belong
in excluded native ledger; this WIP document revision is not newly certified.


## A103-2 exchange-type repair authorization

2026-10-15 latest user `continue`, immediately after the exchange-type repair
proposal and WIPb210a1f, authorizes one remediation and one independent final
review. This is distinct from the prior partitions-container continuation.
Native continuation grants exactly remediation1/finalreview1 and preserves prior
failures/counts/PR108 bindings while clearing current certification. Existing
approved /root/issue103_container_owner remains available and accountable as
implementation_worker/gpt-6-sol/medium; no owner replacement or design reset.

Primary decision resumes the consolidated bounded observation-type repair under
INV103-4/AC103-5: validate exchange string type before mapping membership, check
existing type preconditions in this same validator boundary, and retain meaningful
correctly re-digested direct/discovered cache and CLI negative fixtures for list/map
exchange values. Use the prior bounded type-perturbation evidence to consolidate
regressions, preserving valid-cache positives and pointer bytes. No blanket catch
of programmer exceptions, schema redesign, financial behavior, directory-durability
claim, merge or successor work. Existing prior repair behavior remains invariant.

Focused closure is controlled schema rejection across store and all three CLI
paths for malformed observation exchange types, positive direct/discovered cache
readback, and fresh required verification/all-AC acceptance/independent final review
on identical saved content. Native preflight/reservation precedes owner resumption.
After reservation remediation0/finalreview1 remain; later outcomes use excluded
ledger after documentation freezes. No further grant is inferred.


## A103-2 consolidated Search-provider input evidence

2026-10-15 independent /root/issue103_exchange_review returned final review FAIL
on verified/accepted content
`7549e3789c22f472e1a6ade5f23c4c517b37754fa04e5b2237fb99f94156da42`.
The cache exchange type guard is correct and previous full1576/48, focused43,
all required gates and fresh verification remain actual passes.

B103-SEARCH-INPUT-SHAPE, INV103-1/3 / AC103-3/4: provider ETF suggestion VWCE.DE
with exchange[] raises TypeError at service.py595; live-search CLI exits without
controlled JSON. Provider Search rows[[]] raises AttributeError at direct_lookup
service.py613; exact-lookup CLI likewise lacks controlled rejection. Reviewer
confirmed both with in-memory injected provider/CliRunner without writes.
The Yahoo adapter returns list(result.quotes) unfiltered at yahoo.py72, so malformed
rows are not excluded by the actual adapter boundary. This is material evidence
for Search input handling, not a failure of the now-repaired cache string guard.

Reviewer consolidated every production EXCHANGE_MAP membership: source observation
121 and cache validation189 guarded; suggestions595 unguarded. Refresh787 already
rejects non-record/wrong-exchange rows; exact lookup rejects a record exchange[]
through observation, but accesses .get on non-record rows first. The existing handoff
requires attributable allowed-region suggestions/exact ETF verification with explicit
rejection, preserving bounded non-exhaustive Search and ambiguity semantics.

Primary accountable decision: explicit stop. Record FAIL/nativeblocker, preserve
cache exchange repair as WIP on original PR108. Remaining remediation0/finalreview0/
designreset0. No blind acceptance from passing cache tests/full suites, automatic
count grant, repeated assertion without evidence, silent exception suppression,
delivery or merge. Directory power-loss guarantee remains outside frozen scope.

One bounded next closure covers the Search-provider boundary: validate response
row shape and exchange type before both suggestion and exact-lookup consumers,
inspect equivalent access preconditions under existing Search limits, and retain
focused malformed-provider response/row/field tests through live-search/exact-lookup
CLI plus valid source positives. Preserve exact-symbol ambiguity/rejection and
non-exhaustive capped suggestions; no new interface/schema/financial behavior.
Fresh required verification, all-AC acceptance and independent final review must
bind identical corrected content. Existing implementation owner remains accountable.
Distinct user authority for one remediation and one final review is required;
none is inferred. Later outcomes use excluded ledger; this WIP documentation
revision is not certified by the previous review.


## A103-2 Search input repair authorization

2026-10-15 latest user `approve` accepts one remediation and one independent final
review for B103-SEARCH-INPUT-SHAPE, after WIP619e09d. Native continuation adds
exactly those counts, clears only current certification and preserves every
prior outcome/reservation/delivery binding. Existing approved owner
/root/issue103_container_owner remains implementation_worker/gpt-6-sol/medium.

Primary decision resumes one bounded Search-provider input repair. Validate
response/row and exchange field shapes before both live suggestion and exact
lookup consumers, checking access preconditions under the already frozen Search
limits. Add provider response/row/field malformed-type tests through service and
CLI, plus valid source positives, explicit exact-symbol ambiguity/rejection,
non-exhaustive capped suggestions and unchanged local pointer where applicable.
Consolidate this boundary rather than just the first crash. Preserve all prior
cache/lock/read/counter repairs and existing accepted interfaces. No blanket
programmer exception suppression, schema/financial/persistence redesign, directory
power-loss guarantee, merge or successor work is authorized.

Focused closure is controlled rejection/error for malformed Search inputs across
both consumers without raw TypeError/AttributeError, preserving valid semantics;
then full required verification, all-AC acceptance and independent final review
bind identical corrected content. Native preflight/reservation precedes resumption.
After reservation remediation0/finalreview1 remain; no further grant is inferred.
Reviewable docs freeze before certification; later outcomes use excluded ledger.
