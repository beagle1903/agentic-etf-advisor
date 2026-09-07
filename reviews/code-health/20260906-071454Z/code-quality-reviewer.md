# Code quality review

- Run: `20260906-071454Z`.
- Reviewed revision: `c25865f84207ae9c7c89b4af1d339407a5d4b614` (PR #45 merge), detached HEAD, no upstream; the commit equals the recorded `origin/main` with zero divergence. The checkout is not on branch `main`.
- Scope: audit only; this reviewer wrote only this report. Application files, tests, dependency declarations, lockfile, configuration, and project documentation were read-only.

## Result

No confirmed P0 or P1 code-quality finding. One P2 maintenance finding concerns obsolete workflow helpers left behind by the revision migration. It is not evidence of a production routing failure. Configured formatting, Ruff, and strict mypy passed. No unused imports were reported by the configured Ruff rules. Vulture is absent from the frozen environment and was skipped without installation; this is an optional check omission, not a blocked baseline gate.

## Checks performed and evidence

Read `AGENTS.md`, `wishlist.md`, product vision, current system architecture, accepted ADRs 0015 and 0016, then the highest iteration document, 017. Compared the implemented #40 slice against its stated boundaries. Reviewed PR #45's `a876384..HEAD` changed-file scope, including new domain/runtime revision contracts and identifier injection. Retention/deletion (#41), interactive revision controls (#42), and acceptance (#43) are explicitly planned work, not new regressions.

Inspected graph construction, nodes, revision runtime, profile/revision models, evidence contracts, both Yahoo adapters, checkpoint adapters, snapshot publication and persistence, and associated workflow/profile/revision tests. Used AST enumeration across every Python source and test module to locate long definitions and unreferenced names, then repository-wide `rg` call-site searches to distinguish actual unused helpers from framework registrations. This was a structural whole-tree scan plus focused source review, not a line-by-line correctness proof of all modules. Other specialty reports own financial arithmetic, provider safety, stores, test completeness, and dependency advisories.

Shared baseline evidence was read directly from this run's logs and [baseline-results.json](baseline-results.json). Gates were not repeated with unchanged inputs:

| Check | Result | Evidence |
| --- | --- | --- |
| `uv run ruff format --check .` | PASS: 110 files already formatted | [01-format.log](01-format.log) |
| `uv run ruff check .` | PASS: all checks passed | [02-ruff.log](02-ruff.log) |
| `uv run mypy` | PASS: 44 source files | [03-mypy.log](03-mypy.log) |
| Full test/evaluation/build/Compose baseline | All recorded exit codes zero | [baseline-results.json](baseline-results.json) |
| Vulture availability | OPTIONAL SKIP: `importlib.util.find_spec('vulture')` is `None` | Direct frozen-environment Python inspection |

The availability and AST checks used `C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv/Scripts/python.exe` with `PYTHONDONTWRITEBYTECODE=1`; no dependency was installed and no cache was written into the repository. If Vulture becomes an explicitly authorized dependency in a future task, its intended high-confidence check is `python -m vulture src/etf_advisor tests --min-confidence 100`; it was not executed here.

Framework callbacks were excluded from dead-code conclusions: Pydantic validators, Typer commands, context managers, and protocol methods have valid indirect invocation paths. An AST name-reference scan alone cannot establish dead code in this repository.

## CQ-01 — P2 maintenance: remove superseded workflow helper paths

- **Confidence:** High for repository-local reachability; no claim about undocumented downstream imports.
- **Affected lines:** `src/etf_advisor/graph/workflow.py:242-243`; `src/etf_advisor/graph/nodes.py:330-365`, especially `360-365`; current replacement/call sites are `src/etf_advisor/graph/workflow.py:205-212` and `src/etf_advisor/graph/revision.py:541-548`.
- **Evidence:** `route_after_construction` appears only at its definition in a repository-wide search excluding reports. Actual construction routing is the conditional function registered at workflow lines 205-212. `nodes.finalize_review` is called once, at revision line 545, and only when the enclosing condition has already established `decision.action == 'approve'`. Consequently its non-approval `needs_revision` return at nodes lines 360-365 is unreachable through the registered graph. Its docstring still describes all non-approvals as requiring revision, although the accepted runtime now distinguishes reject-and-close from typed revision requests.
- **Reproduction:** Run `rg -n 'route_after_construction|nodes.finalize_review' src tests`, then inspect the construction conditional and the `decide` approval condition. No runtime mutation or external dependency is needed.
- **Impact:** Maintainers can mistake obsolete helpers for active routing policy or edit the wrong path when adding #42 controls. This is maintenance debt, not an observed unsafe decision or failed baseline. The current graph uses the typed runtime correctly.
- **Remediation agent prompt:**

> In agents-lab, perform a narrowly scoped cleanup of superseded workflow helpers in `src/etf_advisor/graph/workflow.py`, `src/etf_advisor/graph/nodes.py`, and the approval message call site in `src/etf_advisor/graph/revision.py`. Remove the unused `route_after_construction` helper after confirming all repository references. Convert the approval-only message helper to a name and return contract that express its actual purpose, or otherwise remove its unreachable legacy non-approval branch. Preserve exact public graph outcomes, final approval wording, typed edit/reject routing, receipt behavior, and JSON state; do not implement deferred dashboard/lifecycle work or weaken review validation. If an external compatibility obligation is discovered, retain a documented compatibility wrapper rather than silently breaking it. Acceptance criteria: one authoritative construction-routing path, no misleading non-approval helper path, unchanged approve/edit/reject-close/reject-revise behavior, and no extra adapter calls. Verification: `uv run pytest tests/test_workflow.py tests/test_revision.py tests/test_revision_identifiers.py tests/test_dashboard.py`; `uv run ruff format --check .`; `uv run ruff check .`; `uv run mypy`; `uv run pytest`; both offline `etf-advisor evaluate-retrieval` and `etf-advisor evaluate-explanations`; `uv build`; `docker compose config --quiet`; `git diff --check`.

## Cohesion, size, duplication, and Yahoo refactor decision

**YahooResearchAdapter: refactor later.** Class size alone does not justify a broad rewrite. AST measurement puts the class at 230 lines (`data/yahoo_research.py:40-269`) and its largest method, `_build_record`, at 93 lines (`177-269`). Its operations all serve one coherent boundary: fetch one source contract and build provenance-bearing research fields. `_RawResearch` already separates raw collection from contract assembly; clock, ticker creation, and sleeping are injectable; parsers are module functions. There is no confirmed code-quality defect caused by this class size.

There is a reasonable later extraction opportunity: metadata retry loops overlap between `data/yahoo.py:156-176`, `data/yahoo_research.py:138-157`, and `159-175`; expense-ratio interpretation is duplicated at `data/yahoo.py:228-237` and `data/yahoo_research.py:362-369`. A shared parsing rule would reduce drift, but legacy versus research observation timestamps, missing-field semantics, and initial/fresh ticker behavior must remain distinct. Do not merge those semantics simply because the loops look similar. Address any confirmed data-correctness finding in the business/security reports through focused fixes first.

Optional future refactor prompt:

> After correctness fixes are complete, characterize both Yahoo adapters with injected tickers and sleepers, then extract only identical expense-ratio interpretation and retry mechanics into a small internal data helper if that reduces duplication. Preserve netExpenseRatio percentage units versus annualReportExpenseRatio fractions, explicit missing/error states, all field provenance, source-reported timestamps, fresh-ticker retry behavior, maximum attempt counts, and exception boundaries. Do not add live Yahoo calls, parallel network execution, new dependencies, or change the snapshot schema. Acceptance: identical canonical snapshot outputs and legacy observations for existing fixtures; identical call/backoff counts on success, transient failure, and exhaustion; explicit malformed/absent-field tests before shared conversion changes. Verify `uv run pytest tests/test_market_data.py tests/test_yahoo_research.py tests/test_data_quality.py tests/test_research_snapshot.py tests/test_snapshot_publication.py`, followed by Ruff formatting/check, mypy, full pytest, both offline evaluation commands, build, Compose config, and diff checks.

Other structural observations, not separately prioritized defects:

- `RevisionRuntime` is 328 lines (`graph/revision.py:255-582`), `validate_revision_state` 147 (`67-213`), and `build_graph` 198 (`graph/workflow.py:30-227`). They have substantial responsibilities, but the runtime's methods correspond to explicit transitions and the validation function centralizes cross-record invariants. Extracting cohesive validators later may help; splitting them by line count during active replay work could hide invariant ordering. No arbitrary maximum-length policy exists in the project.
- `YahooFinanceAdapter.fetch_source_documents` at `data/yahoo.py:60-61` has no repository call site. It is a small public convenience composition, not proven dead code for library consumers; it does not merit a removal defect by itself.
- Evidence provenance and candidate models duplicate normalization/identity validators (`rag/evidence.py:48-77` and `100-129`). Both actively validate trust boundaries. Shared pure predicates could reduce maintenance, but independent model validation should remain.
- `workflow.py:7` imports a LangGraph internal durability constant. The exact frozen version passes current gates; compatibility across future LangGraph upgrades needs the replay tests. This is dependency coupling to monitor, not evidence that the current code is broken.

## Limitations and final verification

No live Yahoo, provider, Neo4j, Chroma, PostgreSQL, or brokerage calls; no services, load tests, code changes, fixes, or package upgrades. No Vulture analysis, independent execution coverage measurement, proof of external API usage, or dynamic analysis of every branch. AST lengths count source lines including comments and blanks and are triage signals only. Ruff pass does not imply absence of unreachable functions or semantic bugs.

Final code-quality verification consists of the passing shared baseline plus read-only AST and exact call-site checks. No changed input or new gate failure justified repeating a gate. This specialty review is complete with an optional static-analysis skip and one low-urgency maintenance finding; overall audit completion and baseline status are determined in `SUMMARY.md` after all roles and repository-write verification finish.
