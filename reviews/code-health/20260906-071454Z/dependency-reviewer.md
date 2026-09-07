# Dependency reviewer

Audit revision: `c25865f84207ae9c7c89b4af1d339407a5d4b614`, detached HEAD equal to the existing local `origin/main` reference. Review completed during the 2026-09-06 UTC continuation in the original `20260906-071454Z` report directory. This is an audit, not an upgrade or product-phase completion.

## Scope and checks

Read AGENTS.md, wishlist, product vision, system architecture, relevant accepted ADRs 0006, 0011, 0015 and 0016, and active iteration 017 in that order. Inspected authoritative `pyproject.toml` and `uv.lock`, dependency consumers across source/tests/docs, Dockerfile, CI, and recent revision-routing commits. Lifecycle #41, interactive controls #42 and acceptance #43 remain planned, not dependency regressions.

The root's preserved [preparation evidence](PREPARATION.md) records successful frozen all-extras setup, Ruff format/lint, mypy, all 360 tests, both offline evaluations, packaging and Compose configuration. Those unchanged gates were not repeated. The currently missing external interpreter does not retroactively change those recorded results.

No source, tests, declarations, lockfile, configuration or project documentation were changed. No installs, upgrades, service starts or live Yahoo/model/database/brokerage requests were made. Only this report was written by this reviewer. Existing unexpected ignored directories documented in PREPARATION.md were preserved.

## Direct versus transitive inventory

Python is constrained to `>=3.12,<3.14` (`pyproject.toml:10`; matching `uv.lock:3`). Build requirement `hatchling>=1.27` (`pyproject.toml:2`) is separate from the application lock: no hatchling package record appears in uv.lock. Therefore the successful isolated build is evidence of current buildability, not evidence of an exactly locked build-tool graph.

| Direct category | Package | Locked version | Declaration line |
| --- | --- | --- | --- |
| Core | langgraph | 1.2.11 | 14 |
| Core | pydantic | 2.13.4 | 15 |
| Core | pydantic-settings | 2.15.0 | 16 |
| Core | typer | 0.27.1 | 17 |
| Checkpoint | langgraph-checkpoint-postgres | 3.1.2 | 22 |
| Checkpoint | psycopg[binary,pool] | 3.3.4 | 23 |
| Dashboard | streamlit | 1.62.0 | 26 |
| Observability | langsmith | 0.11.1 | 29 |
| Providers | langchain-ollama | 1.1.0 | 32 |
| Providers | langchain-openrouter | 0.2.8 | 33 |
| RAG | chromadb | 1.5.9 | 36 |
| RAG | langchain-chroma | 1.1.0 | 37 |
| RAG | neo4j | 6.2.0 | 38 |
| RAG | neo4j-graphrag | 1.19.0 | 39 |
| RAG | yfinance | 1.7.0 | 40 |
| Development | mypy | 2.3.1 | 45 |
| Development | pytest | 9.1.1 | 46 |
| Development | pytest-cov | 7.1.0 | 47 |
| Development | ruff | 0.16.4 | 48 |

Important transitive packages are `langchain-core 1.6.0` (`uv.lock:973-974`), `langgraph-checkpoint 4.2.0` (1049-1050), `langgraph-prebuilt 1.1.0` (1077-1078), `langgraph-sdk 0.4.3` (1090-1091), `ollama 0.6.2` (1511-1512), `openrouter 0.10.8` (1549-1550), `psycopg-binary 3.3.4` (1910-1911), and `psycopg-pool 3.3.1` (1939-1940). `langchain-core` is imported directly by revision/workflow modules but currently arrives through LangGraph's declared graph. This is a declaration-maintenance consideration, not a demonstrated installation failure.

All 150 non-project package records in the inspected lock use the official `https://pypi.org/simple` registry with distribution SHA-256 hashes; 19 are declared runtime/development dependencies and 131 are transitive. This universal-lock count differs from any one platform's installed package set. No Git branch or credential-bearing dependency URL was found. Most optional direct dependencies have no version lower/upper bound, but frozen installation still uses the lock; lack of upper bounds alone is not a current defect.

## Confirmed P2 maintenance finding: unused optional integration packages

**Severity:** P2 maintenance/footprint. **Confidence:** high for absence of current consumers; medium for eventual removal suitability. **Affected files:** `pyproject.toml:37` and `pyproject.toml:39`; package/dependency records `uv.lock:959-966` and `uv.lock:1451-1464`.

