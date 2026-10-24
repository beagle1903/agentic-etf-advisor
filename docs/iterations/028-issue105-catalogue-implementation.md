# Iteration 028: Issue 105 implementation evidence

The approved generation-2 design is in
[`028-issue105-catalogue-design.md`](028-issue105-catalogue-design.md).
This implementation adds an explicit <=100 versioned direct-listing scope,
resumable bounded cached research jobs, detached canonical schema-2
finalization, complete-only publication, exact full-pool retrieval, and pure
at-most-ten round-robin selection before the existing portfolio enumerator.
The dashboard exposes the preparation and new-review flow. The legacy path
omits all new request/report fields.

The tests use a versioned fixture of 240 synthetic US/EU directory listings.
An actual Streamlit AppTest previews 40, saves eight five-member batches,
finalizes, publishes, exact-retrieves, and reaches a ready graph review with
all 40 evidence rows and a portfolio member outside the packaged six. It
JSON-roundtrips and restores the saved checkpoint with catalogue, document,
graph, FX and collector adapters set to fail if called. These are production
orchestration paths with injected local provider and store doubles.

## Frozen acceptance evidence map

| ID | Explicit scenario and test evidence |
| --- | --- |
| AC105-1 | Generation-2 design, independent challenge and coordinator approval are recorded in the immutable Issue105 ticket ledger and the approved design handoff. The coordinator verifies their exact capsule digest/content binding; product tests cannot prove human/session provenance. |
| AC105-2 | `test_large_versioned_scope_never_truncates_and_preserves_coverage` verifies the 240-listing fixture and exact 0/100/101/>100 limits. `test_app_prepares_40_and_creates_review_with_outside_six_member` exercises real Streamlit script entry, full preparation, publication, review, and an outside-six ready position. |
| AC105-3 | `test_transport_request_deadline_and_receive_body_are_enforced`, `test_swallowed_transport_breach_cannot_be_cached`, `test_bnd_issuer_fallback_reserves_time_and_requests_before_invocation`, `test_record_and_canonical_payload_limits_reject_before_publication`, `test_late_complete_finalization_reuses_cache_and_exact_coordinates`, `test_failure_keeps_success_and_exact_retry_only_failed_member`, `test_started_attempt_crash_requires_exact_retry`, `test_result_ack_loss_preserves_success_without_recollection`, `test_exhaustion_and_stale_complete_cache_never_publish`, `test_foreign_cached_member_rejects_before_canonical_commit`, `test_invalid_cache_coordinates_reject_before_replacement`, `test_finalization_precommit_and_lost_ack_recover_truthfully`, `test_request_publication_failure_and_exact_recovery` (stage/activation/lost acknowledgement), and `test_stale_new_publication_rejects_before_staging` cover actual bounds, immutable cache, explicit retry, crash states, canonical commit, previous active, uncertainty and complete-only activation. `test_reference_file_count_duplicate_foreign_and_pinned_resume` and `test_ten_distinct_reference_files_aggregate_for_ten_members` cover ten-file/aggregate input validation, accepted ten-file use and no edited-file reread. Existing Issue104 reference tests retain per-file record/byte and identity rules. |
| AC105-4 | `test_full_40_pool_shortlists_after_first_ten_and_preserves_exact_totals` checks full screening, after-first-ten entry, <=10 enumeration, deterministic report/draft and exact cash. `test_contrasting_profiles_change_catalogue_shortlist_targets`, `test_exclusions_and_full_pool_identity_conflict_are_not_hidden_by_shortlist`, `test_alternative_representative_is_retained_but_final_groups_are_unique`, and `test_bounded_shortlist_can_be_infeasible_despite_full_pool_alternative` cover target/exclusion/category/group/alternative behavior and an honestly blocked bounded case. The AppTest permutes exact-document response order and checks pinned output order. Existing construction tests cover missing/stale/conflicting category and consumed-field provenance. |
| AC105-5 | The AppTest follows publication through exact retrieval, complete evidence, screening, shortlist, portfolio, JSON checkpoint and offline restore with zero catalogue/document/graph/FX/collector calls. It rejects scope digest and recomputed altered membership, version, missing/extra Chroma rows, changed universe, content/fingerprint, manifest, graph context, active pointer, persisted shortlist, request and receipt. `test_us_eu_contract.py` retains actual USD/EUR entry/revision, zero-cash FX, empty/all-invalid/all-stale schema2, legacy exact dump and nonempty-downgrade regressions; `test_revision.py` retains one-use receipts, failed/ambiguous retry, artifact reuse and downstream zero-call restore. |
| AC105-6 | The AppTest asserts every displayed preview count (discovered, direct, direct-only, overlap, combined, matched, requested), provider status/partitions/unsupported country and venue limits, job requested/researched/pending/failed/generation/finalization/publication and selection usable/shortlist/final/capacity/dispositions/omissions/unknown/reason totals/not-evaluated. `test_overlap_and_provider_limit_counts_are_pinned` checks nonzero overlap and 42 attempted provider partitions; the explicit unknown/not-evaluated summary case distinguishes null from zero. ADR0040, usage, vision, architecture and this iteration record describe the scope and limitations. |

