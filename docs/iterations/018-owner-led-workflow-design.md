The implementation should add a small policy extension to the existing engine. Keep ordinary phase events, owner routing and content checks. Do not add certificates, external journals, transcript seals, or ticket-specific exceptions.

This handoff binds the existing Issue86 capsule:

`issue-86-owner-led-workflow`, generation `1`, digest `94b135a551b96d9e2af8a8321488aac343d5d5d38c8bc9e661d9bf7e2bfafbc8`.

It supplies implementation details within the frozen definitions; it does not replace the capsule or authorize implementation before independent challenge and coordinator approval.

### Scope and diagnosis

The relevant execution path is:

- [`State.gate`](C:/Users/burha/.codex/worktrees/owner-led-workflow/agents-lab/scripts/ticket_workflow.py:325) rejects delivered tickets before considering another operation.
- [`replay`](C:/Users/burha/.codex/worktrees/owner-led-workflow/agents-lab/scripts/ticket_workflow.py:382) rejects every event following delivery.
- [`extension`](C:/Users/burha/.codex/worktrees/owner-led-workflow/agents-lab/scripts/ticket_workflow.py:751) adds finite allowances only before delivery.
- [`phase_start`](C:/Users/burha/.codex/worktrees/owner-led-workflow/agents-lab/scripts/ticket_workflow.py:540) already enforces the approved implementation owner and independent reviewers.
- [`append`](C:/Users/burha/.codex/worktrees/owner-led-workflow/agents-lab/scripts/ticket_workflow.py:954) checks content before constructing the temporary file but does not reread the input files immediately before replacement.
- [`check_pr`](C:/Users/burha/.codex/worktrees/owner-led-workflow/agents-lab/scripts/ticket_workflow.py:1045) requires the recorded delivery binding to equal the current PR identity and content.

Thus ownership does not need another routing framework. The missing pieces are a reusable continuation, clear current-versus-historical certification, policy dispatch that preserves old replay, and transactional input rechecks.

Only development workflow tooling, tests, instruction bodies, templates, validators and documentation are affected. Application interfaces and graph/checkpoint JSON impact: **none**. Provider, database, financial, authentication, global configuration, role registration/model/access and CI privilege changes remain excluded. No Issue23/83/84 ledger, PR85 certificate, stopped attempt or local recovery work is imported or resumed.

### Policy and JSON contract

Retain outer ledger schema `1`, strict parsing and the existing exact event envelope `{type, at, data}`.

Use two policy names:

- `timed-v1`: every existing initialization without a `policy` field.
- `owner-led-v1`: a new initialization with the additional exact field `"policy": "owner-led-v1"`.

Unknown policy names or any other additional initialization fields fail closed. New templates select `owner-led-v1`; existing files are not rewritten.

Retain the complete existing capsule schema, five counted phases and default limits:

```json
{
  "implementation": 1,
  "initial_review": 1,
  "remediation": 1,
  "final_review": 1,
  "design_reset": 1
}
```

New policy keeps elapsed-time accumulation, pause/resume, conservative charges and recorded timestamps as audit information. Time does not reject dispatch, resume, delivery or continuation under this policy. Do not simulate this by adding enormous time budgets or resetting elapsed values.

Add exactly these two event types.

`policy_transition`:

```json
{
  "type": "policy_transition",
  "at": "UTC seconds timestamp",
  "data": {
    "policy": "owner-led-v1",
    "authority": {
      "kind": "user",
      "name": "nonempty bounded text",
      "evidence": "concrete authorization reference"
    },
    "capsule": {
      "id": "current id",
      "generation": 1,
      "digest": "current capsule digest"
    },
    "reason": "nonempty bounded text"
  }
}
```

Requirements:

1. Current policy is `timed-v1`, with a complete capsule matching the reference.
2. No active or suspended phase.
3. The ticket has neither a predecessor nor any split event.
4. It may be delivered, stopped or over the legacy time allowance. The prefix is first replayed under its original semantics.
5. It grants **zero** phase slots and changes no count, limit, capsule, owner, blocker, design/challenge approval, evidence, certification or delivery binding.
6. It switches only subsequent event interpretation and time enforcement. It is one-way and cannot repeat.
7. Authority must explicitly authorize this policy change. A user authorization that established this very policy-change ticket may support its transition; this is not an additional count grant. Record its normalized identity so it cannot subsequently be reused to grant allowances.

