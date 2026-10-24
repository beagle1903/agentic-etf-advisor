# ADR 0040: Bounded opt-in catalogue research and selection

Status: Accepted for Issue 105 implementation

## Context

ADR 0038's Yahoo directory describes observed listings, while ADR 0039's
`us-eu-v1` path used a small packaged research universe. Directory membership
alone cannot establish research coverage, eligibility, or suitability. The
existing ten-candidate exhaustive construction limit also cannot take a larger
retrieved pool directly.

## Decision

An explicit `us-eu-v1` request pins one validated directory version and a
complete, filtered set of at most 100 direct listings. Resolving over the limit
fails; no prefix is silently selected. A resumable local job collects each
member through bounded Yahoo requests and bounded reference inputs. Successful
source observations are cached with their original timestamps. Finalization
validates every member and detaches a canonical schema-2 snapshot with one new
destination ingestion time. A committed finalization is recovered byte-for-byte
after lost acknowledgement; a precommit retry can choose a later time only after
checking unchanged sources. Source age never renews. Publication uses the
existing Chroma/Neo4j complete-snapshot readback and active-pointer CAS protocol.

New reviews opt in through an absent-by-default catalogue request. Exact
retrieval verifies pinned directory membership, active identity, complete
manifest, documents, fingerprints, and graph context for every requested member.
The full pool, up to 100, is screened and checkpointed. Pure
`sleeve-category-round-robin-v1` then classifies all listings, first covers
unrepresented economic groups, fills spare slots with remaining alternatives,
and chooses at most ten before the unchanged subset
enumeration. Its ordered report records every listing's disposition, counts,
shortlist and final positions. The final portfolio admits at most one position
per economic group. It may miss a feasible full-pool combination;
the original construction blocker remains visible. Saved review validation
recomputes the same pure decision without provider or store calls.

The request, evidence, construction, revision, and receipt identities must be
equal. Legacy absent-field serializers and the existing `us-eu-v1` currency,
economic-group, exact-money, FX-needs-rate and source-provenance rules remain
unchanged. No live financial write or automatic migration is introduced.

## Consequences

Jobs may age out before completion, and missing provider fields can block
publication or a portfolio. A larger checkpoint is bounded by membership and
payload limits. Yahoo's shared yfinance session requires one process-wide lock
while a bounded attempt owns the transport. Complete directory and research
counts are distinct and neither proves Yahoo-wide completeness.