`test_oversized_or_malformed_catalogue_rejects_before_scope` verifies the
32MiB catalogue input bound and strict schema. The explicit 101-ID test
exposed a pre-count parser cap; removing that cap while bounding serialized
filter input lets the exact matched count appear without truncation.
`test_directory_symbol_outside_research_limit_reports_unsupported` creates a
valid 13-character directory symbol and asserts the fixed unsupported reason
before any research job. `test_foreign_cached_member_rejects_before_canonical_commit`
substitutes another member's digest-valid cached record and verifies that
finalization rejects it before committing canonical coordinates.
`test_invalid_cache_coordinates_reject_before_replacement` checks both an
ingestion time before creation and mixed successful cache times. These exposed
and repaired missing pre-replacement cache validation. Issue103 catalogue tests continue to cover
duplicate/conflicting listing identities and provider partition completeness.
No provider lookup is invoked by scope planning.

## Measured verification

Final repaired-content focused suite:
`uv run pytest -q tests/test_issue105_catalogue.py tests/test_issue105_app.py tests/test_issue105_remediation.py tests/test_us_eu_contract.py tests/test_dashboard.py tests/test_revision.py tests/test_evidence.py tests/test_construction.py tests/test_catalogue.py`
reached 100% and exited 0. Final full offline `uv run pytest -q` reached
100% and exited 0; the suite displayed 40 skips. The full suite ran on the
same product source as the final focused run; the later change was only the
two-case BND reservation test and this evidence note. The focused suite was
rerun and passed after that addition. `uv run ruff check .`
passed; `uv run ruff format --check .` reported 204 files formatted;
`uv run mypy src` passed 63 source modules. `uv build` produced the sdist
and wheel. `uv run python scripts/validate_codex_workflow.py`,
`uv run python scripts/ticket_workflow.py validate`,
`docker compose config --quiet`, and `git diff --check` passed, all exit 0.
Earlier full/focused runs on pre-remediation content or interrupted for
material same-scope repairs are not final-content certification evidence.

## Self-review and limits

The A105-2 arbitration restored the approved two-pass shortlist: unrepresented
groups first, then remaining alternatives, with the round-robin append order
passed into the unchanged constructor. The usable count is measured before
zero-target shortlist omission; final positions still enforce one per economic
group. The new request/report fields remain absent in legacy serializers,
Issue104 USD/EUR source, economic identity, exact cash and FX rules remain in
place, and full-pool FX needs-rate staging was not optimized away.

Remediation found three concrete frozen-contract gaps: displayed direct and
overlap/job/selection totals lacked complete assertions, an explicit 101-ID
scope failed before reporting its matched over-limit count, and finalization
could replace cached coordinates before validating a digest-valid but foreign
or internally inconsistent record. The first is now displayed and tested, the
second reports exact over-limit counts, and the third rejects before canonical
commit. A valid 13-character directory symbol also gets a fixed unsupported
reason before collection. The final focused/full tests above ran after these
repairs.

These positive cases use injected local doubles and establish contract
behavior, not live Yahoo completeness or suitability. The AppTest does not
operate real Chroma, Neo4j or PostgreSQL services. A bounded shortlist can
still miss a feasible full-pool combination; the original blocker and
per-listing omissions remain visible. Long jobs can age out without renewing
source observations. No brokerage action or external financial write occurs.

## A105-4 final-review repair, 2026-10-24

The failed independent final review identified two frozen-contract defects in
the prior content. Before editing the product code, an offline regression
using installed yfinance 1.7.0 demonstrated that a catalogue `Ticker` left the
singleton bound to its request-limited session after both successful and
exhausted attempts; a later ordinary `Ticker(session=None)` reused it. A real
Streamlit AppTest also demonstrated that an explicit 101-listing preview hid
the planner's `matched=101 limit=100` reason behind a generic error.

