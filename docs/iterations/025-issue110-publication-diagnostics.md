# Iteration 025: Issue 110 research publication diagnostics

Issue [#110](https://github.com/beagle1903/agentic-etf-advisor/issues/110) uses the
ordinary `DESIGN_READY` capsule `issue-110-publication-diagnostics`, generation 1,
digest `9ab4571a213a2af1d0f25ea935aa1b329807607470530275c0806a81c313434c`.
The user authorized the bounded diagnosis, diagnostic repair, focused tests and
fresh publication retry on 2026-10-15.

The initial local refresh failed with a generic `schema_encoding` message. Its original
exception was not retained, so its precise cause remains unconfirmed. A read-only
probe using the current local runtime read Neo4j's active pointer, all six Yahoo
symbol records, a fresh six-record snapshot and health report, and the Chroma
collection successfully. This did not prove the earlier failure was transient.

The CLI now records a fixed publication stage and selects fixed source, store,
input, local-I/O, market-data quality, or genuine integrity diagnostics. It never
prints exception text, provider responses, connection details or canonical payloads.
Failures retain a nonzero exit. Existing validation, immutable version handling,
store ordering and active-pointer semantics are unchanged. Focused tests inject
source, graph, validation and integrity failures, including secret-looking messages,
and verify their fixed output and failed exit.

The first authorized fresh-version retry, `issue110-20261015T155632Z`, failed
nonzero at `source_fetch: source_failure` before canonical payload save or store
publication. A following read-only reproduction found `MarketDataError` at BND
record construction: Yahoo holdings were absent and the official issuer fallback
raised `IssuerSourceError`. The adapter intentionally reports the fixed
`issuer_source_error` reason; the issuer client's deeper failure reason was not
retained. A separate direct issuer read then returned ten holdings, supporting an
intermittent source failure without proving its network cause.

One further bounded retry with a new version, `issue110-20261015T160113Z`,
published successfully. It activated digest
`aac9b0ccb8ab868b2edecc1abb85432715a51cdbb90bf641b4809da7c76e5a7f`
with six verified Chroma documents and six Neo4j documents, replacing active
version `issue79-20260927T0910Z`. The failed version remains a failed attempt;
the prior snapshot was preserved until the successful activation. Live source
availability remains outside the application's guarantee.

## PR 111 review repair (2026-10-16)

[Coordinator arbitration A110-1](../workflow/issue-110-arbitration.md) accepted three
same-scope diagnostic defects under AC110-1/AC110-2. The inactive-version retry now
marks a missing canonical payload as `payload_load: input_validation`. Ordinary
Pydantic input errors use their current stage, while a nested error carrying an
allowlisted research-integrity code keeps that code. On an active legacy snapshot
without fingerprints or a supplied payload, the required Neo4j document
reconstruction runs under `graph_readback` before Chroma verification resumes.
The existing missing-document check still precedes reconstruction.

Three real CLI fault-injection regressions failed on the delivered code with the
reported wrong stages/categories, then passed after repair. A separate nested
integrity validation fixture preserves `numeric_provenance`; existing schema-2
malformed-input cases retain their safe integrity diagnostic. Each CLI failure
remains nonzero and hides injected private text. This repair changes only the
CLI's attribution, with no further live publication or store data changes.
The corrected content passed 30 focused CLI tests and the full service-free
suite (1,604 passed, 48 skipped). Ruff lint/format, mypy (55 source files),
`uv build`, static workflow and ticket-ledger validators, and `git diff --check`
also passed. The separate independent final review remains pending.
