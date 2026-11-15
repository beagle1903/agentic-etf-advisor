# ADR 0052: Input-bound starter subset objective

- Status: Accepted for Issue153 after separate architect advice, independent challenge and coordinator approval.
- Date: 2026-11-15.
- Authority: [approved Issue153 agreement](https://github.com/beagle1903/agentic-etf-advisor/issues/153#issuecomment-6894043869).

Fresh starter roots pin both shortlist `sleeve-category-feasible-v2` and subset
`sleeve-count-category-v1` before sealing initial revision inputs. The optional
`PortfolioConstructionPolicy.starter_subset_algorithm` selects only the latter.
It requires starter research and explicit shortlist v2; null, unknown values and
feedback mentioning either selector reject. Absent subset selection preserves
historical first-feasible behavior and exact omission in Python and JSON. Restore,
retry, receipt reuse and child revisions preserve their saved input selectors;
no saved review is upgraded. The input policy selects computation, never a report.

Keep shortlist v2 unchanged. Over its at-most-ten candidates, retain every existing
identity, source/category, sleeve, position and category-weight feasibility check.
Among feasible subsets minimize exactly `(-position_count,
abs(10000*growth_count-position_count*growth_target_bps),
-distinct_normalized_source_categories, original_evidence_index_tuple)`.
Maximum feasible cardinality wins first, followed by sleeve fund-count balance,
then category coverage, then original evidence order. There is no extra preference
for larger growth count at a tie. Preserve source-order presentation and the
existing exact equal-sleeve basis-point division and largest-remainder cash cents.
Existing stable blocker precedence is unchanged. The report keeps its shortlist
`algorithm` and adds `subset_algorithm` only for new selection; its existing full
input digest binds both fields.

This is a bounded deterministic choice among already shortlisted candidates, not
a full-pool optimizer or benchmark-exposure veto. Category labels do not establish
independent economic risk, legal Fund identity, suitability or expected returns.
No source collection, adapter, clock, graph key, operation stage, store/publication,
migration, live run, trade or external financial write is introduced. Historical
baseline corpora and their expected outputs remain unchanged; new synthetic tests
carry independently specified expectations for the new version.
