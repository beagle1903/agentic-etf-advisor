"""Durable canonical payloads for retryable research-snapshot publication."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

from etf_advisor.research.models import ETFResearchSnapshot

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def default_snapshot_path(snapshot_version: str) -> Path:
    """Return a deterministic ignored path for one explicit snapshot version."""

    safe_version = _SAFE_FILENAME.sub("_", snapshot_version).strip("._-") or "snapshot"
    version_digest = hashlib.sha256(snapshot_version.encode("utf-8")).hexdigest()[:12]
    return Path(".artifacts") / "research-snapshots" / f"{safe_version}-{version_digest}.json"


def load_research_snapshot(path: Path) -> ETFResearchSnapshot:
    """Load and validate a canonical snapshot payload."""

    return ETFResearchSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def persist_research_snapshot(snapshot: ETFResearchSnapshot, path: Path) -> Path:
    """Atomically persist a snapshot, refusing to replace different content."""

    if path.exists():
        existing = load_research_snapshot(path)
        if existing.content_digest() != snapshot.content_digest():
            raise ValueError(f"Snapshot payload already exists with different content: {path}")
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot.model_dump_json(indent=2)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            existing = load_research_snapshot(path)
            if existing.content_digest() != snapshot.content_digest():
                raise ValueError(
                    f"Snapshot payload already exists with different content: {path}"
                ) from None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return path
