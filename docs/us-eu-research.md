# US/EU research and currency usage

The dashboard defaults to legacy US/USD. Choose **US / EU (us-eu-v1)** for a new
review, choose USD/EUR base and enter decimal major-unit cash with at most two
fractional places. The UI converts once to integer minor units. A base revision
requires both cash amounts and new retrieval; a legacy review cannot switch contracts.

One-shot publication remains explicitly bounded; catalogue preparation is a
separate local workflow.
Replace the angle-bracket placeholders with your local paths and a new version:

```powershell
uv run etf-advisor publish-research-universe --universe <universe.json> --advisory-contract us-eu-v1 --reference-facts <attributed-reference.json> --snapshot-version <new-version>
uv run etf-advisor evaluate-us-eu
uv run etf-advisor evaluate-analysis
```

The reference root has exactly `schema_version: 1` and `records`. Each record has
normalized `symbol`, `exchange` and these five complete `ResearchField` objects:

| Name | Unit | Available value |
| --- | --- | --- |
| share_class_id | isin | Checksum-valid share-class ISIN |
| economic_group_id | issuer_fund_id | Namespaced issuer fund/subfund identity |
| domicile | iso3166_alpha2 | Uppercase two-letter country |
| fund_base_currency | iso4217 | USD or EUR |
| share_class_currency | iso4217 | USD or EUR |

Each field has `value`, `missing_reason`, `unit`, `provider`, `source_url`,
`observed_at`, `ingested_at`, `snapshot_version`. Available values use null
missing_reason; missing values use null value and an explicit supported reason.
Identity must cite issuer/exchange material; never infer fund group from umbrella,
family, benchmark or ticker. Limit ten unique listings/one MiB. Duplicate/unknown
keys, nonfinite values, malformed provenance/identifiers/publication coordinates,
duplicate listings and supplied-universe association errors reject the whole input.

## Explicit curator Fund identity

For a separately curated local input, use reference `schema_version: 2` with
`identity_contract: "curator-fund-v1"`, a complete `registry_envelope`, and the
same five complete fields per listing. The economic group field uses
`curator_fund_id` and `audited_curator_registry_v1`; an available value must be
an active key in the bound registry, paired with an active checksum-valid class
ISIN and an official current Fund-proof URL. Select it explicitly for one-shot
ingestion:

```powershell
uv run etf-advisor publish-research-universe --universe <universe.json> --advisory-contract us-eu-v1 --identity-contract curator-fund-v1 --reference-facts <curated-schema2.json> --snapshot-version <new-version>
```

The local dashboard offers the same explicit selection for a published
catalogue research scope with bound curator proof. A selected profile, research
snapshot and every review artifact must agree on the marker and registry
generation. The complete proof stays in saved evidence; restore revalidates it
at the saved check time without a registry or provider read. Current Fund,
inventory, every active membership and required context-link source must each
be within the inclusive 120-hour past and five-minute future window. Old
rename lineage remains historical and cannot refresh current proof. A retry
cannot switch identity contract or silently rebuild an old snapshot.
For a curator retry, provide the original canonical snapshot file and the same
explicit identity option; the reference file is needed only for fresh
collection and is never reread for replay.
Local registry publication also requires source collection and audit attestation
at or before generation recording, with child recording no earlier than its
actual parent. Suspended Funds remain unavailable; this version does not define
a suspended-to-active resumption workflow.

The registry and schema 2 inputs are user-curated local material. The software
checks structure, chronology, exact source references and parent-relative
publication, but it cannot authenticate actors, official source truth or legal
Fund completeness. This repository ships no real curator registry, key or
curated reference file and does not activate a live path by default.

Source times and citations determine freshness. Fresh collection validates the
file before making detached fields with destination ingestion/version, preserving
all source facts and observations. File access does not renew observations. Retry,
reactivation and restoration use original canonical payloads without rereading or
rebinding the file. Absent reference records yield unavailable economic identity
and construction exclusions. No fabricated live default facts are shipped.

The exact Yahoo exchange mapping establishes listing region separately from
domicile/fund/share-class currency. UK/Swiss/OTC/unknown venues and subunits such as
GBp/GBX/US cents are unsupported. Original fee, per-listing share-volume,
concentration, exact categories and sector controls stay unchanged. Metrics are
never guessed from names or summed across venues. One fund's classes/listings
cannot count as independent positions; separate same-index funds are not merged.

ECB EUR/USD observations belong to the existing retrieval receipt. Same-currency
candidates make no FX request. Selected cross-currency positions require valid FX
even for zero cash. Missing/stale/future references block. Maximum age120hours uses
effective-date UTC midnight, with five-minute future observation tolerance.
Weekend/holiday references can expire. Exact half-up conversion exposes separate
base and trading amounts; do not add USD/EUR trading amounts together. These are
illustrations, not executable prices, quantities or proceeds.

`evaluate-us-eu` replays ten separately versioned synthetic cases without network,
clock, model or stores. `evaluate-analysis` retains Issue99's original datasets,
37 cases and legacy EU-rejection expectations. Neither certifies live readiness,
Yahoo completeness, regulatory eligibility, suitability, returns or independent
risks. Live EU fee/category/volume/holdings completeness remains unproven. Local
curation is structurally checked, not independently authenticated. Evaluation does
not publish data or mutate saved reviews.
# Reported-holdings overlap in Source evidence

The review dashboard lets you choose two exact candidate documents from the
validated evidence pool, including catalogue members outside the packaged six.
The diagnostic shows the sum of matching reported holding weights in percentage
points and each candidate's reported-row weight sum. It uses only current,
attributed `top_holdings` observations and shows each original provider, URL,
observation time and the persisted freshness check time. The calculation details
show exact rational amounts; visible values are approximate six-place rounded
figures. Zero means no overlap among these reported identities under the stated
rule. The lists may be partial; the result is not complete fund or portfolio
overlap and does not affect selection or weights. Missing symbols, repeated or
conflicting identities, invalid provenance, stale or future fields and diagnostic
size limits make overlap unavailable. Official BND repeated bond rows remain
valid source evidence even when they prevent a match.