`continuation`:

```json
{
  "type": "continuation",
  "at": "UTC seconds timestamp",
  "data": {
    "authority": {
      "kind": "user",
      "name": "nonempty bounded text",
      "evidence": "new concrete finite continuation authorization"
    },
    "capsule": {
      "id": "current id",
      "generation": 1,
      "digest": "current capsule digest"
    },
    "counts": {
      "implementation": 0,
      "initial_review": 0,
      "remediation": 1,
      "final_review": 1,
      "design_reset": 0
    },
    "reason": "same-scope repair and its concrete failure or changed-content reason"
  }
}
```

Requirements:

1. Current policy is `owner-led-v1`; capsule reference is current.
2. A successful implementation has previously completed. Continuation is the post-implementation recovery path, including after review or delivery. Initial implementation/design recovery continues to use finite `extension`.
3. No active/suspended phase and no split/predecessor history.
4. The full count map uses the existing bounded strict integers: no booleans, negatives, omitted keys or unknown keys.
5. `remediation` delta must be positive. If independent review is required, or any initial/final review has ever been reserved, `final_review` delta must also be positive. Other deltas may be zero or explicit positive finite values.
6. Add the deltas to lifetime limits; never change consumed counts.
7. Keep the approved owner and current design/challenge/approval unchanged. Continuation cannot repair a missing or failed design gate.
8. Preserve unresolved blockers. Continuation does not resolve findings.
9. Clear **current** delivery eligibility, verification, acceptance, successful review and their content references. Clear the current failed-final stop only because this event supplies explicitly authorized repair/review allowances.
10. Mark a new repair as required and clear current `remediated` success. Do not fabricate an initial-review failure event.
11. The next write work is ordinary `remediation` by the existing approved owner, followed by fresh verification/acceptance and, when required, `final_review`.
12. Preserve every prior delivery binding in order. Later delivery must use the original repository and PR number.

A continuation is a finite grant, not a design reset and not a new ticket generation.

### Authority identity

For new-policy allowance grants, normalize evidence with Unicode NFKC, whitespace collapse and case folding. Display names do not participate in identity.

Maintain a consumed-authorization set derived from:

- Capsule user-authorization evidence, including earlier capsule records.
- Every historical extension authorization, renormalized when transitioning.
- Policy-transition authorization.
- Every new-policy extension and continuation authorization.

New-policy `extension` and `continuation` reject an identity already in that set. Do not reject a legacy prefix because two historical strings collapse under the stronger normalization; seed the set conservatively and prohibit their future reuse.

The transition itself grants no counts and may cite the capsule’s existing explicit policy-change authorization. It must never make that authorization available for a later count grant. This distinction applies generically, with no user-, ticket- or message-specific exception.

Under `owner-led-v1`, existing `extension` retains its strict existing shape but requires `seconds == 0` and at least one positive count delta. It remains a non-delivered extension mechanism. Preserve its existing requirement to grant both remediation and final review when clearing a failed-final stop, and invalidate current certification in that case. A delivered ticket uses `continuation`, not `extension`.

Static validation cannot establish that text really represents a human decision. The coordinator remains responsible for truthful authorization references.

### Ownership and phase transitions

Routine mechanical/ordinary work uses one approved owner for capsule preparation, implementation, self-review, verification and any allowed same-scope repair. These activities can occur in one session; recording sequential ledger phases does not require fresh agents.

Consequential contracts retain separate architect, independent design challenge, coordinator approval and independent code review. High-risk/disputed implementation requires independent code review; if the contract itself is consequential, classify it accordingly and require the consequential design gates.

Preserve all existing role/model/access pins and explicit specialist escalation rules. A handoff is available for concrete necessity, not the default response to findings.

For new policy:

