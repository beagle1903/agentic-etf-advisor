R92SD1 design handoff: one bounded Issue92 stage-aware fixture repair.

This handoff is read-only. No files, ledger events, tests, commits, pushes or PRs were changed. It requires the reserved independent challenge and coordinator approval before the original implementation owner resumes. The user’s latest `approved` supplies the finite authorization described below; another user confirmation is unnecessary for this same scope.

**Diagnosis and scope**

The failed path is concrete:

- `tests/test_ticket_workflow.py:1271`, `test_issue92_actual_saved_recovery_and_portable_baselines`, reads the current Issue92 ledger. At line1289 it requires `issue92_pr_identity_stage == "repairing"` whenever the event count is at least18.
- The legitimate verification start at event21 produces `verifying` through `scripts/ticket_workflow.py:2497`. The third formal verification therefore failed despite correct production replay.
- `test_issue92_actual_saved_pr_identity_repair_and_archived_stop` at line2777 contains a second related assumption: remediation count6, verification limit3 and fixed prior limits. Those values must also follow the actual saved disposition; merely fixing line1289 would expose the adjacent failure.
- `State.gate` at line1749 and the replay failure guards at lines1987–2010 correctly stop substantive work after this completed failure. The explicit additional finite authority needs one narrow append-only disposition; changing a test alone cannot legitimately resume the stopped ticket.

The demonstrated defect maps to **I84GATES and AC84VERIFY**, with its finite remedy constrained by **I84CYCLES, I84TIME, I84HISTORY and I84ISOLATE**. All original S84 definitions and seven acceptance IDs remain unchanged.

Classification is consequential workflow replay/resumption with a mechanical test correction inside an established requirement. The write owner remains `/root/issue84_remainder_implementation`, `implementation_worker`, `gpt-6-sol`, medium. No owner replacement, specialist escalation or new implementation pass is warranted.

Authorized changes are limited to:

1. The two actual-ledger tests and focused supporting tests.
2. The exact Issue92 disposition, native replay/gates/status, source loading, authority audit and publication-age binding needed for this finite repair.
3. A new immutable evidence package, `.gitattributes` coverage, new ADR0038, iteration020 and directly affected workflow instructions/static checks.

Non-goals remain product/authentication work; actual Issue23/83 introduction, transition or resume; financial operations; application graph/checkpoint changes; provider/database interfaces; role/configuration/CI privilege changes; rewrites of accepted ADRs or historical archives; generic renewal, successor, new initial review, implementation, design reset, replacement owner, additional PR allowance or merge.

**Frozen starting point and invariants**

Use the complete current 23-event stop, never a reconstruction:

- Canonical ledger digest: `f3e67a49ac9ee5df4ed9ec6ff0fd4573c813fe3e8f6dee0329d2ba37d16ca32d`.
- Raw SHA256: `574af94846f38a4c5865b8c5f47141dd4bf4e53867334658a9522af73294015c`.
- Failed content: `e8bffb9f4841d4af9d80c1af471d7bcde7cd786b173bf6119ac927cbe162019a`.
- Capsule: `issue-92-issue84-remainder`, generation1, digest `197879ccd445194f77287455919e1f15efb5dce4366c5283a000ab6405dbeace`.
- Original publication grant: `76f78ac061f9e2c69b6a3aba6e4e89f4b7875321facce3e79b3c6dbdc1f53c2d`.
- Latest preceding repair grant: `0dd602e87bd79c779877ad92cbcd4c3bfd0771b771f1522bbce68d0ae841253f`.

The first recovery remains failed at initial review. The PR-identity repair remains failed at verification, with `{"phase":"verification","event_index":22}`. Event23 retains `B92-LIVE-STAGE-FIXTURE-ASSUMPTION`, criterion AC84VERIFY. Its required remediation count is7; `verification_repair_count` is7.

