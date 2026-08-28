"""Replaceable checkpoint-store boundary for dashboard workflow sessions."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from importlib import import_module
from typing import Any, Protocol

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr


class DashboardCheckpointStore(Protocol):
    """Open checkpointers without exposing connection ownership to the dashboard."""

    durable: bool

    def setup(self) -> None:
        """Initialize any required storage schema."""

    def open(self) -> Any:
        """Return a context manager yielding a LangGraph checkpointer."""


class MemoryCheckpointStore:
    """One process-local checkpointer used by the default offline dashboard path."""

    durable = False

    def __init__(self) -> None:
        self._saver = InMemorySaver()

    def setup(self) -> None:
        """The in-memory saver has no external schema."""

    @contextmanager
    def open(self) -> Iterator[InMemorySaver]:
        yield self._saver


class PostgresCheckpointStore:
    """Short-lived PostgreSQL connections around durable LangGraph operations."""

    durable = True

    def __init__(self, connection_uri: SecretStr) -> None:
        self._connection_uri = connection_uri

    def setup(self) -> None:
        """Create or migrate the LangGraph checkpoint tables idempotently."""

        with self.open() as saver:
            saver.setup()

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