**Evidence and reproduction:** `rg -n 'langchain.chroma|neo4j.graphrag' src tests docs README.md wishlist.md pyproject.toml` finds only the two declarations. The implemented Chroma adapter calls `importlib.import_module("chromadb")` and `chromadb.HttpClient` at `src/etf_advisor/rag/chroma_store.py:29-35`; Neo4j uses `importlib.import_module("neo4j")` and the raw driver at `src/etf_advisor/rag/neo4j_store.py:197-203`. The reviewed architecture and active iteration specify no consumer of either integration package. The product's LangChain/graph-database intent does not require these particular wrappers.

**Impact:** every `--extra rag`/`--all-extras` setup resolves and installs two integration packages that current adapters do not call. neo4j-graphrag additionally introduces declared edges to fsspec, json-repair, pypdf, scipy and types-pyyaml. Actual exclusive removals require resolver inspection because other packages can share them. This increases maintenance and installation surface; no vulnerability or runtime failure is inferred.

**Actionable remediation prompt:** In a separately authorized maintenance change, inspect all source/test/docs and planned consumers of `langchain-chroma` and `neo4j-graphrag`. Remove one unused direct RAG declaration at a time, regenerate uv.lock using UV, and inspect the complete transitive diff; retain raw chromadb/neo4j APIs and every accepted retrieval/snapshot contract. If a real documented consumer exists, retain the package and document that specific consumer instead. Do not change financial behavior, call live services, or combine this with version upgrades. Acceptance: all current import paths and offline adapter tests work, only justified dependency edges disappear, and complete full-gate verification below passes with all extras. Commands: `uv remove --optional rag langchain-chroma`, review/test, then in a separate change `uv remove --optional rag neo4j-graphrag`, review/test; never run both before verifying the first. Roll back only that change's declaration/lock diff using its saved before-state, preserving unrelated user changes.

## Security and compatibility assessment

Three official maintainer advisories were checked against locked versions on 2026-09-06. These are targeted checks, not an exhaustive vulnerability audit:

- [GHSA-g48c-2wqr-h844](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-g48c-2wqr-h844) lists langgraph `<=1.0.9`, patched `1.0.10`; locked `1.2.11` lies outside that range. Its checkpoint-byte write-access prerequisite remains a relevant security boundary.
- [GHSA-mhr3-j7m5-c7c9](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-mhr3-j7m5-c7c9) lists langgraph-checkpoint `<4.0.0`, patched `4.0.0`; locked `4.2.0` lies outside that range. The described cache/pickle prerequisites were not enabled by the inspected workflow compile call.
- [GHSA-wwqv-p2pp-99h5](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-wwqv-p2pp-99h5) concerns checkpoint JSON deserialization before `3.0`; locked checkpoint `4.2.0` lies outside that range.

No affected locked dependency is confirmed by these three checks. This does not certify the complete lock as vulnerability-free. No new scanner was installed; package-outdated metadata is not a substitute for a vulnerability scan.

Upgrade-sensitive boundaries include the private `langgraph._internal._constants.CONFIG_KEY_DURABILITY` import (`src/etf_advisor/graph/workflow.py:7`) used by the synchronous receipt guard (98-99), checkpoint serialization/restoration, provider structured-output and retry parameters, and Yahoo scalar units/field shapes. Current frozen gates pass; future incompatibility is a risk, not a confirmed regression. LangGraph/checkpoint changes require explicit replay/ambiguous-attempt regression verification. Database client/server compatibility and real provider behavior were not exercised. CI currently installs base+dev dependencies (`.github/workflows/ci.yml:22`), so this run's all-extras evidence is broader than that CI job.

## Outdated inspection and environment limitations

The required command was attempted exactly against the root-provided frozen environment:

```text
uv pip list --python C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv/Scripts/python.exe --outdated
exit 1: error: No virtual environment or system Python installation found for path `C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv/Scripts/python.exe`; run `uv venv` to create an environment
```

**Classification:** blocked supplemental environment inspection: the external directory and metadata remain, but Scripts/python.exe is absent after the long pause. No cause is established. `uv pip list --help` provides no `--path` alternative. A system-Python registry fallback resolved to the WindowsApps alias, produced no Python process/output, and was interrupted without an install. These failures are distinct from the earlier successful baseline and from code defects.

