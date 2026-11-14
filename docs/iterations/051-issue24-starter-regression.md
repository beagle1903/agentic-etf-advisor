# Issue 24: synthetic starter regression baseline

## Authorized owner and outcome

Ordinary evaluation work, authorized by the user's `approved` on 14 November
2026 and [Issue 24 agreement](https://github.com/beagle1903/agentic-etf-advisor/issues/24#issuecomment-6880895689).
Owner and participant: `/root/starter_baseline_owner`; assignment
`implementation_worker`; activity implementation/remediation/verification;
requested preset `sol`, model `gpt-6.1-sol`, medium. Inherited full filesystem and
network access is observed; restrictions are instruction-only, without backend
model/access attestation. The coordinator owns commit/push/PR delivery.

One reviewable outcome: a separate offline synthetic starter regression report
and CLI. Keep this inseparable corpus/scorer/test slice with its owner. No new
framework or UI. ADR 0049 applies prospectively; no ledger or reservations.

## Frozen scope, contracts and expectations (before scoring)

One twenty-lead packaged starter pool in its exact source order. Every fact is
invented, including attributed Yahoo-format URLs: no real Yahoo observation is
claimed. Fixed observation/preparation 2026-11-05T12:00:00Z; check 13:00:00Z.
Snapshot version `issue24-starter-synthetic-v1`, schema 2. Sixteen growth rows
cycle Large Blend, Large Growth, Foreign Large Blend, Diversified Emerging Mkts;
four defensive rows use Intermediate Core Bond. Fee 0.1%, daily volume 200000,
reported holdings one shared SYN/Synthetic holding row at exactly 10 percentage
points, concentration 10%. Singleton listing identity only; no legal identity.

Nine cases cross conservative/income, moderate/balanced, aggressive/growth with
requested shortlist capacities 3, 5, 10. Profile horizon 12, drawdown 25%, initial
USD1000 and monthly USD250, no exclusions. Fresh construction explicitly selects
v2. Three additional moderate/capacity-five cases: all four defensive category
fields missing; unsupported weapons exclusion; SPY missing holding symbol and
VOO holdings not reported with separately available concentration retained.

The expected vectors are independently calculated from policy and construction
contracts (not captured from the scored implementation). Policy targets are
2000/8000, 5750/4250, 9500/500 growth/defensive bps. V2 seeds the largest feasible
count pair closest to these targets; category-first source order chooses the
first distinct growth categories and earliest bonds. Construction retains source
order and the first feasible maximum-size subset. Thus capacity 3 selects
SPY/BND/AGG for conservative, SPY/IVV/BND otherwise. Capacity 5 selects
SPY/BND/AGG/SCHZ/SPAB for conservative, SPY/IVV/VOO/BND/AGG for moderate,
SPY/IVV/VOO/VTI/BND for aggressive. Capacity 10 selects SPY/IVV/VOO/VTI/BND
for all three profiles. Equal sleeve division gives integer quotient/remainder
bps in source order. Cash uses per-sleeve largest remainder, source-order ties.
The committed corpus freezes every exact document ID, bps and both cash vectors.
Fixture identity is frozen before the scorer first runs; hashes recorded below.
Missing defensive categories yields construction blocked missing_sleeve_coverage;
unsupported exclusion yields blocked insufficient_eligible_candidates. Holdings
limitations do not alter selection; missing symbols/not-reported lists stay
unavailable, never zero. Every available shared-row diagnostic is partial with
10/10 row sums and 10 percentage points overlap, not complete exposure.

## Invariants, interfaces, acceptance and verification

- I24-1: Production financial, identity, screening, construction, state/replay,
  provider and store contracts unchanged. JSON/state impact: none.
- I24-2: Expectations independent of actual results; all twelve cases score
  exact stage/status/reason and ready document/weight/cash vectors.
- I24-3: Report distinct requested/collected/screened/eligible/excluded/
  shortlisted/selected counts and reasons. Pair diagnostics retain each row sum,
  exact percentage-point units, provenance, saved check time and limitations.
- I24-4: Identical serialized reports on repeat runs; no live/source/provider,
  registry/publication/database/store operations or wall-clock renewal.
- I24-5: Existing Issue99/retrieval/explanation baselines and historical saved-v1
  goldens unchanged. Existing starter tests already cover individual v2 shortlist,
  exact cash, saved v1 and reload; this slice adds cross-case reporting/scoring.
- AC24-B1: Twelve named fixed cases pass deterministic agreement only.
- AC24-B2: Visible failures and CLI nonzero for altered selection, sum-preserving
  wrong weights/cash, ready/blocked reason mismatch, unavailable-to-zero substitution.
- AC24-B3: Meaningful forbidden-call tests enforce offline replay and repeat bytes.
- AC24-B4: Focused and full service-free tests, lint/format/mypy/build/Compose and
  role validation pass; durable evidence records actual outcomes and limitations.

Risks: synthetic evidence proves no suitability, return, live coverage or independent
risk improvement. No aggregate weighted/portfolio overlap or quality threshold.
If a financial/identity expectation cannot follow the existing contract, stop the
affected case and ask the coordinator; do not change that contract. Frozen reasons
must not be silently adapted to observed results. Root audits historical bytes.

## Pre-score fixture freeze

Before the first scored replay, corpus bytes SHA-256:
`c91ba0827aa34baf7aab50b2f7882248c0bb712bdf2f17ee385f4f4c97a9c079`;
canonical corpus SHA-256:
`016a64e11db61e62a5d5201cf516963a5a0be82f7a85f78ea813db31991a71c0`.
Fixture assembly used the existing synthetic record builder, exact prescribed
field changes and independently written integer vectors; it never invoked
screening, construction or holdings diagnostics. It stored exact selected IDs
using each fixture snapshot digest before running the evaluator.

## Implementation and verification evidence

The first full twelve-case scoring run passed with zero mismatches; no frozen
expectation or fixture byte changed. The CLI is `uv run --frozen etf-advisor
evaluate-starter`. It emits one JSON report, returns zero for complete agreement
and nonzero with case/field mismatches for disagreement. `requested` means the
20-member full pool; `shortlist_capacity` separately records 3/5/10. Source
outcomes, screening rules, construction exclusions and shortlist dispositions
retain their distinct reasons. All twelve frozen inputs have ready evidence;
expected blockers are construction-stage outcomes. Reported stage reads actual
evidence status before labeling construction.

The report reuses the existing pure selected-ID pair diagnostic, including its
saved check time, per-side row sums and provenance. It adds no aggregate metric.
Two detached full-matrix runs are compared byte-for-byte with source collection,
provider and all store/registry constructors, preparation/artifact-file lookup,
network connection, filesystem reads/writes and application clock hooks forbidden.

Focused tests cover changed expected selection, exact reason/status disagreement,
sum-preserving weight/initial/monthly cash corruption, unavailable-to-zero and
actual construction/diagnostic output corruption through the real CLI. The first
focused pytest attempt was intentionally stopped while reducing redundant full
matrix reruns in single-case mutation checks; it is not a completed passing run.
The first lint attempt found formatting/one long string; those were corrected.
Mypy (70 source files), model-preset validation, build and Compose config initially
passed. Final focused/full and post-change static results are recorded below.
No optional real-store gate applies: research serialization, retrieval,
screening and publication runtime contracts are unchanged.

Final focused command `uv run --frozen pytest tests/test_starter_evaluation.py
-o addopts='' -q` passed **15 tests in 208.17 seconds**. The real CLI completed
with exit 0: **12 cases agree**, 10 ready and two expected construction blockers.
The unavailable/ambiguous case retains three available and seven unavailable
selected pairs. Ignored `.artifacts/starter-report.json` (1,960,078 bytes) has
SHA-256 `032b9a3957dfff49d22ef5087734f4631bb3a8674abfdb37e2b59a515579f8eb`;
its command and exit are in `.artifacts/starter-report-command.txt`.

The first full frozen suite had **1 failed, 1,741 passed, 71 skipped in 708.66
seconds**. Its sole failure was the unchanged existing dashboard lifecycle AppTest
exceeding its existing ten-second `app.run` limit. That run overlapped the focused
suite and CLI initially. An unchanged isolated retry also timed out (78.22 seconds
total); no timeout, test, fixture or production change was made. A separate unrelated
pytest process was observed outside this worktree and left untouched. Contention
is plausible, not demonstrated causation. A bounded exact-base comparison extracted
511d26e src/tests only under ignored `.artifacts/starter-base`, proved its import
path and passed that same AppTest in 6.41 seconds. A second unchanged current-source
isolated run then passed in 7.84 seconds. These are transient timeout observations,
not a demonstrated product contract defect or a claimed baseline failure. The final
full rerun follows serially below with source/test files held unchanged.

Coordinator preservation audit: four pre-existing analysis/retrieval/explanation/
metric baseline JSONs and `tests/test_issue141_starter.py` match their pre-edit
SHA-256 values. All twelve historical ignored saved-v1 golden files in the original
Issue 141 worktree also match pre-edit hashes. This is byte preservation evidence,
not a new claim of historical saved-v1 acceptance or Issue 117/123 completion.
Post-change mypy passed (70 source files), Ruff lint/format passed (280 files), and
diff checks passed. Build, preset validation and Compose config passed; the wheel
contains both the new evaluator and its separate frozen JSON corpus.

The final serial command `uv run --frozen pytest -o addopts='' -q` passed
**1,742 tests, 71 optional skips in 497.32 seconds (8:17)**, exit 0. The exact
unchanged dashboard AppTest that timed out previously passed in this complete
run. Log: ignored `.artifacts/starter-full-serial.log`. No source/test file changed
during this run; the only later edit is this verification record. The earlier
failed and incomplete attempts remain documented above and are not counted as
passing evidence. Verification completed on 14 November 2026 UTC under Windows,
Python 3.13.14, locked dependencies with the dashboard extra (Streamlit 1.62.0).

Owner self-review found no unresolved scope/contract defect: production modules
are unchanged except the CLI import/command, the new evaluator calls existing
pure interfaces, all expectations retain their pre-score hash, and diagnostics
remain separate from selection/weights/cash. The coordinator's read-only content
review also reported no actionable defect. AC24-B1 through B4 pass locally.
There is no live data, provider, database, durable restoration, suitability,
financial quality or return claim. Historical saved-v1 preservation is the
separate byte audit above. Commit, push, PR and CI publication remain with the
coordinator; local passing checks do not claim merge or parent-issue completion.

## Delivery content identity

Tested implementation commit: `85cf750913977403b902cefa2067363a43fd8ce5`.
The pre-score raw corpus hash recorded above identifies the local CRLF bytes:
193,751 bytes, SHA-256
`c91ba0827aa34baf7aab50b2f7882248c0bb712bdf2f17ee385f4f4c97a9c079`.
Git normalized only this new corpus's line endings for the committed LF blob:
188,831 bytes, SHA-256
`4b183c14498ca4458e7ca5c6f0e3b77d31f52b9bb894126608696eacacc85fa3`.
The coordinator verified that replacing local CRLF with LF exactly reproduces
that committed blob. Canonical JSON SHA-256 remains
`016a64e11db61e62a5d5201cf516963a5a0be82f7a85f78ea813db31991a71c0`;
no JSON value or expectation changed. This final evidence-only documentation
update leaves tested runtime and corpus semantics unchanged and adds no new
acceptance claim.
