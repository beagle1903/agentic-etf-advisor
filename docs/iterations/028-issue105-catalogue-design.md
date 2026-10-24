# Issue105: bounded catalogue research and selection design

Date: 2026-10-23. Separate read-only architect `/root/issue105_design`,
`design_architect / gpt-6-astra / high`. Coordinator transcription of its returned
DESIGN_READY handoff. Pending independent challenge and coordinator approval;
this document alone grants no implementation authority.

Capsule `issue-105-catalogue-selection`, generation1,
`38a418bebc1692e4ee3f7ca31de84c5fbf387b2ed1f79093aa1be74018261798`.
Owner: `/root/issue105_owner`, implementation_worker/gpt-6-sol/medium.
Human approved starting this queued chat on 2026-10-23. Dependencies103/104
closed; PR114 merged, clean synchronized main749feeb verified before start.

## 1. Scope and current execution path

Explicit catalogue mode within us-eu-v1 selects a bounded scope, collects/caches
research in resumable batches, publishes its complete snapshot, retrieves the
complete bounded scope, screens it, and shortlists at most ten before unchanged
subset enumeration.

Current constraints traced by architect:

- `research/universe.py:load_research_universe` defaults to six packaged members.
- `data/yahoo_research.py:YahooResearchAdapter.fetch_snapshot` fetches supplied
  members sequentially.
- `research/models.py:ETFResearchSnapshot.validate_snapshot_consistency` requires
  every field to share snapshot ingestion time/version.
- `rag/evidence.py:CandidateEvidenceBundle` bounds requested_limit at ten and
  schema2 ready candidates at that limit.
- `domain/construction.py:_validate_upstream` rejects pools over ten before
  classification; `_select_subset` enumerates bounded subsets.
- `graph/revision.py:operation_digest` binds full profile/requested limit to
  retrieval; putting the request in profile preserves that boundary.
- `dashboard.py:review_payload` and `validate_persisted_construction` recompute
  construction from persisted upstream evidence.

Path: catalogue preview -> frozen scope -> explicit research batches -> complete
canonical snapshot -> existing publication -> existing retrieval receipt -> full
bounded evidence -> screening -> pure shortlist -> existing <=10 constructor ->
explanation/review.

Non-goals: global optimizer, cap increase, forced whole-catalogue fetch, inferred
categories, unrelated sources, auth/hosting, trades/external financial writes,
live saved-review modification, Issue115 FX-call optimization. Preserve existing
Issue104 financial and replay staging and exact absent-marker legacy paths.

## 2. Request and scope (INV105-1/2/3/5)

Strict `CatalogueScopeV1`, literal schema `catalogue-research-scope-v1`, contains:
pinned catalogue version/map yahoo-listing-map-v1; normalized user filters and
optional explicit listing IDs; complete members sorted by exact listing ID;
member listing ID, exact symbol/exchange, selected observation origin/time;
coverage discovered/direct-only/combined/matched/requested counts, original
full-refresh time, provider-partition status and unsupported-country/venue limits;
canonical SHA256 over all scope content except its own digest.

Strict `CatalogueRequestV1`, schema `catalogue-selection-v1`, contains complete
scope plus exact published snapshot_version/snapshot_digest. Optional profile
`catalogue_request` requires us-eu-v1 and enabled evidence. Explicit null, unknown
schema, bad digest, duplicate identities/incompatible mode reject. Absence omits
the field exactly, retaining existing dumps without a new null/default key.

Resolve from complete validated `catalogue_projection`, never truncated
`local_search(...).matches`. Filters: exact mapped region/country/exchange,
case-insensitive symbol/name substring, explicit listing IDs. Intersection;
selected IDs must belong to filtered results. Default/hard maximum requested
scope100, configurable downward1..100. Zero and over-limit reject with counts and
fixed reasons; never take a prefix. User explicitly narrows excess scope.
Incompatible research symbols are reported unsupported and prevent the requested
plan; no silent omission or instrument-changing normalization. Directory names,
currency, domicile/category text cannot become research facts.

