# Agent operating instructions

## Read order

Before changing the project, read these files in order:

1. `wishlist.md` for raw user intent.
2. `docs/product/vision.md` for stable scope and non-goals.
3. `docs/architecture/system.md` for the current system shape.
4. Relevant records under `docs/architecture/decisions/`.
5. The active file under `docs/iterations/`.

## Ticket design and implementation workflow

Every issue-backed work item, including bugs, documentation, evaluations, and verification,
uses separate sequential sessions with explicit project-scoped roles in `.codex/agents/`.
The coordinator records the selected role, model, effort, rationale, and escalations.

1. **Design phase:** select `planning_analyst` only for a low-risk solution fully determined by
   existing architecture. Financial eligibility, safety, authentication, persistence or replay,
   security, and other consequential contracts require `design_architect` regardless of diff size.
   Unclear dependencies or acceptance criteria route to `code_reviewer`; architectural ambiguity
   routes to `design_architect`. Review roles return findings and cannot authorize implementation.
2. **Design gate:** record and approve a complete `DESIGN_READY` handoff in the issue, canonical
   iteration document, or dedicated design document. Include scope, non-goals, invariants,
   interfaces, JSON/state impact, acceptance criteria, focused tests, documentation needs, and
   risks. A missing, incomplete, or `DESIGN_BLOCKED` handoff blocks any write-capable role.
3. **Implementation phase:** select the approved scope's write-capable role from the table below.
   It follows the handoff, adds focused tests, runs required gates, and records remaining scope.
4. **Escalation:** agents must not silently redesign or change model or effort. The coordinator
   records the reason and starts a separate sequential session. Return architectural ambiguity
   to `design_architect` before remediation.

| Role | Model | Effort | Access |
| --- | --- | --- | --- |
| `planning_analyst` | `gpt-5.6-terra` | medium | read-only |
| `design_architect` | `gpt-6-astra` | high | read-only |
| `bounded_worker` | `gpt-5.6-terra` | medium | workspace-write |
| `implementation_worker` | `gpt-5.6-sol` | medium | workspace-write |
| `code_reviewer` | `gpt-5.6-sol` | high | read-only |
| `implementation_specialist` | `gpt-5.6-sol` | high | workspace-write |

The detailed task matrix is authoritative; Terra → Sol → Astra is routing shorthand, not a
mandatory sequence through all roles.

| Task | Default | Escalation |
| --- | --- | --- |
| Search and aggregation | planning_analyst | design_architect for conflicting sources, nuanced conclusions, or consequential recommendations |
| Code review | code_reviewer | design_architect for security, concurrency, architecture, large diffs, or subtle correctness |
| Feature design | design_architect | planning_analyst only when low-risk and fully determined by existing architecture |
| Subtask planning | planning_analyst | code_reviewer for unclear dependencies or acceptance criteria; design_architect for architectural ambiguity |
| Implementation | implementation_worker | implementation_specialist for cross-cutting changes, unfamiliar code, migrations, concurrency, or difficult debugging |
| Unit tests | bounded_worker | implementation_specialist for important edge cases or complex stateful behavior |
| Integration tests | implementation_specialist | design_architect for distributed systems, nondeterminism, difficult infrastructure, or unclear failures |
| CI/CD | implementation_worker | implementation_specialist for production deployment, secrets, permissions, releases, or provider-specific failures |
| Review comments | bounded_worker for straightforward fixes; implementation_specialist for substantive remediation | code_reviewer for analysis; design_architect for systemic design or safety problems |

Low effort fits clear, mechanical, low-impact work; medium fits ordinary multistep engineering;
high fits ambiguity, important edge cases, or costly mistakes. `xhigh` is exceptional and
`max`/`ultra` are last-resort settings, not routine quality switches. These six pinned roles
do not silently adopt those settings. Lower effort for a routine follow-up requires a newly
selected appropriate role/session. Luna/low may be explicitly selected for bounded read-only
fact gathering; it cannot issue a design gate or implement a ticket. No permanent Luna role
or GPT-5.5 default is added.

Dependent phases remain sequential, with no parallel subagents. All six roles have explicit
descriptions and relative `config_file` registrations. ADR 0018 compatibility policy remains:
no `enabled`, generic-agent model/effort defaults, concurrency scalars, `max_threads`, default
role, or project-level model override. Sequencing is coordinator policy, not a runtime cap.
ADR 0020 supersedes the earlier fixed routing; accepted ADRs remain history.

Any one-off workflow exception must be explicitly approved and recorded in the issue and PR.
Static validation checks configuration and markers, not actual live-session provenance.

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
