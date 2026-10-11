# Iteration 021: Issue #94 conserved owner-led allowances

Issue #94 implements frozen capsule `issue-94-conserved-owner-led-split-lineage`,
generation 1, digest `4612f83c55b0727daf999abb08001d289baa91ed947ca7f90bb9d7dff99250f5`.
Classification is consequential. `/root/issue94_owner` is the approved
`implementation_worker`, `gpt-6-sol`, medium owner. Separate S94D1 design,
independent S94C1 challenge and coordinator approval preceded implementation.
The single user-approved Issue #93/#94/#95 split supplies Issue #94's authority;
continuing work did not renew its allowance.

ADR 0036 covers generic owner-led conserved batch allocation, local versus inherited
prerequisites, symmetric lineage authority/participant audit and repository append
serialization. This replaces only the conserved split/lineage subset of the abandoned
Issue #84/#92 attempt. The change is limited to development workflow code, tests and directly
affected governance instructions. Issue #92 recovery machinery, Issue #23/#83 exact
transition, application state, financial rules and external writes remain outside it.

The native `docs/workflow/tickets/issue-94.json` is an administrative **local-phase
projection**, with `predecessor: null`; it does not replay Issue #92. The external
approved journal retains inherited counts `(5,4,7,5,4)`, Issue #94 allocation
`(1,1,1,1,0)` and effective limits `(6,5,8,6,4)`. One design, one challenge, one
implementation, one initial review, one remediation, one final review, at most two
formal verifications (second only after the sole remediation), zero design revision
or reset, and one PR are authorized. Elapsed time is audit-only. The native default
reset slot grants no reset. Before every later reservation and delivery, the
coordinator reconciles native checks with the external finite journal and full
participant exclusions. The native ledger alone cannot enforce that ancestry.

The source manifest SHA256 is
`8edfaf64f1ad27fe427830fd2582caf0a6c8aa411594e3b98a74fe1d68a2f42d`;
participant inventory SHA256 is
`aaacbbb420f4e9970fc1e6f54b8ec23e9675d3ae451727d274a60a29e740a1e6`;
frozen issue body SHA256 is
`503593a93ad1584be1e49b4c050ad1ca733995bfefecc76defb1204b02c50290`.
The preserved backup is `e7c31b7337c1a94631b4fa7ff73f687b343b49be` and
Issue #92's 33-event raw SHA256 is
`13e3dd82a8aeb5c0a51c302d7f94b658a6c46f867c692b83d9b2c9c02eaa41bb`.
Original missing-ledger S94D1/S94C1 native checks remain rejected and their
reservations consumed; later projection checks are labelled as such. The historical
Issue #92 failed final review remains failed. Certification and independent review
outcomes belong in the excluded current ticket ledger or linked external evidence
after these docs are frozen. No merge is authorized.
