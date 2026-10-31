# Issue132 exact architect handoff

Coordinator transcription of separate `/root/issue132_design` DESIGN_READY,
generation1 capsule4338ddbd905054aefed3e2bf594200472ea9fe1a15cdaf12866f226d9bec9e30.
This document records the complete implementable definition recipe from the
architect response; independent challenge and coordinator approval are separate.

## Contract and exact schema

Event type `local_registry_authority`; contract `issue123-local-registry-v1`.
Source ref: id `issue-123-usable-reference-and-bnd-diagnostic`, generation4,
digest9e7404cbcf12d186489e399c6a2884afd1d3bfa7f7363be1727fcb6e0d2860ec.
Original41 canonical digest2d7a3127922376a1a6991fd40192145a408f6df68c8cbefa6763e865e4d4142e.
Issue132 normalized initialization approval digest
cafa481265220bf1308016fa3e08235333ceee79b337ac2a5b027b3f2a53defa;
also reject existing Issue128 GOVERNANCE_APPROVAL_DIGEST. These are native
digest(normalized_evidence(evidence)) with canonical JSON-string hashing.

Outer event keys exactly `type`, `at`, `data`. Data keys exactly `transition`,
`authority`, `capsule`, `source_history`, `replacement`, `target`, `changes`, `reason`.
transition is the contract above; authority is strict named-user native authority;
capsule is exact source ref; source_history has exactly integer event_count and
digest; replacement is complete native target capsule, target its capsule_ref;
reason is native nonempty text. Strict structural JSON equality must distinguish
integers from floats/bools. Reject missing/extra/null/coerced values, duplicate
keys and nonfinite values under existing load/append validation.

At zero-based index i require i>=41; original41 prefix digest exact; source_history
count equals i and digest binds every preceding event as schema1 history. Current
and supplied source refs must equal exact gen4 ref. Valid later planning/grant
suffixes remain bound. No runtime read of fixtures, ignored artifacts or external
Issue132/123 ledgers for admission or governance-authority exclusion.

## Exact deterministic target recipe

Pure `local_registry_target(source, authorization)` deep-copies exact admitted
source, sets generation5 and deep-copies event authority as authorization.
Classification, owner, rationale and every unlisted value remain exact. Only
the eight definition changes below are allowed. Each appended paragraph is
preceded by exactly one ASCII space. Exact replacement anchors occur once.

### scope.S123-1 append

The sole prospective publication exception is one separately authorized ADR0042 curator-fund-v1 bootstrap attempt in one newly frozen ignored local registry directory with no pre-existing active registry, for at most10 selected exact listings and at most10 directly proven distinct legal Funds, one stable opaque key per Fund and one initial immutable registry generation. Before any operation, freeze the exact directory, listings, Fund/class and source manifest, named authorized curator and distinct independent proof reviewer, key-issuance authority and local-publication authority in the fresh approved operational design. Use the existing injected identifier boundary, complete legal Fund/class evidence, inventories, comparisons and transition attestations. Unresolved identity, collision, continuity or unavailable proof stops. Use LocalFundIdentityRegistry.publish exactly once with expected_parent_digest=None against the actual empty parent; snapshot generation must be1 and snapshot.parent_digest and audit.compared_parent_digest must be null. Permit at most one active.json replacement. No existing-registry mutation or refresh, second publication attempt, retry, key rotation, rename/succession operation, reactivation or recovery bypass. Stop and retain evidence after failure or uncertain commit outcome; do not retry. Preserve the existing128KiB registry,256members,256sources,1000characters/text and reference10listings/1MiB ceilings, all financial/proof/freshness/source rules and all consumed acquisition and diagnostic allowances. This transition grants no counts, source attempt, real key issuance or publication operation; distinct later operational authority and renewed native design/challenge/coordinator approval are required.

### non_goals[1] replacement

Anchor:

```text
No store activation or existing user data/review mutations. This amendment grants no real key issuance, registry publication or operational source authority.
```

Replacement:

```text
No store activation or existing user data/review mutations except the single isolated local registry active-pointer publication expressly bounded by S123-1 and INV123-3 under separate operational authority. No default application adoption, Chroma/Neo4j publication or saved-review mutation. This transition grants no real key issuance, registry publication, operational source authority or counts.
```

### invariants.INV123-3 replacement

Anchor:

```text
no publication/activation or financial write.
```

Replacement:

```text
no publication/activation except the single separately authorized isolated local registry bootstrap and active-pointer publication bounded by S123-1, and no financial write. Preserve default application configuration, Chroma/Neo4j, existing registries and saved reviews. Actual-parent/CAS validation, independent authorized curator/reviewer attestations and genuine publication outcome evidence are mandatory; detached assertions cannot substitute for publication.
```

### interfaces replacement

Exactly this one-element list:

```json
["none changed; existing ReferenceFactsFile/load_reference_facts/bound_reference_fields, RegistryEnvelope, new_key and ADR0042 proof/publication validators, LocalFundIdentityRegistry.publish, YahooCatalogueResearchCollector/YahooRequestBudget, VanguardHoldingsClient, source-quality and pure evidence/screening/construction as clients. LocalFundIdentityRegistry.publish is permitted only for the separately authorized single bootstrap bounded by S123-1 and INV123-3. Operational acquisition, named curator/reviewer assertions, real key issuance and local registry publication require concrete separate authority; this transition performs none."]
```

### json_state_impact replacement

```text
Existing ignored reference schema2 with identity_contract=curator-fund-v1 and complete bound RegistryEnvelope; detached research numeric schema2 remains independent. The separately authorized S123-1 bootstrap may create one ignored local immutable registry generation and its active.json pointer through the existing publisher. No product schema, graph/checkpoint/state or saved-review migration. This governance transition changes only the ticket capsule and workflow audit state; it creates no registry, key, source artifact or pointer.
```

