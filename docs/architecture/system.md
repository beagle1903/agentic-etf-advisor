# System architecture

## Current shape

The system is a LangGraph workflow with explicit boundaries between orchestration,
deterministic finance logic, retrieval, model providers, and presentation.

```text
Dashboard / API
      |
      v
LangGraph workflow ----> durable checkpoints (PostgreSQL)
      |
      +----> market-data adapter (Yahoo/yfinance for development)
      |
      +----> Chroma: source chunks and semantic retrieval
      |
      +----> Neo4j: ETF/entity relationships and graph enrichment
      |
      +----> provider adapter: Ollama Cloud or OpenRouter
      |
      +----> LangSmith: traces, datasets, and evaluations
      |
      v
Human review interrupt -> final explanation
```

## Retrieval responsibilities

- Chroma stores chunked, attributable unstructured material such as ETF descriptions,
  methodology documents, and research notes.
- Neo4j stores normalized entities and relationships. Graph records reference source IDs
  rather than silently duplicating the source of truth.
- Hybrid retrieval merges semantic candidates with graph neighborhoods, then reranks and
  applies freshness and source-quality checks.

The versioned research-universe path packages six curated symbols separately from mutable source
data. Every material field stores either a value or an explicit missing reason together with its
provider, source URL, observation time, ingestion time, unit, and snapshot version. The first rich
contract covers identity, category, fund family, benchmark, fees, average volume, top holdings,
sector exposure, geography exposure, and top-ten concentration. Yahoo's current development
adapter does not report geography exposure, so that field remains explicitly provider-unsupported.

Publication uses version-and-digest-scoped document IDs. Chroma is staged and its IDs, version,
and snapshot digest are read back before graph publication begins. Neo4j then writes the snapshot
graph and changes one `ResearchCatalog` active pointer in the same query transaction. Hybrid
retrieval reads that pointer first and filters Chroma to the exact active version and digest. A
failed stage or graph transaction therefore leaves the previous active snapshot reachable;
inactive staged Chroma records do not enter advisory retrieval. A published version is
content-address checked and cannot be reused for different snapshot content. Canonical field-level
provenance JSON is retained on each source document in both stores. When no snapshot has ever been
activated, hybrid retrieval uses a dedicated legacy-only semantic query that removes every record
carrying version or digest metadata, so a failed first publication cannot bypass activation.

The publication CLI writes the validated canonical snapshot payload atomically to an ignored local
artifact before either database is changed. An explicit-version retry loads that payload rather
than refetching mutable provider data. If Neo4j already reports the requested version and digest as
active, a retry without the local payload reads Neo4j's persisted document count and IDs, verifies
every ID plus exact version/digest metadata in Chroma, and rechecks the active pointer before
returning a successful no-op. Reactivating an inactive version requires its original payload.

The implemented Neo4j projection uses `ETF`, `FundFamily`, `Category`, `Sector`, and
`SourceDocument` nodes. Yahoo's `fundFamily` field is preserved as fund-family/provider
context; it is not presented as the ETF's legal issuer. ETF relationships provide the
reusable entity graph, while each source document also links directly to the fund family,
category, and weighted sector exposures it reported. Each upsert replaces those source-specific
relationships, including when metadata disappears. Snapshot publication also replaces the
normalized ETF-level fund-family, category, and weighted sector relationships in the same
activation transaction, preventing legacy relationships from surviving a newer snapshot. Sector
relationships are parsed fail-closed from canonical field provenance, and retrieval preserves the
source status so unavailable evidence cannot become a zero weight. Chroma distance remains the
ordering signal; the sector evaluation demonstrates constraint-context value, not ranking lift.

Holdings, geography, benchmark, and overlap relationships remain outside the graph projection.
Geography is provider-unsupported, and the other relationship families have no measured
graph-specific consumer yet.

The workflow can receive an injected `CandidateEvidenceRetriever` at its side-effect
boundary. The live adapter wraps the existing hybrid retriever, converts ranked results into
an evidence bundle, and rechecks source URL, observation timestamp, and freshness before the
human-review interrupt. Ready evidence requires an attributable HTTP(S) URL and Yahoo's
source-reported `quote_type=ETF` and `market=us_market` metadata. It preserves the first result
for each symbol and omits mismatched graph context rather than fabricating a relationship. The
evidence model now exposes normalized source-linked sector weights and explicit availability
status. The persisted candidate contract independently requires the graph context's source ID and
normalized symbol to match the candidate, so restored checkpoints and replaceable retrievers
cannot relabel another ETF's sector weights as citation support.