## 3. Research jobs, bounds, cache and failures (INV105-1/2/4)

Ignored local research-job store separate from graph checkpoints/catalogue store.
Strict versioned manifest pins scope, policy, normalized validated reference inputs
and digest, and unique destination snapshot version. Capture created_at at job
creation for bookkeeping only, never ResearchField ingestion. Canonical snapshot
ingestion time/digest do not exist until successful finalization. A successful
collection is an immutable normalized validated source-cache record, not a
canonical snapshot. Capture cache ingestion after all listing source reads,
including BND fallback; preserve original cache coordinates across resume/retry.

Replaceable interfaces:

```python
plan_catalogue_scope(catalogue, filters, limits) -> CatalogueScopeV1
begin_catalogue_research(scope, reference_inputs, policy,
                         *, clock, identifiers, store) -> ResearchJob
advance_catalogue_research(job_id, expected_generation,
                           *, collector, store, clock, monotonic) -> ResearchProgress
retry_catalogue_research(job_id, listing_id, previous_attempt_id,
                         expected_generation, ...) -> ResearchProgress
finalize_catalogue_research(job_id, *, store, clock) -> ETFResearchSnapshot
publish_catalogue_research(job_id, *, publisher, store) -> PublicationResult
```

`ResearchRecordCollector.collect(listing, snapshot_version, references, budget,
*, clock)` returns one validated schema2 intermediate ETFResearchRecord. Assign
common cache ingestion after collection using injected clock and reserved job
version. Reuse Yahoo normalization/exact proofs/reference validation. Intermediate
coordinates never claim final snapshot ingestion. Existing fetch_snapshot remains
compatible in behavior/signatures.

| Resource | Default | Allowed ceiling/range |
| --- | --- | --- |
| Requested listings |100|1..100|
| Listings per explicit advance |5|1..10|
| Attempts/listing/job |2|1..3|
| Yahoo HTTP attempts/listing attempt including auth |12|1..12|
| Yahoo request timeout |10s|positive, <=10s|
| Advance collection deadline |300s|30..600s|
| Yahoo response body |2MiB|positive, <=2MiB|
| Normalized cached record |256KiB|<=256KiB|
| Canonical job snapshot/evidence payload |32MiB|<=32MiB|
| Catalogue input blob for this path |32MiB|<=32MiB|

Bound actual Yahoo session requests, including auth/internal retries, remaining
time and bytes while receiving. Counting collect calls alone is insufficient.
One metadata attempt at adapter level; retries explicit job attempts. A latched
budget failure must fail the attempt even if an optional accessor catches it.

Preserve BND issuer path:16MiB/25000rows/90s bounds. Reserve its maximum time and
two requests before invoking; stop before starting if remaining advance budget
cannot cover it. Count calls separately; no parser/source/freshness changes.

Successful cached records immutable including cache coordinates. Resume reuses
them without providers/reference reads/replacement/rebinding. Explicit retry
collects only unsuccessful/ambiguous attempts within limits, never successful
records. Preserve complete normalized values/missingness/units/providers/URLs/
observation times/numeric and exposure proofs/listing associations. Finalization
creates detached destination copies, never edits cached successes.
Persist attempt started before provider, then validated result/sanitized failure.
One advance/retry/publish writer/job: bounded lock, generation comparison, atomic
manifest replacement. Crash with started attempt is ambiguous, requiring explicit
retry identifying that attempt. Rerun/status/cache/dashboard refresh never retries.

Failure retains requested membership. Stop advance at failure, keep earlier
successes, later members pending. Exhausted attempts block job. Fresh collection
requires explicit new job/version; never reset old job. Normal missingness/source_error
fields remain records, not manufactured qualification; whole-record failure,
identity mismatch, malformed data or bound breach does not count researched.

