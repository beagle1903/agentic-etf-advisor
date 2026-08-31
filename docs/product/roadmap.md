# Product roadmap

## Purpose

Evolve the current local prototype into a trustworthy educational US ETF portfolio
decision-support system. Delivery remains incremental: every slice must produce a runnable
artifact, explicit acceptance criteria, automated tests, and source-attributable financial
outputs.

This roadmap is directional rather than a promise of dates. The active delivery contract
continues to live in the highest-numbered file under `docs/iterations/`.

## Proven baseline: iterations 000-014

The repository already proves the following vertical slices:

- Reproducible Python and Docker development environment.
- JSON-serializable LangGraph state with pause, review, and resume behavior.
- Timestamped Yahoo Finance development data behind a replaceable adapter.
- Chroma semantic retrieval joined to source-linked Neo4j context.
- Deterministic offline retrieval evaluation and market-data freshness guardrails.
- Deterministic illustrative policy calculations separated from ETF selection.
- Freshness-checked ETF evidence and structured, source-grounded model explanations.
- A local Streamlit review experience with approve, edit, and reject decisions.
- Optional PostgreSQL checkpoints that survive browser-session and process loss.
- A deterministic explanation/safety evaluation gate covering grounding, refusal, unsafe language,
  numeric support, and prompt injection.
- A curated six-ETF research universe with field-level provenance, explicit missingness, stable
  snapshot digests, and graph-authoritative cross-store activation.
- Measured source-linked sector relationships that provide structured threshold context without
  changing semantic ranking; unmeasured graph expansions remain deferred.
- Deterministic, source-attributable candidate screening with explicit pass, fail, and unknown
  reason codes for listing, instrument type, freshness, fees, liquidity, concentration, and
  supported sector exclusions.

This is a strong research and review foundation, but it is not yet a complete portfolio
advisor. It does not build an ETF portfolio, validate all portfolio constraints, authenticate
users, use production-licensed market data, or execute trades.

## Next: prove advisory quality

### Iteration 011: explanation and safety evaluation baseline (complete)

Build a small versioned evaluation set for grounded explanations before adding more model-led
behavior.

Acceptance gate:

- Measure citation validity, claim support, subject-to-source agreement, refusal behavior,
  unsafe recommendation language, and prompt-injection resistance.
- Keep a deterministic offline evaluator; add LangSmith-backed runs only as an optional adapter.
- Block progression when a regression can put an unsupported or unsafe claim before review.

### Iteration 012: versioned ETF research universe (complete)

Move from manually supplied symbols to a small, curated, reproducible US ETF universe with a
richer source contract.

Acceptance gate:

- Preserve source URL, provider, observation time, ingestion time, units, and snapshot version
  for every material field.
- Cover the attributes needed for later screening, such as fees, liquidity, category,
  benchmark, holdings, sector, geography, and concentration, while representing missing data
  explicitly.
- Publish Chroma and Neo4j changes as one validated snapshot or leave the previous snapshot
  intact.
- Keep Yahoo/yfinance development-only and retain a replaceable path to licensed data.

### Iteration 013: measured graph and retrieval improvement (complete)

Expand relationships only where the richer data can demonstrate decision value.

Acceptance gate:

- Add holdings, sector, geography, benchmark, and overlap relationships in the smallest useful
  increments.
- Compare semantic-only retrieval with graph-enriched retrieval on the same versioned cases.
- Require measurable lift in ranking, constraint verification, or explanation context before
  retaining each schema expansion.
- Remove or defer graph complexity that does not earn its operational cost.

### Iteration 014: deterministic candidate screening (complete)

Turn retrieved research candidates into an auditable eligibility and comparison stage without
delegating financial rules to the model.

Acceptance gate:

- Apply explicit rules for US listing, instrument type, freshness, fees, liquidity,
  concentration, exclusions, and available exposure evidence.
- Report pass, fail, and unknown separately; missing evidence must never become a silent pass.
- Produce a comparison table with reason codes and citations, not an unexplained model ranking.
- Cover boundary values and conflicting constraints with deterministic tests.

### Iteration 015: explainable model-portfolio construction

Combine the policy ranges and eligible candidates into an illustrative portfolio draft that a
human can inspect and change.

Acceptance gate:

- Use deterministic allocation and validation logic; use the LLM only to explain evidence and
  trade-offs.
- Preserve cash totals and enforce weight totals, allocation ranges, diversification limits,
  exclusions, and minimum/maximum position rules.
- Show why every ETF is present, which user constraint it serves, and which source supports its
  material facts.
- Label uncertainty and stale or incomplete evidence, and fail closed when a required constraint
  cannot be verified.
- Remain educational: no forecast, guaranteed return, suitability claim, trade instruction, or
  brokerage action.

## Then: make review operationally complete

### Iteration 016: revision loop and audit trail

Make edit and reject decisions useful inputs to a controlled rerun instead of terminal labels.

Acceptance gate:

- Classify feedback and rerun only the affected deterministic, retrieval, or explanation stages.
- Never replay side effects accidentally across a checkpoint resume.
- Keep profile versions, evidence snapshot IDs, generated drafts, review decisions, and revision
  lineage auditable.
- Add explicit retention and deletion behavior for local checkpoints.

### Iteration 017: authenticated multi-user review

Add identity and authorization before exposing discovery or collaboration features.

Acceptance gate:

- Enforce per-user access to reviews and prevent opaque tokens from acting as authentication.
- Add pending-review discovery, concurrent-review conflict handling, and administrative audit
  controls.
- Define threat-model, secret-management, backup, migration, and recovery procedures.
- Preserve the offline single-user mode for development and deterministic testing.

## Later: production-readiness gate

Hosted deployment is a separate decision, not an automatic continuation of the local prototype.
Before any public launch:

- Replace or license market and reference data for the intended use and redistribution model.
- Add production observability, service-level objectives, cost controls, privacy controls,
  dependency scanning, and incident procedures.
- Validate retrieval, explanation, portfolio constraints, and human-review behavior against a
  broader curated evaluation suite.
- Perform legal and compliance review for the actual jurisdictions, claims, and user experience.
- Keep brokerage connectivity and every other external financial write out of scope unless a
  later ADR defines a separately approved, immediately pre-execution human control.

## Cross-cutting rules

Every roadmap slice must continue to satisfy these constraints:

- Financial claims retain source and observation timestamps.
- Graph state remains JSON-serializable; nondeterminism and side effects stay behind interfaces.
- Provider, database, embedding, and market-data implementations remain replaceable.
- Human review happens after evidence and guardrails and before advisory finalization.
- Plugins, skills, MCP servers, and editor hooks are adopted only for a defined need and with the
  narrowest practical access.
- No credentials, private downloads, or `.env` files enter version control.
- No trade execution, guaranteed returns, or autonomous financial decisions.

## Sequencing rule

Complete iterations in order unless new evidence justifies a change. A consequential reorder or
scope change should update this roadmap, create or supersede the relevant iteration plan, and use
an ADR when it changes an accepted architectural boundary.
