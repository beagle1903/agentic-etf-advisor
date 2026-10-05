Generation 2 is ready for independent challenge. It authorizes no implementation. The coordinator must freeze the complete contract below, obtain the separately authorized challenge, and request the specific implementation allowance only after a clean result.

The execution path is `main` → `validate_all`/`replay` → `State.gate`, with `append` performing candidate replay before atomic replacement. Currently, terminal replay rejects every later event, and `check_pr` compares only the original `delivery_binding`. The exception should intercept exactly one pinned certificate before the terminal rejection, preserving all other behavior. References: [replay and terminal check](C:/Users/burha/.codex/worktrees/cycle-bounded-workflow/agents-lab/scripts/ticket_workflow.py:412), [append](C:/Users/burha/.codex/worktrees/cycle-bounded-workflow/agents-lab/scripts/ticket_workflow.py:1145), [content_digest](C:/Users/burha/.codex/worktrees/cycle-bounded-workflow/agents-lab/scripts/ticket_workflow.py:1016), [check_prefix](C:/Users/burha/.codex/worktrees/cycle-bounded-workflow/agents-lab/scripts/ticket_workflow.py:1258), [check_pr](C:/Users/burha/.codex/worktrees/cycle-bounded-workflow/agents-lab/scripts/ticket_workflow.py:1305).

**Capsule identity and authority**

```json
{
  "id": "issue-84-pr85-correction-delivery",
  "generation": 2,
  "repo": "beagle1903/agentic-etf-advisor",
  "issue": 84,
  "pr": 85,
  "classification": "consequential",
  "architect": {
    "role": "design_architect",
    "model": "gpt-6-astra",
    "effort": "high",
    "session": "/root/pr85_design_revision2"
  },
  "challenger": {
    "role": "code_reviewer",
    "model": "gpt-6-sol",
    "effort": "high",
    "session": "/root/pr85_challenge_revision2"
  },
  "proposed_owner": {
    "role": "implementation_worker",
    "model": "gpt-6-sol",
    "effort": "medium",
    "session": "/root/pr85_redelivery_implementation"
  },
  "proposed_reviewer": {
    "role": "code_reviewer",
    "model": "gpt-6-sol",
    "effort": "high",
    "session": "/root/pr85_redelivery_review"
  },
  "implementation_authorized": false,
  "rejected_generation": 1,
  "rejected_capsule_digest": "e21925dd0c39c9642d29798fc0353bcb6135182c5c470ae23f647316f5233473",
  "original_prefix_events": 61,
  "original_prefix_digest": "320737ce852729b2fc75b19c9a06c5d072c1149059b9fc023e88891aa0b8d4a6",
  "original_capsule_id": "issue-84-cycle-bounded-workflow",
  "original_capsule_generation": 3,
  "original_capsule_digest": "df870f205cc3a8053c152699ce16030a1cedc518fdda0588ae16d3cbcd95fda9",
  "original_delivered_content": "f9ffcec169e992a677214253f486e022203785fac2a54184be5cb4198b6fc6f7",
  "original_consumed": {
    "implementation": 2,
    "initial_review": 1,
    "remediation": 3,
    "final_review": 3,
    "design_reset": 2
  }
}
```

Rationale: the status correction changes content after delivery. Reusing the original certificate would violate I84HISTORY/I84GATES. One certificate bound to the actual supplemental history closes this particular publication gap without reopening the ticket.

Scope: retained status fix, one pinned certificate validator, its replay/append/prospective-check/status/PR integrations, focused tests and workflow documentation. Permitted implementation files are `scripts/ticket_workflow.py`, `tests/test_ticket_workflow.py`, workflow guidance, the supplemental iteration records, and one new ADR.

Non-goals: generic correction/reopening policy; further attempts; role changes; CI privilege changes; new content exclusions; split or migration changes; edits to Issue23/83 histories; application/authentication/provider/database/financial work.

**Frozen invariants and acceptance**

Retain the generation-1 invariant and acceptance IDs:

| ID | Required interpretation |
|---|---|
| I84HISTORY / AC85C-HISTORY | Exact original 61-event prefix, capsule, counts and original binding survive. Original delivered state remains terminal. Issue23/83 files and histories are unchanged. |
| I84CYCLES / AC85C-BOUND | One certificate; complete fixed historical import; exactly the authorized remaining slots; no retries, dropped failures, reused approvals or replacement sessions. |
| I84GATES / AC85C-EVIDENCE | Complete generation-2 capsule, challenge and coordinator approval agree. Fresh verification, acceptance and independent review bind identical final content. |
| I84GATES / AC85C-IDENTITY | Certificate applies only to this repository, Issue84 and PR85. |
| I84SPLIT / AC85C-STATUS | Preserve the existing correction of unallocated split-pool reporting, including zero; allocation enforcement remains unchanged. |
| I84ISOLATE / AC85C-ISOLATE | Workflow-only diff, documented exception, required checks and independent review. |

