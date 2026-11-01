# Issue134 exact architect handoff

Coordinator transcription of separate `/root/issue134_design` DESIGN_READY against
generation1 capsule `ef108151e006112327986ef46ebdf995b4bba332f3e3b94f45beb5b8e5faaa76`.
Independent challenge and coordinator approval are separate later gates. This is
governance only, not actual Issue123 authority or a product change.

## Exact event and admission

Event `manifest_sequence_amendment`, contract `issue123-manifest-sequence-v1`.
Outer keys exactly `type`, `at`, `data`; native timestamp checks unchanged. Data
keys exactly `transition`, `authority`, `capsule`, `source_history`, `replacement`,
`target`, `changes`, `reason`. Authority is strict native named-user authority;
reason native nonempty text. Source ref is exactly id
`issue-123-usable-reference-and-bnd-diagnostic`, generation6, digest
`9929b6f75007a776e3f14d3ee53f7631a5db66c5384aa0e3f0e78daa1c18bc52`.
Repository beagle1903/agentic-etf-advisor, issue123, owner-led-v1, consequential,
review_required true. Current and supplied source refs must both match exactly.

Pin actual49 immutable history digest
`bb14145e68f53476ef1ba7e8189fdff40dd0c535eba83924431480e394bcc70d`.
Fixture tests also pin original47
`dc69597ff2b6ddd9cd9c0b41dbc5111ea956291f557221b460fd3a7b4f902471`.
At zero-based index i require i>=49, digest({schema:1,events:history.events[:49]})
exact, source_history exactly {event_count:i,digest:complete preceding schema1
history digest}. Strict integer, not bool/float. Valid later planning/grant/audit
suffixes may bind while exactgen6/lifecycle remain valid; total preceding count is
not fixed at49. No runtime fixture/ignoredartifact/approvaldoc/otherissue ledger read.

Require both old capsule_amendment/local_registry_authority markers and no prior
manifest_sequence_amendment marker. Reject active/suspended/offlinepause, delivered,
current/history delivery binding, retirement, splitpool/remainder/children,
predecessor/ancestry/historicaltransition/retainedreservation/failedfinalreview.
Keep ordinary blockers and prior failed outcomes. Approved owner must strict-equal
the full exact source owner including session /root/issue123_owner; no specialist
or disguised owner handoff.

## Exact one-path target

Pure `manifest_sequence_target(source, authorization)` deep-copies source; exactly
one occurrence of the anchor below is replaced once in scope.S123-1; generation7
and deep-copied event authorization. Every other capsule value/type stays exact.

Anchor:

```text
Before any operation, freeze the exact directory, listings, Fund/class and source manifest, named authorized curator and distinct independent proof reviewer, key-issuance authority and local-publication authority in the fresh approved operational design.
```

Exact replacement, one unwrapped string:

```text
Before source discovery or acquisition, the fresh approved operational design must freeze the exact isolated ignored directory, named authorized curator and distinct independent human proof reviewer, distinct source/key/publication authority references, exact bounded official-domain queries and host policy, initial source leads and acquisition-manifest format, request/attempt/byte limits, deadline policy and exclusive attempt accounting. The initial plan must distinguish planned sources and candidate listings from established facts; it need not assert undiscovered Fund/class evidence or a complete source inventory. During the single bounded discovery attempt, record each discovered exact URL and its justification before acquisition, and append redirect, response, byte, original observation, collection, time and outcome evidence without renewing observations. Before any market collection, freeze at most10 exact source-justified provider listings, their source-to-field associations, and remaining attempts within the same approved bounds. Before any real key issuance or registry publication, freeze the complete direct legal Fund/class and active ISIN membership evidence, source manifest with available raw bodies and exact locators, complete inventories/comparisons/continuity dispositions and every current proof constituent at saved check time; obtain the distinct authorized human reviewer's actual approval of that proof before issuance/publication. Use the unchanged reference loader and publisher; publish the one bound envelope before any market collection that requires it, and stop without market collection or retry after failed or uncertain publication. Staging permits discovery before final evidence manifests exist; it changes no acquisition count, financial/proof/freshness rule, actor authority or one-shot publication safeguard.
```

Full resulting S123-1 length3998, native canonical string digest
`f3cf94b11c8b23be2a04d17f87fb6e4615b96338e87e538fb0a391b6602403f0`.
Proposal verbatim would be4021; do not use it or raise native4000 limit. Target
capsule digest depends on later real approval, not a synthetic fixed target digest.

