# Business logic review

Run: `20260906-071454Z`. Reviewed commit: `c25865f` (current checkout; no branch changes). Audit only. Two confirmed P1 findings; no P0 finding. Both concern implemented source-backed eligibility controls, not planned Iteration 017 lifecycle or dashboard work.

## Scope and checks

Read `AGENTS.md`, raw wishlist, product vision, architecture, accepted ADRs 0002, 0004, 0010, 0014 and 0015, and active Iteration 017. Inspected the recent revision/identifier changes and their interaction with existing business contracts. Inspected profile and policy models, research models, both Yahoo adapters, candidate evidence selection/validation, screening, construction and independent validation, explanation grounding/safety, revision planning and review recomputation, and dashboard contract entry points. Read relevant policy, screening, construction, Yahoo, explanation and revision test fixtures and assertions.

Root owns the required baseline checks; this reviewer did not duplicate them. Targeted reproductions used the frozen environment at `C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv/Scripts/python.exe`, with `PYTHONDONTWRITEBYTECODE=1` and `python -B -` via standard input. Both reproductions passed through production validation and printed the outcomes below. No live services or market/provider endpoints were called, and no project files were modified to reproduce them.

## BL-1 — P1: Field-level stale screening evidence can produce an eligible portfolio position

Confidence: high; reproduced with production screening and construction functions.

Affected locations:

- `src/etf_advisor/domain/screening.py:403-431`: freshness uses the candidate's matching document-level health observation.
- `src/etf_advisor/domain/screening.py:434-490`: numeric rules read field provenance and values without checking the field observation against the evidence freshness window.
- `src/etf_advisor/domain/screening.py:590-644`: provenance parsing checks shape and flattened agreement, but not field freshness.
- `src/etf_advisor/domain/construction.py:534-550`: the additional field-level freshness check is limited to category.
- `src/etf_advisor/research/models.py:179`: source-document observation is the newest observation across fields.

Evidence and impact: an otherwise ready SPY candidate with an expense-ratio observation 30 days before the evidence check passes expense-ratio screening and remains in a ready five-position portfolio under a 24-hour window. The category and candidate-level observations remain current. This also applies to liquidity, concentration, and sector provenance because their rules do not perform the missing per-field time check. In a mixed-timestamp snapshot, a field that was within the window at ingestion can expire before newer fields do; selecting the newest timestamp masks that expiry at retrieval. A replaceable retriever can also return this internally well-formed payload. This is distinct from an elapsed wall-clock recheck on restored reviews: the reproduction is already stale relative to the bundle's own authoritative `checked_at`.

Minimal reproduction from repository root (run in the frozen environment with bytecode disabled):

```python
import json
import runpy
from datetime import timedelta
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.domain.construction import (
    PortfolioConstructionInput, construct_model_portfolio,
)

m = runpy.run_path("tests/test_construction.py")
inputs = m["_construction_input"](m["_profile"]())
evidence = inputs.candidate_evidence
candidate = evidence.candidates[0]
fields = json.loads(candidate.metadata["field_provenance_json"])
fields["expense_ratio_pct"]["observed_at"] = (
    evidence.checked_at - timedelta(days=30)
).isoformat()
candidate.metadata["field_provenance_json"] = json.dumps(fields)
# Recompute the local synthetic identity for the changed input, rather than
# introducing a separate digest-tamper error unrelated to this finding.
evidence.snapshot_version = evidence.snapshot_digest = None
screening = screen_candidate_evidence(evidence)
result = construct_model_portfolio(PortfolioConstructionInput(
    profile=inputs.profile,
    policy_calculation=inputs.policy_calculation,
    candidate_evidence=evidence,
    candidate_screening=screening,
    construction_policy=inputs.construction_policy,
))
print(screening.candidates[0].verdict, result.status)
print([position.symbol for position in result.draft.positions])
```

Observed output: `pass ready`; `['SPY', 'VTI', 'QQQ', 'VEA', 'BND']`. Fee observation was `2026-08-03T08:00:00+00:00`; evidence check was `2026-09-02T08:00:00+00:00`; declared maximum age was `24.0` hours.

Remediation agent prompt:

