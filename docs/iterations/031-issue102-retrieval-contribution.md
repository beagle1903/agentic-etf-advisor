# Iteration 031: Issue 102 retrieval contribution

Issue [#102](https://github.com/beagle1903/agentic-etf-advisor/issues/102) is an ordinary evaluation-only owner-led ticket. Its `DESIGN_READY` capsule is generation 1, digest `4994a3d11541a735f3ed26d80718a063368f42947275b784ea82ac15f31d8f62`, with frozen `INV102-1` through `INV102-3` and `AC102-1` through `AC102-4`. The approved owner is `/root/issue102_owner`, `implementation_worker`, `gpt-6-sol`, medium. The authorized scope is additive reporting in the existing offline retrieval evaluator. No product financial, safety, persistence, ranking, provider, or graph contract changes are authorized.

## Frozen controls before implementation edits

- Original `retrieval_baseline.json`: `retrieval-baseline`, version 3, SHA256 `9d159ac7eb6b4bae9eec36aaf829bd22dacdf8efac42964c8c369c344b2a5a4e`.
- Original `retrieval_expected_metrics.json`: version 1, SHA256 `af28ed7c9889e2e399fc2d8f871889bc1dbbc9ae195c9dd8b1884989dab90415`. It binds the preceding dataset identity and K=3. Both files remain byte-for-byte unchanged.
- The five exact case IDs, queries, ordered candidate controls, and source observation snapshots are:

| Case | Query | Ordered candidate IDs, distances | Relevant IDs | Expected graph contexts | Sector control |
| --- | --- | --- | --- | --- | --- |
| `broad-us-equity` | broad US equity exposure | SPY 08-26 .08; VTI 08-26 .12; QQQ 08-26 .31 | SPY, VTI | SPY, VTI | none |
| `total-market-specificity` | total US stock market ETF | SPY 08-26 .09; VTI 08-26 .11; QQQ 08-26 .34 | VTI | VTI | none |
| `large-growth-equity` | large growth technology-oriented US equity ETF | QQQ 08-26 .07; SPY 08-26 .27; VTI 08-26 .33 | QQQ | QQQ | none |
| `core-bond` | intermediate core bond diversification | BND 08-26 .06; VTI 08-26 .38; SPY 08-26 .41 | BND | BND | none |
| `technology-sector-threshold` | ETF technology exposure at or above forty percent | QQQ 08-28 sectors .07; SPY 08-28 sectors .08; VTI 08-28 sectors .10 | QQQ sector document | QQQ sector document | Technology >= 40%; QQQ sector document matches |

All 08-26 candidates refer to full original document IDs `yahoo-finance:{symbol}:2026-08-26`, with `observed_at=2026-08-26T20:00:00Z`. All 08-28 candidates refer to `yahoo-finance:{symbol}:2026-08-28:sectors`, with `observed_at=2026-08-28T20:00:00Z`. Each is a curated Yahoo Finance reference document with a quote URL and source label. The dataset has **no research snapshot identity field**, nor separate field-level provenance/observation timestamps; those absences must be reported explicitly. Document ID dates and sector context are not substituted for a research snapshot or field provenance. The 08-28 sector documents are distinct from the 08-26 reference documents and from Issue 99's synthetic analysis fixture.

Existing `evaluate_strategy` at K=3 defines hit rate as the mean case indicator for any relevant result; recall as the mean fraction of relevant documents returned; MRR as the mean reciprocal rank of the first relevant result; attribution as the fraction of returned results with URL and timestamp; graph-context recall as matched source-linked contexts over expected contexts; graph-field accuracy as exact fund-family and category fields over expected fields; sector coverage as returned records with structured sector status over returned records in sector-judged cases; sector exact match as correct threshold-match sets over sector judgments. The original expected-control file freezes both variants, each case, aggregate, and metric deltas. Ranking and attribution must be reported separately from context and sector results. The semantic candidate controls, including order and distances, are identical for both variants.

## Implementation and measured evidence

The existing `evaluate-retrieval` JSON now adds `cases`: each contains the frozen query,
ordered candidate IDs and distances, relevant/context/sector judgments, actual ordered
semantic and hybrid results, source/provider URL and observation time, nullable snapshot and
field provenance, nullable graph context and sector status, the existing metrics for each
variant and their deltas. The Issue 99 `evaluate-analysis` output reuses this case readout
as an additive `paired` field while retaining its frozen metric gate. The source URL for
each row is `https://finance.yahoo.com/quote/{symbol}/`; the returned provider is
`Yahoo Finance`. Both variants returned the same IDs and distances as the frozen controls
above. All three returned sources in each 08-26 case report `2026-08-26T20:00:00Z`;
all three in the sector case report `2026-08-28T20:00:00Z`. No result has a research
snapshot identity or field-level provenance. Semantic results have no graph context or
sector status; hybrid results have source-linked graph context, and only the sector case's
three results have `available` sector status.

| Case | Actual ordered symbols, distances in both variants | Hit / recall / MRR, both | Graph context recall / field accuracy, semantic to hybrid | Sector coverage / exact threshold, semantic to hybrid |
| --- | --- | --- | --- | --- |
| broad-us-equity | SPY .08, VTI .12, QQQ .31 | 1 / 1 / 1 | 0 / 0 to 1 / 1 | 0 / 0 to 0 / 0 |
| total-market-specificity | SPY .09, VTI .11, QQQ .34 | 1 / 1 / .5 | 0 / 0 to 1 / 1 | 0 / 0 to 0 / 0 |
| large-growth-equity | QQQ .07, SPY .27, VTI .33 | 1 / 1 / 1 | 0 / 0 to 1 / 1 | 0 / 0 to 0 / 0 |
| core-bond | BND .06, VTI .38, SPY .41 | 1 / 1 / 1 | 0 / 0 to 1 / 1 | 0 / 0 to 0 / 0 |
| technology-sector-threshold | QQQ .07, SPY .08, VTI .10 (08-28 sector documents) | 1 / 1 / 1 | 0 / 0 to 1 / 1 | 0 / 0 to 1 / 1 |

Attribution is 1 for both variants in every case. Aggregate hit/recall/attribution are
1/1/1 for both; MRR is .9 for both, so all ranking and attribution deltas are zero.
Aggregate context recall, exact fund-family/category accuracy, sector coverage and
exact technology-threshold judgment are each 0 for semantic and 1 for hybrid, with
delta +1. Sector metric denominators cover the sector-judged case only; zero in other
cases means no judgment, not failed sector evidence. This measures useful structured
context availability and the frozen threshold judgment, with no ranking lift and no
evidence for another graph expansion.

Focused tests assert unchanged source/control hashes, paired order and distances,
per-result provenance and missing metadata, deterministic replay, and independent
ranking, graph-field, context, sector-coverage and exact threshold mutations. The
evaluator runs from packaged fixtures without embeddings, Chroma, Neo4j, Yahoo,
network, wall clock or model calls. Live embedding quality, store behavior, source
coverage, live retrieval and model behavior remain untested. These observations do
not measure portfolio suitability, returns, or market freshness.

Self-review: inspected the diff for product retrieval, schema, financial, persistence
and provider changes; only evaluation models/reporting, focused tests and this iteration
were changed. Reused `evaluate_strategy` and the existing Issue 99 expectation gate;
no fixture, metric formula or ranking behavior changed. Verification commands and
outcomes are recorded separately in the Issue 102 ledger.
