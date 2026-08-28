# Iteration 007: Source-grounded review evidence

- Status: Complete
- Started: 2026-08-28

## Goal

Attach a deterministic, freshness-checked bundle of retrieved ETF source evidence to the
existing human-review boundary while keeping the policy calculation illustrative and
separate from ETF selection.

## Deliverables

- A replaceable `CandidateEvidenceRetriever` protocol and hybrid-store adapter.
- A deterministic profile-derived retrieval query.
- Typed evidence and provenance models that preserve source IDs, content, URLs, timestamps,
  distances, source metadata, and optional graph context.
- Freshness and provenance guardrails that use one injected clock value and fail closed.
- An optional workflow evidence node that reaches human review only for ready evidence.
- `etf-advisor demo --with-evidence` for exercising the live local retrieval path.
- Offline regression tests for current, stale, missing, duplicate, mismatched, empty, and
  store-failure evidence cases.

## Acceptance criteria

- The evidence adapter is injectable and tests do not require Chroma, Neo4j, credentials,
  network access, or a model provider.
- The same validated profile always produces the same retrieval query.
- Ready evidence preserves semantic result order, keeps the first result per symbol, and
  retains source URL, observation timestamp, source content, metadata, distance, and graph
  context in JSON-serializable state.
- The shared freshness policy blocks stale and future observations before human review and
  exposes source, URL, timestamp, status, age, and reason in the state payload.
- Missing required provenance, empty retrieval, mismatched graph context, and store failures
  cannot produce an ungrounded review interrupt; mismatched graph context is omitted.
- Excluded sectors remain visible, and the workflow explicitly states that current evidence
  does not verify sector exposure.
- The existing approve/reject lifecycle remains available when evidence is ready.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and `uv run pytest`
  pass without network access.

## Deferred

- LLM-generated explanations and provider adapters.
- Dashboard rendering and durable multi-user review UI.
- ETF-level allocation selection, suitability claims, forecasts, and trade execution.
- Sector/holding/benchmark expansion and graph-aware reranking until evaluation demonstrates
  measured value.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes.
- `uv run pytest` passes offline (74 tests).
- The injected workflow reaches review with ready evidence and ends before review for stale
  or failed evidence.
- JSON serialization of the evidence bundle succeeds without custom encoders.
- The existing offline retrieval evaluation remains unchanged and deterministic.
