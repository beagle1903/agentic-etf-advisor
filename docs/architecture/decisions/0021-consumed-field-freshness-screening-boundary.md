# ADR 0021: Enforce consumed-field freshness at the screening boundary

- Status: Accepted
- Date: 2026-09-13

## Context

Research ingestion checks every canonical field before publishing a snapshot, but fields can age at
different rates after publication. Candidate evidence health classifies the source document using
its document timestamp. A newer document field could therefore keep that document current while an
older fee, liquidity, concentration, sector, or identity field had expired relative to the same
persisted evidence check time. Deterministic screening and construction previously accepted that
mixed-timestamp evidence.

Candidate evidence also requires affirmative flattened `market` and `quote_type` classifications.
Screening previously used the document citation to confirm those rules when canonical identity
provenance was absent. That made a document timestamp stand in for missing field evidence.

## Decision

Screening validates every available canonical field it consumes against the evidence bundle's
persisted `checked_at`, maximum age, and future tolerance. It performs no clock read. The exact age
and future-tolerance boundaries remain current; one microsecond beyond either boundary blocks the
complete screening operation with a stable `field_stale` or `field_future` diagnostic and the
field's source citation.

The consumed fields are `market`, `quote_type`, `expense_ratio_pct`, `average_daily_volume`, and
`top_10_concentration_pct`. Available `sector_exposures` are consumed and checked only when the
profile requests sector exclusions. Category freshness remains the separate construction check
defined by ADR 0014.

Canonical shape, flattened-value/status agreement, units, values, identity consistency, and graph
sector agreement are validated before freshness. When exclusions are requested, the available
canonical sector shape is validated whether graph context is available, unavailable, or absent;
graph weights are compared only when available. An available stale or future field is a hard
blocker. An absent scalar field or explicit missing reason keeps its existing three-valued unknown
result because there is no available value to age. Entirely absent canonical identity provenance
now produces `us_listing_unknown` or `etf_type_unknown`; supplied identity provenance that is
missing or contradicts the mandatory candidate classification remains a contract error.

Construction maps the specific field-freshness blocker to its existing `evidence_not_ready`
reason. Workflow screening keeps its existing error list and adds the stable freshness code,
field citation, and persisted check time as JSON. Explanation, dashboard, and revision boundaries
continue to recompute the same authoritative screening and construction paths.

## Consequences

- A current document cannot mask an expired material field during screening or construction.
- Replacement retrievers and restored checkpoints cannot bypass field freshness through valid
  document health, direct model mutation, or previously accepted downstream artifacts.
- Missing evidence remains distinguishable from expired available evidence.
- Existing successful screening JSON, thresholds, units, ordering, citations, and category checks
  remain unchanged when all consumed fields are current.
- Historical reviews accepted under the former behavior can fail restoration validation. They are
  not silently rewritten or assigned new artifact identities.
- Freshness remains relative to the persisted evidence check time. This decision does not add a
  present-day restore-time clock check, repair published snapshots, or prove live-store behavior.
