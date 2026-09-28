# Issue 71: Real-store critical-path verification

- Status: implementation self-reviewed and all local gates passed; PR/CI and coordinator review pending.
- Issue: https://github.com/beagle1903/agentic-etf-advisor/issues/71
- DESIGN_READY: https://github.com/beagle1903/agentic-etf-advisor/issues/71#issuecomment-5865798979
- Owner: `implementation_worker`, `gpt-6-sol`, medium; ordinary verification/documentation
  within established ADR 0027 contracts, selected by the coordinator.
- Authorization: user authorized selecting/starting the next task; the delegated Issue71 request
  authorizes this scoped coverage, verification and PR delivery. Merge remains a user decision.
- Baseline: clean `main` at `5b182997f96bb9f40dc4f4782a93b01a938c1603`; GitHub confirms
  lossless PR #76 and official BND/connection setup PR #80 merged.

Issue71 was created `2026-09-22T08:05:23Z`, before ADR 0026 adoption on September 26. Its historical
exemption applies; no retrospective ledger/adoption or ledger phase commands are used. The complete
capsule freezes I71-NUM/PATH/FAIL/ISOLATE/OFFLINE/STATE and AC71-1 through AC71-6. No financial,
numeric, persistence/replay, provenance, activation, JSON-state, adapter or workflow/configuration
contract changes are authorized or made.

## Merged evidence and confirmed gaps

The 39 real-store cases already on the baseline cover canonical lossless publication and store
readback, exact numeric tokens, evidence/screening/construction, PostgreSQL reopen, dashboard
recomputation, manifest/content mutation rejection, activation rollback/CAS, historical retry,
reactivation/shrinking history, concurrent immutable Chroma staging, generic graph guards and
catalog contention. Issue70/79 iteration records retain those deliveries' evidence; ADRs 0027/0028
define their existing contracts. This ticket reuses those tests and does not duplicate them.

Two gaps remained: the Chroma mutation test stopped at a direct hybrid-retriever exception,
without composed workflow-to-dashboard proof or actual numeric/provenance mutations; the contributor
guide and runbook described opt-in execution without exact mandatory triggers and evidence.

The existing lossless test now asserts every screened candidate passes and retains exact
`46.272379900000004` concentration observations and source citations after PostgreSQL reopen and
dashboard validation. The existing mutation parameterization adds adjacent numeric substitution and
field-provenance alteration, reseals the mutable Chroma fingerprint, and runs every mutation through
real hybrid/evidence retrieval, the compiled graph, and the dashboard renderer. Rejected evidence
blocks before screening, provider generation and review. The renderer exposes only the fixed
allowlisted code and republish instruction; rejected source text, private marker and connection
password are absent. Graph state remains JSON-serializable.

CONTRIBUTING and the local runbook now document the existing local/release gate for snapshot
serialization/numeric proofs, Chroma metadata/stage/readback, hybrid retrieval/evidence, screening
contracts, activation/manifest/projection/retry, and relevant integration fixture/harness changes.
They require non-skipped final-content evidence before merge, including environment, commands,
counts, outcomes, cleanup and PR/CI identity. Current CI remains service-free without optional
stores/extras provisioning; a CI configuration change requires separate workflow approval.

## Acceptance evidence map

| ID | Evidence |
| --- | --- |
| AC71-1 | `test_lossless_real_chroma_graph_postgres_reopen_dashboard` uses complete schema-2 research documents with real Chroma and Neo4j. `test_issuer_real_stores_reopen_dashboard` supplies additional official-composition fixture evidence. |
| AC71-2 | The lossless and issuer tests publish, retrieve, screen, construct and reach `awaiting_human_review`; dashboard recomputation validates restored evidence. New assertions require complete passing screening candidates. |
| AC71-3 | `test_real_schema2_mutated_chroma_workflow_shows_safe_dashboard_diagnostic` covers persisted adjacent numeric and field-provenance tampering plus the three merged content/competing-metadata cases. Each blocks with no review/provider and a fixed actionable dashboard diagnostic. |
| AC71-4 | The lossless path preserves exact `46.272379900000004` in real Chroma readback, candidate evidence, restored dashboard and screening observations. No tolerance or numeric contract redesign. |
| AC71-5 | Existing `real_stores` fixture uses generated Compose identity, loopback ports and disposable stores; deterministic embeddings and fixed snapshot clocks avoid providers. Existing startup-failure teardown regression and fresh cleanup inspection prove the harness behavior. |
| AC71-6 | CONTRIBUTING's opt-in contract coverage and the runbook's required gate section name every trigger, exact command, zero-skip requirement and auditable final-content evidence; CI rationale is explicit. |