### acceptance.AC123-2 append

For the S123-1 bootstrap, audit the actual empty parent, generation1, null expected/snapshot/audit parent, complete issue transitions and actual publisher result. Require the independently approved bound envelope to match the retained immutable blob and active pointer after confirmed publication; on failure or uncertain commit retain the outcome and stop without retry. Complete five-field objects do not require five positive facts. Publication, download and attestation never renew source observations.

### acceptance.AC123-5 replacement

Anchor:

```text
No store activation or Issue117 proof/readiness implication.
```

Replacement:

```text
Audit the separately authorized S123-1 bootstrap with its frozen ignored directory and manifest, named curator and independent proof reviewer, distinct source/key/publication authorities, actual-parent/CAS and attestation evidence, one-attempt accounting, immutable blob/pointer digests and actual success, failure or uncertain commit outcome. No store activation beyond that isolated registry pointer, default application adoption, Chroma/Neo4j publication, saved-review mutation or Issue117 proof/readiness implication.
```

### verification[0] append

For the separately authorized S123-1 bootstrap, verify the frozen directory/manifest and actor/source/key/publication authorities, actual empty parent, generation1 and null parent bindings, complete inventory/comparison/issue transitions, one publish invocation and at most one active-pointer replacement through the unchanged publisher. Reconcile the returned envelope, immutable blob and active pointer only after confirmed success; failure or uncertainty stops without retry. Verify the retained source/market attempt history and all stricter operational ceilings. No static workflow check or synthetic fixture authenticates a person, source truth or real-world inventory completeness.

The exact changes map has only version and definitions. version is the contract;
definitions maps each of the eight paths to exact before/after values above.
No classification entry or arbitrary patch operation. AC123-2/verification/JSON
consistency additions distinguish genuine publication and acknowledge the future
pointer write; they add no product mechanism. INV123-1/2/4, AC123-1/3/4, all other
non-goals, owner, rationale, documentation, risks and escalation remain unchanged.

## Admission, preservation and effects

Require exact repo/issue123/owner-led/consequential/required review and source;
no prior local_registry_authority marker; existing capsule_amendment marker present.
Reject active/suspended/offline pause/delivered/delivery history or binding,
retired/split pool or remainder or children/predecessor/ancestry/retained historical
reservation/historical transition/failed final review. Approved owner must exist
and role/model/effort match frozen owner, no specialist; preserve actual session.
Reject normalized authority already consumed or matching either governance digest.
Changed display names, NFKC/case/whitespace do not produce new authority.

On success set capsule=replacement and local_registry_authority marker with exactly
contract, source, target, source_history (deep copy) and event (zero-based index).
Consume normalized authority once. Clear ready/challenge_ok/verified/accepted/
reviewed/remediated, design_session/challenge_session/author_session,
design_ref/challenge_ref/approved_ref and verified_content/acceptance_content/
review_content. Keep design_started=true. Preserve every other state field,
including old amendment marker, counts/local/inherited/limits/budget/clock/elapsed,
sessions/write authors/approved owner/authority consumption, blockers and required
remediation, pending repair, verification_repair_count, failure flags and delivery
identity. Normal replay advances elapsed audit; no subtraction or grant.

Add one authority record class local_registry_authority and replacement authorization
reference in authority_records and validate_map connected accounting. Unchanged
later capsule authorization references are not second grants; reuse for extension,
continuation/split/new authorization rejects in either applicable order. Update
test current_capsule helper. Leave append/check_prefix/check_pr/content and original
PR identity behavior intact, no custom append bypass.

## Later native route and verification

Distinct operational event creates gen5 without readiness/counts. Separate finite
grant design_reset+1 (other deltas0) may precede as a bound suffix or follow. Checked
reset consumes3/3 and advancesgen6, followed by successful fresh architect, independent
challenge, coordinator approval, existing remaining implementation and remediation,
new verification/acceptance and independent final_review. Retained remediation history
forbids initial_review substitution. Cleared author/remediated prevent stale blocker
resolution; design_started prevents initial-design bypass. No actual123 event here.

Focused tests use tests/fixtures/issue123-original41.json as immutable historical
evidence and label all appended authorities/outcomes synthetic. Cover exact8deltas,
all unlisted fields/state preservation; wrongsource/history/completeprefix/suffix;
wrongtarget/map/ninthpath/types/extra/missing/null/duplicate/nonfinite; prior and both
governance authority variants with otherwise recomputed valid target; later reuse
and connectedlineage/capsule refs; repeated/lifecycle/owner/missingoldmarker; reset
exhaustion/stale success; complete syntheticgen6 route through finalreview; invalid
append byte preservation and observed event/ledger/candidate races; ADR0043/timed/
continuation/split/prefix/currentPR/content regressions. Run existing parentCAS,
bootstrap/precommit/acknowledgement, actor/inventory/comparison/bounds/freshness/legacy
registry tests unchanged. No runtime repair or live operation in tests.

Add ADR0044, activeiteration039 and nonexecutablerunbook, applicable AGENTS/
CONTRIBUTING/staticmarkers; preserve acceptedADR0042/43. Full locked/default/dev/
MINIMAL and meaningful optional checks, identicalcontent verification/acceptance and
independent review precede delivery. JSON impact is strictworkflowevent/capsule/audit
only, none to product/graph/checkpoint. Static checks cannot authenticate humans,
sources, real-world inventory or enforce live caps as a runtime kill switch.
