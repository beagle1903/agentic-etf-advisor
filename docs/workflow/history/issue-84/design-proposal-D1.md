# Issue84 remainder — D1 architect handoff

Author: /root/issue84_remainder_design, design_architect, gpt-6-astra, high.
Current main: 10b4a4e67cf8abec7d20243d6a642e690a2c0e08.
Outcome: DESIGN_BLOCKED. This is a proposal, not implementation authorization.
Coordinator transcription of the read-only architect's complete contract and disposition.

## Frozen proposal capsule

```json
{
  "schema": "issue84-remainder-design-proposal-v1",
  "status": "DESIGN_BLOCKED",
  "repo": "beagle1903/agentic-etf-advisor",
  "issue": 84,
  "classification": "consequential",
  "frozen_capsule": {"id":"issue-84-cycle-bounded-workflow","generation":3,"digest":"df870f205cc3a8053c152699ce16030a1cedc518fdda0588ae16d3cbcd95fda9"},
  "architect": {"role":"design_architect","model":"gpt-6-astra","effort":"high","session":"/root/issue84_remainder_design","reservation":"D1"},
  "proposed_implementation_owner": {"role":"implementation_worker","model":"gpt-6-sol","effort":"medium","session":null,"authorized":false},
  "rationale": "Allowance conservation, authority reuse and historical replay are consequential governance contracts. Existing role pins remain unchanged. A new owner session requires a recorded approved disposition, not automatic replacement of an exhausted owner.",
  "authority": {"kind":"user","name":"burha","evidence":"2026-10-07 approval in chat 01a11682-286e-7500-a4ce-24bff6b2c093 for one read-only design revision, one independent challenge and supplemental reservation after ordinary gate rejection; later continue resumes the same D1 reservation.","implementation":false,"publication":false},
  "scope": {"S84":"Replace completion/elapsed-time exhaustion with finite review/design-reset/reimplementation cycle caps; update workflow engine, tests, templates, instructions and docs; backwards-compatible append-only historical migration and split attempt conservation."},
  "assigned_remainder": ["AC84SPLIT/I84SPLIT owner-led allocation and whole-lineage approval conservation","AC84TIME/AC84HISTORY exact Issue23 to Issue83 introduction and transition removing only time barrier","Concrete exhausted Issue84 disposition preserving histories and bindings"],
  "non_goals": ["Authentication/application/graph/financial/provider/database contracts","Issue83 implementation, verification, acceptance or automatic resume","PR85 recovery or special recertification machinery","Rewriting events/capsules/failures/counts/content/PR bindings","Role model/effort/access/registration/dependency/CI privilege changes","Arbitrary legacy migration","Separate wishlist retirement","Automatic successor creation/extensions/replacement/publication"],
  "invariants": {
    "I84CYCLES":"Default one implementation/initial-review/remediation/final-review/design-reset lifetime attempt persists across agents/sessions/quota resets/design resets. Extra attempts require explicit named user authorization.",
    "I84TIME":"Completion time/quota waits/open-phase elapsed time never gate new cycle-only work or require minute extensions. Timing may remain historical/audit data.",
    "I84HISTORY":"Existing ledger prefixes/capsules/counters/content/PR bindings remain immutable and validated; explicit policy transition cannot clear attempts, review outcomes or substantive blockers.",
    "I84GATES":"Consequential design/challenge/approval, role ownership, review independence, content-bound acceptance/verification/review and clean delivery remain enforced.",
    "I84SPLIT":"Successor/sibling allocation conserves remaining attempt allowances and inherits consumed history; split/new issue cannot silently replenish attempts.",
    "I84ISOLATE":"Only development-governance engine/docs/tests change; current Issue83 product work preserved."
  },
  "acceptance": {
    "AC84TIME":"New cycle-only ledgers and explicitly transitioned expired/suspended legacy ledgers can resume after arbitrary waits without timing extensions; status explains remaining attempts rather than misleading minute debt.",
    "AC84CYCLES":"Counted phase limits/failed-final-review stop still enforce across resets/handoffs/quota waits; explicit count extension cannot be replayed or impersonated.",
    "AC84HISTORY":"Historical delivered/split/bootstrap ledgers replay without rewriting; transitions preserve prefix/capsule/counts/bindings and deny clearing substantive blockers or converting delivered tickets.",
    "AC84SPLIT":"Split successors/siblings inherit consumed counts and validated allocated remaining allowances, cannot multiply attempts or reuse allocations; terminal predecessors remain retired.",
    "AC84GATES":"Existing ownership/design/challenge/approval/content-bound acceptance/review/verification/PR gates and unrelated static workflow checks remain correct.",
    "AC84DOCS":"AGENTS/CONTRIBUTING/README/templates/role bodies explain cycle-only policy; new ADR supersedes timing only; finite-workflow history remains untouched.",
    "AC84VERIFY":"Focused engine/CLI/negative fixtures plus required offline/static/evaluation/build/Compose gates pass; independent review required; no services/product behavior changes."
  },
  "interfaces": ["Workflow replay, State.gate/status","Strict split/exact historical transition parsing","Whole-lineage allocation and authorization validation","Atomic append and CLI source handling","Merge-base history and primary-issue/PR/content binding","Workflow documentation/templates/static validation","Application/provider/store/financial interfaces: none"],
  "json_state_impact": {"application_graph_checkpoint":"none","workflow":"Strict owner-led split and one exact lineage transition; derived conserved pools and identities; no old-event changes"},
  "verification": ["Immutable focused scenario fixtures","Actual saved-file append/prefix/status/PR binding in temporary repos","Required Ruff/configured mypy/offline tests/workflow validators/evaluations/build/Compose/diff gates","Independent review excludes historical/current write and verification authors","Actual saved delivered ledger and identical content publication checks"],
  "documentation": ["New ADR extending ADR0033 for specified contracts","Active iteration with challenged spec/disposition/evidence","AGENTS/CONTRIBUTING/workflow README/affected templates/instructions","Preserve accepted ADRs and history"],
  "risks": ["Cloned sibling allowances","Later-sibling or timed-ancestor approval reuse","Concurrent appends","Partial/arbitrary introduction","False product authority after transition","Bootstrap/PR identity change disguised as continuation"],
  "escalation_triggers": ["Concrete frozen-ID failure to coordinator arbitration","Consequential ambiguity blocks implementation","Specialist needs recorded evidence and sequential escalation","Exhaustion/failed final review/serious blocker requires user decision"],
  "implementation_blocker":"No approved executable bootstrap and publication disposition for exhausted incompatible Issue84 history.",
  "current_allowed_next_action":"Already authorized independent read-only challenge of this exact proposal",
  "current_allowed_write_counts":{"implementation":0,"remediation":0,"verification":0,"initial_review":0,"final_review":0,"publication":0}
}
```

