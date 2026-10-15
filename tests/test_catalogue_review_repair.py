"""Independent Issue 103 review scenarios, frozen AC103-2/3/4/5."""

from __future__ import annotations

import copy
import errno
import os
from pathlib import Path
from typing import Any

import pytest
from test_catalogue import T0, FakeProvider, row
from typer.testing import CliRunner

from etf_advisor import catalogue, cli
from etf_advisor.catalogue.service import (
    CatalogueError,
    CatalogueService,
    canonical,
    digest,
    validate_catalogue,
)
from etf_advisor.catalogue.store import CatalogueStore


def _service(tmp_path: Path) -> tuple[CatalogueService, FakeProvider, CatalogueStore]:
    provider = FakeProvider()
    store = CatalogueStore(tmp_path)
    return (
        CatalogueService(store, provider, provider, clock=lambda: T0, monotonic=lambda: 0.0),
        provider,
        store,
    )


def test_rejected_add_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeService:
        def add_direct(self, value: str) -> dict[str, Any]:
            return {
                "verification": {"verification": "rejected", "reason": "non_etf"},
                "publication": "not_attempted",
            }

    monkeypatch.setattr(cli, "_catalogue_service", FakeService)
    result = CliRunner().invoke(cli.app, ["catalogue", "lookup", "AAPL", "--add"])
    assert result.exit_code != 0
    assert "rejected" in result.stdout


def test_discovered_record_must_link_exact_partition_and_page(tmp_path: Path) -> None:
    svc, provider, store = _service(tmp_path)
    provider.rows[("de", "GER")] = [row()]
    assert svc.refresh()["status"] == "published"
    saved = store.read()
    assert saved is not None

    wrong_partition = copy.deepcopy(saved)
    wrong_partition["discovered"][0]["provenance"] = {
        "country": "fr",
        "exchange": "PAR",
        "offset": 0,
    }
    wrong_partition["version"] = digest(
        {k: v for k, v in wrong_partition.items() if k != "version"}
    )
    with pytest.raises(ValueError):
        validate_catalogue(wrong_partition)

    wrong_identity_digest = copy.deepcopy(saved)
    report = next(
        p
        for p in wrong_identity_digest["coverage"]["partitions"]
        if p["country"] == "de" and p["exchange"] == "GER"
    )
    report["pages"][0]["identity_digest"] = "0" * 64
    wrong_identity_digest["version"] = digest(
        {k: v for k, v in wrong_identity_digest.items() if k != "version"}
    )
    with pytest.raises(ValueError):
        validate_catalogue(wrong_identity_digest)


@pytest.mark.parametrize("stage", ["blob", "pointer"])
def test_store_io_failure_keeps_prior_and_returns_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    svc, _, store = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    before = (tmp_path / "active.json").read_bytes()
    actual_replace = os.replace

    def broken_replace(src: str | Path, dst: str | Path) -> None:
        if (stage == "blob" and str(dst).endswith(".json") and Path(dst).name != "active.json") or (
            stage == "pointer" and Path(dst).name == "active.json"
        ):
            raise OSError("fixture_io_failure")
        actual_replace(src, dst)

    monkeypatch.setattr(os, "replace", broken_replace)
    result = svc.refresh(force=True)
    assert result["status"] == "failed"
    assert result["active_version"] == store.read()["version"]
    assert (tmp_path / "active.json").read_bytes() == before


def test_post_pointer_cleanup_error_does_not_claim_prior_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, _, store = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    before = store.read()
    assert before is not None
    real_unlink = Path.unlink

    def broken_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path.name == "publish.lock":
            raise OSError("fixture_cleanup_failure")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", broken_unlink)
    result = svc.refresh(force=True)
    assert result["status"] == "published"
    active = store.read()
    assert active is not None
    assert active["version"] == result["version"]
    assert active["version"] != before["version"]
    assert result["cleanup_error"] == "lock_release_error"


@pytest.mark.parametrize("operation", ["refresh", "direct"])
def test_cas_loser_reports_validated_winner_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    svc, provider, store = _service(tmp_path)
    provider.lookups["VWCE.DE"] = [row()]
    original_publish = store.publish

    def winner_then_conflict(candidate: dict[str, Any], parent: str | None) -> dict[str, Any]:
        original_publish(candidate, parent)
        raise CatalogueError("cas_conflict")

    monkeypatch.setattr(store, "publish", winner_then_conflict)
    result = svc.refresh() if operation == "refresh" else svc.add_direct("VWCE.DE")
    active = store.read()
    assert active is not None
    assert result["active_version"] == active["version"]
    assert result["active_version_state"] == "validated"


