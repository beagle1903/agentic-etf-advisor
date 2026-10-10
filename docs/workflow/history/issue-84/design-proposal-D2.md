D2 complete replacement proposal for coordinator transcription. This is a technically complete, read-only design; implementation and publication remain unauthorized. C2 must independently challenge the exact saved proposal before coordinator approval.

**Identity, scope and authority**

- Repository baseline: `67b93e77cc3a2c665fb902e44508ff693f877e43`, inspected clean at `C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab`.
- Architect: `/root/issue84_correction_design`, `design_architect`, `gpt-6-astra`, high.
- Reservation: D2, recorded before dispatch under the user’s October 8 “continue.” The ordinary gate rejection remains a rejection.
- Original frozen contract remains `issue-84-cycle-bounded-workflow`, generation 3, digest `df870f205cc3a8053c152699ce16030a1cedc518fdda0588ae16d3cbcd95fda9`.
- Assigned implementation remainder is owner-led split conservation and whole-lineage authority reuse, plus the exact retained Issue23→Issue83 introduction/transition. The bootstrap below is the narrowly bounded governance disposition needed to execute that remainder without escaping Issue84’s exhausted history.
- Current allowance: one D2 design and one C2 independent challenge only. No implementation, remediation, verification, code review, successor creation or publication allowance is granted by this proposal.

Keep the original S84, six invariant definitions and seven acceptance definitions unchanged. They are available in the preserved ledger’s initialization capsule; changing only its generation from 1 to 3 produces the verified frozen digest above.

The governing invariants remain:

| ID | Required preservation |
|---|---|
| I84CYCLES | Lifetime consumption survives agents, sessions, quotas, resets and successors; additional attempts require explicit finite user authority. |
| I84TIME | Owner-led timing is audit data, never automatic exhaustion or a requirement for minute extensions. |
| I84HISTORY | Historical prefixes, capsules, counters, outcomes and content/PR bindings remain immutable. |
| I84GATES | Separate consequential design, independent challenge, coordinator approval, classified ownership, independent review and identical-content certification remain mandatory. |
| I84SPLIT | Successors inherit consumption and receive only conserved remaining allowances. |
| I84ISOLATE | Changes stay within development governance; Issue83 product work remains preserved. |

Acceptance remains AC84TIME, AC84CYCLES, AC84HISTORY, AC84SPLIT, AC84GATES, AC84DOCS and AC84VERIFY, with their exact original definitions.

Non-goals: authentication/product work; financial, provider, database or graph-state changes; resolving Issue83’s substantive blocker; changing old ledgers or accepted ADRs; importing PR85’s correction/recovery execution machinery; generic adoption; transferred certification; default-budget successors; automatic retries, owner replacement or publication.

**Observed execution paths**

The relevant current implementation is [ticket_workflow.py](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:279):

- `State.gate` rejects suspended phases and uses lifetime remediation counts to determine review prerequisites.
- `replay`, initialization handling, rejects owner-led predecessors and copies historical timed-parent limits into children.
- `policy_transition` rejects predecessors and suspended phases.
- `phase_resume` retains the existing reservation but currently has no distinct transition-only authorization check.
- `completed` assigns `author_session` only after successful implementation.
- `append` locks one ticket, validates its candidate and checks real source/ledger/content bytes before replacement.
- `validate_all` does not yet perform the required whole-lineage grant audit.
- `check_prefix` checks final policy rather than the initialization policy.
- `check_pr` requires current primary-issue delivery bound to actual repository, PR and content.

The live source confirms that an inherited successor at counts `4/3/4/4/4` cannot simply use today’s initial-review gate: the inherited remediation count would reject it. The contract below explicitly distinguishes inherited consumption from the new successor’s local phase prerequisites.