- Remediation requires a completed implementation and an actual initial-review failure, unresolved blocker, or continuation’s pending repair.
- Starting remediation consumes its lifetime slot and clears current verification, acceptance, review and remediation success.
- Failed remediation cannot retain an earlier `remediated=True`.
- A required review starts only after successful current verification and acceptance bind the same content as the review reservation.
- Initial review cannot substitute for the final review required after remediation.
- Final review requires successful remediation and fresh matching verification/acceptance.
- Any failed final review stops further work until an explicit finite grant; existing unresolved blockers still prevent delivery.
- Reviewer independence excludes **all** recorded implementation, remediation and verification authors across the entire history, including previous deliveries and owner handoffs.
- Same-scope findings do not invalidate the approved design and do not automatically require a new architect.
- Genuine contract ambiguity may reserve the existing bounded `design_reset`; scope expansion requires separate authorized work. For new-policy `design_reset` reservations, add exact fields `criterion` and `reason`: the criterion must be a frozen invariant/acceptance ID, and the reason must identify the contract ambiguity. This records why architecture work is necessary without granting any new allowance.
- Initial design remains one-time, challenge remains bound to that completed design/generation, and the existing reset counter limits further architecture attempts.

A failed verification must remain a failed verification. To repair outside the implementation phase, record its concrete frozen-criterion blocker and use the existing bounded remediation allowance; do not silently edit inside a completed verification phase.

### Historical and current delivery state

Keep historical delivery events immutable. Maintain a derived ordered `delivery_history` and the original PR identity.

`delivery_binding` remains the most recently recorded binding; `delivered` means that binding is currently eligible for delivery. During continuation, retain the binding/history but set `delivered=False`. Consequently `check_pr` cannot reuse the old binding, even if the repository happens to return to the same content.

A new `delivery` event uses the existing schema and ordinary gate:

- Current verification, acceptance and required review agree.
- Current repository content agrees.
- No active/suspended phase, unresolved blocker, failed-final stop or pending repair.
- Repository and PR number equal the first historical delivery’s identity, if one exists.

The event appends another historical binding and sets current delivered state. Direct consecutive deliveries without continuation remain invalid. Later source changes cannot be certified by an unchanged delivered record.

No new exclusion is added to `content_digest`.

### Legacy and split behavior

All event streams without new-policy initialization or explicit transition retain the existing `timed-v1` validation and outcomes, including timed pauses, exhaustion, extension, delivered-terminal handling and split allocations.

Do not retrofit the new semantics into legacy events before a transition.

For this slice, reject:

- `split` under `owner-led-v1`.
- New-policy initialization with a non-null predecessor.
- Transition of a ticket with a predecessor or any prior split.
- Continuation on any split/predecessor ticket.

This prevents duplicated legacy counter allowances from entering the new policy. Existing timed split histories and successors continue to replay unchanged. No new cycle split pool is introduced or implied.

Status must identify the policy. New-policy status reports actual lifetime counts, limits and `remaining_counts = limits - counts`, elapsed audit seconds, `remaining_seconds: null`, current certification flags, pending repair, current binding and historical bindings. Legacy remaining-time calculations retain their original meaning. A retired legacy split must be labeled retired; if an allocation remainder is displayed, use the actual remaining split pool, including zero, rather than recomputing an unsplit allowance.

### Atomic append and input boundaries

Keep the existing one-writer lock and atomic replace. Strengthen the implementation for both policy paths without changing legacy replay semantics.

The API may preserve its current positional arguments and add an optional `source_path` for a CLI event file. The CLI must supply that path.

Within the lock:

1. Strictly parse and defensively copy the event. If `source_path` is supplied, read its actual bytes and require its parsed event to equal the supplied event.
2. Capture the current ledger-file set and exact bytes, including the current target’s absence when initializing. Read and validate the candidate using that snapshot.
3. Capture current repository content. Apply existing content-equality rules for review/verification reservations, successful outcomes, acceptance and delivery.
4. Write and fsync the candidate temporary file.
5. Immediately before replacement, reread the actual event source bytes when present, the actual ledger-file set/bytes, candidate temporary bytes and repository content. Reject any difference from the transaction’s snapshots or expected candidate.
6. Only then call `os.replace`; clean temporary/lock files on success or failure.

There is no separate evidence journal. Evidence is inline in the strict event; references to remote evidence are recorded references, not secretly mutable transaction inputs. Do not claim that this authenticates human evidence or atomically locks every arbitrary external editor. The workspace must be quiescent during certification/publication, and the transaction performs a final real filesystem check immediately before replacement.

