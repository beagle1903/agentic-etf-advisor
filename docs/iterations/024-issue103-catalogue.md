# Iteration 024: Issue 103 Yahoo listing catalogue implementation

Issue [#103](https://github.com/beagle1903/agentic-etf-advisor/issues/103) implements
the approved generation 2 capsule `issue-103-yahoo-catalogue`, digest
`b9c97b4c7f067883a8752c7b8846b9cb63c85ca5848c926e3567542074b7a234`.
The separate architect handoff, independent challenge and coordinator approval are
recorded in [the design handoff](024-issue103-catalogue-design.md). A103-1's original
failed challenge and approved overlap clarification remain part of that history.

## Delivered boundary

`etf_advisor.catalogue` contains the fixed `yahoo-listing-map-v1` manifest, strict
observation and catalogue validation, bounded discovery/direct lookup operations,
and an ignored local immutable JSON store. The optional yfinance 1.7.0 adapter builds
the reviewed two-equality ETFQuery per partition and supplies a session whose HTTP
requests, including cookie/authentication calls, use the smaller of ten seconds and
the refresh deadline remainder. Search is exact for direct lookup and capped at 25
non-exhaustive suggestions. The CLI exposes `catalogue refresh`, `search` and
`lookup`; it does not call research publication or advisory screening.

All 42 partitions must finish for a full refresh publication. Reports retain fixed
query, provider/map versions, requested/response times, offsets, counts, totals,
identity digests, retries/errors, duplicate/rejected counts and truncation state.
Incomplete or unattempted partitions stay visible in the returned report, while the
active pointer remains on its prior validated version. The 24-hour reuse clock is
the prior full-refresh completion time, unaffected by direct additions. Local search
labels a version `direct_only`, `fresh` or `stale` and exposes its age and matched
count before the output limit.

The catalogue stores discovered and direct observations separately. Full refresh
retains direct observations byte-equivalently, including original response and quote
times. Combined projection counts their union and selects the whole discovered
observation on overlap, with no optional-value backfill. A same-symbol different-
exchange union fails publication and preserves the prior active pointer. Direct
verification, publication and resulting selected projection are separate outputs.
The store validates schema, digest, counts, identities, fixed manifest and page
report before exposing the active version; a bounded lock and parent CAS prevent
last-writer overwrite. Runtime sessions, clocks and locks stay outside catalogue JSON.

## Verification and observed source limits

Synthetic focused fixtures cover mapping/exclusions, exact ETF lookup and rejection,
the architect's T0/T1/T2 overlap sequence, empty and multi-page partitions,
duplicates, changed totals, malformed/bool counts, short pages, source failures,
retry/unattempted reports, expired/forced reuse, prior-version preservation,
corrupt JSON and CAS, and transport/deadline bounds. The slow-provider fixture found
and fixed an over-deadline response retention bug before completion.

A bounded live probe on 2026-10-14 verified one exact `VWCE.DE` Search result as ETF
on `GER`; Search omitted source quote time and currency, so both remain explicit
absences in the direct observation. A separate `pl/WSE` screen call returned
start 0/count 57/total 57 with the reviewed page shape. These checks establish
adapter capability only. No complete 42-partition live catalogue was collected;
other source coverage, Yahoo taxonomy accuracy, upstream omissions and same-count
changes remain unverified. `provider_partitions_complete` is conditional on a later
full successful refresh and does not assert all Yahoo or EU ETFs. Seven EU member
countries have no mapped source exchange; unsupported is not a zero listing count.

The existing six-symbol research universe, US-only advisory eligibility, frozen
Issue 99 evaluation dataset identities and graph/checkpoint state were not changed.
No trades, financial writes, hosted distribution or provider raw response storage
are introduced.

## Initial review remediation

The independent initial code review failed with four same-scope scenarios, recorded
in `docs/workflow/issue-103-review-repair.md`. Each was reproduced as a failing
focused test before repair. Rejected `catalogue lookup --add` results now exit
nonzero. Discovered records must match their exact country/exchange partition and
page offset; complete catalogue readback recomputes each page's normalized identity
digest and count from linked records and checks the response observation time.
Blob/pointer I/O failures now return a controlled failed publication with the
previous active version retained; cleanup after successful pointer movement cannot
falsely report an unchanged prior version. Out-of-range source quote timestamps
now yield an incomplete partition or rejected direct lookup. The initial review
remains a failed historical gate; fresh content-bound verification, acceptance and
independent final review remain required after this repair.

## PR 108 post-delivery repair

Three P2 review comments are handled under the finite Issue 103 continuation and
arbitration A103-2. A failed refresh or direct addition reads the current validated
active catalogue before reporting `active_version`, with `attempted_parent_version`
kept separate. If that read fails, `active_version_state=unknown` prevents a captured
parent from being mislabelled current. Publication retries release of its own lock
three times after a transient unlink error; persistent cleanup failure is exposed as
`cleanup_error=lock_release_error` while the already committed version still reports
published. It does not remove an unowned or purported stale lock. Complete partition,
page and retry-error evidence now has exact required keys and types on catalogue
construction and readback, so a recomputed digest cannot legitimate hidden raw fields
or missing audit counters. Focused fixtures reproduced the original three failures
before repair and exercise CAS winner metadata, transient and persistent cleanup,
and correctly digested nested-schema rejection. Final content-bound verification
and independent final review remain required; the original delivery and reviews
remain immutable ledger history.