## Verification record

Verified on September 28, 2026 UTC, against the baseline above plus this four-file test/documentation
diff. Final PR commit and CI identity accompany the issue/PR evidence. Redacted environment:
Windows 11 `10.0.26200`, PowerShell, Python 3.13.14, uv 0.9.7, Docker 29.8.0, Compose 5.5.1,
repository-locked dependencies including RAG/checkpoint/dashboard extras. `uv.lock` SHA256:
`8e7a15afacdf82c0cb363c0246f21b4fab679c86e55a1d1ac435c08419ea23b8`.

| Command/check | Result |
| --- | --- |
| `uv run pytest -q -o addopts='' -m 'not real_store' tests/test_lossless_contract.py tests/test_dashboard.py tests/test_workflow.py` | 247 passed in 23.54 seconds. |
| `uv run pytest -q -o addopts='' tests/test_real_store_integration.py::test_real_store_start_failure_still_tears_down` | 1 passed in 1.11 seconds; deterministic startup-failure teardown proof. |
| `RUN_REAL_STORE_TESTS=1 uv run pytest -q -o addopts='' --tb=short --show-capture=no tests/test_real_store_integration.py` | All 41 collected cases passed in 151.25 seconds, zero failures/errors/skips. |
| `uv run pytest -q -o addopts='' -m 'not real_store' --tb=short --show-capture=no` | 1,241 passed, 41 intentionally deselected real-store cases in 190.21 seconds; zero failures/errors/skips. |
| `uv run ruff check .`; `uv run ruff format --check .` | Passed; 148 formatting targets. |
| `uv run mypy src` | Strict check passed, 49 source files. |
| `uv run python scripts/validate_codex_workflow.py` | Passed. |
| `uv run etf-advisor evaluate-retrieval` | Five baseline cases retain ranking/attribution and complete graph-sector context. |
| `uv run etf-advisor evaluate-explanations` | All 14 expected decisions matched. |
| `uv build` | Source distribution and wheel passed. |
| `docker compose config --quiet`; `docker compose -f compose.integration.yaml config --quiet` | Passed; integration validation supplied fixture-style loopback-port variables. |
| `git diff --check` | Passed. |

The successful integration run used project `etf-advisor-contract-41e3b86b8acd`. At
`2026-09-28T08:05:06Z`, Docker container and volume queries filtered by that exact Compose project
returned empty. Development and unrelated preexisting projects were preserved. The earlier full
run's project `etf-advisor-contract-4ef5d2395eac` was also verified removed after teardown.

Runs not counted as acceptance: the first expanded integration run passed 36 and failed five
because the new graph harness omitted an in-memory checkpointer. After adding the required saver,
four probes passed and one failed because the assertion expected `numeric_provenance`; the actual
graph-authoritative fingerprint correctly produced `document_integrity` first. Correcting that
test expectation yielded the complete successful run above. No product correction was needed.
The first full offline run passed 1,240 with one existing three-second Streamlit cold-start timeout;
the unchanged test passed immediately in isolation (1 passed in 5.69 seconds), followed by the
complete successful offline rerun above. Docker Desktop was started hidden after its engine was
stopped; no development publication/review operation was executed.

Self-review confirms the diff contains only `tests/test_real_store_integration.py`, CONTRIBUTING,
the local runbook and this evidence record. The existing complete fixture and all accepted
contracts remain unchanged. No escalation or one-off workflow exception was needed.

## PR #82 cleanup-evidence remediation

