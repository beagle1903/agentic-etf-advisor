# Performance reviewer — 20260906-071454Z

## Result and scope

One confirmed P2 finding; no P0 or P1 performance finding. The legacy Chroma fallback requests the whole collection even for a small result limit. Other scaling concerns below are observations or unmeasured risks, not confirmed user-facing latency defects.

Reviewed detached HEAD `c25865f84207ae9c7c89b4af1d339407a5d4b614`, matching the recorded `origin/main` commit, without switching branches. Inspected AGENTS.md, wishlist, product vision, architecture, relevant accepted ADRs 0001/0005/0007/0015/0016, and the highest iteration, 017. Inspected Yahoo collection and parsers, vector/graph stores and publication, evidence bounds, construction enumeration, explanation prompts/provider setup, revision integrity/replay, checkpoint adapter, dashboard reruns, packaging declarations/Dockerfile, relevant tests, and the PR #45 merge changes. Issue #41 lifecycle and #42 interactive revision forms remain explicitly planned work, not regressions.

## PERF-01 — Legacy retrieval materializes the entire Chroma collection

- **Severity:** P2.
- **Confidence:** High; confirmed with an injected fake collection and direct source inspection.
- **Affected files and exact lines:** `src/etf_advisor/rag/chroma_store.py:72-83` obtains collection size, passes it as the query limit, and filters/slices afterward; `:110-120` constructs every returned `RetrievedSource`. `src/etf_advisor/rag/hybrid.py:39-41` reaches this fallback when no snapshot is active. `tests/test_chroma_store.py:102-104` currently expects full-collection querying in the small mixed-collection fixture.
- **Evidence:** A fake collection with `count() == 50000`, called through `search_unversioned("broad market", limit=5)`, recorded `{'requested_limit': 5, 'actual_n_results': 50000, 'where': None}`. The fake returned only one small row; no large dataset, network, or external service was used. This proves request amplification, not actual Chroma latency or peak RSS.
- **Trigger:** Search before first successful snapshot activation in a collection containing accumulated legacy documents and/or staged versioned documents. Even an all-legacy collection incurs the whole-collection request. A failed initial publication must remain unreachable, so excluding versioned records is necessary.
- **Impact:** Retrieval transfers and parses O(collection size) document content and metadata instead of O(requested results), making a five-result lookup scale with retained history. Staged documents that cannot be used still consume response and parsing resources. The active version-and-digest path is bounded by the requested limit and is not affected by this finding.
- **Remediation agent prompt:**

  > Implement bounded legacy semantic retrieval in `src/etf_advisor/rag/chroma_store.py` and the minimum required store/publication metadata interfaces, with regression tests in `tests/test_chroma_store.py`, `tests/test_hybrid_retrieval.py`, and snapshot publication tests. Preserve the strict invariant that a document carrying either snapshot version or digest metadata can never enter the no-active-snapshot fallback. Prefer an explicit legacy visibility marker with a documented one-time migration, or a separately scoped legacy collection, so Chroma can filter eligibility before top-K ranking. Do not assume missing-key `$ne` semantics or simply replace `collection_count` with `limit`, which can omit valid legacy results behind staged hits. Preserve ranking, version/digest immutability, source provenance, and adapter replaceability; do not delete user data, silently migrate a live store, call financial/model endpoints, or change finance policy. Acceptance: empty/all-legacy/mixed/partially versioned/staged-only collections behave correctly; eligible results up to K are returned in rank order; normal fallback queries request only bounded eligible results and never materialize all retained documents; any migration requirement fails safely and is explicit. Add an instrumented fake with a large reported count, high-ranked staged hits, and more than K valid legacy hits. Verify with `uv run pytest tests/test_chroma_store.py tests/test_hybrid_retrieval.py tests/test_snapshot_publication.py`, then `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy`, `uv run pytest`, both offline evaluation commands, `uv build`, and `docker compose config --quiet` in an isolated frozen environment.

### Minimal local reproduction

Run using the audit's external frozen Python with `-B`, or an existing frozen environment. This does not contact Chroma or create a client connection.

```python
from types import SimpleNamespace
from etf_advisor.rag.chroma_store import ChromaDocumentStore

class Collection:
    def count(self):
        return 50000

    def query(self, **kwargs):
        print(kwargs)  # n_results is 50000 although the caller requests 5
        return {
            "ids": [["legacy"]], "documents": [["safe synthetic"]],
            "metadatas": [[{}]], "distances": [[0.1]],
        }

client = SimpleNamespace(get_or_create_collection=lambda name: Collection())
store = ChromaDocumentStore(client=client)
assert len(store.search_unversioned("broad market", limit=5)) == 1
```