## Deterministic candidate screening

Ready evidence enters a pure, side-effect-free screening stage before optional explanation
generation. The stage applies the same stable rule sequence to every candidate: US listing, ETF
type, freshness, expense ratio, average daily volume, top-ten concentration, and requested sector
exclusions. Rules and candidates use `pass`, `fail`, or `unknown`; missing evidence and exclusions
outside the available sector taxonomy never become silent passes.

The default research policy uses a maximum 1.0% expense ratio, minimum 100,000-share average daily
volume, maximum 60.0% top-ten concentration, and zero exposure tolerance for a supported requested
sector. The values are checkpointed, configurable, and explicitly labeled as illustrative filters
rather than suitability thresholds. Screening preserves Chroma order and does not produce a model
ranking.

Scalar judgments read canonical field provenance and require its flattened status and value to
agree. Sector judgments require the source-linked Neo4j weights to match the canonical sector
field exactly. Every result carries a stable reason code, observed value, threshold, source URL,
and observation timestamp. The dashboard recomputes the bundle from evidence before rendering,
which prevents persisted or replacement data from silently relabeling a result.

## Deterministic model-portfolio construction

ADR 0014 defines the deterministic stage between candidate screening and optional explanation
generation. It revalidates the profile, policy calculation, ready evidence, recomputed
screening, and checkpointed construction policy without a model or side effect. Only candidates
with a complete `pass` screening verdict and consistent, supported category provenance can enter
feasibility search.

The accepted contract uses exact source-category mapping to assign candidates to the existing
growth and defensive policy sleeves. It does not infer an asset class from a ticker, source prose,
fund-family/provider value, or model output. The initial policy requires three to five positions,
5.00% to 80.00% per position, at most 80.00% in one source-reported category, and one-basis-point
weight precision. These values are illustrative research controls rather than suitability or
optimization claims.

The implementation also checkpoints a maximum candidate-pool size of ten. Larger pools fail with
`candidate_pool_limit_exceeded` before subset enumeration, bounding exhaustive deterministic
tie-breaking to at most 1,024 subsets under the initial contract. Category provenance receives its
own freshness check against the evidence bundle's check time, maximum age, and future tolerance;
a stale or future category blocks construction even when the candidate-level observation is
current.

Construction chooses the feasible subset with the most positions and uses upstream retrieval order
only for deterministic tie-breaking. It divides each exact policy sleeve equally in integer basis
points, reconciles initial and recurring cash independently in integer cents, and uses stable
remainder rules to preserve every total. Missing or unsupported candidate category evidence may
exclude that candidate; stale evidence, contradictory provenance, cross-contract mismatches,
tampered screening, or an infeasible complete constraint set block the stage before explanation or
human review.

The graph payload is one JSON-mode `portfolio_construction` bundle containing the
checkpointed construction policy, optional draft, validation checks, excluded-candidate audit
records, and stable errors. The dashboard recomputes the bundle from its upstream state before
rendering it, just as it recomputes candidate screening. An explanation provider may
describe only a validated draft and cannot select candidates, change weights, repair a blocker, or
decide suitability.

The implemented pure constructor chooses the largest feasible subset, retains upstream order as
its only tie-breaker, and allocates the exact growth and defensive sleeve targets in integer basis
points. It reconciles initial and recurring cash independently in integer cents with stable
largest-remainder ordering, then runs an independent validation pass over eligibility, sleeve and
position constraints, category concentration, exact totals, and source attribution. A blocked
bundle stops the workflow before optional explanation generation or human review. Presentation of
the ready bundle shows its positions, exact weight and cash totals, allocation bands, construction
rules, validation outcomes, deterministic reasons, exclusions, and attributable source metadata.

## Retrieval evaluation

The offline baseline replays one versioned, curated candidate set through two explicit
interfaces: semantic retrieval alone and the existing source-linked graph enrichment path.
Both variants receive the same candidates in the same order. Deterministic metrics report
hit rate, recall at K, mean reciprocal rank, source-attribution rate, graph-context recall,
exact fund-family/category field accuracy, sector-context coverage, and exact sector-threshold
matching.

The packaged baseline contains only source-attributable documents with UTC observation
timestamps. Source documents reject timezone-naive observations rather than silently
assigning UTC to an unknown wall time. The baseline does not call Chroma, Neo4j, an embedding
model, a provider, the network, or the wall clock. This makes metric changes reviewable and
repeatable while leaving live-store and LangSmith-backed evaluation behind replaceable
adapters. Because the hybrid retriever preserves Chroma order, the measured sector improvement is
explicitly constraint-context lift. It justifies the sector projection but not any further schema
expansion.

