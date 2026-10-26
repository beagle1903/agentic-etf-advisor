# ADR 0042: Proposed audited curator-assigned economic Fund identity

- Status: Proposed; design-only Issue #124. No runtime policy is activated.
- Date: 2026-10-26
- Authority: approved generation 2 design capsule `51714f9efe5ae108cc76b88a04304e18e2a2157a60bd23d548bfa764881ace20`; [complete handoff](../../iterations/035-issue124-curator-identity-design.md) and [A124-1 arbitration](../../workflow/issue124-arbitration.md).
- Future implementation requires separate authorization and consequential gates.

## Context

[ADR 0039](0039-us-eu-currency-contract.md) uses an attributed issuer fund/subfund
group, exact same-group equality, and one selected listing per economic group.
The current schema 1 [reference contract](../../us-eu-research.md) calls the group
unit `issuer_fund_id`. An issuer's share-class or product number and an umbrella
name do not, by themselves, identify the legal Fund across classes. The bounded
Issue #123 corpus did not demonstrate a separate issuer Fund code; it does not
establish that no such code exists elsewhere. The proposal defines a distinct,
honestly labeled curator-assigned policy without altering that existing contract.

## Proposed decision

An authorized curator assigns one opaque stable key to one explicitly identified
legal Fund/subfund across directly proven classes:
`curator-fund-v1:<registry-uuid>:<fund-uuid>`. UUIDs are canonical lowercase v4,
generated through an injected identifier boundary. Exact full-string equality
defines equality. A registry generation, Fund name, membership set, issuer code,
or source URL cannot become the key. Issuer identifiers remain separately
attributed evidence. One review pins one registry lineage and generation; mixed
or stripped markers fail. No equivalence with schema 1 issuer groups is inferred.

Before issuance, retain official issuer or exchange evidence identifying the
legal issuer, jurisdiction, umbrella where applicable, distinct Fund, and direct
membership of each checksum-valid class ISIN. Establish current applicability and
distinguish active, authorized-only, closed, and unknown classes. Compare the
candidate against every retained Fund, alias, tombstone, and other new candidate,
including plausible continuity or transfer. Exact context collisions, overlapping
ISIN membership, and diagnostic-normalized name collisions suspend issuance until
source-backed same/distinct dispositions resolve them. NFKC, casefold, whitespace
collapse, and punctuation removal only find candidates; they never prove identity.
Distinct Funds with the same name require affirmative separation proof.

The curator and a distinct independent reviewer are named authorized actors,
human or project-scoped agent, with identity, role, authorization reference and
disposition retained. Software checks structure, source references, consistency,
and bindings. Neither hashes nor audit assertions authenticate official source
truth, actor identity, or real-world completeness.

The proposed immutable versioned registry uses the exact `RegistryEnvelope`,
`CurrentProof`, `Transition`, and `InventoryCheck` shapes in the
[design handoff](../../iterations/035-issue124-curator-identity-design.md#proposed-future-json-contracts).
Each touched context has a complete asserted inventory of parent and proposed
registered classes plus newly observed rows. Publication validates the actual
retained parent, mechanically derived transition coverage and entry digests,
source chronology, complete comparisons, attestation, and expected-parent-digest
CAS before atomic active-pointer replacement. Existing keys, members, aliases,
sources, and tombstones cannot disappear. Corrections append new source IDs.
Unexplained or unmappable changes suspend affected Funds. A rename retains the
key only with continuity evidence and the former context as an alias; potential
renames cannot receive a fresh key as a workaround. A proven survivor retains its
key in succession, an absorbed Fund retires, and a genuinely new Fund follows
issuance. Related keys describe succession, never equality.

Current Fund, inventory, active-class membership, and needed current-context
links have explicit proof. Assertions in another context need one fresh,
source-backed link to the Fund's current context. Historical lineage evidence
keeps the original rename/succession chain but cannot establish current identity.
Let `C(F)` contain the source IDs in current Fund, inventory, every membership,
and every required current-context link; lineage-only sources are excluded.
`C(F)` is nonempty and the group observation is its minimum `observed_at`.
**Every** constituent independently must satisfy the existing inclusive
`T - 120 hours <= observed_at <= T + 5 minutes` window at saved check time `T`.
A source used in both historical and current roles receives that current check.
Effective/publication dates inform applicability; downloading, attesting,
registry editing, and binding never renew source observation time.

Future reference schema 2 would require `identity_contract="curator-fund-v1"`,
the complete bound registry envelope, and the existing five complete records,
within ten listings and one MiB. Its group unit would be `curator_fund_id`,
provider `audited_curator_registry_v1`, with a primary official Fund-proof URL.
Available groups must resolve to active Funds and matching active class ISINs;
missingness remains explicit. Absent-by-default identity markers would propagate
through US/EU profile, research, evidence, screening, construction, and
explanation. Null, unknown, mixed, removed, or downgraded markers reject. Numeric
research schema 2 remains independent. Schema 1 and absent-marker legacy bytes,
IDs, digests, references, and saved reviews are never migrated or rebound. Saved
contract switches require a new review.

Canonical registry snapshots use sorted object keys, compact UTF-8 JSON,
`ensure_ascii=False`, no floats, and validated canonical arrays. The SHA-256
digest binds an immutable generation and parent digest. Limits are 128 KiB,
32 Funds, 256 total members, 256 sources, and 1,000 characters per text field;
over-limit input blocks instead of pruning. Raw source bodies stay in ignored
local audit material. Future records retain bound proof; fingerprints, manifests,
receipts, and artifacts include the marker and proof. Offline restore rechecks
the bound envelope, current proof and saved check time with zero external reads.
It cannot rederive parent-relative completeness without the parent; it trusts
the bound publication attestation for historical transitions. No new top-level
graph key or side-effect stage is proposed.

## Consequences and verification

This is a proposal only. It makes no change to current APIs, graph/checkpoint
JSON, schema 1 references, live data, financial/category rules, source adapters,
or stores. It issues no real key and activates no policy. Future implementation
must follow the [bounded plan](../../iterations/035-issue124-curator-identity-design.md#bounded-future-implementation-and-verification-plan)
and [curation runbook](../../curator-fund-identity-proposal.md), under separate
authorization. Focused cases must prove cross-class equality, distinct Funds in
one umbrella, collision and rename handling, class lifecycle, exact freshness,
legacy byte compatibility, and offline replay. Source coverage, US ISIN
availability, live portfolio readiness, and actor/source authenticity remain
unproven. Issue #121, #123, #117, and PR #122 retain their own outcomes and gates.
