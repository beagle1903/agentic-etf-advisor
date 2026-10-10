# ADR 0035: Conserved owner-led lineage and pinned Issue84 remainder

- Status: Accepted for Issue #92 implementation
- Date: 2026-10-08
- Extends: ADR 0033; preserves ADR 0026 historical timed ledgers and ADR 0034 arbitration.

Owner-led splits allocate only the parent's remaining counted phase allowances. The
parent retires on its first split, retains a debit pool for later siblings, and
cannot reclaim an allocation. Each child inherits every consumed count and receives
only its explicit allocation above that baseline. Local design, implementation,
verification and review prerequisites use the child's own events; lifetime gates
continue to use inherited plus local starts. Repository validation checks the
whole lineage, so approvals cannot be reused by an earlier child or a later sibling,
including after an old timed ancestor transitions. Historical timed duplicates
remain replay-compatible but cannot authorize new owner-led actions.

The sole historical timed introduction exception is the complete Issue #23 and
Issue #83 pair identified by fixed canonical digests. Issue #23 retains five seconds
of historical timed split allowance. Issue #83 may record a transition of its
existing suspended implementation reservation to owner-led timing without starting
or resuming it, changing its consumed count, resolving B83-EXHAUSTED, or certifying
product work. A later resume of that exact reservation needs a separate user grant.

Issue #92 is the sole pinned successor for the exhausted Issue #84 remainder. Its
initializer checks complete immutable archived source bytes, the D2/C2 closeout,
the finite user disposition, the exact execution capsule and the derived historical
counts of 4/3/4/4/4. It retains failed outcomes, historical authors and PR #85
bindings as history. The grant adds one implementation, one verification and one
independent initial review. It grants no remediation or retries. Issue #92 uses a
new publication target and fresh content-bound certification; PR #85 certificates
cannot certify it. The bootstrap cannot be reused as generic adoption.

Ticket appends share a repository-level cooperating-writer lock and recheck ledger
membership and raw working-file bytes immediately before replacement. This detects
observed races, but it does not authenticate user authority or lock arbitrary file
editors. Product code, graph state, provider boundaries and historical files are
unchanged.