Changes exactly {version:contract,definitions:{scope.S123-1:{before:full oldscope,
after:full newscope}}}. Replacement is complete native capsule; target exact
capsule_ref(replacement). strict_equal supplied replacement/ref/map, then native
capsule validation. Reject changed outside text, any second path, null/extra/missing/
coerced types, duplicate keys/nonfinite via strict native load. No arbitrary patch.

## Authority exclusion and accounting

Reject normalized evidence already consumed in state.authorization_history, including
actual A/B. Additionally reject digest(normalized_evidence(evidence)) in this table:

| Recorded authority | Digest |
| --- | --- |
| Issue128 governance | 26e4a4959ccf8d67ccb9236868991214dfac55f7b6bc16a0eab2bd915db243c9 |
| Issue132 governance | cafa481265220bf1308016fa3e08235333ceee79b337ac2a5b027b3f2a53defa |
| Issue134 G | 07f5ee894d8cb6aa3450c5a4e3a120e1ab1a7cf7093e96cf39cf50adcb68f233 |
| Held R | 20f2aca5aee644eeb7e7bf24ba5012585622da44dba8782d7c3ad6d3117f4058 |
| C recorded bullet | a753f605e11bb0aef92cb6867238d26c326768023d8626c035fe7da4cf9e32b9 |
| D-curator recorded bullet | 64d7461ded1441aab0094f35901784497807ac8dc226d21ee981751486a99d0d |
| D-proof-review recorded bullet | 4b26e2b8cfedde167cea89c6dea74c1d394e4777c58e3a51bb2b8bfb259891c1 |
| D-key recorded bullet | ebf4bd61cf400d52e6c106b3e516dc396bf538d6cb630d1a5a5c5e3159d90491 |
| D-publication recorded bullet | e2d3816d83ca0193e05e640fdacc93a38041d67ef97172b4645eb6dd809abab1 |

C/D fingerprints are complete corresponding exact Markdown bullet blocks including
their - C: / - D-...: labels in ignored prior-operational-execution.md, UTF8/native
normalized. Preserve exact texts in ADR/test evidence and recompute digests, not
merely copy constants. These are purpose records, not invented native grants.
Name/NFKC/case/internal/surrounding whitespace cannot create new authority. Static
fingerprints do not detect paraphrased reuse or authenticate people; coordinator
must check real later operational approval for exact event/target/currenthistory.
No generalized semantic authorization system. R remains distinct and held.

Add one consuming record class manifest_sequence_amendment in authority_records;
add its evidence to capsule_references. Do the same consume/reference treatment in
validate_map connected accounting. Later unchanged capsule authorization is a
reference, not another grant. Reuse for extension/continuation/split/newauthorization
rejects in applicable same/connected sibling/descendant/reverse orders. Update test
current_capsule helper. No participant-independence, append/prefix/PR/content bypass.

## Exact state effects

New optional State field manifest_sequence_amendment:dict|None=None, preserving
absent-marker legacy behavior. On success store capsule=replacement and marker
exactly {contract,source:oldref,target:newref,source_history:deepcopy,event:i}; add
normalized authority once. Clear exactly ready/challenge_ok/verified/accepted/
reviewed/remediated false; design_session/challenge_session/author_session None;
design_ref/challenge_ref/approved_ref None; verified_content/acceptance_content/
review_content None; design_started true.

Preserve every other state field: old markers, events, counts/local/inherited/limits,
budget/policy/clock, sessions/writeauthors/originalapprovedowner, consumed/extension
authorities, blockers, pending_repair, verification_repair_count, failure flags,
historical outcomes and delivery identity. Normal replay advances last/elapsed;
no time subtraction, clock restart, count grant or operation. Clear stale author/
remediation so old blocker resolutions cannot pass. design_started requires counted
reset; retained remediation history forbids initial_review substitution.

## Later operational order and safeguards

Later fresh exact operational approval then native atomic event -> unapprovedgen7,
zero grants/calls. Apply already approved heldR exact authority, reset+1 only,
allotherdeltas0/seconds0. Recommended event thenR. R-before-event validsuffix only
when heldconditions actually satisfied and fresh transition approval binds suffix.
Checked/reserved reset4/4 ->gen8, fresh architect/challenge/coordinator approval.

Approved bounded plan beforediscovery; URL justification/log beforefetch; actual
source-grounded exactlistings and remainingbudget freeze beforemarket. Complete
legalFund/class/activeISIN/currentconstituents/rawproof/locators/inventory/comparison/
continuity, actual humanburha sourceproofapproval BEFORE issuance. Then bounded keys
through existing injected boundary, exact envelope and genuine curator/reviewer
assertions about actual keys/content/times BEFORE publish. Do not relabel pre-key
sourceproofapproval as attestation of nonexistent envelope bytes. One emptyparent
publication, reconcile returned envelope/blob/pointer on confirmed success, then
reference loader/collector/market requiring bound input. Publication is not market
eligibility; market success is not prerequisite for publication. Failure/uncertainty
stops without collection or retry.

