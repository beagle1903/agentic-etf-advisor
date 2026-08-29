# Iteration 012: Versioned ETF research universe

- Status: Complete
- Started: 2026-08-29

## Goal

Replace manually supplied research candidates with a small, curated, reproducible US ETF
universe and publish one field-attributable snapshot across Chroma and Neo4j without exposing a
partially updated advisory dataset.

## Deliverables

- A packaged `us-etf-research-core` universe containing SPY, VTI, QQQ, BND, VEA, and VWO.
- A typed snapshot contract for name, ETF/market identity, category, fund family, benchmark,
  expense ratio, average volume, top holdings, sector exposure, geography exposure, and top-ten
  concentration.
- Field-level provider, source URL, observation time, ingestion time, units, snapshot version,
  and explicit missing reason.
- A Yahoo Finance development adapter using `Ticker.info` and `Ticker.funds_data` behind a
  replaceable interface and injected clock.
- Stable snapshot digests and version-scoped source-document IDs.
- Chroma staging/readback followed by one Neo4j snapshot-write and active-pointer transaction.
- Active-version filtering in the production hybrid retrieval path.
- An `etf-advisor publish-research-universe` command with an optional universe file and explicit
  snapshot version.

## Acceptance criteria

- Universe membership is versioned, ordered, duplicate-free, packaged, and independent from live
  source results.
- Every material research field has exactly one value or missing reason and complete source and
  timestamp metadata.
- Source-unsupported geography and missing source fields remain visible rather than becoming
  empty values or silent passes.
- All snapshot fields agree on version and ingestion time, and snapshot documents preserve a
  stable content digest.
- A published snapshot version is immutable; different content must use a new version.
- Chroma must read back every staged ID, version, and digest before Neo4j is called.
- Neo4j activates only a complete expected document count inside the same query transaction as
  the snapshot graph write.
- Hybrid retrieval scopes Chroma candidates to Neo4j's active version.
- Chroma verification and graph transaction failures leave the previous active graph version
  unchanged.
- Existing unversioned development ingestion remains usable before the first snapshot activation.
- Ruff, mypy, the offline test suite, packaging, and Docker Compose configuration pass.

## Boundaries and deferred work

- The curated universe is deliberately small and is not an ETF recommendation or complete market
  catalog.
- Yahoo/yfinance remains for local research and personal development only; this is not a market-
  data licensing decision.
- The source does not provide geography exposure through the current adapter, so it is recorded as
  `provider_unsupported` and cannot support a geography claim.
- Staged but inactive Chroma documents are harmless but are not automatically deleted yet.
- Holdings, sector, geography, benchmark, and overlap graph expansion must earn measured value in
  Iteration 013 before becoming retained schema.
- Candidate eligibility, ranking, portfolio construction, forecasts, brokerage connectivity, and
  trades remain out of scope.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes for 39 source files.
- `uv run pytest` passes offline (162 tests).
- `uv run etf-advisor --help` exposes `publish-research-universe`.
- `uv build` produces source and wheel artifacts.
- The wheel contains the packaged `research/universe_v1.json` file.
- `docker compose config --quiet` passes.

## PR review hardening

- Snapshot source-document IDs now include both immutable version and content digest, preventing
  same-version concurrent staging attempts from overwriting each other.
- Neo4j's active identity and the Chroma retrieval filter now use both version and digest.
- Canonical per-field provenance JSON is persisted in both Chroma and Neo4j source documents.
- The publication command persists a canonical local payload before store writes and reuses it for
  explicit-version retries instead of refetching mutable provider data.
- Tests cover provenance round-tripping, distinct same-version candidate identities, exact active
  digest filtering, persisted-payload retries, and already-active no-op retries.
