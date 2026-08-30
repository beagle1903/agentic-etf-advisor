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
status. Excluded sectors remain visible as an unverified constraint until Iteration 014 applies
deterministic pass, fail, and unknown screening rules.

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

The optional explanation stage receives a provider-agnostic `ExplanationGenerator`. It sends
an allowlisted policy-reference index and a bounded set of source records to a structured
Ollama or OpenRouter adapter. Every returned statement declares a policy or source-evidence
basis. Deterministic validation rejects unknown keys, unknown document IDs, and ETF subjects
that do not match their cited records. A rule-based safety gate also rejects explicit return
guarantees, trade or recommendation instructions, suitability claims, forecasts, and risk-free
outcomes. Citation URLs and timestamps are copied from validated evidence, not model output.
Source text is treated as untrusted quoted data, every ordinary provider SDK exception is
sanitized at the adapter boundary, and fixed safety limitations are appended after generation.
Every numeric value in a generated statement must also be present in that statement's exact
cited policy fields or source records. This deterministic check blocks fabricated fees,
percentages, amounts, and other numbers without claiming to solve general semantic entailment.

## Explanation evaluation

The first explanation baseline replays one versioned request and eight curated provider outputs
through the same `validate_and_bundle_explanation` function used before human review. It covers
valid and invalid citations, supported and unsupported numeric claims, matching and mismatched ETF
subjects, provider refusal, unsafe financial language, and both resisted and followed prompt
injection. Per-dimension accuracy and the overall gate are deterministic and require no provider,
network, database, credential, or wall-clock access.

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
6. Draft a source-grounded explanation.
7. Run rule-based and evaluation guardrails.
8. Pause for human review.
9. Finalize, revise, or reject.

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

Both modes render policy, evidence, and explanation fields from the interrupt rather than
recalculating them. Before rendering, a typed presentation contract revalidates every nested field,
policy/evidence consistency, and the identity, URL, and timestamp of explanation citations against
the validated evidence records. Contract failures show a controlled error without review controls.
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
