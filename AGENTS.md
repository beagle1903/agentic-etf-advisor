# Agent operating instructions

## Read order

Before changing the project, read these files in order:

1. `wishlist.md` for raw user intent.
2. `docs/product/vision.md` for stable scope and non-goals.
3. `docs/architecture/system.md` for the current system shape.
4. Relevant records under `docs/architecture/decisions/`.
5. The active file under `docs/iterations/`.

## Ticket design and implementation workflow

Every issue-backed work item, including bugs, documentation, evaluations, and verification, uses
an explicit project-scoped role from `.codex/agents/`. The coordinator records the classification,
selected role, model, effort, rationale, authorization, and any escalation evidence.

1. **Classify by impact:** mechanical and architecture-determined work uses `bounded_worker`;
   ordinary work within established contracts uses `implementation_worker`. Financial eligibility,
   safety, authentication, persistence or replay, security, and other consequential contracts
   require a separate `design_architect` handoff regardless of diff size.
2. **Record the design capsule:** every issue has a complete `DESIGN_READY` capsule before implementation edits.
   It records classification, owner role/model/effort, rationale and user
   authorization; scope and non-goals; invariants, affected interfaces, and JSON/state impact;
   acceptance criteria and focused verification; documentation needs, risks, and escalation
   triggers. Record an explicit `none` for unaffected interfaces or state.
3. **Complete routine work in one session:** for mechanical and ordinary work, the authorized
   implementation owner may author and record the capsule, then implement, add focused tests,
   self-review, run verification gates, and document limitations in that same session. A separate
   planning or review session is not a routine prerequisite, and repeated user approval is not
   required after the authorized capsule is recorded.
4. **Gate consequential work:** only a separate read-only `design_architect` session may produce
   the consequential handoff, and the coordinator must approve it before a write-capable role
   starts. A missing, incomplete, unapproved, `DESIGN_BLOCKED`, or out-of-scope capsule blocks
   implementation. Review findings cannot authorize implementation or contract changes.
5. **Escalate from evidence:** high-risk or disputed output adds an independent `code_reviewer`.
   Concrete complexity, unresolved failure, concurrency, migration risk, or consequential
   ambiguity may require `implementation_specialist`. The coordinator records the trigger and
   starts a fresh separate sequential session. Multiple files, integration tests, or unfamiliarity alone do not require escalation.
   Architectural ambiguity returns to `design_architect`.
6. **Bound the ticket lifetime:** follow ADR 0026 and the finite ledger policy below.
   Exhaustion and failed final review stop work for explicit user decision. No automatic
   design reset, replacement agent or quota reset replenishes limits.

| Role | Model | Effort | Access |
| --- | --- | --- | --- |
| `planning_analyst` | `gpt-6-luna` | medium | read-only |
| `design_architect` | `gpt-6-astra` | high | read-only |
| `bounded_worker` | `gpt-6-luna` | medium | workspace-write |
| `implementation_worker` | `gpt-6-sol` | medium | workspace-write |
| `code_reviewer` | `gpt-6-sol` | high | read-only |
| `implementation_specialist` | `gpt-6-sol` | high | workspace-write |

The classification table is authoritative; Luna → Sol → Astra is routing shorthand, not a
mandatory sequence through all roles.

| Classification | Owner and execution contract |
| --- | --- |
| Mechanical, low-risk, architecture-determined | `bounded_worker` owns the capsule, implementation, focused tests, self-review, and verification in one session. |
| Ordinary feature or bug within established contracts | `implementation_worker` owns the same complete sequence in one session. |
| Consequential contract | `design_architect` produces the separate approved handoff before `implementation_worker` starts. |
| High-risk or disputed implementation | Add `code_reviewer` after implementation and record the trigger and findings. |
| Demonstrably difficult implementation | Escalate to `implementation_specialist` in a fresh session with a concrete recorded reason. |

`planning_analyst` remains available for explicitly requested read-only discovery and planning.
It is not a routine prerequisite. Routine review fixes remain with the implementation owner when
they fit the approved capsule.

Low effort fits clear, mechanical, low-impact work; medium fits ordinary multistep engineering;
high fits ambiguity, important edge cases, or costly mistakes. `xhigh` is exceptional and
`max`/`ultra` are last-resort settings, not routine quality switches. These six pinned roles
do not silently adopt those settings. Lower effort for a routine follow-up requires a newly
selected appropriate role/session. Luna/low may be explicitly selected for bounded read-only
fact gathering; this exception cannot issue a design gate or implement a ticket. No GPT-5.5
default is added.