## Other checks and bounded scaling observations

### Yahoo request counts and retry behavior

`YahooResearchAdapter.fetch_snapshot` collects symbols sequentially (`data/yahoo_research.py:84-89`), while `_fetch_one` obtains metadata and three optional fund properties (`:97-136`). The same ticker/funds object is reused; successful properties in the installed frozen yfinance client share cached parsed fund data. Property-access count is therefore not a reliable HTTP-request count. Metadata retries use a fresh ticker, are capped at the configured attempts, and use injected exponential backoff (`:138-175`); defaults are three attempts and 0.25-second initial delay. One exhausted retry loop adds 0.75 seconds of scheduled backoff, excluding request time. Ticker creation and metadata have separate retry loops. The older `YahooFinanceAdapter` independently bounds history and metadata attempts (`data/yahoo.py:122-186`).

Read-only inspection of the installed `yfinance/scrapers/funds.py:71-79,107-115,155-163,166-182` shows that after a failed shared fund fetch, subsequent uncached properties may invoke the same fetch again. The repository converts each optional-property exception to a missing/source-error result (`yahoo_research.py:300-310`) instead of coordinating a shared retry budget. This remains a bounded amplification risk to measure; no rate-limit incident, actual HTTP count, or SLA violation was established here. HTTP deadlines and internal Yahoo retry/cookie behavior were not validated live. Increasing universe size should be preceded by request-count instrumentation and a bounded concurrency policy, with deterministic output order and one ingestion timestamp preserved.

### Revision integrity, repeated serialization, and retained history

PR #45 adds whole-state canonical hashing and full retained-ledger validation. `graph/revision.py:61-77` serializes the ledger and checks the sealed digest; `:77-198` validates historical revisions/receipts; pure/prepare/execute boundaries validate and deep-copy state (`:347-355,370-375,403-422`). `domain/revision.py:56-68` sorts and encodes canonical JSON. These costs grow with retained history, while immutable artifact references avoid duplicating unchanged upstream artifacts within the ledger. Repeated review recomputation is a deliberate trust-boundary check and must not be removed merely as an optimization.

A new local, non-network microcheck used the existing policy-only graph/test factories, created 25 successive typed profile revisions in an `InMemorySaver`, and measured five repeated `validate_revision_state` calls at each sample. Results are development-machine medians, not production benchmarks:

| Revisions | Current ledger JSON bytes | Median validation time |
| --- | ---: | ---: |
| 1 | 2,831 | 0.125 ms |
| 10 | 44,608 | 1.549 ms |
| 25 | 114,253 | 3.940 ms |

All 25 states reached `awaiting_human_review`. Serialized byte counts used Python's default `json.dumps`, including spacing; they are not actual PostgreSQL storage sizes. This demonstrates expected approximately linear current-ledger growth, not a present blocking defect. Retaining every successive full checkpoint can amplify cumulative storage; PostgreSQL storage, long histories, and evidence-heavy histories were not measured. Incorporate that measurement in planned Issue #41 rather than reporting its unfinished retention work as a regression. No caching across mutable/restored states is recommended without preserving full tamper checks.

### Construction and beyond-six-symbol scaling

`domain/construction.py:102-106` enforces a hard maximum pool size of ten, with matching `max_positions` validation (`:119-122`). The input path blocks oversized pools before `combinations` enumeration (`:539`, `:730-732`). Exhaustive subset search therefore remains bounded to at most 1,024 subsets, with early return on a feasible preferred subset. Evidence can accept up to 50 candidates (`rag/evidence.py:24`), but that does not raise the constructor's hard cap. The dashboard slider is 1-10 (`dashboard_app.py:94`). Raising the candidate limit would require an intentional design change rather than assuming this constructor scales to a complete ETF universe.

### Neo4j, publication, and snapshot digest work

`rag/neo4j_store.py:14-27` defines uniqueness constraints on lookup identities. Context retrieval batches source IDs through `UNWIND` and source-linked expansion (`:63-85`), rather than issuing a graph query per semantic hit. Snapshot publication batches document records in one transaction and switches activation there (`:88-156`), preserving consistency at the cost of a larger transaction as universe size grows. Legacy upserts still loop per document (`:214-234`), appropriate to the current small development path. No `EXPLAIN`/`PROFILE`, database calls, or large transaction tests were performed, so actual index selection and transaction memory are unverified.

