# Test coverage reviewer

Run: `20260906-071454Z`. Revision reviewed: `c25865f` (PR #45 merge), without branch changes. Audit only; this reviewer wrote only this report. See [PREPARATION.md](PREPARATION.md) for the exact branch, upstream, starting changes, environment, and frozen installation evidence.

## Assessment

The deterministic suite provides substantial coverage of the implemented scope, particularly the new revision and receipt controls. The recorded baseline has **360 passing tests**, passing Ruff format/check, strict mypy, both offline evaluations, build, and Compose configuration validation. I inspected `baseline-results.json`; I did not repeat unchanged baseline gates. Passing tests do not establish a defect-free baseline: targeted probes below reproduce three unsafe accepted inputs outside existing regression fixtures, and the architecture review identifies an additional missing interrupt-presence case.

There are no separate P0 findings here. Three P2 verification gaps are actionable below. TC-01 and TC-02 describe missing regression protection for defects independently owned by the security, architecture, and business-logic reports; do not count those underlying defects again during synthesis. TC-03 is a confirmed coverage limitation, **not a confirmed store defect**.

## Checks performed and coverage map

Read order followed: AGENTS.md, wishlist, product vision, system architecture, accepted ADRs 0006, 0008, 0010, 0014, 0015, and highest iteration 017. Inspected the current five-commit history, including revision routing and the identifier injection follow-up. Read the test inventory across all 23 test modules and focused source/test bodies at the safety and persistence boundaries.

| Area | Existing evidence and judgment |
| --- | --- |
| Revision routes and downstream invalidation | `tests/test_revision.py:84-129` parameterizes all five classes for edit and reject, exact visited nodes, cleared artifacts, retained upstream IDs, parent/child decision separation, and adapter counts. Mixed precedence begins at line 131; malformed decisions and disabled stages at 170 and 203. Good coverage of implemented routing. |
| Receipts, restore, replay, and explicit retry | `tests/test_revision.py:212-328` covers successful reuse on a recompiled graph, failed/ambiguous attempts, explicit attempt two, and malformed/missing/duplicate/out-of-order/cross-thread/cross-revision/input/output mutations. The tamper test deliberately recomputes the outer seal, so it exercises semantic checks rather than only digest mismatch. Lines 379-418 cover prepare-commit failure and unsafe durability overrides; lines 421-550 cover thread/ledger loss, invalid retry, child lineage, snapshot identity, malformed resume, and unsafe output with matching digests. Strong offline coverage, with real persistence limitation below. |
| Identifier replay | All four `tests/test_revision_identifiers.py` tests cover deterministic root/retry/child state, prepare replay, no allocation on receipt reuse/approval, and artifact collision protection. This supports the most recent PR #45 follow-up. |
| Source and provider failures | `test_market_data.py`, `test_data_quality.py`, `test_evidence.py`, and `test_workflow.py` cover bounded retry, exhausted metadata, empty retrieval, unsupported ETF/US identity, malformed URL/content, forged freshness labels, foreign graph identity, sanitized provider errors, and no review after source failure. Rich research mixed valid/invalid rows are missing (TC-02). |
| Freshness | `tests/test_cli.py:239-281` checks every research field before ingestion and bounded future skew. `tests/test_evidence.py:111-166,393-439` tests top-level current/stale/future observations and recomputed health. `tests/test_construction.py:285-308` explicitly covers stale/future category provenance. Scalar and sector field ages during retrieval/screening need equivalent tests (TC-02). |
| Snapshot staging, activation, immutability | `tests/test_snapshot_publication.py:69-231` checks stage/readback failures, graph failure, digest mismatch, immutable versions, and interleaved publishers using fakes. `test_snapshot_io.py` checks canonical round trip and same-path conflicting content. `test_cli.py:170-237,282-437` covers canonical retry, freshness-before-store, active no-op, and missing Chroma records. `test_hybrid_retrieval.py:72-111` keeps staged documents inaccessible without activation. Actual store behavior remains unevaluated (TC-03). |
| Screening and allocation | `tests/test_screening.py:25-207` covers threshold equality, failures, unknowns, unsupported exclusions, unit/status contradictions, and range validation. `tests/test_construction.py` covers feasible subset order, category/position limits, no sleeve coverage, failed/unknown exclusions, stale categories, >10 pool blocker, screening mismatch, basis-point precision, independent tamper detection, JSON round trip, and tiny cash rounding. No additional confirmed arithmetic defect found. |
| Explanation and dashboard | Production validator, references, selected positions, numeric grounding, prompt-injection treatment, provider sanitization, restoration, and renderer contracts have tests. The safety phrase corpus is narrow and checkpoint/interrupt tests concentrate on full construction payloads (TC-01). |
| Offline evaluation | Both evaluation tests verify deterministic scores and adverse changes fail the gate. Eight curated explanation cases are a regression baseline, not evidence of broad language coverage. |

## TC-01 — P2: missing cross-product tests at the human-review safety boundary

**Confidence:** high. **Classification:** confirmed regression coverage gap; underlying production defects overlap architecture/security findings.

**Evidence and exact locations:** `tests/test_dashboard.py:613-623` tests asymmetric explanation presence only with a full portfolio; `tests/test_dashboard.py:673-697` tests upstream mismatches only using `paused_state_with_portfolio_and_explanation()`. `src/etf_advisor/dashboard.py:331-371` gates checkpoint artifact comparison on construction being present in the interrupt. The architecture reviewer/root reproduced accepting a policy-only mismatch and accepting a full checkpoint's interrupt after all four optional artifacts were removed. Separately, `tests/test_explanation.py:352-371` enumerates only six unsafe phrasings; `tests/test_dashboard.py:594-611` restores only a guarantee and unsupported numeric claim. The imperative pattern at `src/etf_advisor/explanation/models.py:50-56` is sensitive to the beginning of a sentence. A direct production-validator probe accepted `Please buy SPY.`.

**Impact:** tests pass while presentation can omit authoritative checkpoint artifacts, or expose a trade instruction that fits an untested wording. The suite needs tests over enabled-stage combinations and adversarial wording rather than more copies of the same full-payload success fixture.

**Reproducible triggers:** using `test_revision.start()`, copy the returned state and interrupt, remove `candidate_evidence`, `candidate_screening`, `portfolio_construction`, and `draft_explanation` from the interrupt only, then call `review_payload`; the root verified it returns an accepted policy-only payload. For the instruction bypass, execute the snippet in the targeted checks below.

**Actionable remediation prompt:**

> In a dedicated follow-up, extend tests/test_dashboard.py, tests/test_explanation.py, tests/test_workflow.py, and the offline explanation fixture with regressions for the architecture/security fixes. Keep accepted educational scope, source attribution, policy arithmetic, provider interfaces, and the frozen dependency versions unchanged. Cover valid policy-only and full-artifact reviews, independently modified policy fields, independently absent or added artifacts, and removal of all downstream artifacts while the sealed checkpoint retains them. Assert rejection before review controls; preserve valid untouched flows. Add direct polite/prefixed trade instructions, punctuation/whitespace variants, and safe negated educational examples through the production validator, graph node, and restored explanation boundary; assert blocked output contains no rejected text. Do not make tests pass by weakening the desired rejection or bypassing the production validation path. Acceptance: each new unsafe case fails against the pre-fix code, passes only with the corresponding boundary fix, and accepted disclaimers still pass. Verify with uv run pytest tests/test_dashboard.py tests/test_explanation.py tests/test_workflow.py tests/test_explanation_evaluation.py, uv run etf-advisor evaluate-explanations, uv run ruff format --check ., uv run ruff check ., uv run mypy, and then the full frozen baseline.

## TC-02 — P2: freshness and malformed-source tests omit independent field ages and partial aggregates

**Confidence:** high. **Classification:** confirmed regression coverage gap; underlying production defects overlap business-logic findings.

**Evidence and exact locations:** `tests/test_screening.py:253-264` assigns the same observation time to every field; existing corruption tests at 183-207 cover status/unit/range, not independent field freshness. The category-specific test at `tests/test_construction.py:285-308` demonstrates a reusable way to distinguish field age from document age. `tests/test_yahoo_research.py:16-25,50-69` uses only valid holdings/sectors and actually expects a two-row sum as top-ten concentration. `src/etf_advisor/data/yahoo_research.py:326-339,342-351` silently omits invalid rows; lines 215-218 compute concentration from retained holdings. `src/etf_advisor/domain/screening.py:419-430` bases freshness on candidate health, separate from scalar provenance validation.

**Impact:** fresh top-level metadata can mask stale fee evidence; malformed provider rows can produce an apparently available smaller concentration/sector set. These omissions directly affect pass/fail/unknown eligibility and merit regression protection at adapter, screening, construction, and review boundaries.

**Targeted observed outputs:** a 2020 expense observation inside a 2026-current candidate produced `pass` with that stale citation; a valid 12% holding plus a malformed second holding produced concentration `12.0` with `missing_reason=None`; a valid technology weight plus malformed energy weight produced only technology with `missing_reason=None`. These observations used injected local fakes and no endpoints.

**Actionable remediation prompt:**

> Add regression tests for the agreed field-freshness and partial-provider-data fixes in tests/test_yahoo_research.py, tests/test_screening.py, tests/test_evidence.py, tests/test_construction.py, and relevant workflow tests. Preserve deterministic pass/fail/unknown semantics and do not infer missing exposures as zero. Parameterize expense ratio, daily volume, concentration, and sector provenance independently of a fresh candidate timestamp at exact max-age, just stale, exact future tolerance, and just excessive future values. Use canonical fresh identities or explicitly rebuild synthetic identity after controlled fixture mutations so failures exercise semantic freshness rather than only a digest. Include valid-plus-malformed rows, missing weights, non-finite/negative/out-of-range weights, duplicate holdings, and truncated top-ten lists. Document the accepted completeness contract; never assert that fewer reported rows prove top-ten completeness without evidence. Acceptance: stale or incomplete evidence cannot silently yield a passing threshold/exclusion; complete valid data retains correct units and provenance; graph flow cannot reach explanation/review on a blocking contract failure. Verify with uv run pytest tests/test_yahoo_research.py tests/test_screening.py tests/test_evidence.py tests/test_construction.py tests/test_workflow.py, uv run ruff format --check ., uv run ruff check ., uv run mypy, both offline evaluations, and the full frozen baseline.

## TC-03 — P2: persistence guarantees are tested only through fakes

**Confidence:** high. **Classification:** confirmed coverage gap, not a proven transaction, serializer, or query defect.

**Evidence and exact locations:** `tests/test_neo4j_store.py:24-82` dispatches canned results based on query substrings; lines 222-234 assert query text without executing Cypher. `tests/test_snapshot_publication.py:41-66` simulates activation using Python state; lines 179-197 enforce race exclusion using a Python lock. `tests/test_chroma_store.py:10-50` uses a fake query result. `tests/test_dashboard.py:58-75,872-899` uses `DurableMemoryCheckpointStore`; `tests/test_revision.py:379-403` injects `InMemorySaver.put` failure. The real `PostgresCheckpointStore` at `src/etf_advisor/checkpoint.py:39-66` dynamically imports PostgresSaver and opens actual short-lived connections, which these tests do not exercise.

**Impact:** the suite can pass even if a real Cypher version rejects the query, an actual Chroma filter/metadata round trip differs, or a PostgreSQL serializer/commit/reconnect path breaks the newly added revision ledger. The tests correctly establish adapter intent but cannot establish external transaction behavior.

**Decision on a temporary live-store integration test:** justified as a small, explicit follow-up, with PostgreSQL reconnect/receipt persistence and Neo4j atomic activation first. Use disposable isolated local stores and injected market/model/embedding fakes. This audit did not start services or contact stores. Do not turn live Yahoo/provider dependencies into baseline prerequisites. Whole-thread expiry/deletion tests belong to the later lifecycle implementation rather than this finding.

**Actionable remediation prompt:**

> Implement opt-in integration contract tests against disposable local PostgreSQL, Neo4j, and Chroma instances using the repository's current locked versions. Keep default offline tests service-free; do not contact Yahoo, model-provider or brokerage endpoints, alter dependency versions, or reuse/delete user databases. Use uniquely scoped disposable storage, fixed clocks, and fake provider/retrieval or local deterministic embeddings. Acceptance: create and interrupt a real PostgresSaver-backed graph, close connections, recompile and restore exact JSON revision/receipt/artifact identities, approve without extra adapter calls, and demonstrate that a persisted started receipt requires explicit retry after restoration. In Neo4j execute the actual publication query, verify failed publication preserves the previous active pointer, reject conflicting immutable versions, and read source-linked relationships. In Chroma verify real version/digest filters and inactive-stage exclusion. Scope cleanup to the test-owned stores and report skipped integrations explicitly when their opt-in prerequisites are absent. Verification: uv run pytest for the unchanged offline suite; document and run an explicit opt-in command such as uv run pytest tests/integration -m integration when the new marked tests exist, with service logs and unique test scope recorded; finish Ruff, formatting, mypy, both offline evaluations, packaging, and Compose config checks.

## Targeted checks and reproducibility

Executed one read-only stdin Python probe with the root's already frozen external environment and bytecode disabled:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
# Pipe the Python snippet to this interpreter with -B -:
# C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv/Scripts/python.exe
```

```python
import sys, json
sys.path.insert(0, "tests")
from test_screening import _evidence
from etf_advisor.domain.screening import screen_candidate_evidence
from test_explanation import _request, _generated
from etf_advisor.explanation.models import ExplanationResult, validate_and_bundle_explanation
x = _evidence()
p = json.loads(x.candidates[0].metadata["field_provenance_json"])
p["expense_ratio_pct"]["observed_at"] = "2020-01-01T00:00:00+00:00"
x.candidates[0].metadata["field_provenance_json"] = json.dumps(p)
x.snapshot_version = x.snapshot_digest = None
s = screen_candidate_evidence(x)
print(s.candidates[0].verdict, s.candidates[0].rules[3].citation.observed_at)
g = _generated()
g.evidence_points[0].text = "Please buy SPY."
b = validate_and_bundle_explanation(_request(), ExplanationResult(provider="test", model="fixed", explanation=g))
print(b.explanation.evidence_points[0].text)
```

Observed: `pass 2020-01-01T00:00:00+00:00` and `Please buy SPY.`. Resetting synthetic snapshot identity deliberately tests the semantic boundary after recomputation; it does not claim that arbitrary byte edits bypass an unchanged snapshot digest. The same probe injected a `FakeTicker` with holdings `[12%, malformed]` and sectors `{technology: 0.3, energy: "bad"}` and observed `12.0 None ['technology'] None`. These targeted results justify follow-up tests; no test or application files were changed.

## Limitations and planned work

No real-store, network, live-provider, process-kill, mutation-testing, broad fuzzing, or quantitative line/branch coverage run was performed. The required baseline was reused from root evidence; I did not install packages or rerun it for unchanged inputs. Test inventory and selected body inspection cannot prove every branch is covered. No metric target or coverage percentage is invented.

Iteration 017 explicitly leaves checkpoint expiry, retention, preview/prune/deletion (#41), richer typed-feedback/retry forms (#42), and final iteration acceptance (#43) unfinished. Missing tests for those future implementations are planned acceptance work, not regressions against the reviewed code. Authentication and concurrent multi-user review are also outside accepted current scope.

This specialty review is complete. Its only repository write is this report; final repository-wide preservation verification belongs to SUMMARY.md.

