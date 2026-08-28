# ADR 0004: Validate structured explanation grounding before review

- Status: Accepted
- Date: 2026-08-28

## Context

The workflow has deterministic policy calculations and freshness-checked source evidence,
but a free-form model response could still invent references, blur calculated policy with
retrieved facts, obey instructions embedded in source text, or reach human review after a
provider failure.

## Decision

Inject an `ExplanationGenerator` behind an explicit side-effect boundary. The provider
receives a bounded prompt containing an allowlisted policy-reference index and at most ten
ranked source records. Source content is marked as untrusted quoted data.

Require structured output whose every statement declares either `policy_calculation` or
`source_evidence` grounding. Policy references must be exact allowlisted keys. Evidence
references must be exact exposed document IDs, and each statement's ETF subjects must match
the cited records. The workflow derives citation URLs and timestamps from validated evidence
rather than accepting them from the model.

Provider errors, malformed output, unknown references, and mismatched subjects stop the
workflow before human review. Deterministic limitations are appended after generation. The
existing policy-only and evidence-only paths remain available without credentials.

## Consequences

- Ollama and OpenRouter remain optional adapters selected through environment settings.
- Offline workflow tests use deterministic fake generators and make no provider calls.
- Structural attribution is enforced, but semantic entailment quality still needs a curated
  explanation evaluation set in a later iteration.
- The dashboard can render one stable explanation bundle with provider identity, statements,
  citations, and limitations.

## Review hardening

Automated review identified that valid references alone could not stop a schema-valid model
response from promising returns or issuing a trade recommendation. A deterministic pre-review
safety gate now rejects explicit guarantees, personalized or imperative trade instructions,
recommendation and suitability language, forecasts, and risk-free outcomes. Fixed limitations
remain presentation context rather than the enforcement mechanism.

The adapter also normalizes every ordinary provider exception into the sanitized
`ExplanationGenerationError`. This includes SDK-specific exceptions that do not inherit from
the narrower built-in exception types previously listed. Process-control exceptions derived
directly from `BaseException` are not swallowed.
