# Issue124: audited curator-assigned economic Fund identity

Status: generation 2 DESIGN_READY handoff. The independent generation 2 challenge
passed and the coordinator approved this design-only documentation scope; the
initial challenge failure and one design reset remain in the
[native ticket history](../workflow/tickets/issue-124.json) and
[A124-1 arbitration record](../workflow/issue124-arbitration.md). Proposal only;
no runtime policy, key, reference or registry is activated.
Architect `/root/issue124_policy_design`, followed by the narrow freshness reset
by `/root/issue124_freshness_design`, both design_architect/gpt-6-astra/high.
Coordinator transcription under A124-1. Capsule generation2 digest
`51714f9efe5ae108cc76b88a04304e18e2a2157a60bd23d548bfa764881ace20`.
The initial challenge failed; that outcome remains recorded. The revised handoff
passed a separate generation 2 challenge and received coordinator approval for
documentation. See [proposed ADR 0042](../architecture/decisions/0042-proposed-curator-fund-identity.md)
and the [future curation runbook](../curator-fund-identity-proposal.md).

The human selected audited curator-assigned keys with strict Fund/class proof and
alias/rename safeguards. This issue is design/documentation only. The future
interface and JSON contracts below are specifications, not current behavior.
Current product, state, financial rules and existing source/reference data remain
unchanged.
Issues121/123/117, their failed passes, counts and bindings are preserved.

## Execution-path evidence

`reference_facts.py` requires five complete objects, not five positive values.
Schema 1 is bounded to ten listings and one MiB; binding changes destination ingestion/version
only. ResearchField and ETFResearchRecord validate provenance/units but do not
authenticate source truth. Current economic_group_id unit is issuer_fund_id.
Construction checks same-ISIN group contradictions and deduplicates equal group
strings; different classes assigned different keys can evade that equality guard.
Encoding, fingerprints, evidence and review/revision preserve canonical facts,
not semantic source authenticity. These are the paths the future proposal affects.

Existing legal source evidence was inspected in Issue #123, not reacquired here:
the iShares VII plc prospectus PDF page 16 / printed page 11 identifies the named
Fund separately from its umbrella; PDF page 21 / printed page 16 associates
classes, with only the USD accumulating class marked L in the cited unhedged row;
PDF page 33 gives the Fund base as USD. The class ISIN is separately on the
issuer page. Source SHA-256:
`d6b2e9451727e32032de96c131c9fdc22d20070886f2bf16e7a8ed48fd9e5348`.
Vanguard associated Fund IDs distinguish ETF and other share-class numbers.
The bounded corpus did not demonstrate separate Fund codes; no global absence
claim follows. Legal identification is stronger than marketing-name resemblance,
but no unapproved name-derived key is inserted.

## Identity, source proof and issuance

Proposed opaque stable key: `curator-fund-v1:<registry-uuid>:<fund-uuid>`.
UUID components are canonical lowercase UUIDv4 through an injected identifier
boundary. Exact complete-string equality defines key equality. Registry generation,
names and membership sets never enter the key. Issuer codes remain separately
attributed evidence; they are not relabelled curator keys. One explicitly pinned
registry lineage/generation per review; mixed lineage/generation rejects. No
federation or implicit equivalence with legacy issuer-ID groups.

One key represents one explicitly legally identified Fund/subfund across classes.
Before issuance, the authorized curator must retain official issuer/exchange
evidence of legal issuer/jurisdiction/umbrella-if-applicable/distinct Fund and
direct membership for each checksum-valid classISIN. Establish current applicability
and distinguish launched, authorized-only and closed classes. Downloading an old
prospectus is not current-applicability proof by itself.

Compare against every retained registry Fund, alias and tombstone, including other
contexts where continuity/transfer may be plausible. Record each candidate match
and source-backed same/distinct/unresolved disposition. Reconcile the complete
official Fund/class inventory for the legal context against the previous observation.
Unexplained missing/new/changed rows suspend affected contexts/Funds.

