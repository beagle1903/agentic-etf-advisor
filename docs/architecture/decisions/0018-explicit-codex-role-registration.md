# ADR 0018: Explicit Codex role registration compatibility correction

- Status: Accepted
- Date: 2026-09-07
- Supersedes: Only ADR 0017 claims about unspecified-agent defaults and concurrency limits.

## Context

[PR #46 review](https://github.com/beagle1903/agentic-etf-advisor/pull/46#discussion_r3944812716)
reported that Codex CLI 0.144.0-alpha.4 rejected the scalar-only agents table during
`app-server --strict-config --stdio` with
`invalid type: boolean true, expected struct AgentRoleToml`, although the repository validator
passed. The coordinator recorded an approved
[DESIGN_READY handoff](https://github.com/beagle1903/agentic-etf-advisor/pull/46#issuecomment-5567363114).

## Decision

Register `agents.design_architect` and `agents.implementation_worker` explicitly in
`.codex/config.toml`, each with its exact role-file description and a `config_file` path relative
to that configuration file: `agents/design-architect.toml` and `agents/implementation-worker.toml`.
Keep the role contracts unchanged: `gpt-6-astra`/`high`/`read-only` for design and
`gpt-6-astra`/`medium`/`workspace-write` for implementation.

Repository compatibility policy removes and rejects `enabled`, `default_subagent_model`,
`default_subagent_reasoning_effort`, and `max_concurrent_threads_per_session` under `agents`.
It adds no `max_threads`, default role, or top-level model override. This is a repository policy
for the reviewed compatibility issue, not a claim about every Codex version's supported settings.

The coordinator selects the named roles and runs design followed by implementation sequentially.
The repository promises neither generic-agent defaults nor a two-thread runtime cap. All other
ADR 0017 decisions, including the recorded approval gate and escalation boundary, remain in force;
ADR 0017 is preserved as accepted history.

## Verification and limitations

The validator checks all registrations before loading their referenced TOML, resolves paths from
the project config independently of cwd, and checks exact role settings and documentation markers.
Isolated command fixtures cover the original false positive, registration and role-file damage,
contract drift, removed scalars, documentation markers, and execution from another directory.
This static check cannot establish the routing or provenance of a running agent session.

The local PATH CLI is `codex-cli 0.128.0`; the review's
`codex app-server --strict-config --stdio` command fails with
`unexpected argument '--strict-config' found` on this version. The alternative non-mutating
`codex features list` config-load check is blocked by unrelated user-global configuration:
`%USERPROFILE%\.codex\config.toml:5:16: unknown variant default, expected fast or flex`
in `service_tier`. The global configuration is not changed. Live CLI compatibility remains
unverified locally; the review's original CLI evidence is distinct from repository validation.
Application behavior, JSON graph state, and replaceable side-effect boundaries are unaffected.

Local remediation verification on 2026-09-07: focused validator tests passed (64); the full
offline suite passed (422 passed, 2 skipped). The workflow validator, Ruff lint and format check,
strict mypy (44 source files), `uv build`, `docker compose config --quiet`, and
`git diff --check` passed. CI for these uncommitted changes remains for coordinator delivery.
