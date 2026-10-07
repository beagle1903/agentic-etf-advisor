# Bounded coordinator arbitration design

Issue #88. Status: DESIGN_READY from separate read-only architect
`/root/arbitration_design` (design_architect, gpt-6-astra/high).
Frozen capsule: `issue-88-bounded-coordinator-arbitration`, generation 1,
digest `5e7df9d37f8cf3d614317a4848a7bd9e83358758610a603647cd3bd9b6da8477`.
Owner: `/root/arbitration_owner`, implementation_worker, gpt-6-sol/medium.
Authorization: user continue in chat `01a11563-1a1b-7be2-ad70-c7d4a60316f2`
on 2026-10-07 for the explicitly queued arbitration scope.
Independent challenge and coordinator approval are required before implementation.

## Scope and boundaries

Frozen S1: permanent arbitration instructions, reusable Markdown decision record,
static guardrails and workflow documentation. Preserve I1-I4: accountable decisions
against frozen criteria, truthful defect closure, existing owner/independence/finite
gates, and workflow-only changes. No product/authentication/financial/provider/database
changes, ledger schema/replay changes, new allowances, stopped-ticket continuation,
Issue23/83/84 or PR85 changes, role settings/registration changes, or accepted-history
rewrites. Product interfaces and graph/checkpoint JSON impact: none. Ledger
schema/event/state impact: none. Instruction and static-validation interfaces change.

## Operational contract

Arbitration is mandatory before another dependent handoff when the same underlying
concern returns after one substantive answer, repair or review response, including
reworded concerns, or when a proposed requirement, success condition or remedy shifts
beyond/conflicts with the frozen capsule or previous closure condition. Compare the
concrete scenario and frozen criterion, not message count. A newly demonstrated defect
always receives attention; repetition cannot suppress it.

The coordinator stops new dependent handoffs and consolidates existing designer,
owner and reviewer evidence in one record. Record phase/reservation state. A running
phase that must stop uses the existing truthful interruption/pause procedure. A
dispatch hold is not automatically an offline coordination_pause; arbitration time
remains recorded under the applicable policy. Do not dispatch sessions merely to
obtain agreement. Further investigation requires a permitted checked/reserved phase.

Classify every concern:

- Demonstrated defect: concrete input/state/execution path, expected versus actual
  result, evidence and violated frozen invariant/AC. Narrow repair and verification
  are required; otherwise stop.
- Contract ambiguity: incompatible readings and their consequential effect. Explain
  clear existing wording with citations; unresolved consequential interpretation
  follows the existing separate architect/challenge/approval path within allowances.
- Preference: no demonstrated frozen-contract failure. Accept or defer with rationale;
  never silently add acceptance criteria.
- Outside scope: absent criterion or explicit non-goal, deferred to separately
  authorized work. A demonstrated current frozen safety/correctness violation still
  blocks delivery. Missing evidence proves neither correctness nor defect absence;
  material uncertainty preventing acceptance requires stop, not a preference label.

Record one primary accountable disposition covering the concerns: narrow repair,
contract clarification, deferral or explicit stop. Record alternatives, disagreements
and rationale. Unanimity is unnecessary. Coordinator authority cannot override
independent certification, waive a demonstrated defect or convert failed checks or
review outcomes into passes.

Set one observable focused closure condition tied to frozen IDs, responsible owner,
verification and next permitted gate. It closes the arbitration episode, not all
ticket acceptance/delivery obligations. Same-scope repair stays with the approved
owner; disagreement alone cannot justify owner replacement or escalation.

Repeated assertions without materially new evidence reference the existing decision.
New material evidence appends to that same episode with its effect and accountable
revision. Further investigation/repair/design reset/review must fit remaining
allowances. Arbitration grants no slot or automatic reset. Failed final review,
exhausted relevant counts, unresolved consequential challenge or serious blockers
produce BLOCKED_FOR_DECISION and require existing explicit finite authorization gates.

## Record and implementation surfaces

Template `docs/workflow/templates/coordinator-arbitration.md`: issue/episode/UTC time/
coordinator; capsule ID/generation/digest/content identity; trigger/prior response;
phase/hold/allowances; role/session/criterion/scenario/expected-actual/evidence/
classification/disputed interpretation table; primary decision/rejected alternatives/
rationale/disagreements; approved owner/next phase/authorization/gates; focused
closure/verification; outcome and appended material evidence. Explicitly grants no
authority, allowance, certification or ledger override.

Completed records live in the active iteration or linked issue-specific workflow
document, outside live ticket JSON. Finish documentation before certification. Later
outcomes use existing excluded current-ticket ledger evidence fields or linked external
evidence; edited certified documentation requires fresh content-bound certification.
Existing blocker/resolve events record actual defects; preferences do not manufacture
blockers. Existing phase outcomes stay truthful. No arbitration event is introduced.

Change AGENTS, CONTRIBUTING, workflow README; developer_instructions only in all six
role TOMLs; the template; new ADR0034; current iteration019; static validator and
isolated static tests. Coordinator alone appends Issue88 ledger. Do not change
ticket_workflow.py, CI, dependencies, accepted history, product architecture or prior
ledgers. Existing State.gate, replay, blocker/resolve and completed certification
remain authoritative.

## Acceptance, verification and risks

AC1/I1: both operational triggers, dispatch hold, consolidated evidence, four
classifications, accountability/rationale/disagreements and focused closure.
AC2/I2: defect requires repair/stop; preference may defer; ambiguity retains design
gates; failures cannot be relabeled. AC3/I3: same owner, sequential checked/reserved
phases, independent challenge/review, finite counts and matching content. AC4/I4:
required checks, unchanged parsed role settings/registrations and historical files,
independent review and ordinary content-bound delivery.

Extend require_markers/require_lines and isolated repository fixtures. Positive cases
accept complete instructions/template from another cwd. Negative cases remove/weaken
each critical clause: triggers, hold, frozen evidence, classification, accountable
decision, truthful closure, same owner, no unanimity/reset, finite gates, preserved
failures, focused closure. Missing/unreadable template and role-return clauses fail
with controlled diagnostics. Preserve role-setting drift rejection tests.

Run focused static/ticket tests, both validators, Ruff lint/format, configured mypy,
offline pytest, retrieval/explanation evaluations, build, both Compose configurations,
diff check and immutable baseline comparisons. No live stores are needed.

Static checks verify required text/settings, not semantic compliance, live behavior,
session independence or authentic authority. Independent challenge/review assess
meaning. Contract ambiguity returns to the architect within remaining allowance;
failed final review/exhaustion stops for user decision; out-of-scope work is deferred.

DESIGN_READY