Exact contexts, aliases, overlapping ISIN membership and diagnostic-normalized
name collisions block issuance until resolved. Diagnostic normalization is NFKC,
casefold, whitespace collapse and punctuation removal: it only raises candidates,
never proves equality. Distinct same-name Funds require explicit separation proof.

The curator and a distinct independent reviewer are named authorized actors; either
may be human or project-scoped agent. Record identity, role, authorization reference
and review disposition; enforce inequality and applicable author independence.
There is no human-only staffing or routine signoff queue. These are audit assertions,
not authenticated identity/live-session provenance. Existing native design,
challenge, coordinator, write-owner/review gates and external-financial-write
approval remain intact. Software validates completeness/consistency/binding,
not source truth, real-world exhaustiveness or actor authenticity.

## Proposed future JSON contracts

Type specification only; no real keys or actual registry data:

```text
RegistryEnvelope {
  digest:sha256,
  snapshot:{
    schema_version:1, policy:"curator-fund-v1", registry_id:uuid,
    generation:positive_integer, parent_digest:sha256|null,
    recorded_at:timestamp, sources:Source[], funds:Fund[],
    audit:{
      curator:Actor, reviewer:Actor, attested_at:timestamp,
      compared_parent_digest:sha256|null,
      comparisons:[{left_key:string,right_key:string,
        disposition:"same"|"distinct"|"unresolved",source_ids:string[]}],
      transitions:Transition[], inventory_checks:InventoryCheck[]
    }
  }
}
Actor { identity:string, role:string, authorization_reference:string,
        review_disposition:string }
Source {
  id:string,authority:"issuer"|"exchange",provider:string,url:https_url,
  body_sha256:sha256,locator:string,observed_at:timestamp,collected_at:timestamp,
  effective_date:date|null,published_at:timestamp|null,publication_date:date|null,
  current_applicability:string
}
Context { issuer_legal_name:string,jurisdiction:string,
          umbrella_legal_name:string|null,fund_legal_name:string }
Fund {
  key:string,status:"active"|"suspended"|"retired",context:Context,
  current_proof:CurrentProof,
  aliases:[{context:Context,source_ids:string[]}],
  members:[{isin:string,status:"active"|"authorized"|"closed"|"unknown",
            source_ids:string[]}],
  lifecycle_source_ids:string[],related_keys:string[]
}
CurrentProof {
  fund:{context:Context,source_ids:string[]},
  inventory:{context:Context,source_ids:string[]},
  memberships:[{isin:string,context:Context,source_ids:string[]}],
  current_context_links:[{from_context:Context,to_context:Context,
                          source_ids:string[]}],
  lineage_source_ids:string[]
}
Transition {
  key:string,before_digest:sha256|null,after_digest:sha256,
  operations:("issue"|"refresh"|"rename"|"membership"|"suspend"|
              "retire"|"succession")[],source_ids:string[]
}
InventoryCheck {
  context:Context,source_ids:string[],rows:[{
    key:string|null,isin:string|null,source_locator:string,
    before_status:"active"|"authorized"|"closed"|"unknown"|null,
    after_status:"active"|"authorized"|"closed"|"unknown"|null,
    disposition:"unchanged"|"added"|"closed"|"changed"|"unresolved",
    source_ids:string[]
  }]
}
```

Unknown/duplicate keys and nonfinite values reject. Dates are ISO dates, timestamps
UTC instants, IDs/hashes canonical. Source references must resolve; active Funds
require identity/inventory proof and active members direct class membership proof.
Exact source spelling remains; normalized names are never persisted identity.

Bound canonical snapshot128KiB,32Funds,256totalmembers,256sources,1000characters
per text field. Over-limit blocks, not pruning. Raw bodies remain ignored audit
material. Digest is SHA256 of UTF8 snapshot JSON: sorted object keys, compact
separators, ensure_ascii=False,no floats; validated canonical arrays byID/key/ISIN.
Retain immutable generations/parent links. Replaceable local publication uses
expected-parent-digest CAS and atomic active-pointer replacement; stale/conflicting
publication fails. No database/authentication platform is proposed.

## Parent transitions, inventory and lifecycle

