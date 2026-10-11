# ADR 0036: Conserved owner-led split lineage

- Status: Accepted for Issue #94 implementation
- Date: 2026-10-11
- Supersedes: ADR 0033 only for its unsupported `owner-led-v1` split boundary.
- Preserves: ADR 0026 historical `timed-v1` replay, finite slots, frozen capsules,
  content and PR binding, and ADR 0033 continuation restrictions.

An owner-led parent can retire with one `split` event containing exactly `authority`,
current `capsule`, nonempty `children`, and `reason`. Every child entry has an issue,
complete five-counter `counts` allocation, and complete generation-one capsule. The
allocation is made once for all children. If parent effective consumption is B and
limits are L, available pool is L-B in each counter. Each allocation is nonnegative,
has at least one positive count, and their componentwise sum cannot exceed L-B. A
child's effective consumption begins at B; limits begin at B plus its allocation.
Local counts begin at zero and govern local prerequisites. Inherited design, challenge,
implementation, remediation, verification, review and certificates never make the
child ready. A nested child may allocate only its own remaining effective allowance.
The parent retires permanently, including unallocated remainder. Splitting does not
grant an attempt or make continuation available to predecessor-bearing tickets.

Child initialization declares `{issue,digest}` for the exact parent prefix ending at
its allocating split and carries the exact allocated capsule. Missing or cyclic
predecessors, duplicate targets, wrong repository or policy, time reversal and
capsule substitution fail. The parent can allocate a child that has not initialized;
its allocation remains unavailable elsewhere. Timed split payloads and replay retain
their previous meaning.

The complete repository candidate is validated for every append. Each connected
owner-led component uses normalized user evidence, independent of display name, with
the original issue/event as its authority origin. Initialization of an allocated child
and its capsule authorization reference the split decision; neither is a fresh grant.
The existing same-ticket policy-transition authority exception remains narrow.
Participant classes derive from declared owners, handoffs, adoption and all phase
starts, including failed and interrupted work. A connected ticket's challenger or
reviewer cannot be another ticket's participant, regardless of append order. Same-role
write-owner continuity remains valid when these independent-role rules permit it.
Normalization does not authenticate people or detect undisclosed aliases.

One ticket-directory lock serializes cooperating repository append writers. Append
parses exact captured ledger bytes and validates the full candidate map before writing
the temporary file. Immediately before its single target replacement, it rereads
actual event-source bytes, ledger membership and bytes, candidate bytes and canonical
repository content. Observed changes reject publication and leave external edits
untouched. The lock does not serialize arbitrary editors, and the final checks are
not an atomic filesystem snapshot. Canonical content exclusions remain the current
ticket ledger and ticket-directory lock/temp files.

Application graph/checkpoint state, financial logic and external integrations are
unchanged. Issue #94's own native ledger is a separate administrative local-phase
projection, documented in iteration 021; generic split support does not migrate it.
