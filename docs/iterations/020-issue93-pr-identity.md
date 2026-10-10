# Iteration 020: Issue #93 PR identity gate

Issue #93 implements the frozen capsule `issue-93-complete-queued-live-pr-identity`,
generation 1, digest
`db10264da16042d7602eda0dbbf19670218abde5689c92a7f10f00f8beeef260`.
Classification is consequential. The approved owner is `/root/issue93_owner`,
`implementation_worker`, `gpt-6-sol`, medium. User authority is the single
three-child split approval recorded in the capsule. The separate S93D1 architect
handoff, S93C2 independent challenge and coordinator approval preceded the
implementation reservation. S93C1 failed and remains failed; one additional
challenge was explicitly authorized solely for S93C2. No design reset, extra grant,
second PR or merge is authorized.

The implementation validates complete queued and live PR identity, including event
repository/base consistency, while permitting a matching head fork. It returns the
validated live PR body/base/head to the existing CI gates. Focused tests cover
malformed and stale identities, ordinary and fork matches, live CLI consumption and
preserved delivery/prefix controls. ADR 0035 records the decision. Application graph
JSON, financial logic and provider boundaries are unaffected.

The native `docs/workflow/tickets/issue-93.json` ledger is a **local-phase
projection**. The approved administrative setup preserves the inherited
implementation/initial-review/remediation/final-review/design-reset counts
`(5,4,7,5,4)` and allocates Issue #93 `(1,1,1,1,0)` from the single shared
three-child pool `(3,3,3,3,0)`. Effective Issue #93 limits are `(6,5,8,6,4)`;
formal verification is limited to two reservations, with the second available only
after the sole remediation. The native default reset slot grants no reset. The
coordinator must reconcile the authoritative external journal, source inventory,
historical participant exclusions and native check before every later reservation
and delivery. The native ledger alone cannot enforce that ancestry or approval.

The administrative source manifest SHA256 is
`8edfaf64f1ad27fe427830fd2582caf0a6c8aa411594e3b98a74fe1d68a2f42d`;
the participant exclusion inventory SHA256 is
`aaacbbb420f4e9970fc1e6f54b8ec23e9675d3ae451727d274a60a29e740a1e6`.
The retained S93D1 handoff raw SHA256 is
`66b8fcfd3004c6ffe3b4a69bebf065e76e0571c9095dd4158c8e973a46dfed45`;
the frozen capsule file raw SHA256 is
`a12927e7939f6a50097db38b7ce76350330e57970ce48b6ee69c52f2ee545536`.
The source manifest binds the backup commit
`e7c31b7337c1a94631b4fa7ff73f687b343b49be` and the preserved Issue #92
33-event raw SHA256
`13e3dd82a8aeb5c0a51c302d7f94b658a6c46f867c692b83d9b2c9c02eaa41bb`.
The manifest freezes 124 sources; the inventory identifies 35 historical participants
and rejects all three prohibited historical reviewer substitutions for new independent
selection. The preserved backup's
`B92-HISTORICAL-REVIEWER-REUSE` failure is not a current certificate.

The native missing-ledger setup rejection and S93C1 failed challenge remain in the
external record; the approved one-time projection materialized only the genuine
S93D1 and S93C2 successes. This procedure is specific to Issue #93. Formal
content-bound verification and independent review outcomes belong in the excluded
current ticket ledger or linked external evidence after documentation is frozen.
