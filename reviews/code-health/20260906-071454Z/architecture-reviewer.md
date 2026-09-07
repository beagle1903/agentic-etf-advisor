# Architecture review

- Reviewed checkout: `c25865f` (PR #45 merge), including changes since `a876384` (2,160 insertions / 114 deletions across 20 files).
- Scope: independent audit only. No source, tests, dependency declarations, lockfiles, configuration, or project documentation were edited. Baseline commands belong to the coordinator; this report does not independently declare those gates passing.
- Result: one confirmed P2 finding; no confirmed P0/P1 architecture finding. Accepted but unfinished lifecycle/UI work is listed separately below.

## Confirmed finding ARCH-01 — P2: policy-only interrupt bypasses checkpoint equality

**Confidence:** high; reproduced offline against the checked-out code and coordinator's frozen environment.

**Affected locations:** `src/etf_advisor/dashboard.py:332-343`, `src/etf_advisor/dashboard.py:355-371`, `src/etf_advisor/dashboard.py:406`; related schema checks at `src/etf_advisor/dashboard.py:94-140`.

**Evidence:** `review_payload` validates the ledger and revision ID, but its checkpoint-versus-interrupt comparisons and deterministic recomputation are inside `if construction is not None`. The default policy-only review therefore accepts a well-formed policy from another profile in its interrupt while retaining the original valid sealed checkpoint. The outer revision digest does not cover `__interrupt__`, so it cannot catch this mismatch. Nested evidence/screening/construction are internally required to appear together, but their presence is not independently compared with checkpoint state outside that branch.

**Impact:** a corrupted/replacement interrupt can display amounts the human is not actually approving. An offline graph with $25,000 initial investment accepted an interrupt policy independently calculated for $90,000, with the same revision ID. Approval remains bound to the original graph state: this is a human-review correctness defect, not demonstrated trade execution, source compromise, or a production remote exploit. It affects implemented policy-only behavior and is not the deferred revision-form work.

**Minimal reproduction:** run the following via standard input using the frozen Python interpreter, with `PYTHONDONTWRITEBYTECODE=1`; no project test/source file is needed.

```python
from copy import deepcopy
from types import SimpleNamespace
from langgraph.checkpoint.memory import InMemorySaver
from etf_advisor.graph.workflow import build_graph
from etf_advisor.dashboard import review_payload
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.policy import calculate_policy

profile = dict(horizon_years=12, risk_tolerance="moderate", objective="balanced",
               max_drawdown_pct=25, initial_investment_usd=25000,
               recurring_monthly_usd=500, excluded_sectors=[])
graph = build_graph(checkpointer=InMemorySaver())
state = graph.invoke({"profile": profile},
                     {"configurable": {"thread_id": "architecture-offline-repro"}})
value = deepcopy(state["__interrupt__"][0].value)
value["draft_policy"] = calculate_policy(InvestorProfile.model_validate(
    {**profile, "initial_investment_usd": 90000})).model_dump(mode="json")
state["__interrupt__"] = (SimpleNamespace(value=value),)
result = review_payload(state)
print(result["draft_policy"] != state["draft_policy"])  # Actual: True
```

Observed output: `mismatched_policy_accepted: True`; checkpoint initial total `25000.0`, displayed initial total `90000.0`. No network, provider, database, or brokerage endpoint was used.

**Remediation agent prompt:**

> Fix policy-only and optional-artifact checkpoint/interrupt consistency in `src/etf_advisor/dashboard.py`, with focused regressions in `tests/test_dashboard.py`. Before rendering any review, require the policy to match the authoritative checkpoint and recompute it from the checkpointed profile; compare presence of every optional artifact against checkpoint state before branching into construction validation. Preserve current construction/explanation revalidation, educational behavior, typed revision routing, and replaceable adapters. Do not infer missing lineage, silently repair mismatches, introduce external calls, change financial rules, or broaden scope into Issue #42. Acceptance: an untouched policy-only review still renders and approves; substituting a valid policy for a different cash amount or risk profile fails without controls; removing all optional artifacts from a full review fails; existing restored construction and explanation cases remain valid. Verify with `uv run pytest tests/test_dashboard.py tests/test_revision.py`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy`, then the full required offline baseline (`uv run pytest`, both evaluation CLI commands, `uv build`, `docker compose config --quiet`).

## Architecture checks and positive evidence

| Area | Inspection and assessment |
| --- | --- |
| Project scope | Read AGENTS, wishlist, vision, system architecture, accepted ADRs 0001/0002/0004/0006/0007/0008/0014/0015/0016 and Iteration 017. Assessed #40 as implemented, #41–43 as pending. |
| JSON state | `domain/revision.py:54-65` hashes canonical JSON with `allow_nan=False`; audit models reject extra fields and serialize through JSON mode at `graph/revision.py:61-64`. Domain outputs are serialized before graph state. Inspected malformed-resume and round-trip regressions. |
| Revision routing | `domain/revision.py:174-210` validates every patch before selecting the earliest ordered feedback class. `graph/revision.py:549-577` preserves upstream artifact identities, clears the contracted downstream set, and routes to the chosen stage. Workflow edges use current status, preventing a retained parent bundle from overriding a fresh blocker. |
| Checkpoint/interrupt consistency | `graph/revision.py:470-513` recomputes policy, screening, construction and explanation before interrupt/resume; `dashboard.py:315-406` also revalidates presentation. ARCH-01 is the identified conditional coverage gap. |
| Operation identity/input/output | `graph/revision.py:67-233` checks thread/revision IDs, attempt ordering, manifests, canonical inputs, output references/digests and unchanged inherited identities. `graph/revision.py:437-468` independently validates reused evidence/explanations. Source identity is checked in `rag/evidence.py:224-261`, including explicit local synthetic identity and rejection of mixed/partial identity. |
| Ambiguous attempts / authorization | Prepare and execute are separate nodes; workflow rejects unsafe durability overrides. `graph/revision.py:370-435` requires a one-use runtime permit for execution; restored started receipts cannot silently recreate permits. `begin` validates explicit retry against the current last non-successful receipt and retains previous attempts. OpenRouter retries are disabled. This does not establish exactly-once remote execution after a lost acknowledgement. |
| Audit lineage | Parent triggering decision and child's eventual review decision are separate; profile and unchanged artifacts retain IDs; fresh runs cannot overwrite existing lineage. Injected clock and identifier interfaces cover runtime nondeterminism. Artifact collisions fail closed. |
| Side-effect interfaces | Retrieval/provider protocols, injected clock/identifiers and checkpoint-store context-manager boundary keep adapters replaceable. Pure policy, screening, construction and revision planning do not call stores or providers. Dashboard is the composition root for opt-in concrete adapters. |
| Snapshot consistency | Chroma stages digest/version-scoped IDs and verifies metadata before graph activation. Neo4j's single parameterized publication query owns the active pointer; legacy retrieval explicitly excludes staged versioned records. Snapshot manifests and explicit-version payload reuse support failure recovery. Hybrid context reads source-specific relationships. Live transaction/concurrency semantics were not exercised. |
| Dependency direction | Domain screening/construction depend on evidence contracts housed in `rag/evidence.py`, which itself references profile models and a retriever protocol. This is an organizational coupling worth revisiting if packages grow, but no concrete import cycle or mandatory live adapter dependency was found. No defect is assigned solely for folder direction. |
| Cohesion / duplication | The ~586-line revision runtime concentrates integrity, artifacts, retry state and routing; `validate_revision_state` (~149 lines) is the highest change-risk concentration. Repeated domain recomputation at explanation/review/presentation boundaries is intentional trust-boundary validation, not automatically redundant logic to delete. Extracting helpers may become useful with #41, but size alone does not justify a defect. |

## YahooResearchAdapter decision: refactor later

`data/yahoo_research.py` is roughly 401 lines; `YahooResearchAdapter` occupies lines 40–269. It has a cohesive purpose: collect Yahoo inputs and convert them to the versioned research contract. Transport/factory, clock and sleeper are injectable. `_RawResearch` separates collection from record construction, and module-level helpers already separate scalar/exposure parsing. `_build_record` is about 94 lines because it explicitly maps every field and provenance, which helps review financial units and missingness.

There is a modest duplication opportunity between `_retry` (159–174), `_fetch_info_snapshot` (138–156), and retry behavior in `data/yahoo.py`. Metadata retry intentionally refreshes the ticker, so a generic extraction must preserve that behavior. Do not refactor merely because the adapter is a known candidate. Fix any independently confirmed parsing/provenance defects first; consider a bounded pure-normalization/transport extraction when adding another data source or changing holdings/sector schemas. That keeps the immediate revision/lifecycle work focused and avoids obscuring sensitive unit/freshness behavior with unrelated structural churn. This is a maintenance recommendation, not a second P2 finding.

## Planned scope, hypotheses and limitations

- **Planned #41:** `checkpoint.py` currently exposes setup/open only. ADR 0016's 30-day retention, meaningful-write timestamps, expiry display, preview/prune, exact-token confirmation and atomic whole-lineage deletion are not implemented. Iteration 017 explicitly marks them pending; their absence is not a completed-slice regression. Future tests should prove reads do not extend expiry and deletion includes checkpoint writes as well as lineage, using one captured clock and no partial deletes.
- **Planned #42:** rich typed feedback/reject-disposition/retry controls, adapter reattachment, lineage inspection and lifecycle controls remain pending. Existing adapter approval is supported; legacy free-text edit/reject fails closed. This is disclosed current scope, not evidence of a new architectural regression.
- **Planned #43:** iteration-wide live-store/acceptance evidence is pending. Existing in-memory persistence-failure tests cannot prove actual PostgreSQL transactional behavior; an isolated temporary-store integration check would add value when #41 is implemented. No service was started for this audit.
- Snapshot publication Cypher was inspected statically; rollback, concurrent publication, and real Chroma metadata behavior were not re-executed. In-flight pointer changes may return the snapshot selected at query start; source-specific relationships retain the relevant field context. No mixed financial snapshot defect was confirmed from this inspection.
- Scaling of full-ledger validation/digest/deepcopy is a hypothesis for long-lived lineages, not a measured regression here. No external or destructive load test was run.
- General semantic entailment, authentication, authorization, concurrent reviewers and database-administrator tampering remain acknowledged non-goals/limitations. No exactly-once external effect or production readiness is claimed.

## Verification and audit write-scope exception

The first targeted command used `uv run --no-sync python -`. It failed before importing application code with `ModuleNotFoundError: No module named 'langgraph'` and unexpectedly created an ignored local `.venv`. This is an audit execution error, not a code defect or failure of the coordinator's subsequently successful frozen sync. The probe was then run successfully using the coordinator's external frozen interpreter at `C:/Users/burha/AppData/Local/Temp/agents-lab-audit-20260906-071454Z-venv/Scripts/python.exe` with `PYTHONDONTWRITEBYTECODE=1`. No baseline gate was needlessly repeated.

The `.venv` was preserved and reported to the coordinator; it was not deleted or reverted. Its 17 files are:

```text
.venv/.gitignore
.venv/CACHEDIR.TAG
.venv/pyvenv.cfg
.venv/Lib/site-packages/_virtualenv.pth
.venv/Lib/site-packages/_virtualenv.py
.venv/Lib/site-packages/__pycache__/_virtualenv.cpython-313.pyc
.venv/Scripts/activate
.venv/Scripts/activate_this.py
.venv/Scripts/activate.bat
.venv/Scripts/activate.csh
.venv/Scripts/activate.fish
.venv/Scripts/activate.nu
.venv/Scripts/activate.ps1
.venv/Scripts/deactivate.bat
.venv/Scripts/pydoc.bat
.venv/Scripts/python.exe
.venv/Scripts/pythonw.exe
```

Therefore this specialty cannot assert strict report-only filesystem compliance. Application/dependency files were not changed, and no git mutation or external service call was performed. The coordinator must preserve this exception in final synthesis alongside baseline results and overall repository verification.
