"""Replaceable, local CAS publication for audited Fund registry generations."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

from etf_advisor.domain.fund_identity import (
    SHA,
    RegistryEnvelope,
    canonical_bytes,
    validate_publication,
)
from etf_advisor.encoding import strict_json


class RegistryPublicationError(ValueError):
    """Confirmed precommit failure or invalid candidate."""


class RegistryCommittedCleanupError(RegistryPublicationError):
    """The active pointer committed, but cleanup or acknowledgement failed."""

    def __init__(self, envelope: RegistryEnvelope) -> None:
        super().__init__("registry_pointer_committed_cleanup_uncertain")
        self.envelope = envelope


class _UnixLockModule(Protocol):
    LOCK_EX: int
    LOCK_NB: int
    LOCK_UN: int

    def flock(self, fd: int, operation: int) -> None: ...


class LocalFundIdentityRegistry:
    def __init__(
        self,
        root: Path = Path(".artifacts/curator-fund-registry"),
        *,
        lock_timeout_seconds: float = 5.0,
    ) -> None:
        self.root = root
        self.lock_timeout_seconds = lock_timeout_seconds

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / ".publish.lock"
        with path.open("a+b") as handle:
            handle.seek(0)
            if not handle.read(1):
                handle.seek(0)
                handle.write(b"0")
                handle.flush()
            deadline = time.monotonic() + self.lock_timeout_seconds
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt

                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        unix_lock = cast(_UnixLockModule, fcntl)
                        unix_lock.flock(handle.fileno(), unix_lock.LOCK_EX | unix_lock.LOCK_NB)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise RegistryPublicationError("registry_lock_timeout") from exc
                    time.sleep(0.05)
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    unix_lock.flock(handle.fileno(), unix_lock.LOCK_UN)

    def _blob(self, digest: str) -> Path:
        return self.root / "generations" / f"{digest}.json"

    def active(self) -> RegistryEnvelope | None:
        pointer = self.root / "active.json"
        if not pointer.exists():
            return None
        raw = pointer.read_bytes()
        if len(raw) > 1024:
            raise RegistryPublicationError("registry_pointer_invalid")
        try:
            data = strict_json(raw.decode("utf-8"))
            if (
                not isinstance(data, dict)
                or set(data) != {"digest"}
                or not isinstance(data["digest"], str)
                or SHA.fullmatch(data["digest"]) is None
            ):
                raise ValueError("invalid active pointer")
            blob = self._blob(data["digest"]).read_bytes()
            if len(blob) > 140 * 1024:
                raise ValueError("registry blob exceeds bound")
            envelope = RegistryEnvelope.from_json(blob.decode("utf-8"))
            if envelope.digest != data["digest"]:
                raise ValueError("pointer digest mismatch")
            return envelope
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            raise RegistryPublicationError("registry_active_invalid") from exc

    def publish(
        self,
        envelope: RegistryEnvelope,
        *,
        expected_parent_digest: str | None,
        checked_at: datetime,
    ) -> RegistryEnvelope:
        envelope = RegistryEnvelope.model_validate(envelope.model_dump(mode="json"))
        committed = False
        try:
            with self._lock():
                parent = self.active()
                validate_publication(
                    envelope,
                    parent,
                    expected_parent_digest=expected_parent_digest,
                    checked_at=checked_at,
                )
                blob_path = self._blob(envelope.digest)
                blob_path.parent.mkdir(parents=True, exist_ok=True)
                blob = canonical_bytes(envelope.model_dump(mode="json"))
                pointer_path = self.root / "active.json"
                pointer_tmp = self.root / f".{uuid4().hex}.pointer.tmp"
                committed = False
                try:
                    if blob_path.exists():
                        if blob_path.read_bytes() != blob:
                            raise RegistryPublicationError("registry_immutable_blob_conflict")
                    else:
                        blob_tmp = self.root / f".{uuid4().hex}.blob.tmp"
                        try:
                            with blob_tmp.open("xb") as handle:
                                handle.write(blob)
                                handle.flush()
                                os.fsync(handle.fileno())
                            os.replace(blob_tmp, blob_path)
                        finally:
                            blob_tmp.unlink(missing_ok=True)
                    if blob_path.read_bytes() != blob:
                        raise RegistryPublicationError("registry_blob_readback_mismatch")
                    with pointer_tmp.open("xb") as handle:
                        handle.write(canonical_bytes({"digest": envelope.digest}))
                        handle.flush()
                        os.fsync(handle.fileno())
                    # Cross-process exclusion still owns the parent observed above.
                    os.replace(pointer_tmp, pointer_path)
                    committed = True
                    if self.active() != envelope:
                        raise RegistryCommittedCleanupError(envelope)
                    return envelope
                except OSError as exc:
                    if committed:
                        raise RegistryCommittedCleanupError(envelope) from exc
                    raise RegistryPublicationError("registry_store_io_error") from exc
                finally:
                    try:
                        pointer_tmp.unlink(missing_ok=True)
                    except OSError as exc:
                        if committed:
                            raise RegistryCommittedCleanupError(envelope) from exc
                        raise RegistryPublicationError(
                            "registry_pointer_temp_cleanup_failed"
                        ) from exc
        except Exception as exc:
            if committed and not isinstance(exc, RegistryCommittedCleanupError):
                raise RegistryCommittedCleanupError(envelope) from exc
            raise
