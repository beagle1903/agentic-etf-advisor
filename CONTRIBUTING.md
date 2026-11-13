# Contributing

This repository delivers short, testable iterations for an educational financial decision-support
system. GitHub tracks coordination and progress; version-controlled Markdown retains product,
architecture, execution, and verification knowledge.

## Sources of truth

- `docs/product/vision.md` defines stable scope and non-goals.
- `docs/product/roadmap.md` defines directional sequencing.
- The highest-numbered file under `docs/iterations/` is the current delivery contract.
- `docs/architecture/system.md` describes the implemented system.
- Accepted ADRs preserve consequential decisions and are not rewritten.
- GitHub issues coordinate work; they do not replace these documents.

## Codex working agreement

Record the issue's scope, non-goals, acceptance criteria, accountable owner, authorization and verification. Use the three model presets and separate task assignments in `AGENTS.md`; a preset does not grant access or responsibility. One owner completes ordinary implementation, focused tests, self-review and verification. Consequential financial, identity, security, persistence/replay or architecture contracts require separate `design_architect` advice and coordinator approval before implementation. Add independent `code_reviewer` review for consequential, high-risk or disputed output. Keep dependent handoffs sequential and record concrete escalation reasons. No-write assignments follow instruction-only restrictions even when inherited access is full; do not describe that as sandbox enforcement.

The [current agreement](docs/architecture/decisions/0049-prospective-working-agreement.md) does not require a ticket ledger, phase reservation, elapsed-time budget, finite-attempt grant, content certificate or delivery binding for prospective work. Historical records remain evidence of their own outcomes. `scripts/validate_codex_workflow.py` checks preset configuration and, with optional `--declaration PATH`, a prospective JSON dispatch record's internal consistency. It cannot prove live identity, permissions or authority. No declaration store or mandatory process engine is added. An old ticket's exhausted attempts do not block normal use of a merged app or permit an unsupported claim that the old acceptance passed.
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

## Early decomposition decision

Consider decomposition before starting a broad implementation and again if evidence shows a
contract question repeatedly reopening, acceptance expanding during repair, several independently
useful outcomes, or components needing distinct review or evidence. Record the concrete scenario
and the original acceptance condition it affects. File count, unfamiliarity and a routine defect
are not triggers by themselves. The coordinator makes one accountable choice with an observable
closure condition: keep a bounded same-scope repair with its owner, propose independently
deliverable sub-issues, or explicitly stop the affected delivery. Use the
[coordinator record](docs/workflow/templates/coordinator-arbitration.md) when a concern recurs or
scope drifts; it is not a planning prerequisite for routine work. A material change of intended
scope returns to the user under [ADR 0049](docs/architecture/decisions/0049-prospective-working-agreement.md).

For each proposed child, state its independently useful outcome, acceptance criteria, non-goals,
affected interfaces and state, dependencies, owner and verification. Map every original parent
requirement to a child, an explicitly authorized deferral, or an unresolved blocker. Use GitHub's
native parent/sub-issue and blocked-by links, and give each deliverable its own reviewable PR.
Execute proposed children one at a time. Merging every child is insufficient to complete the
parent: check the original acceptance criteria and blockers separately. A proposal does not
replace an owner or bypass applicable design, review or PR checks. Keep an inseparable
financial, identity, security, persistence/replay or architecture invariant together, with its
separate design advice and coordinator approval. A demonstrated current correctness defect still
blocks the affected delivery when enhancements are assigned elsewhere.

| Scenario | Accountable disposition |
| --- | --- |
| Broad unstarted tracking parent with independently useful outcomes | Propose native sub-issues and dependencies before implementation; map the parent's complete acceptance. |
| Started historical ledger ticket with remaining allowances | If a split is proposed for that historical ticket, preserve its recorded outcomes and use only its applicable authorized disposition; GitHub hierarchy alone never grants or resets an attempt. |
| Historical exhausted ticket or failed final review | Keep the recorded failure or stop visible. A new issue may address a separately authorized outcome, but its number does not make the original acceptance pass. |
| Single-scope defect found during implementation or review | Keep narrow repair and verification with the owner; splitting is unnecessary. |
| Inseparable consequential contract | Keep the invariant in one deliverable and obtain separate design advice and approval before changing it; partial children cannot make it safe. |

Prospective work follows ADR 0049 and needs no ledger, reservation, finite allowance or content
certificate. Historical [ADR 0034](docs/architecture/decisions/0034-bounded-coordinator-arbitration.md)
and [ADR 0036](docs/architecture/decisions/0036-owner-led-conserved-split-lineage.md) explain
their recorded tickets; do not rewrite their events, failed outcomes or PR bindings. A new issue
number is a new scope and evidence record, not proof of the old ticket's success.

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

This suite is a required local/release gate before merging changes to research snapshot
serialization (including numeric encoding/proofs), Chroma research metadata or stage/readback,
hybrid retrieval or candidate evidence, deterministic screening contracts, or snapshot activation,
manifest/projection verification and retry. Changes to the fixtures or integration harness that
prove these paths must also run it. Ordinary offline work retains the service-free default.

Current CI (`.github/workflows/ci.yml`) runs the locked service-free suite and static checks; it
does not provision the optional RAG/checkpoint extras or disposable Docker stores. Until a
separately approved service-backed CI change, the required local/release run supplies that proof.
A green offline CI run alone does not satisfy this gate. Use the full real-store file, with no
failures, errors or skips; an unavailable service or missing extra is incomplete acceptance.

Before merge, record the tested commit/content identity, UTC time, redacted OS/Python/dependency
and Docker/Compose environment, exact opt-in command, collected/passed/failed/error/skipped counts,
critical-path outcomes and confirmation that the generated project was removed after teardown.
Link the durable iteration evidence, PR and CI run. Evidence must apply to the final reviewed
content; rerun after relevant changes. See the [runbook](docs/runbooks/local-development.md#required-real-store-delivery-gate)
for commands and the [Issue71 evidence map](docs/iterations/017-issue-71-real-store-contract.md).

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
