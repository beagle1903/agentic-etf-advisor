# ADR 0026: Finite ticket development lifetime

- Status: Accepted
- Date: 2026-09-26
- Supersedes: ADR 0023 automatic repeated-design-reset behavior only.
- Preserves: ADR 0018 compatibility, ADR 0022 routine ownership, ADR 0025 routing.

Repeated resets could restart the remediation counter and create a larger unbounded
loop. Issue73 implements the user-approved finite policy in AGENTS and CONTRIBUTING.
A versioned JSON ledger derives ticket state from strict append-only events. Default
120 active minutes and lifetime counted slots persist across sessions/agents/quotas.
Start reserves slots; open phases charge through now; pause and exact-session resume
retain reservations. One implementation, initial review, remediation, final review
and design reset are the defaults. Consequential design has an independent challenge
before approval; challenge does not consume a code-review slot. Frozen contract IDs
prevent scope growth. Safety defects still deny delivery after a hard development stop.
Named explicit finite user extensions append deltas rather than erase history.
Splits validate predecessor prefixes and allocations, inherit counters and receive
allocated remainder. Siblings share that remainder; the predecessor retires.

The stdlib CLI atomically appends under a one-writer lock and gates dispatch/delivery.
CI checks merge-base event prefixes, deletion, current primary issue identity and
recorded delivery prerequisites, including PR edited events. Existing historical
issues/PRs predating adoption are exempt until explicitly adopted. Adoption of Issue73
conservatively charges creation through bootstrap and records known design/challenge
sessions; tooling did not exist during these phases.

This is recorded governance, not a kill switch or cryptographic authority. Manual
truthfulness and coordinator interruption are necessary; arbitrary uncommitted local
history edits cannot be proven absent until comparison with committed history. No
product API, financial policy, graph/checkpoint JSON, side-effect interface, credential,
provider/database dependency or global Codex setting changes.

## Review-completed enforcement details

Future initialization embeds the complete frozen capsule, not opaque identifiers.
Design, challenge, approval and every phase bind its exact digest and generation.
A failed reset clears prior successful design; an explicit successful reset advances
its generation. Future adoption is forbidden. The one approved Issue73 migration
preserves the exact 18-event historical prefix and appends a complete capsule binding.
Classified pinned write ownership is enforced; fresh same-role handoffs and concrete
specialist escalations are explicit events. Independent review excludes every write
session, including remediation and verification authors. Extension approval identity
uses normalized evidence independently of authority display name.

Successful review, verification and acceptance bind identical canonical repository
content. Delivery additionally binds original PR number and repository; CI compares
the current PR-head content. Only the mutable current-ticket JSON and temporary
ledger lock/temp files are excluded. Original unchanged CI reruns remain valid;
other PRs or changed content cannot reuse delivered state. Source/test/documentation
changes after review require new evidence within the remaining finite allowance.
