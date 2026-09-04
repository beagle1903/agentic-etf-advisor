# ADR 0015: Plan revisions from typed feedback and guard side effects with receipts

- Status: Accepted
- Date: 2026-09-04

## Context

The current review boundary accepts approve, edit, and reject. Approval finalizes, while edit and
reject both end with `needs_revision`; starting again invokes the graph from profile validation and
can repeat retrieval or provider calls. Free-form feedback does not identify which state changed,
which artifacts are stale, or whether a completed side effect is safe to reuse.

A revision loop must not give a model or UI heuristic authority to interpret financial intent. It
must also distinguish pure deterministic recomputation from operations whose external outcome may
already exist after a process or connection failure.

## Decision

Represent every non-approval review response as a typed decision. `edit` always creates a child
revision. `reject` has an explicit `revise` or `close` disposition. Revision-requesting decisions
contain validated feedback items classified as `profile`, `evidence`, `screening_policy`,
`construction_policy`, or `explanation`. Bounded free text is retained only as audit context and
cannot select a class, build a patch, or choose a route.

Map each class to one restart boundary:

| Class | Restart boundary |
| --- | --- |
| `profile` | `validate_profile` |
| `evidence` | `retrieve_candidate_evidence` |
| `screening_policy` | `screen_candidates` |
| `construction_policy` | `construct_portfolio` |
| `explanation` | `draft_explanation` |

For mixed feedback, choose the earliest boundary in workflow order. Validate the complete decision
before creating a revision, then clear all state at or after that boundary. Unchanged upstream
artifacts are referenced through immutable identity and canonical digest. Policy calculation has no
separate feedback class because it remains a pure result of the validated profile.

Give each revision an ID, sequence, plan, and immutable identities for the stages enabled and
reached. A non-root revision links its parent and stores the parent's decision separately as its
`triggering_decision_id`. Its own `review_decision_id` is absent until that revision is reviewed.
Policy-only revisions do not invent evidence, screening, construction, explanation, or operation
identities. Represent each retrieval or explanation call that is actually attempted with an
operation receipt containing revision, stage, attempt, operation ID, canonical input digest,
status, optional output identity/digest, and injected UTC times.

A succeeded receipt is reusable only when its input matches and the referenced output passes local
validation with the same digest. Failed and ambiguous attempts never retry automatically. A
`started` receipt without a durable result is ambiguous and stops before another adapter call;
explicit retry creates a new attempt identity. Missing, duplicate, out-of-order, cross-revision, or
digest-mismatched receipts fail closed.

Future external financial writes are not generic replayable stages. They continue to require a
separate human approval immediately before execution under ADR 0002.

## Consequences

- Review feedback becomes deterministic graph input rather than model-interpreted prose.
- The graph can recompute pure stages freely while making external-call reuse and retry visible.
- A broad change invalidates more downstream work, but mixed changes cannot accidentally start too
  late.
- The state contract gains revision and receipt records, all serialized as JSON-mode model dumps.
- The dashboard must collect typed feedback and may not reconstruct routing policy itself.
- Explicit retry may require the user to repeat a provider or retrieval cost after an ambiguous
  attempt; the system favors visible uncertainty over accidental replay.
