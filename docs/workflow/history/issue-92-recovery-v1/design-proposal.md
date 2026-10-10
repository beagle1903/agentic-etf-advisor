R92D1 complete proposal for coordinator transcription and the single independent challenge. This proposal grants no implementation, tests, verification, code review or publication.

## Identity and frozen contract

Architect: `/root/issue92_recovery_design`, `design_architect`, `gpt-6-astra`, high. Reservation R92D1 began at `2026-10-09T09:50:08Z` in the coordinator’s local recovery record. The native design-reset check rejected the exhausted Issue92 grant; that rejection remains truthful.

This is a consequential recovery contract for the demonstrated failure `B92-LIVE-LEDGER-FIXTURE-DRIFT`, against existing `AC84VERIFY` and `I84GATES`. Preserve the complete existing definitions of S84, all six invariants and all seven acceptance criteria.

- Issue92 capsule: `issue-92-issue84-remainder`, generation 1, digest `197879ccd445194f77287455919e1f15efb5dce4366c5283a000ab6405dbeace`.
- Original Issue84 capsule: generation 3, digest `df870f205cc3a8053c152699ce16030a1cedc518fdda0588ae16d3cbcd95fda9`.
- Original Issue92 grant: `76f78ac061f9e2c69b6a3aba6e4e89f4b7875321facce3e79b3c6dbdc1f53c2d`.
- Original D2 proposal: `48d4b86ce324331a5d2dbf8ae0d42254243de83f4cd329fc7f4a63c067ab8458`.
- Original closeout manifest: `a161bebe339b8c8ad97fc934896089a501d3f6756ff3102843d539c702ec6eb8`.
- Exact six-event Issue92 stop ledger: `290ffe7e16d19de8c7e67df54cbf06c517e6313778a377da20877af9490a967a`.
- Its raw SHA256: `382fe647e24fcaf6dd8e5a006bed7fbb32389cdab7af9b134f37bb83c099ce0f`.
- Failed repository content: `a69779793820e624eb12f66f0fb6f243db7f7fc14940161b984a46ec5c6e5d4f`.

The recovery supplements the original execution restrictions only through a later explicit finite user grant. It does not rewrite the original grant or capsule, advance its generation, alter frozen definitions, or treat the old no-remediation grant as if it had authorized this repair.

## Observed defect and execution paths

