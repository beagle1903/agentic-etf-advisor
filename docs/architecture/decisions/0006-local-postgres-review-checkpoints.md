# ADR 0006: Restore local reviews by opaque PostgreSQL thread token

- Status: Accepted
- Date: 2026-08-28

## Context

The first dashboard keeps its LangGraph checkpointer and compiled graph inside one Streamlit
browser session. This proves the human-review lifecycle, but a refresh or process restart loses
the only handle to the paused workflow. ADR 0002 requires durable checkpointing before review can
reliably happen later.

Durability does not by itself provide user identity, authorization, concurrency control, or a
safe multi-user listing of pending financial reviews.

## Decision

Keep the offline in-memory dashboard as the default. Add an explicit durable option that stores
LangGraph checkpoints in the existing local PostgreSQL service. Create each durable thread with a
random version-4 UUID and restore only the exact thread named by that opaque review token. Do not
enumerate database threads in the dashboard.

Open a short-lived PostgreSQL connection for each create, restore, or resume operation. Recompile
the graph against the same checkpoint store and revalidate the complete interrupt payload before
rendering review controls. A restored graph resumes from the saved human-review interrupt; it does
not replay retrieval or provider side effects. The local default DSN uses the container's explicit
IPv4 loopback binding and a bounded connection timeout so service failures return control to the
dashboard.

The review token is a local capability reference, not authentication. The dashboard must state
that boundary and must not describe this slice as multi-user or production-ready.

## Consequences

- A user can restore a paused or completed local review after losing the browser session.
- PostgreSQL and the optional checkpoint dependency are required only when durable mode is used.
- Database connection strings remain secret settings and are not rendered or logged.
- Anyone with local database access or a review token may be able to access that development
  checkpoint; authentication and per-user authorization remain a separate iteration.
- Checkpoint deletion, retention, thread discovery, and concurrent-review conflict handling are
  deferred until an authenticated lifecycle exists.
