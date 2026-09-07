# agents-lab code-health audit summary

Run: **20260906-071454Z**. Reviewed revision: **c25865f84207ae9c7c89b4af1d339407a5d4b614**. Final synthesis: 2026-09-06 UTC.

## Executive summary

All seven independent specialty reports have been delivered and read for this synthesis. The frozen setup and all eight required baseline gates passed, including **360 tests**. Targeted offline probes nevertheless confirmed five behavior defects: two P1 eligibility/data defects and three P2 explanation, review-presentation, and retrieval defects. Three additional P2 maintenance/coverage findings concern store integration tests, obsolete workflow helpers, and unused optional dependencies. No P0 finding was established.

**Important distinctions:** passing the finite baseline does not make these defects disappear. Package currency remains **unknown** because the later installed-package check was blocked and registry fallbacks did not finish successfully. The requested reports are complete, but **strict audit completion under the reports-only write criterion is not satisfied**: two unintended ignored environment/cache directories were created and preserved. Every one of the 131 pre-existing files still matches its starting SHA-256; source, tests, dependency declarations, lockfile, configuration, and product/architecture/iteration documents are unchanged.

This was a maintenance audit, not product-phase acceptance. No fix, staging, commit, push, PR, branch change, reset, merge, rebase, recurring-automation change, Docker service startup, trade, or live financial/model/database request was performed.

## Scope and starting revision

- Starting checkout: **detached HEAD**, not branch `main`; no upstream exists. HEAD equals the existing local `origin/main` reference, with zero commits ahead/behind. No fetch was performed, so the remote server's latest revision is not asserted.
- Initial ordinary Git status was clean; there were no pre-existing changed files. The status in starting-state.json was captured immediately after creating the review directory and therefore includes the audit's own `?? reviews/` entry.
- Reviewed the checked-out PR #45 merge, the revision-routing implementation and identifier-injection follow-up, and their interaction with the existing source, retrieval, screening, construction, explanation, checkpoint, and presentation code.
- Read AGENTS.md, wishlist.md, product vision, system architecture, relevant accepted ADRs through 0016, and the highest iteration file, 017, in the prescribed order.
- Python at baseline: **3.13.14**. UV: **0.9.7**. Direct declarations, optional extras, development group, and build requirement are recorded in [PREPARATION.md](PREPARATION.md); locked direct/transitive versions are in [dependency-reviewer.md](dependency-reviewer.md). pyproject.toml and uv.lock were authoritative; no requirements.txt was assumed.
- Iteration 017 #40 routing/replay is implemented. #41 lifecycle, #42 interactive revision controls, and #43 iteration-wide acceptance remain planned. Their absence is not counted as a regression.

## Baseline results

The commands ran in this order against the audited revision. Exact outputs and exit codes are retained in [baseline-results.json](baseline-results.json). No required baseline gate failed or was skipped.

| Command | Result | Evidence |
| --- | --- | --- |
| `uv sync --all-extras --frozen` | PASS; external environment, 150 installed packages | [setup](00-uv-sync.log) |
| `uv run ruff format --check .` | PASS; 110 files reported formatted | [format](01-format.log) |
| `uv run ruff check .` | PASS | [Ruff](02-ruff.log) |
| `uv run mypy` | PASS; 44 source files | [mypy](03-mypy.log) |
| `uv run pytest` | PASS; 360 tests in 28.08 seconds | [pytest](04-pytest.log) |
| `uv run etf-advisor evaluate-retrieval` | PASS; five cases per strategy; graph context improves without changing ranking | [retrieval](05-retrieval.log) |
| `uv run etf-advisor evaluate-explanations` | PASS; eight of eight curated decisions | [explanations](06-explanations.log) |
| `uv build` with external `--out-dir` | PASS; sdist and wheel built | [build](07-build.log) |
| `docker compose config --quiet` | PASS | [Compose](08-compose.log) |

The baseline ran at approximately 07:16-07:18 UTC. UV run commands retained the all-extras frozen environment through UV_NO_SYNC/UV_FROZEN settings. Build's sole argument adjustment directed artifacts outside the repository. Formatting and mypy cache locations were external. The attempted pytest cache redirection misparsed Windows backslashes; its resulting exception is recorded below.

