# ADR 0011: Route explanation output by provider capability

- Status: Accepted
- Date: 2026-09-01

## Context

The explanation adapter originally used Ollama's JSON-schema `format` parameter for both local
Ollama and the direct `https://ollama.com` API. Ollama Cloud does not currently support that
structured-output capability. Ten durable review attempts reached the provider and stopped with
the same generic generation error, while the saved graph state retained no provider, model,
output method, or failure category that could explain the problem.

Switching every Cloud model to function calling would still make the adapter depend on a
model-specific tool implementation. A live `gemma4:31b` probe reached Ollama Cloud but did not
produce tool arguments that validated against the nested explanation schema.

## Decision

Select the Ollama output path from the configured endpoint rather than from a hard-coded model
allowlist:

- Local Ollama keeps provider-enforced JSON-schema output.
- Direct Ollama Cloud receives the same bounded prompt plus the explicit Pydantic JSON schema and
  returns ordinary text. The adapter extracts a bounded JSON object and validates it locally with
  the exact `GeneratedExplanation` contract.
- OpenRouter keeps strict function calling.

All paths still pass through the existing deterministic citation, subject, numeric-support, and
financial-claim validation before human review. Plain Cloud text is never rendered directly.
Malformed or unsupported output remains fail-closed.

Provider failures receive a stable redacted category together with provider, model, output method,
and an optional HTTP status. Credentials, prompts, retrieved source content, and raw model responses
never enter graph state or dashboard diagnostics. The adapter logs only the same redacted fields and
the exception class.

## Consequences

- The Cloud path is not coupled to Gemma or to a static list of tool-capable models.
- Any text-capable Cloud model may satisfy the contract, but no model is guaranteed to do so; local
  validation remains authoritative and stops invalid output after one request.
- Local Ollama retains stronger provider-side schema enforcement where it is supported.
- Saved reviews and the CLI/dashboard expose enough non-secret context to distinguish credentials,
  rate limits, unsupported capabilities, unavailability, invalid responses, and other provider
  failures.
- A model change remains an environment setting and does not require application code changes.
