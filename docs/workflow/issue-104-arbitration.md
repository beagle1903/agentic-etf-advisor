# Issue104 coordinator arbitration A104-1

- Opened 2026-10-18 UTC by `/root`; user approved starting Issue104 in this chat.
- Capsule `issue-104-us-eu-currency`, gen1 digest
  `4ef81eb8df7c89f8dbd0e7f36720cc2a9544467b4c5e5c6763967ee5b6d1f3a6`.
- Trigger: independent challenge identifies incompatible reference-fact provenance
  readings after the architect's complete substantive handoff. No implementation.
- Prior handoff SHA256:
  `180b9454fd24b6ff693649c4b1c635099e38ca561d298f48c799ad6c8f9e26c3`.
- Current phase challenge ends FAIL; dispatch held until clarification. Remaining
  before reset: implementation1, initial_review1, remediation1, final_review1,
  design_reset1. No running phase needs interruption; no offline pause claimed.

| Role/session | Frozen IDs | Scenario and evidence | Expected/actual | Classification |
| --- | --- | --- | --- | --- |
| architect `/root/issue104_design`; challenger `/root/issue104_challenge` | INV104-1/2/5, AC104-1/3/5 | Reuse reference-facts ResearchField in later snapshot; handoff lines90–103; research/models.py fields must match new snapshot ingestion/version; encoding.py repeats validation | Either reject older publication metadata or rebind ingestion/version while preserving observation; handoff does not select one | contract ambiguity |

Primary decision: narrow contract clarification by fresh separate architect under
the existing single design-reset reservation. No frozen scope, invariant, AC,
non-goal or owner change. Require exact reusable-input behavior and immutable source
observation/citation fields, then fresh independent challenge and coordinator
approval. Original challenge remains failed.

Rejected alternatives: let implementer choose (financial provenance is consequential);
waive validator (breaks integrity); assume rejection or rebinding without architect
authority (unresolved contract). No new allowance or automatic approval is granted.
FX staging has no independent blocker: retrieval can fetch when any candidate
differs from base, and construction decides whether selected draft needs the rate.

Focused closure: architect `/root/issue104_design_reset` supplies one deterministic
T0-reference/T1-snapshot rule under INV104-5/AC104-5, including preserved source
facts and publication metadata handling, with focused freshness/reuse/tamper tests;
fresh independent challenge passes the clarified complete document's exact hash.
Next permitted gate is consequential coordinator approval, never implementation
before it. Outcome remains pending; later evidence belongs here before content
certification or in the excluded current-ticket ledger after certification.

## Closure before implementation

Fresh architect `/root/issue104_design_reset` chose validated detached destination
publication-coordinate binding only at fresh collection, preserving exact source
tuple and original freshness. No retry/restoration rebinding. Full amended handoff
SHA256 `84ab2407b145c1c5a0fb887f66b169436ffd42423249f560ddf8444b8d0f9874`
is embedded in generation2 capsule digest
`e93ab282dac4f49b5e7f8c2d9f1dec224cd1bef85c9ff427ffa1103e9db77c6c`.
Fresh independent `/root/issue104_challenge2` verified both hashes and PASSed the
complete effective contract and A104-1 closure under the same frozen IDs. No
remaining material blocker identified. Coordinator accepts this accountable
clarification; A104-1 is closed, original failed challenge retained. Ticket
acceptance remains pending implementation, verification and independent review.
