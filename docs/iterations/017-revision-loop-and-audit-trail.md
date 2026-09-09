# Iteration 017: Revision loop and audit trail

- Status: Active
- Created: 2026-09-04
- Tracking issue: https://github.com/beagle1903/agentic-etf-advisor/issues/22

## Goal

Turn human edit and reject feedback into controlled, auditable revisions that rerun only the
earliest affected workflow stage, reuse completed side effects safely, and give the local user an
explicit lifecycle for durable checkpoints.

## Scope

- Typed review decisions whose feedback class and structured payload determine the rerun boundary.
- Deterministic revision planning across profile validation, policy calculation, retrieval,
  screening, portfolio construction, explanation, and human review.
- Downstream invalidation that prevents a new revision from retaining stale drafts or decisions.
- Replay-safe receipts for retrieval and provider side effects, with injected clock values captured
  once and retained in the applicable revision or operation record.
- Auditable profile versions, research-snapshot identities, evidence bundles, drafts, review
  decisions, operation attempts, and parent/child revision lineage.
- A replaceable local checkpoint lifecycle with explicit expiry, preview, prune, and exact-thread
  deletion behavior.
- Dashboard controls for typed revision feedback, reject disposition, lineage inspection, expiry,
  and deletion without duplicating workflow policy.

## Non-goals

- Authentication, authorization, pending-review discovery, collaboration, or concurrent editing.
- Brokerage connectivity, trade execution, email, file publishing, or any external financial write.
- Free-form model classification of review feedback or model authority over profile changes,
  screening rules, portfolio constraints, rerun routing, or deletion.
- Automatic refresh, retry, or fallback after an ambiguous side-effect attempt.
- Editing accepted ADR history, individual audit events, or one revision out of a retained lineage.
- Production backup, legal hold, recovery, tamper-proof external audit storage, or data residency.
- Changing the accepted eligibility, allocation, safety, grounding, or recommendation boundaries.

## Acceptance criteria

- Approve, edit, reject-and-revise, and reject-and-close have explicit typed and tested outcomes.
- Every feedback class maps to one restart stage and one downstream invalidation set; mixed feedback
  selects the earliest affected stage in a fixed order.
- Free text is retained as bounded audit context but cannot choose a rerun boundary or mutate
  financial state without the corresponding validated typed payload.
- Pure stages recompute deterministically. A completed retrieval or provider operation is reused
  only when its revision, stage, attempt, canonical input digest, and validated output all match.
- A missing, malformed, contradictory, stale, tampered, or ambiguous operation receipt stops before
  adapter invocation. A retry requires an explicit human action and a new attempt identity.
- Every retained revision links its profile version and outcome. A non-root revision also links the
  parent revision and the parent decision that triggered it. Evidence, draft, operation-receipt,
  and review-decision references are required only when their stages were enabled and reached or
  the decision was actually submitted.
- Local durable checkpoints expire 30 days after the last meaningful write unless configured
  otherwise. Read-only restore does not extend retention.
- Expiry cleanup is explicit, previewable, and scoped to expired threads. Exact-thread deletion
  removes the complete checkpoint and audit lineage atomically or fails closed.
- In-memory review state is discarded on process/session loss or an explicit discard action.
- The dashboard displays revision and lifecycle status without treating the opaque token as user
  authentication and without exposing credentials, prompts, source content, raw provider output,
  or review tokens in logs.
- Graph state remains JSON-serializable; provider, retrieval, clock, checkpoint, and market-data
  integrations remain replaceable; every future external financial write still requires a
  separate approval immediately before execution.
- Focused workflow, store-contract, restore, tamper, replay, retention, deletion, and Streamlit
  tests pass together with Ruff, formatting, strict mypy, the full offline test suite, packaging,
  Docker Compose validation, and diff checks.

## Planned work items