Current governing records are [ADR0033](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/docs/architecture/decisions/0033-owner-led-finite-continuation.md:1), [ADR0034](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/docs/architecture/decisions/0034-bounded-coordinator-arbitration.md:1), and the active [Iteration019 record](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/docs/iterations/019-coordinator-arbitration.md:1). The focused scope is confirmed by the [Issue84 reconciliation](https://github.com/beagle1903/agentic-etf-advisor/issues/84#issuecomment-6038690233).

**Common strict types and validation**

Retain schema 1 and exact event envelope `{type, at, data}`. New variants use exact key sets; reject unknown/missing fields, duplicate JSON keys, nonfinite numbers and coercions.

- Counts: exact keys `implementation`, `initial_review`, `remediation`, `final_review`, `design_reset`; exact integers, excluding Boolean, bounded to `0..10000000`. Check additions for overflow before mutation.
- Issue/PR numbers: positive exact integers.
- SHA256: lowercase 64-character hexadecimal.
- Authorities: existing exact `{kind,name,evidence}`; user grants require `kind:"user"`.
- Capsule references: exact `{id,generation,digest}`.
- Timestamps: existing monotone UTC-second representation.
- Approval normalization: Unicode NFKC, whitespace collapse, case-fold of evidence, independent of display name. Where a historical or new record has an authority anchor, normalize and conserve that anchor independently too.
- Session comparisons for independence use the same normalization. Preserve original display strings.
- Canonical JSON digest: existing `digest`, over the complete JSON value with sorted keys, compact separators and `ensure_ascii=True`. A ledger digest includes `{schema:1,events:[...]}`.
- Raw file hashes separately bind bytes where specified.

No serialized graph/checkpoint state changes occur. New workflow state is JSON-serializable when projected for status: lists/maps for histories, pools, provenance and identity sets.

**Owner-led splits**

For owner-led parents, `split.data` has exactly:

```json
{
  "authority": {"kind": "user", "name": "...", "evidence": "..."},
  "capsule": {"id": "...", "generation": 1, "digest": "..."},
  "successor": 123,
  "successor_capsule": {"id": "...", "generation": 1, "digest": "..."},
  "counts": {
    "implementation": 0,
    "initial_review": 0,
    "remediation": 0,
    "final_review": 0,
    "design_reset": 0
  },
  "reason": "..."
}
```

The example gives the schema, not a grant.

1. The first split requires no active or suspended phase, delivery, unresolved blocker, failed-final stop or pending repair.
2. Freeze inherited consumption `C = parent.counts` and available pool `P = parent.limits - C`. Reject negative components.
3. Require a nonzero allocation `A`, with `0 <= A[k] <= P[k]` for every counted phase. Debit it immediately.
4. Retire the parent permanently. Later sibling allocations may only debit the retained pool. Retirement permits no phase, delivery, extension, continuation or automatic reclamation.
5. A child’s existing `{issue,digest}` predecessor reference identifies a complete parent prefix containing exactly its allocation. Verify the child identity and `successor_capsule`.
6. Set child `counts=C`, `limits=C+A`, and `inherited_counts=C`. Never copy the parent’s unallocated limits.
7. Inherit every prior session, write/verification author and consumed authority identity. Do not inherit successful implementation, design approval, verification, acceptance, review or delivery certification.
8. Local phase prerequisites use local events and `counts-inherited_counts`; lifetime limits always use total `counts`. In particular, a child without local remediation may take its explicitly allocated initial-review slot despite historical remediation. A child’s own failed review, remediation, final-review and verification requirements remain enforced.
9. An explicit child extension affects that child only. It never replenishes a retired parent or sibling.
10. Apply the same rules recursively. Detect cycles, duplicate allocations, missing parents, cross-repository references and capsule substitutions.
11. Pending allocations to not-yet-created children still debit the parent and consume their authority. Missing child initialization does not refund an allocation.

Retired-parent status reports its actual remaining count pool, including zero. Child status reports inherited counts, allocated counts, local consumption and remaining total limits. Historical timed `split_remaining` stays a separate seconds value.

**Whole-lineage authority conservation**

After local replay, audit the complete current ledger set as one lineage graph. Frozen parent prefixes establish inheritance; current sibling records establish later actions.

Identify a grant/action by its issue and event index. Register consumed normalized evidence and any recorded normalized authority anchor from:

- Ancestor initialization/capsule authorization.
- Timed and owner-led splits.
- Extensions and policy transitions.
- Continuations.
- The special Issue84 inheritance disposition below.

A reference to the same bundled grant is an alias, not a second grant. The child’s capsule may reference its own allocation authority; that alias cannot authorize another split, extension or continuation.

Historical timed-only duplicates remain replay-compatible. Their identities are nevertheless consumed and unavailable to any new owner-led grant in that lineage.

Reject reuse regardless of order: earlier-child extension before later-sibling allocation, and later-sibling allocation before earlier-child extension. Scan pre-transition timed ancestors too. Inspect all current sibling records, not merely the child’s frozen predecessor prefix.

Call this audit from repository validation, status/check, candidate append validation and CI. A public dispatch/delivery path must not obtain a gate-capable state by bypassing validated lineage context.

Count actual reservations once using their source identity. Copied inherited counters and duplicated archival representations never become new starts.

**Exact Issue23→Issue83 introduction and transition**

The only exceptional pair is:

| Source | Required complete canonical digest | Events |
|---|---|---:|
| Issue23 | `edb0ea490e463a75cbb92696e1400c2ad8f32e939ae9fb905db132cb27e0baac` | 10 |
| Issue83 | `b46ec791f25f51f7e022d00e6a654e0429e59b59a874500247f7f974c60664f9` | 9 |

Raw retained file hashes are respectively:

- `724087c8856d412e98070c8e677ff37e3c17638bd188c11e38c722f7329267b0`
- `0a975b01eb0a5732eecbccfca0de99ff0a952a9787c2af15b6870c08097f248c`

Only Issue83 event 10 accepts:

```json
{
  "type": "lineage_policy_transition",
  "at": "<actual UTC time>",
  "data": {
    "policy": "owner-led-v1",
    "authority": {"kind": "user", "name": "...", "evidence": "..."},
    "capsule": {
      "id": "issue-83-authenticated-owned-review",
      "generation": 1,
      "digest": "56f152c798123ae05ae6775870478c709363d745b4e52ac79f5327930e0f4f79"
    },
    "prefix_digest": "b46ec791f25f51f7e022d00e6a654e0429e59b59a874500247f7f974c60664f9",
    "predecessor": {
      "issue": 23,
      "events": 10,
      "digest": "edb0ea490e463a75cbb92696e1400c2ad8f32e939ae9fb905db132cb27e0baac"
    },
    "time_barrier": "B83-EXHAUSTED",
    "reason": "<explicit transition-only disposition>"
  }
}
```

Require the original repository and exact parent/child histories, with no intervening event, changed capsule, extra parent event, extra successor or repeated transition.

The parent’s exact replay contains:

- Initial split-time pool: 6,056 seconds.
- Allocation to Issue83: 6,051 seconds.
- Retained historical `split_remaining`: **5 seconds**.
- Sole successor: Issue83.
- Retired timed state.

Preserve all five seconds. They are historical timed data, not owner-led count allowances, and cannot be converted to counts. This exception does not transition Issue23 or authorize a second child.

Issue83’s transition precondition must positively require the exact retained suspension, not reject it:

- `active is None`.
- `suspended.phase == "implementation"`.
- `suspended.session == "/root/issue83_implementation"`.
- Suspended capsule/role/start metadata equal the retained event 7 reservation.
- `clock_running is False`.
- Implementation consumption and limit both equal 1.
- `author_session is None`.
- Verification, acceptance and review remain false.
- Event 8 remains `outcome:"interrupted"`.
- B83-EXHAUSTED remains present with its original criterion, scenario, evidence and required-remediation value.

The transition changes only the child’s policy and the interpretation of its timing barrier. It grants zero counts and causes no phase start, resume, successful completion, blocker resolution or certification. It seeds consumed authorities from both complete histories.

Status distinguishes:

- Historical timed debt and the parent’s five-second residual.
- Timing no longer being an owner-led rejection reason.
- The existing suspended reservation.
- Zero additional implementation starts available.
- Substantive verification/review incompleteness still blocking delivery.

A future resume is a separate user decision. For this exact transitioned reservation only, require `phase_resume.data` to be exactly `{session,authority,capsule,reason}`; the additional user authority must be distinct from the transition grant and all inherited consumed identities. It resumes the same suspended reservation without incrementing or resetting its count. It does not resolve B83 or set any successful/certified flag. Ordinary resumes elsewhere retain their existing schema.

This future resume possibility is specified so the time-only transition is executable; neither actual introduction, transition nor resume belongs to the workflow implementation grant.

For CI introduction, ordinary new ledgers must initialize with `owner-led-v1`. Final-policy-only checking is insufficient. The exact pair is the sole timed introduction exception: both complete prefixes, immediately followed by the valid child transition, original repository and primary Issue83. All ordinary product delivery/content gates still apply. Merely introducing the pair cannot pass Issue83 delivery.

**Exact exhausted Issue84 source acquisition**

Use literal archived source documents. Do not load or execute old correction/recovery code.

The mandatory fixed historical inputs are:

| Name | Source | Canonical digest |
|---|---|---|
| L84 | Preserved complete 62-event Issue84 ledger | `e941ecb38388154683e01f982a9397dec8a54d801b634bb56c25e7d1d52551e5` |
| H | Complete correction journal | `743aec3b11e23638bc7e6e4c5180775cbd790cee18575c7af4167f12e2bf70df` |
| R | Complete failed last-recovery journal | `2a2ac80fabc45f00a7dbefc52e46baf82cb8a6d1270a4622cf02b825b6e82fe2` |
| S0 | Coordinator supplemental record through D2 start, 11 events | `33fee8d76801460432d6b2542299cecbc8a8f385c002f76c5f7e578212a4ebc9` |

Sources:

- L84: `C:/Users/burha/.codex/worktrees/cycle-bounded-workflow/agents-lab/docs/workflow/tickets/issue-84.json`.
- H: `C:/Users/burha/.codex/pr85-correction-journal.json`.
- R: `C:/Users/burha/.codex/pr85-last-recovery-journal.json`.
- S0: `C:/Users/burha/.codex/issue84-remainder/authorization-and-phases.json`, preserving its exact first 11 events and top-level fields.

L84 raw SHA256 is `6ee4fae0cf99cb2211d3fb8ee2df0857fc6be051613a7d8b9fb87fd67abcbbec`; H raw SHA256 is `ce0a56d952cb1209dadfb3667c8f9b03ac0e6e0853f4212a21c5f018d60d644e`; R raw SHA256 is `eb2b20bbe52b3f6b6867226e8a96528d9452a00601f5fb1492ab8085d8276d02`.

Preserve the prior D1 proposal, C1 failure and E1 stop as literal text sources with raw hashes:

- D1: `86cd40b398c9b8bb2a2b4dfb535710a2d1841b9095ce5acf70cccfa672db9c00`.
- C1: `39aaf227e64caad23457c7b2931dffbbe3e1b8e82261b622179aa0dc8461dc53`.
- Original E1: `69226227c74e03cd33e56bbe033097b5590a004d45ad77340249311a28f718d7`.
- Last-recovery failure handoff: `14c1e463f0ad8edfc19826ff8e53dea6e1d0877790e90e66f73f9b6af9f68a13`.

Any subsequent coordinator resolution is a separate appended/new record, not a replacement of the original E1 stop.

Acquisition must read complete actual files, verify the fixed hashes, and confirm no unaccounted later source work or events. Do not silently slice a newer L84/H/R document to the expected prefix. A changed historical source or unexplained additional reservation stops the proposed bootstrap.

H is already embedded exactly in L84 event 62: require equality of its `historical_import` and `transcript` with those event-62 fields. Preserve both source representations, but count H once.

R contains the R1 start in `bootstrap.reservation.events`, R1 completion in transcript event 1, and R2–R5 starts/results in the transcript. Require exactly the retained 11 transcript entries and R5’s failed result. The embedded CI-failure source and all observations remain part of R.

The strict recognition rule for these old documents is fixed complete digest plus exact source structure/selectors. It does not accept arbitrary legacy data with a caller-supplied hash. This is an immutable historical projection, not successful replay through today’s incompatible normal engine and not historical certification of new content.

**Historical accounting projection**

Derive, then compare against the fixed expected accounting:

| Source | Implementation | Initial review | Remediation | Final review | Design reset |
|---|---:|---:|---:|---:|---:|
| L84 native phase starts, events 1–61 | 2 | 1 | 3 | 3 | 2 |
| H1–H10 | 1 | 1 | 1 | 1 | 2 |
| R1–R5 | 1 | 1 | 0 | 0 | 0 |
| Total | **4** | **3** | **4** | **4** | **4** |

H phases derive from the six imported phase records, then H7–H10 transcript starts. H6’s transcript completion closes the imported reservation; it is not another start. Map H7 to challenge, H8 to implementation, H9 to verification and H10 to initial review. H1–H6 retain their recorded phase types.

R1 is a separate supplemental design allowance, not a design-reset count. D1 and D2 are separate supplemental `design_revision` reservations; C1 and C2 are separate challenges. None disappear into, or replenish, the five counted pools.

Native verification starts total four; H2/H9 add two and R4 adds one. Preserve these seven historical verification reservations individually, including the coordinator-owned H2 record and unknown historical timestamps. Preserve native and supplemental designs/challenges individually as well.

Expected historical write/verification exclusions include:

```text
/root
/root/issue84_implementation
/root/issue84_implementation_correction
/root/pr85_status_correction
/root/pr85_redelivery_implementation
/root/pr85_last_recovery_implementation
```

Derive the union from all source starts and H `write_authors`, then assert these inclusions. Include later applicable authors from the completed supplemental source too. Do not infer independence solely from role labels or omit interrupted/failed authors.

Preserve all authority objects, anchors, outcomes, observations, interruptions and source references. Historical missing timestamps remain explicitly unknown; never manufacture elapsed time. D1’s recorded 3,441 seconds and C1’s 479 seconds remain unchanged; D2/C2 receive actual measured audit values.

The two historical PR85 bindings remain:

- Original: repository `beagle1903/agentic-etf-advisor`, PR85, content `f9ffcec169e992a677214253f486e022203785fac2a54184be5cb4198b6fc6f7`.
- Correction: same repository and PR85, content `7d680f302d12007e99a51f3d8540e7acd35b3e4420c6495116ee07dff2c1c45d`.

They are historical bindings only. R5 remains failed, B85-EXTERNAL-JOURNAL-FILE-RACE remains unresolved for the stopped PR85 recovery, and the original work remains superseded/blocked as recorded.

**D2/C2 completion without circular digests**

Use three sequential layers.

1. **Challenge input.** After saving this complete D2 proposal and recording its actual completion, the coordinator builds a strict manifest:
   ```text
   {
     schema: "issue84-d2-challenge-input-v1",
     proposal_digest: SHA,
     frozen_capsule: CapsuleRef,
     fixed_sources: map of the fixed source names above to their verified digests,
     supplemental_prefix_digest: SHA,
     supplemental_event_count: positive integer
   }
   ```
   The supplemental prefix includes the exact S0 prefix, D2 completion and C2 reservation. Its complete bytes are supplied to C2. C2 reviews the proposal and that manifest, including the projected accounting. C2’s result names both exact digests.

2. **Completed closeout.** After C2, record its actual result and coordinator decision. Archive the complete supplemental document through that decision, C2’s actual result text, D2’s text and the new coordinator resolution. Validate that the challenged supplemental prefix remains an exact prefix. No D2/C2 outcome may be omitted. No extra phase or grant may be hidden in the suffix. Permitted suffix content consists of measured audit/interruption observations, the existing C2 reservation’s result, and the coordinator disposition; any additional reservation or authority requires a new explicit decision and cannot use this instance.

3. **Future user disposition.** A later finite user grant binds the completed closeout manifest digest, this proposal digest, the challenge-input digest and its PASS result, and the deterministic execution capsule described below.

This proposal does not embed its own digest or predict C2’s result, closeout digest, future authority, target issue or PR number. Those are constrained instance values, not technical decisions left for implementation. C2 failure or absent coordinator approval makes the future bootstrap inadmissible.

For every source descriptor use exact `{path,kind,raw_sha256,canonical_sha256}`. `kind` is `json` or `text`; canonical hash is null for text. Paths are fixed repository-relative archive locations, never runtime arbitrary filesystem paths. Archive all required files under `docs/workflow/history/issue-84/`; the manifest names exactly the required sources and rejects extra/missing names.

The final closeout manifest has exactly `{schema,repo,source_issue,frozen_capsule,proposal_digest,challenge_input_digest,sources,coordinator_decision}`. Its decision contains exact `{authority,proposal_digest,challenge_input_digest,outcome,evidence}` with coordinator authority and `outcome:"approved"`. C2’s bound result must be PASS and its session independent of D2 and all historical write/verification authors.

The later user grant binds this whole manifest, so no final outcome is self-excluded or silently replaced.

**Narrow future Issue84 inheritance bootstrap**

Recommended future disposition: one separately identified successor **N**, one new implementation owner, one implementation, one verification and one independent initial review, with zero remediation, final-review retry, design/reset/challenge retry, owner replacement or automatic renewal. Authorize at most one new PR for N. These quantities are proposed, not granted.

The future explicit grant has exactly:

```text
{
  schema: "issue84-remainder-finite-disposition-v1",
  repo: "beagle1903/agentic-etf-advisor",
  source_issue: 84,
  target_issue: N,
  authority: {kind:"user", name:Text, evidence:Text},
  authority_anchor: Text,
  proposal_digest: SHA,
  closeout_digest: SHA,
  execution_capsule_digest: SHA,
  owner: {role:"implementation_worker", model:"gpt-6-sol",
          effort:"medium", session:Text},
  counts: {implementation:1, initial_review:1, remediation:0,
           final_review:0, design_reset:0},
  supplemental: {verification:1, design:0, challenge:0, design_revision:0},
  seconds: 0,
  publication: {mode:"one-new-pr", repo:"beagle1903/agentic-etf-advisor",
                primary_issue:N, count:1, excluded_prs:[85]},
  bootstrap_exception: true,
  reason: Text
}
```

N is a newly explicitly designated issue, not 23, 73, 83, 84 or any existing ledger. The owner is fresh, explicitly selected and excluded from review. Reject reused authority evidence or anchors from the whole imported lineage.

Instantiate a normal complete execution capsule using the same original S84, invariant and acceptance definitions, with:

- `id:"issue-N-issue84-remainder"`, `generation:1`, target repository/issue N.
- Consequential classification and the explicitly named future owner.
- User authorization copied from the grant’s authority object.
- Non-goals, interfaces, state impact, verification, documentation, risks and escalation rules specified in this D2 contract.
- Rationale identifying the exhausted Issue84 inheritance and focused remainder.
- `escalation:null`.

Its broader original S84 definition does not widen implementation: the D2 proposal digest and assigned remainder are additional mandatory scope bounds. Preserve the original generation-3 capsule separately, byte/value unchanged. The successor’s new administrative identity does not rewrite that capsule.

To avoid a digest cycle, compute the execution capsule from the grant’s authority object and owner before computing the final grant object/digest; the capsule does not contain the grant digest.

This is a single compiled bootstrap instance. The implementation pins the selected N, grant digest, closeout digest and proposal digest as constants after the future user decision. It does not expose a generic caller-selected adoption/import command. Future attempts to reuse the source for another issue or publication require rejection, not a new default.

Use ordinary schema-1 `initialize` with its existing required fields, `policy:"owner-led-v1"`, `adoption:null`, `predecessor:null`, plus one special key:

```text
issue84_remainder: {
  version: "issue84-remainder-inheritance-v1",
  source_issue: 84,
  history_manifest_digest: SHA,
  proposal_digest: SHA,
  grant_digest: SHA
}
```

That extra key is accepted only for the exact pinned instance. All ordinary initialization schemas stay strict and future generic adoption remains forbidden.

Initialization atomically validates the complete archive, closeout, grant, capsule derivation and global uniqueness before returning any state. Set:

- `counts = {4,3,4,4,4}`.
- `inherited_counts = counts`.
- Inherited old remaining allowances: all zero.
- `limits = counts + grant.counts`, therefore `{5,4,4,4,4}`.
- Supplemental historical reservation registry retained, with only one new verification available.
- Current successful implementation, verification, acceptance, review and delivery: absent/false.
- Current delivery history: empty.
- Historical delivery history: both unchanged PR85 bindings.
- Historical outcomes/findings/author exclusions/authority identities: complete derived union.
- Current approved owner: the explicitly selected fresh owner.
- No inherited operational suspension or active phase; original source reservations remain in the historical registry.

Bind current design/challenge readiness to D2/C2 and coordinator approval of the exact parameterized D2 contract, plus the user-approved deterministic capsule instance. Do not use any original Issue84, H or R design approval as readiness for N.

The new finite disposition permits a fresh implementation of the focused remainder. It does not relabel R5 as passed or resolve its stopped recovery. The successor’s historical findings projection must continue to show that failure and explain that the corresponding PR85 mechanism is excluded. Its current acceptance must prove that no runtime correction/recovery certificate or external-journal dependency was imported.

Current phase prerequisite flags derive only from N’s phases; lifetime counts include inherited starts. This allows the one explicitly granted initial review after N’s own successful implementation/verification/acceptance. A failure in N remains a current blocker and cannot be hidden as inherited history.

For this instance, reject split, continuation, extension, design/reset/challenge starts, owner handoff and remediation/final-review starts. A new explicit finite user decision would need a separately specified successor disposition; ordinary defaults do not apply.

Maintain a unique source-claim registry during full-repository validation: L84’s pinned lineage root can be claimed by exactly N once. A duplicate target, alternate source alias, duplicate initialization or attempted live Issue84 reopening rejects.

**Before the new engine exists**

The later grant must explicitly authorize the bootstrap exception above. Otherwise implementation remains blocked.

After that grant, the coordinator first runs the current ordinary check and retains its real rejection. Before dispatch, the coordinator records the exact initialization and implementation `phase_start` under the approved narrow exception, with the actual timestamp and owner. The durable target ledger and local reservation must agree; no successful engine check is invented.

The implementation start consumes the granted slot immediately: total implementation consumption becomes 5. The owner builds support for this exact contract within that reservation. Once available, the new engine must validate the actual saved initialization/start and all archived sources before any next phase or successful completion is accepted.

A disagreement between saved reservation, grant or new replay stops the attempt; it cannot be repaired by deleting the start, editing history or issuing a fresh default ledger. This exception is solely for the first implementation start needed to build the new validator. Verification and review require functioning native gates and recorded reservations.

**Publication and CI**

The successor’s eventual publication uses ordinary fresh implementation, verification, acceptance, independent review and delivery events. It does not emit `correction_delivery` or `recovery_delivery`.

Required order:

1. Complete implementation, tests, archive, manifest and reviewable documentation within the implementation reservation.
2. Freeze content and reserve the one verification on that content.
3. Complete required verification and content-bound acceptance.
4. Reserve the one independent initial review. Exclude every historical and current implementation, remediation and verification author, plus D2/C2 design participants as required by the independent-session contract.
5. A failed completed verification/review stops; no repair/review retry is granted.
6. After a clean review, allocate exactly one draft PR identity for the authorized branch `codex/issue-N-issue84-remainder`, targeting main. This pre-delivery draft allocation is explicitly part of the later finite publication authority, not permission to merge or claim delivery.
7. Record a single `publication_target` event, exact data `{repo,pr,grant_digest,evidence}`. Require the original repository, PR other than 85, new PR creation after the future grant, primary issue N and the authorized branch. Repeated or changed target rejects.
8. Ordinary delivery must bind exactly that target and the freshly verified/accepted/reviewed content.
9. Run focused workflow and CI-equivalent offline checks against the **actual saved delivered ledger**, then current-PR/content checks. Record their true results in excluded current-ledger evidence or linked external evidence without changing certified source/docs.
10. Publish the delivered ledger and verify exact-head CI before claiming merge readiness.

Creating the draft can produce an expected missing-delivery CI rejection before the delivery event exists. Preserve that outcome; it is not a passed delivery gate. The final delivered-head checks must pass.

All archive files, manifests and frozen grant documents participate in the normal repository content digest. Add no content exclusions. Only existing current-ticket and lock/temp exclusions apply.

CI must verify:

- Immutable merge-base live-ledger prefixes.
- Immutable archived sources and the fixed source-claim instance.
- The target ledger’s exact N, grant, owner and capsule.
- Original initialization policy, with only the explicit pair/bootstrap exceptions.
- Current primary issue N and exact fresh PR/content binding.
- Historical PR85 bindings cannot satisfy N’s delivery.
- Source Issue84 cannot exploit historical-issue exemption to certify this new work.
- A PR with a changed inherited target ledger cannot evade the target binding by changing its primary-issue marker.

Publication checks execute from the saved repository state; fixtures never infer their baseline from a mutable live ledger tail.

**Atomicity and dependency boundaries**

Use one repository-level cooperating-writer lock for all ticket appends and source-claim/allocation updates; per-ticket locks alone cannot conserve sibling pools.

Within the lock:

1. Capture actual event-source bytes, every ledger filename/byte sequence, all required archived source/manifest/grant bytes and current repository content.
2. Parse strictly; form the candidate complete ledger set.
3. Replay every relevant ledger and run full lineage, authority and unique-source-claim audits.
4. Write/fsync the candidate temporary file.
5. Immediately reread all captured real inputs, complete membership, temporary bytes and repository content.
6. Reject any difference; otherwise atomically replace only the target ledger.

No runtime external-journal path exists. Archived historical files are ordinary content-bound repository inputs. The coordinator’s local files are acquisition sources before freezing; after archival they cannot silently influence replay or publication.

This protects cooperating writers and detects observed file changes. It does not authenticate human approvals or lock arbitrary editors; publication still requires a quiescent workspace.

**Focused acceptance fixtures**

Use immutable fixture documents, positive controls that reach the intended branch, and precise negative rejection assertions.

| Frozen IDs | Required scenarios |
|---|---|
| I84SPLIT / AC84SPLIT | Allocate the final count to child A; child B over-allocation rejects without mutation. Valid siblings consume disjoint allocations; retired status reports exact residual including zero. |
| I84SPLIT / AC84CYCLES | Child limits are inherited consumption plus allocation, never copied parent limits. Duplicate child/allocation, missing parent, cycle, capsule substitution and parent-refund attempts reject. |
| I84SPLIT / AC84CYCLES | Later-sibling approval reuse by earlier-child extension rejects in both temporal orders, including normalized name/Unicode/case/whitespace variants. Timed-ancestor approval reuse after transition rejects. |
| I84HISTORY / AC84HISTORY | Timed-only historical replay remains unchanged; original archive documents and all failed outcomes remain exact. |
| I84TIME / AC84TIME | Exact Issue83 event-10 transition succeeds with the actual suspended reservation, clock stopped and implementation count 1/1. Arbitrarily long later time changes no count or flags and causes no timing rejection. |
| I84HISTORY / AC84HISTORY | Parent’s 6,056/6,051/**5** time accounting remains exact. No conversion to count allowance. Zeroing those five seconds fails. |
| I84GATES / AC84GATES | Transition preserves interrupted outcome, absent author, B83 and false certification. Automatic or transition-authority-only resume rejects; separately authorized same-reservation resume changes no count or blocker. |
| I84HISTORY / AC84GATES | Mutated/truncated pair, intervening event, extra parent/child, wrong repository/primary issue and arbitrary timed-init-plus-transition introduction reject. Correct pair without product certification fails delivery. |
| I84CYCLES / AC84HISTORY | Bootstrap derives native/H/R `4/3/4/4/4`, counts H once, retains seven historical verification reservations and separate D1/C1/D2/C2. Omission or relabeling of any reservation/result rejects. |
| I84GATES / AC84GATES | Missing source, altered hash, reconstructed source with omitted failure, forged source selector, changed S0 prefix or missing C2/coordinator outcome rejects. |
| I84GATES / AC84GATES | C2 result for another proposal/input snapshot, failed challenge, absent approval, reused future authority, mismatched deterministic capsule or historical author as reviewer rejects. |
| I84CYCLES / AC84SPLIT | No future grant means no bootstrap. Valid grant yields limits 5/4/4/4/4 and exactly one verification. Implementation reservation consumes the fifth implementation; retries, extra review/verification, defaults and second successor reject. |
| I84GATES / AC84GATES | N can reach its granted initial review despite inherited remediation count; N’s local failed verification/review/remediation conditions cannot be bypassed using inherited-baseline logic. |
| I84HISTORY / AC84GATES | Historical PR85 bindings remain visible but cannot certify N, another PR or changed content. Fresh N delivery succeeds only with its recorded new target. |
| I84GATES / AC84VERIFY | Cross-ticket lock contention prevents double allocation. Actual event/source/archive/manifest/ledger-membership/temp/content-file changes before replacement reject without overwriting another writer’s change. |
| I84GATES / AC84VERIFY | Run positive and negative fixtures before delivery and against the actual saved delivered ledger; archive/live-ledger tail changes cannot alter the intended fixture baseline. |
| I84ISOLATE / AC84VERIFY | Product/authentication files, primary Issue23/83 histories, graph JSON, role pins, provider boundaries and CI privileges remain unchanged. |

Required verification also includes the repository’s configured Ruff lint/format, mypy, offline pytest, both workflow validators, offline evaluations, package build, Compose configuration and diff checks. No services, live providers or financial actions are introduced.

**Documentation, risks and final disposition**

Add a new ADR narrowly extending ADR0033 for owner-led allocation, the exact pair exception and the single exhausted-source disposition. Preserve accepted ADRs, original Issue84 capsule and prior failed records. Update current workflow instructions, templates and iteration evidence only where these contracts require it. Do not revive `wishlist.md`.

Main risks are incomplete inheritance, aliasing a consumed approval, confusing historical failure with current certification, cross-ticket races, and accidentally turning the pinned bootstrap into generic adoption. The complete-source hashes, deterministic projection, unique source claim, explicit finite grant, separate current prerequisites and actual-delivered-state tests are mandatory controls.

No repository files were edited and no tests or mutating commands were executed during D2. The source observations and hashes above were read-only.

The next permitted action is the already-authorized C2 challenge against this complete saved proposal and its input snapshot. If C2 fails, preserve the result and stop `BLOCKED_FOR_DECISION`. If C2 passes and the coordinator approves, present the exact instantiated finite successor/bootstrap/publication decision to the user. This design alone authorizes none of those writes.

DESIGN_READY
