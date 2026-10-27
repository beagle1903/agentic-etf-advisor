# Proposed curator Fund identity: curation and validation runbook

Status: **historical Issue #124 design and curation worksheet**. Issue #126
implements its bounded local contracts; this worksheet still issues no key,
reads no provider, publishes no registry, alters no reference file and changes
no saved review. The default path remains [schema 1 issuer identity](us-eu-research.md).
Read the [proposed ADR 0042](architecture/decisions/0042-proposed-curator-fund-identity.md)
and [complete generation 2 design](iterations/035-issue124-curator-identity-design.md)
for the approved Issue #126 implementation. The bounded Issue #123 corpus
does not establish a universal absence of issuer Fund codes.

## Evidence worksheet for a future authorized curation

1. Fix one legal context: issuer legal name, jurisdiction, distinct Fund/subfund
   legal name, and umbrella legal name if present. Keep the source's original
   spelling. An umbrella, product, family, index, ticker, or class label does
   not identify the Fund.
2. For each candidate class, record its checksum-valid exact ISIN and direct
   official issuer/exchange source that binds it to that Fund. Label class
   status active, authorized, closed, or unknown; authorization alone does not
   prove launch. Record the complete asserted Fund/class inventory and every
   newly observed row.
3. For each source, retain authority, provider, HTTPS URL, body SHA-256, precise
   locator, original UTC observation and collection times, effective date,
   publication instant/date when known, and an explicit current-applicability
   statement. A historical prospectus may prove an event; its download time
   cannot make its Fund/class assertion current.
4. Compare the candidate with all retained keys, aliases and tombstones and all
   other new candidates, including other legal contexts where a rename,
   transfer, merger, or split is plausible. Record a source-backed same,
   distinct, or unresolved disposition. Flag exact-context and overlapping-ISIN
   conflicts and NFKC/casefold/whitespace/punctuation name collisions. A
   normalized match is a review lead, not equality proof. Resolve distinct
   same-name Funds with affirmative legal separation evidence.
5. Reconcile the previous and proposed inventories. Each touched context must
   cover all previously registered and proposed members and newly observed
   source rows, with exact before/after statuses. An unexplained missing,
   added, changed, or unmappable row suspends affected Funds. An unresolved
   possible rename blocks a new key.
6. Record one named authorized curator and a distinct independent reviewer,
   their roles, authorization references and dispositions. They may be humans
   or project-scoped agents. This records audit assertions; it does not
   authenticate them. Keep raw source bodies in ignored local audit storage.

No real candidate, ISIN, key, or registry entry is supplied by this proposal.
The [Issue #121 source report](iterations/033-issue121-reference-preparation.md)
is historical evidence of missing strict fields, not a curation certificate.

## Proposed publication decision table

| Scenario | Required disposition |
| --- | --- |
| New Fund with direct current Fund, inventory and class proof, resolved comparisons, and independent review | Issue one opaque `curator-fund-v1` key through injected ID generation. |
| Same Fund, different directly proven class ISINs | Retain one key; add members with matching inventory and transition evidence. |
| Distinct Funds under one umbrella or with the same marketing name | Keep separate keys only with explicit distinct legal Fund evidence. |
| Proven legal-context rename | Keep the key, append former context as alias and event evidence, then require fresh current-context Fund/class/inventory proof. |
| Possible rename, overlapping ISIN, normalized-name collision, conflicting source, or unexplained inventory | Suspend affected issuance or Funds until resolved; no fresh-key workaround. |
| Class launched, closed, or changed | Retain historical member and proof; record exact status/source transition and inventory rows. |
| Merger, split, or transfer | Record related-key succession and affected transitions; retain a proven survivor, retire an absorbed Fund, or require new-Fund issuance where genuinely distinct. Unsupported continuity stays suspended. |
| Stale or missing current proof | Reject active use even if historical alias and lineage evidence is intact. |

Publication would compare against the **actual retained parent**, validate all
mechanically derived transitions and exact entry digests, then use an
expected-parent-digest CAS and atomic pointer replacement. Immutable generations,
sources, members, aliases, and tombstones remain available. The full
`RegistryEnvelope` and bounds are specified in the
[handoff](iterations/035-issue124-curator-identity-design.md#proposed-future-json-contracts).
This document does not create a registry or prescribe a live publication command.

## Current proof and time checks

For an active Fund, bind current Fund identity, complete inventory, every active
class ISIN membership, and any required current-context link. Each assertion's
context is the actual source context. If it differs from the Fund's current
context, one fresh source-backed link must reconcile it. Historical rename or
succession sources remain immutable lineage evidence; they cannot substitute
for current proof.

At saved check time `T`, form `C(F)` from current Fund, inventory, membership,
and context-link source IDs. Require it nonempty. The group observation time is
the minimum original observation in `C(F)`, and **each** member of `C(F)` must
independently meet the inclusive 120-hour age and five-minute future windows.
Checking only the minimum misses a future-dated constituent. A source used in
both current and historical roles is checked as current. Effective/publication
dates help establish applicability; collection, attestation, registry write and
reference binding never renew an observation.

Fresh future reference binding would replace destination ingestion/version only;
the source facts, proof bytes and original observations stay exact. Future schema
2 would use explicit `identity_contract="curator-fund-v1"`, group unit
`curator_fund_id`, provider `audited_curator_registry_v1`, a complete bound
registry envelope, and the existing five-field, ten-listing/one-MiB limits.
Schema 1 retains `issuer_fund_id` and its existing bytes. Offline restore must
validate the bound current proof against the **saved** check time and issue no
external read. The parent digest commits to history but does not reconstruct it;
offline replay trusts the bound publication attestation for parent-relative
transition coverage. Neither the digest nor an audit assertion proves source
truth or actor authenticity.

## Future implementation checks and stop conditions

Implement only under a separate approved consequential ticket. Start with pure
registry/proof validation and a replaceable local CAS adapter, then versioned
reference binding, then explicit marker/proof propagation through research,
review/revision and explanation. Preserve the financial/category rules,
one-per-group selection, graph JSON serializability and replaceable side-effect
boundaries. No automatic migration or saved-review contract switch is allowed.

Focused tests should cover cross-class equality; distinct Funds in one umbrella;
same names in distinct contexts; Unicode/punctuation collisions; proved rename
with old lineage plus fresh current proof; stale/missing current proof; conflicting
contexts without a fresh link; each inclusive freshness edge; class launch and
closure; succession; omitted inventory or transition rows; stale CAS; tampered
digests/references; mixed/stripped markers; unchanged schema 1 golden bytes;
detached binding; and offline restore with registry/provider access disabled.
An actual implementation must still establish source coverage, live ISIN and
category availability, and portfolio readiness; this design does not certify any
of them. Ambiguous equality, proof, replay or compatibility semantics return to
the consequential design gate instead of being filled in by code.