- [x] Define revision planning, audit lineage, and checkpoint lifecycle contracts in ADRs 0015 and
  0016 (#39).
- [x] Implement deterministic revision routing and replay guards (#40).
- [ ] Implement audit lineage and the local checkpoint lifecycle (#41).
- [ ] Present revisions, rerun controls, and checkpoint deletion in the dashboard (#42).
- [ ] Run end-to-end revision-loop and audit-trail acceptance verification (#43).

The GitHub tracking issue owns progress, parent/sub-issue relationships, blocked-by relationships,
pull requests, and closure. This file is the canonical execution contract and will retain final
acceptance evidence.

## Review-decision contract

The review boundary accepts one JSON-safe decision. `approve` is terminal. `edit` always requests a
new revision. `reject` requires the reviewer to choose either `revise`, which rejects the current
draft and creates a child revision, or `close`, which ends the lineage with a rejected outcome.

Each non-approval decision contains a stable decision ID, the reviewed revision ID, action,
disposition, bounded reviewer note, one or more typed feedback items when revision is requested,
and one injected UTC submission time. A free-text note is explanatory evidence only. It cannot be
parsed by a model or heuristic to infer a financial patch, feedback class, or restart stage.

A decision that creates a child revision remains the review decision of its reviewed parent. The
child stores that ID separately as `triggering_decision_id`. Its own `review_decision_id` remains
absent while the child is awaiting review and is populated only when that child is reviewed.

### Feedback classes and restart boundaries

| Feedback class | Required typed payload | Restart stage | Invalidated state |
| --- | --- | --- | --- |
| `profile` | Validated `InvestorProfile` patch | `validate_profile` | Policy, evidence, screening, construction, explanation, review, and final state |
| `evidence` | Explicit refresh request and bounded retrieval options | `retrieve_candidate_evidence` | Evidence, screening, construction, explanation, review, and final state |
| `screening_policy` | Validated screening-policy patch | `screen_candidates` | Screening, construction, explanation, review, and final state |
| `construction_policy` | Validated construction-policy patch | `construct_portfolio` | Construction, explanation, review, and final state |
| `explanation` | Bounded explanation instruction with no financial mutation | `draft_explanation` | Explanation, review, and final state |
| `close` | Rejection reason; no mutation payload | none | No rerun; terminal rejected outcome |

When a decision contains multiple feedback items, the planner chooses the earliest stage in this
fixed order:

```text
validate_profile
retrieve_candidate_evidence
screen_candidates
construct_portfolio
draft_explanation
human_review
```

The planner validates every item before creating a revision. One malformed, contradictory, or
unsupported item blocks the entire decision; it never applies a partial patch. The new revision
records the complete plan and clears every artifact at or after its restart stage before routing.
Unchanged upstream artifacts remain referenced by immutable ID and digest rather than copied and
silently relabeled.

Policy calculation remains a pure consequence of the validated profile, so it has no separate
feedback class. A requested allocation-target change must be expressed through a valid profile
change. Screening and construction policy edits remain explicit reviewed research-control changes,
not personalized suitability decisions.

## Revision and audit contract

One durable thread contains an ordered lineage. Each revision record includes:

- `revision_id`, sequence number, status, created time, and optional completed time;
- for a non-root revision, `parent_revision_id` and `triggering_decision_id`; both are absent on the
  root revision;
- `profile_version_id` plus the canonical profile digest;
- the restart stage, ordered invalidation set, typed feedback classes, and planning digest;
- source research `snapshot_version` and `snapshot_digest`, plus a separate evidence-bundle ID and
  digest, only when retrieval was enabled and produced query-specific candidate evidence;
- IDs and canonical digests only for policy, screening, construction, and explanation artifacts
  whose stages were enabled and reached in that revision;
- an optional `review_decision_id`; once submitted, the linked decision carries its action,
  disposition, bounded note, typed payload digest, and submission time;
- operation receipts only for side-effect stages attempted in that revision; and
- the current awaiting-review, approved, rejected, or blocked outcome.

Absence is therefore stage-aware, not represented by invented placeholder identities. The
policy-only default remains a valid auditable revision with a profile version and policy draft but
without evidence, screening, construction, explanation, or side-effect-operation references.

Identifiers are opaque and unique within their record type. Digests use canonical JSON with stable
key ordering and exclude secrets, raw provider output, prompts, and transient connection data.
Digests are integrity checks, not signatures or proof against a database administrator. The audit
trail is tamper-evident while retained but is intentionally removed by an authorized whole-thread
deletion.

Every ready evidence bundle must carry one research snapshot version and digest. Every candidate
must agree with that identity. Legacy or test evidence without a published research snapshot uses
an explicit local synthetic identity; missing or mixed identity never reaches review.

## Side-effect replay contract

Retrieval and explanation attempts are represented by JSON-safe operation receipts containing the
thread, revision, stage, attempt number, operation ID, canonical input digest, status, optional
validated output ID and digest, and injected start/completion times.

- A pure stage may be recomputed whenever its contracted inputs are available.
- A `succeeded` side-effect receipt may be reused without an adapter call only when the exact input
  digest matches, the referenced output is present, and local contract validation reproduces the
  output digest.
- A `failed` receipt remains auditable. The workflow does not retry automatically; an explicit
  retry creates the next attempt number and operation ID.
- A `started` receipt without a durable success/failure result is ambiguous after restoration. The
  workflow fails closed before adapter invocation and requires an explicit retry with a new
  attempt. It never guesses whether the earlier external call completed.
- A missing, duplicated, out-of-order, cross-revision, or digest-mismatched receipt is a contract
  error and cannot be repaired by UI code or a model.

No current stage writes to an external financial system. A future broker, email, publication, or
other external write must remain outside this generic revision replay path and receive its own
separate approval immediately before execution, as required by ADR 0002.

## Local checkpoint lifecycle

The in-memory store lasts only for the process/browser session and supports an explicit discard.
There is no recovery promise after session or process loss.

The local PostgreSQL store assigns `last_activity_at` and `expires_at` with one injected UTC clock.
The default retention is 30 days after the last meaningful write: initial creation, review
decision, revision creation, explicit retry, or terminal transition. Read-only load, preview, or
render does not extend expiry. A bounded local configuration may change the interval, and the
dashboard must display the effective expiry.

Expiry does not trigger hidden background work. An explicit prune operation first offers a
non-mutating preview and then deletes only threads whose persisted expiry is at or before the same
captured check time. The dashboard does not enumerate other review tokens; administrative discovery
remains deferred to Iteration 018.

Explicit deletion requires the exact version-4 review token and a separate confirmation value. It
deletes every checkpoint, write record, revision, decision, receipt, draft, and lifecycle record
for that thread in one store operation. Partial revision or event deletion is unsupported because
it would leave misleading lineage. The operation returns only `deleted`, `not_found`, or a
sanitized failure. Deletion is permanent in the local prototype; no audit tombstone, archive, or
backup is promised outside the checkpoint store.

## Verification plan

The implementation slices must add deterministic coverage for:

- every feedback class, reject disposition, mixed-feedback precedence, and invalid payload;
- exact restart nodes, adapter call counts, downstream clearing, and unchanged upstream reuse;
- successful output reuse, explicit retry, ambiguous attempts, digest mismatch, and restored state;
- profile, snapshot, evidence, draft, decision, receipt, and lineage JSON round trips and tampering;
- 30-day boundaries, read-only restore, retention refresh after meaningful writes, preview, prune,
  exact-thread deletion, not-found behavior, atomic failure, and in-memory discard;
- dashboard feedback controls, lineage rendering, expiry, deletion confirmation, invalid restored
  state, and the existing educational and authentication boundaries.

Final acceptance will record the tested merge commit, UTC timestamp, redacted environment,
commands and results, pull-request and CI links, representative outcomes, and remaining
limitations. Live market data, provider calls, credentials, and external financial writes are not
required for this iteration's deterministic acceptance unless separately approved.

## Current slice

Issue #39 closed through PR #44, merged into the verified default branch `main` at
`a876384a05475550689e01ffd2c5bdc3484fdac0`. Issue #40 implements the typed planner, graph revision
routes, minimal retained lineage required for replay checks, and retrieval/provider operation
receipts. Lifecycle work (#41), interactive revision controls (#42), and iteration-wide acceptance
(#43) remain separate.

### Issue #40 slice evidence (2026-09-05 UTC)

- Branch: `codex/iteration-017-revision-routing`, based on the PR #44 merge above.
- Environment: local Windows, Python 3.13, locked dependencies, in-memory checkpointers and injected
  retrieval/provider/clock fakes. Dashboard and PostgreSQL checkpoint extras were installed;
  automated persistence-failure tests use replaceable in-memory saver implementations.
- Typed approve, edit, reject-and-revise, and reject-and-close outcomes pass. Each feedback class,
  mixed-feedback precedence, complete-patch rejection, exact streamed restart nodes, downstream
  clearing, profile/artifact identity reuse, and parent/child decision separation are covered.
- Replay tests cover successful reuse with zero additional calls, explicit second attempts after
  failures and ambiguous interruptions, checkpoint commit failures before adapter execution,
  asynchronous durability override rejection, missing/duplicate/out-of-order/cross-thread or
  cross-revision receipts, input/output digest mismatch, local output safety validation, malformed
  responses, and restored checkpoint/lineage tampering.
- Policy-only revisions retain only real profile/policy identities. Evidence carries one validated
  source snapshot identity or an explicit local synthetic identity. JSON round trips and the
  immutable upstream references are verified.
- `uv run pytest`: **356 passed**, including the installed Streamlit tests. One initial cold-start
  Streamlit timeout did not recur in the complete successful runs.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` (43 source files), `uv build`,
  `docker compose config --quiet`, and `git diff --check`: passed.
- No live market/provider calls, credentials, trades, external financial writes, retention, expiry,
  prune, or deletion were needed or introduced.

### Calling the revision boundary

Submit a `ReviewDecision` JSON payload through the current `Command(resume=...)`. Required identity
fields are `decision_id`, `revision_id`, and aware UTC `submitted_at`; `action` is `approve`, `edit`,
or `reject`. An edit uses `disposition="revise"`, a nonempty `note`, and a `feedback` list such as
`[{"kind": "profile", "patch": {"initial_investment_usd": 60000}}]`. Reject requires an explicit
`revise` or `close` disposition. Close has no mutation feedback. Notes are bounded audit context.

For a failed or ambiguous operation, invoke the same thread with
`{"retry_request": {"action": "retry", "revision_id": "<current revision>", "operation_id": "<last attempt>"}}`.
A retry cannot replay a successful attempt or repair malformed/mismatched receipts. Recompile with
the required adapters before retrying external stages. Restoration and approval themselves do not
call those adapters. Durability must remain synchronous so started receipts are committed before
execution; the compiled graph defaults to this mode and rejects unsafe overrides.

The existing Streamlit form still lacks the typed feedback/reject-disposition/retry controls owned
by #42. Its adapter accepts the typed values, and its approval path remains compatible. Legacy
free-text edit/reject responses fail closed. Pre-revision saved checkpoints are not silently
migrated, and supplying a new profile on an existing thread is rejected rather than resetting its
lineage. A new unrelated run needs a new thread. The local audit digest detects inconsistency; it
is not a signature or protection against a database administrator.


### PR #45 review follow-up: injectable audit identifiers

The review identified direct `uuid4()` calls inside revision orchestration. `build_graph` now
accepts an `IdentifierFactory` and passes it to `RevisionRuntime`, which uses it for all revision,
profile/artifact, and operation IDs. UUID generation remains the default adapter. Injected artifact
ID collisions stop before overwriting a retained artifact.

Four regressions verify identical audit state across root/retry/child flows with fixed clock and
identifier sequences, reproduction of a failed prepare transition from its prior state and factory
cursor, zero identifier allocation during successful receipt reuse/approval, and collision handling.
This does not bypass ambiguous-operation guards or promise deterministic IDs from the default random
factory after process loss. Full suite: **360 passed**. Ruff, formatting, strict mypy (44 source
files), packaging, Docker Compose validation, and diff checks passed.

### Issue #41 implementation handoff and evidence

The coordinator-approved `DESIGN_READY` handoff is recorded at
https://github.com/beagle1903/agentic-etf-advisor/issues/41#issuecomment-5573395329.
This implementation is limited to audit reconstruction and managed checkpoint lifecycle; Issue
#42 UI controls/rendering and Issue #43 acceptance remain separate.

`reconstruct_audit` validates retained identities/digests and evidence snapshot consistency before
returning detached JSON history. Managed stores enforce per-thread exclusion, atomic independent
checkpoint/lifecycle commits, persisted bounded retention, meaningful-event deduplication,
expiry/legacy fail-closed access, exact preview/prune, complete confirmed deletion, and memory
discard. ADR 0019 records transaction and operational metadata choices without changing accepted
ADR history. The architecture and local runbook document usage and limitations.

Local verification on 2026-09-08 passed: **171 focused tests** covering lifecycle, PostgreSQL
connection/store doubles, dashboard regressions, revision replay, and identifiers; **456 tests** in
the full offline suite; the Codex workflow validator; Ruff lint and format check; strict mypy
(46 source files); `uv build`; `docker compose config --quiet`; and `git diff --check`. One earlier
focused run hit the existing three-second Streamlit cold-start timeout; that same focused set and
the full suite subsequently passed without a code change for the timeout.

All lifecycle/store verification uses deterministic memory/connection doubles; live PostgreSQL,
providers, market data, trades, and external financial writes were not invoked. Live PostgreSQL
transaction and advisory-lock behavior remains the material unverified integration risk and needs
separate approval. Issue #42 still owns UI controls/rendering and Issue #43 owns iteration-wide
acceptance. Coordinator review passed; delivery evidence is recorded in the pull request.

### PR #55 review remediation

The coordinator-approved `DESIGN_READY` handoff is recorded at
https://github.com/beagle1903/agentic-etf-advisor/pull/55#issuecomment-5588465386,
addressing https://github.com/beagle1903/agentic-etf-advisor/pull/55#discussion_r3955098338.
Process-local runs retain repr-hidden transient retriever/generator dependencies and candidate
limit, reinject them into fresh managed graphs, and clear adapter references on discard.
Checkpoint JSON, lifecycle exclusion, replay guards, and durable restore behavior are unchanged.
Real-graph regressions use deterministic fake adapters for explanation-only and evidence-refresh
revisions, upstream identities, lineage/receipts, fresh saver handles, discard/deletion safety,
and durable dependency omission. Startup still closes Neo4j after drafting: retaining a retriever
does not repair its closed live resources. Resource ownership redesign, durable adapter
reattachment, Issue #42 controls/rendering, and live-service verification remain outside scope.

Local remediation verification on 2026-09-08: five new real-graph regressions passed;
the focused dashboard, lifecycle, PostgreSQL-double, revision, and identifier suites passed
**176 tests**; `uv run pytest` passed **461 tests**. The Codex workflow validator, Ruff lint,
format check (119 files), strict mypy (46 source files), `uv build`,
`docker compose config --quiet`, and `git diff --check` passed. An initial focused command named
a nonexistent `tests/test_checkpoint.py` and collected no tests; the corrected suites above passed.
No live services or external financial writes were used. Coordinator review and the complete
remediation gate set passed before delivery to PR #55.

### Issue #48 Yahoo exposure completeness hardening

The coordinator-approved `DESIGN_READY` handoff is recorded at
https://github.com/beagle1903/agentic-etf-advisor/issues/48#issuecomment-5601233304.
The design was produced read-only by `design_architect` with GPT-6 Astra/high and approved for a
fresh sequential `implementation_specialist` session with GPT-5.6 Sol/high. The implementation is
limited to atomic Yahoo holdings and sector parsing plus fixture-only adapter-to-workflow
regressions; Issue #47 field freshness, policy thresholds, graph schemas, provider support, and
repair of existing snapshots remain separate.

Malformed returned collections now make the complete affected field `source_error` without
retaining partial rows. A holdings error also makes derived top-ten concentration unavailable.
Every returned row is validated before concentration is calculated, complete collection totals
above 100 percentage points fail closed, and concentration is not clamped. Valid short holdings
lists, sparse sector maps, explicit zeros, fractions, percentage points, numeric strings, and
provider holding order remain supported.

PR #57 review found that converting exposure strings to binary floats before unit classification,
range checks, and aggregation could erase a just-over-boundary value. Exposure parsing now retains
exact decimal weights through those decisions and top-ten derivation, rejects Python and NumPy
boolean scalars, and converts accepted values without understating them in the existing float
model. Adapter-to-source-document-to-evidence-to-screening coverage proves that a holding reported
as `60.000000000000001` cannot pass the unchanged 60% concentration limit. Boundary regressions
also cover just-over-one unit classification and individual and aggregate just-over-100 rejection.

Local verification on 2026-09-09 uses only fixed clocks, deterministic identifiers, in-memory
checkpointers, fake drivers, and provider fixtures. The focused Yahoo, snapshot, screening, Neo4j,
construction, and workflow suite passed **123 tests**. The complete offline suite passed **649
tests**. `uv sync --all-extras --frozen`, the Codex workflow validator, Ruff format and lint, strict
mypy (46 source files), retrieval evaluation, explanation evaluation, `uv build`,
`docker compose config --quiet`, and `git diff --check` all passed. Retrieval retained perfect
source attribution and exact graph-sector constraint matching without changing semantic ranking;
all eight explanation/safety decisions matched their expected fail-closed result.

Residual limitations remain explicit: Yahoo's ambiguous numeric unit convention is unchanged;
the adapter cannot detect rows omitted upstream; previously published lossy snapshots are not
repaired automatically; and no live Yahoo, database, model, trade, or external financial-write
operation is part of this slice.
