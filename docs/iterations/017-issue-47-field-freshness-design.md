# Issue 47: Field-level screening freshness design

- Status: DESIGN_READY; awaiting user approval.
- Implementation authorization: Pending. This document does not authorize implementation.
- Prepared: 2026-09-13.
- Issue: https://github.com/beagle1903/agentic-etf-advisor/issues/47
- Baseline: `b82bc9d8a9fefd8da10ed64f4c944fc0149f47d1`.
- Relationship: Supporting design for the active [Iteration 017](017-revision-loop-and-audit-trail.md).

## Routing and phase boundary

The coordinator selected `design_architect`, GPT-6 Astra/high, for a separate read-only
design session (`/root/issue47_design`). Financial eligibility and restored-state validation
require this role under AGENTS.md and ADR 0020. The architect returned this handoff without
editing files. The coordinator records it here for user review. No write-capable implementation
role has started; no escalation or workflow exception was used.

After explicit approval, select a separate sequential `implementation_specialist`,
GPT-5.6 Sol/high. The scope crosses screening, construction error handling, workflow diagnostics,
and restored-state regressions. Approval must be recorded before that session starts.

## Verified problem

An offline reproduction against the baseline changed only SPY's canonical expense-ratio
observation to 30 days before the evidence check time and regenerated the local synthetic
identity. Production screening still returned fee `pass`; construction returned `ready` and
retained SPY. The architect used `.venv/Scripts/python.exe -B`, without changing files or calling
external services. This is design evidence, not a completed regression suite.

The execution path explains the gap:

- `research/models.py`, `ETFResearchSnapshot._to_source_document`, chooses the newest field
  observation as the document observation.
- `rag/evidence.py`, `select_candidate_evidence`, and `CandidateEvidenceBundle.validate_ready_bundle`
  check document-level health rather than every canonical field.
- `domain/screening.py`, `screen_candidate_evidence` and `_screen_candidate`, check document health;
  `_numeric_rule` and `_sector_rule` consume canonical fields without checking their timestamps.
  `_confirmed_rule` can confirm identity using document attribution when canonical provenance is absent.
- `domain/construction.py`, `_validate_upstream`, recomputes screening but independently checks
  freshness only for category.

Source paths above are relative to `src/etf_advisor/`. A field can expire before a newer document
observation, so ingestion-time validation alone cannot fix this defect.

## Scope and non-goals

Enforce the existing evidence freshness window for canonical fields consumed by screening.
Preserve category freshness in construction. Remove affirmative identity confirmation when
canonical eligibility provenance is absent. Carry attributable, stable diagnostics through the
existing graph error boundary.

| Canonical field | When freshness is checked |
| --- | --- |
| `market` | Every candidate when canonical evidence is available |
| `quote_type` | Every candidate when canonical evidence is available |
| `expense_ratio_pct` | Every candidate when available |
| `average_daily_volume` | Every candidate when available |
| `top_10_concentration_pct` | Every candidate when available |
| `sector_exposures` | When exclusions were requested and the canonical field is available |
| `category` | Existing construction check remains authoritative |

Identity means the US-market and ETF classifications consumed by eligibility rules. `symbol`
remains the normalized candidate/document key; the research contract has no canonical symbol
`ResearchField`. `name` is a display label. Do not invent symbol provenance or require name
provenance. Preserve graph source-document and normalized-symbol checks.

Non-goals: new thresholds, units, ranking, financial policies, provider support, snapshot repair,
Yahoo parser changes, database schemas, checkpoint migration, authentication, lifecycle changes,
live-service acceptance, and Iteration 018. Do not add wall-clock revalidation of old reviews:
freshness is evaluated against the persisted bundle check time.

## Invariants and decisions

1. Use only `evidence.checked_at`, `evidence.health.max_age_hours`, and
   `evidence.health.future_tolerance_minutes`. Never read a clock or substitute document or
   ingestion time for a field observation.