No application graph/checkpoint JSON change. No side-effect interface change. Workflow JSON gains the single event and a separate status projection defined below.

**Exact certificate schema**

The following type notation is normative. Objects have exactly the listed keys; unknown or missing keys reject. Arrays preserve order. `int` means Python `type(x) is int`, excluding booleans. JSON duplicate keys and nonfinite numbers reject before validation.

- `Text`: nonempty string, at most 4,000 characters.
- `SHA`: lowercase hexadecimal string of exactly 64 characters.
- `UTC`: valid `YYYY-MM-DDTHH:MM:SSZ`.
- `Ref`: exact object `{ "id": Text, "generation": int, "digest": SHA }`.
- `Evidence`: exact object `{ "anchor": Text, "summary": Text }`.
- `Anchor` strings are compared after Unicode NFKC normalization, whitespace collapse and case folding. They must be nonempty after normalization.
- Approval evidence additionally uses the existing `evidence_key` normalization when checking original-ledger evidence. Existing historical normalization behavior is not changed.

The only added outer event is:

```text
{
  "type": "correction_delivery",
  "at": UTC,
  "data": {
    "version": "pr85-correction-v2",
    "repo": "beagle1903/agentic-etf-advisor",
    "issue": 84,
    "pr": 85,
    "prefix_digest": SHA,
    "capsule": object,
    "capsule_digest": SHA,
    "historical_import": object,
    "historical_import_digest": SHA,
    "transcript": [Entry, ...],
    "content": SHA,
    "delivery_evidence": Evidence
  }
}
```

`capsule` is the complete frozen generation-2 contract, including this schema, fixed historical import, validation rules and test matrix. Its canonical digest uses the existing `digest` function. The implemented exception pins that single digest. A capsule file is the complete specification, not merely the identity JSON above. No digest is placed inside the object whose digest it represents.

`historical_import` must equal the capsule’s complete fixed historical-import object; its digest must equal `digest(historical_import)`. It cannot be an arbitrary caller-supplied history. The coordinator must mechanically encode the following fixed values and tables before challenge; that encoding introduces no discretionary contract decisions.

**Fixed historical import**

The historical-import object has exactly these keys:

```text
{
  "sources": [Source, Source, Source, Source],
  "authorizations": [HistoricalAuthorization, HistoricalAuthorization, HistoricalAuthorization],
  "phases": [HistoricalPhase, HistoricalPhase, HistoricalPhase,
             HistoricalPhase, HistoricalPhase, HistoricalPhase],
  "observations": [HistoricalObservation, ...],
  "unknowns": {
    "phase_timestamps": "not recorded; do not fabricate",
    "interruptions": "none recorded in the inspected sources",
    "provenance": "recorded evidence, not authenticated live-session provenance"
  }
}
```

`Source` is exactly `{ "id": Text, "locator": Text, "sha256": SHA, "normalization": "git-blob" | "lf" }`. Fixed sources:

| ID | Locator | SHA256 | Normalization |
|---|---|---|---|
| S1 | `d1611e70db24c665770220fd6d9045e9fe5769a8:docs/iterations/018-issue-84-pr85-status-correction.md` | `48a398f0dacbfd32f757eec5b3e88ee9396f8d4055ffd2b11b466e9048df49ae` | git-blob |
| S2 | `d1611e70db24c665770220fd6d9045e9fe5769a8:docs/iterations/018-pr85-redelivery-design.md` | `c6ac46549e5ace1d8832a9a85fb6c44b4b30f4c913d2c9381c176411318cbc4d` | git-blob |
| S3 | `d1611e70db24c665770220fd6d9045e9fe5769a8:docs/iterations/018-pr85-correction-delivery-capsule.json` | `2485d8e1264a3f8cbb3e3527d677b124d9af09580fa9ca1b89d1ececf2d93d13` | git-blob |
| S4 | `docs/iterations/018-pr85-redelivery-design.md through the recorded revision2 phase_start, inspected 2026-10-05` | `acb180357132c078600ff8aeaf95267f24fb97034ae4f96b3f12b21191891dff` | lf |

