# ADR 0025: Route project Codex roles to the GPT-6 family

- Status: Accepted
- Date: 2026-09-25
- Supersedes: Earlier pinned model assignments and the permanent-Luna prohibition in ADRs 0017,
  0020, and 0022; all other workflow decisions remain in force.

## Context

The project uses six explicitly registered Codex roles with risk-based responsibilities, pinned
reasoning efforts, and read-only or workspace-write boundaries. The GPT-6 family now supplies a
matching tier for each existing responsibility. Keeping the previous GPT-5.6 assignments would
leave active role configuration and guidance behind the available model family, while changing
responsibilities or approval policy would exceed this migration's purpose.

## Decision

Pin the project roles as follows:

| Role | Model | Effort | Access |
| --- | --- | --- | --- |
| `planning_analyst` | `gpt-6-luna` | medium | read-only |
| `design_architect` | `gpt-6-astra` | high | read-only |
| `bounded_worker` | `gpt-6-luna` | medium | workspace-write |
| `implementation_worker` | `gpt-6-sol` | medium | workspace-write |
| `code_reviewer` | `gpt-6-sol` | high | read-only |
| `implementation_specialist` | `gpt-6-sol` | high | workspace-write |

Luna → Sol → Astra is only routing shorthand; the classification table remains
authoritative. Luna/low may still be selected explicitly for bounded read-only fact gathering,
but that separate exception cannot issue a design gate or implement a ticket.

Preserve every role description, responsibility, reasoning effort, sandbox boundary, sequential
handoff, approval gate, escalation rule, and reviewer non-authorization rule. Preserve ADR 0018's
compatibility policy: no generic model or effort default, project-level model override, default
role, concurrency scalar, `max_threads`, or `enabled` setting.

## Consequences

- Fresh sessions use the GPT-6 model matched to each registered role; existing sessions are not
  retroactively changed.
- Static validation enforces the complete authoritative table as well as each role TOML, reducing
  model/documentation drift.
- The implementation bootstrap necessarily uses the pre-migration routing. Repository validation
  cannot prove runtime model availability or actual live-session provenance.
- Product APIs, graph/checkpoint state, JSON schemas, providers, dependencies, financial behavior,
  and external-write boundaries are unchanged.
- ADRs 0017, 0018, 0020, 0022, and 0023 remain accepted history. Only their earlier pinned model
  assignments and the prohibition on permanent Luna roles are superseded.
