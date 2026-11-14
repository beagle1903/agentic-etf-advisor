# Issue 24: roadmap and status reconciliation

## Agreement, 14 November 2026

The user approved this chat's queued documentation/status slice with “continue”.
The [issue agreement](https://github.com/beagle1903/agentic-etf-advisor/issues/24#issuecomment-6874005011)
records authorization, owner, actions and acceptance. This is ordinary existing-contract
documentation under ADRs [0049](../architecture/decisions/0049-prospective-working-agreement.md)
and [0051](../architecture/decisions/0051-model-presets-and-assignments.md).

Accountable owner: coordinator/current chat `01a1d461-0368-7702-8880-71aea4c29c56`,
performing `implementation_worker` work. No fresh preset dispatch or model override was
made in this existing session. The documented routing target is `sol` / `gpt-6.1-sol` /
medium; backend identity/effort is not independently attested. Observed inherited access
is unrestricted filesystem and network with approval policy never. Restrictions are
instruction-only, not a separate access boundary. No separate planning/review session is
required for this routine prose; the owner performs self-review and focused verification.

Scope: reconcile current roadmap and #24/#117 status summaries, preserve historical
scope/outcomes, and recommend one concrete next slice. Permitted delivery includes
commit/push/PR and these status updates. No automatic child issue, product implementation,
source pass/provider request, publication, compatibility/storage removal, migration,
financial/identity/replay/security/workflow contract change, trade or financial-system
write. Affected interfaces: documentation and issue descriptions. Product APIs and
JSON/graph state impact: none.

One reviewable outcome fits the current issue; no split is needed. The protected dirty
default checkout and other worktrees/ignored evidence are preserved. Work uses isolated
branch `codex/issue24-roadmap-reconciliation` based on main
`a012b34582b5dcfd60e83eacc99e19dfc3be52e2`.

## Acceptance and source audit

- AC24-D1: The roadmap distinguishes implemented capabilities, dated live evidence and
  deferred readiness; its opening agrees with current vision/system and immediate US/USD direction.
- AC24-D2: Current #24/#117 summaries acknowledge PRs #145–148 as applicable, with
  dated source/merge evidence. No collection is repeated or current source health inferred.
- AC24-D3: Preserve original historical issue descriptions, accepted ADRs, ledgers,
  failed outcomes and unmet criteria. Keep #24, original broader #117 and #123 open;
  delivery of children is not parent acceptance.
- AC24-D4: One new presentation proposal states its evidence, scope, non-goals,
  observable acceptance and authorization boundary without reopening completed work.
- AC24-D5: Owner source/diff review, changed-document links, preset validation and
  appropriate repository checks pass; required PR CI is reported separately.

Live GitHub PR metadata was checked on 14 November; all four PRs below are merged.
The source reports remain unmodified, including their at-authoring pending status.
Their later merge disposition is recorded here rather than rewriting history.

| Delivered evidence | Immutable merge | Boundary |
| --- | --- | --- |
| [PR145](https://github.com/beagle1903/agentic-etf-advisor/pull/145), [iteration045](045-issue117-us-starter-use-2026-11-11.md) | `c9c58b0eac2d30630ae4ca5ac4a6c8245f604583` | One 11 November pass: 20/20 collected, 17 construction eligible, three drafts awaiting review; no approval/explanation/retry or PostgreSQL restart proof. |
| [PR146](https://github.com/beagle1903/agentic-etf-advisor/pull/146), [iteration046](046-issue115-selected-fx.md) | `085db17be7f38b317cff0b712f2f0f592ebc9ed9` | Selected-subset FX delivered; existing selection/weights/cash and historical review semantics preserved. |
| [PR147](https://github.com/beagle1903/agentic-etf-advisor/pull/147), [iteration047](047-issue106-early-decomposition.md) | `6fbb42987559d0647b40a1ac0290ef1f47f01bd9` | Decomposition guidance delivered; no automatic splitting or new product authority. |
| [PR148](https://github.com/beagle1903/agentic-etf-advisor/pull/148), [iteration048](048-issue109-model-presets.md) | `a012b34582b5dcfd60e83eacc99e19dfc3be52e2` | Three presets/six assignments delivered; instruction-only restrictions, no runtime identity/access-enforcement attestation. |

Current #24 still scheduled the completed starter exercise and treated #106/#109 as
pending with unchanged role pins; #117 still scheduled that exercise. The roadmap
opened with an obsolete US-only implementation statement and presented closed children
as a queue. These are status/documentation defects, not authority to change support.
#123's current stopped/deferred summary already matches the evidence and needs no edit.
Original #117 US/EU publication, partial-job and saved-review proof remain unmet.

## Next-slice recommendation and rationale

Recommend automatically showing the existing reported-holdings comparisons for pairs
of selected draft positions at human review. The November 11 conservative and moderate
drafts both selected SPY/IVV/VOO/VTI/BND; reported SPY/IVV top-holdings overlap was
37.25827 percentage points with partial reported lists. This is a measured review
information gap, not a demonstrated construction defect or a new risk metric.

Inspection of `dashboard_app._render_evidence` at the base commit confirmed that #101
already supplies a manual two-candidate control over the evidence pool. Its pure helper
and completed acceptance remain intact. The new proposal adds automatic presentation
for at most ten unordered pairs from at most five selected positions, using those same
results. It must retain per-side coverage/provenance, partial-list and unavailable
labels, exact units and saved check time; it cannot imply independent risk or complete
portfolio overlap. Ready/offline review must perform no external calls and preserve
serialized state, IDs, selection, weights and cash. Focused tests would cover exact
selected-pair membership, five-position bound, partial, zero and unavailable results.

No weighted/portfolio-wide aggregation, index/Fund inference, source call, financial
rule, schema, storage or universe change is proposed. The roadmap contains the complete
observable acceptance proposal. A future user decision is needed to schedule it;
consequential interpretation would require separate advice/approval. No child is created.
This narrow presentation outcome has evidence now; reopening curation or removing
compatibility/storage has neither new evidence nor authorization in this slice.

## Verification and delivery

The owner updated the current sections of #24 and #117, then compared each returned
`<details>` historical suffix byte-for-byte with the fetched original: both unchanged.
Both issues remain open; #123 required no update. The issue summaries link the immutable
operational evidence and keep the recommendation separate from implementation authority.

Source/diff self-review checked AC24-D1 through AC24-D4 against current vision/system,
ADRs 0049/0051, iterations 045–048, merged PR metadata and the existing manual-pair UI.
All thirteen relative links in the two changed documents resolve. No behavior/prose-marker
test was added. In the isolated locked default/development environment, preset validation,
Ruff lint/format (275 files), build and Compose configuration passed. The build emitted a
temporary uv cache-write warning but successfully produced both wheel and source archive.
The protected default checkout still has the same staged/untracked paths as at start.

`uv run --frozen mypy` passed (69 source files). The full locked service-free suite
passed with **1,706 passed, 83 optional skips in 405.63 seconds**. The final document
link and diff checks passed; only the roadmap and this new iteration are included.
Both published issue bodies were fetched again and matched the prepared text exactly,
including their preserved original sections and open status. AC24-D1 through AC24-D4
and local AC24-D5 checks pass; PR CI is reported on the PR after publication.
No live-source, real-store, financial readiness or independent review result is claimed
for this prose-only slice. #24, #117 and #123 remain open with their deferred criteria.
