# ADR 0027: Preserve research numbers and immutable snapshot semantics

- Status: Accepted design; implementation acceptance pending independent review.
- Date: 2026-09-26
- Issue: https://github.com/beagle1903/agentic-etf-advisor/issues/70
- Approved capsule: https://github.com/beagle1903/agentic-etf-advisor/issues/70#issuecomment-5847394674
- Independent challenge: https://github.com/beagle1903/agentic-etf-advisor/issues/70#issuecomment-5847412153
- Coordinator approval: https://github.com/beagle1903/agentic-etf-advisor/issues/70#issuecomment-5847412334

## Context

Chroma can return a binary64 research observation as an adjacent representable value. QQQ's
`46.272379900000004` concentration became `46.2723799`, contradicting retained field provenance
and stopping screening. A tolerance would also accept a substituted observation at a threshold.
Schema dispatch, mutable staging, retry freshness ordering and graph activation previously lacked
the independent semantic checks needed to preserve exact financial evidence across stores.

## Decision

New research uses schema 2. Fee, volume and concentration values are canonical finite Python
binary64 `repr` strings under `binary64-text-v1`. Flattened values carry the identical token.
Exposure wire records contain `weight_pct_token` and `source_weight_pct_decimal`; native duplicate
weights are forbidden. Exact decimal proofs use normalized coefficient/exponent tokens under
`decimal-exact-v1`, canonical zero, at most 1,100 coefficient digits, and exponent -1,100 through 2.
Exact rational summation rejects totals above 100. Conversion chooses the least representable
binary64 value greater than or equal to the original decimal. Yahoo carries its original parsed
decimal values into the proof; persisted readers never invent proofs. Concentration uses the exact
first-ten sum followed by one upward conversion. Signed binary64 zero remains distinguishable.

Wire dispatch accepts only exact integer schema markers 1 and 2. JSON readers reject duplicate
keys and nonfinite constants before typed validation. Evidence, graph context and screening bundles
must use one encoding throughout. Schema-1 serializers omit new default fields so existing canonical
payloads, document IDs, checkpoint dumps and digests remain unchanged.

The schema-2 document fingerprint hashes canonical UTF-8 JSON containing its ID, exact rendered
content and complete scalar metadata. Only the fingerprint itself and the named adapter legacy
visibility marker are excluded. The independent semantic validator checks tokens, missingness,
units, exposure proofs, duplicate values, rendered content and provenance. Neo4j retains expected
fingerprints in its immutable manifest; consumers recompute them against that authority rather
than trusting a mutable Chroma fingerprint.

Chroma research staging uses `add`, never upsert. Existing complete identical records can be reused;
conflicting identities fail. Complete bounded readback checks arrays, membership, content and
metadata after insertion, including contention between separate clients. Generic writers reserve
`research:` IDs. Older writers must be quiesced for rollout.

Neo4j uses an explicit transaction: lock the catalog, compare the expected prior identity, create
or verify immutable sources and exact unfiltered manifest membership, replace the active projection,
verify its semantics, reverify immutable sources and manifest, move the pointer, then commit.
Confirmed precommit failures roll back. A lost commit acknowledgement remains uncertain. Historical
source relationships are independent of active ETF relationships. Reactivation restores only the
projection, while shrinking universes clear obsolete active relationships without deleting history.

An exact already-active retry is classified before freshness. It strictly validates any supplied
payload and performs read-only verification of Chroma, manifest, source facts, projection and stable
pointer. New or inactive publication requires the original payload and fresh API-level assessment.
Historical schema-1 snapshots retain their original provenance and identity: per-document rendering
can be reconstructed without assuming the original record ordering or repairing stored sources.

Workflow diagnostics retain allowlisted codes and fixed remediation text, not raw exceptions,
metadata, provider output or connection details. JSON graph state gains nested encoding markers and
tokens only; side-effect adapters remain replaceable and no new top-level state key is introduced.

## Consequences

This is an encoding/integrity correction, not a threshold, ranking, category, allocation or provider
change. Missing BND concentration remains missing and cannot become an eligibility pass. Existing
schema-1 evidence with genuinely conflicting provenance still fails. No automatic snapshot or
checkpoint repair, external financial writes, or trade execution is added. Non-skipped real-store
proof and independent code review remain necessary before delivery.
