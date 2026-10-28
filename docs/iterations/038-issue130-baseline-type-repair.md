# Issue130: behavior-preserving baseline type repair

Status: ordinary owner implementation passed under the pre-recorded DESIGN_READY
capsule. Content-bound verification, acceptance and independent review remain the
next gates. No runtime or public-contract change is authorized by this ticket.

The human approved one separate behavior-preserving repair attempt on28October2026
for the26baseline type errors that blocked Issue128/PR129, followed by one additional
Issue128 implementation attempt. This [repair issue](https://github.com/beagle1903/agentic-etf-advisor/issues/130)
uses only the repair part of that package. The128slot will be separately recorded
in its existing ledger; no old failure or count is reset. No automatic merge or
actual123amendment/sourcecall/key/activation is authorized.

Classification: ordinary work inside established contracts, limited to annotations,
type narrowing and local-variable names in the seven existing source modules.
Owner `/root/issue130_owner`, implementation_worker / gpt-6-sol / medium, owns
implementation, meaningful tests, self-review and verification. Separate independent
code review is required because these modules cover financial/identity/locking
paths and a disputed required gate. If a repair needs any actual runtime or
consequential contract change, stop for separate design rather than expanding scope.

The [native ledger](../workflow/tickets/issue-130.json) binds complete generation1
capsule `issue-130-behavior-preserving-baseline-type-repair`, digest
`43fcf35b90677ecb4043e3cff8500844eff7544bd0c29aa21b3a7d8b22f0eac9`.
Default finite lifetime: implementation1, initialreview1, remediation1,
finalreview1, designreset1; no automatic extensions. Elapsed time is audit-only.

Both prescribed locked mypy forms reproduce26errors:4 in fund_identity,
5 in fund_identity_registry,4 in policy,4 in screening,2 in research_job,
3 in construction and4 in explanation/models. No ignore/config/dependency change
is permitted. Preserve exact keyword presence/model_fields_set/serialization
omission/legacy bytes and all marker/proof/freshness/financial/lock behavior.
Interfaces and product/graph/checkpoint JSON impact: none.

Required evidence: both type checks, meaningful existing seven-module regression
and semantic-equivalence checks, full locked default tests with retained counts
and skips, Ruff/format, both workflow validators, build, Compose and diff checks.
Finish documentation before identical-content verification/acceptance and independent
review. Deliver a separate repair PR; a stacked dependency may make it available
to existingPR129 without merging either PR or transferring certificates.

## Owner implementation and self-review

The seven scoped source modules now use narrow optional-key `TypedDict` annotations
at their existing model-construction calls. The raw explanation profile value is
only cast for static typing; `InvestorProfile.model_validate` still receives the
original dictionary and rejects an unknown marker. The Unix registry lock module
has a typed protocol cast around the same imported `fcntl` object and the same
`flock` operations. Local names in the registry proof validator distinguish
membership assertions, context links, and nullable matched members. No model
fields, validators, serializers, branches, constants, external calls, or public
interfaces changed.

Self-review compared each edited call against its preceding expression. Every
optional keyword retains its original truth/presence condition and value; in
particular legacy absence remains absent rather than explicit `None`. The
registry lock keeps its `os.name` branch, exact exclusive/nonblocking/unlock
flags, timeout, error handling, and file handle. No mypy ignore, configuration,
dependency or product-contract change was made. Focused regression additions
assert legacy omission and selected-marker `model_fields_set`/JSON presence
through policy, construction and explanation; the raw invalid explanation marker
still fails Pydantic validation. Existing synthetic proof, registry CAS,
catalogue, screening, construction and offline restore tests exercise the
remaining touched execution paths.

## Owner verification

The implementation owner ran the following checks on the repair worktree.
The coordinator must still conduct content-bound verification and acceptance,
independent review, and delivery on the final content.

| Check | Owner result |
| --- | --- |
| `uv sync --frozen` | Passed; 57 locked packages audited. |
| `uv run --frozen mypy` | Passed; 67 source files. |
| `uv run --frozen mypy src` | Passed; 67 source files. |
| Focused identity, policy, screening, construction, catalogue and explanation suites | Passed; the full final suite below includes the added equivalence assertions. |
| `uv run --frozen ruff check .` | Passed. |
| `uv run --frozen ruff format --check .` | Passed; 230 files formatted. |
| `uv run python scripts/validate_codex_workflow.py` | Passed. |
| `uv run python scripts/ticket_workflow.py validate --issue 130` | Passed. |
| `uv build` | Passed; source distribution and wheel built. |
| `docker compose config --quiet` | Passed. |
| `git diff --check` | Passed on final tracked source/tests; iteration markdown whitespace checked separately. |
| `uv run --frozen pytest -q -ra` | Passed on final source/tests (exit 0). Quiet output gave individual skip reasons but no aggregate counts. |
| `uv run --frozen pytest -q --junitxml=.artifacts/issue130-pytest.xml` | Passed on unchanged source/tests (exit 0). JUnit: 1,870 total, 1,811 passed, 59 skipped, zero failures/errors; 202.850 seconds. |

No provider or registry source collection, registry/store activation, real key,
trade, or external financial write was attempted. The synthetic tests do not
establish live curator source validity. Local Windows execution does not directly
exercise the Unix `fcntl` branch; the source remains exactly the same runtime
module and operations, and Linux CI will exercise that path.

The 59 default skips are optional transport/store/dashboard dependencies
(`curl_cffi`, `psycopg`, `chromadb`, `streamlit`) and guarded disposable real-store
tests. They were retained as skips; no optional integration or external service
was enabled for this annotation-only repair.