Retain C4queries/24responses(conservativeattemptreservation)/oneattemptURL/15s/
2MiB/24MiB/15min; <=10exactlistings, Yahooonecollection/listing12requests/10s/2MiB/
120s and120requests/1200saggregate; existinginvokedBNDfallback3attempts/90s/16MiB.
No diagnosticrepeat/replacement/appretry/duplicateverificationpass or renewed old
allowances/windows. Originalcurator and humanreviewer, exactapprovedignoredroot,
existingroot/failure/uncertaintystop with no root substitution; <=10Funds/listings,
onekey/Fund, registrygeneration1, null expected/snapshot/audit parent, onepublishcall,
atmostonepointerreplacement with actualparentCAS/inventory/transitions unchanged.
128KiB/256members/256sources/1000chars/text; reference10listings/1MiB. Every current
proof constituent saved120h/fiveminutes; BND1080h onlyofficialholdings/concentration.
No observation renewal, inferred facts, financial/numeric/identity/proof/legacy/
savedreview change. Five complete fields permit explicitunsupportedvalues. No actual
source/runtime/clientrepair/existingregistry/app/store/Issue117/merge/trade/write.

## Tests, docs, verification and next gate

New tests/test_ticket_manifest_sequence_amendment.py and immutable exact
tests/fixtures/issue123-original49.json. Pin47/49/gen6, exact1anchor/1path/deepcopy/
3998length/scopehash/unlistedpreservation, reject4021proposal; wrongrepo/issue/policy/
classification/ref/history/mutatedprefix/incompletesuffix/count/digest/target/map/
secondpath/outsidetext/types/missingextra/null/duplicate/nonfinite. Accept valid
planning/distinctgrant suffixes. Exhaustedreset allowszero-countamendment but blocks
reset beforegrant. Every deniedauthority andconsumedA/B, with validrecomputedtarget
and NFKC/case/whitespace/namevariants; oneconsumingrecord/latercapsuleref controls,
latergrantreuse and connectedlineage reference/reuse in applicable eventorders.

Every lifecycle/owner/missingmarker/repeat guard; fullState comparison allowing
only exacteffects/time, explicitly preserve failures/blockers/debt/owner/markers/
counts. Staledesign/challenge/verification/acceptance/review/blockerresolve and
initialdesign/initialreview shortcuts fail. Fullsynthetic49->gen7->distinctheldshapedR
->reset4/4->gen8freshdesign/challenge/approval->originalownerimplementation6/6
->remediation2/2->verification/acceptance->independentfinal_review1/1->delivery.
Synthetic remediation resolvesblockers only via validnativeevidence. Identicalcontent
and firstoriginalPR binding, reruns and laterrepair forbiddifferentrepo/PR/stalecontent.

Actualappend invalidcandidate bytepreservation and repositorylock; observedeventfile,
otherledger,candidatetemp,contentraces; mergebaseprefix/currentprimaryPR checks remain.
Existing ADR0043/44/timed/ownerled/continuation/split/identity/registryCAS/bootstrap/
precommit/ack/actor/inventory/comparison/bounds/freshness/legacy regressions unchanged.
No fake runtime stagevalidator or liveacquisition for governance tests. Software
does not establish actor/source truth, realinventories or operational success.

Add ADR0045 with exact schema/recipe/constants/effects/authoritytexts/tests, new
nonexecutable docs/workflow/issue123-manifest-sequencing-runbook.md; active040,
A123-1 linkage, AGENTS/CONTRIBUTING/staticmarkers. Preserve acceptedADR0042-44.
Locked MINIMAL/default/dev, focusedregressions, Ruff/format, configuredmypy/mypy src,
build/nativeworkflow/Compose/diff and meaningfuloptionalchecks; finish docs before
identicalcontent verification/acceptance/independentreview and commit/push/ownPR/
nativeoriginaldelivery/currentheadCIcommentsunresolvedthreads. No mergeauthority.
Operational proof/capability/freshness/humanreview/one-shot success remain future
stopconditions; no unresolved governance defect is claimed by this design.

Independent challenge focuses on onepath/4000boundary, completeprefix, authority/
reference/lineage, retainedfailure/repair and proof->issuance->actualattestation->
publish->boundcollection sequence. No reopening acceptedgen6blocker or inferring
actual123authority. DESIGN_READY, pending separate challenge/coordinator approval.
