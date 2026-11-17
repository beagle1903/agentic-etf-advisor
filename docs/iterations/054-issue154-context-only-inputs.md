# Issue154: disclose context-only allocation inputs

## Approved design capsule (before runtime edits)

DESIGN_READY. User approved starting and selected **Context-only disclosure
(Recommended)** (Option B). Authority: [coordinator approval](https://github.com/beagle1903/agentic-etf-advisor/issues/154#issuecomment-6945962777).
Separate read-only `/root/issue154_design` design_architect, requested astra/high,
provided advice before coordinator approval. Owner/participant `/root/issue154_owner`,
implementation_worker, implementation/remediation/verification, requested sol /
gpt-6.1-sol / medium. Coordinator `/root` owns commit/push/PR. Observed inherited
unrestricted filesystem/network and approval never; restrictions are instruction-only,
without backend model/access attestation. No delegation. ADR0049/0051 apply;
no prospective ledger, phase reservation or time grant.

One reviewable outcome: explain that risk tolerance and objective alone choose the
growth/defensive target. Required horizon and maximum tolerable drawdown remain
validated human-review context. The calculation neither enforces a drawdown limit
nor assesses horizon suitability. Add context-only labels/help to initial and typed
revision forms, visible notice beside review allocation, separate displayed Policy
notes, human-input metrics, and a notice before all generated explanations,
including restored text. CLI prints equivalent notice outside preserved state JSON.
Add a narrow static provider instruction without changing reference payloads.
Preserve existing widget identities, including implicit initial-widget identities
by explicitly retaining their original identity inputs where necessary.

Frozen invariants: I154-1 allocation bands/targets, exact money, screening and
construction unchanged; I154-2 profile requirements, ranges, typed revision and
routing unchanged (context does not bypass side effects); I154-3 schemas, stored
notes/limitations, artifacts/digests, receipts, graph keys/stages and selectors
unchanged; I154-4 consistent initial/revision/review/notes/explanation/CLI disclosure;
I154-5 no forecast, protection, guarantee or suitability claims.
Affected interfaces: presentation and static explanation-provider instruction.
JSON/state impact: **none**.

AC154-1: unchanged targets/cash across all risk/objective pairs and horizon/drawdown
boundaries, including aggressive/growth 1 year/5% and 60 years/90% both 95/5.
AC154-2: initial/revised context-only labels/help, visible review and Policy notes.
AC154-3: CLI/explanation notice, actual provider message capture showing static
clarification and unchanged reference payload. AC154-4: rendering preserves supplied
artifacts/review bytes; note-tamper rejection remains. AC154-5: explicit pre-change
saved policy/explanation restore, review and approval offline without provider;
existing retry/children/Issue153 markers preserved. AC154-6: historical evaluation
corpora/expectations unchanged, focused and standard checks, independent review.

Non-goals: change financial rules, add suitability rules, change saved notes or
limitations/validators/reference indexes, rewrite historical explanation text or
baselines, migrate saved reviews, change operation digest/replay, address other
Issue151 concerns, call sources/providers/services, run live research, trade, or
write to external financial systems. Successful receipts reuse saved results;
future explicitly authorized attempts/retries use the current static instruction.
The instruction is not bound into operation digests: no exact historical-prompt
replay or perfect semantic enforcement claim.

Docs: new ADR0053, current system and this iteration. Verification: locked dev and
dashboard dependencies; meaningful focused policy/profile/dashboard/revision/provider/
explanation/CLI tests including pre-change saved fixture; unchanged analysis/starter/
explanation evaluations; serial full pytest, role validator, Ruff lint/format, mypy,
build, Compose config, doc links and diff checks. Coordinator performs offline local
UI visual verification. Real-store gate does not apply to this presentation/static
instruction slice. Material financial/replay ambiguity returns to coordinator/design;
routine same-scope repair remains with owner. Remaining risks: disclosure cannot
prove suitability or fully enforce model semantics, and historical text remains
unchanged behind the current display notice. Actual failures and limits follow.

## Coordinator clarification: initial widget identity

Initial number inputs have implicit identities derived from label/help. Changing
those strings would conflict with preserved widget identity. Coordinator chose
adjacent always-visible, field-specific context-only captions while retaining all
initial number-input arguments. Revised widgets retain their existing explicit
keys and may change labels/help. Rejected alternative: reset implicit initial IDs
for a label suffix. Closure: rendered initial/revision forms mark each field as
context-only while original keys, ranges and routing remain unchanged. This is a
presentation clarification of AC154-2 against I154-2, not a new financial contract.

## Implementation and initial verification

Recorded this capsule/ADR/system update before runtime edits. Captured the synthetic
policy-only and explanation checkpoint fixture from merged main
`abfbf0eeeef8404237ce3d6d1e2359639b3aa820` before changing runtime code; its saved
policy notes, historical `review constraint` explanation text, limitations,
checkpoint/receipt artifacts and provider input payload remain unchanged.
New fixture is `tests/fixtures/issue154-pre-change.json`; this is offline synthetic
evidence, not live PostgreSQL durability or authenticated history.

Shared presentation constants now supply field captions/help, review/Policy notes,
explanation and CLI notices. No domain calculation, saved-state model/validator,
reference index, operation digest or evaluation corpus was edited. Initial input
arguments and revised widget keys/ranges remain exact. Static system instruction
alone changes future provider messages; human/reference JSON is tested against the
pre-change fixture. CLI disclosure precedes its original JSON projection and still
omits the retained ledger/capability.

Locked dev/dashboard installation succeeded. Initial new tests: **17 passed in
18.72s**, including pre-change checkpoint restore/render/approve without attached
adapters, exact display non-mutation, provider message capture/payload equality,
CLI and actual Streamlit AppTest form output. Initial Ruff before formatting found
two long lines and two automatically fixable import errors; formatting/import fixes
resolved them. Current Ruff lint and format pass (288 files); mypy passes (71 source
files), preset validator, wheel/source build, Compose config and diff check pass.
Changed documentation's local relative links resolve. Expanded focused tests and
remaining full/evaluation outcomes follow. During focused collection, owner added
two further tests proving context-only profile edits retain the existing retrieval/
provider invalidation/calls; that running suite had already collected the earlier
version. Those two tests receive their own run and the complete final suite.

Expanded focused suite: **557 passed in 158.86s**, covering policy/profile,
dashboard/revision controls, explanations, CLI, revision runtime, starter and
Issue153 selector/replay coverage. Additional context-edit tests first failed
(**2 failed**) because their test submission omitted the required `revise`
disposition for Edit. Adding the existing required disposition fixed the test
fixture; production routing was unchanged. Corrected tests: **2 passed in 1.50s**.
These verify unchanged targets/cash while both fake retrieval and provider calls
increase from one to two for a horizon-only or drawdown-only typed profile edit.

Coordinator's actual local browser check on 17 November used default policy-only
Streamlit with retrieval/provider/durable options off. It observed per-field
initial captions, uncollapsed disclosure above the 57.5/42.5 allocation, context
metrics, expanded Policy notes, and both context-only revised profile labels.
Review and revision viewport screenshots were visually inspected outside this
checkout. No decision submitted and no source/provider/database option enabled.
Browser overlay/element-screenshot timeouts were resolved using the visible Edit
label and ordinary viewport captures; no product failure was observed. This checks
those visible sections, not live providers, saved-store UI or the full document.

All three offline CLI evaluators exited 0 with `passed=true`: analysis (168,730
bytes), starter (1,960,078 bytes), explanations (5,016 bytes). Starter report SHA-256
`032b9a3957dfff49d22ef5087734f4631bb3a8674abfdb37e2b59a515579f8eb`
is exactly the prior accepted report. All 14 tracked files under the historical
evaluation directory are byte-identical to merged main. No existing fixture or
expected baseline was rewritten. The new pre-change saved-checkpoint fixture
SHA-256 is `470d80d632fbb51fe53b066234687ee67e055fd34a14adb711ccbf6c040548fd`.
Logs/reports are ignored local `.artifacts/issue154-*` evidence.

Owner self-review: policy calculation and complete policy equality checks are
untouched; notices are separate display calls and never appended to supplied
notes/limitations. Rendering directly supplied saved artifacts leaves payload JSON
and checkpoint state identical. Static provider clarification precedes unchanged
reference instructions; captured actual human message equals the pre-change payload.
Current instructions do not silently regenerate historical explanations or bypass
receipt reuse. Initial number inputs retain the exact original label/range/default/
step arguments; revisions keep their explicit keys and validated typed route.
Mandatory fields and all monetary/screening/construction logic remain unchanged.
No schema, graph stage, operation digest, receipt rule, selector, source adapter,
registry/store/persistence implementation, migration or financial write changed.

Real-store opt-in gate is not triggered by presentation/static-instruction changes;
no service, live source, real provider, trade or external financial write ran.
Saved checkpoint tests use in-memory durable-store doubles and synthetic data;
they establish compatibility/offline approval, not real PostgreSQL restart coverage.
Current text makes no suitability, drawdown protection, exact historical prompt
replay or perfect semantic entailment claim. Separate independent review and
coordinator delivery remain subsequent gates.

Final complete serial suite: **1,784 passed, 71 optional skips in 383.32s
(6:23), exit 0**. Log: ignored `.artifacts/issue154-full.log`. Runtime/test files
were unchanged during this full run. No full-suite failure occurred. This includes
the corrected context-edit tests, historical note-tamper rejection, saved restore/
retry/children and Issue153 marker regressions. No optional-service acceptance is
claimed from the skipped cases.

Local AC154-1 through AC154-5 and the local checks in AC154-6 pass. Owner self-review
found no unresolved defect against the frozen scope. All source/test edits are now
frozen for the separate independent review. Coordinator owns recording that review
and subsequent commit/push/PR/CI; this record does not assert those later outcomes.

## Independent review and coordinator delivery

Separate `/root/issue154_review`, code_reviewer assignment, requested sol /
gpt-6.1-sol / medium, returned **PASS** after owner verification. The reviewer
inspected all nine scoped files, neighboring consumers, the saved fixture and
recorded logs/reports, and found no concrete defect or material acceptance
uncertainty against I154-1 through I154-5 and AC154-1 through AC154-6. No edits,
test reruns or external actions were performed by that reviewer. Inherited access
was unrestricted with instruction-only read restrictions, without backend access
or model attestation. The reviewer was separate from the design author, owner
and coordinator's browser verification.

Coordinator accepts the reviewed disclosure outcome. This documentation-only
closeout records the review without changing runtime, tests or their evidence.
Commit/push/PR and CI follow; their links and outcomes belong in the issue/PR
delivery record. No merge or completed CI is asserted here.