Before the new disposition, consumption is `5/4/6/4/4`, limits `5/4/6/5/4`, local verification `3/3`; order is implementation/initial-review/remediation/final-review/design-reset. There is no active or suspended phase, current certification, publication target or delivery. `initial_failed` remains true and `final_failed` false.

Preserve every original event, capsule, count, author, authority, blocker/resolution, failed outcome and historical PR85 binding. Retain all89 existing archive files byte-for-byte. Elapsed time remains measured audit data; additional seconds are0 and time does not replenish or exhaust owner-led counts.

**Small immutable source package**

Create `docs/workflow/history/issue-92-stage-fixture-repair-v1/` after challenge and approval. It contains20 files, adding to the existing89; do not duplicate older archives.

Ten source descriptors:

| Key | Fixed filename | Source |
|---|---|---|
| `stop_ledger` | `stop-ledger.json` | Exact23-event stopped ledger |
| `preparation_start` | `preparation-start.json` | Exact initial one-event authorization/reservation document |
| `before_integrity` | `verification/before-integrity.json` | Prior formal verification record |
| `before_status` | `verification/before-status.json` | Prior formal verification record |
| `current_status` | `verification/current-status.json` | Prior formal verification record |
| `verification_summary` | `verification/summary.json` | Prior formal verification record |
| `ruff_check` | `verification/ruff-check.log` | Complete prior gate log |
| `ruff_format` | `verification/ruff-format.log` | Complete prior gate log |
| `mypy` | `verification/mypy.log` | Complete prior gate log |
| `pytest` | `verification/pytest-full.log` | Complete failed full-suite log |

The eight closeout descriptors are `source_manifest`, `proposal`, `challenge_input`, `challenged_supplemental`, `completed_supplemental`, `challenge_result`, `challenge_report`, `coordinator_decision`, using the existing corresponding filenames. The remaining two files are `closeout-manifest.json` and `finite-grant.json`.

Descriptors use exact keys `{path,kind,raw_sha256,canonical_sha256}`. JSON files require strict JSON parsing and both hashes; text requires UTF-8, raw hash and null canonical descriptor. Proposal identity is separately the canonical JSON digest of the decoded complete text string. Literal paths and files only; reject traversal, symlinks, unexpected descriptor membership or substitutions. Extend `-text` Git attributes to the new archive. All package files remain inside canonical certified content.

`source-manifest.json` has exact keys:

`schema, repo, issue, capsule, original_capsule, failed_content, stop_ledger_digest, prior_grant_digest, prior_closeout_digest, sources`.

Its schema is `issue92-stage-fixture-sources-v1`; prior grant is the `0dd…` grant and prior closeout is `a5218d6ae86412b9699ba29f597e95069b68450acbab1e726e861d457c4adb03`. Existing source loaders validate the entire older89-file chain. The new loader validates complete source bytes and their relationships, including21-event verifying observations, failed content, local verification3/3, the single failed pytest invocation, 1 failed/1,509 passed/47 skipped, duration499775ms and retained stop events22–23. It must not claim the unexecuted later gates passed.

Use the existing eight-descriptor closeout structure with schema `issue92-stage-fixture-closeout-v1`. Freeze source manifest and this proposal before challenge. Challenge input has the existing exact keys:

`schema, repo, issue, capsule, original_capsule, proposal_digest, source_manifest_digest, supplemental_prefix_digest, supplemental_event_count`.

Its schema is `issue92-stage-fixture-challenge-input-v1`, and its prefix contains exactly three supplemental events: R92SD1 start/end, then R92SC1 start. Preserve the initial authorization document’s nested event envelopes; do not flatten or rewrite its first event. The completed document extends that identical prefix with challenge end and coordinator approval.

Supplemental starts and ends record reservation, session, pinned role/model/effort, timestamps and evidence. Design end binds the proposal; challenge start binds the challenge input; challenge end binds the structured result; approval binds the coordinator decision. Design/challenge elapsed time is retained. R92SD1 and R92SC1 are consumed once; revisions remain0.

