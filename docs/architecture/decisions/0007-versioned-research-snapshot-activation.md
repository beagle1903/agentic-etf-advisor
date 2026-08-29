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

## Review hardening addendum

PR review exposed three details that the original decision did not make strong enough. This
addendum supersedes the version-only identity and refetch-on-retry implications above:

- Source-document IDs are scoped by both snapshot version and content digest. Concurrent publishers
  that propose different content under the same version therefore stage disjoint Chroma records;
  the Neo4j uniqueness check permits at most one digest to own that version.
- The active graph identity contains both version and digest, and hybrid retrieval filters Chroma
  on both values. A losing or abandoned same-version candidate cannot become reachable through a
  winner's active pointer.
- Each source document persists deterministic structured JSON for every field's value or missing
  reason, provider, source URL, observation time, ingestion time, unit, and snapshot version in
  Chroma and Neo4j.
- Before store writes, the CLI atomically persists the canonical validated payload. An
  explicit-version retry reuses that payload. If the requested version and digest are already
  active, a missing local payload is handled as a successful no-op; an inactive published version
  still requires its original payload for safe reactivation.

## Post-merge integrity correction

A read-only review of the merged implementation found four gaps in those guarantees. The
implementation now applies the original activation decision as follows:

- With no active snapshot, hybrid retrieval performs an explicit legacy-only query instead of an
  unfiltered query, so an abandoned first-stage snapshot cannot reach advisory retrieval.
- Yahoo research fields use the source-reported market timestamp, and the shared stale/future
  boundary runs before the canonical payload or retrieval stores are written.
- Snapshot publication replaces normalized ETF fund-family/category relationships as well as
  source-specific relationships inside the active-pointer transaction.
- Every new graph snapshot persists its expected document count. A missing-payload no-op reads that
  manifest, verifies exact Chroma IDs and identity metadata, and rechecks the active pointer before
  reporting success. Older snapshots without a count require their canonical payload once to
  backfill it.