At the later token-continuation, the temporary environment directory remained but its Python executable was absent. Earlier command results and build artifacts remained available; code and lock hashes remained unchanged. The cause of interpreter loss is unknown. This blocks the later installed-package inspection, not the already executed baseline. No unsupported claim of current environment usability is made. [PREPARATION-FAILURE.md](PREPARATION-FAILURE.md) records the exact blocked command, evidence, classification, and safe next action.

## Prioritized deduplicated findings

The IDs below map to the original reports. Every role report contains exact line evidence, confidence, impact, checks/limits, and a self-contained remediation agent prompt with scope, constraints, acceptance criteria, and verification commands. Coverage findings TC-01/TC-02 overlap the first four defects and are incorporated into their remediation rather than counted twice.

| Priority / ID | Classification and confidence | Strongest evidence and impact | Remediation direction |
| --- | --- | --- | --- |
| **P1 / BL-1** | Confirmed eligibility defect; high | `src/etf_advisor/domain/screening.py:403-490,590-644`; `domain/construction.py:534-550`. Fee provenance 30 days old passes a 24-hour window while the document/category remain current; recomputed construction is ready and selects SPY. | Validate each consumed canonical field against the bundle's checkpointed check time, age, and future tolerance; preserve attribution and fail closed. [Full prompt and reproduction](business-logic-reviewer.md). |
| **P1 / BL-2** | Confirmed source-normalization defect; high | `src/etf_advisor/data/yahoo_research.py:215-219,253-268,319-351`; `domain/screening.py:548-552`. Malformed holding/sector rows are dropped; a surviving 10% holding becomes available top-ten concentration, and malformed energy becomes absent/zero. Production screening returns ready/pass and `sector_exclusions_clear`. | Preserve partial/malformed exposure data as unavailable/incomplete; never derive affirmative eligibility from dropped rows. Retain explicit zeros and distinguish legitimate short lists. [Full prompt and reproduction](business-logic-reviewer.md). |
| **P2 / SEC-01** | Confirmed explanation-safety defect; high | `src/etf_advisor/explanation/models.py:50-70,500-505`; `graph/nodes.py:280-283`. Otherwise valid responses containing “Please buy SPY.”, passive recommendations, and a future-outperformance assertion pass. The production node reaches human review with the instruction. | Harden ordinary prohibited wording and add benign/negated controls through generation and restored review. Do not claim general semantic entailment. [Full prompt and reproduction](security-reviewer.md). |
| **P2 / ARCH-01** | Confirmed review-integrity defect; high | `src/etf_advisor/dashboard.py:332-343,355-371`. Policy-only interrupt equality is conditional on construction presence. A valid $90,000 policy can replace the displayed $25,000 policy. Root also confirmed that removing all four ETF artifacts from a full interrupt is accepted while the sealed checkpoint retains them. | Compare policy and optional-artifact presence with authoritative checkpoint values before branching; recompute from checkpointed inputs. [Full prompt](architecture-reviewer.md), [independent stronger reproduction](TARGETED-VERIFICATION.md). |
| **P2 / PERF-01** | Confirmed request-amplification defect; high | `src/etf_advisor/rag/chroma_store.py:72-83,110-120`; `rag/hybrid.py:39-41`. A fake collection count of 50,000 causes `n_results=50000` for a requested limit of five; filtering occurs afterward. | Bound eligible legacy retrieval before top-K ranking while preserving exclusion of any staged/versioned record. Simply capping the pre-filter query is unsafe. [Full prompt and reproduction](performance-reviewer.md). |
| **P2 / TC-03** | Confirmed verification gap, not a proven store defect; high | `tests/test_neo4j_store.py:24-82,222-234`; `tests/test_dashboard.py:58-75,872-899`; `tests/test_revision.py:379-403`. Fakes establish intended calls but cannot execute actual Cypher or prove PostgreSQL serialization/commit/reconnect behavior. | Add a separate opt-in disposable-store contract suite; retain a service-free default baseline. [Full prompt and scope](test-coverage-reviewer.md). |
| **P2 / CQ-01** | Maintenance debt, not a runtime-routing failure; high for local reachability | `src/etf_advisor/graph/workflow.py:242-243`; `graph/nodes.py:360-365`; `graph/revision.py:541-548`. One router is orphaned; the legacy non-approval helper branch cannot be reached through the registered graph. | Remove or clarify superseded helpers in a narrow cleanup, preserving current typed outcomes and approval wording. [Full prompt](code-quality-reviewer.md). |
| **P2 / dependency footprint** | Maintenance debt; high for no current consumer, medium for removal suitability | `pyproject.toml:37,39`; `uv.lock:959-966,1451-1464`. langchain-chroma and neo4j-graphrag are declared, while current adapters use raw Chroma and Neo4j clients. No present source/test/docs consumer was found. | Verify planned consumers, then remove at most one unused wrapper per verified change, reviewing the full transitive diff. This is not a vulnerability claim. [Full prompt and rollback procedure](dependency-reviewer.md). |

