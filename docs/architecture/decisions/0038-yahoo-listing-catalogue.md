# ADR 0038: Local Yahoo listing catalogue

- Status: Accepted for Issue #103 implementation
- Date: 2026-10-14
- Design authority: Issue 103 generation 2 approved architect handoff

## Decision

The catalogue is a local research directory beside the six-symbol research universe.
It changes no advisory eligibility, US-only screening, allocation, graph/checkpoint
state, or research publication identity. Yahoo `ETFQuery` partitions use exact region
and exchange equality, size 250, ascending ticker order, and fixed
`yahoo-listing-map-v1` with 33 EU and 9 US partitions. UK, Swiss, OTC/deleted and
unknown exchanges are excluded. Seven EU countries have no mapped Yahoo exchange
and are reported as unsupported, not as having zero ETFs.

Each provider page is validated against exact offset, count, total and ETF/exchange
identity. A completed refresh requires all partitions, exact unique identity totals,
and the fixed 40-page/10,000-row per-partition, 256-attempt and 300-second global
bounds. Requests, including authentication, are capped at ten seconds and remaining
deadline. A failed bound or source response returns incomplete evidence while the
prior active version remains. The status `provider_partitions_complete` means only
that these Yahoo partitions and reported pages passed these checks. It cannot detect
upstream omissions or same-count changes and makes no all-market claim.

Listing identity is provider, exact normalized symbol including suffix, and Yahoo
exchange. Source exchange alone determines listing country/region. The record keeps
the response observation time separate from nullable source quote time and stores
only normalized allowlisted fields. Direct Search lookup requires one exact ETF
symbol with an allowed exchange. Search suggestions are capped at 25 and labelled
non-exhaustive; they never substitute for discovery.

Each immutable catalogue version keeps discovered and direct observations separately.
A complete refresh replaces discovery but copies retained direct observations and
their original times/provenance exactly. Combined search selects the entire discovered
observation on overlap, with no optional-field backfill. Direct-only observations
remain when discovery omits them. Counts use set union; a symbol assigned different
exchanges across components blocks publication. Changed valid optional values do
not constitute identity conflicts. Local search uses only the selected observation.

The ignored `.artifacts/catalogue/` store writes validated content-addressed JSON
blobs, then atomically replaces a small active pointer under a bounded cross-process
lock and parent-version CAS. Readers reject malformed schemas, duplicate keys,
nonfinite JSON, mismatched digest/count/identity, and missing blobs. A failed or
interrupted candidate cannot overwrite the prior active version. Full refresh reuse
lasts 24 hours from its own completion; direct additions do not renew it. Runtime
provider, clock, deadline and persistence interfaces remain replaceable.

## Limits

Yahoo/yfinance is an unofficial development source. The mapping reflects only
reviewed Yahoo exchange codes; Yahoo ETF taxonomy is accepted as source
classification, not a regulatory or financial eligibility conclusion. Provider
partitions may reject requests, omit rows, or change while pagination runs. Catalogue
versions are not atomic market snapshots. Publication is local only; no hosted
redistribution or external financial write is authorized.
