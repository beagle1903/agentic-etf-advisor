# Issue 70: Lossless numeric snapshot implementation

Status: implementation self-reviewed and verified; coordinator freeze and independent review pending.

Approved consequential scope, frozen invariants I70-NUM, I70-EXPOSURE, I70-IDENTITY, I70-ACTIVATE,
I70-RETRY, I70-CONSUME, I70-ENCODING, I70-COMPAT and I70-STATE, and acceptance AC70-1 through AC70-12
are recorded in the complete [DESIGN_READY capsule](https://github.com/beagle1903/agentic-etf-advisor/issues/70#issuecomment-5847394674).
The independent challenge and coordinator approval precede the write session. Implementation owner
is `/root/issue70_implementation`, `implementation_specialist`, gpt-6-sol/high. User authority is
"fix it", followed by an explicit continuation and finite extension recorded in Issue70 comments.
The extension ends no later than 2026-09-26T19:42:54Z; review/remediation counts remain unchanged.

## Implementation boundaries

The shared numeric codec, research wire models and Yahoo decimal handoff preserve exact values.
Chroma staging and Neo4j activation separately verify immutable evidence. Hybrid retrieval checks
graph-authoritative fingerprints; pure evidence, screening, construction, revision, explanation
and dashboard paths revalidate their serialized nested contracts. No BND coverage, universe,
threshold, category, allocation, ranking or external-write behavior is changed.

ADR0027 documents the contract and the local runbook documents writer quiescence and explicit retry.
Existing accepted decisions and historical failed attempts remain intact.

## Verification evidence

The first complete offline run lost its process handle across the pause and is unconfirmed. The
replacement run passed 1,159 cases; the next expanded offline run passed 1,179 cases. Independent
disposable real-store runs passed 8, then 22, then 24, then 28 cases with no skips. A complete
opt-in run then passed 1,211 cases in 259.48 seconds, including all 30 current real-store cases.
Final AC70-8 selector hardening and three regressions followed that run; its complete opt-in
repeat passed all 1,214 cases in 261.17 seconds with zero failures or skips. The final handoff
content is rerun after recording this evidence. These outcomes do not authorize delivery.

The expanded suite initially failed service setup because Docker Desktop had stopped; the owner
restarted it hidden before retry. Two mistaken `scripts/evaluate_*.py` invocations did not run an
evaluation; the documented `etf-advisor` evaluation commands subsequently passed. Test expectation
and fixture failures were corrected and rerun; none is counted as successful verification.

Self-review tightened preactivation complete canonical Chroma readback, the final pointer check
after graph enrichment, strict duplicate graph-weight rejection, and outer consumer duplicate-key
JSON parsing. It also found that the selector could hide same-identity mixed encodings through
legacy-style deduplication. Schema-2 mixed/duplicate results and contradictory joins now fail,
and ready schema-2 health observations match candidates exactly. These changes close frozen
AC70-8/9/12 requirements without changing financial policy. Hybrid integrity failures preserve
their allowlisted category through the retrieval adapter rather than becoming transport failures.

### Frozen acceptance evidence map

| Frozen ID | Focused evidence |
| --- | --- |
| AC70-1 | Real Chroma get/query, hybrid/evidence/screening, PostgreSQL close/reopen, dashboard exact `46.272379900000004` token. |
| AC70-2 | Canonical/adjacent/native/nonfinite codec rejection; field unit and flattened status contradictions; unchanged screening regression suite. |
| AC70-3 | Exact `0.7+99.3`, zero/signed zero/subnormal proof round trips; `60+60`, `100+epsilon`, missing/wrong/native proofs fail. |
| AC70-4 | Actual CLI stale-active schema1/schema2 and historical-schema1 matrices, each with/without payload; new/inactive stale API and CLI freshness regressions. |
| AC70-5 | Active and inactive real manifests reject foreign, wrong-label, null-ID, duplicate-edge, missing and extra children. |
| AC70-6 | Real content changes with unchanged/recomputed fingerprint and semantically valid competing metadata/content fail graph-authoritative retrieval. |
| AC70-7 | Exact-int rejection table at snapshot/document/manifest/graph/evidence/screening boundaries; duplicate JSON keys, consumer JSON entrypoints, downgraded restored artifacts. |
| AC70-8 | Same-identity mixtures in both orders, outer-marker downgrade, replacement retrieval, omitted/duplicate observations, graph joins, screening/construction/revision output/explanation/dashboard rejection. |
| AC70-9 | Malformed bounded Chroma arrays and post-stage canonical readback fail; fresh-connection real rollback verifies previous pointer/facts/projection; CAS and committed-but-lost-ack uncertainty. |
| AC70-10 | Two real Chroma clients synchronize after first read and before conflicting same-ID adds; exactly one succeeds, accepted bytes remain unchanged, both clients can reuse identical content. |
| AC70-11 | Schema1 snapshot/document/evidence/screening golden JSON and digests compared directly with approved base `148eba7`; existing checkpoint round trips, real A→B→A/shrinking history, failed-first-publication legacy hiding. |
| AC70-12 | Fixed allowlisted workflow/publication diagnostics, private-marker/DSN redaction, invalid replacement/restore never reaches provider or review, JSON-safe token round trips. |

### Gate commands

```powershell
$env:RUN_REAL_STORE_TESTS='1'
uv run pytest -q -o addopts=''
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/validate_codex_workflow.py
uv run etf-advisor evaluate-retrieval
uv run etf-advisor evaluate-explanations
uv build
docker compose config --quiet
docker compose -f compose.integration.yaml config --quiet
git diff --check
```

Ruff lint and all 142 formatting targets pass; strict mypy passes all 47 source files; workflow
configuration validation passes. Retrieval retains ranking on all five baseline cases and gains
complete graph context; explanation evaluation passes 14/14. Source/wheel build and both Compose
config checks pass. The integration config warns about unset test-port variables outside its
fixture; the disposable fixture supplies independently allocated loopback ports.

### Limitations and handoff

No live Yahoo/provider portfolio-generation run or development snapshot/checkpoint mutation is
part of these fixed-provider proofs. Missing BND concentration remains missing, and a valid numeric
publication does not promise an eligible portfolio for incomplete source data. Old conflicting
schema1 evidence is not repaired. Older writers must be quiesced before rollout.

No credentials, private payloads, prompts, raw provider output, environment files or external
financial writes are added. Disposable generated test volumes are torn down; development volumes
and saved reviews remain intact. CI and independent code review are pending coordinator delivery.
No commit, push or PR is authorized from this implementation session; the coordinator freezes the
complete worktree and obtains independent review first.

## Single authorized remediation pass

The independent [initial review](https://github.com/beagle1903/agentic-etf-advisor/issues/70#issuecomment-5848800520)
failed on two frozen-contract scenarios: ordinary generic graph indexing could overwrite an active
research projection (I70-ACTIVATE), and malformed schema-2 record containers/items escaped the
sanitized CLI diagnostic boundary (AC70-7/12). The coordinator reserved the single
[remediation pass](https://github.com/beagle1903/agentic-etf-advisor/issues/70#issuecomment-5848800680).
This pass changes only those defects and their tests/evidence; other approved implementation
content and the BND exclusion remain unchanged.

Generic Neo4j upsert now acquires the existing publication catalog lock in one explicit transaction
and rejects all ordinary documents while any active research pointer exists. This covers both
same-symbol overwrite and different-symbol projection pollution, with no partial batch writes.
Inactive generic indexing retains its existing document behavior. No lock primitive, relationship
model, automatic retry, or publication ordering is redesigned.

Real contention probes reproduce Neo4j's `Neo.TransientError.Transaction.DeadlockDetected` when
publication owns the catalog first. This is a confirmed-rollback, fail-closed result, not successful
indexing: only the fixed `retrieval_unavailable` diagnostic is exposed. The regression accepts that
specific transactional outcome or the post-lock `projection_integrity` guard, requires rollback,
and verifies the exact pointer, complete projection, and absent ordinary document using a fresh
client. A subsequent ordinary write must hit the guard. Both lock orders are repeated three times.
The early probes failed because they incorrectly required only the guard diagnostic; those runs
are not counted as passing verification.

Schema-2 snapshot decoding now rejects malformed record containers/items before indexing or
field traversal. Actual CLI regressions for `null`, `[null]`, and `[{}]` require the fixed
`schema_encoding` diagnostic, no private marker, no TypeError/KeyError, and no provider/staging call.
Schema-1 compatibility is unchanged.

Remediation-focused CLI, Neo4j, snapshot, and lossless contract tests pass 104 cases. All eight
focused real-store guard/contention cases pass in 47.46 seconds. Ruff lint/142 formatting targets,
strict mypy/47 source files, workflow validation, five retrieval baseline cases, explanation
evaluation/14 cases, source/wheel build, both Compose configurations, and whitespace checks pass.
The complete opt-in remediation rerun uses the gate command above; its definitive outcome and
the complete changed-file path/blob manifest hash accompany the coordinator freeze. Independent
final review remains required before delivery.
