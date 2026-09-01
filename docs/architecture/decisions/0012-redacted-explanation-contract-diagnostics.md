# ADR 0012: Persist redacted explanation contract categories

- Status: Accepted
- Date: 2026-09-01

## Context

Two direct Ollama Cloud review attempts returned output that passed the generated-explanation
schema, then failed deterministic safety or grounding validation. The graph collapsed prohibited
claims, unknown references, subject mismatches, and unsupported numbers into the same generic
`explanation_contract` error. Because rejected model text is intentionally not checkpointed, the
saved review could not identify which local rule needed prompt or model investigation.

## Decision

Deterministic explanation validators raise a typed local contract error with one stable category:

- `prohibited_claim`
- `unknown_policy_reference`
- `unknown_source_reference`
- `subject_mismatch`
- `unsupported_numeric_claim`
- `contract_validation_error` for an unexpected validation-path failure

The explanation node persists the category with the existing generic failure message. The
dashboard labels it as a redacted local diagnostic. Generated text, model-supplied references,
unsupported values, prompts, source content, and raw provider responses remain outside graph state
and presentation.

## Consequences

- One future provider request can identify the deterministic rule that rejected otherwise
  schema-valid output.
- Saved review tokens remain useful for troubleshooting without replaying the provider call.
- The taxonomy is provider- and model-independent and does not weaken any validation rule.
- Unexpected validation exceptions still fail closed under a generic local category.
