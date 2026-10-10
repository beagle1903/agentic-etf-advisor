R92PD1 is technically ready for the single independent challenge. Issue 92 remains `BLOCKED_FOR_DECISION`; this proposal grants no implementation, verification, review or publication.

**Identity, authority and scope**

Architect: `/root/issue92_pr_identity_design`, `design_architect / gpt-6-astra / high`, read-only. Reservation R92PD1 was recorded at `2026-10-09T17:24:47Z`. The native design-reset rejection remains a rejection. The [coordinator’s issue record](https://github.com/beagle1903/agentic-etf-advisor/issues/92#issuecomment-6085859455) authorizes only this proposal and one subsequent independent challenge.

The consequential change is a narrowly pinned disposition after the failed initial review, together with repair of `B92-LIVE-PR-HEAD-IDENTITY`. The future implementation owner remains:

```json
{
  "role": "implementation_worker",
  "model": "gpt-6-sol",
  "effort": "medium",
  "session": "/root/issue84_remainder_implementation"
}
```

Permitted prospective work:

1. Enforce actual queued/live PR head identity and Issue 92’s granted head repository and branch.
2. Add precise negative coverage and immutable, replay-safe fixtures.
3. Implement the exact finite post-review disposition below.
4. Preserve and validate its complete evidence package.
5. Update only directly affected workflow documentation, static checks and a new ADR.
6. Complete fresh certification and the original unused publication sequence, contingent on later explicit finite authority.

Non-goals: product/authentication work; actual Issue23/83 introduction, transition or resume; finance/provider/database/application-state changes; generic recovery or retries; a new issue or successor; another implementation pass; owner replacement; role/configuration/CI-privilege changes; accepted-history rewrites; additional PRs; merging.

**Frozen definitions and pins**

Keep the complete Issue92 capsule, generation and definitions unchanged:

- Capsule: `issue-92-issue84-remainder`, generation `1`.
- Digest: `197879ccd445194f77287455919e1f15efb5dce4366c5283a000ab6405dbeace`.
- Original Issue84 capsule: `issue-84-cycle-bounded-workflow`, generation `3`, digest `df870f205cc3a8053c152699ce16030a1cedc518fdda0588ae16d3cbcd95fda9`.
- Original Issue92 grant: `76f78ac061f9e2c69b6a3aba6e4e89f4b7875321facce3e79b3c6dbdc1f53c2d`.
- Original closeout: `a161bebe339b8c8ad97fc934896089a501d3f6756ff3102843d539c702ec6eb8`.
- First recovery grant: `ecba220c1e266721d5e199a8d8c5b3e0d0ae7722a2b430b182d6b4019fa369b0`.
- First recovery closeout: `cceaadefea56843630f0156d83f7c13a0a7172c7a6fa44858d85be21ef2b7d48`.
- Exact sixteen-event stop: canonical `61532d8802dc4a19a0b2b15d5bbbb35fa5b163ebdaa92ee15fdf860789154f2e`; raw `910929a9a2d3b51bd4261d7173ff3d97cd91e253870db8f4cc24add0047094a8`.
- Failed-review content: `6f985a3dd80b75e430422b3ab9c86a0793e88345af135970bbb63776bce89c87`.
- Review report raw SHA256: `3c99f27005ee1c9ef3d918d3a1d5ab9f3e08120bad6dfa4ef788f14707d0373d`.

The current ledger’s complete bytes equal the supplied sixteen-event snapshot. Read-only hash inspection also confirmed all sources described by the existing Issue84 and recovery manifests.

The unchanged scope definition is:

> S84: Replace completion/elapsed-time exhaustion with finite review/design-reset/reimplementation cycle caps; update workflow engine, tests, templates, instructions and docs; backwards-compatible append-only historical migration and split attempt conservation.

The unchanged invariants are:

| ID | Exact definition |
|---|---|
| I84CYCLES | Default one implementation/initial-review/remediation/final-review/design-reset lifetime attempt persists across agents/sessions/quota resets/design resets. Extra attempts require explicit named user authorization. |
| I84TIME | Completion time/quota waits/open-phase elapsed time never gate new cycle-only work or require minute extensions. Timing may remain historical/audit data. |
| I84HISTORY | Existing ledger prefixes/capsules/counters/content/PR bindings remain immutable and validated; explicit policy transition cannot clear attempts, review outcomes or substantive blockers. |
| I84GATES | Consequential design/challenge/approval, role ownership, review independence, content-bound acceptance/verification/review and clean delivery remain enforced. |
| I84SPLIT | Successor/sibling allocation conserves remaining attempt allowances and inherits consumed history; split/new issue cannot silently replenish attempts. |
| I84ISOLATE | Only development-governance engine/docs/tests change; current Issue83 product work preserved. |

The unchanged acceptance definitions are:

| ID | Exact definition |
|---|---|
| AC84TIME | New cycle-only ledgers and explicitly transitioned expired/suspended legacy ledgers can resume after arbitrary waits without timing extensions; status explains remaining attempts rather than misleading minute debt. |
| AC84CYCLES | Counted phase limits/failed-final-review stop still enforce across resets/handoffs/quota waits; explicit count extension cannot be replayed or impersonated. |
| AC84HISTORY | Historical delivered/split/bootstrap ledgers replay without rewriting; transitions preserve prefix/capsule/counts/bindings and deny clearing substantive blockers or converting delivered tickets. |
| AC84SPLIT | Split successors/siblings inherit consumed counts and validated allocated remaining allowances, cannot multiply attempts or reuse allocations; terminal predecessors remain retired. |
| AC84GATES | Existing ownership/design/challenge/approval/content-bound acceptance/review/verification/PR gates and unrelated static workflow checks remain correct. |
| AC84DOCS | AGENTS/CONTRIBUTING/README/templates/role bodies explain cycle-only policy; new ADR supersedes timing only; finite-workflow history remains untouched. |
| AC84VERIFY | Focused engine/CLI/negative fixtures plus required offline/static/evaluation/build/Compose gates pass; independent review required; no services/product behavior changes. |

This proposal and its eventual digest impose an additional narrow execution bound; S84 does not authorize unrelated changes.

**Observed execution path and demonstrated failure**

The relevant path is in [scripts/ticket_workflow.py](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:2952):

1. `main`, CI branch, reads the queued event and fetches live PR metadata.
2. `current_pr` at line 2833 compares the PR number, head SHA, base SHA/ref/repository.
3. It returns the queued PR object with only the live body substituted.
4. `main` uses the returned base SHA for `check_prefix` and head SHA for `content_digest`.
5. `check_pr` at line 2779 evaluates the primary issue, ledger, repository, Issue92 branch/base restrictions and recorded delivery binding.

The failure is concrete: equal head SHA does not imply equal head branch or repository. The live metadata can identify another branch or fork while `check_pr` sees the queued approved head. Separately, equal queued/live fork metadata can pass the current Issue92 branch predicate because it never checks the head repository.

The focused [publication test](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/tests/test_ticket_workflow.py:1750) supplies only head/base refs; its negatives mutate queued refs. Existing [live-metadata tests](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/tests/test_ticket_workflow.py:2694) cover SHA and base changes, but omit head ref/repository disagreement.

This is a demonstrated `I84GATES / AC84GATES` failure and an `AC84VERIFY` coverage gap. The earlier verification pass remains historical evidence; it does not override the failed review.

**PR identity contract**

Keep live acquisition behind the existing replaceable HTTP boundary. `current_pr` remains a deterministic validator over supplied queued/live objects; tests inject metadata without network access.

Before comparing identity, validate all consumed structural fields. Missing, null, malformed or incorrectly typed identity fields must raise `Invalid`; never substitute queued values for missing live values.

Required fields:

- Queued event: object, positive exact-integer `number`, object `repository` with nonempty `full_name`, object `pull_request`.
- Queued and live PR: valid UTC `created_at`; object `head`; object `base`.
- Live PR: positive exact-integer `number`.
- Each head/base: nonempty string `sha`, nonempty string `ref`, object `repo`, nonempty string `repo.full_name`.
- Git object IDs: complete lowercase hexadecimal object IDs, 40 or 64 characters; no abbreviations, whitespace or coercion.
- Repository full names: exactly two nonempty slash-separated components, without whitespace/control characters.
- Refs: nonempty exact strings without whitespace/control characters. Do not trim or case-fold identity comparisons.
- Body: string or null; null becomes the existing empty-body interpretation. Missing live body may follow that same interpretation, so the primary-issue gate fails where required.
- If queued embedded PR `number` exists, require it to match the event number.

External GitHub objects may contain additional fields; do not apply the workflow ledger’s exact-key schema to the entire external API response.

`current_pr` must require:

```text
live.number == event.number
queued.head.(sha, ref, repo.full_name) == live.head.(sha, ref, repo.full_name)
queued.base.(sha, ref, repo.full_name) == live.base.(sha, ref, repo.full_name)
queued.created_at == live.created_at
queued.base.repo.full_name == live.base.repo.full_name == event.repository.full_name
```

Use the validated live PR fields in the returned event, including head, base, creation time and body. Preserve the queued event envelope. Both inputs remain unmodified. A mismatch produces a precise head/base/PR-identity rejection before content certification.

This universal queued/live comparison does not forbid ordinary fork PRs: a matching live/queued fork head remains eligible for ordinary tickets under their existing contracts.

For Issue92, `check_pr` independently requires:

```text
head.repo.full_name == "beagle1903/agentic-etf-advisor"
head.ref == "codex/issue-92-issue84-remainder"
base.repo.full_name == event.repository.full_name == ledger.repo
base.ref == "main"
PR number == recorded publication_target.pr
PR number != 85
created_at > latest valid Issue92 disposition grant timestamp
```

Keep all existing primary-issue, changed-ledger, historical-exemption, merge-base, creation-time, target, delivered-state and content-binding rules. For the new disposition, the latest required creation threshold includes event 17’s grant; the original and first-recovery thresholds remain satisfied.

`main` must continue to bind:

- `--base` to the validated live base SHA;
- prefix validation to that base SHA;
- repository content to the validated live head SHA;
- delivery to the actual saved ledger and actual PR identity.

There is no queued fallback following failed or unavailable live acquisition. This check describes one observed live snapshot; it does not claim to lock GitHub against subsequent changes.

**Finite accounting**

The first recovery is over and remains failed. Its initial review was consumed.

| Resource | Current | Proposed limit change | Result after new start |
|---|---:|---:|---:|
| Implementation | 5/5 | 0 | 5/5 |
| Initial review | 4/4 | 0 | 4/4 |
| Remediation | 5/5 | +1 | 6/6 |
| Final review | 4/4 | +1 | 5/5 |
| Design reset | 4/4 | 0 | 4/4 |
| Local verification | 2/2 | +1 | 3/3 |
| Original new PR | 1 unused | 0 | One original allowance |
| Original actual-saved-delivery check sequence | 1 unused | 0 | One original sequence |

Historical inherited counts remain `4/3/4/4/4`. Counts increase only at ordinary phase starts. This is another counted remediation followed by **final review**, with no reclassification of the failed initial review.

R92PD1 and R92PC1 are supplemental read-only preparation reservations. They add no native design-reset or code-review allowance.

**Immutable source acquisition**

Use the new fixed root:

```text
docs/workflow/history/issue-92-pr-identity-repair-v1/
```

The coordinator freezes complete local snapshots before challenge. Copying this package into the repository requires the later finite write approval. Existing Issue84 and first-recovery archives remain unchanged.

A descriptor has exactly:

```text
{
  path: FixedRepositoryRelativePath,
  kind: "json" | "text",
  raw_sha256: SHA256,
  canonical_sha256: SHA256 | null
}
```

JSON descriptors require the canonical digest; text descriptors require null. Preserve complete bytes, including empty logs. Reject missing/additional source names, changed selectors, symlinks, traversal, malformed JSON, duplicate keys and nonfinite numbers.

The new source manifest has exactly:

```text
{
  schema: "issue92-pr-identity-sources-v1",
  repo: "beagle1903/agentic-etf-advisor",
  issue: 92,
  capsule: CapsuleRef92,
  original_capsule: CapsuleRef84,
  failed_content: FailedReviewContent,
  stop_ledger_digest: Stop16Digest,
  original_manifest_digest: OriginalCloseoutDigest,
  original_grant_digest: OriginalGrantDigest,
  prior_recovery_manifest_digest: FirstRecoverySourceManifestDigest,
  prior_recovery_closeout_digest: FirstRecoveryCloseoutDigest,
  prior_recovery_grant_digest: FirstRecoveryGrantDigest,
  sources: FixedSourceMap
}
```

The first-recovery source-manifest digest is `6451c9e60e8782a88b7b5135d4acf83c46f7993dc7e143725ca15032b531d374`.

The fixed source map includes these complete files, copied under the new root using the listed filenames:

| Source name | Filename |
|---|---|
| `stop_ledger` | `issue92-ledger-at-review-stop.json` |
| `review_report` | `independent-review-report.md` |
| `review_closeout` | `failed-review-closeout.json` |
| `review_reservation` | `initial-review-reservation.json` |
| `review_start` | `initial-review-start.json` |
| `review_end` | `initial-review-end-fail.json` |
| `review_startup` | `review-startup-observation.json` |
| `blocked_status` | `final-blocked-status.json` |
| `prior_bootstrap` | `eight-event-bootstrap-ledger.json` |
| `prior_remediation_reservation` | `remediation-reservation.json` |
| `prior_remediation_end` | `remediation-end-pass.json` |
| `prior_blocker_resolution` | `blocker-resolution.json` |
| `prior_verification_reservation` | `fresh-verification-reservation.json` |
| `prior_verification_start` | `fresh-verification-start.json` |
| `prior_verification_end` | `fresh-verification-end-pass.json` |
| `prior_acceptance` | `complete-acceptance.json` |
| `preparation_start` | `pr-identity-design-start.json` |

The first sixteen entries originate from the coordinator’s retained Issue92 recovery records, except the stop snapshot originates from the new preparation directory. `preparation_start` is the complete current authorization-and-phases document through R92PD1’s reservation.

Also include exactly these 26 entries under `verification/`, with source-map keys equal to `verification/<filename>`:

```text
after-integrity.txt
after-status.json
before-archive-roundtrip.txt
before-status.json
compose-config.log
compose-config.result.txt
diff-check.log
diff-check.result.txt
explanations-eval.log
explanations-eval.result.txt
mypy.log
mypy.result.txt
native-validator.log
native-validator.result.txt
pytest-full.log
pytest-full.result.txt
retrieval-eval.log
retrieval-eval.result.txt
ruff-check.log
ruff-check.result.txt
ruff-format.log
ruff-format.result.txt
static-validator.log
static-validator.result.txt
uv-build.log
uv-build.result.txt
```

Acquire complete actual files, not summaries. The manifest therefore has exactly 43 source entries.

Validate their relationships:

- Stop ledger contains exactly sixteen events and both fixed hashes.
- Complete current ledger equals the stop document before bootstrap preparation.
- Archived original two-event, six-event and eight-event documents agree with their corresponding stop prefixes.
- Standalone remediation, resolution, verification, acceptance and review events equal the corresponding sixteen-event entries.
- Reservations identify the same owner/reviewer, timestamps, capsule, content, counts and limits.
- Failed review closeout agrees with the report hash, failed outcome, review reservation, startup accounting and blocked state.
- Earlier full-suite results remain a pass on the failed-review content; they are never treated as a new verification.
- Preparation source retains its genuine failed native gate and read-only limits.
- Existing `remainder_sources` and `recovery_sources` validation remains mandatory for the complete original 36-file archive set. Preserve the separately retained original capsule too.

Duplicated representations identify the same reservation; count each reservation once. Unexpected extra work or source changes stop acquisition.

**Noncircular proposal, challenge and approval**

Use existing canonical JSON hashing: sorted keys, compact separators, ASCII escaping, no nonfinite values. For text, `proposal_digest = digest(decoded_utf8_text)`; also retain its distinct raw-byte hash.

Freeze in this order:

1. Complete source snapshots and `source-manifest.json`.
2. Exact `design-proposal.md`.
3. R92PD1 completion and R92PC1 reservation in the local supplemental record.
4. `challenged-supplemental.json`, containing that complete three-event prefix.
5. `challenge-input.json`.
6. Independent structured challenge result and full report.
7. Coordinator decision.
8. Completed supplemental snapshot and closeout.
9. A later, distinct explicit finite user grant.

The challenge input has exactly:

```text
{
  schema: "issue92-pr-identity-challenge-input-v1",
  repo: Repo,
  issue: 92,
  capsule: CapsuleRef92,
  original_capsule: CapsuleRef84,
  proposal_digest: SHA256,
  source_manifest_digest: SHA256,
  supplemental_prefix_digest: SHA256,
  supplemental_event_count: 3
}
```

R92PC1 uses a distinct read-only `code_reviewer / gpt-6-sol / high` session. The coordinator records its exact session before dispatch. It must differ from R92PD1 and all excluded historical/current writers, verifiers and design/challenge participants.

The result has exactly:

```text
{
  schema: "issue92-pr-identity-challenge-result-v1",
  reservation: "R92PC1",
  session: Text,
  role: "code_reviewer",
  model: "gpt-6-sol",
  effort: "high",
  proposal_digest: SHA256,
  challenge_input_digest: SHA256,
  outcome: "CHALLENGE_PASS" | "CHALLENGE_FAIL",
  evidence: Text
}
```

The coordinator decision has exactly:

```text
{
  schema: "issue92-pr-identity-coordinator-decision-v1",
  authority: CoordinatorAuthority,
  proposal_digest: SHA256,
  challenge_input_digest: SHA256,
  challenge_result_digest: SHA256,
  outcome: "approved" | "blocked",
  evidence: Text
}
```

The completed supplemental record preserves the challenged document’s top-level fields and exact first three events, followed by challenge completion and coordinator decision. Actual timing observations, if necessary, are retained explicitly and frozen before closeout; they cannot add another reservation or alter the challenged prefix.

The closeout has exactly:

```text
{
  schema: "issue92-pr-identity-closeout-v1",
  repo: Repo,
  issue: 92,
  capsule: CapsuleRef92,
  original_capsule: CapsuleRef84,
  source_manifest_digest: SHA256,
  proposal_digest: SHA256,
  challenge_input_digest: SHA256,
  sources: FixedCloseoutMap
}
```

`FixedCloseoutMap` has exactly eight descriptor entries:

```text
source_manifest          -> source-manifest.json
proposal                 -> design-proposal.md
challenge_input          -> challenge-input.json
challenged_supplemental   -> challenged-supplemental.json
completed_supplemental    -> completed-supplemental.json
challenge_result         -> challenge-result.json
challenge_report         -> challenge-result.md
coordinator_decision     -> coordinator-decision.json
```

Require matching proposal/input digests, independent sessions, monotone actual timestamps, `DESIGN_READY`, `CHALLENGE_PASS` and `approved`. No document contains its own digest or the digest of a document that depends on it.

A failed challenge stops this preparation. It authorizes no automatic amendment, second challenge or replacement.

**Prospective finite grant**

After the challenge passes and coordinator approval is recorded, request one explicit finite decision with exactly this schema:

```text
{
  schema: "issue92-pr-identity-repair-grant-v1",
  repo: "beagle1903/agentic-etf-advisor",
  issue: 92,
  authority: UserAuthority,
  authority_anchor: Text,
  at: UTCSeconds,
  capsule: CapsuleRef92,
  original_grant_digest: OriginalGrantDigest,
  prior_recovery_grant_digest: FirstRecoveryGrantDigest,
  stop_ledger_digest: Stop16Digest,
  failed_content: FailedReviewContent,
  source_manifest_digest: SHA256,
  proposal_digest: SHA256,
  closeout_digest: SHA256,
  owner: ExactOriginalOwner,
  count_deltas: {
    implementation: 0,
    initial_review: 0,
    remediation: 1,
    final_review: 1,
    design_reset: 0
  },
  supplemental_deltas: {
    verification: 1,
    design: 0,
    challenge: 0,
    design_revision: 0
  },
  review_disposition: "one-final-review-after-failed-initial-review-and-counted-repair",
  publication: {
    mode: "retain-original-unused-one-new-pr",
    original_grant_digest: OriginalGrantDigest,
    prior_recovery_grant_digest: FirstRecoveryGrantDigest,
    additional_count: 0,
    total_count: 1,
    repo: "beagle1903/agentic-etf-advisor",
    primary_issue: 92,
    head: "codex/issue-92-issue84-remainder",
    base: "main",
    excluded_prs: [85],
    actual_saved_delivery_check_runs: 1,
    additional_actual_saved_delivery_check_runs: 0
  },
  bootstrap_exception: "append-one-pr-identity-disposition-and-one-remediation-start",
  seconds: 0,
  merging: false,
  reason: Text
}
```

Exact integer validation excludes Booleans and coercion. Unknown/missing keys reject. The future authority, timestamp and completed-document digests are instance values. All quantities, owner, identifiers and dispositions above are fixed.

Save as `finite-grant.json`. The implementation pins its canonical digest and the source-manifest, closeout, proposal and stop digests as constants. No caller-selectable import or retry interface is introduced.

The grant explicitly supplements the first recovery’s stop rule only for this exact failed-review state. It does not rewrite that earlier grant.

**Event 17 and bootstrap**

Introduce one narrowly recognized event:

```text
{
  type: "issue92_pr_identity_repair",
  at: UTCSeconds,
  data: {
    version: "issue92-pr-identity-repair-v1",
    authority: UserAuthority,
    authority_anchor: Text,
    capsule: CapsuleRef92,
    prefix_digest: Stop16Digest,
    grant_digest: SHA256,
    source_manifest_digest: SHA256,
    closeout_digest: SHA256,
    proposal_digest: SHA256,
    reason: Text
  }
}
```

It is admissible only as event 17, after the exact complete sixteen-event prefix, under the original Issue92 repository, policy, owner and capsule. Require:

- Complete pinned source/grant/closeout validation.
- Event authority and anchor exactly equal the new grant.
- Event time at or after the grant and completed preparation.
- Counts and limits exactly `5/4/5/4/4`.
- Local verification starts/limit exactly `2/2`.
- `initial_failed=true`, `final_failed=false`.
- Successful original implementation by the exact existing owner.
- Existing first-recovery stage `failed`, failure `initial_review`.
- Verified and accepted historical content equal the fixed failed-review content.
- Reviewed/delivered false, no publication target or delivery history.
- No active/suspended phase.
- Exactly the current blocker `B92-LIVE-PR-HEAD-IDENTITY`, requiring remediation count 6.
- No prior new disposition, altered source claim, owner or inherited state.

The event increases only remediation limit to 6, final-review limit to 5 and local-verification limit to 3. It clears current verification/acceptance/review certification and content references; marks repair pending; sets current remediation readiness false. It resolves no blocker.

Retain `initial_failed=true` and the old recovery’s `failed/initial_review` fields as historical state. Add a separate current disposition instead of overwriting the first recovery as successful.

The next event must be ordinary remediation `phase_start`, event 18, with the exact existing owner/role/capsule. It consumes remediation count 6 immediately.

The existing engine cannot accept this pair. The later user grant must therefore expressly authorize the following bootstrap:

1. Confirm exact branch, base commit, current failed content, full sixteen-event ledger and retained sources before changing the repository.
2. Run and retain the current ordinary remediation gate’s genuine rejection.
3. After finite approval, acquire/copy the approved archive package, preserving raw bytes.
4. Under the repository cooperating-writer lock, recheck all captured source/ledger bytes and membership.
5. Atomically save the original sixteen events plus events 17 and 18 with actual timestamps; record the matching local reservation before resuming the existing owner.
6. Record the pre-package failed-content identity and the actual prepared-content identity separately. Archive addition must not be misrepresented as unchanged source content.
7. Once the new validator exists, validate the **actual saved eighteen-event ledger**, complete archive package and counted reservation before successful remediation completion or any dependent phase.

This is the only pre-validator exception. No native pass is invented. Bootstrap mismatch stops; deleting starts, rewriting prefixes or creating a replacement ledger is forbidden.

Replay after repair must not require current source content to equal the historical failed-content digest. Fresh certification binds the repaired content separately.

**Replay, gates and status**

Affected implementation points are [State.gate](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:1241), [replay](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:1385), [completed](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:2333), [lineage_audit](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:2388), and [append](C:/Users/burha/.codex/worktrees/issue84-design-correction/agents-lab/scripts/ticket_workflow.py:2607).

Add separately derived fields:

```text
issue92_pr_identity_ref: null | {grant_digest, proposal_digest, closeout_digest}
issue92_pr_identity_stage:
  absent | repair_pending | repairing | repaired |
  verifying | verified | reviewing | reviewed | delivered | failed
issue92_pr_identity_failure: null | {phase, event_index}
issue92_pr_identity_supplemental: JSON reservation/outcome records
```

Status exposes both the prior failed recovery and current disposition, counts/limits, remaining allowances, current certification and blocker state. Use only JSON-serializable projections.

The exact event-17 handler is the sole exception to the prior failed-recovery substantive-event stop. An absent, invalid or repeated event leaves that stop effective.

After a valid event 17:

- Permit only the new current disposition’s exact progression.
- Preserve the old recovery fields unchanged; its phase-completion and resolve rules must not process later phases.
- The new `failed` stage stops every subsequent substantive phase, target and delivery.
- `initial_review` always remains unavailable.
- Final review becomes available only under this exact validated disposition and its granted remaining count.
- All unrelated tickets and pre-event-17 histories retain their prior behavior.

Required progression:

```text
17 disposition
18 counted remediation start
   successful remediation end
   resolve B92-LIVE-PR-HEAD-IDENTITY
   fresh verification start/pass
   complete acceptance
   fresh independent final_review start/pass
   original publication_target
   ordinary delivery
```

Resolution requires successful new remediation at count 6, its evidence, no active/suspended phase, and the exact named blocker. The successful remediation at count 5 cannot resolve the new blocker.

Verification requires resolved repair, no blocker and one remaining local verification allowance. Acceptance requires all seven frozen ACs and identical freshly verified content. Final-review start requires the new successful remediation, fresh verification and acceptance on identical content; the old verification/acceptance cannot qualify.

Any completed remediation, verification or final-review failure sets the new stage to `failed` and retains the consumed start. Existing truthful audit/blocker recording remains possible. No completed-phase retry exists.

Existing pause/interruption/resume retains the same owner/session/reservation and count. It neither reopens a completed failure nor replenishes an allowance.

**Authority, independence and atomicity**

Preserve normalized authority evidence and anchors using Unicode NFKC, collapsed whitespace and case-folding, independently of display name.

The new finite authority must be distinct from every consumed identity in:

- Original Issue84/native/H/R/supplemental histories.
- Original Issue92 capsule/grant and source records.
- First recovery preparation, grant, event and reservations.
- Current read-only preparation authority and completed closeout.

References to the same new grant across archive/event/reservation are aliases of one action. They cannot authorize another extension or disposition. Register the new action in whole-lineage validation; reject evidence/anchor reuse in either order, including cross-field reuse.

Keep the unique Issue84 source claim at Issue92. No second claim, alternate ticket marker or duplicate disposition is accepted.

Review exclusions retain all historical/current implementation, remediation and verification authors, all previously excluded architects/challengers, and R92PD1/R92PC1. The future final review uses a fresh independent read-only session. Normalized aliases cannot bypass exclusions.

Retain the repository writer lock and final rereads of real event source, all ledger names/bytes, all archive/manifest/grant bytes, candidate temporary bytes and repository content before replacement. New source files participate in the existing content and raw-byte race checks.

Add no content exclusions. Extend exact-byte Git handling only for the new archive root. Existing archives remain byte-identical.

**Focused acceptance and tests**

Use immutable archived two-, six- and sixteen-event baselines, fresh copies and deterministic timestamps. Do not derive test fixtures from the mutable live Issue92 ledger. Temporary-repository tests compute their own real content digest.

Required precise scenarios:

| Frozen IDs | Required positive and negative controls |
|---|---|
| I84GATES / AC84GATES | Matching full queued/live identity passes and returns live metadata without mutating either input. Live body updates still reach primary-issue validation. |
| I84GATES / AC84VERIFY | Same SHA but changed live head ref rejects. Same SHA/ref but changed live head repository rejects. Both changed rejects. |
| I84GATES / AC84GATES | Matching queued/live fork metadata passes generic identity consistency, then fails Issue92’s independent granted-head-repository check. Matching wrong branch similarly fails Issue92. |
| I84GATES / AC84VERIFY | Missing/null/wrong-type head, base, repo, full_name, ref, SHA, number or creation time fails closed. Boolean number and abbreviated/malformed SHA reject. Extra unrelated GitHub fields remain accepted. |
| I84GATES / AC84GATES | Existing PR-number, base SHA/ref/repository, CLI-base, current-body, primary-issue, creation-time, target, delivered-state and content negatives retain intended rejection paths. |
| I84HISTORY / AC84HISTORY | Original two/six-event fixtures and first-recovery behavior remain valid without requiring the new package. Exact sixteen-event stop remains failed without event 17. |
| I84CYCLES / AC84CYCLES | Event 17 adds only the specified limits; event 18 consumes remediation 6. Initial review, new implementation, fourth verification, second new remediation/final review and ordinary extension/continuation/split reject. |
| I84GATES / AC84HISTORY | Altered/truncated/extended prefix; wrong position, capsule, owner, source, grant, challenge, decision or timestamp; missing/additional keys; changed deltas; Boolean counts; duplicate marker all reject. |
| I84GATES / AC84GATES | Resolve with old remediation rejects. Verification before resolution rejects. Review before fresh verification/acceptance rejects. Historical certification and altered content reject. |
| I84CYCLES / AC84GATES | Each completed future failure stops all later phases/publication. Exact interrupted-reservation resume consumes no additional slot. Prior failed recovery remains visible after every successful new stage. |
| I84GATES / AC84VERIFY | New-source/grant/closeout and existing event/ledger-membership/temp/content race tests reach a successful positive control, execute the mutation hook, reject precisely and preserve original ledger bytes. |
| I84SPLIT / AC84CYCLES | New authority evidence/anchor aliases reject in both temporal orders. Existing whole-lineage and source-claim conservation tests retain their meaning. |
| I84ISOLATE / AC84VERIFY | Primary Issue23/83 and old worktrees remain unchanged; product/state/provider/role/CI-privilege boundaries remain unchanged. |

Add an integration-level CI test with injected HTTP responses and realistic complete GitHub metadata so the production `main → current_pr → content_digest/check_pr` path is exercised. A fork-negative test that merely fails on missing metadata is insufficient.

Native saved-state checks must inspect the actual saved eighteen-event bootstrap and later real states, reporting their real stage. Synthetic delivery fixtures cannot substitute for actual publication evidence.

Required formal verification remains Ruff lint/format, configured mypy, full offline pytest, both workflow validators, offline retrieval/explanation evaluations, package build, Compose configuration and diff checks. Reserve exactly one fresh verification; preserve failures without reruns.

**Publication sequence**

The original one-new-PR permission and first recovery’s one actual-saved-delivery check sequence remain unused and are conserved.

1. Finish all authorized source/tests/docs/archive changes during remediation.
2. Freeze content.
3. Complete the one new verification and all acceptance evidence.
4. Complete the one new independent **final review** on identical content.
5. Commit/push certified content and allocate the original single draft PR, using the existing repository/branch, base `main`, primary issue 92 and PR other than 85.
6. Preserve any expected pre-delivery CI rejection.
7. Append the sole `publication_target` with the **original** grant digest. Require the new disposition’s clean current review, no blocker/pending repair/failure, and actual current content equal to verification/acceptance/review.
8. Run the native delivery gate and append ordinary delivery bound to that target/content.
9. Run the original one authorized actual-saved-delivery sequence: full offline suite, native/static workflow validation, merge-base prefix validation, actual current PR/head/base/content checks and archive integrity.
10. Record results externally without changing certified source/docs. Publish the delivered-ledger commit, confirm unchanged canonical source content and passing exact-head CI before readiness claims.

PR creation must occur after the new grant. This retains an unused publication allowance; it does not authorize another PR or another post-delivery check sequence.

A failure in the post-delivery sequence stops publication/readiness claims without retry. Preserve the saved delivery event as history; do not rewrite the terminal ledger or manufacture a replacement certificate.

**Interfaces, documentation and risks**

Affected interfaces: workflow source acquisition, replay/status/gates, authority/source-claim auditing, append, immutable fixtures and CI PR metadata validation. Application, financial, provider and database interfaces: **none**. Application graph/checkpoint JSON impact: **none**. New workflow state remains JSON-serializable.

Add a new ADR for this exact post-initial-review disposition and live-head identity contract. Preserve ADRs 0026/0033/0034/0035/0036 and both earlier grants unchanged. Update Iteration020 and directly affected workflow instructions/static markers to explain remediation 6, verification 3, final review 5, the event-17/18 bootstrap and conserved publication permissions.

Material risks are confusing prior failed recovery with current authorization, clearing certification incompletely, reusing stale remediation, reopening initial review, aliasing consumed authority, circular source hashes, fallback to queued metadata, fixture dependence on live state and publication from synthetic evidence. The pinned package, separate state, exact gates and actual saved-state checks address those risks.

A source/bootstrap mismatch, unavailable existing owner, unexpected prior work, unresolved consequential ambiguity, serious new blocker, completed failure or exhausted allowance stops `BLOCKED_FOR_DECISION`. No replacement, automatic extension or design retry follows.

No files were edited, tests run, ledger events appended or publication actions taken in this design session. The next permitted action is the single independent challenge against the exact transcribed proposal and frozen source manifest. Implementation remains unauthorized until that challenge passes, the coordinator approves, and the user grants the concrete finite disposition.

DESIGN_READY