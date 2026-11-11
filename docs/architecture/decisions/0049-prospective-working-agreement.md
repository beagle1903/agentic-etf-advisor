# ADR 0049: Prospective issue and PR working agreement

- Status: Accepted for Issue 143
- Date: 2026-11-11
- Supersedes: Earlier mandatory process gates for prospective work only. Historical ADRs, ledgers, failed outcomes and PR bindings remain unchanged.

## Context

The finite ticket workflow added phase reservations, elapsed audit budgets, allowance grants, content certificates and delivery bindings to ordinary repository changes. Repeated same-scope repair and review could require further process changes before a concrete defect was addressed. The user approved a short agreement and explicitly asked to remove that recurring loop in [Issue 143](https://github.com/beagle1903/agentic-etf-advisor/issues/143#issuecomment-6801153109).

## Decision

An issue or PR records authorized scope, non-goals, observable acceptance criteria, an accountable owner and verification. One owner completes implementation, focused tests, self-review and same-scope fixes. Consequential financial, identity, security, persistence/replay or architecture contracts receive separate read-only design advice and coordinator approval before implementation. Consequential, high-risk or disputed output receives independent code review. Review findings identify concrete failures against the agreement; the coordinator resolves repeated disputes with one evidence-backed decision and closure condition. Unresolved material defects stop the affected delivery. Material scope changes return to the user.

Prospective work requires no ticket ledger, phase reservation, elapsed-time budget, finite-attempt grant, design generation, content certificate or delivery binding. The six project roles, pinned model/effort/access, explicit relative registrations and ADR 0018 configuration restrictions remain. The static validator checks those structural settings alone. CI retains locked installation, role validation, Ruff and service-free pytest. Historical ticket tooling and records remain available for inspection but cannot be treated as a current gate or relabeled as successful. Exhaustion on an old ticket does not prohibit normal use of a merged application; a new scenario does not retroactively satisfy the old ticket's acceptance.

## Consequences and limits

The agreement removes process enforcement, not product safeguards. Existing financial rules, evidence freshness/provenance, JSON checkpoint/replay behavior, external financial write approval and the opt-in real-store gate for affected runtime contracts remain. Static configuration validation cannot prove live role provenance or human authorization. Issue and PR review must supply the substantive evidence.
