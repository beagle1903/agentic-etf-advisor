# Iteration 015: Ollama Cloud provider compatibility

- Status: Complete
- Started: 2026-09-01
- Completed: 2026-09-01

## Goal

Make optional grounded explanations usable and diagnosable across Ollama Cloud models without
weakening the existing fail-closed review boundary.

## Deliverables

- Endpoint-capability routing for local Ollama, Ollama Cloud, and OpenRouter.
- A model-agnostic Ollama Cloud JSON-text path with strict local Pydantic validation.
- Stable redacted provider diagnostics persisted in JSON-serializable graph state.
- Stable redacted local contract diagnostics persisted in JSON-serializable graph state.
- Request-scoped policy/source reference allowlists and Cloud schema enums.
- Dashboard and CLI visibility for provider, model, method, failure category, and optional HTTP
  status.
- Offline regression coverage for endpoint routing, JSON extraction, sanitization, state
  persistence, and dashboard rendering.

## Acceptance criteria

- Ollama Cloud never receives the unsupported JSON-schema `format` parameter.
- The Cloud adapter makes one provider invocation per review attempt and performs no automatic
  fallback retry.
- Cloud output cannot reach human review unless it passes the exact explanation schema plus all
  deterministic grounding and financial-safety validation.
- Provider credentials, prompts, source content, and raw responses are absent from checkpoints and
  UI diagnostics.
- Parsed output that fails a deterministic local rule identifies the rule category without
  checkpointing generated text, model references, or unsupported values.
- A configured model that returns malformed JSON fails with `invalid_response` and identifies the
  provider, model, and `prompt_json` method.
- Provider prompts identify the exact references allowed for each grounding basis, and the Cloud
  schema enumerates those strings without normalizing an unknown response.
- Local Ollama continues to use `json_schema`; OpenRouter continues to use strict
  `function_calling`.
- Ruff, formatting, mypy, the full offline test suite, packaging, Docker Compose validation, and
  one explicitly approved Cloud verification request complete successfully.

## Verification

- `uv run pytest` passes all 219 offline tests.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes in strict mode.
- `uv build` produces the source and wheel artifacts.
- `docker compose config --quiet` passes.
- `git diff --check` passes.
- One approved Cloud function-calling probe reached `gemma4:31b` but returned tool arguments that
  failed the nested explanation contract, motivating the final model-agnostic `prompt_json` path.
- Live verification of the then-new `prompt_json` path was still pending at that point; no
  additional Cloud request was made before that implementation was pushed.
- Two later direct Ollama Cloud review attempts returned schema-valid explanations but both stopped
  at the generic deterministic contract boundary. Evidence and screening were ready in both runs.
  This verified the `prompt_json` routing path but exposed the need for redacted local rule codes
  before spending another provider request.
- The first live attempt after adding local rule diagnostics returned `unknown_policy_reference`.
  The follow-up implementation makes the policy/source allowlists explicit and constrains the
  request-scoped Cloud schema while retaining the same fail-closed validator and one-request rule.
- One explicitly approved verification run from current `main` commit `3e5a253` used Ollama Cloud
  with `gemma4:31b` and the `prompt_json` path. The single request returned a schema-valid,
  deterministically grounded explanation with no explanation errors, reached the human-review
  boundary, and completed successfully. No fallback request or automatic retry was made.
