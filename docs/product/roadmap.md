# Product roadmap

## Purpose

Evolve the local, single-user educational ETF research and portfolio-building prototype.
The immediate supported journey is the fixed twenty-candidate US-listed/USD starter.
The implemented legacy US, opt-in US/EU and bounded catalogue paths remain supported;
broader live US/EU readiness is deferred, not established by those implementations.
UK, Swiss and other non-EU listings remain outside the US/EU target. Delivery remains
incremental: every slice must
produce a runnable artifact, explicit acceptance criteria, automated tests, and
source-attributable financial outputs.

This roadmap is directional rather than a promise of dates. The active delivery contract
continues to live in the highest-numbered file under `docs/iterations/`.

## Proven baseline: iterations 000-017

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
- Capability-aware Ollama Cloud explanation generation with strict local validation, request-scoped
  reference allowlists, one-request behavior, and redacted provider and contract diagnostics.
- Deterministic model-portfolio construction with exact weight and cash reconciliation, explicit
  category and position constraints, source-attributable reasons, fail-closed dashboard
  recomputation, and durable human-review restoration.
- Typed, auditable revision planning with explicit feedback boundaries, immutable lineage,
  fail-closed side-effect replay receipts, local checkpoint retention/deletion, and allowlisted
  dashboard lifecycle controls.

Iteration 016 builds, validates, presents, and restores a checkpointed illustrative portfolio
at human review with deterministic safety gates. The local prototype does not optimize for
expected performance or execute trades. Source coverage and portfolio quality remain measured gaps.

## Completed advisory-quality iterations

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

### Iteration 015: Ollama Cloud provider compatibility (complete)

Make optional grounded explanations usable and diagnosable across Ollama Cloud models without
weakening the fail-closed human-review boundary.

Acceptance gate:

- Route output handling by endpoint capability rather than model-name allowlists.
- Validate plain Cloud JSON locally against the exact explanation, grounding, numeric-support, and
  financial-safety contracts.
- Persist only stable redacted provider and local-contract diagnostics.
- Make one provider request per review attempt, with no automatic fallback retry.
- Complete offline quality gates and one explicitly approved successful Cloud verification.

### Iteration 016: explainable model-portfolio construction (complete)

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

### Iteration 017: revision loop and audit trail (complete)

Make edit and reject decisions controlled, auditable reruns rather than terminal labels.

Acceptance gate:

- Route typed feedback only to its earliest affected workflow stage and invalidate downstream
  artifacts deterministically.
- Reuse only validated successful side-effect receipts; require an explicit retry after failed or
  ambiguous attempts.
- Preserve revision lineage, source-snapshot identity, audit reconstruction, bounded retention,
  exact-thread deletion, and process-local discard behavior.
- Present allowlisted history and lifecycle controls without treating a review token as
  authentication or exposing private audit content.

## Current disposition: local analysis and portfolio quality (parent #24)

Reconciled on 14 November 2026 against merged main `a012b34582b5dcfd60e83eacc99e19dfc3be52e2`.
The original seven slices are complete; this list records their delivered order, not a queue:

1. **#99** — Freeze a broader reproducible analysis baseline and align this roadmap.
2. **#103** — Discover Yahoo US/EU ETF catalogue entries and support direct-symbol lookup;
   report pagination and provider coverage honestly.
3. **#104** — Explicit US/EU listing and currency contracts, with the separately approved
   vision and architecture changes.
4. **#105** — Publish broader research snapshots and choose a bounded per-request candidate
   shortlist for actual dashboard portfolio use.
5. **#100** — Compare ETFs with attributable facts and visible evidence gaps.
6. **#101** — Measure reported-holdings overlap with explicit partial-coverage limits.
7. **#102** — Measure semantic retrieval and existing graph contribution on identical cases.

### Delivered since the original sequence

- **#141 / PR #142:** curated US/USD starter, twenty packaged source leads, bounded
  preparation and allocation-aware shortlisting for fresh reviews. Saved reviews keep
  their recorded version. See [iteration 043](../iterations/043-issue141-curated-us-starter.md).
- **#143 / PR #144:** approved immediate starter direction and prospective issue/PR
  working agreement, without removing financial, data or saved-state safeguards.
  See [iteration 044](../iterations/044-issue143-prospective-working-agreement.md).
- **PR #145:** one source pass on **11 November 2026** collected 20/20 leads;
  17 were construction eligible. Three profiles on the same prepared artifact produced
  ready drafts with exact weights/cash, **awaiting human review**. No explanation,
  approval, retry or PostgreSQL process-restart proof was produced. Detached JSON review
  validation is distinct from durable restoration. See [dated evidence](../iterations/045-issue117-us-starter-use-2026-11-11.md).
