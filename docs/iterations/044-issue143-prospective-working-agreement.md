# Issue 143 prospective working agreement

## Authorization and ownership

The user approved the short agreement, corrected the recurring phase/allowance loop as the target of this work, and directed implementation. The [Issue 143 comment](https://github.com/beagle1903/agentic-etf-advisor/issues/143#issuecomment-6801153109) records the prospective transition exception. The selected owner is `implementation_worker` / `gpt-6-sol` / medium, for ordinary repository workflow implementation. A separate read-only `design_architect` handoff (`/root/issue143_scoped_architect`) produced a substantive DESIGN_READY recommendation; independent `/root/issue143_workflow_review` challenged it and passed. The coordinator approved that scoped design before this implementation. Earlier preconfigured architect attempts were blocked by stale session instructions and supplied advisory only; they are not represented as approved handoffs.

## Scope and non-goals

Adopt [ADR 0049](../architecture/decisions/0049-prospective-working-agreement.md) in active project guidance, issue/PR forms, CI and role configuration validation. Preserve historical ADRs, iterations, ledgers and the ticket engine. Do not change application source, financial eligibility, safety, market data, persistence/replay, graph JSON or external integrations. Do not alter the historical Issue 143 ledger; it remains uncommitted audit material.

## Invariants and interfaces

- W143-I1: Six named role registrations and their exact descriptions, relative paths, role filenames, model, effort and access remain pinned. ADR 0018 prohibited defaults and project overrides remain prohibited.
- W143-I2: Historical events and outcomes remain unchanged and cannot be claimed as prospective acceptance.
- W143-I3: Product and financial/data safeguards, including required real-store verification for affected runtime changes, remain.
- Affected interfaces: contributor guidance, issue/PR templates, role TOML instructions, validator CLI and CI workflow.
- JSON/state impact: none. Product/runtime interfaces: none.

## Acceptance and verification

- W143-AC1: Active guidance and forms are usable without a ledger, phase/time/allowance grant or content certificate, while preserving technical development gates.
- W143-AC2: The validator checks only structural TOML role/config contracts and runs from another cwd without docs or ledgers.
- W143-AC3: CI retains locked install, role validation, Ruff and pytest without the ticket CI gate or exclusive token/history requirements.
- W143-AC4: Workflow README labels historical tooling optional; existing ledger engine/tests and historical records remain. Two Issue 73 fixture reads are isolated from unrelated live ledgers without weakening their assertions.
- W143-AC5: No application source or state changes; new ADR and iteration record provenance, risks, non-goals and test evidence.

Focused tests cover malformed/missing/swapped/pinned role configuration, nonempty instructions, prohibited defaults and unrelated settings. Run validator, focused validator and historical ticket tests, Ruff lint/format, mypy, full default pytest, build, Compose config if available and diff check. External services and source calls are out of scope.

## Risks and escalation

Static checks cannot authenticate live sessions or approval; the issue and PR retain evidence. The prose agreement may leave a consequential contract ambiguity; return that to separate architecture advice and coordinator decision. A concrete acceptance failure requires owner repair and verification or an explicit stop. No finite phase grants or new certificates are introduced.

## Implementation evidence

The owner integrated the coordinator's AGENTS and six role instruction changes, then updated
CONTRIBUTING, the four issue forms, PR template, CI, workflow archive README, validator and
focused tests. The two Issue 73 historical tests now strict-load only their intended fixture.
The historical ticket engine and ledger files were not changed; the existing untracked Issue 143
ledger remains outside the proposed PR.

The validator CLI passed from the worktree. Focused validator and historical ticket tests passed
before the final nested-duplicate regression was added; the full suite below includes it.
`uv run ruff check .` passed; `uv run ruff format --check .` reported 265 files formatted;
`uv run mypy` reported no issues in 69 source files; `uv build`, `docker compose config --quiet`
and `git diff --check` passed. The latter printed only Windows line-ending conversion warnings.
The independent final diff review by `/root/issue143_workflow_review` reported PASS with no
actionable defect. That review is substantive advice against W143-AC1..5, not a native ticket
certificate or historical ledger event.

The full service-free CI run on reviewed commit
`330286dc58ec6f926d04ff8c80becbe0e0729d6e`
[passed](https://github.com/beagle1903/agentic-etf-advisor/actions/runs/43061429441):
1,704 passed and 83 skipped in 80.79 seconds. Locked install, role validation, Ruff lint and
format, and pytest all passed. The 83 skips are the suite's optional cases; no live-store or
market-data source verification is claimed. The duplicate local Windows `uv run pytest -q`
was intentionally interrupted after CI success at the observed 84% progress marker; it is
neither a local pass nor a test failure. No external services or market-data source calls were
launched locally; the real-store suite is not applicable to governance-only changes. Final PR
review remains for delivery.