## Execution paths

State.gate (scripts/ticket_workflow.py:336) rejects retired/delivered/exhausted tickets. Replay (433) rejects owner-led predecessors/splits and split-lineage transitions. Historical child init copies parent limits/counts, which would multiply owner-led remaining allowances. normalized_evidence (274) normalizes authority but local/frozen-prefix checks cannot catch later-sibling reuse. Append (1138) requires candidate-wide validation of all ledgers and cooperating cross-ticket serialization. check_prefix (1227) tests final policy, allowing generic timed initialization plus transition to meet introduction test. completed (1007) sets author_session only after successful implementation: Issue83 interruption consumed its slot without producing successful implementation. ADR0033 continuation requires success and original repo/PR and cannot transport incompatible Issue84 cycles-v1/correction_delivery history or PR85 binding.

## Strict types

Keep schema 1 and exact {type,at,data} event envelope; reject missing/extra keys, duplicate JSON keys, nonfinite values and coercions. Counts have exactly implementation, initial_review, remediation, final_review, design_reset. Exact Python integers (not Boolean) in 0..10000000; bounded arithmetic. Issues positive exact integers; SHA256 lowercase 64 chars. Authority exactly {kind,name,evidence}, kind=user for allocation/grants. Capsule ref exactly {id,generation,digest}. Existing monotone UTC-second times. Authority identity NFKC, collapsed whitespace, casefold of evidence independent of display name. Existing digest canonicalizes the whole {schema:1,events:[...]} document.

## Owner-led split schema and algorithm

Under owner-led-v1, split.data has exactly:

```json
{"authority":{"kind":"user","name":"<name>","evidence":"<distinct approval>"},"capsule":{"id":"<parent>","generation":1,"digest":"<sha256>"},"successor":123,"successor_capsule":{"id":"<child>","generation":1,"digest":"<sha256>"},"counts":{"implementation":1,"initial_review":1,"remediation":0,"final_review":0,"design_reset":0},"reason":"<bounded explanation>"}
```

