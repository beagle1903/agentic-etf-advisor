# Agent operating instructions

## Read order

Before changing the project, read these files in order:

1. `wishlist.md` for raw user intent.
2. `docs/product/vision.md` for stable scope and non-goals.
3. `docs/architecture/system.md` for the current system shape.
4. Relevant records under `docs/architecture/decisions/`.
5. The active file under `docs/iterations/`.

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
