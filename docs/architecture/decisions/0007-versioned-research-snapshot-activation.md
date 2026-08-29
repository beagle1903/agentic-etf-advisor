# ADR 0007: Activate versioned research snapshots through Neo4j

- Status: Accepted
- Date: 2026-08-29

## Context

Manually supplied symbols and independent Chroma/Neo4j upserts cannot prove which ETF universe
was researched or that both stores expose the same publication. A cross-database transaction is
not available, and overwriting stable document IDs could damage the previous usable snapshot
before the second store succeeds.

Later screening also needs more than price, category, and fund-family text. Fees, liquidity,
benchmark, holdings, sector, geography, and concentration must retain their own provenance and
must distinguish unavailable evidence from a real zero or an empty value.

## Decision

Package a small, curated six-symbol universe independently from mutable research data. Build one
typed `ETFResearchSnapshot` whose every material field contains a value or an explicit missing
reason plus provider, source URL, observation time, ingestion time, unit, and snapshot version.
Yahoo Finance remains a replaceable development adapter. Geography is explicitly marked as
provider-unsupported because the current adapter does not receive that field.

Render one versioned source document per ETF. Stage all documents in Chroma, then read back their
IDs, snapshot version, and snapshot digest. Only after that verification does Neo4j execute one
query transaction that writes the snapshot-scoped source graph and changes the single
`ResearchCatalog` active-snapshot relationship.

Hybrid retrieval asks Neo4j for the active version before querying Chroma and filters semantic
candidates to that exact version. When no active research snapshot exists, the legacy unversioned
development path remains available.

## Consequences

- A Chroma staging or verification failure never starts graph publication.
- A Neo4j transaction failure leaves the prior active pointer unchanged. Versioned Chroma staging
  records can remain as unreachable orphans and may be cleaned up by a later retention iteration.
- Neo4j is the activation authority; this avoids claiming an impossible distributed transaction.
- Existing active snapshots remain intact because new documents use version-scoped IDs.
- Holdings, sector, geography, benchmark, and overlap graph relationships are still deferred to
  Iteration 013. This iteration stores the richer contract without asserting unmeasured graph
  value.
- A network failure after Neo4j commits can make the CLI outcome uncertain, as with any remote
  commit acknowledgement. Re-running the same snapshot version is idempotent and reveals the
  active version.
