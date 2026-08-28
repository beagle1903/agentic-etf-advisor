# Iteration 010: PostgreSQL-backed durable human review

- Status: Complete
- Started: 2026-08-28

## Goal

Allow one local dashboard review to survive browser-session or process loss without replaying the
workflow stages that ran before the human-review interrupt.

## Deliverables

- A replaceable checkpoint-store boundary with in-memory and PostgreSQL implementations.
- An opt-in dashboard control that creates PostgreSQL-backed workflow threads.
- Opaque UUID review tokens plus exact-token restore from a fresh graph instance.
- Restored-interrupt contract validation before approve, edit, or reject controls are rendered.
- Explicit UI and documentation boundaries separating durability from authentication.

## Acceptance criteria

- The default policy-only dashboard remains offline and uses no PostgreSQL connection.
- Durable create, restore, and resume operations use short-lived connections and the same thread
  identifier without retaining a live database connection in Streamlit session state.
- A browser URL carrying the exact review token can restore the saved state after session loss.
- Unknown, malformed, or non-version-4 tokens do not enumerate or reveal other checkpoints.
- A restored malformed interrupt fails closed before review controls are shown.
- Approve, edit, and reject resume the existing checkpoint without rerunning market-data,
  retrieval, or provider side effects.
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and `uv run pytest` pass.
- A real local PostgreSQL smoke test creates, restores, approves, and reloads one isolated thread.

## Deferred

- Authentication, authorization, accounts, and multi-user tenancy.
- Pending-review discovery, retention policy, deletion, and administrative audit UI.
- Concurrent reviewer conflict handling and production database operations.
- Hosted deployment and licensed market-data redistribution.
- Brokerage connections, ETF allocation selection, forecasts, suitability claims, and trades.

## Verification

- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes for 68 files.
- `uv run mypy` passes for 31 source files.
- `uv run pytest` passes offline (128 tests).
- `docker compose config --quiet` passes and `uv build` produces the source and wheel artifacts.
- A real PostgreSQL smoke test creates a durable policy review, restores it through a separately
  compiled graph, approves it, and reloads the completed checkpoint.
- In-app browser verification creates a PostgreSQL-backed review, restores the paused interrupt in
  a fresh tab from the URL token, approves it, and restores the completed result in another fresh
  tab with no browser-console warnings.
- The local DSN uses `127.0.0.1` plus a five-second connection timeout after live verification
  showed that `localhost` could wait on an unreachable Windows resolution path.
