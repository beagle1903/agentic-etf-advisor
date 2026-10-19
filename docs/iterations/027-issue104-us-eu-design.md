# Issue104 consequential design handoff

Architect `/root/issue104_design`, `design_architect`, gpt-6-astra/high, returned
DESIGN_READY on 2026-10-18. Capsule `issue-104-us-eu-currency`, generation 1,
digest `4ef81eb8df7c89f8dbd0e7f36720cc2a9544467b4c5e5c6763967ee5b6d1f3a6`.
Read-only handoff; independent challenge and coordinator approval are required.
No source changes, tests, runtime publication or saved-review mutation occurred.

## Scope, execution path and non-goals

Explicitly selected `us-eu-v1` covers attributable listing identity, USD/EUR cash,
deterministic construction, explanation, presentation and restoration. Retain the
existing US contract for legacy inputs/checkpoints. Current paths are:

- `cli.publish_research_universe`: explicit universe membership.
- `data.yahoo_research.YahooResearchAdapter.fetch_snapshot` / `_build_record`.
- `research.models.ETFResearchRecord` / `ETFResearchSnapshot` and
  `encoding.validate_document`: canonical content and fingerprints.
- `rag.evidence.HybridCandidateEvidenceRetriever.retrieve` /
  `select_candidate_evidence`: current `us_market` requirement.
- `domain.screening.screen_candidate_evidence`.
- `domain.construction.construct_model_portfolio`: upstream revalidation,
  bounded subset selection and exact allocation.
- `explanation.models.build_explanation_request` and reference indexes.
- `dashboard.review_payload`: complete-chain recomputation.
- `domain.revision.plan_revision` and `graph.revision.validate_revision_state`:
  immutable artifacts and retrieval/provider receipts.

Iteration026 diagnostics remain unchanged. Relevant ADRs: 0010, 0014, 0015,
0021, 0027, 0028, 0033, 0034, 0038. No catalogue-wide ingestion, candidate picker,
different-fund overlap analysis, optimization, brokerage eligibility, suitability,
tax, authentication, trades, external financial writes, saved-review migration or
unrelated cleanup.

## Listing and source contract: INV104-1/4, AC104-1/2

Reuse exact `yahoo-listing-map-v1` exchange/country mapping in `catalogue/mapping.py`:

- US: `ASE BTS CXI NAE NCM NGM NMS NYQ PCX`.
- EU: `VIE BRU PRA CPH TAL HEL ENX PAR BER DUS EUX FRA GER HAM HAN MUN STU ATH BUD ISE MDD MIL TLO RIS LIT AMS DXE WSE LIS BVB MAD MCE STO`.

Only that mapping establishes country/region. UK, Swiss, OTC/deleted, unmapped
venues and EU countries without mapped venues are unsupported. Listing identity
is `(yahoo_finance, exact normalized symbol including suffix, exchange)`. Never
merge by stripped symbol, name, currency, domicile, benchmark or geography.
Contradictory exchanges for one symbol in a snapshot block the contract.

New canonical `ResearchField[str]` fields:

| Field | Unit | Meaning |
| --- | --- | --- |
| listing_exchange | yahoo_exchange_code | Exact source exchange |
| trading_currency | iso4217 | USD or EUR |
| price_unit | quote_unit | Exact USD or EUR major unit only |
| share_class_id | isin | Checksum-valid share-class ISIN |
| economic_group_id | issuer_fund_id | Namespaced issuer fund/subfund identity across classes |
| domicile | iso3166_alpha2 | Optional with explicit missing reason |
| fund_base_currency | iso4217 | Optional source fact |
| share_class_currency | iso4217 | Optional source fact |

Retain quote_type, market, category, fee, volume, composition and exposure fields.
Market is descriptive in the new contract, never an exchange substitute.
`us_market` with EU exchange or non-US market with US exchange is conflicting;
missing market does not defeat independently verified exchange identity.
ETF verification is canonical source `quote_type=ETF`, equal to flattened data;
it is source classification, not regulatory certification. Missing/non-ETF fails
explicitly. Catalogue membership supplies no advisory proof.

