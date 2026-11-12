# Issue 106: early decomposition decision

## Authorization and owner

The user explicitly approved starting [Issue 106](https://github.com/beagle1903/agentic-etf-advisor/issues/106) on 2026-11-12. The [issue start record](https://github.com/beagle1903/agentic-etf-advisor/issues/106#issuecomment-6832806262) gives the scope, acceptance and verification. This is ordinary coordinator documentation within the current [ADR 0049 working agreement](../architecture/decisions/0049-prospective-working-agreement.md). The owner is `implementation_worker` / `gpt-6-sol` / medium: one session for the narrow edit, self-review and verification. The issue's older ledger and allowance language describes superseded prospective process; it is historical context, not a requirement to start a new ledger or obtain a grant.

## Scope and boundaries

Add an early decision rule to `AGENTS.md`, `CONTRIBUTING.md` and the existing coordinator-arbitration template. A coordinator considers decomposition before committing to a broad implementation and again when concrete new evidence shows repeated contract uncertainty or growing acceptance. The decision distinguishes same-scope repair, a proposal for independently deliverable sub-issues, and an explicit stop. Use GitHub's native parent/sub-issue and blocked-by links, execute proposed children one at a time, and account for every original acceptance requirement before claiming parent completion.

Do not automatically split or create issues, add a planning prerequisite or management engine, change pinned roles, alter active Issue 24 work, or edit product, finance, saved-state, source-provider, ledger engine or JSON. Accepted ADRs and historical outcomes remain unchanged. The legacy split and arbitration details in [ADR 0034](../architecture/decisions/0034-bounded-coordinator-arbitration.md) and [ADR 0036](../architecture/decisions/0036-owner-led-conserved-split-lineage.md) remain history; this change adds guidance under ADR 0049, not a new authority or technical contract.

Affected interfaces: operating guidance, contributor guidance and one documentation template. Runtime, external, financial and persistence interfaces: none. JSON or graph state impact: none.

## Acceptance and verification

- I106-1: Historical failures, exhausted attempts and PR bindings remain honestly described; a new issue number cannot relabel a failed original criterion as passed.
- I106-2: Same-scope defects stay with the accountable owner. An inseparable consequential invariant stays together and uses the current separate design/approval gate.
- AC106-1: The rule gives observable loop indicators and one accountable choice of narrow repair, independently deliverable proposal, or stop without requiring routine planning.
- AC106-2: Examples cover an unstarted broad parent, a started issue with remaining historical allowances, a failed or exhausted historical issue, a normal single-scope defect and an inseparable consequential contract.
- AC106-3: A proposed split maps every original requirement to a child, an authorized deferral or an explicit blocker; child completion alone cannot close the parent.
- AC106-4: Guidance uses native parent/sub-issue and blocked-by links, one-at-a-time execution and independently reviewable PR outcomes. It grants no automatic split, authority, counter reset, owner replacement or bypass of current design/review gates.
- AC106-5: The existing template supports an evidence-backed accountable decision under ADR 0049; proportionate checks validate links, scenario coverage, role configuration and the final diff. No prose-marker test or change to historical replay is needed.

Verification plan: manually walk the five AC106-2 scenarios through the written rule and template; check changed Markdown relative links; run role configuration validation and `git diff --check`; run any further repository gate justified by the final changed paths. Record outcomes and remaining limitations below. If the proposed text would change a consequential product or architecture contract, stop and return it for separate design advice and coordinator approval. If an original issue criterion cannot be reconciled with ADR 0049, report the concrete choice rather than silently changing governance.

## Implementation evidence

The owner added the rule to `AGENTS.md`, expanded its practical application in
`CONTRIBUTING.md`, and adapted the existing coordinator template for ADR 0049. A
manual walkthrough against AC106-2 reached these dispositions:

| Scenario | Observed guidance |
| --- | --- |
| Broad unstarted parent | Propose independently useful children, native links and complete parent coverage before implementation. |
| Started historical ticket with remaining allowances | Preserve actual outcomes and use only its applicable authorized disposition; GitHub links do not grant or reset attempts. |
| Failed or exhausted historical ticket | Keep failure visible; a newly authorized scope cannot relabel old acceptance. |
| Ordinary single-scope defect | Same owner repairs and verifies without a split. |
| Inseparable consequential invariant | Keep one deliverable and obtain separate design advice and coordinator approval. |

The checks completed on 2026-11-12 UTC. The changed-document relative-link check found no missing target. The role configuration
validator passed. `git diff --check`, Ruff lint, Ruff format, mypy (69 source files), the full
service-free pytest run (100%, exit 0 with optional skips), `uv build`, and
`docker compose config --quiet` passed on the isolated worktree. No real-store or live-source
claims are made for this documentation-only change. Self-review found no changed runtime,
ledger or role configuration paths. The issue's original AC5 asked for focused static
checks protecting prose. ADR 0049 narrowed static validation to role configuration, so
this prospective implementation uses the approved scenario and link checks for the rule
instead of adding a marker-enforcing test. Substantive coordination remains issue/PR
evidence, which static text checks cannot prove.