def test_failed_attempt_does_not_label_parent_active_when_readback_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, _, store = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    parent = store.read()
    assert parent is not None
    reads = 0
    original_read = store.read

    def unavailable_read() -> dict[str, Any] | None:
        nonlocal reads
        reads += 1
        if reads > 1:
            raise CatalogueError("invalid_pointer")
        return original_read()

    monkeypatch.setattr(store, "read", unavailable_read)

    def fail_publish(candidate: dict[str, Any], captured: str | None) -> dict[str, Any]:
        raise CatalogueError("cas_conflict")

    monkeypatch.setattr(store, "publish", fail_publish)
    result = svc.refresh(force=True)
    assert result["status"] == "failed"
    assert result["attempted_parent_version"] == parent["version"]
    assert result["active_version"] is None
    assert result["active_version_state"] == "unknown"


@pytest.mark.parametrize("stage", ["pointer", "blob"])
def test_catalogue_read_io_failure_is_controlled_at_service_and_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    svc, _, store = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    before = (tmp_path / "active.json").read_bytes()
    active = store.read()
    assert active is not None
    real_read = Path.read_bytes
    denied_name = "active.json" if stage == "pointer" else f"{active['version']}.json"

    def deny_read(path: Path) -> bytes:
        if path.name == denied_name:
            raise PermissionError("fixture_read_denied")
        return real_read(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", deny_read)
        with pytest.raises(CatalogueError, match="store_io_error"):
            store.read()
        with pytest.raises(CatalogueError, match="store_io_error"):
            svc.refresh(force=True)
        with pytest.raises(CatalogueError, match="store_io_error"):
            svc.add_direct("VWCE.DE")
        with pytest.raises(CatalogueError, match="store_io_error"):
            svc.local_search("VWCE")
        patch.setattr(cli, "_catalogue_service", lambda: svc)
        patch.setattr(catalogue, "CatalogueStore", lambda: store)
        for command in (
            ["catalogue", "refresh", "--force"],
            ["catalogue", "lookup", "VWCE.DE", "--add"],
            ["catalogue", "search", "VWCE"],
        ):
            cli_result = CliRunner().invoke(cli.app, command)
            assert cli_result.exit_code == 1
            assert '"reason": "store_io_error"' in cli_result.stdout

    assert (tmp_path / "active.json").read_bytes() == before
    assert store.read() == active


def test_transient_owned_lock_cleanup_allows_next_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, _, store = _service(tmp_path)
    real_unlink = Path.unlink
    failed = False

    def transient_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        nonlocal failed
        if path.name == "publish.lock" and not failed:
            failed = True
            raise OSError("fixture_transient_cleanup_failure")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", transient_unlink)
    assert svc.refresh()["status"] == "published"
    assert failed
    assert not (tmp_path / "publish.lock").exists()
    assert svc.refresh(force=True)["status"] == "published"
    assert store.read() is not None


def test_lock_metadata_failure_releases_fd_and_allows_next_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, _, _ = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    before = (tmp_path / "active.json").read_bytes()
    real_fstat = os.fstat
    acquired_fd: int | None = None
    failed_once = False

    def fail_once(fd: int) -> os.stat_result:
        nonlocal acquired_fd, failed_once
        acquired_fd = fd
        if not failed_once:
            failed_once = True
            raise OSError("fixture_lock_metadata_failure")
        return real_fstat(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fstat", fail_once)
        failed = svc.refresh(force=True)

    assert failed["status"] == "failed"
    assert failed["reason"] == "store_io_error"
    assert failed_once
    assert acquired_fd is not None
    with pytest.raises(OSError) as closed:
        real_fstat(acquired_fd)
    assert closed.value.errno == errno.EBADF
    assert not (tmp_path / "publish.lock").exists()
    assert (tmp_path / "active.json").read_bytes() == before
    assert svc.refresh(force=True)["status"] == "published"


@pytest.mark.parametrize("failure", ["write_error", "short_write", "close_error"])
def test_lock_marker_acquisition_failure_releases_owned_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    svc, _, _ = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    before = (tmp_path / "active.json").read_bytes()
    real_write = os.write
    real_close = os.close
    real_fstat = os.fstat
    acquired_fd: int | None = None
    failed_once = False

    def capture_fstat(fd: int) -> os.stat_result:
        nonlocal acquired_fd
        acquired_fd = fd
        return real_fstat(fd)

    def broken_write(fd: int, data: bytes) -> int:
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            if failure == "write_error":
                raise OSError("fixture_marker_write_failure")
            return real_write(fd, data[:4])
        return real_write(fd, data)

    def broken_close(fd: int) -> None:
        nonlocal failed_once
        if fd == acquired_fd and not failed_once:
            failed_once = True
            raise OSError("fixture_marker_close_failure")
        real_close(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fstat", capture_fstat)
        if failure == "close_error":
            patch.setattr(os, "close", broken_close)
        else:
            patch.setattr(os, "write", broken_write)
        result = svc.refresh(force=True)

    assert failed_once
    assert result["status"] == "failed"
    assert result["reason"] == "store_io_error"
    assert acquired_fd is not None
    with pytest.raises(OSError) as closed:
        real_fstat(acquired_fd)
    assert closed.value.errno == errno.EBADF
    assert not (tmp_path / "publish.lock").exists()
    assert (tmp_path / "active.json").read_bytes() == before
    assert svc.refresh(force=True)["status"] == "published"


def test_persistent_lock_close_failure_is_controlled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, _, _ = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    before = (tmp_path / "active.json").read_bytes()
    real_fstat = os.fstat
    real_close = os.close
    acquired_fd: int | None = None

    def capture_fstat(fd: int) -> os.stat_result:
        nonlocal acquired_fd
        acquired_fd = fd
        return real_fstat(fd)

    def deny_close(fd: int) -> None:
        if fd == acquired_fd:
            raise OSError("fixture_persistent_close_denial")
        real_close(fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fstat", capture_fstat)
        patch.setattr(os, "close", deny_close)
        result = svc.refresh(force=True)

    assert result["status"] == "failed"
    assert result["reason"] == "lock_release_error"
    assert (tmp_path / "active.json").read_bytes() == before
    assert acquired_fd is not None
    real_close(acquired_fd)
    # Permanent close denial may leave an unreleased lock; the failure stays explicit.
    (tmp_path / "publish.lock").unlink(missing_ok=True)


def test_lock_marker_read_failure_warns_after_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, _, store = _service(tmp_path)
    real_open = Path.open

    def deny_marker_read(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.name == "publish.lock" and args and args[0] == "rb":
            raise OSError("fixture_lock_marker_read_failure")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_marker_read)
    result = svc.refresh()
    assert result["status"] == "published"
    assert result["cleanup_error"] == "lock_release_error"
    assert store.read() is not None
    assert (tmp_path / "publish.lock").exists()


def test_replaced_lock_is_not_removed_after_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, _, store = _service(tmp_path)
    real_unlink = Path.unlink
    replaced = False

    def replace_on_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        nonlocal replaced
        if path.name == "publish.lock" and not replaced:
            replaced = True
            real_unlink(path, *args, **kwargs)
            path.write_text("replacement-owner", encoding="ascii")
            raise OSError("fixture_lock_replaced")
        real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", replace_on_unlink)
    result = svc.refresh()
    assert replaced
    assert result["status"] == "published"
    assert result["cleanup_error"] == "lock_release_error"
    assert (tmp_path / "publish.lock").read_text(encoding="ascii") == "replacement-owner"
    assert store.read() is not None


def test_reused_inode_replacement_lock_is_not_removed_after_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, _, store = _service(tmp_path)
    real_unlink = Path.unlink
    real_stat = Path.stat
    replaced = False
    original_identity: os.stat_result | None = None

    def replace_on_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        nonlocal replaced, original_identity
        if path.name == "publish.lock" and not replaced:
            original_identity = real_stat(path)
            replaced = True
            real_unlink(path, *args, **kwargs)
            path.write_text("replacement-owner", encoding="ascii")
            raise OSError("fixture_lock_replaced_with_reused_inode")
        real_unlink(path, *args, **kwargs)

    def reused_inode_stat(path: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        if path.name == "publish.lock" and replaced:
            assert original_identity is not None
            return original_identity
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", replace_on_unlink)
    monkeypatch.setattr(Path, "stat", reused_inode_stat)
    result = svc.refresh()
    assert replaced
    assert result["status"] == "published"
    assert result["cleanup_error"] == "lock_release_error"
    assert (tmp_path / "publish.lock").read_text(encoding="ascii") == "replacement-owner"
    assert store.read() is not None


@pytest.mark.parametrize(
    ("location", "change"),
    [
        ("report", ("source_version", "remove")),
        ("report", ("source_version", None)),
        ("report", ("rejected_count", "remove")),
        ("report", ("rejected_count", True)),
        ("report", ("raw_response", {"private": "value"})),
        ("report", ("query", {"extra": "raw"})),
        (
            "report",
            (
                "errors",
                [
                    {
                        "offset": 0,
                        "attempt": 1,
                        "code": "provider_error",
                        "at": "2026-10-14T08:00:00Z",
                        "raw_payload": "hidden",
                    }
                ],
            ),
        ),
        ("page", ("identity_digest", "remove")),
        ("page", ("raw_payload", [1, 2, 3])),
        ("page", ("requested_at", 123)),
    ],
)
def test_nested_report_page_schema_rejects_correctly_digested_payload(
    tmp_path: Path, location: str, change: tuple[str, Any]
) -> None:
    svc, provider, store = _service(tmp_path)
    provider.rows[("de", "GER")] = [row()]
    assert svc.refresh()["status"] == "published"
    saved = store.read()
    assert saved is not None
    mutated = copy.deepcopy(saved)
    report = mutated["coverage"]["partitions"][0]
    target = report if location == "report" else report["pages"][0]
    key, value = change
    if value == "remove":
        target.pop(key)
    else:
        target[key] = value
    mutated["version"] = digest({k: v for k, v in mutated.items() if k != "version"})
    with pytest.raises(CatalogueError):
        validate_catalogue(mutated)


def test_nested_schema_is_checked_on_store_readback(tmp_path: Path) -> None:
    svc, _, store = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    saved = store.read()
    assert saved is not None
    mutated = copy.deepcopy(saved)
    mutated["coverage"]["partitions"][0]["pages"][0]["raw_payload"] = {"unexpected": True}
    mutated["version"] = digest({k: v for k, v in mutated.items() if k != "version"})
    (tmp_path / f"{mutated['version']}.json").write_bytes(canonical(mutated))
    (tmp_path / "active.json").write_bytes(
        canonical({"schema": "yahoo-catalogue-pointer-v1", "version": mutated["version"]})
    )
    with pytest.raises(CatalogueError, match="invalid_page_report"):
        store.read()


@pytest.mark.parametrize("counter", ["duplicate_count", "rejected_count"])
def test_complete_partition_rejects_forged_counters_on_readback(
    tmp_path: Path, counter: str
) -> None:
    svc, provider, store = _service(tmp_path)
    provider.rows[("de", "GER")] = [row()]
    assert svc.refresh()["status"] == "published"
    saved = store.read()
    assert saved is not None
    forged = copy.deepcopy(saved)
    report = next(
        p
        for p in forged["coverage"]["partitions"]
        if p["country"] == "de" and p["exchange"] == "GER"
    )
    report[counter] = 1
    forged["version"] = digest({k: v for k, v in forged.items() if k != "version"})
    with pytest.raises(CatalogueError, match="invalid_partition_report"):
        validate_catalogue(forged)
    (tmp_path / f"{forged['version']}.json").write_bytes(canonical(forged))
    (tmp_path / "active.json").write_bytes(
        canonical({"schema": "yahoo-catalogue-pointer-v1", "version": forged["version"]})
    )
    with pytest.raises(CatalogueError, match="invalid_partition_report"):
        store.read()


@pytest.mark.parametrize("partitions", [None, 7, "wrong", {"wrong": "container"}])
def test_complete_coverage_rejects_invalid_partition_container_on_readback_and_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, partitions: Any
) -> None:
    svc, _, store = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    saved = store.read()
    assert saved is not None
    forged = copy.deepcopy(saved)
    forged["coverage"]["partitions"] = partitions
    forged["version"] = digest({k: v for k, v in forged.items() if k != "version"})
    with pytest.raises(CatalogueError, match="invalid_coverage"):
        validate_catalogue(forged)

    (tmp_path / f"{forged['version']}.json").write_bytes(canonical(forged))
    pointer = canonical({"schema": "yahoo-catalogue-pointer-v1", "version": forged["version"]})
    (tmp_path / "active.json").write_bytes(pointer)
    with pytest.raises(CatalogueError, match="invalid_coverage"):
        store.read()

    monkeypatch.setattr(cli, "_catalogue_service", lambda: svc)
    monkeypatch.setattr(catalogue, "CatalogueStore", lambda: store)
    for command in (
        ["catalogue", "refresh", "--force"],
        ["catalogue", "lookup", "VWCE.DE", "--add"],
        ["catalogue", "search", "VWCE"],
    ):
        result = CliRunner().invoke(cli.app, command)
        assert result.exit_code == 1
        assert '"reason": "invalid_coverage"' in result.stdout
        assert (tmp_path / "active.json").read_bytes() == pointer


def test_complete_coverage_accepts_empty_provider_partitions(tmp_path: Path) -> None:
    svc, _, store = _service(tmp_path)
    assert svc.refresh()["status"] == "published"
    saved = store.read()
    assert saved is not None
    assert saved["coverage"]["status"] == "provider_partitions_complete"
    assert len(saved["coverage"]["partitions"]) == len(saved["manifest"])
    assert all(report["unique_count"] == 0 for report in saved["coverage"]["partitions"])
    assert validate_catalogue(saved) == saved


@pytest.mark.parametrize("origin", ["direct", "discovered"])
@pytest.mark.parametrize("exchange", [[], {}])
def test_active_observation_exchange_type_is_controlled_at_store_and_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin: str, exchange: Any
) -> None:
    svc, provider, store = _service(tmp_path)
    if origin == "direct":
        provider.lookups["VWCE.DE"] = [row()]
        assert svc.add_direct("VWCE.DE")["publication"] == "published"
    else:
        provider.rows[("de", "GER")] = [row()]
        assert svc.refresh()["status"] == "published"
    saved = store.read()
    assert saved is not None
    assert validate_catalogue(saved) == saved
    forged = copy.deepcopy(saved)
    forged[origin][0]["exchange"] = exchange
    forged["version"] = digest({k: v for k, v in forged.items() if k != "version"})
    with pytest.raises(CatalogueError, match="invalid_observation_identity"):
        validate_catalogue(forged)

    (tmp_path / f"{forged['version']}.json").write_bytes(canonical(forged))
    pointer = canonical({"schema": "yahoo-catalogue-pointer-v1", "version": forged["version"]})
    (tmp_path / "active.json").write_bytes(pointer)
    with pytest.raises(CatalogueError, match="invalid_observation_identity"):
        store.read()

    monkeypatch.setattr(cli, "_catalogue_service", lambda: svc)
    monkeypatch.setattr(catalogue, "CatalogueStore", lambda: store)
    for command in (
        ["catalogue", "refresh", "--force"],
        ["catalogue", "lookup", "VWCE.DE", "--add"],
        ["catalogue", "search", "VWCE"],
    ):
        result = CliRunner().invoke(cli.app, command)
        assert result.exit_code == 1
        assert '"reason": "invalid_observation_identity"' in result.stdout
        assert (tmp_path / "active.json").read_bytes() == pointer


def test_json_type_perturbations_have_controlled_validation_boundary(tmp_path: Path) -> None:
    svc, provider, store = _service(tmp_path)
    provider.lookups["VWCE.DE"] = [row()]
    assert svc.add_direct("VWCE.DE")["publication"] == "published"
    direct = store.read()
    assert direct is not None
    provider.rows[("de", "GER")] = [row()]
    assert svc.refresh(force=True)["status"] == "published"
    discovered = store.read()
    assert discovered is not None

    values: list[Any] = [None, True, 0, "wrong", [], {}]
    probes = 0
    for baseline, origin in ((direct, "direct"), (discovered, "discovered")):
        assert validate_catalogue(baseline) == baseline
        fields: list[tuple[str, ...]] = [
            ("parent",),
            ("operation",),
            ("manifest",),
            ("coverage",),
            ("counts",),
            (origin, "0", "symbol"),
            (origin, "0", "exchange"),
            (origin, "0", "provenance"),
            (origin, "0", "observed_at"),
        ]
        if origin == "discovered":
            fields.extend(
                [
                    ("coverage", "partitions"),
                    ("coverage", "attempts"),
                    ("coverage", "partitions", "0", "pages"),
                    ("coverage", "partitions", "0", "errors"),
                    ("coverage", "partitions", "0", "unique_count"),
                    ("coverage", "partitions", "0", "pages", "0", "count"),
                    ("coverage", "partitions", "0", "pages", "0", "identity_digest"),
                ]
            )
        for path in fields:
            rejected = 0
            for value in values:
                mutated = copy.deepcopy(baseline)
                target: Any = mutated
                for key in path[:-1]:
                    target = target[int(key)] if isinstance(target, list) else target[key]
                target[path[-1]] = value
                mutated["version"] = digest({k: v for k, v in mutated.items() if k != "version"})
                try:
                    validate_catalogue(mutated)
                except CatalogueError:
                    rejected += 1
                probes += 1
            assert rejected > 0, path
    assert probes == (9 + 16) * len(values)


def test_out_of_range_source_time_is_controlled(tmp_path: Path) -> None:
    svc, provider, store = _service(tmp_path)
    huge = 10**100
    provider.rows[("at", "VIE")] = [row("X.VI", "VIE", regularMarketTime=huge)]
    refresh = svc.refresh()
    assert refresh["status"] == "incomplete"
    assert store.read() is None
    provider.lookups["VWCE.DE"] = [row(regularMarketTime=huge)]
    lookup = svc.direct_lookup("VWCE.DE")
    assert lookup["verification"] == "rejected"
