# Iteration 011: Explanation and safety evaluation baseline

- Status: Complete
- Started: 2026-08-29

## Goal

Measure whether curated provider outputs are allowed or blocked by the exact production
pre-review validator before adding more model-led advisory behavior.

## Deliverables

- A versioned offline request and eight curated provider-output cases.
- Explicit coverage for citation validity, claim support, ETF/source agreement, refusal
  behavior, unsafe financial language, and prompt-injection resistance.
- A deterministic evaluator that replays cases through `validate_and_bundle_explanation`.
- Per-dimension accuracy, sanitized case decisions, and one fail-closed aggregate gate.
- An `etf-advisor evaluate-explanations` command that emits stable JSON and exits nonzero when
  any curated decision regresses.
- Refusal replay through the production explanation node rather than an evaluator-owned decision.
- A deterministic numeric-claim guard requiring every generated number to exist in that
  statement's exact cited policy fields or source records.

## Acceptance criteria

- The packaged baseline runs without credentials, providers, databases, network calls, or a
  wall clock and produces byte-for-byte stable CLI output.
- A safe, grounded response that ignores an instruction embedded in source text reaches review.
- Unknown source references and mismatched ETF subjects fail before review.
- Provider refusal produces no review-ready explanation.
- Guaranteed outcomes and a followed prompt-injection trade instruction fail before review.
- A fabricated expense ratio, including leading-decimal forms such as `.03%`, fails even though
  it cites a real source, because the numeric fact is absent from that source.
- A truthful negative guarantee disclaimer remains accepted to cover a safety false-positive
  boundary.
- Missing evaluation dimensions, duplicate case IDs, and ambiguous result/refusal fixtures are
  rejected during dataset validation.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and
  `uv run pytest` pass offline.

## Boundaries and deferred work

- The numeric-claim guard is deterministic support checking, not general semantic entailment.
  Broader paraphrase and contradiction judgments require curated human labels or a separately
  evaluated optional judge.
- LangSmith-hosted datasets and runs remain optional and are deferred until there are
  credentialed provider outputs worth comparing; the offline gate remains authoritative in CI.
- Multilingual safety cases, larger adversarial sets, statistical confidence, and live-provider
  comparisons remain future evaluation expansions.
- ETF selection, portfolio construction, suitability claims, forecasts, brokerage connections,
  and trades remain out of scope.

## Verification

- `uv run etf-advisor evaluate-explanations` reports eight of eight expected decisions correct
  and `1.0` accuracy for all six dimensions.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes for 73 files.
- `uv run mypy` passes for 33 source files.
- `uv run pytest` passes offline (140 tests).
- `docker compose config --quiet` passes.
- `uv build` produces source and wheel artifacts, and the wheel contains both versioned
  evaluation JSON files.
- Repeated CLI output is byte-for-byte stable, and a deliberately inverted expectation makes
  the command exit nonzero.

## Review correction

Automated review found that leading-decimal values such as `.03%` were not tokenized and could
skip numeric-support validation. The numeric grammar now accepts signed leading-dot and
leading-comma decimals, and both the unit suite and packaged baseline cover the bypass.

Review also found that the refusal dimension assigned `reject` inside the evaluator, so it could
not detect a production workflow regression. The refusal fixture now calls the production
`draft_explanation` node with a generator that raises `ExplanationGenerationError` and requires
the complete blocked-state contract. A regression test replaces that node with an unsafe
review-ready result and proves the dimension and aggregate gate fail.