Structured challenge and coordinator records use the existing corresponding field sets with schema names changed to `issue92-stage-fixture-challenge-result-v1` and `issue92-stage-fixture-coordinator-decision-v1`. The result must be `CHALLENGE_PASS`, and the decision `approved`, binding identical proposal/input/result digests. R92SC1 must be a separate `code_reviewer`, `gpt-6-sol`, high session, distinct from all writers and R92SD1. Freeze its actual session identity at reservation.

The coordinator may calculate new manifest/proposal/input/closeout/grant hashes after transcription and completion. Pin those exact results in implementation; do not accept arbitrary matching self-declared packages.

**Authority and grant**

The new grant records the already-provided user approval, after technical challenge/approval. Its `at` is the truthful grant-recording time, not an invented earlier timestamp.

Use exact keys:

`schema, repo, issue, authority, authority_anchor, at, capsule, original_grant_digest, prior_recovery_grant_digest, prior_pr_identity_grant_digest, stop_ledger_digest, failed_content, source_manifest_digest, proposal_digest, closeout_digest, owner, count_deltas, supplemental_deltas, review_disposition, publication, bootstrap_exception, seconds, merging, reason`.

Required values:

- Schema `issue92-stage-fixture-repair-grant-v1`.
- Original capsule and owner unchanged.
- Authority kind `user`; preserve the preparation record’s name/evidence and exact anchor `human-approved-stage-aware-fixture-repair-2026-10-09-after-third-verification-failure`.
- Count deltas `{implementation:0,initial_review:0,remediation:1,final_review:0,design_reset:0}`.
- Supplemental deltas `{verification:1,design:0,challenge:0,design_revision:0}`.
- Review disposition `conserve-unused-final-review-after-stage-fixture-repair`.
- Bootstrap exception `append-one-stage-fixture-disposition-and-one-remediation-start`.
- Seconds integer0, merging booleanfalse.
- Stop/content/source/proposal/closeout and all three older grant bindings exact.

Publication retains the preceding grant’s complete publication object unchanged: original one new PR, additional count0, original repo/head/base/primary issue92, excluded PR85, one actual-saved-delivery check sequence and additional sequences0.

All count fields require actual integers, rejecting booleans. Use existing normalization for evidence and anchors. The preparation record and later grant are two records of **one approval**, not two issuances. Permit their exact designated relationship inside this pinned package; do not manufacture different evidence wording or a fresh anchor to evade reuse detection. The disposition consumes the identity once. Reject its normalized evidence or anchor anywhere else in prior authority history or another ledger, regardless of traversal order, display name or whitespace. The designated preparation/grant relationship must not become a general authority-reuse exemption.

**Disposition and replay**

Add the single event type `issue92_stage_fixture_repair`, allowed only as event24 of Issue92 after the exact stopped23-event prefix.

Its data uses exact keys:

`version, authority, authority_anchor, capsule, prefix_digest, grant_digest, source_manifest_digest, closeout_digest, proposal_digest, reason`.

Version is `issue92-stage-fixture-repair-v1`; all other values match the pinned grant/package. Timestamp is at or after completed technical approval and the grant. Validate all starting-state conditions above, exact owner, absence of any earlier stage-fixture disposition, and the exact sole blocker.

Effects:

- Raise only remediation limit6→7 and local verification limit3→4.
- Keep final-review limit5 and all consumption unchanged.
- Clear current verification/acceptance/review/remediation readiness and associated content references; preserve design readiness and the frozen approved capsule.
- Mark pending repair.
- Preserve previous recovery and PR-identity stage/failure fields permanently as failed historical results.
- Create distinct JSON-serializable `issue92_stage_fixture_ref`, `issue92_stage_fixture_stage`, `issue92_stage_fixture_failure`, and supplemental participant records. Initial stage is `repair_pending`; failure is null.

