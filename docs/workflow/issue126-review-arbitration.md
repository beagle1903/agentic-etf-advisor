# Issue126 coordinator arbitration A126-2

- Opened: 2026-10-27, after `/root/issue126_review` completed initial review FAIL.
- Coordinator: `/root`, standing Issue126 implementation authorization and
  AGENTS/ADR0034 arbitration authority. No additional user authority or count grant.
- Frozen capsule: issue-126-audited-curator-fund-identities, generation1 digest
  `c50e07ba8308449c2f0fd402de5f1a94aafe8cf7d38bb598363d349626be3335`.
- Failed reviewed/verified content:
  `6b9e2254cf24d97fc3ff1adbaf431946bf02a75d653208ceb1ca5e361d119962`.
- Trigger: concrete review reproductions return to the inventory/history
  completeness concern after owner self-review tightened mapped inventory and
  offline transition binding. Consolidate before a dependent repair handoff;
  the new unmapped-row and lineage-deletion evidence receives attention.
- Current state: implementation1/1 and initial review1/1 consumed; no active phase.
  Remediation1, final review1, design reset1 remain. Verification and acceptance
  bind failed content only, and cannot certify a changed repair. Delivery blocked
  by failed review and B126-INVENTORY/B126-LINEAGE.
- Dispatch hold only; no coordination_pause or time subtraction. Review finished
  before this record; original owner will receive a checked reserved remediation.

| Role/session | Frozen criterion | Concrete expected/actual evidence | Classification |
| --- | --- | --- | --- |
| Reviewer `/root/issue126_review` | INV126-1/2, AC126-1/2 | `_envelope()` plus a source-backed row with key=null, isin=null, disposition=unresolved, source_locator=synthetic#inventory in its active context passes both envelope validation and initial publication after digest recomputation. Existing checks guard mapped keys only (fund_identity.py lines556-560,759-763). Expected: affected active context cannot publish unresolved/unmappable inventory. | Demonstrated defect B126-INVENTORY. |
| Reviewer `/root/issue126_review` | INV126-2/3, AC126-1/3 | Initial envelope -> valid rename successor with lineage ['fund'] -> third generation refresh clearing lineage [] with valid parent/digests/transition/inventory passes actual-parent publication. Global source and alias remain but explicit completed-event lineage disappears (parent diff lines680-704). Expected: historical lineage references retained. | Demonstrated defect B126-LINEAGE. |
| Architect `/root/issue126_design` / handoff035+036; challenger `/root/issue126_challenge` | Same IDs | Unresolved/unmappable rows require affected suspension, active affected Funds reject; historical-only lineage remains immutable while current proof is independently fresh. The existing design states the expected results and trust boundary. | Clear frozen contract, no competing explicit reading requiring redesign. |
| Owner `/root/issue126_owner` | Same IDs | Mapped inventory coverage and several source/history cases passed existing tests. These tests did not cover null-key unresolved rows or post-rename lineage deletion. | Existing evidence is incomplete for the new concrete scenarios; it proves neither their correctness nor absence. |

## Primary accountable decision: narrow repair

Authorize the same approved implementation owner to repair both demonstrated
failures within the existing single remediation allowance. Enforce the affected
active-context inventory safeguard for unmapped unresolved rows in both internal
bound-envelope and actual-parent publication validation as appropriate. Retain
historical completed-event lineage references across later generations; refreshing
current proof cannot delete them. Preserve legitimate suspended inventory,
resolved mappings, positive rename/current-proof refresh and historical no-expiry
behavior. Keep original source observations and current C(F) rules unchanged.

The reproductions are new material evidence. Neither finding changes the frozen
contract or authorizes scope expansion. Reject delivery with known defects,
relabeling initial review as pass, a new owner, automatic design reset, a new
ticket/count pool, or extra agent agreement polling. No disagreement with the
reviewer's expected behavior is presently recorded; future concrete incompatible
evidence belongs in this episode before any dependent handoff.

## Observable focused closure

Owner `/root/issue126_owner`, implementation_worker/gpt-6-sol/medium, adds:

- Initial and successor active-context publication failures for source-backed
  unresolved unmapped inventory rows, plus appropriate suspended/resolved controls.
- A three-generation rename/refresh test rejecting removal of historical lineage
  references, plus fresh current endpoint proof retaining historical lineage.

Run focused registry/propagation/offline/legacy regressions and required current
checks. Update only necessary reviewable documentation/evidence before fresh
content-bound verification. All changed content needs new acceptance and independent
final review; prior certificates cannot be reused. Resolve native blockers only
after successful reserved remediation. The next permitted gates are same-owner
verification then independent final review, with checks/reservations in order.
Failed final review stops for explicit finite user authority. Closure is not ticket
acceptance, delivery, source authenticity or live readiness.

Outcome pending; later closure evidence belongs in the excluded current-ticket
ledger, without modifying certified documentation after final review.

## Same-episode new evidence during reserved remediation

Coordinator inspected the focused repair before certification. Publication now
rejects null-key/ISIN rows unless disposition is unresolved, then rejects an
affected active Fund. The bound RegistrySnapshot validator still only guards
disposition=unresolved. A null-key/ISIN row labeled unchanged with both statuses
null can skip both mapped-row validation and that disposition guard; source-backed
envelope validation may accept it although publication rejects it. This is the
same B126-INVENTORY declared-coverage defect at the offline boundary, not a new
criterion. Accountable revision: include a focused reproduction and align strict
internal unmapped-row classification with publication before fresh certification;
no parent lookup is needed. Original owner and same remediation reservation.

The owner also reported a same-defect edge: an active successor retains former
context A as an alias after rename to B; an unresolved inventory row in touched A
must affect that successor even if all current assertions use B. Include the
retained alias/touched-context control in the same focused safeguard. A baseline
run was truthfully interrupted at approximately 11% before this refinement; it is
not a failed or completed verification result. No additional phase/count granted.
