# Issue 101: reported-holdings overlap design

Status: DESIGN_READY; separate read-only architect `/root/issue101_design`,
`design_architect`, `gpt-6-astra`, high. Human approved this chat on 2026-10-25.
This coordinator transcription is the complete operative handoff supplement for
capsule `issue-101-reported-holdings-overlap`, generation 1, digest
`b93474d07d80f9030d1110fa5b564ec80a29108bd7739df6f24a4920248c6e41`.
Scope S101-1, INV101-1..4, AC101-1..4 remain frozen in the ledger.
Owner: `/root/issue101_owner`, implementation_worker / gpt-6-sol / medium.
Independent challenge and coordinator approval must precede implementation.

## Scope and execution

One ephemeral pairwise diagnostic over existing attributed `top_holdings` measures
reported-list overlap, not complete fund, portfolio or economic exposure. No
normalization, threshold, selection/ranking/weight penalty, optimizer, provider
call, graph expansion, checkpoint field, historical migration or financial-rule
change. Screening, construction, cash, selection and explanation remain unchanged.

`research.models.WeightedExposure` has name, optional provider-local symbol and
weight, with no universal security ID. Yahoo `_holding_exposures` retains every
returned row and decimal proof; do not truncate to ten. Vanguard `parse_holdings`
intentionally retains repeated labels/tickers for distinct ranked bond rows.
`encoding.validate_document` and CandidateEvidenceBundle validate schema/source/
snapshot/numeric contracts; schema1 needs additional consumed-holdings validation
because validate_document returns early for that schema.

Add `src/etf_advisor/dashboard_overlap.py`, used only by the validated Source
evidence view in dashboard_app._render_evidence. dashboard.review_payload already
validates checkpoint/interrupt artifacts and recomputes finance before rendering.
Keep existing dashboard_comparison behavior. load_dashboard_run restores and
validates evidence offline; recompute this diagnostic after restore without a new
restore operation.

## Identity (INV101-1/2, AC101-1/2)

Identity is an exact reported symbol within one provider namespace, with reported
name as an ambiguity check; this does not establish ISIN or economic identity.
Both fields require exactly equal validated provider strings, otherwise
identity_namespace_mismatch. No translation/reconciliation across providers.

Symbol: stripped outer whitespace, nonempty, at most 24 printable ASCII characters
and no whitespace; key is uppercase. Preserve punctuation/suffixes; no exchange
removal, aliases or inferred symbols. Name: stripped outer whitespace, 1..300
printable characters; key is `" ".join(name.split()).casefold()`. Preserve
punctuation, accents, share classes and maturity; no fuzzy matching.

Every row needs a usable symbol, including zero-weight rows. Any repeated symbol
key OR name key within either list makes overlap unavailable, including identical
duplicates and different weights. Never overwrite/deduplicate/aggregate identities
or keep only valid survivors. Across lists, same symbol/different name OR same
name/different symbol makes the pair unavailable. Same symbol/name once on each
side is a valid match. Distinct consistent pairs are simply unmatched.

Official BND repetitions remain valid source evidence; missing/distinguishing
identities make only this diagnostic unavailable. Do not corrupt/reclassify the
snapshot or change ingestion/screening.

## Formula and exact arithmetic (INV101-1/2/3)

Weights are percentage points of fund assets. For matching keys k:
`O(A,B) = sum(min(w_A[k], w_B[k]))`; coverage `C_A=sum(all A rows)` and likewise B.
No coverage division, averaging, portfolio weights, residual holdings, Jaccard
score or extrapolation. Validate every weight and exact sum in [0,100]; assert
`0 <= O <= min(C_A,C_B) <= 100`; never clamp.

Schema2: use existing document_schema, strict_json, decode_exposures,
decimal_value, binary_value and upward checks. Tokens must agree with original
canonical proofs. Calculate `Fraction(decimal_value(source_weight_pct_decimal))`,
not upward binary64 tokens. Schema1: exact Python int or finite float only,
excluding bool/string/other numeric types; Fraction(int) or Fraction.from_float.
These are exact persisted binary64 facts; never invent original decimal proofs.
Reject mixed encodings/malformed markers through existing validators. All sums
and minima use rational arithmetic, no tolerance or ambient Decimal arithmetic.
Signed zero contributes zero without modifying source values/tokens.

