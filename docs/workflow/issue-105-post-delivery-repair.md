# Issue105 A105-5: bounded PR116 post-delivery repair

2026-10-24, coordinator /root. User approved one additional repair and one
independent final review for the two specified PR116 blockers, noting 26% usage
remaining. Keep the pass bounded; no model exception, scope expansion or merge
authorization. Owner remains /root/issue105_owner, implementation_worker /
gpt-6-sol / medium; independent reviewer code_reviewer / gpt-6-sol / high.

Native continuation preserves original PR116/content binding and all previous
events/counts, adds remediation1/final-review1, clears current certification and
resumes post-delivery audit. Gen2 capsule and approved handoff unchanged. Before
reservation remediation1/final-review1 remain; implementation/reset0. No active
phase or offline time subtraction. Earlier local passes and review passes remain
historical evidence; they do not waive current CI/review failures.

| Evidence | Frozen criterion | Expected/actual | Classification |
| --- | --- | --- | --- |
| CI40109595789, head4d2147e | AC105-5, required checks | Minimal locked dev environment works; six new tests unconditionally import absent optional curl_cffi/yfinance and fail | Demonstrated test-environment defect |
| GitHub discussion_r4367665020, dashboard job ID assignment | INV105-2/5, AC105-3/5/6 | Explicitly reopen same cached job after session loss without calls; only session-state ID populated by new-job creation exists | Demonstrated frozen resume/UI gap |

Primary decision: **narrow repair** with same owner and original PR. Make the
optional-provider regressions follow established optional-dependency conventions
without skipping unrelated tests or weakening mandatory core coverage. Keep the
actual provider regressions meaningful with extras installed; validate the locked
minimal CI environment separately from the existing optional-enabled workspace.
Do not alter global environment/dependencies or broaden CI configuration merely
to hide the difference without justification.

Add explicit saved-job ID input or equivalent bounded selector using existing
strict ResearchJobStore validation. A read/load action must not collect, retry,
finalize, publish or create a new job. Invalid/missing/corrupt input is sanitized
and cannot retain a stale selected job. After new Streamlit session, load the
partial job, retain cached successes/source timestamps/version/generation, then
explicitly advance only pending work or retry the exact ambiguous/failed attempt.
Preserve existing finalized/published job semantics and bounded transitions.

Rejected: waive red CI because local full pytest passed; drop optional-enabled
regressions; automatically recollect successes; trust arbitrary job IDs; reset
counts, create a new ticket/PR, or change financial/replay/FX/shortlist policy.
These are failures of clear frozen contracts, not a new design requirement.

Closure: negative-before/positive-after focused tests for minimal dependencies
and actual fresh-session AppTest reopening; strict rejection/zero-side-effect
load, cached-success preservation and pending-only explicit continuation. Run
appropriate focused checks plus one full minimal-environment suite and preserve
optional-enabled regression evidence; static/build/config gates as required.
Record exact outcomes/limits, resolve both blockers after successful remediation,
fresh content-bound verification/acceptance and independent final review, then
redeliver on PR116 and verify latest-head CI and actual unresolved review threads.
Failed final review stops for explicit finite human decision. No new allowance
is created by this record; later outcomes belong in excluded ledger evidence.

## Focused closure before fresh certification

Same owner returned REMEDIATION PASS. Isolated locked minimal environment full
pytest reached100% exit0; optional-enabled focused11-file suite and all6 CI-related
cases passed. Minimal targeted cases appropriately skip4 installed-provider tests
and execute/pass2 BND core checks. Actual fresh-session AppTest loads the existing
partial job read-only, preserves cache/version/generation, then explicitly advances
only pending work; invalid/missing/corrupt IDs clear selection. Store rejects a
manifest identity inconsistent with the requested job. No automatic provider or
publication calls occur during loading. Negative-before/positive-after evidence
and exact environment commands are recorded in the implementation note.

Ruff/format/mypy63/build/workflow/Compose/diff gates pass; source/tests/docs are
quiescent. Frozen financial/FX/shortlist/replay contracts unchanged. Both blockers
may resolve after successful remediation; current-content verification and
independent final review remain mandatory before redelivery on original PR116.
This closes only the repair episode and grants no further phase/merge authority.