The [review finding](https://github.com/beagle1903/agentic-etf-advisor/pull/82#discussion_r4119940021)
identified that the runbook's unscoped container query could miss remaining project volumes while
the fixture captures teardown errors. The coordinator authorized routine remediation within
AC71-5/6 and I71-ISOLATE; the same implementation owner/model/effort and historical exemption apply.
No product, CI/configuration, Compose configuration or cleanup operation is changed.

The fixture now emits its exact generated project identity before startup. Before the unchanged
teardown, it reads only project-label-selected containers, independently verifies their project
label, and retains at most 16 unique, validated generated anonymous-volume names. Missing/failed
inspection, duplicate/invalid container IDs, wrong project, malformed mounts, unexpected names or
an exceeded bound fail cleanup evidence while the original scoped teardown still runs.

Live inspection confirmed that the pinned PostgreSQL/Neo4j images create three anonymous volumes
without Compose project labels. Label-scoped volume queries return no volumes even while those
mounts exist. The corrected PowerShell gate retains exactly one session project and volume
inventory with `Tee-Object`, checks both exact project-label container/volume queries, and also
checks every retained anonymous name with a read-only exact-name volume query. Each Docker query
must succeed; any remaining resource or missing/ambiguous/malformed inventory blocks acceptance.
The mock startup-failure regression consumes its own markers with `capsys`, so it cannot make the
operator-facing full-file run ambiguous.

The existing cleanup regression also covers generated mount inventory, wrong-project/unexpected
name/malformed/bounded inventory rejection, and inspection failure still reaching teardown. It
passes independently (1 case, 0.53 seconds). Ruff lint/148-format targets, strict mypy/49 source
files, workflow validation and whitespace checks pass. During the final run, exact-name queries
successfully detected all three mounted anonymous volumes before teardown; the project-label
volume query remained empty.

The final-source run executed the runbook's PowerShell gate verbatim from
`$env:RUN_REAL_STORE_TESTS` through all post-run checks (environment/bootstrap was already healthy).
All 41 collected cases passed in 98.50 seconds with zero failures/errors/skips. The retained sole
session project was `etf-advisor-contract-35686fe85301`; its three generated anonymous names were
captured before teardown. Both project-label queries and all three exact-name volume queries
succeeded with empty results afterward, and the gate printed its zero-container/volume cleanup
confirmation. Development and preexisting projects were preserved.

An earlier interim identity/label-only version also passed 41 cases in 98.45 seconds, but that is
not the remediation's final-source cleanup proof because it lacked anonymous-volume inventory.
This harness-only remediation does not change previous product/offline acceptance. Final pushed
commit, review-thread response/resolution and push CI outcome accompany the PR evidence.

## Explicitly authorized parser remediation after final review

Final independent review reopened the cleanup finding: default PowerShell JSON error handling could
convert rejected inventory into an empty list and permit cleanup confirmation. The user's explicit
`fix it` authorization is recorded at
https://github.com/beagle1903/agentic-etf-advisor/issues/71#issuecomment-5866493381.
This fresh attempt remains limited to the documented parser, its executable regression and evidence;
same ordinary owner/model/effort and historical exemption. Product, test fixture, Compose, cleanup
operations and CI/workflow configuration are unchanged.

The runbook now uses `ConvertFrom-Json -ErrorAction Stop` inside an explicit try/catch before any
resource inspection. Parse failure throws a fixed cleanup-unverified message. Existing shape/name
checks, correct empty arrays, exact anonymous-volume queries, Docker exit codes and pytest exit
status remain intact.

`pwsh -NoProfile -File scripts/verify_real_store_cleanup_gate.ps1` executes the exact documented gate
with service-free command doubles. All 12 cases pass: malformed JSON, native parser error,
injected nonterminating parser error, wrong top-level type, nonstring name, duplicate name and invalid
name all reject with zero Docker inspections and zero cleanup confirmations. Valid `[]` and one-name
arrays succeed with two/three inspections; nonzero pytest exit, failed Docker inspection and a
remaining anonymous volume reject. Resource query doubles reject unrelated project/name filters;
the script restores the prior integration opt-in environment value.

On local PowerShell 7.6.5 the native malformed-JSON examples already throw an ArgumentException
under default handling, so removing the explicit flag alone did not reproduce the review scenario.
The separate injected nonterminating error makes that scenario deterministic: removing
`-ErrorAction Stop` in memory fails `nonterminating-parser-error`; the corrected exact gate passes.
The initial regression script had missing zero defaults in its command doubles and rejected the
valid empty array; those mock defaults were corrected before the successful results above.

The corrected runbook's positive PowerShell gate ran verbatim from the opt-in assignment through
all post-run checks: 41 cases passed in 107.67 seconds, zero failures/errors/skips. Sole generated
project `etf-advisor-contract-caca2659df7b` retained three anonymous mount names before teardown;
both project-label queries and all three exact-name queries returned empty afterward, and the gate
confirmed zero containers/volumes. The focused existing cleanup regression passed (1 case,
0.62 seconds). Ruff lint/148-format targets, strict mypy/49 source files, workflow validation and
diff checks pass. No development or unrelated resource was mutated. Final commit/CI and the reply
to the reopened thread accompany PR evidence; only the coordinator may resolve it after the new
independent final review passes.

## Limitations

These are deterministic fixture proofs on disposable local services. They do not claim live market
freshness, provider availability, production concurrency/hosting/authentication, trade execution,
or repair of historical snapshots. Development stores, snapshots, volumes and saved reviews remain
untouched. No credentials, private data, raw provider output, prompts or `.env` files are added.
