# Issue 126: audited curator Fund identities

Status: DESIGN_READY architect handoff approved; implementation owner pass in
progress pending content-bound verification and independent review.

Separate read-only architect `/root/issue126_design`,
design_architect/gpt-6-astra/high, returned this handoff against generation 1
capsule `c50e07ba8308449c2f0fd402de5f1a94aafe8cf7d38bb598363d349626be3335`.
Coordinator transcription. No material conflict requiring capsule revision was
identified. Approved implementation owner, once gated:
`/root/issue126_owner`, implementation_worker/gpt-6-sol/medium.

## Scope and authority

Implement [Issue 126](https://github.com/beagle1903/agentic-etf-advisor/issues/126)
under its [native ledger](../workflow/tickets/issue-126.json). The exact registry,
proof, transition and inventory shapes and substantive semantics are incorporated
from the [generation-2 design](035-issue124-curator-identity-design.md) and
[ADR 0042](../architecture/decisions/0042-proposed-curator-fund-identity.md).
Issue124 certification covered design documents only. This implementation has
separate consequential gates and content certification.

One owner pass proceeds through pure contracts/synthetic fixtures, local adapter,
reference/research codecs, downstream/replay, tests and documentation. No real key
issuance, reference curation, provider acquisition, live registry/Chroma/Neo4j
activation, saved-review migration, financial-rule change, trade or external
financial write. No Issue121/123/117 counter or authority transfer, readiness claim
or automatic merge. The human authorized routine implementation and delivery work;
architect/challenge/coordinator approval are internal gates.

## Pure identity and publication boundaries

INV126-1/2/3, AC126-1/2/3. Add `domain/fund_identity.py` with strict
RegistryEnvelope, Source, Context, Fund, CurrentProof, Transition, InventoryCheck
and audit models matching the incorporated handoff. Separate canonical envelope
and entry serialization/digests, internal envelope validation, actual
parent-relative publication validation, and available group/class resolution at
an explicit checked_at. No filesystem, network or wall clock in pure contracts.

Keys contain canonical lowercase UUIDv4 components; full-string equality defines
identity. Identifier generation is injected; names, aliases, sets and issuer codes
never generate keys. Enforce canonical snapshot 128 KiB, 32 Funds, 256 total
members, 256 sources and 1,000 characters per text field. Reject duplicate JSON
keys, unknown fields, coercions, floats, invalid dates/UTC instants, hashes/keys,
duplicates and noncanonical arrays. Compact sorted-key UTF-8 JSON uses
ensure_ascii=False. Arrays order sources by ID, Funds/transitions by key,
members/memberships by ISIN, context collections by exact canonical context;
reference lists are sorted and duplicate-free.

Active Funds require current Fund/inventory proof and memberships covering exactly
active class ISINs. Differing assertion contexts need the prescribed unique
source-backed current-context link. Retained assertions and source references are
audit input, not authenticated legal evidence. Compute C(F) from current Fund,
inventory, active memberships and required links. Each constituent independently
passes inclusive T-120h through T+5min; group observed_at is the minimum. This
fixed proof rule cannot be weakened by configurable research-health windows.
Historical-only lineage retains references, chronology, applicability and immutable
integrity without age expiry. Dual-role sources receive the current check.

Actual-parent validation derives changed Funds/operations, exact transition
coverage and before/after entry digests; complete touched-context inventories;
unchanged retained sources; retained keys, members, aliases and tombstones;
generation increment and parent lineage. Issuance compares all retained Funds
and other new entries. Same/unresolved comparisons cannot justify a second
active key. Diagnostic normalization only flags candidates. Rename retains key,
former-context alias and continuity proof. Member additions/closures retain
history. Succession needs linked affected transitions/event evidence; retired
predecessor historical membership is distinct from active duplication. Absorbed
Funds remain retired; related keys never imply equality. Unsupported changes
cannot become active via new key/free text.

Add replaceable `data/fund_identity_registry.py` with bounded immutable
digest-addressed blobs, retained generations and a small active pointer.
Publication receives expected parent digest and explicit check time, obtains
bounded cross-process exclusion, reads actual active parent, validates content
and transitions, writes/readbacks immutable content, then atomically replaces the
pointer. Follow existing local-store patterns without coupling catalogue semantics.
Precommit failure preserves prior pointer. Postcommit acknowledgement/cleanup
failure reports actual outcome, never implied rollback. Downstream has no registry
reads.

## References, collection and codecs

INV126-3/4, AC126-4/5. Extend `data/reference_facts.py` ReferenceFactsRecord,
ReferenceFactsFile, ReferenceFactsProvider, LocalReferenceFacts,
load_reference_facts and bound_reference_fields with exact schema dispatch.
Schema1 stays exact. Schema2 requires identity_contract=curator-fund-v1, complete
bound registry envelope and five complete fields per listing within ten listings
and one MiB. Available groups use curator_fund_id, audited_curator_registry_v1,
official current Fund-proof URL, derived observation and active Fund/matching
active ISIN. Missingness remains explicit.

Provider/bound-record lookup retains file contract/envelope; separate versioned
types or explicit context may implement this without allowing curator units
through schema1. Selected curator mode with insufficient input errors or blocks;
no invented proof or issuer fallback. Binding validates detached input and changes
only ResearchField ingested_at/snapshot_version, preserving proof and source facts.

YahooResearchAdapter.fetch_snapshot/_build_record/_new_listing_fields and
YahooCatalogueResearchCollector.collect retain explicit marker/proof, reject
provider mismatch and revalidate provider models (model_copy is not validation).
ETFResearchRecord/ETFResearchSnapshot gain absent-by-default marker/proof; snapshot
and records agree on one registry lineage/generation/digest. ResearchField needs
no new property.

ETFResearchSnapshot.decode_wire/serialize_snapshot currently process every field
except symbol/advisory_contract as ResearchField. Explicitly separate and reattach
identity marker/proof there and in catalogue _encoded_record/_record_from_cache.
Scalar document metadata stores canonical proof JSON/digest plus marker, covered
by existing fingerprint. encoding.document_schema/validate_document reconstruct
and validate identity metadata, canonical proof JSON/digest and partial/stripped/
downgraded rejection. Numeric schema2 remains independent. Absent-marker issuer
mode rejects surviving curator units/provider/proof or reserved curator keys;
valid_group_id's broad string grammar must not permit unit-changing downgrade.

## Consumers, entry points and saved artifacts

INV126-4/5, AC126-5/6. InvestorProfile and PolicyCalculation carry optional marker
without changing arithmetic or reading registry. Profile selects policy; evidence
pins proof. CandidateEvidence/CandidateEvidenceBundle and selection/retrieval/
provenance conversion compare candidate/metadata markers and one bundle registry.
Validate current proof at saved checked_at. Empty blocked results retain requested
marker without invented candidate proof. assess_research_fields checks current
proof at supplied time before publication: aggregate/document freshness cannot
replace each-constituent checks.

Screening results/bundles compare/propagate marker. Construction _validate_upstream,
_economic_identity, persisted validation, positions/drafts/bundles and catalogue
shortlist consume validated contract. Preserve exact group equality, same-ISIN
contradiction checks, enumeration, selection, allocations and FX. Missing identity
stays unknown/excluded; malformed/contradictory proof cannot silently become
missingness. ExplanationRequest/ExplanationBundle compare and retain marker;
complete proof stays available through evidence, never replaced by prose.

Update existing CLI research-ingestion/saved retry checks and dashboard profile/
catalogue builders to select/retain explicit identity contract. Numeric schema
does not select identity. Defaults remain legacy.

catalogue/research_job.py binds marker/proof in job references/manifests/digests,
caches and final snapshots. _references enforces consistent schema/registry;
_local_references reconstructs context. _validate_collected, cache readback and
_validate_finalization reject collector substitutions. Finalization detaches only
destination coordinates; existing bounds still apply.

domain/revision profile feedback rejects identity-contract changes as advisory
switches already do. operation_digest naturally hashes full profiles/upstream
artifacts; retain this. RevisionRuntime.validate_output compares profile/evidence
markers. review, dashboard.review_payload, ReviewPayload consistency and explanation
reconstruction repeat pure validation at persisted time. Receipts/artifacts retain
marker/proof without new graph keys or stages.

Offline validation checks bound internal integrity, declared coverage, statuses,
active Fund/class association and current proof at original saved time, with zero
ancestor/latest-registry/provider/source reads or new clock assessment. Actual
historical completeness is publication's real-parent check; offline replay trusts
the bound publication attestation. Hashes/attestations authenticate neither actors
nor official source truth.

## Focused verification and documentation

- AC126-1/2: same Fund/two ISINs; distinct Funds/umbrella; same/normalized names
  needing separation; unresolved comparisons; rename/alias; membership closure;
  suspension/retirement/succession; omitted transition/inventory; false parent/
  entry digest; deleted/edited history; stale CAS; atomic failures and contention.
- AC126-3: old rename/fresh endpoint; missing/stale current proof; unlinked contexts;
  120h inclusive/just outside; nonminimum constituent five-minute future inclusive/
  just outside; historical/current dual-role source.
- AC126-4/5: schema/bounds, detached binding, numeric-codec and cache/finalization
  roundtrips, fingerprints, mixed generations and marker/proof removal/downgrade/
  tampering at shared validation boundaries.
- AC126-6: synthetic graph review, saved JSON restoration and downstream revision
  with external reads disabled, saved-time retention, contract-switch rejection,
  legacy golden bytes/digests and unchanged financial/FX regressions.
- AC126-7: locked sync/workflow/ledger/Ruff/pytest gates and meaningful optional
  research/catalogue/dashboard/checkpoint tests. Report skips/live-store limits.
  Exact-content independent review and latest-head CI/comments/threads required.

Owner updates this iteration, system architecture and usage/reference guidance.
Resolve ADR0042 Proposed status through actual Issue126 design/acceptance, preserving
Issue124 history. Complete docs before certification. Main risks: marker loss,
codec confusion, missing-value bypass, commit-acknowledgement ambiguity and source
age renewal. Consequential ambiguity returns to coordinator within finite slots;
concrete difficult implementation may escalate with evidence. No extra scope/slot
is granted by this handoff. Synthetic tests cannot establish source coverage,
authenticity, US ISIN availability or live portfolio readiness.

DESIGN_READY

## Independent challenge and coordinator approval

`/root/issue126_challenge`, code_reviewer/gpt-6-sol/high, independently challenged
the handoff against INV126-1 through INV126-5 and AC126-1 through AC126-6 and
returned PASS without a material ambiguity or demonstrated design failure.
The review confirmed actual-parent publication versus offline attestation trust,
historical/current proof partition, each-source saved-time freshness, full proof
binding and named codec hazards. Explicit null versus absent markers, unit-changing
downgrade despite broad legacy group syntax, model_copy revalidation and catalogue
proof-size limits remain focused implementation tests under AC126-4/5/6.
The challenge changed no files and ran no tests; it is not runtime acceptance.

Coordinator `/root` approves generation 1 digest
`c50e07ba8308449c2f0fd402de5f1a94aafe8cf7d38bb598363d349626be3335`
for `/root/issue126_owner`, implementation_worker/gpt-6-sol/medium, on 2026-10-26.
Separate native design/challenge/approval bind that same immutable capsule.
The approved owner may implement, test, self-review and document within scope;
content-bound verification/acceptance and independent code review remain required.

## Implementation record (owner pass)

The bounded implementation adds pure strict `RegistryEnvelope`/Fund/current-proof
contracts, actual-parent publication validation, and a replaceable local
digest-addressed registry with cross-process exclusion and expected-parent CAS.
The store retains immutable generation blobs and reports pointer failures before
commit separately from acknowledgement/readback/cleanup uncertainty after
commit. Synthetic registry data is generated only in tests. No actual source
body, key issuance operation, live registry activation or external financial
write was performed.

[Coordinator arbitration A126-1](../workflow/issue126-arbitration.md) resolved
two self-review findings within this pass. Publication rejects unsupported
suspended-to-active reactivation; a future resumption procedure requires a
separate contract. Retired resurrection remains rejected. Every source must be
collected and the audit attested no later than the generation recording; a
child's recording cannot precede its actual parent's. Equal timestamps are
valid. These declared-event order checks do not authenticate sources or actors
and do not change the fixed current-proof freshness window.

Reference schema 2 binds one complete envelope and exact Fund/class/provider/
URL observation. Research snapshots, scalar document metadata, catalogue jobs,
evidence, profile/policy, screening, construction, explanation, revision,
dashboard review and CLI retry carry or compare the explicit identity marker.
Saved review validation uses its bound envelope and original check time; no
ancestor registry, latest pointer, provider or new-clock read is required.
The existing profile arithmetic, selection, FX and graph stage/key structure
are retained. Schema 1 and absent-marker serialization are unchanged.

Focused synthetic checks cover initial and successor publication, 730-day
historical rename with fresh current endpoint, every-source current freshness
edges including a nonminimum future constituent, historical/current dual-role
source, missing/inactive membership, transition/inventory and entry-digest
failure, retained history, stale CAS, precommit/postcommit pointer outcomes,
unsupported suspended reactivation, source/attestation/parent recording order,
positive same-status refresh/suspension/retirement,
schema2 reference attribution, end-to-end three-Fund saved research through
ready construction, marker downgrade rejection and zero live-registry reads
during saved JSON replay. These fixtures establish deterministic contract
behavior only; they do not establish legal/source truth or market-data coverage.

The owner ran the locked checks on the implemented runtime and tests:
`uv sync --frozen` (57 packages audited), workflow configuration validation,
Issue 126 ledger validation, `ruff check .`, `ruff format --check .`, and
`pytest -q -ra`. The full baseline suite passed with 1,805 passed and 60 skipped
among 1,865 collected tests. The skips cover unavailable optional packages and
the disabled `RUN_REAL_STORE_TESTS` disposable integration opt-in. The focused
Issue 126 suite passed 26 tests. `git diff --check` found no whitespace errors.

The owner then installed locked `dashboard`, `rag`, `checkpoint`, and `providers`
extras and ran 377 relevant tests across Fund identity, catalogue, Streamlit
dashboard/revision, PostgreSQL checkpoint contracts, Chroma store, snapshot
publication, US/EU contracts, and prior comparison/catalogue repair seams:
377 passed, zero skipped. An earlier broader optional run had one Streamlit
AppTest exceed its fixed 10-second timeout under load; it passed in isolation,
and this final selected optional run passed. These checks use synthetic/local
fixtures; `RUN_REAL_STORE_TESTS` remained disabled and no disposable Compose or
live production store was activated. They establish neither official source
completeness/authenticity nor live portfolio readiness.

The owner reviewed the transition/inventory binding, chronology, marker and
replay paths after the initial fixture correction. At that point no further
frozen-contract ambiguity or failing check had been identified. Content-bound
verification, acceptance, independent review and delivery remained
coordinator-owned gates.

## Independent initial review and bounded remediation

The independent initial review failed on two concrete frozen-contract cases:
source-backed unmapped inventory rows could coexist with an affected active
Fund, and a third generation could delete explicit completed-rename lineage
references. [Coordinator arbitration A126-2](../workflow/issue126-review-arbitration.md)
assigned both same-scope repairs to the original owner under the single reserved
remediation allowance. The earlier verification/acceptance binds the failed
content and cannot certify this repair.

The bound snapshot now requires every unmapped inventory row to be labeled
`unresolved` and rejects an unresolved row when an active Fund uses its context.
Affected contexts include the Fund, retained alias, current inventory or class
assertions, and required current-context links. Actual-parent publication keeps
the same safeguard. Source-backed unresolved rows remain valid for suspended
affected Funds; resolved mapped rows remain valid. A later generation must retain
every prior `current_proof.lineage_source_ids` reference, while fresh current Fund,
inventory and class sources may change without redating historical evidence.

Focused synthetic tests reproduce active initial and successor publication
failure, former-context alias and linked-current-context effects, malformed
unmapped `unchanged` classification, and valid suspended/resolved controls. A
three-generation rename then fresh refresh passes with years-old retained lineage
and rejects deletion of that lineage. The repaired focused identity suite passed
29 tests; identity plus the legacy catalogue-cache regression suite passed 46.

On the repaired runtime/test content, frozen baseline `pytest -o addopts='' -q -ra`
passed **1,809 tests with 59 skips**. The skips cover optional dependencies absent
from baseline and disabled disposable `RUN_REAL_STORE_TESTS` integration. With
locked `dashboard`, `rag`, `checkpoint`, and `providers` extras installed, the
selected Fund identity/catalogue/dashboard/checkpoint/Chroma/US-EU suite passed
**380 tests with no skips**. `uv sync --frozen`, workflow configuration and ticket
validation, Ruff check/format, and `git diff --check` also passed. No real source
acquisition, live store activation, credential use, or external financial write
occurred. These checks do not authenticate source completeness or establish live
portfolio readiness. Fresh content-bound verification, acceptance, independent
final review and delivery remain coordinator-owned gates.
