# Issue 110 coordinator arbitration A110-1

- Opened: 2026-10-16T07:19:25Z; coordinator /root. User authorization: 2026-10-16 `ok do it` after three P2 findings and bounded proposed repair, tests, verification and independent review.
- Frozen capsule: issue-110-publication-diagnostics generation 1, digest 9ab4571a213a2af1d0f25ea935aa1b329807607470530275c0806a81c313434c. Previous verified content acc2941ebddb72565eab566b18809a10e9545071612db11f2e47165268442d44; delivery PR111.
- Trigger: diagnostic misclassification returned in previously untested supported paths after initial diagnostic repair and delivery. Existing closure was correct sanitized stage/category with nonzero failure under AC110-1/2.
- Current phase: none; no active reservation or interruption required. Dispatch hold opened and resolved by this decision; not an offline pause. Continuation grants exactly one remediation and one final-review delta, preserving all prior history and default counters. Current remaining: remediation 2, final_review 2, initial_review 1, design_reset 1, implementation 0. Only one repair/review attempt authorized here; unused counters are not new scope authorization.

| Evidence / participant | Frozen criterion | Concrete path | Expected vs actual | Classification |
| --- | --- | --- | --- | --- |
| GitHub bot discussion_r4285409780; coordinator current-code check | AC110-1, AC110-2 | Inactive existing version, required canonical payload absent | input_validation expected; graph_lookup/store_failure actual | demonstrated defect |
| GitHub bot discussion_r4285409818; coordinator current-code check | AC110-1, AC110-2 | Valid JSON custom universe missing required field raises plain Pydantic ValidationError in universe_load | input_validation expected; generic schema_encoding actual | demonstrated defect |
| GitHub bot discussion_r4285409844; coordinator current-code check | AC110-1, AC110-2 | Active schema1 without supplied payload/fingerprints; Neo4j snapshot_documents reconstruction fails | graph_readback expected; chroma_readback actual | demonstrated defect |

- Primary decision: narrow repair of stage attribution and validation classification, with focused regression tests for all three paths and retained genuine nested integrity causes. INV110-1 preserves execution/validation/persistence/financial contracts; INV110-2 requires fixed allowlisted sanitized diagnostics and original internal exceptions.
- Rejected alternatives: waive findings because CI passed (paths missing); reset design or replace owner (no consequential ambiguity); change graph/publication schema or store data (outside scope). No disagreement with the three scenarios; root cause of historical live provider failure remains unconfirmed and is separate evidence.
- Owner / next gate: original /root/issue110_owner, implementation_worker gpt-6-sol medium. Check/reserve remediation before resuming owner. Then same-owner content-bound verification and acceptance; separate read-only code_reviewer gpt-6-sol high final review with independence and finite reservation. Same PR111 only; no merge, live publication or data changes.
- Focused closure condition: all three injected CLI regression scenarios report correct fixed stage/category, nonzero exit and no raw secret/source leakage; nested actual allowlisted integrity errors retain their code. Owner supplies focused tests and required gates against frozen IDs; independent reviewer checks these scenarios and unchanged invariant behavior on identical certified content. Any demonstrated defect or material acceptance uncertainty stops redelivery. Closure does not itself certify acceptance.
- Outcome: narrow repair authorized; exact checked/reserved execution and later results are recorded in excluded issue110 ledger evidence. No new ledger event or automatic reset introduced.

## Owner repair evidence and closure status

The original approved owner reproduced all three scenarios as failing real CLI
tests before changing production code. The inactive retry reported
`graph_lookup: store_failure`, ordinary custom-universe validation reported
`universe_load: schema_encoding`, and legacy graph document reconstruction
reported `chroma_readback: store_failure`. The fixtures assert nonzero exit and
no injected private data in output; the legacy fixture also fixes the order of
Chroma's existing missing-ID check and Neo4j reconstruction.

The narrow repair reports `payload_load: input_validation`,
`universe_load: input_validation`, and `graph_readback: store_failure` for those
same scenarios. A nested Pydantic validation error with an actual allowlisted
`ResearchIntegrityError` still reports `numeric_provenance`. Focused CLI tests
pass after repair (30/30). The full service-free suite passed 1,604 tests with
48 expected skips; Ruff lint/format, mypy, build, workflow validators and diff
checks passed. No data adapter, snapshot schema, freshness rule, financial
decision, store mutation or replay behavior changed. This satisfies the owner
portion of the focused closure condition under AC110-1/2 and INV110-1/2.
Content-bound verification and acceptance evidence belongs in the excluded
Issue110 ledger; independent final review of that same content remains the next
permitted gate. The episode cannot certify ticket acceptance by itself.
