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
