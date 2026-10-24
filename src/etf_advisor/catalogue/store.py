"""Immutable JSON catalogue blobs with bounded cross-process CAS publication."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from .service import CatalogueError, CommittedCleanupError, canonical, validate_catalogue


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CatalogueError("duplicate_json_key")
        result[key] = value
    return result


def _strict_json(data: bytes) -> Any:
    try:
        return json.loads(
            data,
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(CatalogueError("nonfinite_json")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogueError("invalid_json") from exc


class CatalogueStore:
    def __init__(
        self, root: Path = Path(".artifacts/catalogue"), lock_timeout: float = 5.0
    ) -> None:
        self.root = root
        self.lock_timeout = lock_timeout

    def read(self) -> dict[str, Any] | None:
        try:
            pointer = self.root / "active.json"
            if not pointer.exists():
                return None
            raw = _strict_json(pointer.read_bytes())
            if (
                not isinstance(raw, dict)
                or set(raw) != {"schema", "version"}
                or raw["schema"] != "yahoo-catalogue-pointer-v1"
                or not isinstance(raw["version"], str)
                or re.fullmatch(r"[0-9a-f]{64}", raw["version"]) is None
            ):
                raise CatalogueError("invalid_pointer")
            path = self.root / f"{raw['version']}.json"
            if not path.is_file():
                raise CatalogueError("missing_blob")
            candidate = _strict_json(path.read_bytes())
            if not isinstance(candidate, dict) or candidate.get("version") != raw["version"]:
                raise CatalogueError("pointer_blob_mismatch")
            return validate_catalogue(candidate)
        except OSError as exc:
            raise CatalogueError("store_io_error") from exc

    def read_version(self, version: str, *, max_bytes: int = 32 * 1024 * 1024) -> dict[str, Any]:
        """Read one immutable pinned blob without substituting the active pointer."""
        if re.fullmatch(r"[0-9a-f]{64}", version) is None or not 1 <= max_bytes <= 32 * 1024 * 1024:
            raise CatalogueError("invalid_version_or_bound")
        try:
            with (self.root / f"{version}.json").open("rb") as source:
                payload = source.read(max_bytes + 1)
        except OSError as exc:
            raise CatalogueError("version_unavailable") from exc
        if len(payload) > max_bytes:
            raise CatalogueError("catalogue_input_limit_exceeded")
        value = validate_catalogue(_strict_json(payload))
        if value["version"] != version:
            raise CatalogueError("version_identity_mismatch")
        return value

    def publish(self, candidate: dict[str, Any], parent: str | None) -> dict[str, Any]:
        validate_catalogue(candidate)
        if candidate["parent"] != parent:
            raise CatalogueError("invalid_parent")
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CatalogueError("store_io_error") from exc
        lock = self.root / "publish.lock"
        deadline = time.monotonic() + self.lock_timeout
        while True:
            owned_marker = uuid4().hex.encode("ascii")
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as exc:
                if time.monotonic() >= deadline:
                    raise CatalogueError("lock_timeout") from exc
                time.sleep(0.05)
            except OSError as exc:
                raise CatalogueError("store_io_error") from exc
            else:
                owned_stat: os.stat_result | None = None
                written_marker = b""
                try:
                    try:
                        try:
                            owned_stat = os.fstat(fd)
                        except OSError as exc:
                            # Recover identity while our exclusive descriptor remains open.
                            for _ in range(2):
                                try:
                                    owned_stat = os.fstat(fd)
                                    break
                                except OSError:
                                    continue
                            if owned_stat is None:
                                raise CatalogueError("lock_release_error") from exc
                            raise CatalogueError("store_io_error") from exc
                        written = os.write(fd, owned_marker)
                        written_marker = owned_marker[:written]
                        if written != len(owned_marker):
                            raise OSError("short_lock_marker_write")
                    finally:
                        close_error: OSError | None = None
                        for attempt in range(3):
                            try:
                                os.close(fd)
                                break
                            except OSError as exc:
                                close_error = exc
                                if attempt == 2:
                                    raise CatalogueError("lock_release_error") from exc
                        if close_error is not None:
                            raise CatalogueError("store_io_error") from close_error
                except (OSError, CatalogueError) as exc:
                    if owned_stat is not None:
                        try:
                            self._release_owned_lock(
                                lock, owned_stat.st_dev, owned_stat.st_ino, written_marker
                            )
                        except OSError as cleanup_exc:
                            raise CatalogueError("lock_release_error") from cleanup_exc
                    if isinstance(exc, CatalogueError):
                        raise
                    raise CatalogueError("store_io_error") from exc
                break
        pointer_committed = False
        try:
            current = self.read()
            if (current["version"] if current else None) != parent:
                raise CatalogueError("cas_conflict")
            blob = self.root / f"{candidate['version']}.json"
            if blob.exists():
                existing = _strict_json(blob.read_bytes())
                if existing != candidate:
                    raise CatalogueError("immutable_blob_conflict")
            else:
                temp = self.root / f".{uuid4().hex}.tmp"
                try:
                    with temp.open("xb") as handle:
                        handle.write(canonical(candidate))
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp, blob)
                finally:
                    temp.unlink(missing_ok=True)
            validate_catalogue(_strict_json(blob.read_bytes()))
            pointer_temp = self.root / f".{uuid4().hex}.tmp"
            try:
                with pointer_temp.open("xb") as handle:
                    handle.write(
                        canonical(
                            {
                                "schema": "yahoo-catalogue-pointer-v1",
                                "version": candidate["version"],
                            }
                        )
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(pointer_temp, self.root / "active.json")
                pointer_committed = True
            finally:
                try:
                    pointer_temp.unlink(missing_ok=True)
                except OSError:
                    if not pointer_committed:
                        raise
            return candidate
        except OSError as exc:
            raise CatalogueError("store_io_error") from exc
        finally:
            try:
                self._release_owned_lock(lock, owned_stat.st_dev, owned_stat.st_ino, owned_marker)
            except OSError as exc:
                if pointer_committed:
                    raise CommittedCleanupError(candidate) from exc
                raise CatalogueError("lock_release_error") from exc

    @staticmethod
    def _release_owned_lock(lock: Path, device: int, inode: int, marker: bytes) -> None:
        """Retry a transient unlink error only while the original lock is still ours."""
        for attempt in range(3):
            current = lock.stat()
            if (current.st_dev, current.st_ino) != (device, inode):
                raise OSError("owned_lock_changed")
            with lock.open("rb") as handle:
                current_marker = handle.read(len(marker) + 1)
            if current_marker != marker:
                raise OSError("owned_lock_marker_changed")
            try:
                lock.unlink()
                return
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(0.05)
