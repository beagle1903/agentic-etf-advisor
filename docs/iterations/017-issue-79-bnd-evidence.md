# Issue 79: Official BND composition evidence

- Status: Remediation complete; final independent review pending.
- Scope: frozen Issue79 capsule and AC79-1 through AC79-8.
- Lineage: user-approved successors of retired Issues77 and 78; finite counters and
  allocated budget remain in ticket ledgers.

The bounded client fetched the August 31 effective-date response on September 27:
16,300 scoped rows, four exact placeholders, 1,190 blank percentages, 26 negative
percentages. Selected ten sum exactly to 4.90581 percentage points; schema-2 stores
`4.905810000000001`, the non-understating binary64 value. Raw response is not retained.

179 focused parser, HTTP, Yahoo, research, CLI, publication and screening tests pass
(the last default-transport boundary test passed separately in the 40-test issuer
suite). Strict mypy, Ruff, formatting, workflow validation, both evaluations, build,
both Compose configs and diff checks pass. All 39 disposable real-store tests pass,
including issuer evidence through Chroma, Neo4j, screening, PostgreSQL reopen and
dashboard recomputation. The full opt-in run passed 1,267 tests in 229.14 seconds
with zero skips; the added default-transport test also passed independently, for
1,268 covered tests in the final worktree.

The first full run had 1,220 passing tests and 38 fixture errors because Docker
Desktop was stopped. After restoring healthy services, all 39 real-store tests
passed. The first live publication failed before source collection because Neo4j
was unavailable; explicit retry published six documents to each store:

- Version: `issue79-20260927T0910Z`.
- Digest: `cd64768184623ad05f2591630c4201fdc108189d9c1e40a90c15066416d80482`.
- Previous active version: `20260926T145330Z`, retained without repair.

Visible five-candidate acceptance passed, and passed again after the remediation in a
freshly restarted Streamlit dashboard, with the
approved 12-year, moderate-risk, balanced profile, 25% maximum drawdown, $25,000
initial amount, $500 monthly contribution and five evidence candidates. With local
source evidence and PostgreSQL retention enabled, the workflow reached Human review
without a screening or construction error. The deterministic portfolio had five
positions and 100.00% total weight: VEA 14.38%, VWO 14.38%, SPY 14.37%, VTI 14.37%
and eligible defensive BND 42.50%. Source evidence and screening details were present
for all five candidates.

The optional grounded-explanation path was also exercised and independently stopped
after screening because the configured local Ollama provider rejected its credentials.
That provider-specific authentication failure is not bypassed or attributed to BND;
the successful portfolio acceptance therefore disabled the optional explanation while
retaining source evidence and durable local review. Independent review remains pending.

## One permitted remediation

Initial independent review identified two frozen-contract gaps: self-consistent
issuer pairs could contain fewer or more than ten holdings, and elapsed checks around
blocking HTTP reads could not interrupt continuously trickling headers or bodies.

The shared publication/screening boundary now requires exactly ten issuer holdings.
Nine- and eleven-row schema-2 pairs with valid proofs/fingerprints both fail before
publication or screening. The regression tests were also exercised against the
prior boundary reconstructed in memory: both failed with `DID NOT RAISE ValueError`.

A deadline watchdog now retains the connected socket and shuts it down at the
remaining total deadline, including after HTTPResponse takes socket ownership.
It spans header and body operations and is cancelled on close or failure. Existing
connect/read/attempt/byte/row/redirect bounds remain intact. Deterministic injected
timer tests and real socket-pair continuous-trickle tests verify both headers and
bodies terminate with the fixed elapsed-limit diagnostic. The issuer suite passes
46 tests. The post-remediation full opt-in suite passes 1,274 tests with zero skips;
Ruff, formatting, strict mypy, workflow validation, both evaluations, build, both
Compose configurations and the diff check also pass.

## Issue 81: Connection setup deadline repair

PR #80 review found that pre-socket DNS/TCP setup could exceed the remaining
total deadline despite the header/body watchdog. The user approved successor
Issue #81 under its frozen ordinary transport-repair capsule; Issue #79's
delivered ledger and acceptance remain historical evidence.

Connection construction and connect now run in a connect-only daemon worker.
The socket timeout and caller wait both use the lesser of five seconds and the
remaining total deadline. A lock gives either the caller or an abandoned worker
cleanup ownership. A late worker never performs HTTP request/response work and
closes its discarded connection on return. Cleanup runs outside the ownership
lock so a delayed close cannot keep the caller waiting. Total exhaustion retains
`issuer_elapsed_limit`; ordinary connect expiry retains the three-attempt retry
path and sanitized `issuer_unavailable` failure.

Failed-first regressions demonstrated the fixed five-second timeout rather than
the remaining 0.25 seconds, and callers still blocked during delayed pre-socket
setup under both limits. The final 52-test issuer suite covers delayed constructor
and connect work, late cleanup with zero requests, sanitized retries and existing
real-socket header/body trickle interruption. Ruff, formatting, strict mypy,
workflow validation, both evaluations, build, both Compose configuration checks
and diff checks pass. A fresh official read returns the same August 31 effective
date, 16,300 rows, ten holdings and concentration `4.905810000000001`.

The final-source full opt-in run passes all 1,280 collected tests with zero
skips, including all 39 disposable real-store tests. Earlier in-progress runs
were stopped when source changed, so they are not used as final acceptance.

Python cannot forcibly terminate an operating-system resolver that ignores its
timeout. Such work may remain in a daemon thread until the OS returns; its result
is discarded and closed, and it cannot parse or publish evidence. No graph,
checkpoint, evidence, parser, freshness or portfolio contract changes.
