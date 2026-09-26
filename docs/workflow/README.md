# Finite development ledger

AGENTS and ADR 0026 define the policy. This directory stores development governance,
outside application graph state. One issue has one canonical `tickets/issue-N.json`. Future initialization requires a complete frozen
capsule with actual definitions (not IDs alone), pinned approved owner and named user
authorization. Bootstrap adoption is restricted to the exact approved Issue73 prefix;
future adoption cannot invent past phases.
Templates live under `templates/`, never under the live ticket directory.

Use UTC seconds timestamps and meaningful evidence references. Fill the initialization
template with the actual repository, issue, classification, frozen contract IDs and
named coordinator authorization. Consequential classification requires review and a
separate completed architect phase, independent challenge and approved design capsule.

```powershell
uv run python scripts/ticket_workflow.py append --issue N --event initialize.json
uv run python scripts/ticket_workflow.py check --issue N --phase design
uv run python scripts/ticket_workflow.py append --issue N --event phase-start.json
```

Dispatch the selected role only after a successful check and durable reservation.
Record the end, then gate the next sequential phase. Role files retain their pinned
settings. All events have exactly `type`, `at`, `data`; unknown fields fail closed.

| Event | Data fields |
|---|---|
| `initialize` | See template; default budget 7200 seconds and one of each counted phase. |
| `phase_start` | `phase`, `session`, `role`, `capsule`; review/verification also require `content` SHA256. |
| `phase_end` | `session`, `outcome` (`pass`, `fail`, `interrupted`), `evidence` |
| `pause` | Same as end, with `interrupted`; preserves exact reserved session. |
| `phase_resume` | `session`; resumes the interrupted phase without another slot. |
| `coordination_pause`, `coordination_resume` | `authority` (coordinator), `evidence`; explicit between-phase offline interval. |
| `design_ready` | `authority` (coordinator), `evidence`, exact current `capsule` reference. |
| `blocker` | `id`, `criterion` (frozen AC/invariant ID), `scenario`, `evidence` |
| `resolve` | `id`, `evidence`; requires a successful remediation after the finding. |
| `acceptance` | `ids` (all frozen ACs), `evidence`, `capsule`, `content` SHA256 |
| `charge` | `authority` (coordinator), positive additional `seconds`, `evidence`; conservative extra charge only. |
| `extension` | `authority` (user), nonnegative `seconds`, full `counts` delta map, `reason`; at least one positive delta. |
| `split` | `authority` (user), `successor` issue, positive `seconds`, `reason` |
| `delivery` | `evidence`, original `pr` number, `repo`, `capsule`, `content` SHA256; terminal after the gate. |
| `capsule_update` | `authority`, complete `capsule`; only during a reserved reset, frozen scope/AC/invariant definitions unchanged. |
| `owner_handoff` | `authority`, pinned `owner`, current `capsule`, `reason`, `escalation` (required for a specialist role change); fresh session. |
| `capsule_binding` | Only approved Issue73 migration: `authority`, exact `prefix_digest`, complete `capsule`; history remains untouched. |

Authority objects always contain `kind`, `name`, `evidence`. They record evidence,
not cryptographic approval. The coordinator checks that it is legitimate. Extension
evidence is single-use, normalized for whitespace independently of display name.
Counted phases: `implementation`, `initial_review`, `remediation`, `final_review`,
`design_reset`. Other charged phases: `planning`, `design`, `challenge`, `verification`.
Clock accounting includes inter-phase coordination until an explicit pause. An open
crashed phase consumes through now; closing it late never removes elapsed time.
The `--now` override supports deterministic tests; do not backdate operational checks.

```powershell
uv run python scripts/ticket_workflow.py check --issue N --phase delivery
uv run python scripts/ticket_workflow.py validate
```

Delivery requires complete acceptance, successful verification, clean required review
and no unresolved blocker. Phase exhaustion prevents another phase, while a clean final
review may still deliver within the time budget. Failed final review stops work until a
finite explicit user extension grants both remediation and final-review slots. Neither
reviewer findings nor a design reset grant authority to extend a budget or change scope.

Splitting retires the predecessor. Each explicit user-approved allocation records
remaining time and consumed counts. The successor initializes with `predecessor` equal
to `{ "issue": N, "digest": "sha256 of predecessor ledger prefix" }`; validate with
the predecessor ledger present. No automatic fresh implementation slot is granted.
Sibling allocations share the original remainder. An extension is a separately approved
finite choice before splitting, not an automatic successor budget.

CI fetches the current PR body and checks the event head against the current head.
Exactly one `Primary issue: #N` line binds the PR; a changed ledger must include that
primary issue. `edited` events rerun checks. Existing merge-base events must remain an
identical prefix; deletion fails. Future issues (created at/after 2026-09-26T04:23:34Z)
require a ledger. Historical issues/PRs are exempt until adopted, but cannot serve as a
false primary reference for changed future ledgers. Static checks cannot authenticate
approval, stop a running agent, or detect every uncommitted local history rewrite.

On BLOCKED_FOR_DECISION preserve the work and report the remaining choices: reduce
scope, split with inherited limits, replace the approach, abandon, or request a finite
extension. Do not restart agents automatically. This guarantees a finite attempt,
not a defect-free delivery or successful completion.

## Capsule and content references

`uv run python scripts/ticket_workflow.py status --issue N` reports the current capsule
reference, approved owner, counters, remaining seconds and repository content digest.
Every future phase uses `{id, generation, digest}`. A reset advances the generation,
clears the successful design/challenge/approval, and requires a successful fresh design.
Only a reserved active reset may revise capsule details; frozen scope, non-goals,
invariant/AC definitions, classification and initial owner cannot silently change.
Explicit owner handoffs record fresh sessions and concrete specialist escalation.

Store event files outside the repository (for example in the OS temporary directory).
Review/verification reservations and successful outcomes are checked against actual
repository content by append. Acceptance and delivery carry that same content digest.
Content covers Git tracked and unignored untracked files, canonical LF text and file
modes. The exact exclusions are this issue's `docs/workflow/tickets/issue-N.json` and
temporary `*.lock`/`*.tmp` files within that tickets directory. Other ticket ledgers,
source, tests, templates and governance docs are included. CI hashes the current PR
head tree, not a queued obsolete event. Delivered state binds original repo/PR number
and content; a different PR or later content cannot reuse it. Original unchanged CI
reruns remain valid. Finish reviewable documentation before final verification/review;
record later outcomes in the excluded ledger rather than editing reviewed content.
