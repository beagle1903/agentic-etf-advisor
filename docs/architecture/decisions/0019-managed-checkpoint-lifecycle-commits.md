# ADR 0019: Manage checkpoint lifetime with independent atomic commits

- Status: Accepted implementation of the coordinator-approved Issue #41 handoff
- Date: 2026-09-08
- Design gate: https://github.com/beagle1903/agentic-etf-advisor/issues/41#issuecomment-5573395329

## Decision

Implement ADR 0016 through `LifecycleStore.managed(thread_id, create=...)`. The store holds
per-thread exclusion throughout each invocation or read, while each checkpoint or pending-write
commit is its own transaction. A checkpoint and its versioned lifecycle metadata commit together.
The PostgreSQL adapter uses a separate session advisory lock connection, not an invocation-wide
transaction. The `started` receipt therefore commits before an adapter can execute, preserving
ADR 0015. PostgreSQL bounds advisory-lock acquisition with a five-second lock timeout so a
competing managed invocation or deletion fails instead of waiting indefinitely. Deterministic
memory doubles roll back only the affected thread on failure.

Lifecycle metadata remains outside `AdvisorState`. It records a schema version, increasing write
version, per-thread retention interval, last activity, expiry, deduplicated semantic event keys,
and a canonical JSON integrity digest. The default interval is 30 days; new threads accept an
integer local setting from 1 through 365 days. Existing threads retain their creation setting.

Creation, accepted decisions, child revisions, accepted explicit retries, and terminal outcomes
renew activity. Decision/revision/previous-attempt identities provide stable event keys; terminal
keys include the revision, outcome, and operation manifest. One injected aware-UTC clock value
supplies both activity and expiry for a qualifying commit. Backward activity clocks fail closed.
Ordinary checkpoint and pending writes advance the version without renewing retention. Reads,
restoration, rejected inputs, and repeated events never renew it.

Durable managed access checks expiry before yielding a saver. At `expires_at <= check_time`, only
lifecycle inspection or explicit deletion remains available. Legacy metadata is not invented:
missing or malformed lifecycle state blocks managed restoration/resume and is excluded from
automatic prune. Exact confirmed deletion remains available even for damaged lineage/metadata.

Preview is non-mutating and captures one cutoff plus exact candidate integrity/version values.
Prune acquires the same thread exclusion, rechecks each candidate, skips changed records, and
never adds newly expired threads. Every exact deletion requires a UUID-v4 token and separate
boolean confirmation. All namespaces, blobs, pending writes, checkpoints, and lifecycle metadata
are removed in one transaction. No partial lineage deletion or tombstone is introduced.

## Consequences and limits

Managed saver handles expire on context exit. Recompile inside a new managed context to resume;
cached graphs cannot recreate a deleted thread. The dashboard backend uses managed access in both
modes; in-memory discard clears the thread and cached state. Memory has no recovery promise or
automatic expiry. Low-level `open()` exists for adapter schema/diagnostics and legacy fixtures;
application workflow access must use `managed()`. Direct database writers do not participate in
the managed exclusion protocol.

Audit reconstruction validates the retained ledger, artifact digests, and each reached evidence
snapshot identity, then returns a detached JSON view of profiles, reached artifacts, decisions,
receipts, parent/child links, and outcomes. Digests are not signatures or protection against a
database administrator. Retained profile/evidence/audit content is private local data and must
not be logged or published.

Issue #42 owns rendering and controls; Issue #43 owns iteration-wide acceptance. The PostgreSQL
adapter is tested with deterministic connection/store doubles. Live PostgreSQL behavior is not
verified by this slice and requires separate approval. No provider/market calls, trade execution,
financial writes, discovery, backup, authentication, or background cleanup is added.
