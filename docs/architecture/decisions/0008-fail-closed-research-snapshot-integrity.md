# ADR 0008: Fail closed across research snapshot publication boundaries

- Status: Accepted
- Date: 2026-08-29

## Context

A post-merge review of the first versioned research snapshot implementation found integrity gaps
at the boundaries between source collection, canonical payload persistence, Chroma staging, Neo4j
activation, retry acknowledgement, and retrieval. Accepted ADR 0007 describes the original
activation design and remains unchanged; this record captures the subsequent corrections.

The quality policy permits limited future clock skew, but the field model previously rejected any
source timestamp later than ingestion before that policy could run. Freshness was also assessed on
one rendered document timestamp per ETF, allowing the newest field to hide stale fields supplied by
a replaceable provider or canonical payload.

## Decision

- With no active snapshot, hybrid retrieval uses an explicit legacy-only query that excludes every
  record carrying version or digest metadata. Abandoned first-stage records therefore remain
  unreachable.
- Preserve every field's source-reported observation timestamp, including a source clock that is
  slightly ahead of ingestion. Before payload persistence or store writes, assess every
  `ResearchField` independently against one captured UTC time. The configured future tolerance
  accepts bounded clock skew; stale fields or timestamps beyond that tolerance block publication.
- Require Yahoo research metadata to provide a usable source-reported `regularMarketTime`; never
  substitute the local fetch time for missing or invalid source provenance.
- Replace normalized ETF fund-family and category relationships, along with source-specific
  relationships, inside the same graph transaction that activates the new snapshot.
- Persist the expected document count for every new graph snapshot. A missing-payload retry for an
  already-active snapshot reads the manifest, verifies the complete Chroma ID set and exact
  version/digest metadata, and rechecks the active pointer before reporting success. Older
  snapshots without a count require their canonical payload once to backfill the manifest.

## Consequences

- One current research field cannot mask another stale or excessively future-dated field.
- Observation and ingestion timestamps remain truthful provenance instead of being clamped to make
  model construction succeed.
- Failed first publication, stale graph relationships, and incomplete retry verification cannot
  silently widen the active advisory dataset.
- The CLI health report identifies failed observations by ETF symbol and field name.
- Chroma records abandoned before graph activation remain as unreachable orphans until a retention
  policy is implemented.
