# Issue 103 arbitration A103-1

Coordinator `/root`, 2026-10-14. Primary decision: contract clarification.
Dispatch hold is recorded as elapsed audit time, not an offline coordination pause.

## Frozen criterion and evidence

Capsule `issue-103-yahoo-catalogue` generation1 digest
`552e8871276002b83388d4b8867bbdae0d27e543f831194a41faf857ca440b83`.
Relevant INV103-3/4 and AC103-3/5 require exact listing identity, retained validated
direct additions, deduplicated counts, immutable versioning and prior-version safety.
Architect `/root/issue103_design` returned DESIGN_READY in
`docs/iterations/024-issue103-catalogue-design.md`. Independent challenge
`/root/issue103_challenge` returned FAIL: contract ambiguity, not implementation defect.

Scenario: directly add VWCE.DE, then a full refresh enumerates the same listing tuple
with changed name or currency. Handoff retains direct observations, replaces discovery,
and rejects conflicting refreshed identity, but leaves overlap representation, conflict
fields, combined count and selected search observation underspecified. Identity tuple
is explicit; that alone does not choose authority among overlapping observations.
No implementation exists, so no expected-versus-actual runtime defect is claimed.

## Classification and accountable decision

Contract ambiguity: one reading rejects a complete refresh for changed optional
metadata; another stores two differing current records for one identity. Their effects
on publication, retention and search differ. Coordinator agrees this material
acceptance uncertainty needs a separate architect clarification rather than an owner
making a persistence choice. No new acceptance criterion or scope is authorized.

Rejected: silently waive failed challenge; infer financial correctness from cache;
drop direct provenance; broaden to research/eligibility; replace implementation owner;
grant/reset phase limits. No participant disagreement about the need to clarify is
currently recorded. Reviewer reported no other design blocker.

## Reservation, allowance and closure

Challenge reservation ends truthfully FAIL. Implementation, initial review, remediation,
final review and design reset each have one remaining default slot before reset start.
Coordinator uses the permitted single design_reset against INV103-4, in a fresh
read-only design_architect session `/root/issue103_design_reset`; native check and
reservation precede dispatch. Reset advances capsule generation without changing
frozen definitions or clearing consumption.

Observable closure: architect supplies one deterministic rule table for same-identity
overlap, changed optional observations, actual identity conflict, retained provenance,
combined listing count and returned search observation. Rules preserve original direct
observation times and prior usable cache on genuine conflict. Independent challenge
of that table must pass against INV103-3/4 and AC103-3/5 on the same capsule generation;
coordinator approval then permits the unchanged owner implementation gate.
Closure ends this episode, not ticket acceptance. New evidence revises this episode;
repeated assertions without evidence refer to its decision. No automatic further reset.

## Closure outcome

2026-10-14: separate reset architect supplied deterministic two-component observation
rules; capsule generation2 digest
`b9c97b4c7f067883a8752c7b8846b9cb63c85ca5848c926e3567542074b7a234`.
Fresh independent `/root/issue103_challenge2` code_reviewer/gpt-6-sol/high returned PASS
against all frozen criteria. A103-1 focused closure is satisfied: direct/discovered
overlap fixture has exact provenance preservation, whole-discovered authority, no
backfill, union counts, omission retention and exchange-conflict preservation rules.
Coordinator approves this handoff; next gate is native implementation check/reservation
for unchanged owner `/root/issue103_owner`. Initial failed challenge remains history.
Consumed reset1; remaining implementation1/initial_review1/remediation1/final_review1,
design_reset0. Episode closed; acceptance and delivery remain outstanding.