The fallback read locked name/version records in native PowerShell and requested only official `https://pypi.org/pypi/<name>/json` metadata, with 16 workers and an 8-second per-request timeout. It did not install, resolve a replacement graph, or edit the lock. The command remained active for more than three minutes without returning its aggregate JSON and was interrupted (exit 1, empty stdout/stderr) at approximately 17:43 UTC. Per-request timeouts did not bound the complete metadata collection/parsing pipeline. The failure's precise network/runtime cause is not established.

**Final outdated-inspection result, 2026-09-06 17:43 UTC:** incomplete/blocked. Zero usable current-version rows were returned by the native package-index pipeline; none of the 19 direct runtime/dev declarations or transitive packages can be certified current or outdated from this attempt. The count of confirmed outdated direct packages is **unknown**, and the count of confirmed outdated transitive packages is **unknown**, not zero. The locked inventory above remains authoritative. Official PyPI JSON pages for langgraph and pydantic were reachable through the browser research service, but their truncated displayed content did not provide a reliable full version comparison, so no latest version is asserted.

Exact native fallback pipeline (read-only):

```powershell
$packages = @()
$packageName = $null
foreach ($line in Get-Content uv.lock) {
    if ($line -match '^name = "([^"]+)"') { $packageName = $Matches[1] }
    if ($line -match '^version = "([^"]+)"' -and $packageName -and $packageName -ne 'agentic-etf-advisor') {
        $packages += [pscustomobject]@{Name=$packageName; Locked=$Matches[1]}
    }
}
$packages | ForEach-Object -Parallel {
    try {
        $item = Invoke-RestMethod -Uri ('https://pypi.org/pypi/'+$_.Name+'/json') -TimeoutSec 8
        [pscustomobject]@{Name=$_.Name; Locked=$_.Locked; Latest=$item.info.version; Python=$item.info.requires_python}
    } catch {
        [pscustomobject]@{Name=$_.Name; Locked=$_.Locked; Error=$_.Exception.Message}
    }
} -ThrottleLimit 16 | ConvertTo-Json -Depth 3
```

Safe next action: in a separately authorized environment-recovery task, restore an external interpreter from the unchanged lock, then rerun the original read-only `uv pip list --outdated` command. Alternatively query a small number of package records with a whole-process deadline and streaming results. Do not change declared or locked versions to fix this inspection failure. A future latest-version response must still be checked for Python constraints, platform wheels, release notes and the complete dependency graph; latest metadata alone cannot prove compatibility. No further fallback or baseline repeat was attempted during this review.

## Future one-at-a-time UV upgrade procedure

These commands are proposals only; none were executed. First select a concrete target from verified current metadata and release notes. From a separate authorized clean maintenance change, save the exact starting pyproject/uv.lock contents outside the repository and record their hashes; preserve unrelated changes. For each single selected package use `uv lock --upgrade-package "<package>==<verified-target>"`, inspect all induced transitive changes, then `uv sync --all-extras --frozen`. For example, choose **one** of langgraph, streamlit, yfinance or a confirmed affected transitive package and substitute its verified target; do not run a blanket `uv lock --upgrade`. If the target exceeds the declared range, first make and review the narrow declaration change. This follows [UV locking and syncing guidance](https://docs.astral.sh/uv/concepts/projects/sync/).

Acceptance for each separate upgrade: retain JSON graph state, exact receipt identity/retry semantics, source provenance, deterministic arithmetic, fail-closed safety and redacted errors; targeted relevant regressions and the full ordered gates below pass. On failure, do not advance to a second upgrade: restore only the upgrade-owned pyproject/lock changes from the saved before-state, `uv sync --all-extras --frozen`, and recheck the failing gate. Never reset or overwrite unrelated work.

```text
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv run etf-advisor evaluate-retrieval
uv run etf-advisor evaluate-explanations
uv build
docker compose config --quiet
```

Future audit execution must again direct the environment/caches/build output outside the repository and set `PYTHONDONTWRITEBYTECODE=1`; disable pytest's cache provider or use a slash-normalized external path. Upgrade implementation can use its normal authorized outputs. Do not start Docker or call live financial/provider services to verify these offline gates.

## Coverage limits and final disposition

No P0/P1 dependency defect was established. One P2 dependency-footprint follow-up is confirmed. Full advisory coverage, artifact signatures/provenance beyond lock hashes, actual client/server integration, Python 3.12 runtime, other operating systems, and minimum-version compatibility were not evaluated. The optional dependencies' minimum compatible versions cannot be inferred from a passing latest locked environment. Report completion does not supersede PREPARATION.md's unexpected-write exceptions or certify a vulnerability-free baseline.