The policy draft now calls a pure deterministic calculation boundary. It selects an
illustrative target inside the existing risk-tolerance band based on the stated objective,
then splits initial and recurring USD amounts to cents while preserving each total. The
result is converted with `model_dump(mode="json")` before entering graph state, so this
calculation does not add a top-level state field or introduce a clock, network, database,
provider, forecast, or trade side effect.

The optional explanation stage receives a provider-agnostic `ExplanationGenerator`. Before the
provider call, its request independently recomputes the persisted portfolio from the validated
profile, policy, evidence, screening, and construction policy. The adapter sends allowlisted policy
and portfolio-construction reference indexes plus a bounded set of source records for selected
positions only. Every returned statement declares a policy, portfolio-construction, or
source-evidence basis. Deterministic validation rejects unknown keys, unknown references, and ETF
subjects that do not match their cited source or construction records. A rule-based safety gate
also rejects explicit return
guarantees, trade or recommendation instructions, suitability claims, forecasts, and risk-free
outcomes. Citation URLs and timestamps are copied from validated evidence, not model output.
Source text is treated as untrusted quoted data, every ordinary provider SDK exception is
sanitized at the adapter boundary, and fixed safety limitations are appended after generation.
Every numeric value in a generated statement must also be present in that statement's exact
cited policy fields, revalidated construction fields, or selected-position source records. This
deterministic check blocks fabricated fees,
percentages, amounts, and other numbers without claiming to solve general semantic entailment.

Provider output steering follows the configured endpoint's capability rather than a model-name
allowlist. Local Ollama uses its JSON-schema `format` support, while direct Ollama Cloud receives an
explicit output schema in the bounded prompt and returns ordinary text because the Cloud endpoint
does not currently support structured outputs. The adapter extracts at most one bounded JSON
object and applies the same Pydantic and deterministic validators locally; raw Cloud text is never
rendered. OpenRouter continues to use strict function calling. None of these paths automatically
retry with a second output method.

Every explanation prompt carries separate request-scoped allowlists for policy,
portfolio-construction, and selected-position source-document references. References must be
copied exactly from the list matching each statement's grounding basis. The schema embedded for
plain Ollama Cloud output further enumerates the union of allowed reference strings and selected
source symbols. The adapter does not guess, normalize, or remap unknown model references;
deterministic basis, reference, and subject validation remains authoritative.

Provider exceptions are categorized into stable redacted diagnostics: authentication, rate limit,
unsupported capability, invalid response, unavailability, or other provider error. Graph state may
retain the category, provider, model, output method, and HTTP status. Credentials, prompts, source
content, and raw model responses remain outside checkpoints and presentation. The local dashboard
labels these fields as redacted before rendering them.

Provider output that passes the Pydantic schema but fails deterministic local validation receives a
separate stable contract category: prohibited claim, unknown policy reference, unknown
construction reference, unknown source reference, subject mismatch, unsupported numeric claim, or
an unexpected contract-validation failure. The graph retains only that category and the generic
fail-closed message. It does not
retain the rejected generated text, model-supplied references, or unsupported numeric values.

## Explanation evaluation

The explanation baseline replays one versioned request and eight curated provider outputs
through the same `validate_and_bundle_explanation` function used before human review. It covers
valid and invalid citations, supported and unsupported numeric claims, matching and mismatched ETF
subjects, revalidated portfolio-construction grounding, provider refusal, unsafe financial
language, and both resisted and followed prompt injection. Per-dimension accuracy and the overall
gate are deterministic and require no provider, network, database, credential, or wall-clock
access.

The gate passes only when every actual accept/reject decision matches its curated expectation. The
packaged cases are a small regression baseline, not proof of general semantic entailment or broad
model safety. LangSmith-backed comparisons remain an optional future adapter; offline evaluation
stays independently runnable and authoritative for repository verification.

Provider refusal is the one case replayed through the production `draft_explanation` node because
there is no structured output to validate. The case passes only when the node returns the complete
blocked generation-error state with no review-ready draft.

## Workflow stages

1. Validate the investor profile.
2. Clarify missing or contradictory constraints.
3. Fetch and validate timestamped market/reference data.
4. Calculate deterministic portfolio constraints and illustrative policy ranges.
5. Retrieve and validate source-grounded ETF evidence.
6. Apply deterministic candidate screening and retain pass, fail, and unknown reasons.
7. Construct and validate an illustrative model portfolio.
8. Draft a source-grounded explanation of the validated result.
9. Run rule-based and evaluation guardrails.
10. Pause for human review.
11. Finalize, revise, or reject.

