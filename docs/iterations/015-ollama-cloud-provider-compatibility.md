# Iteration 015: Ollama Cloud provider compatibility

- Status: In progress
- Started: 2026-09-01

## Goal

Make optional grounded explanations usable and diagnosable across Ollama Cloud models without
weakening the existing fail-closed review boundary.

## Deliverables

- Endpoint-capability routing for local Ollama, Ollama Cloud, and OpenRouter.
- A model-agnostic Ollama Cloud JSON-text path with strict local Pydantic validation.
- Stable redacted provider diagnostics persisted in JSON-serializable graph state.
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
- A configured model that returns malformed JSON fails with `invalid_response` and identifies the
  provider, model, and `prompt_json` method.
- Local Ollama continues to use `json_schema`; OpenRouter continues to use strict
  `function_calling`.
- Ruff, formatting, mypy, the full offline test suite, packaging, Docker Compose validation, and
  one explicitly approved Cloud verification request complete successfully.

## Verification

- `uv run pytest` passes all 217 offline tests.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `uv run mypy` passes in strict mode.
- `uv build` produces the source and wheel artifacts.
- `docker compose config --quiet` passes.
- `git diff --check` passes.
- One approved Cloud function-calling probe reached `gemma4:31b` but returned tool arguments that
  failed the nested explanation contract, motivating the final model-agnostic `prompt_json` path.
- Live verification of the final `prompt_json` path remains pending; no additional Cloud request
  was made before this implementation was pushed.
