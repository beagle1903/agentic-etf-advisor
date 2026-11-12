# Coordinator decision record

Use this record in an issue or iteration when a concern recurs after a substantive response or
the proposed requirement, remedy or success condition shifts. Ordinary first-pass work needs no
episode. The current [ADR 0049 agreement](../../architecture/decisions/0049-prospective-working-agreement.md)
governs prospective work; [ADR 0034](../../architecture/decisions/0034-bounded-coordinator-arbitration.md)
and [ADR 0036](../../architecture/decisions/0036-owner-led-conserved-split-lineage.md) retain
their historical ledger meaning. This record grants no split, authority or acceptance.

- Issue / episode / UTC date / coordinator:
- Authorized scope and original acceptance criteria (link or IDs):
- Trigger, concrete scenario and prior substantive response:
- Evidence and expected versus actual result; missing evidence and disputed readings:
- Classification: demonstrated defect / contract ambiguity / preference / outside scope:
- Loop indicators, if any: independently useful outcomes / recurring contract question /
  expanding acceptance / components needing distinct evidence or review:
- One accountable choice: bounded same-scope repair / independently deliverable sub-issue
  proposal / explicit stop (include contract clarification or authorized deferral if applicable):
- Rejected alternatives, disagreement and rationale:
- Owner, focused observable closure condition, verification and next permitted step:
- Outcome and evidence link; later material evidence and accountable revision:

For a proposed decomposition, record each child's outcome, acceptance criteria, non-goals,
interfaces and state impact, dependencies, owner, verification and PR outcome. Map **every**
original requirement to a child, an authorized deferral or a remaining blocker; link native
GitHub parent/sub-issues and blocked-by dependencies. Execute dependent children sequentially.
Check parent acceptance separately after child PRs merge. A same-scope defect stays with its
owner; an inseparable consequential invariant stays together and follows the current design gate.

A demonstrated defect requires verified repair or an explicit stop. Do not relabel a failed check
or historical result as passed. For historical ledger tickets, cite their actual phase, outcomes,
remaining allowances and applicable authorization without editing or resetting them. Prospective
work under ADR 0049 has no mandatory ledger, reservation, allowance or content certificate.
