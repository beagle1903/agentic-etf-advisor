# ADR 0028: Official BND holdings and field-specific monthly freshness

- Status: Accepted design; implementation acceptance pending independent review.
- Date: 2026-09-27
- Issue: https://github.com/beagle1903/agentic-etf-advisor/issues/79
- Capsule: `issue-79-bnd-market-value-evidence`, generation 1,
  digest `a8ce5016cec689ad81fdb7d34da97a13a63e0ed9222c52461928fd96a935f777`.

Yahoo does not currently report BND holdings. The user approved a bounded official
Vanguard fallback and a 45-day window for its monthly holdings. Signed economic
values, repeated bonds and blank percentages preclude residual completeness inference.

The injected HTTPS client fixes the Advisors port-0928 endpoint, validates TLS,
rejects redirects and content encoding, streams at most 16 MiB, allows at most
three transient attempts, and arms a watchdog for the remaining 90-second budget.
The watchdog shuts down the retained socket during header or body reads even when
bytes trickle continuously or the HTTP connection has detached socket ownership.
Responses cancel their watchdog on close. Connect and read
timeouts are five and ten seconds. The pure parser rejects duplicate keys, invalid
dates, extra date buckets, malformed scoped rows and more than 25,000 scoped rows.

Validate every fixedIncome and shortTermReserves row. Only present, exactly empty
percentage, market value and face amount together authorize exclusion as a non-valued
placeholder. All other rows require exact bounded market values. Blank percentages
remain in ranking but may not enter the selected ten. Rank descending exact market
value, then collection order and original row index. Repeated identities and negative
values remain distinct. Selected market values and percentages must be nonnegative;
percentages must be at most 100. Exactly ten original percentages sum rationally to
at most 100. Existing schema-2 proofs and upward binary64 conversion preserve the sum.

Unavailable Yahoo BND holdings invoke the injected issuer client. Complete Yahoo
holdings and other symbols make no issuer calls. Holdings and concentration receive
the same issuer provider, fixed URL and effective-date UTC boundary atomically, or
the new snapshot fails before persistence/publication.

One pure resolver serves CLI assessment, publication and screening/replay. Only
vanguard_advisors, BND, the exact URL and the two composition fields receive 1,080
hours. Pair provenance must match and contain exactly ten holdings even when a
truncated or oversized pair has a self-consistent concentration and fingerprint.
Future issuer dates fail without clock tolerance.
Document health and other fields preserve existing policy. Screening messages expose
the issuer field window. No schema, fingerprint, allocation, financial threshold,
universe membership or historical-state migration changes.

Placeholder interpretation is user-approved, not a completeness guarantee. Live
source changes still fail closed and never convert missing evidence into a pass.