Publication compares with the actual retained parent, not caller summaries.
Exactly one transition covers each added/changed Fund, none unchanged; exact
before/after entry digests and operations cover mechanically derived changes.
Keys, historical members, aliases and sources cannot disappear. Sources append;
corrections get new IDs; existing source-object edits reject. ISINs cannot be
replaced in place.

- New Fund: issue operation, direct proof, complete duplicate comparisons against
  every retained parent Fund and every other new Fund.
- Context/name change: rename operation, exact former context appended as alias,
  continuity source; no continuity means no fresh-key workaround.
- Member addition/status/source update: membership or refresh, exact matching
  inventory rows and evidence. Closure retains the member and proof.
- Transfers/mergers/splits: succession operations, related affected-key transitions
  and event evidence; unsupported continuity remains suspended.
- Suspend/retire explicitly; no deletion or key reuse. Proven survivor keeps key,
  absorbed Fund retires, genuinely new Fund needs issuance procedure. related_keys
  records succession, not equality.

For every touched context, inventory rows cover union of parent/proposed registered
members, no duplicates, statuses exactly matching both snapshots. Include newly
observed source rows. Unresolved/unmappable rows suspend affected Funds; active
affected Funds reject. Actors attest source-inventory completeness. Software
cannot discover omitted source rows or authenticate semantic truth.

## Future reference integration, freshness and replay

Propose reference schema2 with required identity_contract="curator-fund-v1",
RegistryEnvelope and existing five-object records, total<=10listings/1MiB.
Curator group unit="curator_fund_id",provider="audited_curator_registry_v1";
source_url points to primary official Fund proof. Available values resolve to
active registry Fund and active matching classISIN. Missingness stays explicit.
Do not overload schema1 issuer_fund_id; schema1 remains byte-compatible.

Add absent-by-default identity_contract to US/EU profile, researchsnapshot/records,
evidence,screening/construction,explanation. Exact markers must agree; null,unknown,
mixed,stripped,downgraded forms reject. Saved contract switches require new review.
Numeric researchschema2 remains unchanged. Proposed records retain complete bound
registry envelope; scalar metadata carries canonical JSON/digest. Bounded proof
duplication supports offline candidate validation; existing sizes still block excess.

ResearchField needs no new properties. Evidence roles belong to proof references,
not permanently to Source objects. Every active Fund requires current_proof:
fund.context equals its current Fund context; sources establish the currently
applicable legal Fund. Inventory proves its complete current Fund/class inventory.
Membership assertions cover exactly every active classISIN with direct proof.
Required current source lists are nonempty; links and lineage may be empty only
when their conditions do not apply. Canonical ordering and no duplicates apply.
Retained member/alias/lifecycle sources cannot substitute for current_proof.

Each assertion context is the actual source context. An inventory or membership
assertion in another context requires exactly one fresh source-backed link from
that context to fund.context. A historical rename alone cannot reconcile conflicting
current assertions. Unproved links, transfers, conflicts or uncertain current
identity reject. A changed context still needs proved continuity, never name
similarity or a new-key workaround.

lineage_source_ids retain completed-event evidence connecting historical key
contexts to the current endpoint. Publication checks actual parent, typed
rename/succession transitions, exact aliases, source chronology and continuity.
After a proved A-to-B rename, fresh current B Fund/class/inventory proof binds the
same key through retained history. Unchanged B assertions need no current-context
link when all current assertions use B. Historical-only evidence retains integrity,
references, chronology and event-applicability checks without a 120-hour expiry;
it cannot establish current identity, inventory or membership and is never redated.

Let C(F) be the union of source IDs in current fund, inventory, every membership
and every current-context link. Historical-lineage-only sources are excluded.
C(F) must be nonempty; group.observed_at is its minimum observed_at. Independently,
every constituent must satisfy T-120h <= observed_at <= T+5min inclusive at saved
checked_at T. Checking only the minimum cannot detect a future-dated constituent.
A source referenced in both current and historical roles receives the full current
freshness check. Effective/publication dates inform applicability; registry edits,
attestation, downloads, ingestion and binding never renew source observations.
Fresh binding changes only
destination ingestion/version; proof bytes, source links and observations stay exact.
Fingerprints/manifests/receipts/artifacts include marker/proof. No top-level graph
key or side-effect stage is added; nested artifactJSON grows. No migration/rebinding
of old bytes,digests,IDs or saved reviews.

