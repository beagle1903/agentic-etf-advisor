"""Synthetic source and publication contract fixtures for Issue 103."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from etf_advisor.catalogue.mapping import EXCHANGE_MAP, MANIFEST, UNSUPPORTED_EU
from etf_advisor.catalogue.service import (
    CatalogueError,
    CatalogueService,
    catalogue_projection,
    make_catalogue,
    observation,
    timestamp,
)
from etf_advisor.catalogue.store import CatalogueStore
from etf_advisor.catalogue.yahoo import YahooCatalogueProvider

T0 = datetime(2026, 10, 14, 8, tzinfo=UTC)


def row(sym: str = "VWCE.DE", exchange: str = "GER", **extra: Any) -> dict[str, Any]:
    return {"symbol": sym, "exchange": exchange, "quoteType": "ETF", **extra}


class FakeProvider:
    version = "fixture-v1"

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self.overrides: dict[tuple[str, str, int], Any] = {}
        self.lookups: dict[str, list[dict[str, Any]]] = {}
        self.calls = 0

    def page(
        self, country: str, exchange: str, offset: int, size: int, deadline: float
    ) -> dict[str, Any]:
        self.calls += 1
        override = self.overrides.get((country, exchange, offset))
        if isinstance(override, Exception):
            raise override
        if override is not None:
            return override
        all_rows = self.rows.get((country, exchange), [])
        rows = all_rows[offset : offset + size]
        return {"start": offset, "count": len(rows), "total": len(all_rows), "quotes": rows}

    def search(self, query: str, limit: int, deadline: float) -> list[dict[str, Any]]:
        self.calls += 1
        return self.lookups.get(query, [])[:limit]


def service(
    tmp_path: Path, provider: FakeProvider | None = None
) -> tuple[CatalogueService, FakeProvider, CatalogueStore]:
    provider = provider or FakeProvider()
    store = CatalogueStore(tmp_path)
    return (
        CatalogueService(store, provider, provider, clock=lambda: T0, monotonic=lambda: 0.0),
        provider,
        store,
    )


def test_mapping_and_identity_scope() -> None:
    assert len(MANIFEST) == 42
    assert len(UNSUPPORTED_EU) == 7
    for code, (country, region) in EXCHANGE_MAP.items():
        value = observation(
            row("ABC.X", code),
            origin="direct",
            observed_at=timestamp(T0),
            provenance={"lookup": "ABC.X"},
        )
        assert (value["country"], value["region"]) == (country, region)
    for code in ("LSE", "EBS", "PNK", "YHD", "UNKNOWN"):
        with pytest.raises(CatalogueError, match="disallowed_exchange"):
            observation(
                row(exchange=code),
                origin="direct",
                observed_at=timestamp(T0),
                provenance={"lookup": "VWCE.DE"},
            )
    a = observation(
        row("X.DE"), origin="direct", observed_at=timestamp(T0), provenance={"lookup": "X.DE"}
    )
    b = observation(
        row("X.AS", "AMS"),
        origin="direct",
        observed_at=timestamp(T0),
        provenance={"lookup": "X.AS"},
    )
    assert a["listing_id"] != b["listing_id"]


def test_direct_exact_and_non_etf(tmp_path: Path) -> None:
    svc, provider, store = service(tmp_path)
    provider.lookups["VWCE.DE"] = [row("VWCE.DE", "GER")]
    provider.lookups["AAPL"] = [row("AAPL", "NMS", quoteType="EQUITY"), row("AAPLX", "PCX")]
    provider.lookups["SWDA.SW"] = [row("SWDA.SW", "EBS")]
    assert svc.direct_lookup(" vwce.de ")["verification"] == "verified"
    assert svc.direct_lookup("AAPL")["verification"] == "rejected"
    assert svc.direct_lookup("SWDA.SW")["verification"] == "rejected"
    assert svc.direct_lookup("UNKNOWN")["verification"] == "rejected"
    assert svc.add_direct("VWCE.DE")["publication"] == "published"
    cat = store.read()
    assert cat is not None
    assert cat["coverage"]["status"] == "not_run"
    assert cat["counts"]["combined"] == 1
    assert cat["direct"][0]["source_quote_at"] is None
    assert svc.local_search("VWCE")["status"] == "direct_only"
    assert svc.local_search("VWCE")["matched_count"] == 1


def test_full_refresh_overlap_precedence_and_retention(tmp_path: Path) -> None:
    svc, provider, store = service(tmp_path)
    provider.lookups["VWCE.DE"] = [row(shortName="Old name")]
    assert svc.add_direct("VWCE.DE")["publication"] == "published"
    original = store.read()
    assert original is not None
    direct = original["direct"][0]
    provider.rows[("de", "GER")] = [row(shortName="New name", currency="EUR")]
    assert svc.refresh(force=True)["status"] == "published"
    first = store.read()
    assert first is not None
    assert first["counts"] == {
        "discovered": 1,
        "direct": 1,
        "combined": 1,
        "overlap": 1,
        "direct_only": 0,
    }
    assert first["direct"][0] == direct
    selected = catalogue_projection(first)[0]
    assert selected["selected_origin"] == "discovered"
    assert selected["observation"]["display_name"] == "New name"
    assert svc.local_search("Old name")["matched_count"] == 0
    provider.rows[("de", "GER")] = [row()]
    assert svc.refresh(force=True)["status"] == "published"
    second = store.read()
    assert second is not None
    assert catalogue_projection(second)[0]["observation"]["currency"] is None
    assert second["direct"][0] == direct
    provider.rows.clear()
    assert svc.refresh(force=True)["status"] == "published"
    third = store.read()
    assert third is not None
    assert third["counts"]["discovered"] == 0
    assert catalogue_projection(third)[0]["observation"] == direct
    provider.rows[("de", "FRA")] = [row(exchange="FRA")]
    prior = (tmp_path / "active.json").read_bytes()
    result = svc.refresh(force=True)
    assert result["status"] == "failed"
    assert result["reason"] == "symbol_exchange_conflict"
    assert (tmp_path / "active.json").read_bytes() == prior


def test_pagination_bounds_and_preserve_previous(tmp_path: Path) -> None:
    svc, provider, store = service(tmp_path)
    provider.rows[("pl", "WSE")] = [row(f"P{i}.WA", "WSE") for i in range(500)]
    assert svc.refresh()["status"] == "published"
    first = store.read()
    assert first is not None
    assert first["counts"]["discovered"] == 500
    calls = provider.calls
    assert svc.refresh()["status"] == "reused"
    assert provider.calls == calls
    provider.overrides[("pl", "WSE", 250)] = {"start": 250, "count": 0, "total": 500, "quotes": []}
    before = (tmp_path / "active.json").read_bytes()
    result = svc.refresh(force=True)
    assert result["status"] == "incomplete"
    assert result["coverage"]["partitions"][-1]["status"] == "unattempted"
    assert (tmp_path / "active.json").read_bytes() == before


@pytest.mark.parametrize(
    "bad",
    [
        {"start": True, "count": 0, "total": 0, "quotes": []},
        {"start": 1, "count": 0, "total": 0, "quotes": []},
        {"start": 0, "count": False, "total": 0, "quotes": []},
        {"start": 0, "count": 1, "total": 0, "quotes": []},
        {"start": 0, "count": 1, "total": 2, "quotes": [row()]},
        {"start": 0, "count": 1, "total": 1, "quotes": [row(quoteType="EQUITY")]},
        {"start": 0, "count": 1, "total": 1, "quotes": [row(exchange="LSE")]},
    ],
)
def test_invalid_page_is_incomplete(tmp_path: Path, bad: dict[str, Any]) -> None:
    svc, provider, store = service(tmp_path)
    provider.overrides[("at", "VIE", 0)] = bad
    assert svc.refresh()["status"] == "incomplete"
    assert store.read() is None


def test_provider_failure_retries_and_unattempted(tmp_path: Path) -> None:
    svc, provider, _ = service(tmp_path)
    provider.overrides[("at", "VIE", 0)] = TimeoutError()
    result = svc.refresh()
    assert result["status"] == "incomplete"
    assert result["coverage"]["attempts"] == 2
    assert result["coverage"]["partitions"][0]["truncation_reason"] == "provider_error"
    assert result["coverage"]["partitions"][1]["status"] == "unattempted"


def test_duplicate_and_changed_total_fail_closed(tmp_path: Path) -> None:
    svc, provider, store = service(tmp_path)
    provider.rows[("at", "VIE")] = [row("X.VI", "VIE")] * 250 + [row("X.VI", "VIE")]
    result = svc.refresh()
    assert result["status"] == "incomplete"
    assert result["coverage"]["partitions"][0]["duplicate_count"] > 0
    assert store.read() is None
    provider.rows[("at", "VIE")] = [row(f"X{i}.VI", "VIE") for i in range(251)]
    provider.overrides[("at", "VIE", 250)] = {
        "start": 250,
        "count": 1,
        "total": 252,
        "quotes": [row("X250.VI", "VIE")],
    }
    result = svc.refresh()
    assert result["status"] == "incomplete"
    assert store.read() is None


def test_expired_cache_and_direct_add_do_not_refresh_discovery(tmp_path: Path) -> None:
    svc, provider, store = service(tmp_path)
    assert svc.refresh()["status"] == "published"
    first = store.read()
    assert first is not None
    provider.lookups["VWCE.DE"] = [row()]
    svc.clock = lambda: T0 + timedelta(hours=23)
    assert svc.add_direct("VWCE.DE")["publication"] == "published"
    second = store.read()
    assert second is not None
    assert second["full_refresh_at"] == first["full_refresh_at"]
    calls = provider.calls
    assert svc.refresh()["status"] == "reused"
    assert calls == provider.calls
    svc.clock = lambda: T0 + timedelta(hours=25)
    assert svc.local_search("VWCE")["status"] == "stale"
    assert svc.refresh()["status"] == "published"
    third = store.read()
    assert third is not None
    assert third["direct"][0] == second["direct"][0]


def test_deadline_after_slow_provider_response(tmp_path: Path) -> None:
    svc, _, store = service(tmp_path)
    ticks = iter([0.0, 0.0, 301.0])
    svc.monotonic = lambda: next(ticks, 301.0)
    result = svc.refresh()
    assert result["status"] == "incomplete"
    assert result["coverage"]["partitions"][0]["status"] == "incomplete"
    assert store.read() is None


def test_store_corruption_and_cas(tmp_path: Path) -> None:
    svc, provider, store = service(tmp_path)
    provider.lookups["VWCE.DE"] = [row()]
    assert svc.add_direct("VWCE.DE")["publication"] == "published"
    parent = store.read()
    assert parent is not None
    candidate = make_catalogue(
        parent=parent,
        operation="direct_add",
        discovered=[],
        direct=parent["direct"],
        coverage=parent["coverage"],
        full_refresh_at=None,
        created_at=timestamp(T0 + timedelta(seconds=1)),
    )
    store.publish(candidate, parent["version"])
    with pytest.raises(CatalogueError, match="cas_conflict"):
        store.publish(candidate, parent["version"])
    pointer = tmp_path / "active.json"
    pointer.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
    with pytest.raises(CatalogueError, match="duplicate_json_key"):
        store.read()
    pointer.write_text(
        json.dumps({"schema": "yahoo-catalogue-pointer-v1", "version": "../" + "a" * 61}),
        encoding="utf-8",
    )
    with pytest.raises(CatalogueError, match="invalid_pointer"):
        store.read()
    pointer.write_text(
        json.dumps({"schema": "yahoo-catalogue-pointer-v1", "version": candidate["version"]}),
        encoding="utf-8",
    )
    (tmp_path / f"{candidate['version']}.json").write_text('{"x":NaN}', encoding="utf-8")
    with pytest.raises(CatalogueError, match="nonfinite_json"):
        store.read()


def test_yahoo_transport_caps_auth_and_page_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = pytest.importorskip("curl_cffi.requests")

    seen: list[float] = []

    def fake_request(self: Any, method: str, url: str, **kwargs: Any) -> object:
        seen.append(kwargs["timeout"])
        return object()

    monkeypatch.setattr(requests.Session, "request", fake_request)
    provider = YahooCatalogueProvider()
    provider._session.deadline = time.monotonic() + 2
    provider._session.request("GET", "https://example.test/cookie", timeout=30)
    provider._session.request("POST", "https://example.test/screen", timeout=30)
    assert len(seen) == 2
    assert all(0 < value <= 2 for value in seen)
    provider._session.deadline = time.monotonic() - 1
    with pytest.raises(TimeoutError):
        provider._session.request("GET", "https://example.test/cookie")