> Fix field-level freshness enforcement in the agents-lab evidence/screening/construction boundary. Scope the change to the material canonical research fields consumed by deterministic judgments, plus focused regression tests and required project evidence. Use the checkpointed evidence check time, maximum age, and future tolerance; keep calculation pure and do not add a wall-clock/network/provider call or silently alter accepted thresholds. Ensure a newer document timestamp cannot make a stale or future field eligible; preserve source/field attribution and explicit blockers. Acceptance: fee, average volume, concentration, sector and identity field boundary cases at the permitted age/future tolerance behave consistently; any consumed out-of-window field stops unsupported screening/construction before explanation or review, including mixed-timestamp snapshots and replacement retrievers. Existing category, missing-data and valid-current cases remain correct. Verify with `uv run pytest tests/test_screening.py tests/test_evidence.py tests/test_construction.py tests/test_workflow.py tests/test_dashboard.py`, then the repository's full Ruff-format, Ruff, mypy, pytest, offline retrieval/explanation evaluation, build, and Compose-config gates. Do not call live financial endpoints or execute trades.

## BL-2 — P1: Partially malformed Yahoo exposures are published as complete available evidence

Confidence: high; reproduced through fake Yahoo collection, snapshot conversion, evidence selection and production screening.

Affected locations:

- `src/etf_advisor/data/yahoo_research.py:319-339`: malformed holding rows/weights are silently skipped while surviving rows remain usable.
- `src/etf_advisor/data/yahoo_research.py:342-351`: malformed sector weights are silently omitted while surviving sectors remain usable.
- `src/etf_advisor/data/yahoo_research.py:215-219`: top-ten concentration is computed from the surviving holdings and capped at 100.
- `src/etf_advisor/data/yahoo_research.py:253-268`: surviving sector and derived concentration values are represented without a missing reason.
- `src/etf_advisor/domain/screening.py:548-552`: a missing requested sector in an available projection is treated as zero exposure.

Evidence and impact: fake Yahoo holdings contained one valid 10% row and a second row with unavailable weight; the adapter reported available top-ten concentration of 10%. Fake sector data contained `technology: 0.20` and `energy: 'unavailable'`; the adapter reported available technology-only sector data. The downstream graph context matched the published canonical data exactly, yet screening classified concentration and a zero-tolerance energy exclusion as `pass`. Therefore canonical/graph equality does not protect against the lossy parser. A source-data error can turn unknown concentration or excluded exposure into affirmative eligibility.

The reproduction does not assume that every ETF must have ten holdings or that sector totals must always equal 100. It demonstrates actual malformed rows being dropped without preserving incompleteness. Legitimate explicit zero weights and justified genuinely short holdings lists should be handled separately.

Minimal reproduction:

```python
import runpy
from datetime import timedelta
from etf_advisor.data.yahoo_research import YahooResearchAdapter
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, SectorExposure
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.domain.screening import screen_candidate_evidence

m = runpy.run_path("tests/test_yahoo_research.py")
class BadFunds(m["FakeFundsData"]):
    top_holdings = [
        {"Name": "Known minority", "Symbol": "AAA", "Holding Percent": 0.10},
        {"Name": "Unknown majority", "Symbol": "BBB", "Holding Percent": "unavailable"},
    ]
    sector_weightings = {"technology": 0.20, "energy": "unavailable"}
class BadTicker(m["FakeTicker"]):
    funds_data = BadFunds()

checked = m["datetime"](2026, 8, 29, 12, 1, tzinfo=m["UTC"])
snapshot = YahooResearchAdapter(
    clock=lambda: checked, ticker_factory=lambda symbol: BadTicker(),
).fetch_snapshot(m["one_member_universe"](), snapshot_version="audit-fake")
record = snapshot.records[0]
document = snapshot.to_source_documents()[0]
context = GraphContext(
    source_document_id=document.document_id, symbol=document.symbol,
    etf_name=record.name.value, sector_exposures_status="available",
    sector_exposures=[SectorExposure(name=x.name, weight_pct=x.weight_pct)
                      for x in record.sector_exposures.value],
)
source = GraphEnrichedSource(
    document_id=document.document_id, content=document.content,
    metadata=document.metadata, graph_context=context,
)
profile = runpy.run_path("tests/test_construction.py")["_profile"]().model_copy(
    update={"excluded_sectors": ["energy"]},
)
evidence = select_candidate_evidence(
    profile, [source], query="audit", checked_at=checked,
    max_age=timedelta(hours=24),
)
result = screen_candidate_evidence(evidence).candidates[0]
print(evidence.status, result.verdict)
print(record.top_10_concentration_pct.value,
      record.top_10_concentration_pct.missing_reason)
print(result.rules[-1].reason_code)
```