Tests must modify a **file on disk** after the initial snapshot and before the final checks. Mutating a Python dictionary alone does not demonstrate this requirement.

### Acceptance and focused tests

Map tests to the frozen IDs rather than adding new scope:

- **AC86OWNER / I86OWNER:** ordinary single-owner complete flow; consequential missing design/challenge/approval rejected; same-owner remediation succeeds without reset; reviewer from any historical write/verification session rejected; explicit legitimate handoff remains possible.
- **AC86BOUND / I86BOUND:** elapsed time beyond 120 minutes does not exhaust a new-policy ticket; legacy boundary still does; starts reserve counts; pause/resume preserves reservations; failed/open attempts retain counts; grants add limits only; zero/negative/bool/unknown/missing deltas rejected.
- **AC86CONTINUE / I86HISTORY:** deliver, continue, repair, reverify, independently review and redeliver on the same PR; every prefix and earlier binding remains exact. Test a second continuation using another explicit finite authorization. Duplicate/normalized authorization and direct delivered reopen fail.
- **AC86GATES / I86CONTENT:** continuation alone cannot deliver; old acceptance/review/verification cannot be reused; blocker remains until successful subsequent remediation; failed remediation/final review does not reuse old success; alternate PR/repository/primary issue rejected.
- **AC86HISTORY:** existing repository ledgers and legacy fixtures retain results; explicit unsplit transition retains counts, limits, elapsed audit, capsule, owner, blockers and bindings; all unsupported split/transition combinations fail while legacy split fixtures remain valid.
- **AC86VERIFY / I86ATOMIC:** CLI event source, current ledger, another ledger, ledger-file addition/deletion, candidate temporary file and source content changed on disk before replace each cause rejection without overwriting the competing change. Lock and malformed input failures also leave the target intact.
- **AC86VERIFY:** tests construct their own immutable fixtures. No fixture assumes that the repository’s live issue ledger has a fixed current event count.
- **AC86VERIFY:** an end-to-end temporary repository writes a real delivered ledger, runs validation/current PR binding, continues and writes the next delivery, then repeats those checks against the actual saved final file.

Run the frozen capsule’s required offline/static gates. Tests must assert the intended rejection reason where an unrelated earlier failure could otherwise mask missing coverage.

### Publication and this ticket’s own transition

Issue86 uses the normal machinery:

1. Complete this design, independent challenge and recorded coordinator approval under its already reserved legacy phases.
2. Reserve/start its implementation through the current gate.
3. The implementation owner adds the generic policy support and passes focused self-checks.
4. End implementation truthfully.
5. Append the standard `policy_transition` using the user’s recorded Issue86 policy-change authorization.
6. Complete documentation before freezing content.
7. Reserve verification and independent review using ordinary events.
8. Append ordinary delivery after the ordinary delivery check passes.

No Issue86 bootstrap branch or hardcoded digest/issue-number exception is permitted.

Before pushing, run publication checks against the **actual saved delivered ledger**, including focused end-to-end publication tests, ledger validation, immutable-prefix comparison, and exact current PR/content binding. These are read-only publication checks on already verified content; they do not require a recursive certificate or reopen a phase. Record their command evidence in the operational results and PR summary.

A failure at this point is reported as a publication failure. Do not push, quietly alter source or invent a successful record. Any repair must use remaining authorized ordinary remediation where the state allows it, or a later explicitly authorized standard continuation.

### Documentation and risks

Add ADR0033, preserving accepted ADR history. It supersedes only active rules concerning time exhaustion, automatic return to design, post-delivery terminality and the new policy’s unsupported split handling. Explain the legacy boundary precisely.

Update AGENTS, CONTRIBUTING, role instruction bodies, workflow README, templates, static validator markers and the active iteration. Keep registrations, models, efforts and access unchanged.

Principal risks are version-dispatch leakage into legacy replay, stale success flags, approval-key reuse, silently transferable PR identity, filesystem checks performed only against cached objects, and tests that depend on the live ledger’s changing length. The test matrix above targets each risk.

This is a finite, owner-led recovery workflow. It preserves independent checks for consequential work without requiring a new design merely because implementation needs a same-scope repair.

DESIGN_READY