The collector now snapshots and restores the singleton's prior session and
session-specific authentication state in `finally` while holding the existing
Yahoo exclusion lock. The offline test instantiates a subsequent ordinary
`YahooResearchAdapter` Ticker, uses its session with a substituted no-network
request, checks success and exhausted-budget paths with and without a prior
singleton, and restores process-wide test state. The preview displays only a
strictly parsed numeric over-limit count and limit; other exceptions retain a
fixed message. The AppTest starts with a valid preview, rejects 101 members,
asserts the old scope is cleared and job start disabled, then checks that an
unexpected provider error does not expose its payload. No collection or
publication action occurs on rejection.

The repair changes neither request, byte or deadline bounds nor portfolio,
FX, shortlist, replay or legacy serializers. The test uses installed yfinance
with offline substitute transport; it does not prove a live Yahoo response.

The repaired-content focused command
`uv run pytest -q tests/test_issue105_final_review_repair.py tests/test_issue105_catalogue.py tests/test_issue105_remediation.py tests/test_issue105_app.py tests/test_us_eu_contract.py tests/test_yahoo_research.py tests/test_catalogue.py tests/test_dashboard.py tests/test_revision.py tests/test_evidence.py tests/test_construction.py`
reached 100% and exited 0. Full offline `uv run pytest -q` then reached
100% and exited 0 with 40 skips on the same source and tests.
`uv run ruff check .` passed; `uv run ruff format --check .` reported
206 files formatted;
`uv run mypy src` passed 63 modules; `uv build` built sdist and wheel.
`uv run python scripts/validate_codex_workflow.py`,
`uv run python scripts/ticket_workflow.py validate`,
`docker compose config --quiet`, and
`git diff --check` passed with exit 0. The prior full suite and failed final
review on the old content remain historical failures, not certification of
this repair. No real Chroma/Neo4j/PostgreSQL or live Yahoo integration was
exercised by these offline positives.

## A105-5 post-delivery repair, 2026-10-24

The subsequent PR review found two more concrete failures. A locked minimal
development installation lacks optional `yfinance` and `curl_cffi`, so four
installed-singleton regressions imported those packages unconditionally and two
bounded issuer-fallback tests imported `yfinance` through the collector. A
separate ignored `.artifacts/issue105-minimal-venv` created with
`UV_PROJECT_ENVIRONMENT` and `uv sync --frozen` confirmed those packages and
Streamlit are absent. The singleton regressions now skip only when their real
optional dependencies are absent; in the optional-enabled environment all four
run. The two bound-reservation cases inject the optional module boundary and
run in both environments. The six-case targeted minimal run gave four skips
and two passes; the optional-enabled run passed all six.

A fresh Streamlit session previously had no saved-job load control. Before the
source fix, the new AppTest failed looking for that control. The dashboard now
accepts an exact saved job ID and calls the strict store read without collecting,
retrying or publishing. Invalid, missing and corrupt IDs clear the selected
job and show a fixed error; store reads also reject a valid manifest placed
under a different ID. The actual two-session AppTest creates a five-of-six
partial job, reopens it in a new session with zero automatic collector calls,
compares the saved cache bytes, source timestamps, version and generation,
then explicitly advances only the sixth member. A separate store test covers
the mismatched manifest identity. These are offline injected local doubles,
not live Yahoo or database integration.

On the final A105-5 product source, the optional-enabled focused command
`uv run pytest -q tests/test_issue105_final_review_repair.py tests/test_issue105_catalogue.py tests/test_issue105_remediation.py tests/test_issue105_app.py tests/test_us_eu_contract.py tests/test_yahoo_research.py tests/test_catalogue.py tests/test_dashboard.py tests/test_revision.py tests/test_evidence.py tests/test_construction.py`
reached 100% and exited 0. In the isolated minimal environment,
`uv run --frozen pytest -q` reached 100% and exited 0 with optional-dependent
tests skipped. The targeted minimal and optional-enabled six-case commands
above confirm that only the four real-singleton cases skip under minimal CI;
the two bound-reservation cases run in both environments.

`uv run ruff check .`, `uv run ruff format --check .` (207 files),
`uv run mypy src` (63 modules), `uv build`,
`uv run python scripts/validate_codex_workflow.py`,
`uv run python scripts/ticket_workflow.py validate`,
`docker compose config --quiet`, and `git diff --check` all exited 0.
The minimal full run uses locked default and development dependencies; the
installed optional packages are exercised only by the focused run. Neither
positive run demonstrates live Yahoo availability or external database health.
