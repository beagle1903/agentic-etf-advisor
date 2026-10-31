# A132-1: event-specific authority accounting evidence

Opened 2026-10-30 by coordinator `/root`; approved governance capsule generation1
4338ddbd905054aefed3e2bf594200472ea9fe1a15cdaf12866f226d9bec9e30.
Reviewed content3754728d38abe8ec8214c17e7ae3f08bfaa669b68b68829bf61fbcff8d3f6e6e.

The independent initial reviewer `/root/issue132_review`, code_reviewer /
gpt-6-sol / high, returned FAIL against AC132-3. A prior model-capacity error
was an agent-turn interruption, not a review outcome; the same logical phase
was retried with its original pinned role and reservation, retaining elapsed audit.

## Scenario and classification

Frozen INV132-2/3, AC132-3 and exact handoff require later authority references
and connected-lineage reuse tests specific to local_registry_authority. Existing
tests establish standalone authority_records and validate_map plus prior/governance
reuse. They do not construct a later capsule_update carrying replacement authority
as a reference or a connected descendant/sibling reusing that new normalized
authority. The new branches in authority_records/validate_map therefore lack
required event-specific acceptance evidence. Generic old-event tests do not
exercise this new event. Expected: legitimate reference accepted without another
grant; new normalized authority use in connected lineage rejected in both
applicable orders. Actual: those test scenarios absent.

Classification: material frozen-acceptance verification gap, no demonstrated runtime
defect. Missing evidence establishes neither correctness nor a product failure.
This concern is already in the frozen criterion; it is not a new requirement.
The initial review remains FAIL. The earlier owner self-review and acceptance
are historical outcomes, not grounds to waive the missing evidence.

## Accountable disposition and focused closure

Primary decision: narrow same-owner remediation using the existing authorized
remediation1 slot, followed by fresh content-bound verification/acceptance and
independent final_review1. No design reset, new slot, scope or owner change.
Owner `/root/issue132_owner`, implementation_worker / gpt-6-sol / medium.
Before dispatch check/reserve remediation; no concurrent dependent phase.
Before repair: implementation1/1, initial_review1/1, remediation0/1,
final_review0/1, design_reset0/1; no new allowance is granted by this record.

Closure condition: add meaningful synthetic event-specific tests that prove a
legitimate later capsule authorization reference is accepted without consumption
as a second authority, and new connected descendant/sibling reuse rejects with
normalized evidence in both applicable insertion orders. Run focused relevant
workflow/lineage suites and required affected checks; update audit docs before
fresh content binding. Resolve the corresponding blocker only with counted repair
evidence. If tests reveal an in-scope defect, repair it narrowly under the same
capsule; material architectural ambiguity stops rather than silently redesigning.

Rejected: relabel initial review as pass; substitute generic old-event tests;
invent unrelated runtime enforcement; dispatch architect for agreement; replace
owner; erase original acceptance/failure; grant a slot through arbitration.
Unanimity is unnecessary. The final reviewer must assess the exact repaired
content and closure evidence, excluding every write/verification author.
Final review failure or exhausted allowance stops BLOCKED_FOR_DECISION.

Later outcomes are recorded in the excluded Issue132 ticket ledger. This record
must be complete before renewed content certification; no new event type is added.
No actual Issue123 ledger, acquisition, key or publication operation is authorized.

## Owner repair evidence prepared for fresh gates

The approved owner added event-specific synthetic tests in
`tests/test_ticket_local_registry_authority.py`. A later counted design reset
and `capsule_update` carrying the generation-5 replacement authorization is
accepted as a reference: `authority_records` marks `reference=True`, and
`validate_map` accepts it without another consumed grant. A fully replayable
generation-6 Issue123 parent with a distinct finite split creates two synthetic
descendants. Their otherwise valid extension and child-split events, using a
renamed and normalized form of the local authority, each pass local replay but
fail connected-lineage validation with `authority reused within connected
lineage`. Child issue 99 and 202 exercise the two accounting insertion orders;
distinct-authority controls validate. A same-ticket continuation reuse is
also rejected. Native predecessor children cannot use continuation, so that
path is tested on the eligible parent. No runtime code changed during this
repair. This is owner evidence for the frozen AC132-3 closure condition, not a
reclassification of the failed initial review or content-bound acceptance.
