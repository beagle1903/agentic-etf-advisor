## Summary

-

## Tracking

- Parent iteration: Part of #
- Completed work item: Closes #
- Canonical iteration document: `docs/iterations/NNN-*.md`

## Design capsule and model routing

- Classification: mechanical, ordinary, consequential, high-risk/disputed, or difficult
- Design handoff: document or issue link, with recorded `DESIGN_READY`
- Authorization: user authorization evidence
- Owner role / model / effort: actual selection and rationale
- Separate architect approval: approver and evidence for consequential work, or not required
- Independent review: recorded high-risk/disputed trigger, role/model/effort, and findings, or not used
- Escalations: concrete reason, approval, and fresh separate sequential session evidence, or none
- Bootstrap or one-off exception: recorded authorization, or none
- [ ] The complete design capsule was recorded before implementation edits
- [ ] Routine work used one owner session, or the reason for another session is recorded
- [ ] Consequential work had a separate `design_architect` handoff and coordinator approval
- [ ] Implementation followed the approved scope
- [ ] Self-review and focused tests were completed by the owner
- [ ] Architectural ambiguity returned to `design_architect`; reviewer findings did not authorize changes

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

Claim boundaries:

- Static workflow validation: pass/fail and command
- Live-session provenance: evidence or not verified
- Codex CLI compatibility: evidence or not verified
- Measured quota savings: evidence or not measured

## Documentation and decisions

- [ ] Product, architecture, iteration, runbook, and ADR files are updated where required
- [ ] No accepted ADR history was rewritten
- [ ] Remaining limitations and follow-up issues are linked

## Safety and data handling

- [ ] No credentials, `.env` values, private data, prompts, raw provider responses, or review tokens are committed or posted
- [ ] Market-data results retain source and observation timestamp metadata
- [ ] The change does not execute trades or imply guaranteed returns
- [ ] Any future external financial write remains behind separate immediate human approval
