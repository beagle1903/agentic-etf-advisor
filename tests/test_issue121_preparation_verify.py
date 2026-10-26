"""Bounded offline preparation verification never repairs malformed inputs."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_prepared_references import MAX_SNAPSHOT_BYTES, summarize


def test_rejects_naive_check_time_before_read(tmp_path):
    with pytest.raises(ValueError, match="timezone-aware"):
        summarize(tmp_path / "reference.json", tmp_path / "snapshot.json", datetime(2026, 10, 26))


def test_rejects_oversized_snapshot_before_json_or_reference(tmp_path):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_bytes(b"x" * (MAX_SNAPSHOT_BYTES + 1))
    with pytest.raises(ValueError, match="16 MiB"):
        summarize(tmp_path / "reference.json", snapshot, datetime(2026, 10, 26, tzinfo=UTC))
