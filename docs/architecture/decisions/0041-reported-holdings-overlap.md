# ADR 0041: Conservative reported-holdings overlap

Status: Accepted for Issue 101 implementation

## Context

The review dashboard has attributable `top_holdings` lists for ETF candidates. These lists may be partial, have different observation times, and lack universal security identifiers. In particular, an official bond list may legitimately repeat a label or ticker for distinct ranked rows. A displayed overlap must not turn those source limitations into a claim about complete fund or portfolio exposure.

## Decision

The Source evidence view computes an ephemeral pairwise diagnostic from the complete validated evidence bundle. It matches a holding only when both candidates have the same provider, normalized reported symbol and normalized reported name. Missing symbols, duplicate symbols or names within a list, and cross-list symbol/name conflicts make the pair unavailable. Source rows are never truncated, deduplicated, aggregated or rewritten.

For each matched identity, the diagnostic takes the smaller reported percentage-point weight and sums those minima exactly as rational numbers. Each candidate separately displays the sum of every reported row. No division by coverage, portfolio weighting, residual estimate or complete-overlap inference is made. Schema 2 uses the canonical source decimal proof after token validation; schema 1 uses the exact persisted integer or binary64 value. Display rounds half up to six decimal places while calculation details retain reduced rational amounts.

The pure calculation revalidates a detached JSON bundle and the complete consumed holdings field. It applies the persisted check time and existing per-field freshness policy, including the official BND monthly window and zero future tolerance. Invalid or ambiguous evidence yields fixed unavailable reasons; a current numerically valid list may retain its row sum when identity is ambiguous. Bounds of 100 candidates, one MiB of provenance per candidate and 1,000 selected holdings per side affect this diagnostic only.

## Consequences

No graph state, checkpoint, serializer, provider, screening, selection, construction, weight or exact-money contract changes. Distinct economic holdings with ambiguous reported identities can make the diagnostic unavailable. A zero means no overlap among the reported identities under this rule; it does not establish independent complete exposure. Original observations and source links remain visible beside the result.