These are documentary anchors; pure replay does not fetch Git objects or conversation data. The complete source snapshots or immutable Git objects remain inspectable by the coordinator and challenger.

`HistoricalAuthorization` is exactly:

```text
{
  "id": "A1" | "A2" | "A3",
  "name": "burha",
  "anchor": Text,
  "evidence": Text,
  "allowances": {
    "remediation": int,
    "final_review": int,
    "design_reset": int,
    "challenge": int,
    "implementation": int,
    "initial_review": int,
    "verification": int
  }
}
```

Fixed authorizations:

- A1: anchor `thread:01a10b8b-adae-7d61-89cb-0ce57ca1c9f4/message:01a10b99-c14a-7830-8ece-0698503e16c6`; evidence is the exact status-exception approval quoted in S1. Allowances: remediation 1, final_review 1, verification 1; every other field 0.
- A2: anchor `thread:01a10b8b-adae-7d61-89cb-0ce57ca1c9f4/message:01a10ba4-298d-7561-9e2d-99522619cd33`; evidence `go on`, with the explicitly recorded scope of one design and independent challenge. Allowances: design_reset 1, challenge 1; every other field 0.
- A3: anchor `thread:01a10c3f-947b-7d22-9a62-18be591c6074/user-reply:ok-approved-to-additional-design-revision-and-independent-challenge`; evidence `ok approved`. Allowances: design_reset 1, challenge 1; every other field 0. This fallback anchor truthfully records that the message UUID was unavailable.

The fallback is permitted only for this fixed A3 record. Future implementation authority requires a distinct concrete message/permalink anchor recorded when received.

`HistoricalPhase` is exactly:

```text
{
  "slot": Text,
  "phase": Text,
  "authorization": "A1" | "A2" | "A3",
  "session": Text,
  "role": Text,
  "model": Text,
  "effort": Text,
  "agent_thread": Text | null,
  "reservation": Evidence,
  "outcome": "pass" | "fail" | "open",
  "result": Evidence | null,
  "capsule": Ref | null,
  "started_at": null,
  "ended_at": null,
  "write_authors": [Text, ...]
}
```

The six required rows, in exact order:

| Slot | Phase/authority | Session and identity | Outcome |
|---|---|---|---|
| H1 | remediation / A1 | `/root/pr85_status_correction`; bounded_worker / gpt-6-luna / medium; agent thread `01a10b9b-f659-7541-889a-bf2c5129bc78` | pass |
| H2 | verification / A1 | `/root`; coordinator verification; role `coordinator`, model/effort `not-recorded`, agent_thread null | pass |
| H3 | final_review / A1 | `/root/pr85_status_review`; code_reviewer / gpt-6-sol / high; agent thread `01a10ba0-4c44-7e60-91fb-113b3ade4648` | pass |
| H4 | design_reset / A2 | `/root/pr85_redelivery_design`; design_architect / gpt-6-astra / high; agent thread `01a10ba6-341a-7611-9ad8-7553849806d1` | pass |
| H5 | challenge / A2 | `/root/pr85_redelivery_challenge`; code_reviewer / gpt-6-sol / high; agent thread `01a10bab-8ed6-7e10-94f0-d5e2b7f0ee68` | **fail** |
| H6 | design_reset / A3 | `/root/pr85_design_revision2`; design_architect / gpt-6-astra / high; agent_thread null | open |

H1–H3 reservation/result evidence references S1 and its corresponding named section. H4–H5 references S2. H6 reservation references S4’s actual `phase_start`; result is null. H4 and H5 capsule refs identify generation 1 and its rejected digest. H1–H3/H6 capsule fields are null: H1–H3 use the existing status capsule in S1; H6 began before the completed generation-2 digest existed.

H1 `write_authors` is `["/root/pr85_status_correction"]`. H2 is `["/root/pr85_status_correction", "/root"]`, conservatively excluding both verification contributors from later review. Other rows have empty arrays.

The H2 import does **not** claim an independently recorded engine reservation or a model assignment. It preserves the actual supplemental verification sequence under the approved import exception.

`HistoricalObservation` is exactly `{ "id": Text, "slot": Text, "anchor": Text, "result": "pass" | "fail" | "rejected", "summary": Text }`. Required observations are:

- Failed initial Ruff format check in H1: `exec-102fdbb7-bc0a-44ff-99b0-5f150387125a`, result fail; corrected within that same implementation attempt.
- Three H1 pytest exit-zero anchors: `exec-f3f41b4f-0ad0-4161-b804-963f70c07d3e`, `exec-5c1ab1cb-e2ae-486b-8496-8abe278da4c0`, `exec-549fc404-6449-41c1-a229-3683303c2e47`.
- H1 final result `msg_00128a8f345bf923016ac37cd4625c87d291e9c3a8e21e4101`: 115 focused tests and subsequent checks passed.
- H2 coordinator validator evidence `exec-ae7a1923-27a2-4289-8bed-78f98ff473ba`.
- Required ordinary gates for H1, H3, H4, H5 and H6 were rejected as terminal, as recorded in S1/S2/S4. Each remains result `rejected`; none becomes a passed gate.
- H5 failure explicitly retains I84CYCLES/AC85C-BOUND and I84GATES/AC85C-EVIDENCE, with the omitted-phase/reused-authority scenario.
- Reviewed status source/test hashes from S1 remain recorded as audit-only evidence:
  - `8ed738d2ba1e700b69b351f3d08fd039402e97cc00f2362d1d38a1cc5845cd6c`
  - `715ca6178031196a57b9e0f1182cc8502e66fb49ceb711e26acc2c44ba65f805`

Observation IDs are fixed descriptive IDs chosen once during mechanical encoding; ordering is by ID, not an invented chronological ordering of unknown tool times.

**Exact future transcript**

Every `Entry` has exactly `{ "seq": int, "at": UTC, "type": Text, "data": object }`. `seq` is contiguous starting at 1. Timestamps are nondecreasing, no later than the certificate timestamp, and the certificate timestamp is no later than replay’s `now`. Elapsed duration never exhausts the attempt.

Allowed variants and exact `data` keys:

```text
phase_start:
  {slot: Text, session: Text, capsule: Ref,
   authorization: Text, gate: Evidence, reservation: Evidence,
   content: SHA|null, prior_digest: SHA}

pause:
  {slot: Text, session: Text, evidence: Evidence, prior_digest: SHA}

resume:
  {slot: Text, session: Text, evidence: Evidence, prior_digest: SHA}

phase_end:
  {slot: Text, session: Text, outcome: "pass"|"fail",
   capsule: Ref, evidence: Evidence,
   observations: [Observation, ...], prior_digest: SHA}

user_authorization:
  {id: "A4", name: "burha", anchor: Text, evidence: Text,
   capsule: Ref, historical_import_digest: SHA,
   allowances: {implementation: 1, verification: 1, initial_review: 1,
                remediation: 0, final_review: 0,
                design_reset: 0, challenge: 0},
   prior_digest: SHA}

design_approval:
  {name: Text, session: "/root", anchor: Text, evidence: Text,
   capsule: Ref, historical_import_digest: SHA, prior_digest: SHA}

acceptance:
  {capsule: Ref, content: SHA,
   evidence: {
     "AC85C-HISTORY": Evidence,
     "AC85C-BOUND": Evidence,
     "AC85C-EVIDENCE": Evidence,
     "AC85C-IDENTITY": Evidence,
     "AC85C-STATUS": Evidence,
     "AC85C-ISOLATE": Evidence
   }, prior_digest: SHA}
```

`Observation` is exactly `{ "anchor": Text, "check": Text, "result": "pass" | "fail", "summary": Text }`.

For every entry, `prior_digest` equals:

```text
digest({
  "historical_import": historical_import,
  "transcript": transcript entries strictly before this entry
})
```

H6 is already active from the fixed import. The only legal complete transcript is:

1. Finish H6 with pass, allowing recorded H6 pause/resume pairs before its end.
2. Start H7, the independent revision-2 challenge; finish with pass.
3. A4 user authorization.
4. Coordinator design approval.
5. Start and finish H8 governance implementation with pass.
6. Start and finish H9 verification with pass.
7. Acceptance.
8. Start and finish H10 independent code review with pass.

Each started phase can contain zero or more alternating pause/resume pairs before its single end. No other entry ordering is allowed.

Fixed future slots:

| Slot | Phase | Session | Authorization | Content |
|---|---|---|---|---|
| H7 | challenge | `/root/pr85_challenge_revision2` | A3 | null |
| H8 | implementation | `/root/pr85_redelivery_implementation` | A4 | null |
| H9 | verification | `/root/pr85_redelivery_implementation` | A4 | final SHA |
| H10 | initial_review | `/root/pr85_redelivery_review` | A4 | same final SHA |