Finalize only after revalidating exactly one complete successful cached record per
requested member, exact symbol/exchange and no extras. Validate cached input before
coordinate replacement; replacement cannot sanitize invalid input. Under job lock
and generation comparison capture UTC T_final after collection is complete; it
cannot precede created_at or any cache ingestion. Inconsistent clock blocks.
Create detached canonical fields replacing only ingested_at with T_final, keeping
reserved version and every source fact/proof exact. Snapshot own ingested_at is
T_final. Validate complete schema2/membership and assess every preserved observed_at
against T_final with unchanged field-specific freshness/future tolerance. Permitted
source skew remains intact, never clamped. Aged successes require separate fresh
job, not replacement.

Atomically persist finalization record with complete canonical payload/version/
T_final/digest before publication. This record is authority; coordinates become
immutable at atomic commit. Precommit crash means no canonical snapshot; explicit
finalization retry may choose later T_final and recheck unchanged cache/freshness.
Committed but lost acknowledgement recovers/validates exact record without new
time or rebuild. Corrupt/incomplete/contradictory committed record fails closed.
After finalization all reads/resume/finalize reuse exact canonical payload without
coordinate/provider changes. New/inactive publication assesses current injected
time; exact active retry keeps existing verification-before-freshness exception.
Staleness cannot authorize rebinding/source refresh. No cross-job mixing/cache reuse,
automatic refresh or directory-wide scan. Reads expose original ages.

## 4. Reference inputs (INV105-4)

Preserve ReferenceFactsFile schema1, ten-record/1MiB limit globally. New collector
accepts up to ten existing-format files, combined100records/10MiB. Validate full
set before provider calls: reject duplicate keys even identical, foreign records,
exchange mismatch; preserve ISIN/group/unit/attribution/currency checks and explicit
missing identity for unsupplied records. Pin normalized validated inputs and digest
in ignored artifact; resume never rereads edited files. Intermediate reference
fields use detached truthful cache coordinates. First fresh-job canonical
finalization assigns destination coordinates per section3 preserving entire source
tuple; this completes fresh collection, not rebinding a canonical snapshot.
Canonical retry/reactivation/retrieval/restoration never rebind reference fields.

## 5. Snapshot/publication (INV105-2/4/5)

Retain numeric schema2/document representation, no schema3 or new field/entity
family. Catalogue snapshot universe_id=catalogue-research-v1,
universe_version=scope.digest, exact full membership in listing-ID order, immutable
job reserved immutable version/common canonical ingestion time committed at
finalization. Job creation/cache ingestion stay operational metadata outside
canonical snapshot/graph state. Existing universe fields bind scope into
documents/fingerprints; retained manifest recomputes bound digest.

Persist full validated canonical snapshot atomically before stores. Reuse
rag/snapshots.py:publish_research_snapshot, Chroma stage/readback then Neo4j
lock/CAS activation. <=100 keeps whole-snapshot publication bounded; no partial
activation. Preserve immutable version/digest/membership/fingerprints, previous
active on confirmed precommit failure, uncertain lost-ack outcome, exact active
retry verification before freshness, original payload/freshness for reactivation.
Record publication started/outcome; lost acknowledgement cannot imply rollback.
Explicit retry loads committed canonical payload directly, verifies actual stores,
never rebuilds from cache or refetches Yahoo/reference/FX. Prior active remains
reachable until activation. Existing retention applies;
automated staged/history cleanup outside scope.

## 6. Retrieval and JSON (INV105-4/5)

Add `CatalogueStore.read_version(version, *, max_bytes)` for immutable lookup.
Fresh retrieval validates pinned version/re-resolves scope; never current pointer
substitution. Replaceable exact-snapshot reader:

```python
load_catalogue_scope(request: CatalogueRequestV1) -> list[GraphEnrichedSource]
```

