# ADR 0039: Opt-in US/EU listings and exact USD/EUR cash

- Status: Accepted design; implementation pending independent acceptance.
- Date: 2026-10-19
- Issue: #104
- Authority: generation2 capsule `e93ab282dac4f49b5e7f8c2d9f1dec224cd1bef85c9ff427ffa1103e9db77c6c`;
  [complete approved handoff](../../iterations/027-issue104-us-eu-design.md).

## Decision

Explicit `advisory_contract: us-eu-v1` selects a semantic contract independently of
numeric schema2. An absent marker retains exact existing US/USD serializers,
reference names and checkpoint behavior. Null, unknown, mixed or removed markers
with surviving new facts fail validation. No migration is inferred.

Reuse `yahoo-listing-map-v1` to establish listing region from source exchange.
Retain exact symbol/suffix/exchange. Domicile, fund/share-class currency, geography
and catalogue membership cannot establish listing eligibility. Source ETF,
major quote unit, attribution and consumed-field freshness remain required.
GBP/subunits and unsupported venues are excluded. Original fee, listing-share
volume, concentration, sector, category and allocation rules remain unchanged.

Construction requires checksum-valid ISIN and attributed issuer fund/subfund group.
Search all feasible representatives allowing at most one selected group; same-ISIN
group contradictions block. Different groups do not establish independent risks.
USD/EUR cash is strict integer minor units, exponent2, range0..100000000000000.
Existing basis-point allocation/largest remainders preserve base totals exactly.
ECB reference data is fetched inside the existing retrieval operation and bound
in its receipt/output artifact. Select under unchanged rules before deciding FX
need; selected cross-currency positions require FX even with zero cash. Convert
once by exact rational multiplication/division and half-up rounding. Never sum
mixed trading amounts or reverse-convert to validate base cash.

The ECB adapter makes one fixed HTTPS request, rejects redirects, caps body64KiB,
uses ten-second timeout and rejects DTD/entities, malformed/duplicate date/USD and
noncanonical rates. Effective-date UTC midnight conservatively anchors age, not
publication time; age120hours and future5minutes are inclusive. No fallback or
automatic retry. Conversions are reference illustrations, not transaction prices.

Reference files contain at most ten unique supplied-universe listings and one MiB.
Strictly validate complete input before binding. Fresh collection creates detached
fields replacing only ingestion/version with destination coordinates, preserving
the normalized source value/missingness/unit/provider/URL/observation exactly.
File access never renews source age. Retry/reactivation/restoration use original
canonical content, never reread/rebind the file. New coordinates change content
identity; prior artifacts remain immutable. A missing provider/file/record gives
explicit missing identity, never synthetic live defaults.

No graph keys or side-effect stages are added. Saved contract changes reject;
base changes require both money amounts and invalidate evidence/FX/downstream.
Later-stage revision and restore validate persisted check time, reusing artifacts
without external calls. Explanation references expose labelled monetary records;
wrong currency, shorthand symbols and unrelated numeric support fail.

## Limits

Provenance/fingerprints verify structure and alteration against bound content,
not whether a curator truthfully quoted an issuer webpage. Yahoo remains an
unofficial development source. Synthetic tests do not prove complete live EU
metrics or ready live portfolios. No catalogue picker/ingestion, optimization,
suitability, tax, trades, external financial writes, automatic migration or live
saved-review mutation is added.
