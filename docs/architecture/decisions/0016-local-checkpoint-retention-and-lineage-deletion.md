# ADR 0016: Retain local revision lineage for 30 days and delete whole threads

- Status: Accepted
- Date: 2026-09-04

## Context

ADR 0006 added opaque-token restoration for local PostgreSQL checkpoints and explicitly deferred
retention and deletion. Iteration 017 adds profile versions, evidence identities, drafts, review
decisions, and operation receipts. Keeping those records forever is an undefined privacy and
operational outcome, while deleting individual records could make the surviving lineage
misleading.

The local token is still a capability reference rather than authentication. Pending-review
discovery, administrative audit, legal hold, backup, and multi-user authorization belong to later
work.

## Decision

Keep in-memory checkpoints only for the process/browser session and support explicit discard.

For the opt-in local PostgreSQL store, retain one complete thread for 30 days after its last
meaningful write. Creation, a review decision, revision creation, explicit retry, and terminal
transition update `last_activity_at` and `expires_at` using one injected UTC clock. Read-only load,
preview, or rendering does not extend retention. A bounded local setting may change the interval,
and presentation must show the effective expiry.

Do not run hidden background deletion. Expose a replaceable checkpoint-store lifecycle boundary
that can preview expired threads at one captured check time and, through a separate explicit prune
operation, delete only those threads. The dashboard does not enumerate other tokens.

Explicit user deletion requires the exact version-4 review token plus a separate confirmation. One
store operation removes every checkpoint, write record, revision, decision, operation receipt,
draft, and lifecycle record for that thread. It succeeds completely or fails closed; deleting an
individual revision or event is unsupported. Return only a sanitized `deleted`, `not_found`, or
failure result.

The retained audit record is tamper-evident through canonical digests, not immutable against a
database administrator. Authorized deletion intentionally removes the complete audit lineage. The
local prototype keeps no tombstone, archive, legal-hold copy, or backup outside the checkpoint
store.

## Consequences

- Local durable reviews have a visible and testable lifetime instead of implicit indefinite
  retention.
- Viewing a saved review does not silently prolong storage of profile or financial context.
- Cleanup remains operator-controlled and previewable; expired data may remain until prune runs.
- Whole-thread deletion preserves lineage integrity among retained records but is permanent in the
  local prototype.
- Authentication, discovery, legal hold, backup, recovery, and administrative audit remain
  Iteration 018 or production-readiness concerns.
- Checkpoint implementations must expose equivalent lifecycle semantics behind the replaceable
  store protocol and must not log tokens, connection strings, prompts, source content, or raw
  provider output.
