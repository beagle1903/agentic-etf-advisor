# Iteration 008: Source-grounded explanation drafting

- Status: Complete
- Started: 2026-08-28

## Goal

Draft a concise provider-backed explanation from the deterministic policy and validated ETF
evidence, then fail closed unless every generated statement has machine-checkable grounding
before the existing human-review interrupt.

## Deliverables

- A replaceable `ExplanationGenerator` protocol and typed request/result contracts.
- Structured explanation sections with explicit policy or source-evidence references.
- Deterministic grounding validation, citation derivation, and fixed safety limitations.
- Optional LangChain adapters for Ollama and OpenRouter with no provider imports at startup.
- An opt-in `etf-advisor demo --with-evidence --with-explanation` lifecycle.
- Offline regression tests for valid output, unknown references, subject mismatch, prompt
  injection content, provider failure, graph routing, and missing configuration.

## Acceptance criteria

- Provider calls occur only through an injected interface and offline tests need no
  credentials, services, network, or model package.
- A model sees only allowlisted policy fields and at most ten ranked source records; source
  content is explicitly treated as untrusted data.
- Every generated statement names its grounding basis and one or more exact references.
- Unknown policy/source references and ETF subjects that do not match cited source records
  stop the workflow before human review.
- Citation identity, URL, source, and observation timestamp are copied from validated evidence
  rather than accepted from model output.
- Provider and schema failures expose a sanitized error and cannot produce a review interrupt.
- Explicit guarantees, trade/recommendation instructions, suitability claims, forecasts, and
  risk-free outcomes fail a deterministic safety gate before review.
- Deterministic limitations prohibit advice, forecasts, allocation selection, and trades, and
  preserve the unverified-sector-exclusion warning when relevant.
- Existing policy-only and evidence-only approve/reject lifecycles remain unchanged.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and `uv run pytest`
  pass without network access.

## Deferred

- Semantic entailment scoring and a curated explanation evaluation dataset.
- Dashboard rendering and PostgreSQL-backed multi-user review.
- ETF allocation selection, suitability claims, forecasts, and trade execution.
- Graph-schema expansion and graph-aware reranking until measured retrieval value exists.

## Review correction

Automated review found that structural grounding did not prevent a model from attaching a
valid citation to prohibited financial language. Generated statements now pass a deterministic
pre-review safety gate for explicit guarantees, trade and recommendation instructions,
suitability claims, forecasts, and risk-free outcomes. Regression coverage confirms that each
category produces `explanation_blocked` state before the human-review interrupt while a
negative guarantee disclaimer remains allowed.

Provider exceptions are now normalized with an adapter-wide `Exception` boundary so unrelated
SDK hierarchies, including Ollama response errors, cannot escape the graph. The public error
remains sanitized and process-control exceptions are not caught.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes for 60 files.
- `uv run mypy` passes for 28 source files.
- `uv run pytest` passes offline (104 tests).
- Focused explanation and workflow regressions pass (29 tests).
- Both locked provider adapters instantiate with `uv run --extra providers` without making a
  model request.
- `uv run etf-advisor demo` preserves the policy-only review and approval lifecycle.
- `uv run etf-advisor evaluate-retrieval` remains deterministic with unchanged ranking and
  graph-context metrics.
- `docker compose config --quiet` passes.
- `uv build` produces the source distribution and wheel.