The [Issue92 stop record](https://github.com/beagle1903/agentic-etf-advisor/issues/92#issuecomment-6066080432) records six failures, 1,393 passes and 47 skips. Read-only inspection confirms the common cause:

- `test_saved_issue92_bootstrap_is_pinned_and_retains_failed_history` loads `workflow.read_all(root)[92]` and assumes implementation remains active.
- `test_issue92_one_verification_and_historical_reviewer_exclusions` loads the same live ledger and appends synthetic events beginning at `2026-10-08T09:07:37Z`.
- `issue92_certified_value`, used by the publication test, does the same.
- The three archive/grant race cases copy the live ledger into a temporary repository and append an implementation completion. After the real verification reservation exists, they encounter recorded-content rejection before their intended race.

References: [tests/test_ticket_workflow.py:581](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/tests/test_ticket_workflow.py:581), [line 641](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/tests/test_ticket_workflow.py:641), [line 911](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/tests/test_ticket_workflow.py:911), [line 1093](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/tests/test_ticket_workflow.py:1093).

The consequential recovery constraints are real:

- `State.gate` expressly forbids Issue92 remediation and any second verification.
- `completed` records the failed verification’s required remediation count as 5.
- The blocker also requires remediation count 5.
- Ordinary owner-led initial review rejects any local remediation, requiring final review instead.
- Issue92 explicitly forbids ordinary extension, continuation, owner replacement and final review.
- `append` checks recorded content and rereads real inputs before replacement.
- `check_pr` requires the actual delivered ledger and exact PR/content identity.

References: [State.gate](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:822), [phase_start ownership and independence](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:1131), [blocker/resolve](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:1358), [completed](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:1699), [append](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:1962).

The original D2 acceptance contract already requires immutable fixtures and actual saved-delivery checks. These requirements are existing closure conditions, not new scope.

## Scope, owner and non-goals

The proposed future repair is owned by the existing `/root/issue84_remainder_implementation`, `implementation_worker`, `gpt-6-sol`, medium.

Permitted work is limited to:

1. Immutable, portable Issue92 fixture baselines and precise positive/negative coverage.
2. The narrowly pinned recovery event, replay state and native gates specified here.
3. Preservation and validation of the recovery’s immutable sources, authorities and reservations.
4. Necessary workflow documentation and a new ADR explaining this one disposition.
5. Existing Issue92 certification and publication, contingent on successful fresh verification and independent review.

No product/authentication work, Issue23/83 introduction/transition/resume, financial writes, provider/database changes, graph-state changes, role/configuration changes, CI privilege changes, new issue, replacement owner, new implementation pass, generic adoption, automatic retry or merge is authorized by the proposed disposition.

Preserve the primary checkout and all stopped historical worktrees.

## Accounting and review classification

Use the ordinary counted `remediation` phase for the repair. Do not invent an uncounted repair phase or alter inherited consumption.

| Item | Before recovery | Proposed change | After reservation |
|---|---:|---:|---:|
| Implementation count/limit | 5/5 | +0 | 5/5 |
| Initial-review count/limit | 3/4 | +0 | 3/4 until its one start |
| Remediation count/limit | 4/4 | limit +1 | 5/5 at repair start |
| Final-review count/limit | 4/4 | +0 | 4/4 |
| Design-reset count/limit | 4/4 | +0 | 4/4 |
| Issue92 verification starts/limit | 1/1 | limit +1 | 2/2 at fresh verification start |
| New PR allowance | 1 unused | +0 | one original allowance |

Historical inherited counts stay `4/3/4/4/4`; they must not be changed to conceal the local remediation.

R92D1 and its independent challenge are separate supplemental reservations. They do not become native design-reset starts, consume review slots or replenish any counted pool. Preserve all prior native/H/R/D1/C1/D2/C2 reservations and outcomes.

The unused initial review may be conserved. This requires an explicit, Issue92-only rule: this one successful remediation occurs before Issue92’s first local review, so the existing single initial-review allowance reviews the complete repaired implementation. It remains counted as `initial_review`. No review is relabeled and no additional review allowance is granted.

The exception applies only when all of these conditions hold:

- The exact approved recovery event is present.
- The exact six-event stop prefix is intact.
- Exactly one local remediation has started and completed successfully.
- No Issue92 initial or final review has previously started.
- The fresh verification and full acceptance pass on identical repaired content.
- No blocker, pending repair, active/suspended phase or completed recovery failure remains.
- The initial-review count is still 3 with limit 4.

Other tickets and other Issue92 histories retain the ordinary remediation/final-review rule. A failed initial review consumes its original slot and stops; no final review is available.

## Strict types and digest conventions

Retain ledger schema 1 and exact event envelope `{type,at,data}`. Reject duplicate JSON keys, unknown/missing fields, nonfinite numbers, Boolean counts, numeric coercions and invalid timestamps.

Use existing bounded exact integers, SHA256 format, capsule-reference shape, authority shape and monotone UTC-second timestamps.

`digest(value)` means SHA256 of existing canonical JSON serialization: sorted keys, compact separators, ASCII escaping and nonfinite numbers forbidden.

For proposal text, `proposal_digest = digest(decoded_utf8_text)`. A separate raw SHA256 binds exact UTF-8 bytes. Do not confuse these hashes.

A source descriptor is exactly:

```json
{
  "path": "<fixed repository-relative path>",
  "kind": "json",
  "raw_sha256": "<sha256>",
  "canonical_sha256": "<sha256>"
}
```

For text, `kind` is `"text"` and `canonical_sha256` is `null`. Reject symlinks, path traversal, arbitrary selectors and missing or additional source names.

All new workflow state and status projections remain JSON-serializable. Application graph/checkpoint JSON impact is **none**. Application, financial, provider and database interfaces are **none**.

## Immutable acquisition and noncircular closeout

Use fixed archive root:

`docs/workflow/history/issue-92-recovery-v1/`

Do not change any file under the existing Issue84 archive.

The coordinator must acquire and freeze a source manifest before the independent challenge. Its exact schema is:

```text
{
  schema: "issue92-recovery-sources-v1",
  repo: "beagle1903/agentic-etf-advisor",
  issue: 92,
  capsule: CapsuleRef92,
  original_capsule: CapsuleRef84,
  failed_content: SHA,
  original_manifest_digest: SHA,
  original_grant_digest: SHA,
  sources: FixedSourceMap
}
```

`FixedSourceMap` contains exactly these source names and fixed archive filenames:

| Name | Filename and source |
|---|---|
| `stop_ledger` | `issue92-ledger-at-stop.json`, exact retained six-event ledger |
| `bootstrap_ledger` | `issue92-bootstrap-ledger.json`, original complete two-event bootstrap file |
| `failure_handoff` | `issue92-verification-failure-handoff.md`, complete stopped-attempt handoff |
| `original_reservation` | `issue92-reservation.json`, existing local record |
| `original_dispatch` | `issue92-dispatch-observation.json`, existing local record |
| `capacity_resume` | `issue92-capacity-resume.json`, existing local record |
| `blocked_status` | `issue92-final-blocked-status.json`, existing local record |
| `original_user_approval` | `user-finite-approval.json`, existing local record |
| `recovery_start` | `recovery-design-start.json`, exact current R92D1 local document through its reservation |

Known identities verified by read-only file/hash inspection:

| Source | Canonical digest |
|---|---|
| `stop_ledger` | `290ffe7e16d19de8c7e67df54cbf06c517e6313778a377da20877af9490a967a` |
| `bootstrap_ledger` | `b43fb7a3df8e01e474aa3ebe40ccc0897d13e5dcbdc368ce524600fe75b41c2e` |
| `original_reservation` | `f2170bb189d6d2b8cadf22ae29a34a032df061edb8dda9890840bca42ea90850` |
| `original_dispatch` | `2ac1eb961196c673b009ab8eb7af22d5369d49dd2978bd8da05d409c2cdeacf5` |
| `capacity_resume` | `34cfc7970b9a03de6d0151276d491545efba9350589cdc13fe696b9b96fab8af` |
| `blocked_status` | `8c26c14d1f3f841afed69956fa13ef626c63b2c12813e4b84f3ee69188afd72d` |
| `original_user_approval` | `23f0fa56c9f0979391513cc3db4666a53ea16748de09106f6c9173e2985153e0` |
| `recovery_start` | `2ea019109e52165958be7301c72d31eb470e2c66d0ba4df3411eb8e3efa24eb9` |

The failure handoff’s raw hash is `78230649554f63f858bd78abbaebbdff35a318994bc27be99362de967b5adc50`. The bootstrap file’s raw hash is `1b3bdb6c23c76ad22d2363b863b6b2da8e6d276cade160250d8f5531213d4b71`.

Acquisition reads complete actual files, records both hashes, and compares the original bootstrap value with exactly the first two events of the frozen stop ledger. It never slices the mutable current ledger to obtain a test fixture. The complete current ledger must still equal the stopped six-event document before future bootstrap preparation. Changed source history or unexplained work stops the instance.

The original `remainder_sources` recognition remains mandatory. It validates all complete L84/H/R/S0/D1/C1/E1/D2/C2/E2 and supplemental sources, including the original failed recovery and original grants. The new manifest references their already-pinned manifest/grant identities; it does not substitute reconstructed summaries for those files.

After saving this proposal and recording R92D1’s actual result, reserve the one challenge and create:

```text
{
  schema: "issue92-recovery-challenge-input-v1",
  repo: "beagle1903/agentic-etf-advisor",
  issue: 92,
  capsule: CapsuleRef92,
  original_capsule: CapsuleRef84,
  proposal_digest: SHA,
  source_manifest_digest: SHA,
  supplemental_prefix_digest: SHA,
  supplemental_event_count: positive integer
}
```

The challenged supplemental snapshot must preserve the complete R92D1 start document, its measured result and the challenge’s checked reservation. R92D1 and the challenge are the only new substantive reservations. Interruption/resume/audit observations may preserve the same reservations; no hidden additional phase or authority is permitted.

The challenge returns complete text and a coordinator-transcribed structured result:

```text
{
  schema: "issue92-recovery-challenge-result-v1",
  reservation: "R92C1",
  session: Text,
  role: "code_reviewer",
  model: "gpt-6-sol",
  effort: "high",
  proposal_digest: SHA,
  challenge_input_digest: SHA,
  outcome: "CHALLENGE_PASS" | "CHALLENGE_FAIL",
  evidence: Text
}
```

Require a distinct session from the architect, all historical/current write and verification authors, and prior design/challenge participants excluded by the original Issue92 contract.

The coordinator decision is separately recorded:

```text
{
  schema: "issue92-recovery-coordinator-decision-v1",
  authority: CoordinatorAuthority,
  proposal_digest: SHA,
  challenge_input_digest: SHA,
  challenge_result_digest: SHA,
  outcome: "approved" | "blocked",
  evidence: Text
}
```

Then create the completed closeout:

```text
{
  schema: "issue92-recovery-closeout-v1",
  repo: "beagle1903/agentic-etf-advisor",
  issue: 92,
  capsule: CapsuleRef92,
  original_capsule: CapsuleRef84,
  source_manifest_digest: SHA,
  proposal_digest: SHA,
  challenge_input_digest: SHA,
  sources: FixedCloseoutSourceMap
}
```

`FixedCloseoutSourceMap` has exactly:

- `source_manifest` → `source-manifest.json`
- `proposal` → `design-proposal.md`
- `challenge_input` → `challenge-input.json`
- `challenged_supplemental` → `challenged-supplemental.json`
- `completed_supplemental` → `completed-supplemental.json`
- `challenge_result` → `challenge-result.json`
- `challenge_report` → `challenge-result.md`
- `coordinator_decision` → `coordinator-decision.json`

Each uses the strict descriptor above. The completed supplemental record must retain the challenged prefix exactly, followed only by actual same-reservation observations, challenge completion and coordinator decision. Require structured `CHALLENGE_PASS` and `approved` for future execution.

A later user grant binds this completed closeout. No document contains its own digest. Missing future write authority is expected at this design stage.

## Proposed future finite grant

After successful challenge and coordinator approval, request one explicit finite decision with exactly this schema:

```text
{
  schema: "issue92-single-recovery-grant-v1",
  repo: "beagle1903/agentic-etf-advisor",
  issue: 92,
  authority: UserAuthority,
  authority_anchor: Text,
  at: UTCSeconds,
  capsule: CapsuleRef92,
  original_grant_digest: SHA,
  stop_ledger_digest: SHA,
  failed_content: SHA,
  proposal_digest: SHA,
  closeout_digest: SHA,
  owner: {
    role: "implementation_worker",
    model: "gpt-6-sol",
    effort: "medium",
    session: "/root/issue84_remainder_implementation"
  },
  count_deltas: {
    implementation: 0,
    initial_review: 0,
    remediation: 1,
    final_review: 0,
    design_reset: 0
  },
  supplemental_deltas: {
    verification: 1,
    design: 0,
    challenge: 0,
    design_revision: 0
  },
  review_disposition: "retain-unused-initial-review-after-single-pre-review-repair",
  publication: {
    mode: "retain-original-unused-one-new-pr",
    original_grant_digest: SHA,
    additional_count: 0,
    total_count: 1,
    repo: "beagle1903/agentic-etf-advisor",
    primary_issue: 92,
    head: "codex/issue-92-issue84-remainder",
    base: "main",
    excluded_prs: [85],
    actual_saved_delivery_check_runs: 1
  },
  bootstrap_exception: "append-one-recovery-and-one-remediation-start",
  seconds: 0,
  merging: false,
  reason: Text
}
```

The named identities and quantities are fixed, not implementation choices. The future authority, timestamp and bound completed-document digests are instance values.

Save it as `finite-grant.json`. Pin its canonical digest, the closeout digest, proposal digest and stop digest in the implementation. No command-line option or caller-provided hash may select another instance.

This grant conserves the unused review and PR permissions. It does not add them again. It explicitly authorizes one publication-condition read-only check run against the actual saved delivered state, including a full suite run; that check is not another verification reservation or permission to change content. A failure stops without a rerun.

## Native recovery event and bootstrap reservation

Add only this narrowly recognized event:

```text
{
  type: "issue92_recovery",
  at: UTCSeconds,
  data: {
    version: "issue92-single-recovery-v1",
    authority: UserAuthority,
    authority_anchor: Text,
    capsule: CapsuleRef92,
    prefix_digest: SHA,
    grant_digest: SHA,
    closeout_digest: SHA,
    proposal_digest: SHA,
    reason: Text
  }
}
```

It is admissible only as event 7 of the exact six-event stopped ledger, in the original repository, issue 92, owner-led policy and original capsule generation.

Require:

- All current/archive/source/grant checks described above.
- Event authority and anchor exactly equal the future grant.
- Event timestamp at or after the grant, all closeout phases and existing history.
- No prior recovery event anywhere in this source claim.
- Counts `5/3/4/4/4`, limits `5/4/4/4/4`, local verification starts 1.
- Successful original implementation by the same approved owner.
- No active/suspended phase, local review start, publication target or delivery.
- False verified/accepted/reviewed/delivered flags.
- Exact original failed verification and sole blocker `B92-LIVE-LEDGER-FIXTURE-DRIFT`, with required remediation 5.
- No altered capsule, original grant, predecessor or inherited state.

It increases only remediation limit to 5 and verification limit to 2. It sets pending repair and separately records the approved recovery contract and readiness. It resolves no blocker and certifies no content.

The next substantive event must be ordinary `phase_start` for `remediation`, by the same owner and capsule. It consumes remediation count 5 immediately. No implementation start is added.

Before the new validator exists:

1. Recheck live checkout identity and exact six-event ledger, archive sources and failed content before preparation.
2. Run the current ordinary remediation check; preserve its genuine rejection.
3. Obtain the explicit future grant and prepare the fixed archive package.
4. Under the repository cooperating-writer lock, compare the captured ledger and source bytes again.
5. Atomically save the original six events plus the exact recovery event and exact remediation start, with actual timestamps, and record the matching local reservation before resuming the existing owner.
6. This is the sole pre-validator write exception. It is not reported as native check success.
7. Once support exists, validate the actual saved eight-event ledger and complete source package before successful remediation completion or any dependent phase.

No deletion, changed timestamp, reconstructed reservation or new ledger may repair a bootstrap mismatch. Such a mismatch stops the attempt.

Normal candidate append for this event must also validate the exact prefix and all fixed identities. Replaying the saved bootstrap does not compare current repaired content to the historical failed-content hash; that hash records the pre-repair source. Fresh verification binds the repaired content separately.

## State transitions and native gates

Add narrowly scoped state fields, projected in status:

- `issue92_recovery_ref`: grant/proposal/closeout identities or null.
- `issue92_recovery_stage`: absent, repair_pending, repairing, repaired, verifying, verified, reviewing, reviewed, delivered, or failed.
- `issue92_recovery_failure`: null or the failed phase/event identity.
- `local_verification_limit`: 1 initially, 2 only after the valid event.
- Complete supplemental reservation/outcome references for R92D1/R92C1.
- Explicit conserved-review disposition.

Derive these from events and pinned sources, never caller-controlled status input.

The original D2/C2 readiness and capsule binding remain intact. Recovery readiness additionally requires its own successful independent challenge, coordinator approval and finite grant. Original design approval alone cannot enable recovery.

Permit only this successful progression:

1. Recovery event.
2. One remediation reservation and successful completion.
3. Ordinary `resolve` of the exact blocker, with evidence identifying repaired fixtures, reached intended gates and repair self-check results.
4. One fresh verification reservation and pass on frozen repaired content.
5. Ordinary complete acceptance for all existing ACs on that content.
6. One conserved initial-review reservation and pass on identical content.
7. One original publication target and delivery.

Existing pause/interruption/resume may retain the same phase, owner and reservation without consuming another slot or subtracting unrecorded time. They do not authorize a completed-phase retry.

For the original blocker, reject resolution before successful remediation or below remediation count 5. Removing it from current blockers does not erase the original blocker event or failure. Acceptance/review/delivery remain unavailable until fresh verification passes.

A completed failure in recovery remediation, fresh verification or initial review sets the recovery stage to `failed` and stops every further substantive phase, target allocation and delivery. The start remains consumed. Existing audit/blocker recording is allowed; no automatic second grant is recognized.

The first verification failure remains unchanged and visible. A later successful verification clears the current verification repair requirement through ordinary success semantics; it does not convert the earlier failure to a pass.

All ordinary Issue92 prohibitions remain: extension, continuation, split, successor, design/reset/challenge starts, owner handoff, new implementation and final review. The recovery event cannot repeat.

A new unrelated serious blocker stops under ADR0034. This disposition authorizes repair of the named demonstrated defect and necessary pinned gate support, not arbitrary findings discovered during review.

## Authority, authors and source claims

Keep normalized authority evidence and anchors using Unicode NFKC, collapsed whitespace and case folding. Compare identities independently of display names.

Derive consumed identities from all existing L84/H/R/supplemental sources, the original Issue92 grant/capsule and original local authority records, plus R92D1/R92C1 authority. The future repair grant must be distinct from all of them.

Treat references to the same future grant in its event, archive and reservation as aliases of one grant. They cannot authorize another action. Register the recovery action in full-lineage validation and candidate append, and reject reuse in either temporal order.

Keep the existing unique Issue84 source claim at Issue92. The recovery adds no source claim and no successor. A recovery marker in another ticket or duplicate Issue92 representation rejects.

Review exclusions retain every historical/current implementation, remediation and verification author, original D2/C2 participants, and the new recovery architect/challenger. Normalize session identities for exclusion comparisons while preserving original display strings. The same owner cannot obtain review eligibility by changing case, whitespace or Unicode presentation.

No old content or PR binding becomes current certification.

## Fixture repair and focused acceptance

Create immutable fixture files from archived sources:

- Original two-event Issue92 bootstrap: exact canonical digest `b43fb7a3df8e01e474aa3ebe40ccc0897d13e5dcbdc368ce524600fe75b41c2e`.
- Exact stopped six-event ledger: digest `290ffe7e16d19de8c7e67df54cbf06c517e6313778a377da20877af9490a967a`.

Load a fresh deep copy for each test. Fixture construction must never depend on `read_all(real_root)[92]`, current live phase, runtime ledger tail or wall-clock date.

Original-grant tests use the two-event fixture and preserve original rejection expectations, including its single verification limit. Recovery tests use the six-event fixture plus explicit candidate recovery events. They must not retroactively reinterpret the original grant.

Use fixed evaluation times after each fixture’s events, or deterministic monotone offsets from its frozen last timestamp. Do not derive synthetic timestamps from the live ledger.

For append tests, build a temporary repository with complete required archives and compute that repository’s actual content when content-bound events are needed. Do not copy live verification content into a different repository.

Mandatory coverage under existing AC84VERIFY/I84GATES:

- The original bootstrap positive control asserts active implementation from the immutable two-event fixture.
- Historical exclusions reject the intended reviewer after a positive independent-review control reaches that same gate.
- Publication positives reach target/delivery/`check_pr`; missing target, PR85, another PR, another content, wrong primary marker, branch or base fail precisely at those gates.
- Every archive/grant race case first succeeds without the injected mutation, then proves the mutation hook executed, the intended append rejection occurred and the original ledger bytes were not replaced.
- Live-ledger progression through verification, review and delivery does not change fixture inputs or synthetic outcomes.
- Exact six-event failure remains replayable without a recovery grant and remains blocked.
- Missing/mutated grant, proposal, challenge, closeout, source, authority or original prefix rejects.
- Failed challenge, absent coordinator approval, wrong capsule/generation, changed owner, extra keys, Boolean counts and changed deltas reject.
- Recovery adds remediation limit 1 and verification limit 1 only; all prior counts and failure records remain exact.
- Repair start consumes remediation count 5; second repair or third local verification rejects.
- Resolve before repair, verification before resolution, initial review before fresh verification/acceptance, reused reviewer and changed content reject.
- The explicitly conserved initial review succeeds after the exact single pre-review repair. Ordinary other histories still require final review after remediation.
- Failed repair/verification/review denies delivery and another phase; interrupted exact-reservation resume adds no count.
- Approval evidence/anchor reuse and normalized session aliasing reject.
- Source claim duplication, ordinary extension/continuation and alternate-target recovery reject.
- Race tests cover actual new recovery grant/closeout/source bytes, event-source bytes, ledger membership, candidate temp and content changes. Existing race protections remain active.
- Existing Issue23/83, sibling conservation and whole-lineage authority tests continue unchanged in meaning.

A separate actual-current-ledger check reads the real saved Issue92 ledger and verifies its exact original prefix, native state and current content binding. It must report the actual stage; it must not assume implementation remains active or use a manufactured delivered fixture as evidence for actual delivery.

All existing required local/static/offline evaluation/build/Compose gates remain required.

## Publication and actual saved-state checks

The original unused one-new-PR authority is retained only after the recovery’s native verification, complete acceptance and independent initial review pass.

Use the existing repository, branch `codex/issue-92-issue84-remainder`, base `main`, primary issue 92 and one new PR other than 85. Allocate it only after clean review. The `publication_target` retains the original grant digest because that grant supplies the one PR allowance; the recovery grant explicitly conserves that same allowance.

For a recovered Issue92, `publication_target` additionally requires native delivery prerequisites to be satisfied: no pending repair, blocker, failure, active/suspended phase or missing/current-content mismatch. It must not allocate a target merely because some earlier review flag is true.

`check_pr` also requires the PR creation time to follow the recovery grant, the exact recorded publication target, actual head/base metadata and repaired content. This is additional validation of the conserved new-PR allowance, not permission to reuse an existing PR.

Required sequence:

1. Finish all repair source/tests/docs/archive files.
2. Freeze content and complete the one fresh verification.
3. Record complete acceptance and finish the independent initial review on that content.
4. Commit/push certified content and allocate the single draft PR.
5. Preserve any expected pre-delivery CI failure.
6. Record the one target and ordinary delivery through native gates.
7. Run the one authorized actual-saved-delivery check sequence from that saved repository state: full offline suite, native/static workflow validation, merge-base prefix validation, exact current PR/head/base/content checks and preserved archive hashes.
8. Record results in local/linked external evidence without changing certified content.
9. Publish the delivered-ledger commit, confirm identical canonical source content and passing exact-head CI before claiming readiness.

The post-delivery check is an explicitly authorized publication condition. It creates no second verification certificate and cannot repair or recertify changed source. If it fails, preserve the saved delivery event as recorded history, report publication blocked, do not claim successful delivery or merge readiness, and stop without retry. No terminal-ledger rewrite is authorized.

Do not add content-digest exclusions. Recovery archives, manifests, grant, fixtures and documents participate in normal certification. Only existing current-ticket/lock/temp exclusions apply.

## Atomicity and interfaces

Changes affect only workflow replay/status/gates, fixed-source acquisition, full-lineage identity auditing, atomic append, fixture construction and current-PR checks.

Keep repository-level cooperating-writer locking. Within append, capture and recheck real event input, all ledger names/bytes, complete relevant archive/manifest/grant files, candidate temp bytes and current content immediately before replacement. New recovery sources are ordinary repository content, never live external-journal dependencies.

Raw archive bytes must survive Git roundtrip. Extend existing exact-byte archive handling only as needed for the new fixed directory. Do not normalize or rewrite old archives.

Recorded evidence cannot authenticate human authority or lock arbitrary external editors. The coordinator must preserve truthful reservations and use a quiescent workspace for certification/publication.

## Documentation, risks and stop conditions

Add a new ADR for this single Issue92 recovery, preserving accepted ADR0035 and earlier history. Document the explicit retained-initial-review rule, counted remediation, second verification limit and pre-validator exception. Update Iteration020 and only workflow instructions/static markers directly affected by this exception.

The original capsule remains frozen; its no-retry wording remains historical. The new ADR and finite grant explain exactly which execution prohibition is supplemented and why no other allowance changes.

Primary risks are treating local repair as uncounted work, silently converting review classification, fixture dependence on live state, circular approval digests, omitted failed outcomes, normalized authority/session aliases, and publication against synthetic state. The fixed sources, explicit deltas, narrow event position, exact stage gates and actual saved-state checks address those risks.

A completed failure, source mismatch, unresolved consequential ambiguity, unavailable existing owner, unexpected prior work or exhausted allowance returns `BLOCKED_FOR_DECISION`. There is no replacement session, automatic amendment, new issue or second challenge under this disposition.

The next permitted phase is the already-authorized single independent R92C1 challenge of this complete saved proposal and its exact input manifest. After a pass and coordinator approval, present the instantiated finite repair grant to the user. No repair is authorized by this handoff.

No repository files were edited and no tests were run. Inspection included complete-file hash checks of the archived source set and confirmation that the current six-event ledger equals the frozen stop document.

DESIGN_READY
