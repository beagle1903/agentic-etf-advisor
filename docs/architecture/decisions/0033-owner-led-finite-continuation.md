# ADR 0033: Owner-led finite continuation

- Status: Accepted for Issue #86 implementation
- Date: 2026-10-06
- Supersedes: ADR 0026 only for time exhaustion, routine return to design, post-delivery terminality and unsupported splits under `owner-led-v1`.
- Preserves: all `timed-v1` histories and outcomes, ADR 0018 role registration compatibility, ADR 0025 model pins, frozen capsules, lifetime counts, independent consequential gates and content binding.

Issue #84 exposed a recovery loop: a same-scope fixture error after delivery required
special certificate machinery because delivery was terminal. Each correction created
another contract surface that could fail review. We will keep one approved implementation
owner through focused tests, self-review, verification and authorized same-scope repair.
Consequential work still requires a separate architect, independent design challenge,
coordinator approval and independent code review. A genuine contract ambiguity can use
the existing bounded design-reset slot; a review finding alone does not invoke it.

New tickets initialize with `policy: owner-led-v1`; ledgers without the field remain
`timed-v1` and replay under their prior rules. The ledger schema and event envelope stay
unchanged. Owner-led elapsed seconds remain measured audit data; the 120 active minutes
are no longer a rejection threshold. All five counted phase limits remain finite,
including consumed starts and failed attempts. Explicit grants add deltas to limits,
never erase counts. Authority evidence is normalized with Unicode NFKC, collapsed
whitespace and case folding for new-policy grants, including older authorizations
seeded during an explicit transition.

An unsplit timed ticket may append a `policy_transition` with an exact capsule reference
and explicit user authority. It grants no count. A successful implementation may be
followed by `continuation` with a new concrete finite user grant of at least one
remediation slot and, where review is required or previously reserved, a final-review
slot. A continuation retains the historical delivery bindings and blockers, clears
current certification and marks repair pending. The existing owner repairs, then fresh
verification, acceptance and independent final review bind the corrected content.
Redelivery uses the original repository and PR number. Later continuations require
another distinct finite authorization. `check_pr` recognizes only the currently eligible
binding; a historical binding alone never certifies changed content.

New-policy splits and predecessor transitions are rejected for this slice because
their inherited allowance pool does not yet have a proven owner-led interpretation.
Historical timed splits continue unchanged. An actual unresolved blocker or failed
final review stops work until a valid finite grant and repair path exists.

Atomic append keeps the one-writer lock. It captures event-source bytes when supplied,
all ledger-file bytes and names, repository content and candidate temporary bytes. It
rereads each real file and current repository content immediately before replacement,
rejecting changed inputs. This is a final filesystem check, not authentication of a
human authorization or a lock on arbitrary external editors. Publication requires a
quiescent workspace and read-only checks against the actual saved delivered ledger.

The change is confined to development workflow tooling and records. Product APIs,
graph/checkpoint JSON, finance logic, provider and database boundaries remain unchanged.