Live adapter requires Neo4j active identity=requested snapshot; authoritative exact
manifest membership/count/schema; all exact-ID Chroma documents and fingerprints;
each document universe ID/version/advisory marker/symbol/exchange matches scope;
source-linked graph contexts; active-pointer recheck. Return listing-ID order,
distance=None, no semantic-ranking claim. Changed pointer, missing/extra row,
wrong context, bad fingerprint/mixed identity/unavailable pinned catalogue reject.
No fallback to six, unversioned data, another snapshot or partial available rows.

Optional strict CandidateEvidenceBundle.catalogue_context contains exact request
and retrieved listing identities. requested_limit1..10 means shortlist capacity;
new candidates pool is complete scope<=100. Ready requires exact membership and
matching health observations. No-context retains all current length constraints
and exact dumps; context mandates schema2/us-eu-v1. Empty blocked outcomes retain
schema2/errors; never infer legacy from empty. Explicit catalogue branch/shared
parser in select_candidate_evidence; no ordinary limit enlargement or slicing.

No new top-level graph keys/operation stages. Nested JSON-mode dumps only;
duplicate JSON keys/nonfinite values/null or unknown markers/mixed modes/partially
removed extensions reject.

## 7. Pure shortlist (INV105-3/4)

After complete upstream validation and unchanged screening/category/group
classification, before _select_subset. Catalogue pool<=100 can be classified;
only shortlist<=10 enters exhaustive enumeration. Ordinary early over-ten failure
unchanged. Full-pool same-ISIN/group contradictions and consumed-field freshness
checks cannot be hidden by omissions.

Algorithm `sleeve-category-round-robin-v1`:

1. Compute existing exact growth/defensive targets. Usable listings pass existing
   screening, supported canonical category and economic-identity requirements;
   alternatives of one group each count usable listings.
2. Capacity=min(requested_limit, construction_policy.max_candidate_pool_size)<=10.
   Zero-target sleeve candidates cannot enter, reason zero_target_sleeve.
3. First consider candidates with economic group not represented yet.
4. At zero-based slot j select available sleeve maximizing
   `(j+1)*target_bps[sleeve]-10000*selected_count[sleeve]`; growth wins ties.
5. Within sleeve select available category with fewest shortlisted members,
   ties normalized category string. Within category smallest tuple
   (economic_group_id, share_class_id, exact_listing_id).
6. Continue until capacity or no unrepresented group. Remaining space repeats
   same process over remaining alternatives without unrepresented-group restriction.
   Never pre-collapse alternatives. Shortlist order becomes unchanged constructor
   upstream order; largest-feasible-subset/tie-breaking remain exact.

This covers policy sleeves/categories/groups, not returns/fees/currency preference
or inferred risk. Base currency cannot reorder. It may miss a globally feasible
combination: keep existing blocked reason plus explicit bounded-selection limitation.
No second shortlist/wider search/relaxation/cap increase.

Optional PortfolioConstructionBundle.catalogue_selection, omitted when absent:
algorithm, scope/snapshot/input digests, capacity/exact targets, usable count,
ordered shortlist IDs, one disposition/requested listing, attributed document/listing
IDs and selected group representative where applicable. Reasons: existing screening,
category/identity reasons, zero_target_sleeve, shortlisted_sleeve_category_coverage,
bounded_shortlist_omission. Shortlisted/final positions/ineligible distinct.
Unreached counts null with reason, never fabricated zero.

validate_portfolio_draft independently enforces recomputed shortlist membership.
Persisted construction/dashboard/review/explanation-request validation recompute
same report/draft. Explanation allowlists remain selected-position-only; model
cannot choose membership or promote omitted candidates.

## 8. Receipts, FX, revisions and restore (INV105-4/5)

Full request in profile binds retrieval input digest. Require profile/evidence
request equality at retrieve_candidate_evidence, RevisionRuntime.validate_output,
construction and review restoration; valid different-request evidence rejects.
Preserve prepare/execute, synchronous started receipt, one-use permit, succeeded
artifact reuse and exact failed/ambiguous retry. Full pool/context in output digest.

