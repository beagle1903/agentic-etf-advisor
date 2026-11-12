# Issue 115: selected-subset FX staging

- Status: approved design; implementation in progress, 12 November 2026.
- Authorization: user approved Issue 115 implementation. Separate read-only `design_architect` (`gpt-6-astra`, high) returned DESIGN_READY; coordinator approved in [Issue 115](https://github.com/beagle1903/agentic-etf-advisor/issues/115#issuecomment-6820935128).
- Owner: `implementation_worker` (`gpt-6-sol`, medium). Consequential financial and replay contract; separate architect handoff completed. Independent review follows implementation.

## Frozen scope and invariants

I115-1: A single pure selection prefix shared by retrieval and construction validates the actual profile, evidence, screening and construction policies; applies the exact sleeve, category, economic-group, catalogue shortlist, subset, weights and base-cash rules; returns the selected positions or the same construction blocker. Final catalogue reports use final FX evidence.

I115-2: The existing retrieval prepare/execute receipt and one-use permit alone authorize side effects. Collect once and capture check time once. After evidence screening and pure selection, skip ECB for blocked or base-only selections. A selected foreign position requires at most one injected ECB fetch per fresh authorized attempt, including zero cash. Missing, unavailable, stale and future observations retain typed reasons; retrieval succeeds and construction blocks when FX cannot support selection. Provider endpoint, bounds, freshness and exact rounding remain unchanged.

I115-3: Fresh evidence-enabled `us-eu-v1` roots pin `fx_staging: selected-subset-v1` in revision inputs and evidence, including empty or blocked evidence. Historical absent-marker reviews keep exact legacy raw-pool behavior and serialized identity through retry, refresh and children. Null, unknown, mixed, lost or switched markers fail. Legacy US, starter and policy-only states omit the marker. Production hybrid and managed entry points use the marked path with actual selected policies and honest screening.

I115-4: Marked retrieval input binds the full stored profile, candidate limit, marker, and exact screening/construction policies. A stored draft policy must equal deterministic policy calculation before a selected FX call. The output binds final evidence, FX disposition, check time and provenance. Replay, audit, dashboard and review validate marker semantics against the original producing revision and policies, even if a changed bundle is rehashed. Existing receipt, permit and envelope safeguards remain.

I115-5: ADR 0015 routing remains. A profile/evidence refresh starts fresh collection; base change needs both cash amounts. Downstream policy changes reuse immutable evidence and check time; newly foreign selection with skipped or unavailable FX blocks offline. Saved FX remains reusable at original time. A combined evidence refresh and policy edit authorizes new retrieval. No new UI, automatic retry, graph key, profile field or operation stage.

Affected interfaces: `domain.construction`, `domain.revision`, `rag.evidence`, `graph.nodes`, `graph.workflow`, `graph.revision`, production composition/adapters and their focused tests. JSON/state impact: two optional, versioned marker fields in existing revision-input and evidence structures; legacy absent serialization is exact. No new external persistence schema or graph key.

## Acceptance and verification

AC115-1: zero ECB calls for canonical screening, group, category, zero-sleeve, cap, shortlist and blocked-preselection cases.
AC115-2: one call in either currency direction and zero cash, independent expected IDs, bps and cash, nondefault policies, rate/failure/stale/future boundaries and exact rounding; hybrid and managed graph paths.
AC115-3: failed or ambiguous retry and succeeded reuse; far-future offline restore without adapters; policy-bound digests; rehashed semantic tamper rejection.
AC115-4: base-to-foreign child blocks offline without FX; foreign-to-base and saved-FX children preserve artifact/check time; mixed refresh and base change use fresh retrieval.
AC115-5: exact golden old US/EU receipts and digests, unused historical FX, old child/retry/refresh; US, starter and catalogue unchanged.

Run focused tests, full service-free suite, lint/format/mypy/build/role validator/Compose config, and opt-in real-store suite with project/volume cleanup. Self-review focuses on legacy bytes, original-revision binding, one-use permits, typed FX reasons and source metadata. No live source call, publication, external financial write or trade is authorized.

Risks: a selection approximation could change financial outcomes; a marker downgrade could bypass replay semantics; a policy edit could accidentally cause network I/O. Escalate contract ambiguity or out-of-scope behavior to the coordinator. Historical ledgers are audit evidence under ADR 0049, not a prospective gate.

## Implementation and self-review

The normal hybrid entry point uses default policies for fresh plain US/EU retrieval;
the managed graph supplies its stored actual policies through `retrieve_selected`.
Only an unmarked saved US/EU graph calls `retrieve_legacy`, retaining raw-pool FX.
The selection callback invokes the same constructor prefix used by final
construction and does not use a fabricated rate. The existing prepared and
one-use retrieval operation owns the only possible ECB call. A required provider
return of `missing/not_requested` is rejected as a usable rate and recorded as
`source_unavailable`; the selected foreign construction remains `fx_missing`.

Self-review checked the direct and managed entry points, legacy serializer and
digest branches, original producing-revision policy binding, blocked and ready
evidence marker validation, downstream child reuse, provider failure and
source observation provenance. The selected-prefix helper returns before the
constructor consumes FX, then final construction recomputes the catalogue
report and draft using the final evidence. This preserves the existing
financial enumerator, weight and cash allocation logic rather than adding a
second predictor.

## Verification evidence

The initial 16 focused Issue 115 cases cover zero-cash foreign selection in both
base-currency directions, a nondefault
base-only subset, zero-call screening, group, category, position-cap and
40-listing catalogue-shortlist omissions, direct hybrid
and explicit legacy routes, provider unavailable and invalid not-requested
returns, downstream policy revision without network, rehashed semantic FX
tampering, exact failed/ambiguous retry, and frozen historical absent-marker
evidence/input/receipt digests. The old synthetic US/EU and curator retrievers
were updated to implement version-aware selection and assert their pre-supplied
FX is actually required.

The initial focused checks passed: 16 Issue 115 cases, the curator offline review
regression, and the US/EU empty/invalid/stale restoration cases. Before the
last replay validation fix, the combined US/EU/revision/catalogue focus suite
passed 246 tests. Ruff format/check, mypy (69 source files), `uv build`, role
validator, Compose configuration, and `git diff --check` passed on the final
runtime source. The first full suite found one obsolete synthetic curator
adapter and was not treated as a pass; that fixture was repaired. Final full
service-free and opt-in real-store results are recorded after their rerun.

The pre-review opt-in real-store gate passed **41 tests, zero failures, errors or
skips** in 97.38 seconds using project
`etf-advisor-contract-fdaf9b09c8e8`. The coordinator captured all three
anonymous volume names and verified the project's labeled containers and
volumes plus those exact names absent after teardown at
`2026-11-12T10:41:39.7181535Z`. The host was Windows with Python 3.13.14,
Docker 29.9.3 (`linux/amd64`) and Compose 5.7.0; dependencies came from the
frozen all-extras lock. The log is ignored local evidence at
`.artifacts/issue115-verification/real-store-final.log`. This run used the
pre-review runtime source; additional test-only cases were added afterward
and passed separately without changing that source.

The pre-review service-free run, `uv run --frozen pytest -o addopts='' -q`,
passed **1,760 tests with 40 optional real-store skips** in 243.67 seconds.
It used the same pre-review runtime source as the real-store gate. The last
test-only additions were covered by the separately passing 16-case focus run.
No live ECB or Yahoo requests, source publication, saved live-review mutation,
or external financial writes were performed. The exact opt-in command was
`RUN_REAL_STORE_TESTS=1 uv run --frozen pytest -q -s -o addopts='' tests/test_real_store_integration.py`
(environment variable set and removed in PowerShell).

## Independent review and narrow repair

The independent `code_reviewer` found two concrete I115-2/I115-4 defects. First,
the marked replay validator checked skipped FX status and reason but did not
bind the canonical skipped observation time to the bundle check time. A
reviewer changed that timestamp by one day, recomputed artifact, receipt and
state hashes, and the saved state still validated. Second, selected retrieval
replaced a provider's valid typed `missing/source_unavailable` observation
with a locally synthesized one at the check time, losing the provider's
original observation timestamp. The coordinator accepted both as same-scope
defects and returned them to the approved implementation owner for repair.

The repair requires `observed_at == checked_at` whenever a marked bundle
reports `missing/not_requested`, including ready and blocked evidence.
Provider-returned valid `missing/source_unavailable` observations now retain
their original timestamp; absence, adapter exception or invalid
`missing/not_requested` still records `source_unavailable` at the check time.
Rehashed skipped-timestamp regressions cover ready and construction-blocked
saved states; an injected provider test verifies exact source-unavailable
timestamp preservation. The updated Issue 115 focus suite has **20 passing
cases**; with blocked US/EU restoration and curator regression cases, **23
focused cases passed**. Ruff check, mypy (69 source files) and `git diff
--check` passed after repair. The two broad gates above are explicitly
pre-repair evidence; final post-repair full and real-store results must be
recorded separately. No live source call or external financial write occurred.

Independent re-review by `code_reviewer` (`gpt-6-sol`, high,
`/root/issue115_review`) passed both repairs and the collateral diff with no
residual defect. Its separate focused process ended during an environment
interruption without a captured result and is not claimed as a pass.
The first post-repair broad runs were likewise interrupted before completion;
Docker became unavailable. The coordinator restarted Docker and removed only
the generated `etf-advisor-contract-39605afaa15e` project, capturing its three
anonymous volume names and verifying all project containers and those exact
volumes absent. Those interrupted runs supply no acceptance pass. Fresh broad
verification follows against the same repaired runtime source.

The completed post-repair real-store rerun passed **41 tests, zero failures,
errors or skips**, in 192.48 seconds. Project
`etf-advisor-contract-725a575d21e5` and all three captured anonymous volumes
were verified absent at `2026-11-12T17:48:36.7039734Z`. The command, frozen
dependencies and environment match the earlier run above. The complete local
log is `.artifacts/issue115-verification/real-store-delivery.log`.

The optional-enabled post-repair full run completed with **1,765 passed,
40 skipped and one failed** in 671.85 seconds. Its only failure was the
unchanged dashboard test
`test_dashboard_evidence_toggle_unlocks_explanation_in_original_order`,
which exceeded Streamlit AppTest's existing three-second timeout while the
store suite was running. That failed run remains failed. The exact case
passed in isolation (one passed in 6.03 seconds total), and the entire
dashboard module then passed **132 tests in 25.51 seconds** with no source
change. A separate frozen minimal environment matching CI verifies the
default full suite without optional-dependency timing interference.

The frozen default full suite completed successfully in the separate
`.artifacts/issue115-ci-venv` environment: **1,723 passed, 83 optional skips**
in 420.50 seconds. It used `uv sync --frozen` and
`uv run --frozen pytest -o addopts='' -q`, with `UV_PROJECT_ENVIRONMENT`
scoped to that command. The optional dashboard and store coverage above
complements these intentional dependency-based skips. No failed check was
relabeled as a pass.

Implementation commit `c5fa9d6b3c0b3bb5ff4f0b8004b1ce4470438010` contains
the same repaired runtime source tested by those focused, dashboard, default
and real-store checks. [CI run 43275792369](https://github.com/beagle1903/agentic-etf-advisor/actions/runs/43275792369)
passed locked installation, role validation, Ruff lint/format and the default
test suite on that commit. Delivery is [PR 146](https://github.com/beagle1903/agentic-etf-advisor/pull/146);
it is open for merge review and does not yet close Issue 115. The final
documentation-only evidence update changes no tested runtime or test files.

## PR 146 inherited-FX review repair

The coordinator accepted [PR review discussion](https://github.com/beagle1903/agentic-etf-advisor/pull/146#discussion_r4554365174)
as a concrete I115-4/I115-5, AC115-4 defect. A marked USD root selected
SPY/CSPX.AS/BND and saved required FX. A construction-only child reduced
the subset to base-only SPY/BND while retaining the evidence artifact. Review
incorrectly checked that inherited artifact's FX disposition against the
child's policy and returned `revision_blocked` instead of human review.

The authorized narrow repair resolves the producing revision for an inherited
evidence artifact at operation-output validation, including descendants that
inherit it again. The stored artifact ID, digest, check time, receipt and
original-producing policy remain authoritative. No new FX call, side-effect
stage, graph state or financial selection rule is introduced. Acceptance is
a human-review-ready foreign-to-base child and offline descendant with the
same evidence identity/digest/check time and zero new retrieval/FX/provider
calls, while skip-to-foreign blocking and tamper rejection continue to pass.

The new regression failed before repair: the first construction-only child
returned `revision_blocked` where human review was expected. After the narrow
change, operation-output validation walks contiguous revisions that retain
the exact candidate-evidence artifact ID and evaluates the saved FX
disposition with that artifact's producing revision inputs. A fresh retrieval
without an artifact reference still uses its current revision inputs. The
test now reaches review after both the base-only child and a second inherited
screening-policy child; the artifact ID, digest and check time remain exact,
and offline restore validates review with one total retrieval and FX call.
The focused Issue 115, revision, US/EU and curator suites passed **275 tests**,
including the failing-before/passing-after regression, retained skip-to-foreign
blocker, and prior tamper cases. Ruff lint/format, mypy (69 source files),
`uv build`, role validator, Compose config and `git diff --check` passed.
The coordinator owns the post-fix real-store gate and PR CI; their results
are recorded separately after completion.

The post-fix full real-store suite passed **41 tests, zero failures, errors
or skips**, in 134.09 seconds using the same frozen all-extras environment
and opt-in command above. Project `etf-advisor-contract-b936a59ab652`, its
labeled containers/volumes, and all three captured anonymous volume names
were verified absent at `2026-11-12T18:22:28.9794283Z`. The ignored complete
log is `.artifacts/issue115-verification/pr146-origin-real-store.log`.

Independent `code_reviewer` (`gpt-6-sol`, high, `/root/issue115_review`)
reviewed the narrow follow-up and returned **PASS**, covering fresh execution,
succeeded receipt reuse, multi-hop origin resolution and retained marker,
artifact and receipt tamper checks. The existing origin contract is unchanged;
this repairs its missed operation-output validation path.