Example only, no issue number or grant assigned.

1. First split requires no active/suspended phase, delivery, failed-final stop, unresolved blocker or pending repair.
2. Freeze consumed C and pool P=limits-C. Retire parent permanently, preserving audit elapsed and historical state.
3. Nonzero allocation A, 0<=A[k]<=P[k] for every counted phase; immediately debit P-=A.
4. Further splits on retired parent only debit remaining pool. No extension/continuation/phase/delivery/reclamation on retired parent; no automatic returns.
5. Child init predecessor remains {issue,digest}, identifying a complete parent prefix with its unique allocation. Child capsule matches successor_capsule.
6. Child counts=C, limits=C+A, never old parent limits. Inherit historical authors, session roles, authority identities. No inherited design approval, successful implementation, verification, acceptance, review or delivery certification.
7. Missing parent, cycles, duplicate child allocation, cross-repo ref, capsule mismatch or allocation reuse reject.
8. Child explicit extension adds only child limits, not parent/siblings. Allow continuation on validated owner-led descendants only; all other continuation requirements unchanged.
9. Recursive retirement uses same algorithm. Conservation counts actual reservations once, not copied counters multiple times.

Status remaining_counts is retired parent's actual unallocated pool including zero; active child's limits-counts. Report derived retired, inherited_counts, allocated_counts; no manufactured events.

## Whole-lineage approval conservation

Pure repository-wide audit after local replay identifies allocations/grants by issue and event index. Seed relevant ancestor init/capsule authorizations, extensions, transitions and historical timed split approvals. Register new owner-led split/extension/continuation actions across entire connected recorded lineage. Duplicate normalized authority consumed by different actions rejects both temporal orders (extension before/after sibling split). Child capsule may structurally reference its own allocation approval without another grant; alias cannot authorize extension/continuation/another split. Timed-only duplicate strings preserve historical replay but are unavailable to new owner-led grants after transition. Complete current ledger set catches later siblings; frozen prefixes prove inheritance. Call audit in validate_all, append candidate validation and CI. Public State.gate cannot bypass validated lineage context.

## Exact Issue23 to Issue83 introduction/transition

Issue23 complete 10-event document digest edb0ea490e463a75cbb92696e1400c2ad8f32e939ae9fb905db132cb27e0baac.
Issue83 complete 9-event document digest b46ec791f25f51f7e022d00e6a654e0429e59b59a874500247f7f974c60664f9.
Only event10 of this exact Issue83 prefix accepts lineage_policy_transition:

```json
{"type":"lineage_policy_transition","at":"<actual UTC time>","data":{"policy":"owner-led-v1","authority":{"kind":"user","name":"burha","evidence":"<new explicit transition approval>"},"capsule":{"id":"issue-83-authenticated-owned-review","generation":1,"digest":"56f152c798123ae05ae6775870478c709363d745b4e52ac79f5327930e0f4f79"},"prefix_digest":"b46ec791f25f51f7e022d00e6a654e0429e59b59a874500247f7f974c60664f9","predecessor":{"issue":23,"events":10,"digest":"edb0ea490e463a75cbb92696e1400c2ad8f32e939ae9fb905db132cb27e0baac"},"time_barrier":"B83-EXHAUSTED","reason":"<explicit time-policy disposition>"}}
```

Require original repo beagle1903/agentic-etf-advisor, exact retired parent with sole child83 and zero residual pool; no extra parent events/child. Reject missing/mutated/truncated prefixes, intervening child event, repeated transition, reused authority, active/suspended phase or changed capsule. Retain all counts/limits/audit elapsed/owners/authors/failed/interrupted outcomes/certification. Seed consumed authority from both histories including timed parent split. Change only child policy/time interpretation; parent remains timed/retired. DO NOT resolve B83-EXHAUSTED: it also records missing verification/review. Report time component inapplicable but retain blocker/substantive incompleteness; later ordinary resolution requires truthful evidence. Implementation consumed1/remaining0, other four consumed0/remaining1. author_session absent; verified/reviewed/accepted false. No phase starts/resumes.

Workflow implementation PR tests immutable fixtures and does NOT introduce/transition actual pair. Later actual introduction needs separate explicit transition approval and primary Issue83 PR. New-ledger CI introduction requires initialization itself owner-led-v1 except exact pair. Final-policy-only test insufficient. Exact pair exception requires both prefixes, immediate valid transition and primary83; ordinary delivery/content checks still reject uncertified product work. Existing merge-base histories retain prior treatment.

