"""Independent Issue 103 review scenarios, frozen AC103-2/3/4/5."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import pytest
from test_catalogue import T0, FakeProvider, row
from typer.testing import CliRunner

from etf_advisor import cli
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