Required dependent phases remain sequential, with no parallel subagents. All six roles have explicit
descriptions and relative `config_file` registrations. ADR 0018 compatibility policy remains:
no `enabled`, generic-agent model/effort defaults, concurrency scalars, `max_threads`, default
role, or project-level model override. Sequencing is coordinator policy, not a runtime cap.
ADR 0022 supersedes ADR 0020 only for mandatory routine phase separation and task-by-task routing;
[ADR 0025](docs/architecture/decisions/0025-gpt6-codex-role-routing.md) supersedes only earlier
pinned model assignments and the permanent-Luna prohibition;
accepted ADRs remain history.

Any one-off workflow exception must be explicitly approved and recorded in the issue and PR.
Static validation checks configuration and markers, not actual live-session provenance.

## Finite ticket lifetime (ADR 0026)

Every future agents-lab ticket has one durable ledger at
`docs/workflow/tickets/issue-N.json`, initialized before any phase. The frozen scope,
invariant IDs and acceptance IDs apply across agents, sessions, quota resets and design resets.
Freeze the complete capsule definitions, owner/model/effort, rationale/authorization,
non-goals, interfaces, explicit JSON/state impact, verification, docs, risks and triggers.
Design, challenge and approval bind the same immutable digest and current generation.
Classified write ownership and any concrete specialist escalation must be recorded;
reviews exclude every implementation, remediation and verification author.
Default budget: 120 active minutes across all work, including discovery, design,
challenge, implementation, verification and review. Start reserves the counted slot;
crashed open phases consume through the current time. Explicit pause records elapsed
and resume continues the same reserved phase. No unrecorded time subtraction.

At most one initial review, one remediation, one final review and one design reset
per ticket lifetime. One implementation pass is the default. A reset consumes the
original budget and never clears counters. Consequential design requires a separate
independent challenge before coordinator approval; challenge is not code review.
Review findings identify a concrete failure scenario and a frozen invariant or AC;
scope expansion becomes separate work. Failed final review, unresolved challenge,
exhaustion or serious blockers means BLOCKED_FOR_DECISION, never delivery of defects.
Clean final review may deliver without another phase slot. A finite attempt is
promised, successful completion is not.

Before dispatch, run `uv run python scripts/ticket_workflow.py check --issue N --phase PHASE`;
then append the phase_start event before starting its agent. Before delivery run the
same check with `--phase delivery`. Append measured phase ends, acceptance evidence,
review outcomes and blocker resolutions. One writer uses atomic validated append.
Explicit finite user extensions append additional seconds and phase counts with named
authority and evidence; no automatic renewal. Splits require explicit user decision,
validated predecessor history, inherited counters and allocated remaining time;
sibling allocations total no more than the predecessor remainder. A split retires
its predecessor. New issue numbers cannot silently evade limits.

Recorded enforcement is not a runtime kill switch. The coordinator must truthfully
record evidence, check open phases periodically and interrupt active agents on
exhaustion. Static validation cannot authenticate approval or session provenance. Approval evidence
is single-use despite changed display names or surrounding/internal whitespace.
Review, verification and acceptance bind identical repository content. Delivered ledgers
authorize only their original PR identity and that content; reruns preserve the binding.
CI validates immutable merge-base history and current primary issue binding on PR
edits. Existing historical tickets are not retrospectively adopted. Issue70 remains
stopped pending a separate user decision; this workflow ticket changes no product code.

## Delivery rules

- Work in short vertical slices with explicit acceptance criteria.
- Keep graph state JSON-serializable so checkpointing and resume remain reliable.
- Put nondeterministic calls and side effects behind explicit interfaces.
- Add or update tests with every behavior change.
- After a phase is complete and verified, commit it, push its branch, and create a pull
  request without waiting for separate approval.
- Keep provider, database, and market-data integrations replaceable.
- Never commit credentials, tokens, downloaded private data, or `.env` files.
- Do not execute trades or imply guaranteed returns.
- Every market-data result must retain source and observation timestamp metadata.
- Any future write to an external financial system requires a separate human approval.

## Long-term memory

- Update stable product facts in `docs/product/`.
- Update the current design in `docs/architecture/system.md`.
- Record consequential decisions as a new ADR; do not rewrite accepted history.
- Record iteration-specific choices and evidence under `docs/iterations/`.
- Keep `wishlist.md` as raw input; do not silently normalize or delete its contents.
