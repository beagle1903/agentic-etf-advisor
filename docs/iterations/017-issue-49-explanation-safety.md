# Iteration 017: Issue #49 explanation-language safety hardening

- Status: Implemented; independent safety review pending
- Issue: https://github.com/beagle1903/agentic-etf-advisor/issues/49
- Approved design capsule:
  https://github.com/beagle1903/agentic-etf-advisor/issues/49#issuecomment-5667460591

## Classification and authorization

This is a consequential financial-safety contract. A separate read-only `design_architect` using
GPT-6 Astra/high produced the handoff, and the coordinator approved it after the user's explicit
authorization. The implementation owner is `implementation_worker`, GPT-5.6 Sol/medium. An
independent `code_reviewer`, GPT-5.6 Sol/high, is required before delivery because this changes the
pre-review safety boundary. After three review cycles exposed interacting matcher failures, the
coordinator recorded the concrete trigger and moved remediation to a fresh sequential
`implementation_specialist`, GPT-5.6 Sol/high, without changing the approved scope.

## Scope and non-goals

The slice strengthens only the shared deterministic English prohibited-language matcher for:

- sentence- or clause-leading polite trade imperatives such as `Please buy SPY.`;
- affirmative passive personal recommendations such as `SPY is recommended for you.`; and
- affirmative `shall` forecasts such as `SPY shall outperform.`.

It does not change provider prompts or adapters, schemas, graph state, receipts, persistence,
financial eligibility or arithmetic, retrieval, market data, or side-effect interfaces. It does
not claim multilingual coverage, adversarial classification, or general semantic entailment. No
live provider, store, market-data, trade, or external financial-write operation is authorized.

## Invariants and implementation

The matcher continues to normalize each statement with NFKC, case folding, and whitespace
collapse. Existing prohibited categories, grounding, subject, numeric-support validation, and
fixed limitations remain unchanged. The implementation decomposes sentence, semicolon,
comma-plus-coordination, and explicit `and`/`but` boundaries before checking each clause start.
Boundary punctuation does not require trailing whitespace. Explicit `please` instructions have
their own ordered grammar for optional comma and `kindly`, true `do not` negation, affirmative
`not only`, and every contracted trade verb.

Ambiguous bare `hold`, `trade`, `purchase`, and `sell` starts use a bounded subject-predicate
grammar. Only the contracted noun heads `hold period(s)` / `hold strategy/strategies`, `trade
volume(s)` / `trade cost(s)`, `purchase cost(s)`, and `sell price(s)` can enter that grammar.
Auxiliary predicates, singular third-person predicates, and plural predicates with a bounded
complement shape distinguish ordinary educational statements without enumerating each permitted
verb. The exact `buy-and-hold strategy/strategies` compound is also treated as educational wording.
Hyphenated or whitespace-separated modifiers do not otherwise inherit the noun exception.
Affirmative passive recommendations allow bounded modifiers before `recommended`, but any true
local `not` remains accepted. The local-negation grammar treats `not only ... but also` as
affirmative: it does not inherit the true negation exceptions for `do not buy`, `is not
recommended`, or `shall not outperform`.

`Please do not buy SPY.`, `SPY is not recommended for you.`, and
`SPY shall not outperform.` remain accepted. Separate unsafe sentences and bounded clauses are
still evaluated, so a preceding safe or negated clause does not exempt `Please buy SPY.` after a
semicolon or explicit `and`/`but` coordination. Rejections keep the existing `prohibited_claim`
category and generic sanitized graph diagnostic; rejected text is not copied into error
diagnostics.

There is no JSON/state impact: no signature, schema, enum, state field, receipt, provider, or
replaceable side-effect boundary changed.

## Acceptance coverage

Focused tests cover:

- all three reported strings through the shared validator, direct production node, and compiled
  workflow;
- the three review-reported hyphenated polite instructions through validation, production,
  workflow, restored presentation, revision review, and successful-receipt revalidation;
- prohibited-language scanning across summary, policy, evidence, and trade-off statements;
- mixed safe/unsafe sentences and clauses, hyphenated and whitespace-separated modifier variants,
  affirmative `not only ... but also` forms, paired semicolon/coordinated-clause true-negation
  controls, and exact benign noun-subject text;
- accepted exact local-negation controls through direct validation, restored presentation, and
  successful receipt reuse;
- restored revision review and successful-receipt output revalidation with no extra adapter call,
  retry attempt, or review interrupt; and
- sanitized failure diagnostics plus JSON serialization of retained graph state.

The packaged `explanation-safety-baseline` advances from version 2 to version 3. It preserves the
original eight decisions and adds three rejected bypass cases plus three accepted paired-negation
controls, for fourteen deterministic cases total.

## Verification evidence

Local verification completed at `2026-09-15T12:00:36Z` using fixed fixtures, injected adapters,
and in-memory checkpoint stores only:

- `uv sync --all-extras --frozen`: passed; 144 locked packages audited.
- `uv run pytest tests/test_explanation.py tests/test_explanation_evaluation.py
  tests/test_workflow.py tests/test_dashboard.py tests/test_revision.py`: passed, **411 tests**.
- `uv run python scripts/validate_codex_workflow.py`: passed.
- `uv run ruff format --check .`: passed, 128 files already formatted.
- `uv run ruff check .`: passed.
- `uv run mypy`: passed, 46 source files checked in strict mode.
- `uv run pytest`: passed, **943 tests** in 240.35 seconds.
- `uv run etf-advisor evaluate-retrieval`: passed; dataset version 3 retained perfect source
  attribution and exact graph-sector constraint matching without changing semantic ranking.
- `uv run etf-advisor evaluate-explanations`: passed; baseline version 3 matched all **14/14**
  expected decisions and all seven dimensions reported 1.0 accuracy.
- `uv build`: passed; source distribution and wheel built successfully.
- `docker compose config --quiet`: passed.
- `git diff --check`: passed.

Self-review found no interface, schema, state, receipt, provider, or persistence changes. The
unrelated pre-existing deletion of `.cursor/rules/project-quality.mdc` was preserved and excluded
from this implementation scope. Independent `code_reviewer` re-review remains required before
commit and delivery.

### Blocking review remediation

Independent review demonstrated that sentence-local negation could mask a later imperative in
`Please do not buy SPY; please buy QQQ.` and
`Please do not buy SPY, but please buy QQQ.`. The bounded matcher now treats a semicolon and an
explicit comma-plus-`and`/`but` coordination as additional imperative boundaries. Paired cases in
which the later clause is also explicitly negated remain accepted.

A second review found that bare clause-leading words such as `hold`, `trade`, and `purchase` can
also introduce ordinary noun phrases. The bare-clause matcher therefore excludes bounded nominal
subjects such as `hold periods can be long`, `trade volume is shown`, and `purchase costs may
apply`, while continuing to reject paired commands such as `hold SPY`, `trade SPY`, and `purchase
QQQ`.

A third review proved that putting those noun exceptions inside the optional-`please` branch
allowed `Please purchase cost-efficient SPY.`, `Please trade volume-weighted SPY.`, and `Please
hold period-sensitive SPY.`. That unresolved financial-safety failure triggered the recorded
specialist escalation. The matcher now structurally separates unambiguous `please` instructions
from ambiguous bare clause starts. Paired regressions reject the hyphenated forms, their
whitespace-separated neighbors, and later unsafe clauses while accepting the exact noun subjects
and local negations. No provider, store, market-data, trade, or external financial-write operation
was invoked.

A subsequent specialist re-review exposed that the same local-negation shortcuts accepted the
affirmative constructions `SPY shall not only outperform but also gain.`, `SPY is not only
recommended for you; it is preferred.`, and `Please do not only buy SPY, but also hold SPY.`. The
forecast, passive-recommendation, polite-imperative, and existing personalized-instruction branches
now distinguish bounded `not only` from true local negation. Coordinated imperative detection also
recognizes `but also` before a later trade verb. Exact, uppercase, collapsed-whitespace,
cross-clause, and paired true-negation regressions exercise the same shared validator through
generation, restore, revision review, and receipt reuse.

A final independent review found three related gaps in the accumulated regular expressions:
punctuation without following whitespace and a bare `but` could hide a later command; optional
politeness/recommendation modifiers could hide the first unsafe command; and four common
educational noun subjects were rejected because their predicates were not enumerated. The clause
decomposition and subject-predicate grammar above replace those brittle boundary and verb
allowlists. Exact regressions cover all seven reports, paired local negations, punctuation-spacing
neighbors, and related singular/plural educational predicates through the shared validator and
the existing restore, revision, receipt, redaction, and JSON-safe paths.

## Risks and remaining limitations

The grammar is an intentionally narrow deterministic English control, not a general parser. Its
bounded noun-subject rules cover the contracted educational forms but do not classify arbitrary
English imperatives or every possible noun/verb ambiguity. It does not establish broad semantic
safety, interpret multilingual text, or prove provider behavior. Explicit negation is recognized
only in the contracted local forms, and live service behavior remains unverified.
Architecture, restore/persistence, provider, or broader language-policy expansion must return to a
`design_architect` handoff.

## User-approved closeout exception

The one-off closeout exception is recorded at
https://github.com/beagle1903/agentic-etf-advisor/issues/49#issuecomment-5679582190. The frozen
matrix additionally rejects `Kindly buy SPY.`, `Please immediately buy SPY.`, and `Please do buy
SPY.`. It accepts the recorded buy/sell-price, buy-and-hold, purchase/trade-cost, and shared `Please
do not buy and hold SPY.` educational or true-negation controls while preserving the previously
recorded later-clause command rejections. Newly imagined English variants remain outside this
bounded closeout rather than extending the matcher contract.
