# Issue153: input-bound starter subset selection

## Approved design capsule (recorded before runtime edits)

DESIGN_READY. Authority: user `continue` and option1 (sleeve fund-count balance,
then category coverage), [coordinator agreement](https://github.com/beagle1903/agentic-etf-advisor/issues/153#issuecomment-6894043869).
Consequential financial and replay change: separate `/root/issue153_design`
(design_architect, astra/high) advice and independent
`/root/issue153_design_challenge` (sol/medium) PASS preceded coordinator approval.
Owner/participant `/root/issue153_owner`, implementation_worker,
implementation/remediation/verification, requested sol / gpt-6.1-sol / medium.
Coordinator `/root` owns commit/push/PR. Observed inherited unrestricted filesystem
and network, approval never; instruction-only restrictions, no backend model or
access attestation. No delegation. ADR0049/0051 apply, without prospective ledgers.

One inseparable outcome: version the bounded starter subset objective and preserve
historical inputs. Keep shortlist-v2 unchanged. Optional construction policy
`starter_subset_algorithm="sleeve-count-category-v1"` requires starter research
and explicit `starter_shortlist_algorithm="sleeve-category-feasible-v2"`.
Absent omits exactly in Python/JSON and keeps historical first-feasible behavior;
null/unknown/nonstarter/without-v2 reject. Fresh roots pin both before sealing;
restore, retry, receipt reuse and children retain presence/value. Feedback cannot
mention either marker, including same value or clearing it. Input policy chooses
computation; reports cannot choose validators. Add `subset_algorithm` only to new
reports, retaining shortlist `algorithm` and input digest binding.

For feasible subsets of at most ten shortlisted candidates minimize exactly
`(-position_count, abs(10000*growth_count-position_count*growth_target_bps),
-distinct_normalized_source_categories, original_evidence_index_tuple)`.
No extra growth-count preference. Preserve source-order presentation, identity
and source/category checks, all constraints/blocker precedence, exact sleeve bps
and cent allocation. No graph key, operation stage, adapter, clock or source-state
change. Interfaces: construction policy/report, revision validation and fresh-root
sealing. JSON impact: optional policy and report fields only, absent bytes preserved.

Frozen invariants: I153-1 feasibility/exact arithmetic; I153-2 exact objective only
for new version; I153-3 historical absence exact; I153-4 input-bound fresh activation;
I153-5 deterministic JSON and side-effect boundaries; I153-6 honest source/category
and risk limits. AC153-1 independent reproduced matrices and cents; AC153-2 objective,
constraint conflicts/ties/blockers; AC153-3 separate new synthetic cases and unchanged
old corpus; AC153-4 fresh/replay/retry/revision/tamper; AC153-5 byte-repeat offline,
forbid live/provider/artifact lookup/clock; AC153-6 unchanged analysis/starter baselines,
standard gates and subsequent independent code review.

Independent reproduction: SPY/IVV/VOO/VTI Large Blend, QQQ Large Growth,
VEA Foreign Large Blend, VWO Diversified Emerging Mkts, BND/AGG/SPAB Intermediate
Core Bond, in that order. Cap5/10 conservative selects SPY1000 QQQ1000 BND2667
AGG2667 SPAB2666; moderate SPY1917 QQQ1917 VEA1916 BND2125 AGG2125;
aggressive SPY/QQQ/VEA/VWO2375 each BND500. Cap3 conservative SPY2000 BND4000
AGG4000; moderate SPY2875 QQQ2875 BND4250; aggressive SPY4750 QQQ4750 BND500.
Initial USD1000/monthly USD250 exact vectors are independently specified in tests.
The old synthetic corpus has different invented categories and four bonds; never
rewrite its input/expected bytes. New expectations for that input are separate tests.

Docs: new accepted ADR0052, current system, starter guide and this iteration.
Risks/triggers: material financial/replay ambiguity returns to coordinator/design;
same-scope fixes remain owner. Category diversity does not prove independent risk,
legal identity, suitability, returns or benchmark exposure limits. No generic/full-pool
optimizer, hard exposure veto, source collection, registry/store/publication/migration,
live run, trade or financial-system write; other Issue151 concerns remain separate.
Verification: meaningful focused tests, unchanged evaluate-analysis/evaluate-starter,
then serial full pytest with locked dev/dashboard installation in this checkout;
preset validator, Ruff lint/format, mypy, build, Compose config and diff checks.
Actual failures and limitations will be retained below.

## Implementation and verification evidence

Implemented the optional selector and omission/null/dependency validation in
construction policy, blocked selector feedback, pinned both fresh-root selectors
before sealing, and added the exact bounded feasible-subset objective. All existing
feasibility gates and cash arithmetic remain shared. Reports gain only the selected
subset marker. Existing saved-v1 fixture checks explicitly remove both fresh markers
before asserting their unchanged historical hashes; no expected hash or baseline
corpus has changed. New tests independently specify both nine-case matrices.

Initial starter/construction focused run: **55 passed in 74.70s**.
The first new test run had **20 passed, one failed** because its zero-target assertion
incorrectly assumed no zero-weight growth position could appear when minimum weight
is explicitly zero. Existing maximum-cardinality semantics permit that position;
the assertion now checks exact zero growth weight and preserved cardinality.
The next new run had **22 passed, one failed** because synthetic retry used the default
candidate limit5 while returning embedded limit10 evidence. Matching the explicitly
requested limit fixed the test fixture. The resulting new suite passed **23 tests
in 17.53s**, including exact vectors/cents and failed-operation retry/receipt reuse.
No production rule changed in response to either test-fixture failure.

An expanded focused run started with a new forbidden-call test import typo; it was
corrected while that already-collected run continued. Its complete outcome and
subsequent corrected verification are recorded below. Initial lint attempts found
formatting/import ordering issues; corrected. Current Ruff lint/format (284 files),
mypy (70 source files), preset validation, build, Compose config and diff checks pass.
The full evaluation directory is byte-unchanged against the base in Git. The
subsequent CLI baseline and final serial full-suite outcomes are recorded below.

Owner self-review: objective tuple has no extra growth tie preference; enumeration
stops only after considering all feasible candidates at the greatest feasible size.
Source-order filtering and exact existing integer weights/cents remain intact.
Absent policy serialization and old first-feasible branch remain exact. Fresh-root
activation runs only before initial input sealing; saved execution never enters it.
Typed policy context and feedback validation reject unsupported selector changes.
No live source/provider/external store/database action, migration, trade or financial write ran.
The synthetic tests establish deterministic agreement, not investment quality,
legal identity, independent risk or live/durable-store coverage. Independent review
and coordinator delivery were separate subsequent gates; the review result follows below.

Corrected focused new-selector/starter suite: **50 passed in 72.63s**.
Expanded focused revision/starter/new-selector run: **187 passed, one failed in
138.54s**; the sole failure was the forbidden-call test's nonexistent preparation
module import described above. Corrected affected coverage passed in the 50-test run.
`evaluate-analysis` and `evaluate-starter` both exited 0 with `passed=true`.
Starter's 12 cases have zero mismatches, and the complete 1,960,078-byte report SHA-256
is `032b9a3957dfff49d22ef5087734f4631bb3a8674abfdb37e2b59a515579f8eb`,
exactly the prior iteration051 report identity. No historical corpus/runtime
expectation was rewritten.

First serial full run: **1,764 passed, 71 skipped, one failed in 460.97s**.
The concrete failure is unchanged
`test_dashboard_revision_controls.py::test_streamlit_policy_review_renders_revision_lifecycle_and_typed_controls`
at `app.run(timeout=10)`: `RuntimeError: AppTest script run timed out after 10(s)`.
All other tests passed. This is a timeout observation, with no asserted cause.
After preserving that run, owner self-review tightened the existing tie test to
assign a distinct bonds-first original evidence order/indexes and explicitly prove
the lower growth count wins an exact tie. This changes only the test, within the
frozen no-hidden-growth-preference criterion. That test and the exact unchanged
AppTest then passed together: **2 passed in 8.91s**. No AppTest timeout, fixture,
expectation or production implementation changed. Ruff lint/format passed again.
The final complete serial suite then ran against frozen source/test files.

The optional real-store gate in CONTRIBUTING is not triggered: research snapshot
serialization, numeric proofs, evidence/retrieval, screening and publication/store
contracts are unchanged. This slice changes pure downstream construction policy
and its existing input-bound revision serialization, tested offline. No real-store,
live-source or durable-process-restart acceptance is claimed.

Final serial complete suite: **1,765 passed, 71 optional skips in 439.46s
(7:19), exit 0**. The unchanged AppTest that timed out in the first full run
passed in this complete run. Log: ignored `.artifacts/issue153-full-final.log`.
No source/test file changed during that run. The preceding failed and intermediate
attempts remain recorded above, with no claim that they passed. Locked default/dev
and dashboard dependencies ran in this isolated Windows/Python 3.13.14 checkout.

Local AC153-1 through AC153-5 and the local gates in AC153-6 pass. Owner self-review
found no unresolved financial/replay/scope defect. Both source-category matrices,
exact bps/cents, maximum cardinality, count/category/order priorities, source-order
ties in both directions, feasible constraint alternatives, zero-target boundary,
selector validation/feedback immutability, fresh sealing, offline restore/retry and
child preservation, and input/report/sum-preserving output tampering are covered.
Existing eligibility, blockers, identity guards and historical cases remain shared.
The unchanged historical starter evaluator's byte-identical report and saved-v1
hash assertions preserve historical behavior independently of the new cases.
Independent code review by `/root/issue153_review` (code_reviewer assignment,
requested sol / gpt-6.1-sol / medium, read-only) passed after owner verification.
The reviewer inspected all nine changed/new files, surrounding validation,
historical goldens, tests and verification logs, and found no concrete frozen
invariant/acceptance failure or material evidence gap. This documentation-only
closeout records that result without changing runtime, tests or their evidence.
Commit/push/PR and CI remain coordinator-owned subsequent gates; no merge or
completed CI is asserted here.
