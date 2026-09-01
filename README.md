# Agentic ETF Advisor

An educational, source-grounded US ETF portfolio decision-support project built with
LangGraph. The project is designed as a sequence of small, testable vertical slices.

The implemented slices validate an investor profile with human review, calculate an
illustrative policy split, health-check and ingest attributable ETF snapshots, join
Chroma-ranked documents to source-linked Neo4j context, compare the semantic-only and
graph-enriched paths on a deterministic offline evaluation set, and optionally attach a
freshness-checked source-evidence bundle and grounded provider explanation to the review
interrupt. A versioned six-ETF research universe now retains field-level provenance and explicit
missingness and activates one verified Chroma/Neo4j snapshot for hybrid retrieval. Measured
source-linked sector relationships add structured threshold context without changing semantic
ranking. A deterministic comparison stage now turns attributable candidate facts into explicit
pass, fail, and unknown rule results before human review.

> [!IMPORTANT]
> This project is educational software, not personalized financial, tax, or legal advice.
> It does not execute trades. Market data can be incomplete, delayed, or incorrect.

## Quick start

Requirements: Python 3.12 or 3.13, `uv`, Git, and optionally Docker Desktop.

```powershell
Copy-Item .env.example .env
uv sync
uv run pytest
uv run etf-advisor demo
```

The demo pauses at a LangGraph human-review interrupt and then resumes with an automatic
approval so the complete lifecycle and the review-ready policy calculation are visible from
the terminal.

The policy draft selects a target percentage inside the configured risk band according to
the stated objective and shows cent-rounded arithmetic splits for the initial and recurring
USD amounts. It remains an illustrative policy calculation: it does not select ETFs,
forecast returns or drawdowns, execute trades, or guarantee results.

Install and start the local phase-one dashboard:

```powershell
uv sync --extra dashboard
uv run etf-advisor dashboard
```

Open `http://127.0.0.1:8501`, complete the profile, inspect the exact workflow review payload,
and approve, edit, or reject it. The default policy-only path is offline. Source evidence and a
provider-backed explanation are opt-in and require their corresponding extras, local services,
indexed data, and provider configuration. The default checkpoint lives only in the current
Streamlit browser session.

To keep a review across browser sessions, start the existing PostgreSQL service and enable the
dashboard's opt-in durable mode:

```powershell
docker compose up -d postgres
uv sync --extra dashboard --extra checkpoint
uv run etf-advisor dashboard
```

The dashboard puts a random review token in the local URL and can restore that exact paused or
completed graph thread later. It never lists other checkpoints. The token is not authentication;
this remains a single-user local development workflow rather than a production multi-user system.

For the opt-in evidence and explanation path, install all required adapters together:

```powershell
uv sync --extra dashboard --extra rag --extra providers
uv run etf-advisor dashboard
```

Install the Iteration 001 data and retrieval integrations:

```powershell
uv sync --extra rag
uv run etf-advisor data-health --symbols SPY,QQQ,VTI,BND
uv run etf-advisor ingest --symbols SPY,QQQ,VTI,BND
uv run etf-advisor search "broad US equity exposure"
```

The read-only health command reports source URLs, observation timestamps, ages, and
freshness classifications. Ingestion rejects stale or future-dated observations before
opening Chroma or Neo4j. Yahoo requests use configurable bounded retries.

The first Chroma ingestion may download its local default embedding model. The ingestion
command prints source IDs, observation timestamps, and Yahoo Finance URLs so retrieved
context remains attributable.

Index the same source documents into the minimal Neo4j relationship graph and join graph
context back to Chroma-ranked results:

```powershell
uv run etf-advisor ingest --symbols SPY,QQQ,VTI,BND --with-graph
uv run etf-advisor hybrid-search "broad US equity exposure"
```

The graph stores ETF, fund-family/provider, category, sector, and source-document nodes. Stable
source document IDs form the join boundary, and a missing graph record is returned as
`graph_context: null` instead of silently fabricating context. Yahoo fund-family metadata is
not presented as a legal issuer. Versioned research snapshots retain source-linked sector weights
and explicit missingness; holdings, geography, benchmark, and overlap relationships remain
deferred until they demonstrate measured value.

Publish the packaged research universe as one snapshot after starting Chroma and Neo4j:

```powershell
uv run etf-advisor publish-research-universe --snapshot-version research-2026-08-30
```

The packaged membership is SPY, VTI, QQQ, BND, VEA, and VWO. The richer contract records fees,
average volume, category, benchmark, top holdings, sector exposure, geography exposure, and
top-ten concentration. Each field carries its own provider, source URL, observation and ingestion
times, units, version, and either a value or an explicit missing reason. The current Yahoo adapter
does not supply geography exposure, so it reports that field as unsupported rather than implying
zero exposure.

Publish a new immutable snapshot version after upgrading from Iteration 012 so Neo4j receives the
measured sector projection. Rechecking an already-active older version without its canonical local
payload verifies that snapshot but intentionally does not mutate it.

Publication stages versioned Chroma documents and verifies their IDs and digest metadata before
Neo4j writes and activates the same snapshot in one graph transaction. Hybrid retrieval uses the
Neo4j active pointer's version and digest to filter Chroma. Document IDs include both values, so
two concurrent attempts using the same version cannot overwrite each other's staged content.
Complete per-field provenance is retained as canonical structured JSON in both stores. If staging
or graph publication fails, the previous active snapshot remains available; inactive staged
documents are not searched by the advisory path. Before the first activation, a dedicated
legacy-only query excludes every document carrying snapshot identity metadata. A published version
cannot be reused for different content.

