# Issue 117: fresh Curated US starter use, 11 November 2026

## Scope and outcome

This is one local, read-only product-use exercise of the merged US/USD starter. The owner was `implementation_worker` (`gpt-6-sol`, medium), classified as ordinary verification of existing interfaces under ADR 0049. The authorized scope and acceptance were [recorded on Issue 117](https://github.com/beagle1903/agentic-etf-advisor/issues/117#issuecomment-6802963743) before execution. No product code, financial rule, graph JSON, saved review, catalogue, registry, or external financial system was changed.

The single source pass completed; all 20 fixed leads were collected, and 17 passed source screening and construction eligibility. Three illustrative profiles on that same artifact produced ready drafts **awaiting human review**. This establishes one dated US/USD starter result, not independent investment risk, suitability, production source rights, or the original US/EU acceptance of Issue 117. The retained US/EU publication and durable restoration criteria remain unmet.

## Reproduction and source identity

From a separate clean checkout of main `67c57ed6bf36558e5a46f5836bbb546aadbe674c` (the protected default checkout was untouched):

```powershell
uv sync --extra dashboard --extra rag
uv run etf-advisor dashboard --port 8502
```

Open `http://localhost:8502`, select **Curated US starter**, and click **Collect current starter data** once. The normal control allocated `.artifacts/issue141-source-runs/400994b9-57e8-4cc6-9677-899f464c9ea2/pass.json` and prepared `.artifacts/issue141-prepared/84945c519de3ba53e09f515aff2ba14b62eebf83075534c8267e053360ebcdc3.json`. Both remain ignored local evidence; neither is committed. The pass file SHA-256 is `4f7e83cfa08dcc2fd8e32210ae57b8dcca37b3b62f250c15e957eef178a47dcf`; prepared artifact digest is `84945c519de3ba53e09f515aff2ba14b62eebf83075534c8267e053360ebcdc3`, packaged universe digest `6b492884c7a7ca9f9cdb065ad4cca675c84b4d020fe3c1d5ab45b112c4edd4f6`, snapshot version `us-starter-1`, and source snapshot digest `0255757885d5b3cb06c82b8500873c0009cadd813bfdd7493cd74cc4c42bc7e7`.

Dependency installation used the two `uv sync` invocations above; their elapsed time was not measured. The app was reachable in the browser by `17:43:39Z`, before the collection began. The dashboard remained local at port 8502 for this exercise.

The pass started `2026-11-11T17:43:56.828172Z`, finished `17:45:10.417549Z`, and recorded `73.587` elapsed seconds under the existing 900-second whole-pass ceiling. Preparation time was `17:45:10.417549Z`. Each lead used five Yahoo requests; no automatic retry or second collection occurred. The source URL for each is `https://finance.yahoo.com/quote/{symbol}/`. These are source quote observation times, distinct from the local collection times:

| Symbol | Exchange | Source observed UTC | Collected UTC | Source-gate result |
| --- | --- | --- | --- | --- |
| BND | NGM | 17:44:19 | 17:44:34.471894 | eligible defensive |
| AGG | PCX | 17:44:31 | 17:44:39.927908 | eligible defensive |
| SCHZ | PCX | 17:44:39 | 17:44:41.510779 | excluded: top-ten concentration not reported |
| SPAB | PCX | 17:42:32 | 17:44:43.312582 | eligible defensive |
| SPY | PCX | 17:44:42 | 17:44:44.828095 | eligible growth |
| IVV | PCX | 17:44:41 | 17:44:46.795904 | eligible growth |
| VOO | PCX | 17:44:43 | 17:44:48.387319 | eligible growth |
| VTI | PCX | 17:44:47 | 17:44:49.466885 | eligible growth |
| ITOT | PCX | 17:44:09 | 17:44:50.570047 | eligible growth |
| SCHB | PCX | 17:44:41 | 17:44:51.671112 | eligible growth |
| QQQ | NGM | 17:44:52 | 17:44:53.461048 | eligible growth |
| VUG | PCX | 17:44:44 | 17:44:54.934574 | excluded: top-ten concentration above 60% |
| SCHG | PCX | 17:44:55 | 17:44:56.425443 | excluded: top-ten concentration above 60% |
| IWF | PCX | 17:44:46 | 17:44:58.273383 | eligible growth |
| VEA | PCX | 17:44:21 | 17:44:59.416748 | eligible growth |
| IEFA | BTS | 17:44:47 | 17:45:01.285825 | eligible growth |
| SCHF | PCX | 17:45:00 | 17:45:03.433937 | eligible growth |
| VWO | PCX | 17:45:02 | 17:45:06.099 | eligible growth |
| IEMG | PCX | 17:45:07 | 17:45:08.446649 | eligible growth |
| SCHE | PCX | 17:42:47 | 17:45:10.388995 | eligible growth |

All observation and collection times above are on 11 November 2026. Yahoo listing symbol, admitted US exchange, ETF class, US market and USD quote were checked by the existing collector. The actual source pass and prepared artifact retain the full attributed field observations and reasons. Source success alone did not waive freshness or screening.

## Three profiles on the same prepared artifact

The normal dashboard review path was exercised for each profile with the selected prepared dataset, evidence required, explanation disabled, PostgreSQL disabled and no excluded sectors. A separate local call to the same `start_dashboard_run` backend used `candidate_limit=10` for the frozen comparisons and detached reconstruction below. Exact inputs were: USD initial `$25,000.00`, recurring monthly `$500.00`, and the same starter request digest above for every profile. There was no FX conversion.

| Profile | Risk / objective | Horizon / max drawdown | Growth / defensive policy | Requested / attempted / collected / screened | Construction eligible / excluded / shortlisted / final | Backend result |
| --- | --- | --- | --- | --- | --- | --- |
| Conservative income | conservative / income | 5 years / 10% | 20% / 80% | 20 / 20 / 20 / 20 | 17 / 3 / 10 / 5 | ready; awaiting review |
| Moderate balanced | moderate / balanced | 12 years / 25% | 57.5% / 42.5% | 20 / 20 / 20 / 20 | 17 / 3 / 10 / 5 | ready; awaiting review |
| Aggressive growth | aggressive / growth | 20 years / 45% | 95% / 5% | 20 / 20 / 20 / 20 | 17 / 3 / 10 / 5 | ready; awaiting review |

The backend evidence check times for that comparison were `17:52:01.559650Z`, `17:52:09.450378Z`, and `17:52:18.084798Z` in table order. All three pinned `sleeve-category-feasible-v2`, had 17 screening passes, two fails (VUG and SCHG) and one unknown (SCHZ), and reported no construction blocker. The ten-candidate shortlist is an input bound; five positions is the existing maximum. The selected positions and exact USD allocation were:

| Profile | Symbol | Weight | Initial USD | Monthly USD |
| --- | --- | ---: | ---: | ---: |
| Conservative | SPY | 5.00% | 1,250.00 | 25.00 |
| Conservative | IVV | 5.00% | 1,250.00 | 25.00 |
| Conservative | VOO | 5.00% | 1,250.00 | 25.00 |
| Conservative | VTI | 5.00% | 1,250.00 | 25.00 |
| Conservative | BND | 80.00% | 20,000.00 | 400.00 |
| Moderate | SPY | 14.38% | 3,595.00 | 71.90 |
| Moderate | IVV | 14.38% | 3,595.00 | 71.90 |
| Moderate | VOO | 14.37% | 3,592.50 | 71.85 |
| Moderate | VTI | 14.37% | 3,592.50 | 71.85 |
| Moderate | BND | 42.50% | 10,625.00 | 212.50 |
| Aggressive | SPY | 23.75% | 5,937.50 | 118.75 |
| Aggressive | IVV | 23.75% | 5,937.50 | 118.75 |
| Aggressive | VOO | 23.75% | 5,937.50 | 118.75 |
| Aggressive | QQQ | 23.75% | 5,937.50 | 118.75 |
| Aggressive | BND | 5.00% | 1,250.00 | 25.00 |

Each profile reconciled to exactly 10,000 basis points, `$25,000.00` initial and `$500.00` monthly. No draft was approved or submitted. The dashboard's decision form defaults its radio selection to **Approve**, so the visible control alone is not a decision; the separate **Submit decision** action was never used. Optional LLM explanation was **not generated**.

The source-gate exclusions were retained in the review. The live construction classified SCHZ as screening **unknown** and VUG/SCHG as screening **fail**; the other 17 were usable before shortlisting. Equal-index ETFs remain separate verified Yahoo listings, not independent economic risks. For example, the saved evidence's reported-holdings comparison of SPY and IVV found 10 matched reported rows and `37.25827` percentage points of overlap in those rows. The SPY reported-row sum was `37.2802996` points and IVV's `37.25827` points, both from Yahoo observations at `17:44:42Z` and `17:44:41Z`. This is limited to reported top holdings, not complete fund or portfolio overlap, and did not change weights.

## Review validation and limits

The UI reached **Human review** for all three profiles and displayed ready policy/portfolio/source evidence; the default process-local checkpoint message explicitly offered no browser-session or process-loss recovery promise. The frozen backend calls used fresh in-memory checkpoint stores, `review_payload` succeeded, then JSON-detached state passed `validate_revision_state`, `reconstruct_audit`, and `review_payload` again with the saved interrupt payload. This reconstruction used the embedded evidence and no provider, registry, catalogue, Chroma, Neo4j, or wall-clock read. It demonstrates offline validation of detached saved evidence; it does **not** demonstrate PostgreSQL durability or restoration after a process restart.

The local analysis command was `uv run python .artifacts/issue117-analyze.py > .artifacts/issue117-analyze-output.jsonl`. That ignored script loaded the one prepared artifact, built each exact profile above with `StarterRequestV1` and `DashboardOptions(with_evidence=True, with_explanation=False, candidate_limit=10)`, and called `start_dashboard_run` once per profile. It then removed the runtime `__interrupt__` object, JSON-round-tripped the remaining graph state, ran `validate_revision_state` and `reconstruct_audit` on those detached bytes, restored the already saved interrupt value as a detached object, and compared `review_payload` before and after detachment. The script read the local prepared artifact only for initial draft creation; the detached review checks made no source call or file read. It saved the private detailed result only under ignored `.artifacts/issue117-analysis.json`. This local analysis did not install a network interceptor, so the no-provider conclusion rests on the selected prepared retriever and the pure validation paths, not a network trace.

The browser automation also exercised the moderate profile with the UI's default five-candidate slider, yielding 20 / 20 / 20 / 20 requested through screened, 17 eligible, three excluded, five shortlisted and five final. During later conservative and aggressive browser runs a Playwright range-input fill displayed `10` in the slider, while the UI coverage continued to display five shortlisted. A pointer click on the slider was intercepted by Streamlit overlay elements. The backend's explicit `candidate_limit=10` runs consistently shortlisted ten. The browser interaction does not establish that the application accepted a slider change; the five-candidate UI observation is kept distinct from the ten-candidate backend comparison and is **not** classified as a demonstrated product defect.

This one pass cannot establish future availability, legal Fund identity, an exhaustive US/EU catalogue, independent exposure, or the retained Issue 117 US/EU publication and saved-review acceptance. A future stale source would require a new explicitly initiated run; this exercise did not renew source timestamps. Issue 123 curation remained deferred. No provider body, credential, token, or private review state is in this report.

## Verification

The existing starter-focused test suite passed with `uv run pytest tests/test_issue141_starter.py`: **27 passed in 69.50 seconds**. The test suite created two additional synthetic ignored run directories with no source observations; neither was a live collection. `git diff --check` passed. `git check-ignore` confirmed the actual source pass, prepared artifact, analysis script and private JSON/JSONL outputs remain ignored. The saved analysis JSON independently summed each profile to 10,000 basis points, 2,500,000 initial cents and 50,000 recurring cents, and confirmed all three detached review payload comparisons. This report is the only proposed repository change, so no new behavior test was added. The owner compared the report's 20 ordered source outcomes, check times, three position sums, screening dispositions, artifact digests and human-review status against the saved local evidence before committing.
