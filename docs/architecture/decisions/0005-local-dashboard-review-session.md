# ADR 0005: Resume the exact local graph thread from the dashboard

- Status: Accepted
- Date: 2026-08-28

## Context

The workflow already pauses with a typed human-review interrupt, but the only presentation is
an auto-approving CLI demo. A local dashboard must show the workflow-owned payload and return a
human decision without duplicating finance policy or silently reconstructing graph state.

## Decision

Use Streamlit only as an optional presentation adapter. One browser session retains the compiled
graph, its in-memory checkpointer, thread configuration, and latest returned state. The dashboard
renders the exact interrupt payload and resumes that same thread with one of the interrupt's
allowlisted actions. Edit and reject decisions require explicit feedback.

The policy-only path remains the default and needs no network, provider, or retrieval service.
Source evidence and provider explanations are opt-in. Neo4j is closed after the initial draft;
the paused graph does not revisit retrieval during review finalization. Untrusted source and model
text is rendered as plain text, and source URLs still originate from the validated evidence
contract.

## Consequences

- A local user can complete the profile-to-review lifecycle without changing graph semantics.
- Browser-session loss is also checkpoint loss in this iteration; the UI states this limitation.
- PostgreSQL-backed, authenticated, multi-user review remains a separate iteration.
- The dashboard performs no brokerage action or external financial-system write.
