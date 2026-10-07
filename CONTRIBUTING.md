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

ADR 0026 replaces automatic repeated design resets with a finite ticket lifetime.
ADR 0033 sets `owner-led-v1` as the new-ticket policy. One approved owner keeps routine
implementation, self-review, verification and authorized same-scope repair together.
Consequential design and review retain independent sessions. An explicit standard
`continuation` can grant bounded repair and review after implementation or delivery,
while preserving consumed counts and historical bindings. A changed contract still
uses the bounded design path or separate scope. The legacy `timed-v1` rules remain
unchanged for their recorded prefixes.

ADR 0034 requires bounded coordinator arbitration before another dependent handoff
when a concern returns after a substantive response or a proposed requirement,
success condition, or remedy shifts beyond the frozen capsule. Record the existing
roles' concrete scenarios and evidence against frozen IDs in the
[arbitration template](docs/workflow/templates/coordinator-arbitration.md), then
classify each as a demonstrated defect, contract ambiguity, preference, or outside
scope. The coordinator makes one accountable decision and focused closure condition,
records disagreements and rationale, and applies the existing checked/reserved phase,
owner, independent review, finite count, and content gates. A demonstrated defect
requires repair and verification or an explicit stop; a failed check stays failed.
Agreement is not a gate, and arbitration supplies no automatic reset or allowance.
Finish the record before content-bound certification.

The six named roles are registered with relative `config_file` paths. ADR 0018's no-defaults,
no-project-model-override, and no-concurrency-scalar compatibility policy still applies.
`scripts/validate_codex_workflow.py` checks static contracts in CI; it cannot prove live-session
role, model, effort, or sandbox provenance.

For the Finite ticket lifetime, historical tickets retain their 120 active minutes
limit. New owner-led tickets retain elapsed audit seconds but use finite counted phase
reservations instead of time exhaustion. Explicit finite user extensions add phase
counts only. A delivered ticket needs a fresh finite continuation and new matching
verification, acceptance and independent review before redelivery on its original PR.
Publication checks read the actual saved delivered ledger before pushing; the ledger
and event file are reread immediately before atomic append replacement.

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

## Finite ticket lifetime (ADR 0026)

Every future agents-lab ticket has one durable ledger at
`docs/workflow/tickets/issue-N.json`, initialized before any phase. The frozen scope,
invariant IDs and acceptance IDs apply across agents, sessions, quota resets and design resets.
Freeze the complete capsule definitions, owner/model/effort, rationale/authorization,
non-goals, interfaces, explicit JSON/state impact, verification, docs, risks and triggers.
Design, challenge and approval bind the same immutable digest and current generation.
Classified write ownership and any concrete specialist escalation must be recorded;
reviews exclude every implementation, remediation and verification author.
Historical `timed-v1` tickets have a 120 active minutes budget across discovery,
design, challenge, implementation, verification and review. New `owner-led-v1`
tickets record elapsed seconds for audit, while finite phase counts govern dispatch.
Start reserves the counted slot;
crashed open phases consume through the current time. Explicit pause records elapsed
and resume continues the same reserved phase. No unrecorded time subtraction.

At most one initial review, one remediation, one final review and one design reset
per ticket lifetime. One implementation pass is the default. A reset consumes the
original budget and never clears counters. Consequential design requires a separate
independent challenge before coordinator approval; challenge is not code review.
Review findings identify a concrete failure scenario and a frozen invariant or AC;
scope expansion becomes separate work. Failed final review, unresolved challenge,
exhaustion or serious blockers means BLOCKED_FOR_DECISION, never delivery of defects.
Clean final review may deliver without another phase slot. A finite attempt is
promised, successful completion is not.

Before dispatch, run `uv run python scripts/ticket_workflow.py check --issue N --phase PHASE`;
then append the phase_start event before starting its agent. Before delivery run the
same check with `--phase delivery`. Append measured phase ends, acceptance evidence,
review outcomes and blocker resolutions. One writer uses atomic validated append.
Explicit finite user extensions append named authority and evidence; owner-led grants
add count deltas with zero seconds, while timed grants retain seconds-and-counts rules.
No automatic renewal. Historical timed splits require explicit user decision,
validated predecessor history, inherited counters and allocated remaining time;
sibling allocations total no more than the predecessor remainder. A split retires
its predecessor. New issue numbers cannot silently evade limits.

Recorded enforcement is not a runtime kill switch. The coordinator must truthfully
record evidence, check open phases periodically and interrupt active agents on
exhaustion. Static validation cannot authenticate approval or session provenance. Approval evidence
is single-use despite changed display names or surrounding/internal whitespace.
Review, verification and acceptance bind identical repository content. Delivered ledgers
authorize only their original PR identity and that content; reruns preserve the binding.
CI validates immutable merge-base history and current primary issue binding on PR
edits. Existing historical tickets are not retrospectively adopted. Issue70 remains
stopped pending a separate user decision; this workflow ticket changes no product code.
