# Bounded ticket workflow governance

Status: DESIGN_READY; coordinator approved 2026-09-26.

Issue: https://github.com/beagle1903/agentic-etf-advisor/issues/73
Approved complete capsule: https://github.com/beagle1903/agentic-etf-advisor/issues/73#issuecomment-5843156904

Classification: consequential development governance. Architect session
`/root/bounded_workflow_design` (design_architect, gpt-6-astra/high/read-only);
independent challenge `/root/bounded_workflow_challenge` (code_reviewer,
gpt-6-sol/high/read-only); approving coordinator `/root`. Implementation owner
`/root/bounded_workflow_implementation` (implementation_worker, gpt-6-sol/medium).
User authorization: "ok apply it. then we will talk about how to wrap current ticket up."

Scope: AGENTS, six instruction bodies, contribution and issue/PR guidance, strict
append-only development ledger, stdlib CLI, CI and validator, focused tests, ADR0026.
Non-goals: Issue70, product, financial contracts, providers, databases, global settings,
role models/efforts/access/registration, automatic orchestration.
Invariants: finite ticket lifetime counters; frozen scope/invariants/ACs; default
120 active minutes; every phase charged; reserve slots before dispatch; one initial
review, one remediation, one final review, one reset; no implicit replenishment.
Consequential challenge and coordinator approval precede writes. Serious blockers
always deny delivery. Explicit finite user extensions only. Split successors inherit
consumed counters and explicitly allocated remainder; sibling allocations cannot
exceed it. One writer validates before atomic append; malformed history fails closed.
Interfaces: workflow CLI, JSON ledger, CI, templates. Application interfaces and
JSON/state impact: none.
Acceptance AC1: finite replay and phase/time gates reject invalid transitions.
Acceptance AC2: clean delivery requires complete frozen ACs, verification and review.
Acceptance AC3: split lineage, append-only history and primary PR binding validated.
Acceptance AC4: existing role/config boundaries and static fixtures retained.
Verification: focused tests and standard offline/static/evaluation/build/Compose gates;
no live stores. Documentation: ADR0026, governance evidence, operating instructions.
Risks: recorded authority is not cryptographic; no runtime kill switch; coordinator
must truthfully record and stop agents. Escalation: scope/contract ambiguity or budget
exhaustion stops work, no automatic reset.

## Adoption evidence

Tools did not exist during initial design/challenge. The approved adoption explicitly
charges the complete continuous interval from Issue73 creation (2026-09-26T04:23:34Z)
to implementation bootstrap. No finer phase timestamps were captured or invented.
Known completed architect and independent challenge sessions reserve their slots.
This ledger is governance metadata outside application graph/checkpoint state.

The bootstrap tooling gap was explicitly charged before the engine gained automatic
inter-phase accounting. That conservative extra charge remains as additional reserve;
history is not rewritten or subtracted. All elapsed-time figures therefore include
this small overcharge. Pauses require explicit records; no offline interval is inferred.

## Implementation and verification (2026-09-26)

Owner completed the approved workflow-only implementation and self-review on the
uncommitted branch `codex/bounded-ticket-workflow`, baseline `1badb20`.
Role models, efforts, sandbox modes, registrations, product source and dashboard tests
remain unchanged. Issue70 worktree was not read or modified by implementation.

- Focused replay/CLI/CI binding suite: 52 passed.
- Original static workflow fixtures: all 234 passed; four added static CI/ledger checks passed.
- Ruff lint and format (137 Python files), workflow validator, strict mypy (46 source
  files), retrieval evaluation, explanation evaluation (14/14), source/wheel build,
  Docker Compose configuration and whitespace checks passed.
- Complete offline suite with locked extras: 1,079 passed, 3 skipped, one failure in
  374.47 seconds. The unchanged Streamlit policy-review AppTest exceeded its explicit
  10-second startup timeout; its isolated repeat failed the same way in 24.50 seconds.
- Commands: `uv run pytest`, then only
  `uv run pytest tests/test_dashboard_revision_controls.py::test_streamlit_policy_review_renders_revision_lifecycle_and_typed_controls`.
- No product fixes, timeout relaxation, broad rerun or live-store tests were performed.
  The full offline gate remains failed; independent review and delivery are pending.

Claim boundaries: static/replay behavior is tested; hosted CI, runtime agent/session
provenance, authority authenticity and physical agent interruption are unverified.
Approval references are evidence records, not cryptographic authorization. The full
verification limitation blocks delivery and cannot be hidden by phase exhaustion.

## One consolidated remediation (R1-R7)

The initial independent review identified seven bounded governance defects. The sole
remediation now tracks all write authors, clears failed-reset design state, restricts
adoption to the exact approved Issue73 historical prefix, binds original delivery PR
and repository content, deduplicates normalized approval evidence, binds complete
capsule definitions/generations, and enforces classified approved ownership with
explicit specialist escalation. No new counters, budgets, resets or product fixes
were introduced. The historical prefix digest remains
`ad92fa4555aa4162c9cefcfce7f6c2d233bdc318748b0b6b6b04bff208ae2779`.

The coordinator reproduced the unchanged Streamlit case successfully first on a clean
main archive and then using this worktree's `.venv\Scripts\python.exe -m pytest`
for that exact case, without product/test edits. Initial startup timeouts remain in
the historical record; this targeted recovery plus the other 1,079 passing offline
cases closes that transient verification gap. Only affected workflow/static gates
are repeated for remediation; final independent review remains pending.

Remediation verification: combined replay/CLI/CI and static workflow suite passed
**312 tests** in 77.24 seconds (74 replay/CLI tests plus 238 static fixtures). Ruff
lint, format check (137 Python files), standalone validator and whitespace checks
passed. Self-review checked all seven regression scenarios, strict capsule fields,
boolean generation rejection, original PR/content reruns, actual-content append
checks, classified mechanical ownership and explicit specialist handoff. The exact
18-event historical prefix is unchanged, and all six role settings/registrations
and application source/dependencies remain unchanged. No further implementation
cycle is authorized after the final independent review without explicit user choice.
