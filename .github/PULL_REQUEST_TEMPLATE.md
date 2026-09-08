## Summary

-

## Tracking

- Parent iteration: Part of #
- Completed work item: Closes #
- Canonical iteration document: `docs/iterations/NNN-*.md`

## Design and model routing

- Design handoff: document or issue link, with recorded `DESIGN_READY`
- Approval: approver and recorded approval link
- Design role / model / effort: actual selection and rationale (AGENTS.md task matrix)
- Implementation role / model / effort: actual selection and rationale
- Review role / model / effort: actual selection, or not used
- Escalations: reason, findings, approval, and separate sequential session evidence, or none
- Bootstrap or one-off exception: recorded authorization, or none
- [ ] Approved design was recorded before any write-capable role started
- [ ] Implementation followed the approved scope
- [ ] Architectural ambiguity returned to `design_architect`; reviews did not authorize changes

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