Empty available lists yield empty_holdings, not zero evidence. Nonempty valid
explicit-zero lists may yield zero. Missing/stale/future/invalid inputs yield null
overlap. A current structurally/numerically valid side may retain its row sum when
identity is ambiguous, labelled "Reported-row weight sum; identity unresolved".
Invalid numeric/provenance/freshness means null coverage on that side; preserve
valid counterpart coverage. Even coverage100 is no completeness certificate.
Disjoint lists prove only zero overlap under this reported identity rule.

## Validation, freshness, bounds and safe presentation

Receive complete JSON-mode bundle; revalidate a detached copy with
CandidateEvidenceBundle. Mutable model instances cannot bypass validation.
Existing schema2 review failures continue to stop review before diagnostic.
For each consumed field: strict JSON/full ResearchField provenance,
percent_of_fund, valid HTTP(S) attribution, aware timestamps, consistent explicit
value/missingness and top_holdings_status. Validate every row, reject unexpected
keys, malformed labels/symbols/weights, conflicting representations and total>100.
Published field snapshot_version must match published candidate metadata; preserve
local-synthetic semantics rather than rebinding original field coordinates.
Use validate_issuer_pair for official BND, including exactly ten rows and matching
composition provenance; preserve schema2 holdings/concentration validation.

Use persisted bundle.checked_at/health policy only; reuse field_max_age and
is_issuer_field. Official valid BND composition: 1080 hours, zero future tolerance.
Others: existing configured age/tolerance. Exact boundaries are current. Never
borrow document time, ingestion time or current wall time. Different funds may
have different observation dates; display both.

Diagnostic-only limits: <=100 candidates, <=1 MiB UTF-8 provenance JSON per
candidate before reparsing, <=1000 holdings per selected list. Exceeding any bound
yields unavailable without truncation/prefix calculation. These do not alter
ingestion or saved-state acceptance.

Fixed reason vocabulary: invalid_evidence, diagnostic_limit_exceeded,
missing_provenance, the existing four MissingReason values, empty_holdings,
invalid_holdings, conflicting_provenance, stale_holdings, future_holdings,
missing_holding_symbol, duplicate_holding_symbol, duplicate_holding_name,
conflicting_holding_identity, identity_namespace_mismatch. Collect distinct reasons
in deterministic order; identity warning cannot conceal freshness failure. Fixed
messages only, no raw exception/JSON/source body/arbitrary missing reason text.
Plain text/dataframe cells, no unsafe HTML. Preserve validated URL/time, never
sanitize invalid identity into a valid match.

## Pure API and state (INV101-3/4)

`reported_holdings_overlap(bundle: dict[str, Any], left_id: str, right_id: str)
-> dict[str, Any]`. Two distinct exact document IDs in bundle required; invalid
selection raises fixed ValueError, no automatic substitute.

Output JSON primitives only: status available/unavailable, reason_codes,
checked_at, snapshot_version, snapshot_digest, left/right, overlap_pp,
matched_holdings (integer iff available else null). Each side includes document ID,
symbol, status/reasons, count, row sum, validated field provider/URL/observation/
ingestion/field snapshot_version. Exact amounts are reduced
`{"numerator":"<integer>","denominator":"<positive integer>"}`, zero 0/1.
Invalid whole-bundle output exposes no purportedly validated attribution/amount.
No Fraction/Decimal/datetime escapes, no new source proof. Source untouched.

Display amounts half-up to six decimal places using integer arithmetic. Mark
rounded results approximate; positive subresolution values display <0.000001,
never zero. Exact rational available in calculation-details expander.

Persistent JSON/state impact: none. No serializers/checkpoints/receipts/artifact
digests/revision inputs/graph state/source/screening/construction changes. No
provider/database interfaces, side effects or cache.

## Actual Streamlit flow (AC101-3)

Separate multiselect "Choose two candidates for reported-holdings overlap", max2,
exact document IDs and existing symbol labels over full validated pool, including
outside-six/exchange-qualified listings. Zero/one: instruction, no result. Two:
recompute every render. Show overlap or fixed unavailable reasons, both sides'
coverage/status/count/provider/original timestamp/source URL in same visible
section, persisted check time and snapshot attribution. Additional provenance and
exact arithmetic may use expander. Always show:

"Reported holdings only; lists may be partial. This is not complete fund or
portfolio overlap and does not affect selection or weights."

Available zero: "No overlap among these reported identities."
Widget scoped to snapshot identity; reject stale selections. Choices outside graph
state. Existing eight-field comparison/detail views stay available.

