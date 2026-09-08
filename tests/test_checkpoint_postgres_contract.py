"""Exercise PostgreSQL adapter statements/transactions with an isolated connection double."""

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr
from test_checkpoint_lifecycle import OTHER, TOKEN, Time, decision, invoke, start

from etf_advisor.checkpoint import MemoryCheckpointStore, PostgresCheckpointStore


class Connection:
    def __init__(self, memory: MemoryCheckpointStore) -> None:
        self.memory = memory
        self.transactions = 0
        self.depth = 0
        self.locked = False
        self.fail_table: str | None = None
        self.statements: list[str] = []

    @contextmanager
    def transaction(self) -> Iterator[None]:
        assert self.locked and self.depth == 0
        self.depth += 1
        self.transactions += 1
        saver = self.memory._saver
        before = deepcopy((saver.storage, saver.writes, saver.blobs, self.memory._metadata))
        try:
            yield
        except BaseException:
            saver.storage, saver.writes, saver.blobs, self.memory._metadata = before
            raise
        finally:
            self.depth -= 1

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        self.statements.append(sql)
        rows: list[Any] = []
        saver = self.memory._saver
        if "pg_advisory_unlock" in sql:
            assert self.locked and self.depth == 0
            self.locked = False
        elif "pg_advisory_lock" in sql:
            assert not self.locked and self.depth == 0
            self.locked = True
        elif sql == "SET lock_timeout = '5s'":
            assert not self.locked and self.depth == 0
        elif sql.startswith("CREATE TABLE"):
            pass
        elif sql.startswith("SELECT record"):
            raw = self.memory._metadata.get(params[0])
            rows = [] if raw is None else [{"record": deepcopy(raw)}]
        elif sql.startswith("SELECT thread_id"):
            rows = [
                {"thread_id": k, "record": deepcopy(v)} for k, v in self.memory._metadata.items()
            ]
        elif sql.startswith("INSERT INTO advisor_lifecycle"):
            assert self.depth == 1
            self.memory._metadata[params[0]] = deepcopy(params[1].obj)
        elif sql.startswith("SELECT 1"):
            table = sql.split()[3]
            key = params[0]
            present = (
                bool(saver.storage.get(key))
                if table == "checkpoints"
                else any(
                    k[0] == key
                    for k in (saver.writes if table == "checkpoint_writes" else saver.blobs)
                )
            )
            rows = [{"exists": 1}] if present else []
        elif sql.startswith("DELETE FROM"):
            assert self.depth == 1
            table = sql.split()[2]
            key = params[0]
            if table == self.fail_table:
                raise RuntimeError("private simulated database failure")
            if table == "advisor_lifecycle":
                self.memory._metadata.pop(key, None)
            elif table == "checkpoints":
                saver.storage.pop(key, None)
            else:
                mapping = saver.writes if table == "checkpoint_writes" else saver.blobs
                for item in list(mapping):
                    if item[0] == key:
                        del mapping[item]
        else:
            raise AssertionError(sql)
        return SimpleNamespace(fetchone=lambda: rows[0] if rows else None, fetchall=lambda: rows)


class PostgresDouble(PostgresCheckpointStore):
    def __init__(self, time: Time) -> None:
        super().__init__(SecretStr("unused-test-connection"), clock=time)
        self.memory = MemoryCheckpointStore(clock=time)
        self.conn = Connection(self.memory)
        self.memory._saver.conn = self.conn

    @contextmanager
    def open(self) -> Iterator[Any]:
        yield self.memory._saver


def test_postgres_contract_independent_commits_preview_delete_and_rollback() -> None:
    pytest.importorskip("psycopg")
    time = Time()
    store = PostgresDouble(time)
    state = start(store)
    assert store.conn.transactions > 1
    assert store.conn.depth == 0 and not store.conn.locked
    initial = store.inspect(TOKEN)
    time.now += timedelta(days=1)
    invoke(store, decision(state, time))
    assert (
        store.inspect(TOKEN)["lifecycle"]["last_activity_at"]
        != initial["lifecycle"]["last_activity_at"]
    )
    start(store, OTHER)
    store.conn.fail_table = "checkpoints"
    before = store.inspect(TOKEN)
    assert store.delete(TOKEN, confirmed=True) == "failure"
    assert store.inspect(TOKEN) == before
    assert store.memory._saver.blobs and store.memory._saver.writes
    store.conn.fail_table = None
    assert store.delete(TOKEN, confirmed=True) == "deleted"
    assert store.delete(TOKEN, confirmed=True) == "not_found"
    assert store.inspect(OTHER)["status"] == "active"
    time.now += timedelta(days=30)
    assert store.prune(store.preview_expired()) == {OTHER: "deleted"}
    assert all(TOKEN not in sql and OTHER not in sql for sql in store.conn.statements)
    assert "SET lock_timeout = '5s'" in store.conn.statements
