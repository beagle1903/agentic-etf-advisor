# Issue105 coordinator arbitration A105-1

- Opened: 2026-10-23, coordinator /root; human approved Issue105 start in this
  chat. No new scope, slot, exception or financial-write authority.
- Frozen capsule: issue-105-catalogue-selection/gen1,
  38a418bebc1692e4ee3f7ca31de84c5fbf387b2ed1f79093aa1be74018261798.
  Initial handoff docs/iterations/028-issue105-catalogue-design.md SHA256
  9ceca3a7d566ad3684139c3bf0ba659967a4c82e5be467d260abccaccf27114b.
- Trigger: separate independent challenge found the architect's job-start
  ingestion coordinate conflicts with frozen truthful source/persistence rules.
  Substantive architect answer proposed immutable job-start coordinates; reviewer
  supplied a concrete later-batch counterexample. Hold dependent implementation.
- Current phase: challenge concluded FAIL; no active implementation. Before reset:
  implementation1/initial-review1/remediation1/final-review1/design-reset1 remain.
  Dispatch hold is not offline coordination_pause; all elapsed audit time retained.

| Role/session | Frozen IDs | Scenario/readings | Expected/actual | Evidence/classification |
| --- | --- | --- | --- | --- |
| architect /root/issue105_design | INV105-1/2/4, AC105-3/5 | Common field ingested_at fixed at job creation, successful records frozen across later batches | Snapshot coordinates consistent but late observations may postdate claimed ingestion | Handoff sections3/5; consequential contract ambiguity |
| independent reviewer /root/issue105_challenge | same | Begin Oct23 08:00, collect Oct24 08:00 from Oct24 07:59 source | Truthful destination ingestion must follow collection, actual proposed timestamp Oct23 | ADR0008 truthful timestamps; Issue104 design destination-ingestion definition; FAIL |

Primary decision: **contract clarification**, separate read-only architect using
the one available design_reset. Preserve frozen scope, invariants/ACs/non-goals,
owner/model/effort and all successful source facts. Architect must distinguish
job creation from actual destination ingestion and freeze precisely when/how
canonical snapshot coordinates become fixed; address crash/retry/cache/freshness
and original source observations without modifying canonical retained snapshots.

Rejected: accept inaccurate ingestion; silently refresh source time; coordinator
invent consequential remedy; begin implementation against ambiguous text; widen
scope, change owner or grant another reset. No role disagreement beyond the stated
conflict; unanimous agreement is not required. Initial challenge remains failed.

Closure: architect returns exact coordinate lifecycle and focused Oct23/24,
retry/crash/freshness tests against INV105-1/2/4 AC105-3/5; coordinator persists
amended handoff and current generation binding; fresh independent challenge passes
that same content; coordinator explicitly approves before implementation.
Only then episode closes; this is not ticket acceptance. Further consequential
ambiguity/exhausted reset stops for explicit decision. Later outcome belongs in
excluded ticket-ledger evidence; edit this record before certification only.

## Closure before implementation

Fresh separate /root/issue105_design_reset returned DESIGN_READY with truthful
post-read intermediate cache times and one complete detached canonical T_final
committed atomically; precommit retry versus committed-lost-ack recovery is exact.
Source tuples remain immutable, finalized payload never rebuilt/rebound. Complete
amended handoff SHA256 b65c7dd9ad694bf81d5c364f6cb87a6094fe9e976f9389c757ca7c50a7b6d261
is bound to generation2 capsule
c1aed72e5deb532209ecc230180ddecc03f42df1b025ef7960a99592d7396072.
Fresh independent /root/issue105_challenge2 code_reviewer/gpt-6-sol/high PASS
confirmed exact document binding and the focused lifecycle/test closure without
other concrete frozen-contract failure. Coordinator approved that same gen2 before
reserving /root/issue105_owner implementation. Episode closed; sole reset consumed.
Original failed challenge retained. This closes only A105-1, not implementation,
acceptance, verification, independent code review or delivery. Native ledger holds
exact timestamps/outcomes and later interruption/resume audit evidence.

## A105-2: alternative listings versus final portfolio positions