Snapshot `content_digest` canonicalizes the snapshot (`research/models.py:160-168`); `to_source_documents` computes one digest before rendering its per-ETF documents (`:170-174`), avoiding an accidental per-record whole-snapshot hash. Repeated digest/readback work at publication boundaries serves integrity checks; no measured need to weaken or cache it was established.

### Model prompt sizes and calls

Provider prompts limit source excerpts to 4,000 characters and only expose selected-position candidates (`explanation/provider.py:27,183-210`). Graph context has at most 100 sector exposures (`rag/models.py:98`); source/candidate contracts bound core content and URLs. Construction defaults to five positions and permits at most ten through its pool constraint. Reviewer instruction text is bounded to 2,000 characters. OpenRouter sets `max_retries=0` (`explanation/provider.py:162`), consistent with explicit operation retry authorization. The receipt prepare/execute split adds checkpoint work intentionally to avoid invisible repeat calls.

The existing fake-provider revision fixture produced total system+human prompt sizes of 10,502 characters for `prompt_json`, 8,429 for `function_calling`, and 8,398 for `json_schema`. These are serialized-message character counts for one fixture, excluding provider-side tool/schema protocol overhead, not token counts or worst-case guarantees. `_build_messages` was run locally after constructing the fixture; only the fixture's one fake generation call occurred. No tokenizer, paid provider, throughput, context-window, or worst-case nested-string benchmark was run. The 100,000-character plain-response validation cap applies after receipt of the response, not a model generation budget.

### Streamlit and packaging/runtime overhead

`dashboard_app.py:39-45` avoids repeatedly restoring the same query token. Explicit submission state controls creation (`:97-130`), and normal rerenders use the saved `DashboardRun` (`:137-142`) instead of recreating the graph or rerunning retrieval. Review rendering independently validates current lineage and recomputes construction/explanation (`dashboard.py:315-410`); its cost grows with ledger size and remains a deliberate safety boundary. Durable operations use short-lived PostgreSQL connections (`checkpoint.py:46-74`); connection establishment cost is unmeasured and pooling should not be introduced without evidence.

Provider, Chroma, Yahoo, and Streamlit imports are lazy at optional integration boundaries. `pyproject.toml` keeps dashboard/RAG/provider/checkpoint dependencies in optional extras, and Dockerfile installs frozen base dependencies without development extras. The full-extras audit install is not representative of the base runtime. The inherited baseline took about 2.89 seconds for retrieval evaluation and 2.75 seconds for explanation evaluation including command startup; those end-to-end timings do not isolate import cost. No wheel bloat, module-import regression, or startup target violation was confirmed.

## YahooResearchAdapter refactor decision

**Later.** The class occupies `data/yahoo_research.py:40-269`; `_build_record` alone spans `:177-269` and combines typed-field assembly, provider fallbacks, units, and missing-reason choices. There is a reasonable future split between raw Yahoo collection, conversion helpers, and canonical record construction, particularly if adding a provider or increasing the universe. Existing injected ticker/clock/sleeper boundaries and `_RawResearch` already supply useful seams. File/class size alone does not establish a performance defect. A broad rewrite now could disturb timestamps, metadata retries, missing statuses, and percentage conversions with no measured six-symbol latency benefit. Any later extraction should preserve fixture outputs, source timestamps, error states, call counts, and the single ingestion clock capture before adding concurrency or caching.

## Verification, skips, and limitations

- Read parent-produced `00-uv-sync-result.json`, `baseline-results.json`, `03-mypy.log`, and `04-pytest.log`: frozen all-extras setup and all eight baseline gates passed; 360 tests passed, mypy checked 44 source files. No unchanged baseline was rerun by this role.
- Targeted checks used `C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv/Scripts/python.exe -B -` with `PYTHONDONTWRITEBYTECODE=1`, stdin scripts, existing test fixtures, and injected fakes. They did not create test/application files or run default `uv run`.
- The first combined microcheck completed lineage measurements but its prompt-size portion called keyword-only `build_explanation_request` positionally and raised `TypeError`. The corrected prompt-only check supplied the five named state fields and passed. This was an audit harness mistake, not a repository defect or baseline failure; it did not justify repeating baseline gates.
- Skipped by audit constraint: live Yahoo/provider calls, Chroma/Neo4j/PostgreSQL interaction, Docker service startup, external load tests, database query plans, network latency/rate-limit measurements, GPU/model inference, and production-sized memory/storage benchmarks. No package upgrades/installations or configuration changes were performed by this role.
- No source, test, dependency, lockfile, product/architecture/iteration document, configuration, or git changes were made by this role. Its sole repository write is this report. Cross-role final repository integrity verification belongs to SUMMARY.md.
