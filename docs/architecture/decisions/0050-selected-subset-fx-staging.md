# ADR 0050: Stage US/EU FX after pure portfolio selection

- Status: Accepted design for Issue 115; implementation subject to independent review.
- Date: 2026-11-12
- Authority: approved [Issue 115 design](https://github.com/beagle1903/agentic-etf-advisor/issues/115#issuecomment-6820935128).

## Decision

Fresh evidence-enabled `us-eu-v1` roots pin `fx_staging: selected-subset-v1` in revision inputs and the final evidence bundle. The marker is absent from legacy, starter and policy-only paths. Historical absent-marker US/EU reviews retain their original raw-result FX decision and exact serializers and receipt input digest. A saved revision cannot switch the marker. Null, unknown, mismatched and lost markers fail validation.

Marked retrieval validates the complete profile and stored deterministic policy, collects research once, captures one check time, and applies actual screening and construction policies through the constructor's pure selection prefix. The prefix includes all pre-FX blockers, category and economic-group rules, catalogue shortlist, feasible subset, weights and base cash. Blocked and base-only selections record `not_requested` without an ECB call. A selected cross-currency position, even with zero cash, invokes the injected bounded ECB adapter at most once inside the existing prepared, permitted retrieval operation. Failure records `source_unavailable`; stale and future observations retain their original typed construction blockers. There is no new operation stage or automatic retry.

The marked retrieval receipt input digest includes the full profile, candidate limit, marker, screening policy and construction policy. The output artifact and digest cover the final evidence bundle, including FX disposition, observation, provenance, check time and request context. Replay rechecks disposition against the original producing revision and its policies. A downstream policy child reuses immutable evidence and cannot acquire FX offline; a new foreign selection with skipped FX blocks. Explicit profile or evidence refresh starts a new retrieval, while a base-currency edit requires both cash amounts. Original saved FX remains reusable at its original check time.

If a required provider returns `missing/not_requested`, retrieval rejects that as a usable
observation and records `source_unavailable`; construction then blocks with `fx_missing`.
This is the coordinator's approved interpretation of an invalid required-provider return,
and does not classify it as a successful rate or an intentional FX skip.

## Limits

The prefix chooses the existing deterministic illustrative portfolio, not an optimized or personalized recommendation. It does not change the ECB transport, exact-money conversion, human review, provider boundaries or financial-write approval. Historical hashes and stored records remain structural integrity evidence, not authentication against an attacker able to replace an entire checkpoint and all hashes. Live source completeness and legal fund identity remain separate questions.