Roles/models/efforts come from the frozen identities above; callers cannot supply substitutes. H7 is separate from H6, and H10 is separate from every historical/current write author. A session cannot change role.

Every future start records the required ordinary dispatch check and its actual result in `gate`. Until a successful certificate exists, that ordinary gate remains terminal-rejected. The approved bootstrap exception—not a fabricated passed gate—authorizes the supplemental reservation. The coordinator records starts before dispatch and all actual pauses, resumes, failures and outcomes in the append-only supplemental journal.

The prospective check receives that complete journal outside the repository. Imported transcript entries must equal its entries exactly. A reviewer must compare it against the actual coordinator reservations and source anchors. This journal is not an additional content-digest exclusion.

**Review seal and noncircular binding**

H10’s `phase_start.prior_digest` is the audit seal for all imported history and transcript through acceptance. The H10 reviewer validates that exact prefix and the final repository content. Its `phase_end.prior_digest` binds the same history plus its own start and any recorded pause/resume entries.

H10’s result evidence must explicitly identify the H10 start seal and final content SHA. The validator checks these values by adding two keys **only to H10 `phase_end.data`**:

```text
audited_prefix_digest: SHA
reviewed_content: SHA
```

`audited_prefix_digest` must equal H10 start’s `prior_digest`; `reviewed_content` must equal H9 start, acceptance, H10 start and certificate `content`.

This avoids a circular certificate digest: the reviewer seals the preceding audit prefix and repository content, not the event containing its own result. The final event is validated structurally and atomically after the review. The certificate digest is computed only after construction, for reporting; it is not an input to its own fields.

**Required rejection predicates**

1. Certificate allowed only as event 62 after the exact fixed prefix. There must be exactly 62 events when it is present. No second certificate or later event.
2. Original state must replay as the expected delivered Issue84 state with fixed capsule, binding and counts, no open phase or blocker.
3. Original state fields remain unchanged. Add a distinct `correction_binding`; do not replace `delivery_binding`, set ordinary `ready`, reopen clocks or grant ordinary phase limits.
4. Generation-1 capsule remains unchanged and failed H5 is mandatory. A3 is the sole historical exception permitting H6 after H5’s failure.
5. Historical import must match the pinned object and digest exactly. Missing H2, failed H5, failed formatting observation, A3, or H6 reservation rejects.
6. All current capsule refs must equal the exact generation-2 ref. H6 success, H7 success, A4 and coordinator approval must bind it and the same historical import.
7. All four authorization anchors are pairwise unique after normalization. Future A4 evidence cannot equal any previously consumed approval evidence after `evidence_key` normalization.
8. Seed consumed evidence from every original authorization-bearing event, including capsule user authorization, extensions, policy transitions and split approvals. Include original coordinator approval evidence when testing attempted reuse. Then add A1/A2/A3. Changing authority display names does not affect uniqueness.
9. A4 must identify this exact proposal, one implementation/verification/initial-review allowance and zero other allowances. It cannot reuse A3’s approval or infer implementation from “ok approved” in the current turn.
10. Strict transcript grammar rejects omitted starts/ends, duplicate starts, extra slots, overlap, end-while-paused, resume-without-pause and different-session resume.
11. A failed H6/H7/H8/H9/H10 outcome makes correction delivery invalid. No later entry restores eligibility. Any actual failure is retained in the journal and reported `BLOCKED_FOR_DECISION`.
12. A failed self-check during an active implementation slot can be corrected inside that same slot. It remains an observation. A failed completed phase, independent challenge or independent review cannot.
13. Any newly discovered unrecorded historical reservation/interruption invalidates the frozen import and stops this attempt. Do not silently append it under the challenged digest.
14. All original write sessions plus H1/H2/H8/H9 authors are excluded from H7/H10. Normalize session identities as above; aliases referencing an already-known agent thread must map to that same identity.
15. H9, acceptance, H10 and final certificate must share one content SHA. Documentation is frozen before H9. No subsequent tracked-file edit can retain that evidence.
16. Prospective check validates the full candidate, journal equality and current `content_digest(root,84)`.
17. Atomic append performs the same validation under the existing writer lock and recomputes current content immediately before `os.replace`. A changed digest rejects without replacing the ledger.
18. `check_pr` selects `correction_binding` exclusively when present; it never falls back to the old binding. Require exact repo, PR85, Primary issue #84 and current PR-head content.
19. `check_prefix` and existing ledger-introduction/lineage checks remain unchanged and mandatory.
20. No expanded source exclusion, generic certificate version, arbitrary issue/PR allowance, or automatic reset is accepted.