P1 is reserved here for affirmative eligibility based on stale or incomplete evidence. The P2 safety/presentation issues still retain human review and do not demonstrate an executed trade or remote exploit. The performance probe proves amplified request size, not measured production latency. Maintenance and test gaps are not misrepresented as confirmed financial-output defects.

## Cross-cutting themes and remediation order

1. **Repair evidence completeness and freshness first (BL-2, BL-1).** Canonical shape/equality cannot recover information silently discarded by a parser, and document freshness cannot establish every field's freshness. Add the TC-02 boundary and mixed-data regressions with each narrow fix.
2. **Close explanation and presentation gaps (SEC-01, ARCH-01).** Strengthen the prohibited-language regression corpus and enforce artifact presence/equality even when the interrupt omits construction. Add TC-01 cases through direct validators, graph nodes, and restored review. A valid seal on state alone does not establish that the displayed interrupt matches it.
3. **Bound legacy retrieval (PERF-01).** Preserve fail-closed staged-record exclusion and ranking. Any live-data migration must be a separately scoped, explicit operation.
4. **Add focused disposable-store evidence (TC-03).** PostgreSQL close/recompile/restore with receipt identity and zero unintended replay, then actual Neo4j activation/rollback and Chroma filtering, offer justified value. Do not start services during this audit or turn Yahoo/model endpoints into test prerequisites.
5. **Perform low-risk cleanup and dependency hygiene separately (CQ-01, dependency footprint).** Remove one obsolete path or dependency at a time. Resolve package currency before selecting any concrete upgrade target; do not blanket-upgrade or treat absence of reported CVEs as comprehensive assurance.

All remediation prompts retain deterministic finance arithmetic, source provenance, replaceable adapters, JSON-safe state, explicit retries, human review, sanitized errors, and the prohibition on financial writes. They propose future work only; none was implemented during the audit.

## YahooResearchAdapter: refactor later

**Decision: later for a broad refactor; targeted parsing correctness fixes now.** Architecture, performance, business logic, and code quality reached the same conclusion. The class is approximately 230 lines, with a roughly 93-line record-construction method. It has a coherent purpose, an explicit raw-data structure, module-level parsers, and injected ticker/clock/sleeper boundaries. Size alone does not establish a defect or measured six-symbol latency problem.

BL-2 justifies making parsing completeness explicit and covering it with regression tests immediately in a future fix. A wider rewrite could obscure source timestamps, unit conversions, retry behavior, and missingness while revision/lifecycle work is active. Consider extracting shared pure normalization or precise retry mechanics after correctness tests, or when another provider/schema creates a demonstrated need. Preserve differences between the legacy and rich adapters rather than merging superficially similar loops.

## Unresolved risks, blocked checks, and planned scope