2. Match `assess_observations` and `_category_is_current` using datetime/timedelta comparisons:
   `observed_at > checked_at + future_tolerance` is future; otherwise
   `checked_at - observed_at > max_age` is stale; otherwise the field is current.
   Exact age and future-tolerance boundaries are accepted. Do not compare rounded health ages.
3. Validate canonical provenance and existing flattened status/value agreement before freshness.
   Malformed JSON, missing or naive timestamps, invalid field models, contradictory values or
   statuses, and existing unit violations remain contract errors.
4. An available consumed stale/future field blocks the complete screening operation. Return no
   partial ready bundle; do not downgrade it to ordinary unknown or construct from surviving
   candidates. ADR 0014 permits candidate-local exclusion for ordinary missing evidence, while
   stale evidence and contradictory upstream contracts block construction. This also matches
   the existing all-candidate category freshness check.
5. Missing scalar provenance and explicit scalar missing reasons retain `expense_ratio_unknown`,
   `volume_unknown`, and `concentration_unknown`. Unavailable sectors retain
   `sector_exposure_unknown`. Do not judge freshness of an unavailable value. Malformed provenance
   still blocks during parsing.
6. Entirely absent canonical identity provenance yields new `us_listing_unknown` or
   `etf_type_unknown` results. A document timestamp cannot establish missing field provenance.
   Preserve hard errors for supplied canonical identity that contradicts the mandatory affirmative
   candidate classification, including an explicit missing reason or different value. Current,
   agreeing provenance retains existing pass codes and citations.
7. No requested exclusions retains `no_sector_exclusions`; unused sector age does not block.
   Any requested exclusion requires freshness of available canonical sectors, even when terms
   are unsupported or graph context is unavailable. Preserve taxonomy, exact graph/canonical
   weight agreement, and unknown handling for missing or unsupported evidence.
8. Preserve candidate/rule order, fail/unknown aggregation, thresholds, units, values, and successful
   citations. Check freshness in deterministic candidate order and then screening field order;
   stop at the first freshness violation. Check consumed fields before producing that candidate's
   rule results so another failed rule cannot hide stale evidence.

## Interfaces and implementation contract

Keep the public signature `screen_candidate_evidence(evidence, policy)` unchanged.

In `src/etf_advisor/domain/screening.py`:

- Pass the full persisted freshness context into `_screen_candidate`.
- Add one pure private available-field freshness helper matching the existing quality policy.
- Check freshness after canonical parsing and before constructing rule results.
- Update `_confirmed_rule` with the two unknown identity results for absent provenance.
- Add `ScreeningFieldFreshnessError`, a `ScreeningContractError` subclass, with stable
  `field_stale` and `field_future` codes. Carry the existing `ScreeningCitation` identifying the
  field plus the authoritative check time. Use a fixed, sanitized message without source content
  or raw payloads.

In `src/etf_advisor/graph/nodes.py`, `screen_candidates` catches the specific freshness error
before the generic contract handler. Retain `screening_blocked` and empty `candidate_screening`.
The existing `screening_errors` item keeps `type="screening_contract"` and a sanitized message,
adding `code`, JSON-mode `citation`, and ISO `checked_at`.

In `src/etf_advisor/domain/construction.py`, `_validate_upstream` catches the freshness subclass
before generic screening exceptions and maps it to existing `ConstructionReason.EVIDENCE_NOT_READY`.
Other contract errors retain current mappings. Inconsistent persisted screening retains
`SCREENING_RECOMPUTATION_MISMATCH`. Preserve `_category_provenance` and `_category_is_current`;
do not broaden this into a provenance-parser refactor.

## JSON, replacement retrievers, and restored state

No new graph state key, evidence field, checkpoint version, snapshot schema, policy field, or
side-effect interface is required. Valid-current successful JSON remains unchanged. Additions
are screening reason strings and structured fields in the existing error list. Explicitly
serialize exception data; never checkpoint exception instances or datetime objects.

Screening validates canonical fields regardless of whether a replacement retriever used
`select_candidate_evidence`, ordinary model validation, `model_copy`, or `model_construct`.
Document-health validation may succeed before field screening blocks; these are distinct boundaries.