Static validation can detect omissions against the pinned import, complete journal and reviewer seal. It cannot discover a wholly unrecorded real-world session or authenticate a fabricated conversation reference. That existing provenance limitation must remain explicit.

**Counts and status interface**

Do not alter existing status `counts`, `limits`, `remaining_counts`, capsule or owner fields. Add exactly one nullable `correction` field; it is null without a validated certificate.

On success:

```json
{
  "version": "pr85-correction-v2",
  "binding": {
    "repo": "beagle1903/agentic-etf-advisor",
    "pr": 85,
    "content": "<validated SHA>"
  },
  "supplemental_counts": {
    "implementation": 1,
    "initial_review": 1,
    "remediation": 1,
    "final_review": 1,
    "design_reset": 2
  },
  "aggregate_counts": {
    "implementation": 3,
    "initial_review": 2,
    "remediation": 4,
    "final_review": 4,
    "design_reset": 4
  },
  "supplemental_challenges": 2,
  "supplemental_verifications": 2,
  "remaining_counts": {
    "implementation": 0,
    "initial_review": 0,
    "remediation": 0,
    "final_review": 0,
    "design_reset": 0
  }
}
```

These values are derived from validated starts, including failed H5 and both design reservations, then compared to the fixed totals. They are not caller-supplied accounting.

**Focused verification matrix**

| Fixture | Expected result / frozen ID |
|---|---|
| Complete valid certificate including failed H5 and failed in-attempt Ruff observation | Pass replay, prospective check, atomic append and PR check; AC85C-HISTORY/BOUND |
| Remove/reorder any historical phase, observation, approval or H6 reservation | Reject; AC85C-BOUND |
| Change H5 fail to pass, remove rejected generation 1 or replace its digest | Reject; AC85C-HISTORY/EVIDENCE |
| Reuse original/A1/A2/A3 approval with renamed authority, whitespace/case/Unicode anchor changes | Reject; AC85C-BOUND |
| Give A4 an extra remediation, review, reset or implementation allowance | Reject; AC85C-BOUND |
| Fail H7/H8/H9/H10 then append a new start or a fabricated successful end | Reject; AC85C-BOUND/EVIDENCE |
| Pause/resume same slot/session, with long quota wait | Pass without extra count; AC85C-BOUND |
| Drop pause from imported journal, resume different session, overlapping start or unfinished phase | Reject; AC85C-BOUND |
| Old generation challenge/approval; approval before challenge; implementation before A4 | Reject; AC85C-EVIDENCE |
| Reviewer matches original writer, status writer, coordinator verifier or governance writer, including known alias | Reject; AC85C-EVIDENCE |
| Change a pre-review transcript entry without updating the sealed prefix; mismatch journal and certificate | Reject; AC85C-EVIDENCE |
| Change source/tests/docs after verification or review; simulate content change immediately before replacement | Reject without ledger replacement; AC85C-EVIDENCE |
| Wrong repo/issue/PR, old content fallback, second certificate or post-certificate event | Reject; AC85C-IDENTITY |
| Alter/truncate original 61-event prefix, change Issue83, weaken merge-base checks | Reject relevant existing check; AC85C-HISTORY/ISOLATE |
| Ordinary delivered ticket unrelated to exact Issue84 prefix | Remains terminal; AC85C-BOUND |
| Existing split-status and over-allocation regressions | Pass unchanged; AC85C-STATUS |

Run focused workflow tests, both workflow validators, Ruff lint/format, mypy, full offline pytest, offline evaluations, package build, Compose configuration validation and diff checks on frozen final content. No services, provider calls or financial writes. Independent H10 review covers the governance changes; the earlier status-only review is audit evidence.

Documentation requires a new ADR for this pinned one-off exception, supplemental journal/import explanation, exact failure behavior and final-content freeze rules. Preserve accepted ADR history and the rejected generation-1 capsule.

Risks are the self-modifying governance validator, incomplete historical timestamps, alias/provenance limits and content-freeze discipline. Any need for generic reopening, extra attempts, a changed scope/schema after challenge, unknown historical work, failed challenge/verification/review or a different implementation owner stops for explicit decision.

No files were changed and no tests were executed during this read-only design session.

DESIGN_READY

<oai-mem-citation>
<citation_entries>
MEMORY.md:18-22|note=[used prior approval and evidence-first workflow guidance]
</citation_entries>
<rollout_ids>
</rollout_ids>
</oai-mem-citation>
