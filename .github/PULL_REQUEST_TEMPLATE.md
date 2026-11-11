## Summary

-

## Tracking

- Issue: Closes #
- Iteration: Part of #
- Durable evidence: `docs/iterations/NNN-*.md`

## Agreement and review

- Authorized scope and non-goals:
- Acceptance criteria and observed results:
- Accountable owner / role / model / effort and rationale:
- Consequential design advice and coordinator approval, if applicable:
- Independent review findings and resolution, if applicable:
- Material limitations or follow-up:

## Verification

- [ ] Focused tests and owner self-review
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run mypy`
- [ ] `uv run pytest`
- [ ] `uv build`
- [ ] `docker compose config --quiet`
- [ ] `git diff --check`
- [ ] Required manual or live verification, if applicable

Commands, results and tested commit:

-

## Safety and data handling

- [ ] No credentials, private data or `.env` values committed
- [ ] No trade execution or guaranteed-return claim introduced
- [ ] Market-data changes retain source and observation time
- [ ] External financial writes have separate human approval, if applicable