Opened 2026-10-23 before certification, /root. Human start/continue authority
unchanged. Frozen gen2 capsule c1aed72e5deb532209ecc230180ddecc03f42df1b025ef7960a99592d7396072,
handoff b65c7dd9ad694bf81d5c364f6cb87a6094fe9e976f9389c757ca7c50a7b6d261.
Trigger: owner reported self-review remedy stopping shortlist at one listing per
economic group, contrary section7 explicit second pass retaining alternatives.
Coordinator interrupted actual owner and recorded truthful pause, same consumed
implementation reservation. No extra phase/slot granted; implementation0 new starts,
initial-review1/remediation1/final-review1 remain, design-reset0. Audit time retained;
dispatch hold alone is not coordination_pause. Existing running test commands are
read-only; their results must be accounted for, not reused against later changes.

| Role/session | Frozen IDs | Expected/actual/evidence | Classification |
| --- | --- | --- | --- |
| architect gen2 | INV105-3/4 AC105-4/5 | Section7 step6: after unrepresented groups exhausted, fill remaining shortlist capacity with alternative listings; unchanged constructor admits at most one final position/group | Clear frozen contract |
| owner /root/issue105_owner | same | Reported spare-slot alternatives as self-review issue; _catalogue_shortlist breaks when no unrepresented group, and test_shared_economic_group_never_takes_multiple_shortlist_slots asserts1 | Demonstrated frozen-algorithm deviation, not portfolio duplicate defect |

Primary decision: **narrow repair** retained with approved owner inside same active
implementation pass. Restore exact section7 second pass; replace conflicting test
with preservation of alternatives in shortlist plus one-per-group final portfolio.
At most ten shortlist rows/enumeration input remains invariant. Add a feasible
alternative-representative fixture where early listing alone cannot meet existing
category/sleeve constraints but an alternative can, and assert final group uniqueness.
This exercises already frozen AC105-4 alternatives, not a new acceptance criterion.

Rejected: silently revise approved algorithm; pre-collapse alternatives; waive
same-group final-position guard; request a new architect to obtain agreement with
clear text; replace owner or grant/reset slots. No designer/reviewer disagreement
other than owner's reported interpretation; independent code review still required.
No optimizer/currency preference/cap increase/Issue115 scope.

Focused closure: same owner restores two-pass algorithm and demonstrates <=10 input,
retained alternative representatives and <=1 selected position/group; rerun affected
focused tests plus full suite after final behavior change, then same-content native
verification and independent initial code review. Initial full pytest pass belongs
to earlier content; current running passes cannot certify repaired later content.
Further material evidence appends here before certification or in excluded ledger
afterward; repeated assertions refer to this decision. Episode closure is not ticket
acceptance. No implementation edits by coordinator.

Additional concrete source evidence before resume: _catalogue_shortlist reports
usable_count=len(available) after zero-target sleeve filtering. Section7 defines
usable before shortlist omission and explicitly separates zero_target_sleeve.
Owner must verify/repair that count under AC105-6/INV105-1 within same pass and
add a focused zero-target counter case where representable by current policy.
This is an existing frozen count definition, not a new criterion or policy change.

### A105-2 recurrence: preserve round-robin output order

Before certification owner reported additional self-review remedy: select by
priority, then pass membership in original classified input order. Coordinator
interrupted again, retained audit time and same paused reservation. Actual code
now builds shortlisted from eligible membership after the round-robin loop.
This changes deterministic subset tie-breaking relative to frozen section7:
"Shortlist order becomes unchanged constructor upstream order" (lines256-257).
The original architect handoff explicitly said "The resulting order becomes
upstream order for the unchanged constructor." Resulting means the algorithm's
append order, not the pre-shortlist evidence order. Legacy ordinary mode alone
preserves its earlier upstream order unchanged.

Classification: demonstrated algorithm/order deviation INV105-3/4 AC105-4/5;
same underlying shortlist-versus-constructor distinction, not new ambiguity.
Accountable revision to existing narrow-repair decision: retain selected append
order as report.shortlist_ids and enumeration input, no post-selection resort.
Keep two-pass alternatives and <=1 final group already restored. Replace the new
original-order assertion with a fixed expected round-robin sequence using
contrasting input order; prove permutation invariance and selected group uniqueness.
Existing scope/AC105-4 already requires these. Reject silently changing frozen
ordering or broad redesign; no new architect/reset/phase allowance/owner swap.
Resume same owner after this clear-contract explanation. Final focused/full gates
must bind repaired content; stale interrupted test runs cannot certify it.

### A105-2 focused closure before certification

