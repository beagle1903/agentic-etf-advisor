# ADR 0035: Validate complete queued and live PR identity

- Status: Accepted for Issue #93 implementation
- Date: 2026-10-10
- Scope: GitHub pull-request CI boundary only

## Context

CI receives a queued GitHub event and fetches the current pull request. The previous
comparison checked the head SHA and base fields but could accept the same head SHA
after the branch or fork changed. It then retained queued PR metadata while using
the live body. That mixture could certify a different PR snapshot.

## Decision

Validate both snapshots before prefix, primary-issue and delivery checks. Require
matching positive PR numbers, UTC-seconds creation time, and complete head and base
SHA, ref and repository identity. The event repository must match both base
repositories. Each SHA is lowercase 40- or 64-character hex; each repository name
has two nonempty components. A missing, malformed or changed identity fails closed.
Matching head forks are valid: the head repository need not equal the base repository.

After validation, return the live PR object. CI therefore uses its body for the
primary issue, base SHA for merge-base prefix validation, and head SHA for content
validation. A queued event with a stale base or head needs a fresh event and rerun.
The existing recorded delivery, original repository/PR/content, historical exemption
and ledger-prefix gates remain in force. This snapshot comparison cannot prevent
GitHub metadata changing after the live fetch.

## Governance boundary

Issue #93 has a one-time administrative lineage projection, documented in the
[iteration record](../../iterations/020-issue93-pr-identity.md). The native Issue #93
ledger records local phases; the separate authoritative journal retains inherited
counts, historical author exclusions and the zero-reset limit. This ADR adds no
generic split support, event schema, product state or external financial write.
