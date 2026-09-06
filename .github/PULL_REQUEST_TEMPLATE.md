## Summary

-

## Tracking

- Parent iteration: Part of #
- Completed work item: Closes #
- Canonical iteration document: `docs/iterations/NNN-*.md`

## Design and model routing

- Design handoff: `docs/iterations/<design-document>.md` or issue comment/link
- Design agent: `design_architect` (`gpt-6-astra`, `high`)
- Implementation agent: `implementation_worker` (`gpt-6-astra`, `medium`)
- [ ] Design was marked `DESIGN_READY` before implementation began
- [ ] Implementation followed the approved design without an undocumented contract change
- [ ] Any architectural escalation or one-off workflow exception is recorded

## Acceptance criteria covered

- [ ]

## Verification

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run mypy`
- [ ] `uv run pytest`
- [ ] `uv build`
- [ ] `docker compose config --quiet`
- [ ] `git diff --check`
- [ ] Required manual or live verification completed, or not required

Evidence summary:

-

## Documentation and decisions

- [ ] Product, architecture, iteration, runbook, and ADR files are updated where required
- [ ] No accepted ADR history was rewritten
- [ ] Remaining limitations and follow-up issues are linked

## Safety and data handling

- [ ] No credentials, `.env` values, private data, prompts, raw provider responses, or review tokens are committed or posted
- [ ] Market-data results retain source and observation timestamp metadata
- [ ] The change does not execute trades or imply guaranteed returns
- [ ] Any future external financial write remains behind separate immediate human approval
