# Local development runbook

## Bootstrap

```powershell
Copy-Item .env.example .env
uv sync
uv run pytest
```

Install the optional integrations when the next slice needs them:

```powershell
uv sync --extra checkpoint --extra dashboard --extra observability --extra providers --extra rag
```

## Quality checks

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Run the graph demo

```powershell
uv run etf-advisor demo
```

## Run durable local human review

Start PostgreSQL, install the two optional dashboard integrations, and launch Streamlit:

```powershell
docker compose up -d postgres
uv sync --extra dashboard --extra checkpoint
uv run etf-advisor dashboard
```

Select **Keep review in local PostgreSQL** when creating the draft. The resulting URL and displayed
version-4 UUID identify the exact saved graph thread. Keep that review token private to the local
development machine. Opening the URL in a new browser session or pasting the token into **Saved
review** restores the paused or completed state and revalidates its review contract.

At human review, **Approve** finalizes without mutation feedback. **Edit** always revises.
**Reject** requires an explicit **Revise** or **Close** disposition; close retains a bounded note
and does not accept mutation feedback. A revision selects one or more typed classes: profile,
evidence refresh, screening policy, construction policy, or explanation. The UI builds those typed
payloads, while the graph validates the complete merged input and chooses the earliest restart
stage. The construction editor intentionally preserves the existing source-category sleeve mapping.
Free-text notes are audit context only and never select routing or mutate financial inputs.

**Revision and operation history** shows only identities, digests, source-snapshot identity,
restart/invalidation classes, decisions, and operation status. It does not dump profile values,
artifact bodies, source text, prompts, credentials, connection details, raw provider output, or the
review token. User-authored notes render as plain text. **Refresh exact thread** reloads saved state
without invoking retrieval or a provider. If a submission outcome cannot be confirmed, all mutation
controls remain disabled until that refresh succeeds.

A current failed or ambiguous retrieval/provider attempt may expose **Retry exact operation**.
Retry is never automatic, targets only the latest attempt on the rendered revision, and may repeat
cost when an earlier call completed but its result was not durably observed. Successful, stale,
foreign, malformed, or already reviewed attempts are ineligible.

The token is not a login, the dashboard does not list other threads, and this slice is not a
multi-user review system. If PostgreSQL is unavailable while submitting a decision, restore the
same token and inspect its current state before retrying.

### Checkpoint lifetime and operator lifecycle API

New durable threads use `CHECKPOINT_RETENTION_DAYS` (integer 1–365, default 30). The effective
interval is saved per thread; changing configuration does not retroactively change existing
threads. Loading/rendering never renews expiry. At the exact expiry boundary, restoration/resume
is blocked. Legacy checkpoints without lifecycle metadata also fail closed and are not migrated.
The dashboard shows the exact durable thread's effective interval and expiry without renewing it.
Lifecycle selection is independent of graph restoration: expired, legacy, damaged, or missing exact
tokens can still receive sanitized inspection and deletion handling. It never enumerates other
tokens and does not expose preview/prune or run hidden cleanup.

The backend lifecycle API is available for explicit local operations after normal store setup:

```python
status = store.inspect(review_token)
preview = store.preview_expired()  # one cutoff, no writes
results = store.prune(preview)  # only unchanged candidates in that preview
result = store.delete(review_token, confirmed=True)  # separate explicit confirmation
```

Deletion permanently removes every namespace, checkpoint, blob, pending write, draft, decision,
receipt, lineage, and lifecycle record for that exact UUID-v4 token. It returns `deleted`,
`not_found`, or sanitized `failure`; no backup or recovery is promised. Prune additionally reports
`skipped` for changed candidates. Missing/malformed metadata is never automatically pruned but can
be deleted with the exact token and confirmation. There is no automatic background cleanup.

In the dashboard, permanent deletion requires re-entering the exact UUID-v4 token in a masked field
and selecting a separate confirmation. The action calls only the lifecycle store's atomic
whole-thread deletion; partial revision/event deletion is unavailable. For an in-memory review,
**Discard process-local state** clears the checkpoint and retained transient adapters after a
separate acknowledgement. Browser-session or process loss has the same no-recovery boundary.

Application code must use `with store.managed(token, create=True) as saver` for a new thread,
and `with store.managed(token) as saver` for existing state. Build the graph inside that context;
complete the invocation there. Do not retain its compiled graph for subsequent operations.
Process-local `DashboardRun` retains repr-hidden adapter dependencies and the candidate limit,
reinjecting them into each fresh managed graph. These fields stay outside checkpoint JSON, and
discard clears adapter references. Startup still closes the Neo4j resource after drafting;
retention alone does not make a closed live retriever reusable. Live resource ownership changes
and durable adapter reattachment are deferred; durable restore/approval remains unchanged.
The dashboard preflights the adapters required by the graph-validated revision plan before mutation.
Known-closed or unavailable external-stage adapters block the action. Approval, reject-close, and
durable policy-only profile revisions do not require them.
Each synchronous checkpoint commits separately while per-thread exclusion blocks prune/deletion.
To retry a failed/ambiguous operation, pass the existing typed `retry_request` to a graph compiled
inside managed access with the required replaceable adapters attached. Never retry implicitly.