## State and side effects

Graph state must remain JSON-serializable. Network calls, clock reads, model calls, and
database writes are wrapped as explicit tasks or adapters so replay after an interrupt is
predictable. Development tests use an in-memory checkpointer; multi-user environments use
PostgreSQL-backed checkpoints.

The optional evidence node receives its retriever through dependency injection. The adapter
captures one injected UTC check time, includes freshness results in state, and ends the run
before review when retrieval is empty, provenance is incomplete, or any observation is stale
or too far in the future. A live store failure is translated into an evidence error instead
of producing an ungrounded review payload. The evidence model recomputes health classifications
from timestamps and the declared freshness window, and the workflow revalidates the serialized
bundle so a replaceable retriever cannot bypass those invariants with an unvalidated model.
Each new run clears downstream review artifacts, and routing uses the current node status so a
reused durable thread cannot carry previously ready evidence across a new retrieval failure.

The construction node is pure and requires the current ready evidence plus recomputed screening.
Each profile-validation run clears its bundle and errors. A ready result is checkpointed only as a
JSON-mode model dump; a stable blocker ends routing before explanation or review.

The explanation node is also optional and requires ready evidence. Its generated bundle and
errors are cleared during every profile-validation run, preventing a reused durable thread
from retaining a prior provider result. Policy-only and evidence-only flows remain available
for deterministic and local-store testing.

The current policy calculation is pure and runs before evidence retrieval and the review
interrupt. It is an arithmetic policy illustration rather than ETF selection or a prediction;
source-grounded evidence remains research context rather than a recommendation.

The local Streamlit dashboard is an optional presentation adapter over this same interrupt. The
default path retains one compiled graph, in-memory checkpointer, thread ID, and latest state inside
the browser session. Durable mode instead opens short-lived connections to the local PostgreSQL
checkpoint store for create, restore, and resume operations. A random UUID review token restores
only that exact thread from a newly compiled graph; the UI does not enumerate saved threads.

Both modes render policy, evidence, deterministic portfolio construction, and explanation fields
from the interrupt rather than reconstructing an allocation in the UI. Before rendering, a typed
presentation contract revalidates every nested field, policy/evidence consistency, and the identity,
URL, and timestamp of explanation citations against the validated evidence records. It recomputes
candidate screening from the evidence and checkpointed screening policy, then recomputes portfolio
construction from the validated profile, policy calculation, evidence, screening, and checkpointed
construction policy. A restored explanation must also match its checkpointed interrupt copy and
rebuild the explanation request from that revalidated construction before passing the same
grounding, selected-position, numeric-support, and prohibited-claim validation used before the
original interrupt. Either persisted mismatch produces a controlled error without review controls.
Policy-only review remains offline by default, while PostgreSQL persistence, evidence, and provider
generation are explicit opt-ins. PostgreSQL durability is not authentication or multi-user
authorization; this remains a local development workflow.

Investor-profile validation accepts only finite initial and recurring cash amounts from
zero through one trillion USD. Unsupported values therefore fail before decimal cent
quantization or the human-review interrupt.

## Data-source boundary

`yfinance` is suitable for research and personal development, but it is unofficial and its
own documentation says Yahoo data is intended for personal use. Before any public hosted
product, replace or license the market-data source and review redistribution terms.

Yahoo price-history and metadata requests use bounded retries with configurable exponential
backoff. A metadata exception exhausts those retries and fails the symbol; a successful
metadata object may still contain legitimately absent individual fields. After collection,
a deterministic quality boundary compares every field's source timestamp with one UTC check time
captured through an injected clock interface. One current field cannot mask stale data elsewhere
in the same ETF record. Stale observations or timestamps too far in the future block ingestion
before the canonical research payload or either retrieval store is written. Rich Yahoo research
uses the source-reported `regularMarketTime`; a missing or invalid source timestamp fails metadata
collection rather than being replaced by the local fetch time. A source timestamp slightly ahead
of ingestion remains intact and is accepted only within the configured future tolerance. The
health result retains the ETF field name, source name, URL, observation time, age, status, and
reason so the same evidence can be rendered by later presentation layers. The default 120-hour
window accommodates daily-close weekends and common market holidays; it does not label those
snapshots as live data.

The same quality policy is applied again when retrieved documents become workflow evidence.
This protects against older snapshots remaining in a retrieval collection after a later
ingestion and keeps the review boundary fail-closed.
