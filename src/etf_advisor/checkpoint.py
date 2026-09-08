"""Replaceable checkpoint-store boundary for dashboard workflow sessions."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
from threading import RLock
from typing import Any, Protocol

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from etf_advisor.clock import Clock, system_utc_now
from etf_advisor.lifecycle import ExpiredPreview, LifecycleStore


class DashboardCheckpointStore(Protocol):
    """Open checkpointers without exposing connection ownership to the dashboard."""

    durable: bool

    def setup(self) -> None:
        """Initialize any required storage schema."""

    def open(self) -> Any:
        """Return a context manager yielding a LangGraph checkpointer."""

    def managed(self, thread_id: str, *, create: bool = False) -> Any:
        """Hold thread exclusion and enforce lifecycle across one invocation/read."""

    def inspect(self, thread_id: str) -> dict[str, Any]:
        """Return one exact thread's lifecycle status without renewing retention."""

    def preview_expired(self) -> ExpiredPreview:
        """Return a non-mutating, version-bound expired-thread prune plan."""

    def prune(self, preview: ExpiredPreview) -> dict[str, str]:
        """Delete only unchanged expired candidates from an explicit preview."""

    def delete(self, token: str, *, confirmed: bool = False) -> str:
        """Delete one exact confirmed UUID-v4 thread or fail closed."""


class MemoryCheckpointStore(LifecycleStore):
    """One process-local checkpointer used by the default offline dashboard path."""

    durable = False

    def __init__(self, *, clock: Clock = system_utc_now, retention_days: int = 30) -> None:
        if type(retention_days) is not int or not 1 <= retention_days <= 365:
            raise ValueError("Retention must be an integer from 1 to 365 days.")
        self.clock, self.retention_days = clock, retention_days
        self._saver = InMemorySaver()
        self._metadata: dict[str, dict[str, Any]] = {}
        self._locks: dict[str, Any] = {}
        self._registry_lock = RLock()

    def setup(self) -> None:
        """The in-memory saver has no external schema."""

    @contextmanager
    def open(self) -> Iterator[InMemorySaver]:
        yield self._saver

    def exclusion(self, thread_id: str) -> Any:
        with self._registry_lock:
            return self._locks.setdefault(thread_id, RLock())

    @contextmanager
    def atomic(self, saver: Any, thread_id: str) -> Iterator[None]:
        # Rollback only this thread, preserving unrelated concurrent work.
        storage = deepcopy(saver.storage.get(thread_id))
        writes = {k: deepcopy(v) for k, v in saver.writes.items() if k[0] == thread_id}
        blobs = {k: deepcopy(v) for k, v in saver.blobs.items() if k[0] == thread_id}
        metadata = deepcopy(self._metadata.get(thread_id))
        try:
            yield
        except BaseException:
            saver.delete_thread(thread_id)
            if storage is not None:
                saver.storage[thread_id] = storage
            saver.writes.update(writes)
            saver.blobs.update(blobs)
            self._metadata.pop(thread_id, None)
            if metadata is not None:
                self._metadata[thread_id] = metadata
            raise

    def read_metadata(self, saver: Any, thread_id: str) -> dict[str, Any] | None:
        return deepcopy(self._metadata.get(thread_id))

    def write_metadata(self, saver: Any, thread_id: str, value: dict[str, Any]) -> None:
        self._metadata[thread_id] = deepcopy(value)

    def metadata_items(self, saver: Any) -> list[tuple[str, dict[str, Any]]]:
        return list(deepcopy(self._metadata).items())

    def exists(self, saver: Any, thread_id: str) -> bool:
        return bool(saver.storage.get(thread_id)) or any(
            key[0] == thread_id for key in (*saver.writes, *saver.blobs)
        )

    def erase(self, saver: Any, thread_id: str) -> bool:
        found = self.exists(saver, thread_id) or thread_id in self._metadata
        saver.delete_thread(thread_id)
        self._metadata.pop(thread_id, None)
        return found

    def discard(self, thread_id: str) -> None:
        with self.exclusion(thread_id), self.open() as saver, self.atomic(saver, thread_id):
            self.erase(saver, thread_id)


class PostgresCheckpointStore(LifecycleStore):
    """Short-lived PostgreSQL connections around durable LangGraph operations."""

    durable = True

    def __init__(
        self, connection_uri: SecretStr, *, clock: Clock = system_utc_now, retention_days: int = 30
    ) -> None:
        if type(retention_days) is not int or not 1 <= retention_days <= 365:
            raise ValueError("Retention must be an integer from 1 to 365 days.")
        self.clock, self.retention_days = clock, retention_days
        self._connection_uri = connection_uri

    def setup(self) -> None:
        """Create or migrate the LangGraph checkpoint tables idempotently."""

        with self.open() as saver:
            saver.setup()
            saver.conn.execute(
                "CREATE TABLE IF NOT EXISTS advisor_lifecycle "
                "(thread_id TEXT PRIMARY KEY, record JSONB NOT NULL)"
            )

    @contextmanager
    def open(self) -> Iterator[Any]:
        try:
            module = import_module("langgraph.checkpoint.postgres")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "PostgreSQL checkpoint support is missing. "
                "Run: uv sync --extra dashboard --extra checkpoint"
            ) from exc

        saver_type = module.PostgresSaver
        with saver_type.from_conn_string(self._connection_uri.get_secret_value()) as saver:
            yield saver

    @contextmanager
    def exclusion(self, thread_id: str) -> Iterator[None]:
        # A separate session-level lock survives per-checkpoint commits. No invocation-wide
        # transaction may hide a started receipt until after its external operation.
        with self.open() as owner:
            owner.conn.execute("SET lock_timeout = '5s'")
            owner.conn.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (thread_id,))
            try:
                yield
            finally:
                owner.conn.execute(
                    "SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (thread_id,)
                )

    def atomic(self, saver: Any, thread_id: str) -> Any:
        return saver.conn.transaction()

    def read_metadata(self, saver: Any, thread_id: str) -> dict[str, Any] | None:
        row = saver.conn.execute(
            "SELECT record FROM advisor_lifecycle WHERE thread_id = %s", (thread_id,)
        ).fetchone()
        return None if row is None else dict(row["record"])

    def write_metadata(self, saver: Any, thread_id: str, value: dict[str, Any]) -> None:
        jsonb = import_module("psycopg.types.json").Jsonb
        saver.conn.execute(
            "INSERT INTO advisor_lifecycle (thread_id, record) VALUES (%s, %s) "
            "ON CONFLICT (thread_id) DO UPDATE SET record = EXCLUDED.record",
            (thread_id, jsonb(value)),
        )

    def metadata_items(self, saver: Any) -> list[tuple[str, dict[str, Any]]]:
        return [
            (row["thread_id"], dict(row["record"]))
            for row in saver.conn.execute(
                "SELECT thread_id, record FROM advisor_lifecycle"
            ).fetchall()
        ]

    def exists(self, saver: Any, thread_id: str) -> bool:
        return any(
            saver.conn.execute(
                f"SELECT 1 FROM {table} WHERE thread_id = %s LIMIT 1", (thread_id,)
            ).fetchone()
            is not None
            for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes")
        )

    def erase(self, saver: Any, thread_id: str) -> bool:
        found = self.exists(saver, thread_id) or self.read_metadata(saver, thread_id) is not None
        # Fixed table allowlist, parameterized exact thread, all namespaces in one transaction.
        for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints", "advisor_lifecycle"):
            saver.conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (thread_id,))
        return found
