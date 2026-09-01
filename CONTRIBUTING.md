# Contributing

This repository delivers short, testable iterations for an educational financial decision-support
system. GitHub tracks coordination and progress; version-controlled Markdown retains product,
architecture, execution, and verification knowledge.

## Sources of truth

- `wishlist.md` retains raw user intent and is not silently normalized.
- `docs/product/vision.md` defines stable scope and non-goals.
- `docs/product/roadmap.md` defines directional sequencing.
- The highest-numbered file under `docs/iterations/` is the current delivery contract.
- `docs/architecture/system.md` describes the implemented system.
- Accepted ADRs preserve consequential decisions and are not rewritten.
- GitHub issues coordinate work; they do not replace these documents.

Every iteration parent issue must link its canonical iteration file. The issue may summarize the
goal and acceptance gate, but detailed scope and durable evidence belong in the repository. At
closure, link to the document at the merge commit so the accepted evidence has an immutable view.

## Issue hierarchy

Use one parent issue for an active iteration. Create sub-issues only for work that is independently
implementable, reviewable, or verifiable. Keep the normal hierarchy to two levels:

```text
Iteration parent
├── contract or design work item
├── implementation work item
├── presentation work item
├── evaluation work item
└── manual or live verification work item, when needed
```

Routine unit tests, formatting, and small file changes belong in the implementing pull request and
do not need their own issues. Use a verification sub-issue when acceptance depends on a manual UI
flow, credentials, paid provider request, external service, operational environment, or other
evidence that CI cannot produce.

Use GitHub's parent/sub-issue and blocked-by relationships instead of reproducing dependency graphs
in prose. Add every parent, sub-issue, and related pull request to the active iteration milestone.
Unscheduled work keeps the `[Roadmap]` prefix and receives an iteration number only when promoted.
Never renumber completed iterations.

## Definition of ready

An iteration is ready to start when:

- its number does not conflict with accepted history;
- its parent issue and canonical `docs/iterations/NNN-*.md` file link to each other;
- the goal, scope, non-goals, acceptance criteria, dependencies, and verification plan are explicit;
- consequential open design choices have an owner and require an ADR when appropriate;
- external credentials, cost, data, or human-approval requirements are identified; and
- independently closable work is represented by a small set of sub-issues.

## Pull requests

- Work from a `codex/<task-name>` branch unless a different branch is explicitly requested.
- Keep each pull request aligned with one independently verifiable issue outcome.
- Use `Closes #<child>` for the child issue completed by the pull request.
- Use `Part of #<parent>` while the iteration remains incomplete.
- Close the parent only from the final integration or completion pull request, after every
  acceptance criterion and required verification has passed.
- Update tests and relevant Markdown with every behavior change.
- Record new architectural decisions as ADRs; do not rewrite accepted history.

The standard local gates are:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build
docker compose config --quiet
git diff --check
```

## Verification evidence

Pull requests contain implementation-specific test results. The iteration document contains the
durable acceptance record. The parent issue receives a concise completion comment linking both.

Record:

- the tested commit or merge commit;
- commands and summarized results;
- CI run and pull-request links;
- UTC date or timestamp;
- redacted provider, model, environment, and method when relevant;
- expected and actual acceptance outcomes;
- manual steps or screenshots only when presentation behavior is part of acceptance; and
- unresolved limitations or follow-up issues.

Do not rely on temporary CI logs or artifacts as the only evidence. Do not paste huge logs, raw
provider responses, prompts containing retrieved source content, credentials, `.env` values,
private data, review tokens, or other secrets into public issues. Public issue attachments are
publicly accessible.

Suggested completion comment:

```markdown
## Verification complete

- Merge commit: `<sha>`
- Pull request: #NN
- Automated checks: `<summary>`
- Manual/live verification: `<redacted environment and result, or not required>`
- Durable evidence: `docs/iterations/NNN-*.md`
- Remaining limitations: `<none or linked follow-up issues>`
```

## Definition of done

Close an implementation or iteration issue as completed only when:

- the linked pull request is merged to `main`;
- required sub-issues are closed and blocking dependencies are resolved;
- acceptance criteria are checked against actual behavior;
- CI and the documented local gates pass;
- required manual or live verification succeeds;
- relevant product, architecture, ADR, iteration, and runbook documentation is current;
- durable verification evidence is recorded without secrets or private data; and
- remaining limitations are explicit and linked to follow-up work.

Use the `not planned` closure reason for intentionally declined or superseded work rather than
presenting it as completed.

## Financial and data safety

- Do not execute trades or imply guaranteed returns.
- Keep eligibility, constraints, and allocation decisions deterministic and evidence-based.
- Preserve provider, source URL, and observation timestamp for market-data results.
- Missing evidence remains unknown and never becomes a silent pass.
- Any future external financial write requires a separate human approval immediately before it.
- Never commit credentials, tokens, downloaded private data, or `.env` files.