- **Package currency: unresolved.** `uv pip list --python <external interpreter> --outdated` failed because that interpreter was absent. WindowsApps Python and native PowerShell registry fallbacks were interrupted without usable current-version rows. Direct and transitive outdated counts are unknown, not zero. No dependency version was changed to repair the environment. Exact failures and follow-up are in [dependency-reviewer.md](dependency-reviewer.md) and [PREPARATION-FAILURE.md](PREPARATION-FAILURE.md).
- **Security dependency coverage: limited.** Three official maintainer advisory ranges were checked against locked LangGraph/checkpoint versions without establishing an affected package. This is not an exhaustive vulnerability scan; see the primary advisory links in the dependency report.
- **Optional Vulture: skipped because absent.** No scanner was installed. Configured Ruff and strict mypy did run and pass.
- **Real stores and live data: intentionally not exercised.** No PostgreSQL/Neo4j/Chroma transactions, query plans, live provider/Yahoo behavior, production load, broad fuzzing, browser security audit, or financial performance validation was performed. No quantitative branch-coverage claim is made.
- **General semantic truth remains unresolved.** Structural citations, numeric-token membership, and regex safety do not prove source truth, unit binding, every paraphrase/language, or general entailment. The identified ordinary prohibited statements are concrete defects within accepted scope, not a demand to solve all semantics.
- **Long lineages:** the performance role measured expected local growth through 25 policy revisions; it did not find a current latency blocker. Evidence-heavy PostgreSQL storage and long-lived histories remain unmeasured. Do not remove integrity validation as a speculative optimization.
- **Planned #41/#42/#43:** retention/expiry/prune/atomic whole-thread deletion, richer revision/retry/lifecycle UI, and iteration-wide acceptance remain unfinished by design. Authentication, concurrent multi-user review, and protection against database administrators are outside the local prototype's accepted scope. No absence of these features was scored as a new regression.

## Final verification and write-scope exception

Final verification reused the recorded successful baseline and the new, justified offline probes; unchanged gates were not repeated. Source and test inputs did not change. Specialty probes independently reproduced the eligibility and safety failures; the coordinator additionally reproduced full-artifact omission at presentation. Performance probes used injected fakes and a small in-memory lineage. Probe-harness failures are reported in their role reports and are not code defects.

The final [workspace verification](workspace-verification.json) compares SHA-256 for **all 131 initially tracked/nonignored files** with [starting-files.json](starting-files.json). There are **zero changes or missing files**, no tracked diff, no staged diff, and the commit remains c25865f. `git diff --check` passes. All nonignored new files are inside this exact run directory.

Ignored-file inspection identifies two unexpected directories outside the permitted report directory:

| Unexpected output | Cause and evidence | Disposition |
| --- | --- | --- |
| `.venv/` — 17 files | Architecture's initial `uv run --no-sync python -` created an incomplete default environment before the external interpreter path was supplied. The probe failed with missing langgraph. Full file inventory is in [architecture-reviewer.md](architecture-reviewer.md). | Preserved; no delete or revert performed. |
| `UsersburhaAppDataLocalTempagents-lab-audit-20260906-071454Z-pytest/` — four files | Baseline pytest's intended external cache setting lost Windows backslashes during option parsing and became a repository-relative cache path. | Preserved; no delete or revert performed. |

These 21 generated files are audit execution errors, not pre-existing user work or application defects. They do not change the 360-test result, but they **violate the report-only write constraint**. The explicit instruction to identify unexpected changes rather than delete/revert them was followed after discovery. Therefore the deliverables are present and the baseline gates passed, while strict audit completion/compliance remains unmet. No source or dependency files changed, and no user work was overwritten. No inspection query remains running.

## Seven independent reports and supporting evidence

1. [Security reviewer](security-reviewer.md)
2. [Architecture reviewer](architecture-reviewer.md)
3. [Test coverage reviewer](test-coverage-reviewer.md)
4. [Performance reviewer](performance-reviewer.md)
5. [Business logic reviewer](business-logic-reviewer.md)
6. [Code quality reviewer](code-quality-reviewer.md)
7. [Dependency reviewer](dependency-reviewer.md)

Supporting records: [Preparation](PREPARATION.md), [supplemental preparation failure](PREPARATION-FAILURE.md), [baseline exit codes](baseline-results.json), [starting state](starting-state.json), [starting hashes](starting-files.json), [coordinator reproduction](TARGETED-VERIFICATION.md), [final workspace verification](workspace-verification.json).