Event25 must immediately be the ordinary remediation start for the original owner and capsule. It consumes remediation7/7 and advances the new stage to `repairing`. No interposed audit event is allowed between24 and25.

After this disposition, only its new stage drives current recovery gates. Earlier failed stages remain visible and cannot veto the newly authorized path or be relabeled successful. Before event24, all old behavior remains identical.

The new progression is:

| Action | Required state | Result |
|---|---|---|
| Remediation start | New `repair_pending`, count6/limit7, exact owner | `repairing`, count7 |
| Remediation pass | Matching active repair | `repaired`; historical failures retained |
| Exact blocker resolution | Successful seventh remediation, no active phase | Resolve only `B92-LIVE-STAGE-FIXTURE-ASSUMPTION` |
| Verification start | Repaired, resolved, no pending repair, count7, verification3/4 | `verifying`, verification4 |
| Verification pass | Same frozen content | `verified` |
| Acceptance | All seven frozen IDs and matching content | Current acceptance |
| Final-review start | Fresh verified/accepted content, initial4, final4/5 | `reviewing`, final5 |
| Final-review pass | Same content, independent fresh reviewer | `reviewed` |
| Target and delivery | All existing current certification gates | `delivered` |

A completed failure in remediation, verification or final review sets the new stage to `failed` with exact phase and one-based event index. It blocks every substantive phase, resolution, acceptance, target and delivery. Retain audit-only blocker/charge/coordination records; do not allow a continuation, extension, split, transition, owner handoff or another special disposition to renew this attempt.

Pause/interruption and exact-session resume preserve the existing reservation/count and stage, with truthful elapsed accounting. They cannot turn a completed failure into resumable interruption.

Add the new authority/event to whole-lineage audit, including unique Issue92 claim checks. Status exposes both historical failures and the new current stage, failure, reference, limits and consumption.

Review exclusions include every historical/current write or verification author, prior review participants, all preceding design/challenge participants and the new R92SD1/R92SC1 participants. Apply normalized identity checks. The unused final review is a fresh separate session; design challenge is not that review.

**Atomic bootstrap and side-effect boundaries**

Retain the genuine native rejection already recorded. Because the current validator cannot accept event24, the coordinator may use the narrowly authorized pre-validator exception to append only events24–25 under the existing repository-wide cooperating-writer lock.

Before replacement, capture and recheck the actual23-event ledger raw bytes, every ledger filename/bytes, source/grant files, all archive bytes, repository content/working bytes and candidate temporary bytes. Validate exact envelopes, prefix, owner, timestamps, authority and reservation without claiming the old native validator passed. Use atomic replacement and release only the lock token this writer owns. Preserve all other ledgers and never steal an existing lock.

The new native engine must validate the **actual saved25-event ledger and package** before remediation closes. All subsequent appends use the native path in `append` at `scripts/ticket_workflow.py:3373`, preserving its real-source, ledger-membership, working-content and temporary-file race checks. No new network, credential or financial side effects are introduced.

**Stage-aware test contract**

Keep archived2-,6-,16- and18-event fixtures immutable, with fresh copies and deterministic fixture timestamps. An immutable18-event fixture still requires `repairing`, remediation6 and verification limit3.

Historical fixtures must never be slices of the mutable current ledger. Add the exact archived23-event stop and deterministic synthetic continuations based on it.

Replace the two actual-ledger tests’ numeric-length assumptions with one test-local independent expected-state assertion. It reads the saved event history and determines:

- Which exact disposition is present.
- The latest relevant start/completion and its matched phase/session/outcome.
- Expected current stage, active/suspended phase, retained failures, counts and limits.
- Current certification/content expectations.

This helper must not call production replay or reuse production stage-selection functions to obtain expectations. It is a small test oracle, not a second gate engine: expected stage follows explicit event facts, counters follow counted starts plus frozen inherited counts, and limits follow the exact recognized disposition. Compare those expectations to replay output. Reject unexpected event shapes/sequences through native validation.