Same approved owner restored the exact two-pass append order and pre-shortlist
usable count. Fixed four-listing regression expects E098.DE,U061,U076,U011;
it retains both alternatives, permits the defensive representative to make a
ready portfolio, and checks final-group uniqueness and permutation invariance.
AppTest separately varies provider document-map insertion order. Final Issue105
focused9/9 and broader Issue104/dashboard/revision/evidence/construction passed;
final complete offline pytest reached100% exit0 with40 skips. Ruff/format/mypy,
build/workflow/Compose/diff gates passed; implementation iteration records outcomes.
Owner returned quiescent files. Earlier interrupted runs are not final evidence.
Episode's focused repair closure is satisfied; next permitted gates are native
same-content verification/acceptance and independent initial review. This is not
ticket delivery or an independent-review result. Later outcomes go in excluded
ticket evidence without changing this record after certification.

## A105-3: frozen acceptance evidence is incomplete

Coordinator /root, opened2026-10-23 after content-bound verification FAIL at
6567f2fdbc7b47bdedb5e18c79dfa1acfef8c9e34d7d3bd7126971dedd06d87a.
Frozen gen2 capsule/handoff unchanged. Owner had reported full tests/ready;
verification rechecked frozen scenarios and found concrete missing assertions.
No implementation or review can be accepted from passing unrelated/partial cases.
No active phase; verification ended FAIL and B105-AC-EVIDENCE blocks acceptance.
Remaining before repair: remediation1, final-review1, initial-review1; no new
implementation/design-reset starts. Repair uses existing single remediation,
after which native review routing requires final review. No extension/reset.
Audit continues; hold is not an offline coordination pause.

| Role/session | Frozen IDs | Expected versus actual | Classification |
| --- | --- | --- | --- |
| owner verification /root/issue105_owner | AC105-6 INV105-1 | Every displayed coverage/job count, direct overlap/provider/unsupported limits and unknown/omission totals asserted; actual tests check requested/cached/evidence and subset of scope counts | Material acceptance uncertainty/evidence gap, not proof of product defect |
| same | AC105-3/4/5 INV105-2/3/5 | Frozen request-specific started/result/staging/activation crash/tamper, exclusion and bounded-infeasible scenarios measured; some rely only on generic protocol tests/code | Same-scope evidence gap |

Primary decision: **narrow repair**, same approved implementation_worker/
gpt-6-sol/medium owner, one existing remediation reservation. Add a clear
scenario-to-test map against the complete frozen handoff and explicit bounded
tests for missing coverage/counts, job states, failures/crashes/retry/uncertainty,
request-specific tampering and constraints. Existing generic tests may be cited
only when exact applicability is demonstrated; do not merely duplicate tests.
Any actual same-scope defect exposed must be repaired and verified. No new
financial policy/selection algorithm, weakening expectations or live-coverage claim.

Reject: call missing evidence a product defect, waive frozen tests because full
pytest passes, approve partial uncertainty, silently shrink ACs, expand beyond
handoff, replace owner or grant phases. No unresolved contract interpretation;
separate architect would consume an unavailable reset and is not a remedy for
missing tests. No independent implementation review has been consumed.

Focused closure: explicit verifiable AC105-1..6 scenario map plus passing tests
covering every previously omitted frozen material case/count; source behavior
unchanged or focused repairs documented with negative/positive regression. Complete
required gates on final content, resolve B105-AC-EVIDENCE after successful
remediation, then fresh content-bound verification/acceptance and independent
final review. Failed final review stops for explicit finite human decision.
Initial verification stays failed. Later evidence updates ledger after final
certification; no new allowance or delivery authority is created by this episode.

### A105-3 repair closure before fresh certification

Same owner returned REMEDIATION PASS with complete AC105-1..6 test map in the
implementation note. Actual AppTest asserts scope/provider/unsupported/job and
selection counters, overlap/unknown/omission totals. Request-specific crash,
publication uncertainty, tamper, exclusion/contradiction/infeasible-shortlist,
transport/reference/BND bounds are explicitly measured or mapped to exact shared
protocol coverage. Tests exposed/repaired truthful scope/UI counters, 101-ID
over-limit reporting, unsupported research symbols, and pre-rebinding cache
member/coordinate validation. Frozen shortlist/FX/legacy contracts unchanged.
Final broad focused regression suite passed; complete offline pytest100% exit0,
40skips ran on the same product source. Only later addition was two BND test
cases; broad focused suite passed again after them. This exact combined evidence
is recorded without claiming the earlier full command included those new cases.
Ruff/format/mypy/build/workflow/Compose/diff passed; files quiescent. This closes
the focused repair episode, not acceptance/delivery. B105-AC-EVIDENCE may resolve
after successful remediation event; fresh native verification and independent
final review remain mandatory. Sole remediation consumed, no new counts granted.
