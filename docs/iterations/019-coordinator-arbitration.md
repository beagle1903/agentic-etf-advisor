# Iteration 019: Bounded coordinator arbitration

Issue #88 implements the separately designed and challenged workflow rule in
ADR 0034. The frozen capsule is `issue-88-bounded-coordinator-arbitration`,
generation 1, digest
`5e7df9d37f8cf3d614317a4848a7bd9e83358758610a603647cd3bd9b6da8477`.
User authorization is the 2026-10-07 `continue` in chat
`01a11563-1a1b-7be2-ad70-c7d4a60316f2`. Separate read-only architect design,
independent challenge and coordinator approval preceded the reserved implementation
by `/root/arbitration_owner` (`implementation_worker`, `gpt-6-sol`, medium).
The [design handoff](019-coordinator-arbitration-design.md) and
`docs/workflow/tickets/issue-88.json` carry the gate evidence.

Scope S1 and I1–I4/AC1–AC4: coordinator instructions, role instruction return
boundaries, reusable arbitration record, static guardrails and focused tests.
Product behavior, graph/checkpoint JSON, ledger schema and replay, role settings,
prior ticket histories, Issue #23/#83/#84 and PR #85 are outside this ticket.

Implementation self-check before certification: the focused static and ticket
workflow suite completed with exit 0 (446 cases at that run); the subsequent
arbitration selection, including eleven final governance-document negative cases,
completed with exit 0 (113 cases). The positive fixture invokes the validator
from outside its repository root. Negative fixtures independently weaken fourteen
role clauses across six roles and sixteen template clauses, plus the documented
missing/unreadable template paths. Both workflow validators, changed-file Ruff
lint and format checks, and `git diff --check` passed. A parsed TOML comparison
against `HEAD` confirmed all six roles' non-instruction fields unchanged. Each
role-file diff has fourteen added instruction lines and zero removed lines; Git
shows no modification to prior ledger files, accepted ADRs, `.codex/config.toml`,
`scripts/ticket_workflow.py`, or CI. Self-review found no remaining criterion-backed
failure scenario in the implemented scope.

The coordinator records final content-bound verification and independent review
in the excluded Issue #88 ledger after the content is frozen. Static validation
cannot prove live coordinator behavior, human authority, or session independence.
