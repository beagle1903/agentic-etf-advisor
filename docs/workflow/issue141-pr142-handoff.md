# Issue 141 PR142 bounded repair handoff, generation 2

Separate read-only designer `/root/issue141_pr_design`, design_architect / gpt-6-astra / high, returned DESIGN_READY on generation2 digest `3d1fdf814724c540fcc118c8fa37980aa2063d6fcb735df1587628bb3c4958ab`. User authorized exactly one additional repair and one independent review for PR142's two findings. Existing owner remains `/root/issue141_owner`, implementation_worker / gpt-6-sol / medium. Independent challenge and coordinator approval precede edits.

## Frozen scope and ambiguity

B141-SLEEVE-FEASIBILITY / AC141-2 is the capacity-three defensive-first two-defensive/one-growth shortlist under95/5 targets; existing minimum500/maximum8000bps position bounds make it infeasible despite SPY/QQQ4750each+BND500 being feasible. B141-CONSTRUCTION-COUNTS / AC141-1 is screening-pass category_missing/category_unsupported counted eligible despite construction exclusion. Correct these two paths and necessary replay binding only.

INV141-3 ambiguity is that validate_persisted_construction recomputes using current constructor and v1 blocked bundles omit starter_selection. A report alone cannot safely dispatch historical behavior. The existing single design-reset slot is reserved for this concrete ambiguity, not for scope expansion or disagreement. No general optimizer, new acquisition, registry, profile/source marker change, threshold/cash change, old-contract change or saved-review migration.

## Input version and replay

Add absent-by-default PortfolioConstructionPolicy.starter_shortlist_algorithm, type Literal["sleeve-category-feasible-v2"] | None. Absence executes exact existing starter v1, including omitted reports on blocked results. Exact present v2 selects corrected algorithm. Explicit null, unknown value or nonstarter use rejects. Omit absent field in Python AND JSON serialization, preserving historical policy/revision/artifact/receipt bytes.

Only the fresh-root starter branch in RevisionRuntime.begin pins v2, before sealing initial inputs, preserving all numeric policy values. Never inject on deserialize/recompute/retry/restore/revision planning. Existing v1/v2 retries and children retain their recorded policy. Reject construction-feedback patches containing this version field. Existing reviews keep v1 throughout lineage; new reviews select v2. Pure construction uses supplied policy with no automatic upgrade.

Report algorithm must match policy-selected dispatch. Unknown/changed/stripped/contradictory report fails deterministic comparison. Report never picks validation algorithm. Existing construction-policy JSON copies and operation bindings carry the selector; no new graph key, stage, profile/source marker or receipt schema.

## Bounded v2 selection

Keep classification, subset selection, categories, equal sleeve weights, precision and cent allocation unchanged. Capacity is min(requested_limit, policy.max_candidate_pool_size,10). Use only positive-target sleeves.

Enumerate two-sleeve count pairs, never candidate subsets. Counts cannot exceed available classified candidates or capacity. A feasible pair has total between min_positions and min(max_positions,capacity), and at least one candidate for each positive target. For each sleeve, divmod(target_bps,count) quotient and any quotient+1 must fit existing position min/max, matching _equal_sleeve_weights.

Choose feasible count pair by largest total, then smallest abs(10000*growth_count-total*growth_target_bps), then larger growth count. Reserve that many candidates per sleeve, visiting defensive then growth. Within sleeve choose an unrepresented normalized category first, then original evidence index. Fill remaining capacity with existing catalogue target-debt formula (growth wins ties), same category/index order. If no feasible pair, reserve one per available positive-target sleeve where capacity permits, defensive first, then fill identically; unchanged constructor returns blocker.

This repairs obvious sleeve-count infeasibility, not all full-pool category/identity combinations. Do not relax bounds or add a wider optimizer to force every result.

## Report and coverage

V2 preserves report structure and adds target_bps and usable_count=len(classified_eligible) before shortlisting. algorithm is sleeve-category-feasible-v2. Its input_digest hashes complete canonical PortfolioConstructionInput using existing _catalogue_input_digest, binding profile-derived targets/evidence/screening/policy/version. V1 digest and bytes remain unchanged.

Retain v2 report on blocked returns after classification/shortlisting complete; final_position_ids stays empty. Earlier failures have no evaluated report. Preserve v1 blocked serialization exactly.

Keep source-health precedence and stale/future/not-screened behavior. For evaluated v2 report use usable_count for construction eligibility; v1 reports derive eligible membership from shortlisted and bounded-omission dispositions. Join construction excluded_candidates by identity, include reasons when report absent. Screening-pass category_missing/category_unsupported counts excluded and never eligible. Shortlist omissions remain eligible. A historical reportless blocked result cannot establish complete construction eligibility: show unavailable after screening when classification completion cannot be established, keep known exclusions visible, distinguish passed screening from construction eligible. With screening not completed preserve zero eligible/not-screened behavior. Reporting must never rewrite saved artifacts.

## Focused closure and verification

Test fresh v2 normal graph capacity3, aggressive/growth95/5, SPY/QQQ/BND4750/4750/500. Include opposite imbalance, scarce sleeve supply, infeasible bounds, deterministic ties/capacity and unchanged category constraints. Category-missing/unsupported fixtures pass screening but construction-exclude; counts/rows agree in ready/post-shortlist-blocked/historical-reportless and stale/future/mixed states.

Capture pre-change v1 READY and BLOCKED golden outputs before edits; identical serialized policies/revision inputs/receipts and absent report stay identical. Replay both versions offline with source/file/clock denied. Fresh roots pin v2, saved retries/receipt reuse/all supported child routes retain version. Algorithm-edit feedback/null/unknown/nonstarter markers, report-policy mismatch and stripping reject. V2 digest changes with allocation/profile inputs; v1 digest and legacy/us-eu/curator fixtures stay unchanged.

Owner runs focused self-review and required gates; no source pass. Fresh identical-content verification/acceptance then the authorized independent final review. Failure or materially wider contract need stops for coordinator decision under finite counts.

Add a new ADR (preserve ADR0047 history), active iteration and guide explaining fresh-v2 vs retained-v1, input-bound version and bounded heuristic. Risks are selector insertion on deserialize, changed historical bytes, child upgrade, feedback downgrade and confusing shortlist omission with ineligibility.

No tests/source calls/edits by designer. Frozen S/INV/AC definitions unchanged. DESIGN_READY.