Use `reconstruct_audit(state, token)` from `etf_advisor.audit` to validate and reconstruct retained
history without clocks, ID allocation, or external calls. The result contains private local
profile/evidence/audit data: do not log, commit, or publish it. For process-local sessions,
`run.discard()` invalidates the run and deletes its memory checkpoint; browser/process loss also
has no recovery promise. Tokens remain capability references rather than authentication.

Lifecycle verification uses deterministic store and connection doubles. This slice did not run
live PostgreSQL, provider, or market integrations. Live PostgreSQL checks require separate approval.

## Exercise hybrid retrieval

With Chroma and Neo4j healthy, index one shared source bundle and query it:

```powershell
uv sync --extra rag
uv run etf-advisor data-health --symbols SPY,QQQ
uv run etf-advisor ingest --symbols SPY,QQQ --with-graph
uv run etf-advisor hybrid-search "broad US equity exposure"
uv run etf-advisor demo --with-evidence --candidate-limit 5
```

`data-health` is read-only and prints each source URL, observation timestamp, age, and
freshness classification. It exits nonzero when the source request fails or any observation
falls outside `MARKET_DATA_MAX_AGE_HOURS`. Ingestion applies the same check before opening a
retrieval store.

Both writes are idempotent because they use the same stable source document IDs. If one
local service fails during ingestion, restore it and rerun the same command; the command
verifies that every requested ID exists in both stores before reporting success.

`demo --with-evidence` derives a deterministic query from its validated example profile,
attaches ranked source evidence and optional graph context to the review interrupt, and
recomputes freshness at retrieval time. Empty, malformed, non-ETF, non-US, stale,
future-dated, or unavailable evidence stops before review and exits nonzero. Ready candidates
require HTTP(S) attribution plus source-reported `quote_type=ETF` and `market=us_market`. The
evidence is research context, not an ETF recommendation or trade instruction.

To add an opt-in provider explanation, set either the Ollama or OpenRouter model credentials
from `.env.example`, install the provider extra, and run:

```powershell
uv sync --extra rag --extra providers
uv run etf-advisor demo --with-evidence --with-explanation --candidate-limit 5
```

`--with-explanation` requires `--with-evidence`. The workflow accepts only structured output
whose policy keys, source document IDs, and ETF subjects match the exact provider input. A
provider/schema/grounding failure or explicit prohibited financial claim stops before review
and exits nonzero.

Local Ollama uses provider-enforced JSON schema. Direct Ollama Cloud uses one ordinary generation
request with the required schema embedded in the prompt, then applies the exact Pydantic,
grounding, numeric-support, and financial-safety checks locally. OpenRouter uses strict function
calling. No provider path automatically retries with a second method.

When generation stops, inspect `explanation_errors` in the CLI output or dashboard. Provider
failures include a redacted `code`, `provider`, `model`, `method`, and optional `http_status`.
Credentials, prompts, source content, and raw responses are intentionally omitted. Common codes
are `authentication`, `rate_limit`, `unsupported_capability`, `invalid_response`, `unavailable`,
and `provider_error`. A new review draft creates a new provider request; restoring a stopped token
does not replay the provider call.

If the provider response parses but local safety or grounding validation rejects it, the error uses
one contract code: `prohibited_claim`, `unknown_policy_reference`,
`unknown_construction_reference`, `unknown_source_reference`, `subject_mismatch`,
`unsupported_numeric_claim`, or `contract_validation_error`. These categories are safe to copy
from the dashboard when troubleshooting. Stop repeated provider attempts after a recurring code;
the rejected generated text is intentionally unavailable and restoring the saved review does not
regenerate it.

## Run the offline retrieval baseline

The packaged curated dataset needs no services, credentials, model downloads, or network:

```powershell
uv run etf-advisor evaluate-retrieval
```

To score a reviewed replacement dataset with the same schema:

```powershell
uv run etf-advisor evaluate-retrieval --dataset .\path\to\retrieval-evaluation.json
```

The report is deterministic for a given dataset version and limit. Treat zero ranking delta
as zero measured ranking lift even when graph-context metrics improve.

## Start infrastructure

```powershell
docker compose up -d chroma neo4j postgres
docker compose ps
```

Neo4j Bolt is exposed on host port `17687` because the standard `7687` port is in a
Windows-reserved range on the original development machine.

Stop containers while preserving named-volume data:

```powershell
docker compose stop
```

Do not use `docker compose down --volumes` unless deletion of local database data is
explicitly intended.

## Secrets

Copy `.env.example` to `.env` and place credentials only in `.env` or a secret manager.
The `.env` file is ignored by Git. Never paste real keys into documentation, tests, Docker
images, or workflow files.
