# Agent operating instructions

## Read order

Before changing the project, read:

1. `docs/product/vision.md` for stable scope and non-goals.
2. `docs/architecture/system.md` for the current system shape.
3. Relevant records under `docs/architecture/decisions/`.
4. The relevant active file under `docs/iterations/`.

## Working agreement

Use the issue and PR to record the problem, authorized scope, non-goals, observable acceptance
criteria, accountable owner and verification. Keep this proportionate to the change; routine
work does not require a separate planning session or repeated user approval.

- One implementation owner completes implementation, meaningful focused tests, self-review,
  documentation and verification. Same-scope review fixes stay with that owner.
- Use separate `design_architect` advice and coordinator approval before changing consequential
  financial, identity, security, persistence/replay or architecture contracts. Add independent
  `code_reviewer` review for consequential, high-risk or disputed changes. Review findings must
  identify a concrete failure against the agreed requirements; preferences do not silently add scope.
- Resolve repeated disagreements with one accountable coordinator decision citing the scenario,
  evidence and observable closure condition. Material defects remain open until verified or the
  affected change is stopped; do not turn failed checks into passes.
- Ask the user when intended scope materially changes, a consequential choice cannot be resolved
  from existing authorization, or a destructive or external financial action needs approval.
  Continue authorized work without another permission loop.
- Keep dependent role handoffs sequential. Delegate only when useful or required by the affected
  contract; multiple files or unfamiliarity alone do not require escalation.

Before a broad implementation, and when new evidence shows a recurring contract question or
expanding acceptance, consider whether the issue still has one reviewable outcome. Concrete
indicators include several independently useful results or components needing distinct evidence.
File count, unfamiliarity and an ordinary defect do not imply a split. Record one accountable
choice: same-scope repair with the owner, a proposal for independently deliverable sub-issues, or
an explicit stop. Keep inseparable consequential invariants together and use their design gate.
For a proposal, map every original requirement to a child, an authorized deferral or a blocker;
use native parent/sub-issue and dependency links, execute proposed children one at a time, and
verify parent acceptance beyond child merges. See [contributor guidance](CONTRIBUTING.md#early-decomposition-decision).

There are no mandatory ticket ledgers, phase reservations, elapsed-time budgets, finite-attempt
grants, design generations, repository-content certificates or delivery bindings for prospective
work. Historical ADRs, ledgers, failed outcomes and PR bindings remain audit evidence; do not
rewrite or relabel them. An old ticket's exhausted attempts do not prohibit normal use of a
merged app. Do not claim a different scenario satisfies that ticket's original acceptance.

## Model presets and assignments

| Preset | Model | Effort |
| --- | --- | --- |
| `astra` | `gpt-6-astra` | high |
| `sol` | `gpt-6.1-sol` | medium |
| `luna` | `gpt-6-luna` | medium |

These three explicit relative `config_file` registrations choose only model and effort. A fresh
dispatch separately records its preset/model/effort, assignment, activity, participant and owner
references, scope, permitted actions, acceptance, rationale, authorization, consequential status,
observed inherited access and `instruction-only` restriction. `owner_ref` is accountability, not
a fourth preset. The assignment names remain `planning_analyst`, `design_architect`,
`code_reviewer`, `bounded_worker`, `implementation_worker` and `implementation_specialist`.

`planning_analyst` performs discovery, `design_architect` design, and `code_reviewer` review or an
optional challenge; these assignments may inspect and report only, with no edits, mutating commands,
external actions or delegation. The other three assignments perform implementation, remediation
or verification within approved scope; verification does not edit. Use `bounded_worker` for
mechanical work, `implementation_worker` for ordinary work, and `implementation_specialist` only
with a concrete complexity or unresolved-failure rationale. A writer's participant must be the
owner. Explicit delivery responsibility may add commit/push/PR actions for a writer. No-write
instructions apply even when the parent grants full access: they are not a filesystem sandbox or
authentication. Record the observed parent/tool access honestly and stop actions outside the
assignment.

Consequential writes retain separate design advice and coordinator approval. Keep dependent
handoffs sequential. A reviewer is independent of the owner and every implementation, remediation
and verification author; optional challenge is independent of its design author. Challenge is not
a mandatory prospective phase under ADR 0049. The optional `--declaration PATH` validator checks
only a JSON declaration's internal consistency, not identity, authority, parent permissions or
whether a handoff happened. The coordinator checks actual participants and authorization. Existing
sessions and historical records retain their original role/model/effort identities; no migration.

Preserve ADR 0018 restrictions: no generic defaults, project-level model override, `enabled`,
concurrency scalar, `max_threads` or default role. See [ADR 0051](docs/architecture/decisions/0051-model-presets-and-assignments.md).

## Delivery and product safeguards

- Work in short vertical slices with explicit acceptance criteria.
- Keep graph state JSON-serializable and checkpoint/replay behavior reliable.
- Put nondeterministic calls and side effects behind explicit replaceable interfaces.
- Add or update meaningful tests with every behavior change; run the checks appropriate to it.
- After verification, commit, push the branch and open a PR without separate permission.
- Keep provider, database and market-data integrations replaceable.
- Never commit credentials, tokens, downloaded private data or `.env` files.
- Do not execute trades or imply guaranteed returns.
- Every market-data result retains source and observation timestamp metadata; make missing,
  stale and conflicting evidence visible. Preserve deterministic financial rules, exact money,
  duplicate-exposure checks, human review and supported saved-state safeguards.
- Any future write to an external financial system requires separate human approval.

## Durable knowledge

Update stable product facts in `docs/product/`, current architecture in
`docs/architecture/system.md`, and iteration-specific choices/evidence in `docs/iterations/`.
Record consequential decisions in a new ADR; do not rewrite accepted history.
