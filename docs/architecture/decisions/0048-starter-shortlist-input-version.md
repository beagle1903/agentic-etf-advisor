# ADR 0048: Input-bound starter shortlist version

- Status: Accepted for Issue 141 generation 2 after separate design, independent challenge and coordinator approval.
- Date: 2026-11-08.
- Authority: Issue 141 generation 2 capsule `3d1fdf814724c540fcc118c8fa37980aa2063d6fcb735df1587628bb3c4958ab`.

Fresh curated US starter reviews pin `sleeve-category-feasible-v2` in the construction policy before the initial revision inputs are sealed. An absent selector retains the exact v1 shortlist and blocked-result serialization for saved reviews, retries and child revisions. Explicit null, unknown values, nonstarter use and feedback edits are rejected. The saved report does not choose its own validator; deterministic recomputation uses the input policy.

V2 enumerates bounded growth/defensive **counts**, using existing minimum and maximum position weights to seed a feasible sleeve balance where one exists. It fills remaining shortlist capacity by target debt and category coverage, then passes the shortlist to unchanged subset selection, category limits and cash allocation. It does not optimize arbitrary full-pool subsets or relax financial rules. Its report binds the complete construction input, includes target basis points and pre-shortlist usable count, and remains attached after post-shortlist blockers. V1 digest and report omissions remain unchanged.

The dashboard uses evaluated construction exclusions and usable count for eligibility. A shortlist omission remains eligible; a screening pass with missing or unsupported construction category is excluded. For historical reportless blocked construction, complete eligibility is unavailable, while known exclusions and source health remain visible. No source observation, legal identity assertion, market provider or external financial write changes.
