# Iteration 023: Issue 99 analysis baseline

Issue [#99](https://github.com/beagle1903/agentic-etf-advisor/issues/99) is an ordinary,
owner-led evaluation and roadmap slice under [parent #24](https://github.com/beagle1903/agentic-etf-advisor/issues/24).
Its complete `DESIGN_READY` capsule, generation 1, digest
`81a67c8b1e69ac3569086f5e9d78d175e185af9df2674e65e55cdb1f26beb6c2`,
preceded edits. Owner: `/root/issue99_owner`, `implementation_worker`, `gpt-6-sol`, medium.
The frozen IDs are `INV99-1` through `INV99-5` and `AC99-1` through `AC99-5` in the
native ticket ledger. The user authorized the bounded issue; no financial or eligibility
contract change is part of this slice.

## Fixture identity and metric meanings

`analysis_baseline.json` is version 1, with 18 exact cases below. The original retrieval
dataset remains version 3 with SHA256
`9d159ac7eb6b4bae9eec36aaf829bd22dacdf8efac42964c8c369c344b2a5a4e`;
the original explanation dataset remains version 3 with SHA256
`09694077a2174f556180b9db6802112be921169593e1df4616562652c7bc6fb4`.
The runner checks both hashes and versions before use. The five retrieval case IDs are
`broad-us-equity`, `total-market-specificity`, `large-growth-equity`, `core-bond`, and
`technology-sector-threshold`. The 14 explanation IDs and expected decisions remain in
the original frozen dataset; the report exposes every actual decision and reason.

Retrieval uses the existing `evaluate_strategy` at K=3 on the same candidate order:
hit rate is the mean of any relevant result; recall is the mean relevant-returned fraction;
MRR is the mean reciprocal rank of the first relevant result. Attribution is the fraction
of returned records with source URL and timestamp. Graph-context recall is matched
source-linked contexts over expected contexts; graph field accuracy is exact fund-family
and category fields over expected fields. Sector coverage is records with structured
sector status over records in sector-judged cases; sector exact match is correct threshold
match sets over sector judgments. The report shows both variants and their difference.
Explanation decision accuracy is actual accept/reject against the frozen expectation;
each dimension's accuracy is correct cases over cases tagged with that dimension. It uses
the existing production validator and provider-refusal node. Analysis agreement is
matching stage, status, codes, exclusions, and applicable exact weights/cents over all
37 cases. These counts do not measure suitability, yield, or returns.

## Synthetic case matrix

All source entries are evaluation-only, attributed to synthetic `yahoo_finance` quote
URLs, fixed observation `2026-09-01T20:00:00Z`, check `2026-09-02T08:00:00Z`, snapshot
`issue99-analysis-v1`, and a 24-hour freshness window. They are invented fixtures, not
downloaded Yahoo facts. Base order is SPY Large Blend, VTI Large Blend, QQQ Large Growth,
VEA Foreign Large Blend, BND Intermediate Core Bond. Every current US ETF has fee 0.1%,
volume 1,000,000 shares/day, top-ten concentration 40%, canonical field provenance, and
source-linked sector context. Base profile: 15 years, moderate/balanced, 30% max drawdown,
USD 1,000 initial, USD 250 recurring, no exclusions. Listed deviations are the only changes.

| Case ID | Deviation | Frozen stage/result and observed detail |
| --- | --- | --- |
| balanced | Base | Construction ready; weights 1438,1438,1437,1437,4250 bps; initial cents 14380,14380,14370,14370,42500; recurring cents 3595,3595,3593,3592,10625. |
| conservative | Conservative/income | Ready; weights 500,500,500,500,8000 bps; 10000 bps and 100000/25000 cents. |
| aggressive | Aggressive/growth | Ready; observed weights 2375,2375,2375,2375,500; same exact totals. |
| one-cent | Initial USD 0.01, recurring 0 | Ready; 1/0 cents; some positive weights get zero cents. |
| zero-cash | Initial/recurring 0 | Ready; 10000 bps and 0/0 cents. |
| sector-reported | Exclude Technology; SPY 10%, others 0% | SPY screening fail/excluded; four-position draft ready. |
| sector-unsupported | Exclude `weapons` | All five screening unknown; construction blocked `insufficient_eligible_candidates`. |
| missing-fee | SPY fee `not_reported` | SPY unknown/excluded; four-position draft ready. |
| missing-category | BND category `not_reported` | BND excluded; blocked `missing_sleeve_coverage`. |
| stale-document | All documents 25 hours old | Evidence blocked; no draft. |
| stale-field | SPY fee field 25 hours old; document current | Screening blocked `field_stale`; no draft. |
| conflicting-fee | SPY canonical 0.1%, flattened 0.2% | Screening contract blocked; no repaired fact or draft. |
| insufficient-two | Aggressive/growth; QQQ and BND only | Blocked `insufficient_eligible_candidates`; no draft. |
| position-infeasible | Max position 4000 bps | Blocked `position_constraints_infeasible`; no draft. |
| concentration-fail | SPY canonical/flat 61% | SPY screening fail/excluded; four-position draft ready. |
| listing-us-usd | SPY, US listing, USD | Evidence ready; one ETF does not claim a feasible portfolio. |
| listing-eu-eur | VWCE.DE, German listing, EUR | Current US-only evidence blocked. |
| listing-eu-usd | CSPX.AS, Netherlands listing, USD | Current US-only evidence blocked despite USD currency. |

## Baseline readout and limitations

The focused replay observed 37/37 matching cases. Retrieval has hit rate 1, recall 1,
MRR 0.9, and attribution 1 for both variants. Graph context recall, exact graph fields,
sector coverage, and exact sector threshold judgments rise from 0 to 1; ranking metrics
do not change. All 14 explanation decisions matched; this is a frozen-output validation
result, not a live model success rate. Ready drafts reconcile 10,000 basis points and
their exact policy cents; blocked construction cases carry no draft. The full machine
readout includes every actual stage, code, exclusion, provenance and total and can be
recreated with `uv run etf-advisor evaluate-analysis`.

Concrete gaps remain: current evidence rejects EU listings irrespective of currency;
the candidate pool still depends on small curated membership; unsupported sector terms
and missing BND category block illustrative construction. Existing retrieval cases show
structured sector context value but no ranking lift. Live Yahoo catalogue completeness,
real-store behavior, embedding quality beyond the frozen ranking, live model response
quality, holdings overlap, diversification quality, suitability, and investment outcomes
are unmeasured. Follow-up issues #103 through #102 own these questions in the roadmap order;
this replay grants no EU eligibility or new financial rule.

The runner uses only packaged fixtures and pure production boundaries. It has no clock,
network, database, model or financial-write call. A changed expected outcome or a failed
production result makes the CLI exit nonzero. Native implementation and verification
evidence is recorded separately in the excluded Issue 99 ticket ledger after this file
is frozen for content-bound certification.
