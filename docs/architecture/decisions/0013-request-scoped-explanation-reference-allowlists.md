# ADR 0013: Constrain generated references with request-scoped allowlists

- Status: Accepted
- Date: 2026-09-01

## Context

The first direct Ollama Cloud attempt after contract diagnostics were added returned a valid
generated-explanation object but failed with `unknown_policy_reference`. The prompt already said
to use keys from the policy reference index, but the generic JSON schema still allowed any string
inside a statement's `references` array.

Silently rewriting an invented reference to a similar policy key would hide provider behavior and
could attach a statement to support the model did not identify. Retrying with a repaired prompt
would also spend a second provider request and make review creation less predictable.

## Decision

Every explanation prompt includes a `reference_contract` with separate exact lists for
`policy_calculation` and `source_evidence`. The system instruction requires each reference to be
copied character-for-character from the list matching the statement basis and prohibits aliases,
prefixes, suffixes, and renamed keys.

For the plain-text Ollama Cloud path, the request-scoped schema embedded in the prompt also adds an
enum containing the allowed reference strings and an enum containing the retrieved source symbols.
Provider-enforced local Ollama and OpenRouter schemas remain static, while their prompts receive
the same explicit reference contract. Existing deterministic validation remains authoritative for
every provider.

## Consequences

- The Cloud model receives machine-readable constraints for values that vary on each request.
- The implementation remains model-name independent and makes one provider invocation.
- Unknown references are still rejected; the adapter does not guess or normalize model output.
- Schema enums improve steering but cannot guarantee provider compliance, so the local contract
  remains fail closed.
