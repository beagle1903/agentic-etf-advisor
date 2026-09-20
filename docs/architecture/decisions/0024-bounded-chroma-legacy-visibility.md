# ADR 0024: Bound and certify Chroma legacy visibility

- Status: Accepted
- Date: 2026-09-18

## Context

ADR 0008 requires the no-active-snapshot branch to exclude every staged or versioned Chroma
record. The original adapter implemented that rule by requesting the collection's complete count,
parsing every semantic result, and filtering locally. That made the amount of data returned for a
small query proportional to collection size. It also relied on absence of snapshot metadata after
retrieval, without a persisted indication that every older record had been classified.

Chroma upserts can encounter existing metadata, collections survive application upgrades, and a
failed first publication deliberately leaves staged records behind. A compatibility repair must
therefore distinguish proven legacy records from blocked records without changing canonical source
payloads, snapshot identities, graph state, or digests.

## Decision

- Reserve document metadata key `etf_advisor_legacy_visibility`. The adapter writes `legacy-v1`
  only when neither `snapshot_version` nor `snapshot_digest` is present, and writes `blocked-v1`
  when either key is present. Classification is based on key presence, including an empty value.
- Reserve collection metadata key `etf_advisor_legacy_visibility_schema`. Integer `1` certifies a
  completely prepared collection; integer `0` means preparation started but is incomplete. Missing,
  Boolean, string, or other values are not ready.
- A newly created empty collection receives schema `1`. Opening an existing collection does not
  add or change readiness. The no-active-snapshot branch freshly reopens the collection and requires
  schema `1` for every operation.
- Legacy retrieval asks Chroma for exactly the caller's limit with an equality filter on
  `legacy-v1`. Every returned row is revalidated for that marker and for absence of both snapshot
  keys. Any contradiction fails the complete operation. The adapter-owned marker is removed before
  evidence leaves the store boundary.
- All adapter upserts assign a marker. Before a legacy upsert, the adapter reads the matching IDs
  and rejects the entire batch if any existing row contains either snapshot key. This guard keeps a
  metadata-replacing or metadata-merging backend from converting staged evidence into legacy
  evidence.
- `prepare-chroma-legacy-visibility` is an explicit compatibility operation. It previews by default.
  `--apply` requires quiesced readers and writers, marks the collection incomplete, reads and updates
  bounded metadata pages, reads back every updated page, validates the complete collection and
  stable count in bounded pages, and writes schema `1` only after success. It never changes document
  text, embeddings, IDs, canonical provenance, or snapshot identity.

## Consequences

- A no-active-snapshot query is bounded by the requested result count rather than collection size.
- Existing collections fail closed until an operator explicitly previews and applies preparation.
- Interrupted preparation and stale or forged markers leave legacy retrieval unavailable instead
  of exposing uncertain evidence. The operation is safe to rerun after readers and writers are
  quiesced again.
- Active snapshot retrieval keeps its exact version-and-digest filter. Graph state, checkpoints,
  canonical JSON, snapshot digests, and finance policy are unchanged.
- The embedded Chroma contract test covers the relied-on equality filter and metadata-only update
  semantics. Docker/server concurrency remains an operational quiescence requirement rather than a
  database lock supplied by this application.