- **#115 / PR #146:** fresh US/EU retrieval requests ECB FX only when the actual
  selected subset needs it; historical absent-marker reviews preserve their semantics,
  and downstream edits remain offline. See [iteration 046](../iterations/046-issue115-selected-fx.md).
- **#106 / PR #147:** early decomposition guidance distinguishes same-scope repair,
  independently useful proposals and an explicit stop. See [iteration 047](../iterations/047-issue106-early-decomposition.md).
- **#109 / PR #148:** three model presets (`astra`, `sol`, `luna`) are separate from
  six task assignments; owner denotes accountability. No-write assignments use
  instruction-only restrictions under inherited access. Static checks do not attest
  runtime identity or enforce a filesystem boundary. See [iteration 048](../iterations/048-issue109-model-presets.md).

The dated starter result does not establish today's source coverage, independent economic
risks among equal-index ETFs, suitability or broad-market completeness. The original
[#117](https://github.com/beagle1903/agentic-etf-advisor/issues/117) US/EU publication,
partial-job and saved-review criteria remain unmet and deferred. Original legal Fund/class
curation in [#123](https://github.com/beagle1903/agentic-etf-advisor/issues/123) remains
stopped/deferred; it is not a prerequisite for normal starter use. Historical failed
outcomes, ledgers and original scopes remain evidence of their own scenarios.

### Preserved simplification dispositions

| Recommendation | Current disposition |
| --- | --- |
| Decide immediate product scope | Delivered by #143: fixed US/USD starter; wider readiness and custom/larger membership deferred. |
| Simplify development workflow | Delivered by #143, with #106 decomposition guidance and #109 preset/assignment separation now also delivered. |
| Choose one current data contract | Deferred; no compatibility retirement, export/reset or saved-review migration is authorized. |
| Reduce storage/publication dependencies | Deferred; the prepared starter already avoids Chroma/Neo4j, but no supported backend is removed. |
| Simplify identity/repeated validation | Further consolidation deferred; listing, share-class, legal Fund and exposure distinctions and exact numeric safeguards remain. |
| Verify each runnable slice | Ongoing practice; the 11 November starter exercise is delivered dated evidence, with its limits above. |

### One proposed next slice: selected-position reported-holdings comparison

**Recommendation only; not scheduled or authorized for implementation.** The November 11
drafts included SPY, IVV and VOO together. The existing #101 control already compares any
chosen pair; it does not automatically show all selected-position pairs at human review.
Surface those existing pairwise results for the draft's at most five selected positions
(at most ten pairs), so a reviewer can see shared reported holdings without manually
finding each pair. This extends presentation; it does not reopen completed #101 acceptance.

Proposed observable acceptance:

- Show exactly the unordered pairs of selected evidence identities, excluding unselected
  candidates; use the existing conservative overlap helper and its persisted check time.
- Retain per-side reported-row sums, field sources/timestamps, exact result units and
  explicit partial-list, unavailable/conflicting/stale/future limitations. Never turn
  unavailable evidence into zero or imply full-fund coverage or independent risks.
- Render a ready and an offline-restored review with no provider/store calls and identical
  graph JSON, source/artifact identities, eligibility, selection, weights and cash.
- Exercise partial, zero and unavailable pairs plus the five-position bound in focused
  helper/UI checks. Keep the existing manual two-candidate comparison available.

Non-goals: a portfolio-wide or weighted overlap score, new identity/index inference,
financial-rule/ranking/optimizer changes, new source calls, larger/custom universes,
schema/storage changes or acceptance of broader #117/#123. A future authorized owner must
confirm the presentation boundary; any consequential interpretation or contract change
requires separate design advice and coordinator approval. No child issue is created here.
The evidence and recommendation are recorded in [iteration 049](../iterations/049-issue24-roadmap-reconciliation.md).

Every future slice needs a concrete limitation, versioned baseline, observable quality criterion,
source evidence, and focused verification. Catalogue entries, researched ETFs, eligible ETFs,
and the per-request shortlist are distinct counts. Passing fixture replay does not show live
Yahoo coverage, model quality, portfolio suitability, or improved returns. New source providers,
graph relationships, and allocation algorithms need their own demonstrated gap and approval.

The former sign-in, multi-user, and production-hosting priorities were withdrawn from active
scope. Issues #23 and #83 were deleted and their historical records remain external; this plan
does not resume them. Accepted architectural decisions remain history. Local human review and
existing financial guardrails still apply.

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
