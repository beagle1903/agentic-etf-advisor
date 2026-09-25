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

## Codex ticket routing

Use the authoritative classification contract in `AGENTS.md`, ADR 0022, and the current GPT-6
model assignments in [ADR 0025](docs/architecture/decisions/0025-gpt6-codex-role-routing.md).
Record the work's classification, actual role/model/effort, rationale, authorization, and
escalation triggers.
Mechanical work uses `bounded_worker`; ordinary work within established contracts uses
`implementation_worker`. In one authorized session, that owner may record the complete
`DESIGN_READY` capsule before implementation edits, implement, add focused tests, self-review,
run verification gates, and document limitations. `planning_analyst` remains available for
explicit discovery or planning and is not a routine prerequisite.

Consequential financial, safety, authentication, persistence/replay, security, or architecture
contracts require a separate `design_architect` handoff and coordinator approval before any
write-capable role starts. Review findings cannot authorize implementation or contract changes.
Add `code_reviewer` only for high-risk or disputed output. Use `implementation_specialist` only
for concrete complexity, unresolved failure, concurrency, migration risk, or consequential
ambiguity; multiple files, integration tests, or unfamiliarity alone are insufficient. Record
the evidence and start a fresh separate sequential session for any escalation or role/effort
change. The PR links the capsule, approval, actual routing evidence, and any exception.

Two consecutive implementation-review cycles that fail for related reasons are evidence that the
approved design or acceptance matrix is incomplete. Stop remediation at that point and return to a
fresh read-only `design_architect` session. Implementation resumes only after the coordinator has
recorded and approved a revised `DESIGN_READY` capsule. An `implementation_specialist` does not
replace this design reset, and reviewer-implementation ping-pong must not continue indefinitely.

The six named roles are registered with relative `config_file` paths. ADR 0018's no-defaults,
no-project-model-override, and no-concurrency-scalar compatibility policy still applies.
`scripts/validate_codex_workflow.py` checks static contracts in CI; it cannot prove live-session
role, model, effort, or sandbox provenance.

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

## Opt-in real-store contract coverage

Default tests use deterministic in-memory or driver doubles and never start local services. To
exercise the disposable PostgreSQL, Neo4j, and Chroma contract suite, install the checkpoint and
RAG extras, ensure Docker Desktop is running, then run:

```powershell
$env:RUN_REAL_STORE_TESTS = "1"
uv run pytest tests/test_real_store_integration.py
Remove-Item Env:RUN_REAL_STORE_TESTS
```

The fixture assigns loopback ports, starts a uniquely named Compose project from
`compose.integration.yaml`, and always runs `docker compose down --volumes` for that project. It
uses no production Compose volumes, credentials, providers, market-data calls, or private data.

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