Preserve Issue104 needs_rate on full retrieved pool and one-shot ECB inside existing
retrieval operation. Do not move after screening/shortlist. Constructor still
requires FX for selected cross-currency positions including zero cash. No Issue115.

Existing thread cannot add/remove/change mode or pinned request; new scope/snapshot
requires new thread. Other profile revisions retain pinned request and existing
invalidation/base rules. Evidence refresh retries pinned active snapshot, never newer
publication. Screening/construction revisions recompute from persisted full pool
without catalogue/reference/retrieval/clock/FX calls. Explanation revisions preserve
construction. Restore validates retained request/evidence/report/source identities/
receipts/artifacts at persisted check time, without catalogue/store/provider reads.
Thus changed pointers do not break valid offline restored reviews; fresh retrieval
still performs active-pointer checks. Existing closed-retriever lifecycle rules remain.

## 9. Dashboard/coverage (INV105-1/3, AC105-2/6)

Explicit US/EU catalogue mode; legacy creation unchanged. Preparation panel actions:
preview scope, begin job, collect next batch, retry exact failed/ambiguous attempt,
publish, use published scope for new review. Status/search read-only; reruns never
advance/provider/publish automatically. Preview full matched/requested counts,
visible over-limit rejection, bounded paginated display without membership changes.

Separate discovered (plus direct-only/combined), requested, researched successful
validated (must equal requested for publication), usable pre-shortlist,
shortlisted, final positions. Show failures/missing/stale/category/identity gaps,
duplicate groups/omissions/provider limits. Not-evaluated differs from zero.
Cached snapshots retain original ages. Catalogue completeness implies neither
research completeness nor eligibility/suitability/ready portfolio.
Keep all helpers before final main() invocation; actual script-entry tests required.

## 10. Acceptance and focused tests

| Frozen ID | Required observable evidence |
| --- | --- |
|AC105-1|Full contract persisted, independent challenge and coordinator approval before owner edits; gates bind exact capsule generation/digest and handoff.|
|AC105-2|Versioned fixture>=240 US/EU listings, resolved scope>=40, ready outside-six portfolio. Actual Streamlit AppTest runs scope/batches/publication/review via production orchestration with injected provider/store doubles.|
|AC105-3|Actual request/body/deadline/record/payload limits; intermediate failure retains successes, no partial activation, explicit retry/resume without timestamp renewal, exhausted block. Crash at started/result/payload/staging/activation preserves prior-active or truthful uncertainty.|
|AC105-4|Same inputs produce identical ordered report/draft; input/provider permutation invariant; after-first-ten relevant members enter, irrelevant first-ten do not monopolize. Contrasting conservative-income/aggressive-growth change sleeve targets/shortlists when warranted; exclusion changes usability; categories/groups/feasible alternatives covered; instrument enumeration input<=10.|
|AC105-5|Publish -> exact retrieve -> screen -> shortlist -> portfolio -> JSON checkpoint -> offline restore; original timestamps,10000bps,exact cash/FX. Tampered scope/version/membership/universe/manifest/Chroma/fingerprint/graph/report/receipt/request reject.|
|AC105-6|Each displayed fixture/job count, overlap/direct counts, omissions, unknown counts/limits asserted; ADR/usage/product/architecture/iteration evidence complete.|

Additional required cases within those IDs:

- Scope0/100/101, duplicate/conflicting identities, unsupported symbols,
  malformed/oversized catalogue. Over-limit rejects before calls.
- Ten-file reference limits, duplicates/foreign input, edits after start, missing
  identity; complete input validation before providers.
- Resume/exact fresh cached reuse zero calls; stale completion blocked; no cross-job
  blending; swallowed optional-accessor transport breach still fails.
- Readback missing/extra ID, pointer change, Chroma failure, Neo4j CAS, lost ack.
- Full-pool same-ISIN contradiction outside shortlist blocks; missing category/group
  explicit excluded, stale/contradictory provenance blocked.
- Cross-currency selected zero cash needs FX; unselected cross-currency retains
  current retrieval-stage needs_rate behavior.