## Atomic and CI contract

One repository-level cooperating-writer lock across ALL ticket appends, existing .lock exclusion. Within lock capture actual event-source bytes, all ledger filenames/bytes and content digest; strictly parse snapshot and form candidate set; replay ALL candidates and audit lineage; write/fsync candidate temp; immediately reread actual source, complete ledgers/membership, candidate temp and content; reject any change, otherwise atomic replace target. Different per-ticket locks insufficient. No hidden external-journal dependency, new exclusions or CI privileges. Preserve live PR metadata, merge-base prefixes, exact repo/PR/content binding.

## Issue84 disposition

Preserved 62-event Issue84 digest e941ecb38388154683e01f982a9397dec8a54d801b634bb56c25e7d1d52551e5. Original counted starts: implementation2, initial_review1, remediation3, final_review3, design_reset2. Architect reports totals with H/R records: implementation4, initial_review3, remediation4, final_review4, design_reset4; source breakdown must remain. Other design/challenge/verification reservations including R1/current D1 remain distinct, not silently relabelled/dropped. Old remaining allowance balances zero. Failed recovery journal digest 2a2ac80fabc45f00a7dbefc52e46baf82cb8a6d1270a4622cf02b825b6e82fe2. Original PR85 content binding f9ffcec169e992a677214253f486e022203785fac2a54184be5cb4198b6fc6f7 and correction binding 7d680f302d12007e99a51f3d8540e7acd35b3e4420c6495116ee07dff2c1c45d stay historical.

Accountable recommended decision: explicit stop on implementation. Authorized challenge may assess this proposal but cannot approve an unspecified bridge. Candidate future finite decision: one workflow implementation, one verification, one independent initial review; zero remediation/final-review retry/design retry/replacement/renewal. Must name independently closable successor and authorize new publication identity preserving Issue84/PR85 as historical work. These are PROPOSED quantities, not granted. Successor cannot default-initialize fresh limits: approved bootstrap must carry every consumed history, zero inherited remaining allowance, authority identity/author exclusions, then add only explicit grant. NO executable bootstrap schema approved here. Importing old certificate transcripts/generic adoption recreates excluded machinery; ordinary init/continuation does not support this.

Rejected: PR85 recertification recovery; history translation/rewriting; default-budget successor with prose-only history; new-PR reuse of old binding; treating D1/challenge as write authority. Closure: recorded user disposition with fully specified independently challenged bootstrap and exact finite/publication binding preserving histories/counts. Until then BLOCKED_FOR_DECISION, no automatic design/implementation.

## Verification matrix

- I84SPLIT/AC84SPLIT: final slot allocated A then B rejects without mutation; cloned parent limits reject; duplicate child/reused allocation/missing parent/cycle/capsule substitution reject specifically.
- I84SPLIT/AC84CYCLES: child extension reuses later sibling approval in either temporal order rejects; migrated child reuses timed parent approval despite name/case/Unicode/whitespace rejects; child extension cannot refill parent/sibling.
- I84HISTORY/AC84HISTORY: timed-only historical duplicates unchanged; exact pair event mutation/truncation/missing parent/new sibling/intervening child event rejects; arbitrary timed init+generic transition introduction rejects.
- I84TIME/AC84TIME: large wait after exact transition no time rejection, implementation still exhausted/certification false.
- I84HISTORY/AC84GATES: extra fields or semantics clearing B83/count changes/product authority/verification reject.
- I84GATES/AC84GATES: other repo/primary issue rejects; correct introduction without product delivery still fails ordinary delivery gate.
- I84GATES/AC84VERIFY: cross-sibling cooperating writer contention no double grant; real source/ledger/membership/temp/content file race rejects without overwriting other's change; actual saved delivery positive passes while other PR/content/certified doc edit/historical writer as reviewer rejects.
- I84ISOLATE/AC84VERIFY: product/graph/role/CI and actual authentication files unchanged.

Immutable fixtures, positive controls reaching intended branches, precise negative rejection assertions; not unrelated earlier failures.

No project files edited or tests executed by architect. Findings based on current repository/retained records. Earlier memory deferral note was not relied on for current facts.

DESIGN_BLOCKED