Every new field retains provider, URL, observation/ingestion time, snapshot version,
unit and value-or-missing reason. Canonical and flat copies agree. Consumed
available fields use the persisted check time and configured freshness window:
default 120 hours and five-minute future tolerance. BND's monthly exception
remains limited to its two composition fields, never identity, currency, category
or FX. Missing exchange/type/currency/unit gives explicit unknown/exclusion;
unsupported values fail; stale available consumed data or contradictory copies
block the complete stage under ADR0021.

GBp, GBX, GBX/GBP, US cents and all subunit quotes are unsupported. Never uppercase
GBp into GBP, implicitly divide by 100 or infer units from suffixes. No prices,
quantities, orders or price-based liquidity calculation are added.

## Source capability and bounded reference facts

Yahoo rich collection copies `info.exchange`, `info.currency`, `info.quoteType`
with existing source `regularMarketTime`. Set price_unit only from exact supported
currency. Never invent fund/share-class identity from ticker.

Inject replaceable `ReferenceFactsProvider.lookup(symbol, exchange)` returning
attributed reference fields or explicit missingness. A bounded production reader
uses an explicitly supplied local JSON file via publication `--reference-facts`:

```text
schema_version: 1
records: [{symbol, exchange,
  share_class_id: ResearchField[str], economic_group_id: ResearchField[str],
  domicile: ResearchField[str], fund_base_currency: ResearchField[str],
  share_class_currency: ResearchField[str]}]
```

At most ten unique listings. Reject duplicates, unknown keys, mismatched
symbol/exchange, malformed identifiers/provenance and records outside the supplied
universe. Available identity facts cite issuer/exchange material. File access
cannot refresh observation times. Absent file/record gives explicitly unsupported
identity fields; malformed supplied evidence fails collection. Ship no synthetic
live defaults. Keep packaged six-symbol membership and existing explicit universe
file selection; no Issue105 ingestion work.

Architect primary-source observations, 2026-10-18 17:24:07–17:28:29 UTC:

- [Deutsche Börse VWCE](https://live.deutsche-boerse.com/en/etf/vanguard-ftse-all-world-ucits-etf-usd-accumulating?currency=EUR)
  identifies ETF, ISIN IE00BK5BQT80 and EUR trading currency.
- [iShares CSPX](https://www.ishares.com/uk/individual/en/products/253743/ishares-core-s-p-500-ucits-etf?siteEntryPassthrough=true&switchLocale=y)
  identifies IE00B5BMR087, Irish domicile, USD fund/share-class currency and EUR
  listings on Amsterdam, Xetra and Borsa Italiana.
- CSPX Amsterdam trades EUR. Issue99 CSPX.AS/USD is synthetic, never measured
  source evidence.
- Yahoo profile pages were inaccessible. Live EU fee/category/volume/holdings
  completeness and ready live EU portfolios were not demonstrated.

Positive construction fixtures may combine those real attributed identity facts
with prominently synthetic metrics. They prove contracts, never live coverage.

## Economic identity: INV104-2, AC104-3

Require attributed share-class ISIN and economic group for new-contract construction.
Group means issuer fund/subfund, not umbrella, fund family, ticker, benchmark or
share class; retained official source establishes grouping. Distribution/hedging
classes of one fund conservatively remain one group.

- At most one selected position per group.
- Same ISIN with different groups in one bundle blocks.
- Same group across ISINs/exchanges is valid, never independent positions.
- Missing group/ISIN excludes with `economic_identity_unknown`.
- Keep alternative representatives in feasibility search. Reject repeated-group
  subsets, then existing largest-subset and lexicographic upstream-index tie-break.
- Otherwise eligible omitted duplicate receives `duplicate_economic_exposure`
  and selected representative listing ID.
- Distinct groups do not establish independent risks. Different funds tracking
  one index remain distinct; holdings overlap is separate work.

## Financial rules and FX: INV104-3/4, AC104-4

Preserve exact normalized category map: growth Large Blend, Large Growth, Foreign
Large Blend, Diversified Emerging Mkts; defensive Intermediate Core Bond.
Trim/collapse/case normalization only. No European aliases or prose inference.
Missing/unsupported category excludes; insufficient sleeve coverage blocks;
stale available or contradictory provenance blocks complete construction.

Keep fee <=1%, volume >=100000 listing shares/day, concentration <=60%, sector
rules. Volume is neither turnover nor fund-wide cross-listing volume; no venue
sums or FX share-count conversion. Preserve 3–5 positions, pool <=10, 500–8000 bps
per position, 8000 bps category limit, total10000 bps, sleeve targets and remainders.

Only USD/EUR base/trading currencies, both exponent2. New profile money is strict
nonnegative integer minor units, range 0..100000000000000:

```text
advisory_contract: "us-eu-v1"
base_currency: "USD" | "EUR"
initial_investment_minor: integer
recurring_monthly_minor: integer
```

Retain non-money profile fields, reject legacy `_usd` keys in this branch. UI
decimal input converts once with exact decimal arithmetic, never float x100.
New policy cash objects `initial_investment` and `recurring_monthly` contain
`currency,total_minor,growth_minor,defensive_minor`. Growth cash is exact half-up
rounding of total_minor*growth_bps/10000; defensive is remainder. Position cash
uses existing sleeve largest remainders. Initial/monthly reconcile independently;
zero cash and positive weights with zero minor cash remain valid.

FX source is [ECB daily reference feed](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml),
USD units per EUR. [ECB policy](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
describes working-day reference rates, not executable prices. Architect bounded
GET returned HTTP200, effective2026-10-16, lexical USD rate1.1253 during the above
interval. No raw response file retained.

Inject `FxReferenceProvider.fetch_eur_usd() -> FxReferenceObservation`. Fixed HTTPS,
TLS verification, no redirects, ten-second timeout, <=64KiB response, one attempt
per retrieval operation. Reject DTD/entity declarations, duplicate date/USD,
missing date/rate and malformed XML. No fallback, inverse feed, interpolation or
automatic retry. Persist inside new candidate_evidence:

```text
fx_reference: {
  status: available|missing, provider: ecb, source_url: fixed endpoint,
  effective_date: YYYY-MM-DD|null, observed_at: UTC datetime,
  base_currency: EUR, quote_currency: USD, rate_decimal: string|null,
  missing_reason: null|not_requested|source_unavailable
}
```

Rate is canonical plain positive decimal: no exponent/plus/redundant leading or
trailing zeros; <=18 significant digits, <=10 fractional places, inclusive range
0.000001..1000000. Decimal/rational arithmetic is authoritative.

Validate against evidence checked_at, never constructor wall time. Effective date
cannot exceed checked_at UTC date. Conservative age anchor is effective-date
midnight UTC, explicitly not a claimed publication timestamp. Age <=120hours
inclusive; +1microsecond blocks. observed_at cannot precede effective date and
can exceed checked_at by <=5minutes.

FX required when selected draft has trading currency different from base, even
zero cash. Select under unchanged financial rules first; missing FX cannot alter
selection. Required missing/stale/future/conflicting FX blocks with distinct stable
codes. Unsupported currencies cannot convert. All retrieved same-currency candidates
make no FX request; same-currency selected portfolios require no rate.

Positions carry base_currency, initial_base_minor, recurring_base_minor,
trading_currency, initial_trading_minor, recurring_trading_minor, and
fx_reference_id null or canonical observation digest. EUR->USD multiplies exact
rate, USD->EUR divides rationally; round each converted amount once half-up to
target minor units. Same currency copies exactly with no FX ID. Never sum trading
amounts across currencies or reverse-convert rounded values to validate base cash.
Weights/base totals never depend on FX; conversions are illustrative, not proceeds.

## JSON, compatibility and persistence: INV104-5, AC104-5

Use semantic `advisory_contract: us-eu-v1` independently of ADR0027 numeric encoding.
Keep numeric research schema2; no schema3 or weakened lossless encoding. Marker
applies to profile, research snapshots/records/source metadata, evidence, screening,
policy/construction and explanation request/bundle. New research requires schema2.

- Absent marker is exact existing US/USD contract. Legacy serializers omit marker
  and new fields, preserving dumps, digests, fixtures, references and checkpoints.
- Unknown/null markers or new fields in legacy envelopes reject. Reject mixed
  semantic contracts in bundle/workflow.
- New profile plus legacy evidence blocks `advisory_contract_mismatch`; no inferred
  exchange/USD. Old schema1/2 reviews stay on original path, never upgraded.
- Changing contract in saved revision is unsupported; new review required.
- USD/EUR base changes within new contract require profile patch with both money
  amounts explicitly, preventing relabelling.

Extend validate_document for fields/rendering/units/flat copies, preserving legacy.
All provenance binds snapshot digests, document fingerprints, immutable manifests
and readback. Removed marker with surviving new fields fails downgrade validation.
No new AdvisorState top-level key. Clients/readers stay outside JSON. FX belongs to
existing retrieval receipt/output artifact, not third operation stage. Retrieval
input binds full profile, so base change invalidates digest.

Profile revision restarts validation and clears evidence/FX/screening/construction/
explanation. Evidence revision refreshes research/FX. Later-stage-only revisions
reuse bound evidence/check time without external calls. Restore validates
reproducibility, never present-day freshness; explicit evidence revision refreshes.

## Explanation and dashboard

New policy refs: policy.base_currency, policy.initial_investment,
policy.recurring_monthly. Keep legacy names unchanged. New construction references
expose listing/category/share-class/group identity, trading currency, exact base
and converted amounts and FX source/date/rate/digest. Every monetary record includes
currency and minor exponent. Sources remain selected-position-only.

New monetary prose requires explicit `USD amount` or `EUR amount`, either order.
Validate each pair against exact cited structured monetary records. Reject $/EUR
symbol shorthand (including euro glyph), unsupported currency tokens, wrong labels,
and amounts supported only by unrelated numeric fields. Keep existing reference,
subject, numeric, safety/refusal checks. This bounded structural grounding does not
claim general semantic entailment. FX descriptions may cite only actually used
observations; source URL/effective date come from validated state, never model text.

Dashboard exposes optional US/EU mode/base currency, defaults legacy. Render base
cash with explicit currency, exchange/region separately from domicile/fund/class
currency, unknown identity exclusions and attributed FX. No catalogue picker.
Creation/revision controls, review_payload, approval/restoration/explanation all
dispatch identically and reject mismatched amounts, labels, groups, FX or artifacts.

## Acceptance and focused verification

- INV104-1/AC104-1/2: all mapped exchanges; US/German/Dutch positives; UK/Swiss/OTC/
  unknown negatives; missing/conflicting exchange/type, non-ETF; domicile/geography
  cannot establish listing; USD fund/class versus EUR trade; subunit rejection.
- INV104-2/AC104-3: same-ISIN listings, different classes in one sourced fund,
  alternative feasible representative, unknown exclusion, contradictory groups
  block, same-index different funds not silently merged.
- INV104-3/4/AC104-4: legacy-equivalent tagged USD vectors, EUR base, both conversion
  directions, zero/one minor cash, remainders, missing/stale/future/conflicting FX,
  exact freshness edges, unsupported category and share-volume units.
- INV104-5/AC104-5: JSON roundtrip, removed/mixed markers, canonical/flat
  substitution, symbol/exchange/group/FX/amount/currency tampering, restore/interrupt
  equality, base revision invalidation, receipt reuse without clock/network.
- INV104-5/AC104-5: exact monetary refs pass; wrong currency or unrelated numeric
  ref fails; unselected listings/unused FX fail; legacy explanations unchanged.
- AC104-5: retain Issue99 bytes/expected legacy outcomes; separately version US/EU
  evaluation with synthetic metrics and limits; same-US-case exact vector comparison.

Extend research/evidence/screening/construction/dashboard/revision/explanation/
publication/analysis tests and isolated injected ECB parser/transport tests. Run
required offline tests/lint/type/build/workflow gates, then independent review.
No live store/provider publication or saved-review mutation required.

New ADR, design/implementation iteration, vision/current architecture, reference/FX
usage, compatibility and actual live coverage limits are required. Preserve history.
Risks: incomplete Yahoo metrics, curated identity coverage/taxonomy, stale reference
inputs, conservative date-only FX and consistent dispatch across direct model parsers.
Synthetic fixtures never certify live readiness. No demonstrated blocker prevents
implementation of the bounded contract. Complete handoff must bind challenge and
coordinator approval; it alone does not authorize implementation.

DESIGN_READY

## Generation2 amendment: A104-1 reference-fact publication binding

Fresh separate architect `/root/issue104_design_reset`, gpt-6-astra/high,
returned DESIGN_READY. This amendment resolves the recorded ambiguity without
changing frozen scope, owner, financial rules or acceptance IDs. The original
challenge remains FAIL; fresh challenge and coordinator approval are required.

Choose publication-metadata rebinding during fresh collection, exclusively for
the five reference fields supplied by ReferenceFactsProvider/--reference-facts.
Retain the schema1 file shape, limits, identifiers, missingness and source rules.

A supplied file is reusable input to fresh research collection. Validate its full
ResearchField objects before binding. Required input ingested_at/snapshot_version
must satisfy existing timestamp/type/syntax constraints, but need not match the
destination snapshot. They are publication coordinates, not source recency.

Create detached destination fields after validation. Preserve the complete
normalized source tuple exactly: `(value, missing_reason, unit, provider,
source_url, observed_at)`, and validated symbol/exchange association. Replace only
ingested_at with the destination snapshot's single captured ingestion time and
snapshot_version with its requested version, for available and missing fields.
Never mutate file/provider objects/prior snapshots/checkpoints. Validate newly
constructed fields and the complete snapshot; unchecked copies are insufficient.

Preservation means equality after existing typed normalization, including UTC.
File access, binding, retry and publication never replace reference observed_at
with clock/file/Yahoo/destination-ingestion time, or issuer/exchange citation with
Yahoo provenance. Input publication coordinates add no extra graph-state fields.
Destination ingestion means ingestion into that snapshot, not first-ever ingestion
or historical-file-chain evidence.

Strict-parse and type-validate the complete file before extraction. Duplicate keys,
nonfinite constants, unknown keys, invalid publication coordinates, identifiers,
provenance, missingness, duplicate listings and invalid listing/universe association
fail collection. Rebinding cannot sanitize invalid input by overwriting it first.

Existing publication freshness examines preserved source observations after
binding. Consumed checks use persisted checked_at; default120hours/future5minutes
unchanged, no identity monthly exception. Current Yahoo/new ingestion cannot
rescue expired reference facts.

Binding occurs only in fresh collection. Canonical payload loading, active retry,
reactivation, retrieval and restoration/replay never rebind or read the file to
repair retained artifacts. Existing canonical payloads remain retry authority.
Destination canonical/flat metadata, rendered documents, fingerprints, digest,
manifests and artifacts include destination coordinates plus preserved source
tuple. New version/time has new content identity; prior content remains immutable.

Focused refinements to AC104-1/3/5:

- T0 file builds two fresh T1/T2 snapshots with different destination versions/time
  and identical source facts/observations. Snapshot/document validation and JSON
  roundtrip pass; digests differ; file/input objects remain unchanged.
- Age120hours passes, +1microsecond fails; future5minutes passes, +1microsecond
  fails despite current destination/Yahoo time. Changing only valid input
  publication coordinates cannot refresh source evidence.
- Invalid input ingestion/version rejects before replacement. Existing malformed
  file/listing/identity cases continue failing.
- T0 coordinates substituted into T1 fail consistency. Source observation,
  citation, ISIN/group or canonical/flat substitution fails semantic or independent
  expected-digest/fingerprint validation. Mutable fingerprint recalculation cannot
  defeat immutable expected fingerprint.
- Canonical retry/restoration retain original coordinates/check time, make no
  reference-provider call and cannot absorb later local-file changes.

Interface supplement: reusable input preserves its validated source tuple; fresh
collection alone binds destination ingestion/version before ordinary serialization
and integrity checks. No new provider method, financial interface, file schema,
top-level graph key or legacy change. Preserve FX staging: retrieval may fetch
when any retrieved candidate differs from base; constructor decides selected need.

Document binding in ADR/reference usage/iteration. Structural validation/digests
cannot authenticate whether freshly curated facts truthfully quote their source;
they validate structure and alteration against bound content. This limitation
does not authorize fabricated live defaults.

DESIGN_READY (generation2, pending independent challenge/coordinator approval)