- Bounded shortlist infeasible although another full-scope subset works: report
  original blocker/limitation, no widening.
- Downstream/restore zero calls; succeeded receipt reuses full bound pool.
- Explicit null/removal/mixed markers and ordinary over-ten bundles reject.
- Preserve Issue104 actual Streamlit entry, USD/EUR revision, empty/all-invalid/
  all-stale schema2, offline restore, exact legacy-empty dumps/nonempty downgrade
  tests; Issue99 dataset bytes and legacy/snapshot/catalogue/revision suites.

Owner focused then full offline pytest/Ruff/mypy/build/workflow/configuration gates;
independent content-bound implementation review. Synthetic positives establish
contract behavior, never live Yahoo completeness.

## 11. Docs, risks and escalation

New ADR for opt-in request/full bounded pool/jobs/complete publication/algorithm;
design/implementation iteration, usage/coverage and measured checks. Update current
vision/architecture to explicitly requested bounded catalogue research, retaining
no forced catalogue-wide ingestion. Do not rewrite accepted ADR0014/15/27/38/39;
explain new opt-in extensions to old universe/pool bounds.

Risks:100 listings may still lack live identity/category/concentration and yield
no portfolio; shortlist may miss feasibility; larger checkpoints require mandatory
count/byte bounds; slow jobs age out without renewing evidence; yfinance shared
session requires one bounded shared exclusion across catalogue/research operations
so another caller cannot replace budgeted session; closed graph-store lifecycle
cannot be revived; hashes bind content, not authenticated truth of source curation.

Inability to enforce actual transport, exact legacy serializers, offline restore
or complete membership is blocker INV105-2/4/5, not authority to weaken/redesign.
Return concrete evidence to coordinator and use finite arbitration/gates.

Architect performed no writes, tests or provider calls. Only coordinator's new
ledger was untracked. DESIGN_READY, pending challenge and coordinator approval.

## Generation2 amendment A105-1

Fresh separate read-only `/root/issue105_design_reset`, design_architect/
gpt-6-astra/high, clarified only the timestamp lifecycle above. Initial challenge
remains failed. Original gen1 capsule/digest above remains historical; current gen2
binding lives in ticket ledger. No frozen IDs/scope/non-goals/owner/other limits or
financial/replay/FX rules change. No source edits/tests/provider calls by architect.

Focused refinements to AC105-3/5:

1. Job Oct23 08:00, late collection Oct24 08:00/source07:59, finalize08:01: all
   canonical fields/snapshot Oct24 08:01; observation07:59 unchanged; job creation
   Oct23; earlier cache bytes unchanged.
2. Resume/failed retry preserves successful cache/source tuples and calls only
   failed/ambiguous member; detached final fields share destination time and JSON
   roundtrip consistency.
3. Pre-finalization-commit crash calls no stores; explicit retry may choose later
   time/recheck unchanged sources. Postcommit lost ack recovers identical bytes/
   version/time/digest without rebinding/providers.
4. Unchanged age/skew boundaries including BND; later ingestion cannot rescue stale
   reference/Yahoo; allowed future source skew intact, excessive blocked.
5. Delayed new/inactive publication stale before staging; exact active retry verifies
   immutable stores unchanged. Reactivation keeps payload and current freshness.
6. Invalid cache coordinates reject before replacement; altered source/proofs/mixed
   canonical ingestion/conflicting digest fail. Offline restore uses canonical
   coordinates/persisted check time without clock/provider/reference/store calls.

New collector time assignment/job finalization only; canonical schema2/field names/
graph keys/Issue104 receipts/FX/legacy dumps unchanged. Document in new ADR/usage;
do not rewrite ADR0008/27/39. Long jobs can age out; precommit crashes can yield later
eventual ingestion, neither renews source age. Failure to distinguish absent from
committed-unacknowledged finalization blocks INV105-2/5. DESIGN_READY, pending
fresh independent challenge and coordinator approval.