Observed output: `ready pass`; `10.0 None`; `sector_exclusions_clear`. Both the raw collection fake and graph projection are local objects; no Yahoo or Neo4j call was made.

Remediation agent prompt:

> Fix partial exposure parsing in `src/etf_advisor/data/yahoo_research.py` and its downstream eligibility contract. Preserve malformed/absent row evidence as unavailable or incomplete rather than silently dropping it into an available aggregate. Scope to holdings, derived top-ten concentration, sector parsing and focused tests; retain replaceable adapters and field-level provenance. Do not invent missing weights, infer zero from a parse failure, normalize impossible totals silently, or change financial screening thresholds. Acceptance: a mixed valid/malformed holdings list cannot produce an available understated top-ten value; a malformed requested-sector weight cannot become a passing zero-exposure exclusion; explicit numeric zero is preserved; valid provider fractions are converted correctly; complete valid data retains existing behavior. Document and test legitimate short lists separately rather than requiring ten rows indiscriminately. Verify with `uv run pytest tests/test_yahoo_research.py tests/test_research_snapshot.py tests/test_screening.py tests/test_neo4j_store.py tests/test_construction.py`, followed by all configured Ruff-format, Ruff, mypy, full pytest, offline evaluations, build, and Compose-config gates. Use fixtures only, without live Yahoo/database/provider calls or financial writes.

## Confirmed strengths and limitations

- US-market and ETF classifications are required before ready evidence; construction uses the explicit category map rather than ticker/prose guesses. Geography remains provider-unsupported and fund-family context is not presented as legal issuer evidence.
- Expense-ratio conversion explicitly distinguishes `netExpenseRatio` percentage points from `annualReportExpenseRatio` fractions. Holdings/sector parsing currently accepts both numeric fractions and percentage-like inputs; provider-schema/unit drift was not externally verified in this offline audit.
- Policy cash uses Decimal cent rounding; construction uses integer basis points and cents, deterministic largest feasible subsets and stable remainder order. Existing fixture assertions cover exact sleeve/position totals, small cash, category limits, infeasibility, and tampered persisted drafts. No independent arithmetic defect was confirmed.
- Missing scalar fields and unsupported sector exclusions remain unknown when absence is properly represented. BL-2 identifies an upstream case where the representation loses that absence.
- Typed revision patches select the earliest invalidation stage and do not use free text to mutate financial inputs. Review recomputes deterministic business outputs. The security and architecture roles separately examine explanation language and checkpoint/interrupt integrity; their findings should be deduplicated in synthesis.
- Source/model text remains structurally attributable, but numeric-token membership and regex claim rejection do not establish general semantic entailment. This audit does not claim that all recommendation/guarantee/forecast paraphrases are rejected.
- There are no implemented brokerage writes or trade execution paths in the inspected scope. Lifecycle expiry/deletion and interactive revision/retry controls belong to planned #41/#42 and are not reported as regressions.
- No live source schema, quote accuracy, jurisdiction/suitability analysis, real portfolio performance, external-store integration, or model behavior was evaluated. Baseline status and repository-wide change verification belong to `SUMMARY.md`; successful targeted reproductions are evidence of defects, not a passing health baseline.

## YahooResearchAdapter refactor decision

Refactor later, after focused correctness fixes with regressions. The adapter has separable transport/retry, source parsing, provenance construction and aggregation responsibilities, but its size alone does not justify a broad rewrite. BL-2 justifies making parsing completeness explicit now. Extracting that tested normalization boundary can be a small part of remediation; defer a wider class redesign until it reduces a demonstrated change risk.

## Final reviewer verification

Both reported defects were reproduced with exit code 0 using the frozen environment and local test fixtures, without modifying source or test files. The reviewer wrote only this role report. No baseline gate was repeated, no application/dependency change was made, and no Git mutation was performed.
