from pathlib import Path

import pytest
from test_research_snapshot import research_snapshot

from etf_advisor.research.snapshot_io import (
    default_snapshot_path,
    load_research_snapshot,
    persist_research_snapshot,
)


def test_snapshot_payload_round_trip_is_digest_stable(tmp_path: Path) -> None:
    snapshot = research_snapshot()
    path = tmp_path / "canonical.json"

    assert persist_research_snapshot(snapshot, path) == path

    restored = load_research_snapshot(path)
    assert restored == snapshot
    assert restored.content_digest() == snapshot.content_digest()


def test_snapshot_payload_refuses_different_content_at_same_path(tmp_path: Path) -> None:
    original = research_snapshot()
    changed = original.model_copy(deep=True)
    changed.records[0].name.value = "Changed ETF name"
    path = tmp_path / "canonical.json"
    persist_research_snapshot(original, path)

    with pytest.raises(ValueError, match="different content"):
        persist_research_snapshot(changed, path)

    assert load_research_snapshot(path) == original


def test_default_snapshot_path_is_windows_safe_and_version_specific() -> None:
    first = default_snapshot_path("research:2026-08-29T12:00:00Z")
    second = default_snapshot_path("research_2026-08-29T12:00:00Z")

    assert first.parent == Path(".artifacts/research-snapshots")
    assert ":" not in first.name
    assert first != second
