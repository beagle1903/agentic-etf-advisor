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
from etf_advisor.catalogue.service import CatalogueService, digest, validate_catalogue
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