The following consumers already recompute the authoritative path and require regression coverage:

- `construct_model_portfolio` and `validate_persisted_construction`.
- `ExplanationRequest.validate_consistency` in `explanation/models.py`.
- `ReviewPayload.validate_review_consistency` and `review_payload` in `dashboard.py`.
- `RevisionRuntime.review` and explanation operation-output validation in `graph/revision.py`.

They must reject formerly passing stale-field artifacts before provider invocation or actionable
review. No production changes to those consumers beyond scoped construction/graph error handling
are expected. If tests expose an architectural gap, return to `design_architect` before expanding scope.

Do not rewrite stored artifacts or automatically regenerate identities. Historical results that
disagree with corrected screening fail validation. Valid-current restore and successful receipt
reuse preserve identities and do not call adapters again.

## Acceptance criteria and focused verification

- [ ] Parameterize market, quote type, fee, volume, concentration, and requested sector exposure
  across current, exact-age, one microsecond stale, exact-future-tolerance, and one microsecond
  beyond-tolerance observations. Assert stable codes and exact field citations.
- [ ] Cover zero future tolerance and timezone-equivalent observations.
- [ ] Keep document, category, and other fields current while one consumed field is stale/future.
  Confirm whole-operation blocking even if another rule/candidate fails or is unknown.
- [ ] Preserve threshold results, missing scalar/sector behavior, #48 source-error handling,
  explicit zero exposure, unsupported exclusions, and valid-current JSON round trips.
- [ ] Absent canonical identity is unknown; canonical identity contradictions still block.
- [ ] No-exclusion flows ignore unused sector age; requested exclusions enforce it.
- [ ] Direct construction given formerly passing screening plus stale-field evidence returns
  blocked `evidence_not_ready`, even when unaffected candidates could form a portfolio.
- [ ] Replacement retrievers with current document health and stale/future fields, including
  unvalidated model construction, reach no explanation call and no human-review interrupt.
- [ ] Direct explanation requests, persisted dashboard/interrupt validation, and revision
  review/reuse reject internally coherent formerly accepted artifacts. Prove field validation,
  not merely a digest mismatch.
- [ ] Valid-current restore/reuse preserves IDs and makes zero additional external calls.

Expected focused files: `tests/test_screening.py`, `tests/test_construction.py`,
`tests/test_workflow.py`, `tests/test_evidence.py`, `tests/test_explanation.py`,
`tests/test_dashboard.py`, and `tests/test_revision.py`. Update shared fixtures only where they
incorrectly relied on identity confirmation without canonical evidence. Preserve explicit
legacy/missing-provenance cases.

After the focused suite, run the full ordered baseline and record exact results:

```powershell
uv sync --frozen --all-extras
uv run python scripts/validate_codex_workflow.py
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run etf-advisor evaluate-retrieval
uv run etf-advisor evaluate-explanations
uv build
docker compose config --quiet
git diff --check
```

These are implementation acceptance gates, not claimed design-phase results. No live provider,
market-data service, or real-store acceptance is required by this design.

## Documentation and risks

Record user approval here before implementation. During implementation, update
`docs/architecture/system.md` and the canonical Iteration 017 record with the final behavior and
verification evidence. Add the next available ADR for available-field hard blockers, identity
provenance requirements, and missing-versus-stale treatment. Do not rewrite accepted ADRs.

Legacy evidence lacking canonical identity can no longer receive affirmative identity screening.
Historical reviews accepted by the defective rules may fail restoration validation. Neither case
receives silent repair. This preserves bundle-relative reproducibility; it does not establish
present-day freshness at restore time, repair published snapshots, validate display-only fields
or source prose, or prove real provider/database behavior.

## Approval record

- Design validation: `.venv/Scripts/python.exe -B scripts/validate_codex_workflow.py` passed;
  staged `git diff --cached --check` passed. Only this design document is included in delivery.
- User approval: Pending.
- Implementation session: Not started.
- Implementation tests and acceptance: Not run.

DESIGN_READY