Publication validates current_proof and actual parent integrity, generation/CAS, complete structural
diffs/transitions/inventory and attestations. Offline current-envelope validation
repeats digest/schema/internal references/status/declared-coverage consistency,
ISIN/key association, source freshness at saved check time and artifact integrity.
It cannot independently prove parent-relative completeness without that parent.
Parent digest commits to history; it does not reconstruct it. Ancestors stay at
registry boundary, not in each record. Replay trusts bound publication attestation
for historical transition checks; neither hashes nor attestations authenticate
actors or official assertions. Fresh research rechecks current proof at its captured
check time. Restore repeats bound current-proof freshness and integrity at the saved
check time, without a new clock assessment, latest registry or external source.

## Bounded future implementation and verification plan

Actual implementation needs separate authorization and approved consequential
handoff. Proposed sequential owner: implementation_worker/gpt-6-sol/medium.

1. Pure registry/proof models/validator: new domain/fund_identity.py; local CAS
   adapter: new data/fund_identity_registry.py.
2. Versioned reference/binding integration: reference_facts.py,yahoo_research.py,
   research models/snapshot I/O,encoding.py.
3. Marker/proof propagation and validation through profile,evidence,construction,
   catalogue jobs,revision/review,explanation; no financial algorithm changes.

Future focused cases: sameFund/differentISIN; distinctFunds/oneumbrella; same names
in different contexts with separation evidence; Unicode/punctuation collision flags;
provenrename keeps key; potentialrename or unexplainedinventory blocks; class
launch/closure keeps identity; explicit succession/history; staleCAS/tamperedproof;
unresolvedrefs/marker removal/mixedgenerations; omittedtransitions/inventoryrows;
fabricatedbeforedigests/deletedhistory; unsupportedrename/transfer; exactfreshness;
old rename S1 plus fresh current B proof preserves key/alias; missing or stale
current proof rejects; mismatched current contexts without a fresh link reject;
inclusive age/future boundaries check every constituent; historical-only S1 stays
unchanged and offline replay performs zero external reads;
originalobservations/detachedbinding/JSON/fingerprints; offlinevalidation with
registry access disabled; legacy goldenbytes and unchanged category/financial/
min3/bothsleeve/FX behavior. No tests ran in this read-only design phase.

Coverage, US ISIN availability and portfolio readiness remain unproven. Independent
challenge should examine duplicate issuance across changed contexts, proof downgrade
and offline replay completeness. A124-1 records the bounded initial amendment;
material repeated concerns need an accountable coordinator decision, not a loop.

## Documentation transcription checks and limits

The approved generation 2 handoff is transcribed to
[proposed ADR 0042](../architecture/decisions/0042-proposed-curator-fund-identity.md)
and the [curation runbook](../curator-fund-identity-proposal.md). The following
pre-certification checks passed on 2026-10-26 in the documentation owner phase:

- `uv run --frozen python scripts/validate_codex_workflow.py`: valid workflow configuration.
- `uv run --frozen python scripts/ticket_workflow.py validate`: recorded ticket ledgers valid; this static check does not authenticate live phase or human authority.
- `uv run --frozen pytest -q tests/test_us_eu_contract.py`: exit 0; two cases skipped. This checks the existing issuer-group/reference path, not the proposed curator registry.
- Local Markdown link-target check for the three Issue #124 documents and ADR-number uniqueness check: passed.
- `git diff --check`: passed. This does not certify Markdown semantics or proposed legal-source truth.

These are checks of unchanged existing contracts and documentation consistency;
there is no curator-policy runtime implementation or synthetic policy test in this
issue. Content-bound owner verification, acceptance, independent review and
current-head PR CI remain separate delivery gates. Source coverage, original
official assertions, actor authenticity, US ISIN availability and live portfolio
readiness are not established by these checks.
