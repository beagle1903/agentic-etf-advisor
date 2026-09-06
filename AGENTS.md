# Agent operating instructions

## Read order

Before changing the project, read these files in order:

1. `wishlist.md` for raw user intent.
2. `docs/product/vision.md` for stable scope and non-goals.
3. `docs/architecture/system.md` for the current system shape.
4. Relevant records under `docs/architecture/decisions/`.
5. The active file under `docs/iterations/`.

## Ticket design and implementation workflow

Every issue-backed work item, including bug fixes, documentation changes, evaluations, and
verification tasks, follows two sequential agent phases. Use the project-scoped agents in
`.codex/agents/`; do not leave the model or reasoning effort implicit.

1. **Design phase:** invoke `design_architect` with `gpt-6-astra` and `high` reasoning effort.
   It is read-only and must inspect the issue plus the required repository records. It returns a
   compact handoff with scope, non-goals, invariants, affected interfaces, JSON/state impact,
   acceptance criteria, focused tests, documentation needs, and risks. It must not edit source,
   tests, CI, configuration, or runtime files.
2. **Design gate:** the coordinator records the handoff in the issue, canonical iteration
   document, or a dedicated `docs/iterations/` design document. The handoff must be marked
   `DESIGN_READY` or `DESIGN_BLOCKED`. Implementation cannot start without a recorded,
   approved `DESIGN_READY` handoff.
3. **Implementation phase:** invoke `implementation_worker` with `gpt-6-astra` and `medium`
   reasoning effort in a separate agent session. It implements only the approved handoff, adds
   or updates tests, runs the required gates, and records verification and remaining scope.
4. **Escalation:** return architectural ambiguity to `design_architect`. The implementation
   worker must not silently redesign the contract or switch to a higher reasoning effort.

The primary coordinator must not mix the phases or continue implementation in the high-effort
design session. Use one design agent followed by one implementation agent; parallel subagents are
not appropriate for this dependent workflow. The project default for unspecified subagents is
Astra at medium effort, while the custom role files pin the design role to high effort.

The bootstrap change that introduces this workflow establishes the policy. All subsequent
issue-backed work must follow it unless an explicit, documented one-off exception is approved in
the issue and pull request.

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
