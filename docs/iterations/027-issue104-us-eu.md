# Iteration027: Issue104 US/EU and currency implementation

## Authorized slice

Implement the approved generation2 [handoff](027-issue104-us-eu-design.md),
preserving legacy US/USD payloads and Issue99 bytes. INV104-1/4, AC104-1/2 cover
listing/source identity; INV104-2/AC104-3 economic groups; INV104-3/4, AC104-4 exact
cash/FX; INV104-5/AC104-5 semantic dispatch, replay, explanation and publication.

Owner responsibilities are implementation_worker. Sequential actual successor
`/root/issue104_owner_sol61`, gpt-6.1-sol/medium, follows the explicit user-approved
[one-off exception](../workflow/issue-104-model-exception.md). Both actual owners
are implementation/verification authors, excluded from independent review.
Original logical reservation/counts/capsule remain unchanged. Coordinator owns
ledger and independent gates; this document grants no phase or acceptance.

## Result

Schema2 research/source fingerprints bind `us-eu-v1` facts. Exact exchange mapping
establishes listing region; canonical ETF/currency/quote units retain missingness
and freshness. Replaceable reference readers validate complete bounded input
before fresh-only detached destination-coordinate binding. Source observations
and citations remain exact; canonical retry/restoration never consult the file.

Bounded selection keeps alternative group representatives, blocks contradictory
ISIN/group data, permits at most one selected group and audits omitted duplicates.
Original financial rules remain unchanged. USD/EUR integer base cash and exact
rational half-up conversion expose base/trading amounts and ECB reference digests.
FX is a one-shot injected retrieval side effect inside the original artifact/receipt.

Creation, complete-input revision, screening/construction, explanation references,
dashboard and restore dispatch identically. Saved contract changes reject. Base
changes explicitly supply both cash amounts and refresh evidence/FX. Downstream
revision/restore reuse original check time without network. Monetary grounding
checks exact labelled pairs against cited monetary records along with existing
reference/numeric/subject/safety rules.

## Evidence and limits

`tests/test_us_eu_contract.py` covers all42 mapped exchanges, unsupported venues,
missing/conflicting identity, subunits, economic duplicates/alternative feasible
representatives, zero/one/max minor cash, both FX directions/exact boundaries,
bounded parser/transport, reference T0 to T1/T2 source-preserving binding and age
edges, malformed input/canonical reload, semantic/flat/group/FX/cash tampering,
graph restore/downstream reuse/base revision/receipt/approval, monetary negatives
and exact legacy USD vectors. Separate `us-eu-contract-v1` has ten synthetic cases.
Issue99 datasets remain unchanged. Gate results go to the coordinator for reserved
content-bound verification and independent review; this is not ticket acceptance.

No live publication or saved-review mutation was performed. Live EU completeness
and ready live portfolios are unproven. Structurally validated source curation is
not authenticated truth. Synthetic fixtures do not establish live facts,
suitability, executable FX or returns. See [ADR0039](../architecture/decisions/0039-us-eu-currency-contract.md)
and [usage](../us-eu-research.md).

## Initial-review repair: Streamlit script entry

Independent initial review demonstrated an AC104-5/INV104-5 failure: the script
called `main()` before defining `_decimal_minor` and `_currency_minor`. Imported
helper tests passed, but actual US/EU creation failed and saved cash rendering
raised NameError. The approved owner's single reserved remediation moves only the
`__main__` invocation below both helpers; no financial or persistence rule changes.

Two actual Streamlit AppTest script-entry regressions failed before that move and
passed afterward. They cover EUR0.01/0 cash creation and displayed totals, then
an existing managed US/EU review's explicit USD-to-EUR profile revision with both
cash amounts and a child revision. Tests use process-local policy-only reviews,
without stores, providers, publication or saved live-review mutation.

The complete US/EU, dashboard and dashboard-revision focused test set passes;
changed-file lint/format checks and diff checks pass. Self-review confirms the
source change only orders script execution after helper definitions. Prior failed
review remains failed; fresh content-bound verification and independent final
review remain required before acceptance.

## Additional finite repair: B104-EMPTY-EVIDENCE

Independent final review demonstrated AC104-2/5 and INV104-4/5 failure: opted-in
US/EU searches with zero results or all rejected candidates attempted a blocked
schema2 bundle, but the empty candidate list inferred legacy schema1 and raised
validation instead. The user authorized one additional remediation and independent
final review. Prior failed reviews remain failed.

The narrow repair uses the explicit semantic contract as encoding fallback only
when no candidate encoding exists: US/EU empty bundles require explicit schema2;
legacy empties retain schema1. Nonempty candidate-derived encoding, strict marker
requirements and mixed/downgrade rejection stay unchanged. No eligibility, cash,
FX, publication or persistence policy is changed.

Six regressions failed before the fix and passed afterward: zero-result,
all-invalid-source and all-stale outcomes, both directly and through graph routing.
They verify retained blocked errors, schema2 JSON roundtrip, guardrail routing,
checkpoint restoration and no unintended FX/provider calls. An exact legacy-empty
wire dump passes before/after; explicit nonempty schema/downgrade protections pass.
The final focused evidence/US-EU/revision/workflow run passes all301 tests. An
earlier focused run hit the existing Streamlit10s timeout; that exact test passed
alone, then the full focused set passed serially without timeout or source changes.
Changed-file lint/format and diff checks pass. Fresh reserved verification and
independent final review remain required before blocker closure or acceptance.