Before either store is changed, the command atomically saves the canonical snapshot under the
ignored `.artifacts/research-snapshots/` directory. Re-running the same explicit version reuses
that payload instead of refetching mutable Yahoo data. Use `--snapshot-file PATH` to select or
restore a particular canonical payload. An already-active version is reported as a successful
no-op only after its persisted Neo4j document manifest and exact version/digest metadata are read
back from Chroma. Snapshots created before manifest counts were introduced require their original
payload once so publication can backfill that count safely.

Yahoo research snapshots use the source-reported `regularMarketTime` rather than the local fetch
clock as their observation timestamp. The shared stale/future quality gate checks every research
field independently before the canonical payload or either retrieval store is written. Bounded
future source-clock skew is preserved and handled by the configured tolerance.

Run the local workflow with retrieved evidence attached to human review after indexing the
same source bundle:

```powershell
uv run etf-advisor demo --with-evidence --candidate-limit 5
```

The workflow builds a deterministic query from the profile, preserves Chroma's ranking,
validates HTTP(S) source URLs and UTC observation timestamps, recomputes freshness, and
requires source-reported ETF and US-market metadata before review. Missing, malformed,
non-ETF, non-US, stale, or future-dated evidence stops the workflow before the interrupt. The
evidence bundle is research context only; it does not select ETFs, allocate money, or execute
trades.

Before review, ready evidence passes through deterministic candidate screening. The same rules
check US listing, ETF type, freshness, expense ratio, average daily volume, top-ten concentration,
and supported sector exclusions. Results preserve retrieval order and include stable reason codes,
thresholds, field source URLs, and observation timestamps. Missing evidence and exclusion terms
outside the available sector taxonomy remain `unknown`; they never become silent passes. The
default 1.0% expense-ratio maximum, 100,000-share volume minimum, 60.0% top-ten concentration
maximum, and zero sector-exposure tolerance are configurable illustrative research filters, not
suitability thresholds or an ETF ranking.

Install the optional provider adapters and generate a structured explanation from the policy
and ready evidence:

```powershell
uv sync --extra rag --extra providers
uv run etf-advisor demo --with-evidence --with-explanation --candidate-limit 5
```

Set `LLM_PROVIDER` plus the matching model and credential variables in `.env`. Ollama and
OpenRouter are imported only for this opt-in path. Each generated statement must cite an exact
policy key or source document ID; unknown citations, mismatched ETF subjects, malformed output,
explicit guarantees/recommendations/forecasts, and provider failures stop before review.
Citation URLs and timestamps come from the validated evidence bundle, not from model output.

Output handling is capability-aware and does not hard-code model names. Local Ollama uses
provider-enforced JSON schema. Direct Ollama Cloud receives the same schema in the prompt and is
validated locally because its Cloud endpoint does not currently support structured outputs.
OpenRouter uses strict function calling. A failed provider run reports a redacted category,
provider, model, method, and optional HTTP status in CLI/dashboard state without exposing
credentials, prompts, retrieved source content, or raw model responses. Each review attempt makes
one provider request and does not automatically retry with another output method.

Run the retrieval baseline without credentials, databases, or network access:

```powershell
uv run etf-advisor evaluate-retrieval
```

The JSON report separates ranking metrics from fund-family/category and sector-context metrics.
The version-three dataset demonstrates complete structured sector context and an exact technology
threshold match with no ranking delta. That evidence retains the sector projection only; it does
not justify adding unmeasured graph relationships.

Run the explanation and safety baseline through the exact production pre-review validator:

```powershell
uv run etf-advisor evaluate-explanations
```

The versioned offline cases cover valid and invalid citations, supported and fabricated numeric
claims, ETF/source agreement, provider refusal, unsafe financial language, and prompt injection.
The command prints deterministic per-dimension JSON metrics and exits nonzero if any expected
accept/reject decision regresses. It does not call a model, service, database, network, or clock.

Start the local data services:

```powershell
docker compose up -d chroma neo4j postgres
docker compose ps
```

Chroma is available at `http://localhost:8000`, Neo4j Browser at
`http://localhost:7474` (Bolt at `neo4j://localhost:17687`), and PostgreSQL at
`localhost:5432`. Ports are bound to the local machine only. The Neo4j host port is
remapped because this Windows machine reserves the standard `7687` port.

`yfinance` is used only as a development/research adapter in this phase. Its documentation
states that it is unofficial and intended for personal use, so it is not a production data
licensing decision.

## Repository guide

- `wishlist.md`: raw, user-owned ideas and requests.
- `AGENTS.md`: operating rules for coding agents.
- `docs/product/`: stable product intent, scope, and the directional roadmap.
- `docs/architecture/`: current architecture and immutable decisions.
- `docs/iterations/`: short delivery plans and acceptance criteria.
- `docs/runbooks/`: reproducible operational procedures.
- `src/etf_advisor/`: application code.
- `tests/`: executable behavior and safety checks.

The directional roadmap is in `docs/product/roadmap.md`. The current delivery contract is in
`docs/iterations/013-measured-sector-graph-context.md`.

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