Do not use a stage allowlist as the assertion. Demonstrate the oracle’s sensitivity by mutating the returned stage or another relevant returned field while leaving the event history intact; the helper must fail. Cover at least a verifying→repairing misreport, failed→verified misreport and incorrect new limits.

Exercise independently labeled projections for:

- Immutable18 repairing.
- Exact23 stopped/failed, verification3/3.
- New24 pending and25 repairing, remediation7/7.
- Repair pass and exact resolution.
- New verification active4/4.
- Verified and accepted.
- Independent final review active5/5.
- Reviewed and delivered.
- Completed failure at each new phase.
- Interrupted/resumed reservations without extra counts.

Run the same actual-ledger assertion against the actual saved current ledger and against temporary saved copies of these projections. Check current source content during active verification **and final review**, and delivered binding during delivery. Do not require historical failed content to equal later repaired source content.

Focused negatives must also reject wrong prefix/event position, duplicate marker, changed capsule/owner/grant/deltas, bool counts, missing/tampered/rebound sources, authority reuse in both lineage orders, early/wrong blocker resolution, stale certification, another repair/verification, initial review, reused reviewer, changed post-certification content and races in every actual input class. Each mutation needs a passing positive control reaching the intended boundary.

Preserve the universal queued/live PR identity fix and all existing realistic HTTP/CLI identity tests.

**Verification, documentation and delivery**

The original owner performs focused tests/self-review within remediation7. After source/package/docs are complete, freeze content and stop edits. The coordinator records truthful remediation completion, exact blocker resolution, checks the native verification gate and reserves verification4 before dispatching that same owner.

Run the required formal sequence once: Ruff lint/format, mypy, full offline pytest, static and native workflow validators, retrieval and explanation evaluations, package build, Compose configuration and diff check. Retain complete logs/status/timings externally, verify identical before/after source content, all109 archive Git-byte roundtrips and unchanged primary Issue23/83 hashes. No automatic rerun after a completed failure.

On success, record acceptance against all frozen IDs and the same content; native-check/reserve the conserved final-review slot before dispatch. Independent final review covers the complete Issue92 remainder and all repairs, not only this assertion. It may inspect focused evidence without rerunning the formal suite. Any serious unresolved defect or failed final review stops.

Add ADR0038 describing only this exact disposition, its retained failures and stage-aware verification. Update iteration020 and directly affected workflow instructions/static markers before certification. Accepted ADRs0026/0033–0037 remain untouched.

After clean final review, conserve the original single draft PR and saved-delivery check sequence. `publication_target.grant_digest` remains the **original** `76f…` grant. `check_pr` must additionally require PR creation after the new grant and event24, while retaining exact live head/base repository/ref/SHA, number, current body/primary issue, target and content checks. Preserve ordinary matching-fork behavior outside Issue92.

Run the one authorized actual-saved-delivery check sequence, including full offline pytest and current live PR/content/prefix/archive validation, against the real saved delivered ledger before publishing that delivered ledger. This is the existing publication condition, not a fifth verification allowance or permission to repair/rerun. Failure stops publication readiness. No merge is authorized.

Affected interfaces are workflow replay, `State.gate`/status, source-package validation, whole-lineage authority audit, atomic append, tests, documentation/static markers and Issue92 publication-age validation. JSON impact is workflow-only fields/events described above; application graph/checkpoint state and provider/database/financial interfaces are **none**.

Principal risks are repeating a mutable-stage assumption, accidentally advancing historical failed stages, broadening the disposition into renewal, reusing authority under altered text, stale content certification, and a post-delivery test failure. The exact prefix, separate current stage, independent test oracle, fixed deltas, single-use authority and full progression controls address them. Any package mismatch, unresolved consequential ambiguity, serious frozen-ID defect or completed failed gate returns `BLOCKED_FOR_DECISION`; no revision or replacement session is authorized by this handoff.

DESIGN_READY