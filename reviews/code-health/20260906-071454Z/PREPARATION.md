# Preparation and baseline evidence

- Audit run: 20260906-071454Z (UTC).
- Checked-out revision: c25865f84207ae9c7c89b4af1d339407a5d4b614, merge PR #45.
- Starting branch: DETACHED HEAD, not main. No upstream exists. HEAD equals the existing local origin/main reference (0 ahead / 0 behind). No remote fetch or branch change was performed; remote freshness is not asserted.
- Initial git status was empty, with no changed files. starting-state.json was captured immediately after creating the report directory, so its `?? reviews/` entry is audit output, not pre-existing user work.
- Python: 3.13.14. uv: 0.9.7 (0adb44480 2025-10-30).
- Read order completed: AGENTS.md, wishlist.md, product vision, system architecture, accepted ADRs 0001-0016, iteration 017.
- Active scope: #40 revision routing/replay implemented; #41 lifecycle, #42 interactive dashboard controls, #43 full iteration acceptance remain planned. This maintenance review is not product-phase acceptance.

## Environment and writes

`uv sync --all-extras --frozen` passed using UV_PROJECT_ENVIRONMENT=C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv. Subsequent baseline commands set UV_NO_SYNC=true and UV_FROZEN=true to keep that exact environment, including all extras. Ruff and mypy caches were directed outside the repository, with PYTHONDONTWRITEBYTECODE=1. The pytest cache override was intended to be external but its Windows backslashes were consumed while parsing PYTEST_ADDOPTS, producing the unexpected repository cache directory described below. Build output used `uv build --out-dir C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-dist`: the sole command-argument adjustment was to avoid writing repository dist/ artifacts while performing the same sdist/wheel build.

Unexpected write-scope exception: the architecture reviewer's first `uv run --no-sync python -` probe, before receiving the external interpreter path, created an ignored local `.venv/` containing 17 files. The probe failed with ModuleNotFoundError for langgraph. The directory was preserved, not deleted or reverted, under the explicit instruction to report unexpected changes. Subsequent probes used the external frozen interpreter. This is a supplemental probe environment failure, not a failed required baseline gate. Final verification must preserve this exception; strict reports-only audit completion cannot be claimed. A second unexpected output was found by the ignored-file inventory: `UsersburhaAppDataLocalTempagents-lab-audit-20260906-071454Z-pytest/` (four cache files), created by the baseline pytest command because its intended external Windows cache path was parsed as a relative path. It is also preserved without deletion. The 360-test result is unaffected. Future commands must use slash-normalized external cache paths or disable the pytest cache provider.

No Docker services were started. No live Yahoo, model-provider, database, or brokerage endpoints were called. Offline tests use injected fakes. Package setup/build and the separately reported dependency-index inspection are the permitted package-network operations. No staging, commit, push, PR, branch switch, reset, merge, rebase, automation changes, or version upgrades were performed.

## Required baseline

| Command | Result | Evidence |
| --- | --- | --- |
| uv sync --all-extras --frozen | PASS; 150 packages installed | [setup log](00-uv-sync.log) |
| uv run ruff format --check . | PASS; 110 files already formatted | [log](01-format.log) |
| uv run ruff check . | PASS | [log](02-ruff.log) |
| uv run mypy | PASS; 44 source files | [log](03-mypy.log) |
| uv run pytest | PASS; 360 passed in 28.08s | [log](04-pytest.log) |
| uv run etf-advisor evaluate-retrieval | PASS; 5 cases per strategy, attributable context metrics | [log](05-retrieval.log) |
| uv run etf-advisor evaluate-explanations | PASS; 8/8 curated cases | [log](06-explanations.log) |
| uv build (external --out-dir) | PASS; sdist and wheel built | [log](07-build.log) |
| docker compose config --quiet | PASS | [log](08-compose.log) |

All required checks ran in order. No baseline gate failed or was blocked. A later supplemental environment failure is recorded separately in PREPARATION-FAILURE.md. Supplemental review probes and dependency findings are separately classified in specialty reports. Passing finite test/evaluation cases is not proof that all financial safety properties hold.

## Direct dependency declarations

pyproject.toml and uv.lock are authoritative; no requirements.txt was used.

- Python: >=3.12,<3.14.
- Build: hatchling>=1.27.
- Core: langgraph>=1.1; pydantic>=2.11; pydantic-settings>=2.10; typer>=0.16.
- checkpoint extra: langgraph-checkpoint-postgres; psycopg[binary,pool].
- dashboard extra: streamlit.
- observability extra: langsmith.
- providers extra: langchain-ollama; langchain-openrouter.
- rag extra: chromadb; langchain-chroma; neo4j; neo4j-graphrag; yfinance.
- dev group: mypy>=1.17; pytest>=8.4; pytest-cov>=6.2; ruff>=0.12.

Version-specific and direct-versus-transitive observations belong to dependency-reviewer.md. starting-files.json retains SHA-256 hashes of all initially tracked and nonignored untracked files for final byte comparison.


## Continuation environment observation

The user resumed work after a token pause later on 2026-09-06. At approximately 17:32 UTC, the external frozen environment directory still existed but its `Scripts/python.exe` was absent. Its disappearance was not explained by the available evidence. Earlier baseline results (07:16-07:18 UTC), build artifacts and all six completed role reports remained present. Repository code, dependency declarations and lockfile still matched all starting hashes. No environment repair, package upgrade, or baseline rerun was performed merely to replace those valid recorded results. The dependency role reports the initially blocked installed-package command and its read-only lock/registry fallback separately; do not mistake that supplemental prerequisite problem for a failed earlier baseline gate or imply that the temporary interpreter is currently usable.