## Independent controls (AC101-2)

Use current complete provenance, same provider, unique symbol/name pairs and
canonical schema2 proofs unless specified. X means (X,Holding X).

| Case | Left | Right | Expected |
| --- | --- | --- | --- |
| Disjoint | X12.5,Y7.5 | Z15,W5 | C20/20,O0,matches0 |
| Identical partial | X12.5,Y7.5 | X12.5,Y7.5 | C20/20,O20,matches2, never100 |
| Partial | X12.5,Y7.5,Z5 | X10,Y12.5,W7.5 | C25/30,O35/2,matches2 |
| Explicit zero | X0 | X10 | C0/10,O0,matches1 |
| Missing | null,not_reported | X10 | Cnull/10,Onull |
| Empty | [] | X10 | empty_holdings,Onull |
| Symbol conflict | (X,Alpha)10 | (X,Beta)8 | conflict,C10/8,Onull |
| Name conflict | (X,Alpha)10 | (Y,Alpha)8 | same conflict,C10/8,Onull |
| Duplicate symbol | X10,X5 | X8 | duplicate,C15/8,Onull |
| Duplicate name | (X,Alpha)10,(Y,Alpha)5 | Z8 | duplicate name,Onull |
| Missing symbol | (null,Alpha)10 | (X,Alpha)8 | missing symbol,Onull,no fallback |
| Namespace | providerP,X10 | providerQ,X8 | mismatch,Onull |
| Exact overflow | X60,Y40.00000000000001 | X10 | invalid,Cnull/10,Onull |
| Corrupt late row | X10 then invalid weight | X8 | entire left unavailable,not8 |

Schema2 identical X proof1e-1/token0.1 + Y proof2e-1/token0.2: C/O3/10.
Schema1 identical floats0.1+0.2: C/O10808639105689191/36028797018963968.
Schema2 identical proof10000000000000001e-17/token0.10000000000000002:
O10000000000000001/100000000000000000; substituted token0.1 rejects.
Bool/string/NaN/infinity/negative/missing or noncanonical proof/duplicate JSON keys/
marker mismatch unavailable or rejected, never smaller available result. Preserve
source -0.0/0e0 with calculated zero. Reordering/swapping preserves metric.

Official BND ten current rows weight1 each, repeated (null,Treasury), exact
concentration10: valid source pair, C10, unavailable missing/duplicate identity;
no aggregation. Ordinary age/future exact boundaries current, one microsecond
beyond rejected. BND observation2026-09-01T00:00:00Z/check2026-10-16T00:00:00Z:
1080hours current, +1microsecond stale. Valid midnight BND observation one
microsecond after check: future despite ordinary tolerance. Wrong pair count/URL/
unequal dates/issuer provenance on wrong field rejects before monthly claim.

Use genuinely valid evidence fixtures. Issue100 lightweight fixture has simplified
provenance/noncanonical proof12.3; it is not authoritative for this diagnostic.

## Verification and documentation

AC101-1: independent challenge of this supplement and exact calculations, then
coordinator approval. AC101-2: vectors, fractions, bounds, symmetry, nonmutation,
invalid inputs. AC101-3: actual dashboard_app.py AppTest zero/one/two, partial,
zero, unavailable identity/freshness, adjacent provenance and limitation text.
AC101-4: JSON-roundtrip/restore valid review with provider/catalogue/document/
graph/FX/collector forbidden, then actually render/select pair while forbidden.
Assert unchanged complete serialized state, screening, construction, selection
order/IDs, bps, exact cash/FX and revision/receipt identities. Cover legacy absent
markers and schema2 US/EU/catalogue. Extend existing 40-member catalogue AppTest
with outside-six pair; loading without restored rendering is insufficient.

Focused diagnostic/dashboard/comparison, Vanguard/revision/US-EU/catalogue
regressions, then locked minimal full suite/static/build/workflow gates and
independent content-bound review. No new live provider/real-store claim required.
Add ADR0041, design/implementation iteration records, architecture and usage.

Conservative matching may make bonds/differently named share classes unavailable;
this is uncertainty, never evidence of independent exposure. Dates/partial lists
remain limits; schema1 cannot recover original decimals. New security IDs, aliases,
numeric results despite ambiguity, complete claims, normalization or financial
effects require separate authority/gates. Same-scope defects remain with owner;
returning concerns invoke arbitration. No extra phase allowance is granted.
