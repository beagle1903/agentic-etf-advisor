"""Pure listing validation, bounded discovery, and catalogue operations."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .mapping import EXCHANGE_MAP, MANIFEST, MAP_VERSION, UNSUPPORTED_EU

SCHEMA = "yahoo-catalogue-v1"
PAGE_SIZE = 250
MAX_PAGES = 40
MAX_ROWS = 10_000
MAX_ATTEMPTS = 256
REFRESH_SECONDS = 300
MAX_SEARCH = 25
MAX_SYMBOL = 40
SYMBOL = re.compile(r"^[A-Z0-9^][A-Z0-9.\-^=]*$")


class CatalogueError(ValueError):
    """A controlled source, validation, or publication failure."""


class CommittedCleanupError(CatalogueError):
    """The pointer moved, but releasing this writer's lock failed."""

    def __init__(self, candidate: dict[str, Any]) -> None:
        super().__init__("lock_release_error")
        self.candidate = candidate


class PageProvider(Protocol):
    version: str

    def page(
        self, country: str, exchange: str, offset: int, size: int, deadline: float
    ) -> Mapping[str, Any]: ...


class SearchProvider(Protocol):
    version: str

    def search(self, query: str, limit: int, deadline: float) -> Sequence[Mapping[str, Any]]: ...


class Store(Protocol):
    def read(self) -> dict[str, Any] | None: ...

    def publish(self, candidate: dict[str, Any], parent: str | None) -> dict[str, Any]: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


def timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise CatalogueError("naive_time")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CatalogueError("invalid_time")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CatalogueError("invalid_time") from exc
    return timestamp(dt)


def symbol(value: Any) -> str:
    if not isinstance(value, str):
        raise CatalogueError("invalid_symbol")
    clean = value.strip().upper()
    if len(clean) > MAX_SYMBOL or not SYMBOL.fullmatch(clean):
        raise CatalogueError("invalid_symbol")
    return clean


def query(country: str, exchange: str) -> dict[str, Any]:
    return {
        "operator": "AND",
        "operands": [
            {"operator": "EQ", "operands": ["region", country]},
            {"operator": "EQ", "operands": ["exchange", exchange]},
        ],
    }


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _nullable(value: Any, field: str) -> tuple[str | None, str | None]:
    if value is None:
        return None, "not_reported"
    if not isinstance(value, str) or not value.strip() or len(value) > 300:
        raise CatalogueError(f"invalid_{field}")
    return value.strip(), None


def observation(
    raw: Mapping[str, Any], *, origin: str, observed_at: str, provenance: dict[str, Any]
) -> dict[str, Any]:
    """Allowlist a source quote; never persist provider response bodies."""
    sym = symbol(raw.get("symbol"))
    exchange = raw.get("exchange")
    if not isinstance(exchange, str) or exchange not in EXCHANGE_MAP:
        raise CatalogueError("disallowed_exchange")
    if raw.get("quoteType") != "ETF":
        raise CatalogueError("non_etf")
    country, region = EXCHANGE_MAP[exchange]
    name, name_missing = _nullable(
        raw.get("shortName") or raw.get("longName") or raw.get("shortname") or raw.get("longname"),
        "name",
    )
    currency, currency_missing = _nullable(raw.get("currency"), "currency")
    underlying = None
    underlying_missing = "not_reported"
    quote_time = raw.get("regularMarketTime")
    if quote_time is not None:
        if type(quote_time) is not int or quote_time < 0:
            raise CatalogueError("invalid_quote_time")
        try:
            quote_time = timestamp(datetime.fromtimestamp(quote_time, UTC))
        except (OverflowError, OSError, ValueError) as exc:
            raise CatalogueError("invalid_quote_time") from exc
    obs = {
        "listing_id": digest(["yahoo_finance", sym, exchange]),
        "symbol": sym,
        "quote_type": "ETF",
        "exchange": exchange,
        "country": country,
        "region": region,
        "mapping_version": MAP_VERSION,
        "display_name": name,
        "display_name_missing": name_missing,
        "currency": currency,
        "currency_missing": currency_missing,
        "underlying_id": underlying,
        "underlying_id_missing": underlying_missing,
        "provider": "yahoo_finance",
        "source_url": f"https://finance.yahoo.com/quote/{sym}",
        "endpoint": "screen" if origin == "discovered" else "search",
        "endpoint_url": (
            "https://query1.finance.yahoo.com/v1/finance/screener"
            if origin == "discovered"
            else "https://query1.finance.yahoo.com/v1/finance/search"
        ),
        "observed_at": parse_time(observed_at),
        "source_quote_at": quote_time,
        "provenance": provenance,
        "origin": origin,
    }
    return obs


OBS_KEYS = frozenset(
    observation(
        {"symbol": "TEST", "exchange": "PCX", "quoteType": "ETF"},
        origin="direct",
        observed_at="2026-01-01T00:00:00Z",
        provenance={"lookup": "TEST"},
    )
)


def validate_observation(obs: Any, origin: str) -> None:
    if not isinstance(obs, dict) or set(obs) != OBS_KEYS or obs["origin"] != origin:
        raise CatalogueError("invalid_observation_schema")
    if obs["provider"] != "yahoo_finance" or obs["mapping_version"] != MAP_VERSION:
        raise CatalogueError("invalid_observation_provider")
    if obs["quote_type"] != "ETF" or obs["exchange"] not in EXCHANGE_MAP:
        raise CatalogueError("invalid_observation_identity")
    sym = symbol(obs["symbol"])
    if sym != obs["symbol"] or obs["listing_id"] != digest(["yahoo_finance", sym, obs["exchange"]]):
        raise CatalogueError("invalid_observation_id")
    country, region = EXCHANGE_MAP[obs["exchange"]]
    if (obs["country"], obs["region"]) != (country, region):
        raise CatalogueError("invalid_observation_mapping")
    for field in ("display_name", "currency", "underlying_id"):
        value = obs[field]
        reason = obs[field + "_missing"]
        if (value is None and reason != "not_reported") or (
            value is not None
            and (not isinstance(value, str) or not value.strip() or reason is not None)
        ):
            raise CatalogueError("invalid_optional_field")
    parse_time(obs["observed_at"])
    if obs["source_quote_at"] is not None:
        parse_time(obs["source_quote_at"])
    if obs["source_url"] != f"https://finance.yahoo.com/quote/{sym}":
        raise CatalogueError("invalid_source_url")
    if obs["endpoint"] != ("screen" if origin == "discovered" else "search"):
        raise CatalogueError("invalid_endpoint")
    if obs["endpoint_url"] != (
        "https://query1.finance.yahoo.com/v1/finance/screener"
        if origin == "discovered"
        else "https://query1.finance.yahoo.com/v1/finance/search"
    ):
        raise CatalogueError("invalid_endpoint")
    prov = obs["provenance"]
    if not isinstance(prov, dict):
        raise CatalogueError("invalid_provenance")
    if origin == "discovered":
        if (
            set(prov) != {"country", "exchange", "offset"}
            or (prov["country"], prov["exchange"]) not in MANIFEST
            or (prov["country"], prov["exchange"]) != (obs["country"], obs["exchange"])
            or type(prov["offset"]) is not int
            or not 0 <= prov["offset"] < MAX_ROWS
            or prov["offset"] % PAGE_SIZE != 0
        ):
            raise CatalogueError("invalid_provenance")
    elif set(prov) != {"lookup"} or prov["lookup"] != sym:
        raise CatalogueError("invalid_provenance")


def _component(items: Any, origin: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        raise CatalogueError("invalid_component")
    result = {}
    for obs in items:
        validate_observation(obs, origin)
        key = obs["listing_id"]
        if key in result:
            raise CatalogueError("duplicate_identity")
        result[key] = obs
    return result


def catalogue_projection(cat: dict[str, Any]) -> list[dict[str, Any]]:
    discovered = _component(cat["discovered"], "discovered")
    direct = _component(cat["direct"], "direct")
    by_symbol: dict[str, str] = {}
    for obs in [*discovered.values(), *direct.values()]:
        old = by_symbol.setdefault(obs["symbol"], obs["exchange"])
        if old != obs["exchange"]:
            raise CatalogueError("symbol_exchange_conflict")
    result = []
    for key in sorted(discovered.keys() | direct.keys()):
        selected = discovered.get(key) or direct[key]
        result.append(
            {
                "listing_id": key,
                "catalogue_version": cat["version"],
                "origins": [
                    o
                    for o in ("discovered", "direct")
                    if key in (discovered if o == "discovered" else direct)
                ],
                "selected_origin": selected["origin"],
                "observation": selected,
            }
        )
    return result


def validate_catalogue(cat: Any) -> dict[str, Any]:
    if not isinstance(cat, dict) or set(cat) != {
        "schema",
        "version",
        "parent",
        "operation",
        "mapping_version",
        "manifest",
        "discovered",
        "direct",
        "coverage",
        "full_refresh_at",
        "created_at",
        "counts",
    }:
        raise CatalogueError("invalid_catalogue_schema")
    if (
        cat["schema"] != SCHEMA
        or cat["mapping_version"] != MAP_VERSION
        or cat["manifest"] != [list(p) for p in MANIFEST]
    ):
        raise CatalogueError("invalid_catalogue_contract")
    if cat["parent"] is not None and (
        not isinstance(cat["parent"], str) or re.fullmatch(r"[0-9a-f]{64}", cat["parent"]) is None
    ):
        raise CatalogueError("invalid_parent")
    if cat["operation"] not in ("direct_add", "full_refresh"):
        raise CatalogueError("invalid_operation")
    parse_time(cat["created_at"])
    if cat["full_refresh_at"] is not None:
        parse_time(cat["full_refresh_at"])
    coverage = cat["coverage"]
    if not isinstance(coverage, dict) or coverage.get("status") not in (
        "not_run",
        "provider_partitions_complete",
    ):
        raise CatalogueError("invalid_coverage")
    if coverage["status"] == "provider_partitions_complete":
        discovered = _component(cat["discovered"], "discovered")
        records_by_page: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
        for record in discovered.values():
            prov = record["provenance"]
            records_by_page.setdefault(
                (prov["country"], prov["exchange"], prov["offset"]), []
            ).append(record)
        if (
            cat["full_refresh_at"] is None
            or set(coverage)
            != {
                "status",
                "partitions",
                "unsupported_eu_countries",
                "unsupported_reason",
                "excluded_venues",
                "excluded_venue_reasons",
                "attempts",
                "completed_at",
            }
            or coverage["unsupported_eu_countries"] != list(UNSUPPORTED_EU)
            or coverage["unsupported_reason"] != "no_mapped_yahoo_exchange"
            or coverage["excluded_venues"]
            != ["OEM", "OQB", "OQX", "PNK", "YHD", "AQS", "CXE", "IOB", "LSE", "EBS"]
            or coverage["excluded_venue_reasons"]
            != {
                code: (
                    "otc_or_deleted"
                    if code in {"OEM", "OQB", "OQX", "PNK", "YHD"}
                    else "outside_us_eu_scope"
                )
                for code in ["OEM", "OQB", "OQX", "PNK", "YHD", "AQS", "CXE", "IOB", "LSE", "EBS"]
            }
            or len(coverage["partitions"]) != len(MANIFEST)
            or type(coverage["attempts"]) is not int
            or not len(MANIFEST) <= coverage["attempts"] <= MAX_ATTEMPTS
            or cat["full_refresh_at"] != parse_time(coverage["completed_at"])
        ):
            raise CatalogueError("invalid_coverage")
        reported_count = 0
        for report, (country, exchange) in zip(coverage["partitions"], MANIFEST, strict=True):
            if (
                not isinstance(report, dict)
                or set(report)
                != {
                    "country",
                    "exchange",
                    "query",
                    "page_size",
                    "sort_field",
                    "sort_asc",
                    "source_version",
                    "mapping_version",
                    "status",
                    "pages",
                    "unique_count",
                    "duplicate_count",
                    "rejected_count",
                    "errors",
                    "truncation_reason",
                }
                or report.get("country") != country
                or report.get("exchange") != exchange
                or report.get("query") != query(country, exchange)
                or report.get("page_size") != PAGE_SIZE
                or report.get("sort_field") != "ticker"
                or report.get("sort_asc") is not True
                or report.get("mapping_version") != MAP_VERSION
                or report.get("status") != "complete"
                or not isinstance(report.get("source_version"), str)
                or not report["source_version"].strip()
                or not isinstance(report.get("errors"), list)
                or type(report.get("rejected_count")) is not int
                or report["rejected_count"] < 0
                or report.get("truncation_reason") is not None
                or type(report.get("unique_count")) is not int
                or type(report.get("duplicate_count")) is not int
                or report["unique_count"] < 0
                or report["duplicate_count"] < 0
                or not isinstance(report.get("pages"), list)
                or not 1 <= len(report["pages"]) <= MAX_PAGES
            ):
                raise CatalogueError("invalid_partition_report")
            for error in report["errors"]:
                if (
                    not isinstance(error, dict)
                    or set(error) != {"offset", "attempt", "code", "at"}
                    or type(error["offset"]) is not int
                    or error["offset"] < 0
                    or error["offset"] % PAGE_SIZE != 0
                    or type(error["attempt"]) is not int
                    or error["attempt"] not in (1, 2)
                    or error["code"] != "provider_error"
                ):
                    raise CatalogueError("invalid_partition_error")
                parse_time(error["at"])
            total: int | None = None
            for index, page in enumerate(report["pages"]):
                if (
                    not isinstance(page, dict)
                    or set(page)
                    != {
                        "offset",
                        "count",
                        "total",
                        "requested_at",
                        "responded_at",
                        "identity_digest",
                    }
                    or type(page.get("offset")) is not int
                    or page["offset"] != index * PAGE_SIZE
                    or type(page.get("count")) is not int
                    or not 0 <= page["count"] <= PAGE_SIZE
                    or type(page.get("total")) is not int
                    or page["total"] < 0
                    or (total is not None and page["total"] != total)
                    or not isinstance(page.get("identity_digest"), str)
                    or len(page["identity_digest"]) != 64
                ):
                    raise CatalogueError("invalid_page_report")
                parse_time(page["requested_at"])
                parse_time(page["responded_at"])
                linked = records_by_page.pop((country, exchange, page["offset"]), [])
                if (
                    len(linked) != page["count"]
                    or digest(sorted(record["listing_id"] for record in linked))
                    != page["identity_digest"]
                    or any(record["observed_at"] != page["responded_at"] for record in linked)
                ):
                    raise CatalogueError("invalid_page_identity_link")
                total = page["total"]
            if (
                total is None
                or sum(page["count"] for page in report["pages"]) != total
                or report["unique_count"] != total
            ):
                raise CatalogueError("invalid_partition_total")
            reported_count += total
        if len(cat["discovered"]) != reported_count:
            raise CatalogueError("invalid_discovered_total")
        if records_by_page:
            raise CatalogueError("unreferenced_discovered_record")
    elif (
        cat["full_refresh_at"] is not None
        or coverage != {"status": "not_run", "partitions": []}
        or cat["discovered"]
    ):
        raise CatalogueError("invalid_coverage")
    projection = catalogue_projection(cat)
    d = len(cat["discovered"])
    direct_count = len(cat["direct"])
    overlap = d + direct_count - len(projection)
    if cat["counts"] != {
        "discovered": d,
        "direct": direct_count,
        "combined": len(projection),
        "overlap": overlap,
        "direct_only": direct_count - overlap,
    }:
        raise CatalogueError("invalid_counts")
    body = {k: v for k, v in cat.items() if k != "version"}
    if cat["version"] != digest(body):
        raise CatalogueError("invalid_digest")
    return cat


def make_catalogue(
    *,
    parent: dict[str, Any] | None,
    operation: str,
    discovered: list[dict[str, Any]],
    direct: list[dict[str, Any]],
    coverage: dict[str, Any],
    full_refresh_at: str | None,
    created_at: str,
) -> dict[str, Any]:
    cat: dict[str, Any] = {
        "schema": SCHEMA,
        "version": "",
        "parent": parent["version"] if parent else None,
        "operation": operation,
        "mapping_version": MAP_VERSION,
        "manifest": [list(p) for p in MANIFEST],
        "discovered": sorted(discovered, key=lambda x: x["listing_id"]),
        "direct": sorted(direct, key=lambda x: x["listing_id"]),
        "coverage": coverage,
        "full_refresh_at": full_refresh_at,
        "created_at": parse_time(created_at),
        "counts": {},
    }
    projection = catalogue_projection(cat)
    d, direct_count = len(discovered), len(direct)
    overlap = d + direct_count - len(projection)
    cat["counts"] = {
        "discovered": d,
        "direct": direct_count,
        "combined": len(projection),
        "overlap": overlap,
        "direct_only": direct_count - overlap,
    }
    cat["version"] = digest({k: v for k, v in cat.items() if k != "version"})
    return validate_catalogue(cat)


class CatalogueService:
    def __init__(
        self,
        store: Store,
        pages: PageProvider,
        search: SearchProvider,
        clock: Callable[[], datetime] = utc_now,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.store, self.pages, self.search_provider = store, pages, search
        self.clock, self.monotonic = clock, monotonic

    def local_search(self, text: str, limit: int = 25) -> dict[str, Any]:
        if not 1 <= limit <= 100 or not text.strip():
            raise CatalogueError("invalid_search")
        cat = self.store.read()
        if cat is None:
            return {
                "status": "unavailable",
                "version": None,
                "matches": [],
                "matched_count": 0,
                "limit": limit,
            }
        needle = text.strip().upper()
        matches = [
            p
            for p in catalogue_projection(cat)
            if needle in p["observation"]["symbol"]
            or needle in (p["observation"]["display_name"] or "").upper()
        ]
        discovery_age = None
        if cat["full_refresh_at"] is not None:
            discovery_age = (
                self.clock() - datetime.fromisoformat(cat["full_refresh_at"].replace("Z", "+00:00"))
            ).total_seconds()
        return {
            "status": "direct_only"
            if discovery_age is None
            else "stale"
            if discovery_age >= 86400 or discovery_age < 0
            else "fresh",
            "version": cat["version"],
            "cache_age_seconds": (
                self.clock() - datetime.fromisoformat(cat["created_at"].replace("Z", "+00:00"))
            ).total_seconds(),
            "discovery_age_seconds": discovery_age,
            "matched_count": len(matches),
            "limit": limit,
            "matches": matches[:limit],
        }

    def suggestions(self, text: str) -> dict[str, Any]:
        deadline = self.monotonic() + 10
        try:
            rows = self.search_provider.search(text, MAX_SEARCH, deadline)
            if self.monotonic() > deadline:
                raise CatalogueError("provider_deadline")
        except CatalogueError:
            raise
        except Exception as exc:
            raise CatalogueError("provider_error") from exc
        return {
            "non_exhaustive": True,
            "provider_total": None,
            "provider_total_missing": "not_reported",
            "returned_count": len(rows),
            "limit": MAX_SEARCH,
            "suggestions": [
                observation(
                    r,
                    origin="direct",
                    observed_at=timestamp(self.clock()),
                    provenance={"lookup": symbol(r.get("symbol"))},
                )
                for r in rows
                if r.get("quoteType") == "ETF" and r.get("exchange") in EXCHANGE_MAP
            ],
        }

    def direct_lookup(self, value: str) -> dict[str, Any]:
        sym = symbol(value)
        start = timestamp(self.clock())
        deadline = self.monotonic() + 10
        try:
            try:
                rows = self.search_provider.search(sym, MAX_SEARCH, deadline)
                if self.monotonic() > deadline:
                    raise CatalogueError("provider_deadline")
            except CatalogueError:
                raise
            except Exception as exc:
                raise CatalogueError("provider_error") from exc
            exact = [
                r for r in rows if isinstance(r.get("symbol"), str) and r["symbol"].upper() == sym
            ]
            if len(exact) != 1:
                raise CatalogueError("no_unambiguous_exact_match")
            obs = observation(
                exact[0],
                origin="direct",
                observed_at=timestamp(self.clock()),
                provenance={"lookup": sym},
            )
            return {
                "verification": "verified",
                "observation": obs,
                "requested_at": start,
                "provider_total": None,
                "provider_total_missing": "not_reported",
            }
        except CatalogueError as exc:
            return {"verification": "rejected", "reason": str(exc), "requested_at": start}

    def add_direct(self, value: str) -> dict[str, Any]:
        parent = self.store.read()
        verified = self.direct_lookup(value)
        if verified["verification"] != "verified":
            return {"verification": verified, "publication": "not_attempted"}
        direct = list(parent["direct"]) if parent else []
        obs = verified["observation"]
        direct = [x for x in direct if x["listing_id"] != obs["listing_id"]] + [obs]
        try:
            candidate = make_catalogue(
                parent=parent,
                operation="direct_add",
                discovered=list(parent["discovered"]) if parent else [],
                direct=direct,
                coverage=parent["coverage"] if parent else {"status": "not_run", "partitions": []},
                full_refresh_at=parent["full_refresh_at"] if parent else None,
                created_at=timestamp(self.clock()),
            )
            saved = self.store.publish(candidate, parent["version"] if parent else None)
            return {
                "verification": verified,
                "publication": "published",
                "version": saved["version"],
                "active_projection": next(
                    p for p in catalogue_projection(saved) if p["listing_id"] == obs["listing_id"]
                ),
            }
        except CommittedCleanupError as exc:
            return {
                "verification": verified,
                "publication": "published",
                "version": exc.candidate["version"],
                "cleanup_error": "lock_release_error",
                "active_projection": next(
                    p
                    for p in catalogue_projection(exc.candidate)
                    if p["listing_id"] == obs["listing_id"]
                ),
            }
        except CatalogueError as exc:
            return {
                "verification": verified,
                "publication": "failed",
                "reason": str(exc),
                **self._active_metadata(parent),
            }

    def _active_metadata(self, parent: dict[str, Any] | None) -> dict[str, Any]:
        """Read current validated state after a failed attempt; never call parent current."""
        attempted = parent["version"] if parent else None
        try:
            current = self.store.read()
        except (CatalogueError, OSError):
            return {
                "attempted_parent_version": attempted,
                "active_version": None,
                "active_version_state": "unknown",
            }
        return {
            "attempted_parent_version": attempted,
            "active_version": current["version"] if current else None,
            "active_version_state": "validated",
        }

    def refresh(self, *, force: bool = False) -> dict[str, Any]:
        parent = self.store.read()
        now = self.clock()
        if not force and parent and parent["full_refresh_at"] is not None:
            age = now - datetime.fromisoformat(parent["full_refresh_at"].replace("Z", "+00:00"))
            if timedelta(0) <= age < timedelta(hours=24):
                return {
                    "status": "reused",
                    "version": parent["version"],
                    "age_seconds": age.total_seconds(),
                    "coverage": parent["coverage"],
                }
        deadline = self.monotonic() + REFRESH_SECONDS
        attempts = 0
        discovered: dict[str, dict[str, Any]] = {}
        reports: list[dict[str, Any]] = []
        failed = False
        for country, exchange in MANIFEST:
            report: dict[str, Any] = {
                "country": country,
                "exchange": exchange,
                "query": query(country, exchange),
                "page_size": PAGE_SIZE,
                "sort_field": "ticker",
                "sort_asc": True,
                "source_version": self.pages.version,
                "mapping_version": MAP_VERSION,
                "status": "unattempted",
                "pages": [],
                "unique_count": 0,
                "duplicate_count": 0,
                "rejected_count": 0,
                "errors": [],
                "truncation_reason": None,
            }
            reports.append(report)
            if failed:
                continue
            report["status"] = "incomplete"
            local: dict[str, dict[str, Any]] = {}
            total: int | None = None
            for page_number in range(MAX_PAGES):
                offset = page_number * PAGE_SIZE
                if offset >= MAX_ROWS or (total is not None and offset >= total):
                    break
                response: Mapping[str, Any] | None = None
                for retry in range(2):
                    if attempts >= MAX_ATTEMPTS or self.monotonic() >= deadline:
                        report["truncation_reason"] = "attempt_or_deadline_limit"
                        break
                    attempts += 1
                    requested_at = timestamp(self.clock())
                    try:
                        response = self.pages.page(country, exchange, offset, PAGE_SIZE, deadline)
                        responded_at = timestamp(self.clock())
                        if self.monotonic() > deadline:
                            raise TimeoutError("catalogue_deadline")
                        break
                    except Exception:  # provider errors never become persisted raw exceptions
                        response = None
                        report["errors"].append(
                            {
                                "offset": offset,
                                "attempt": retry + 1,
                                "code": "provider_error",
                                "at": requested_at,
                            }
                        )
                        if retry == 1:
                            report["truncation_reason"] = "provider_error"
                if response is None:
                    break
                try:
                    start, count, received_total = (
                        response[k] for k in ("start", "count", "total")
                    )
                    rows = response["quotes"]
                    if (
                        any(type(x) is not int or x < 0 for x in (start, count, received_total))
                        or not isinstance(rows, list)
                        or start != offset
                        or count != len(rows)
                        or count > PAGE_SIZE
                        or (total is not None and received_total != total)
                        or offset + count > received_total
                    ):
                        raise CatalogueError("invalid_page")
                    total = received_total
                    ids = []
                    for row in rows:
                        if not isinstance(row, dict) or row.get("exchange") != exchange:
                            raise CatalogueError("invalid_row_exchange")
                        obs = observation(
                            row,
                            origin="discovered",
                            observed_at=responded_at,
                            provenance={"country": country, "exchange": exchange, "offset": offset},
                        )
                        key = obs["listing_id"]
                        ids.append(key)
                        if key in local:
                            report["duplicate_count"] += 1
                            # Page provenance/time can differ; source facts must agree.
                            comparable = (
                                "symbol",
                                "exchange",
                                "display_name",
                                "currency",
                                "source_quote_at",
                            )
                            if any(local[key][k] != obs[k] for k in comparable):
                                raise CatalogueError("conflicting_duplicate")
                        else:
                            local[key] = obs
                    report["pages"].append(
                        {
                            "offset": offset,
                            "count": count,
                            "total": total,
                            "requested_at": requested_at,
                            "responded_at": responded_at,
                            "identity_digest": digest(sorted(ids)),
                        }
                    )
                    report["unique_count"] = len(local)
                    if count == 0 and total == 0 and offset == 0:
                        report["status"] = "complete"
                        break
                    if count < PAGE_SIZE and offset + count < total:
                        raise CatalogueError("short_page")
                    if offset + count == total:
                        if len(local) != total:
                            raise CatalogueError("duplicate_total_mismatch")
                        report["status"] = "complete"
                        break
                except (CatalogueError, KeyError, TypeError, ValueError) as exc:
                    report["rejected_count"] += 1
                    report["errors"].append(
                        {
                            "offset": offset,
                            "code": str(exc) if isinstance(exc, CatalogueError) else "invalid_page",
                        }
                    )
                    report["truncation_reason"] = "invalid_page"
                    break
            if report["status"] != "complete":
                report["truncation_reason"] = report["truncation_reason"] or "page_or_row_limit"
                failed = True
            else:
                for key, obs in local.items():
                    if key in discovered:
                        failed = True
                        report["status"] = "incomplete"
                        report["truncation_reason"] = "cross_partition_duplicate"
                        break
                    discovered[key] = obs
        completed_at = timestamp(self.clock())
        coverage = {
            "status": "provider_partitions_complete" if not failed else "incomplete",
            "partitions": reports,
            "unsupported_eu_countries": list(UNSUPPORTED_EU),
            "unsupported_reason": "no_mapped_yahoo_exchange",
            "excluded_venues": [
                "OEM",
                "OQB",
                "OQX",
                "PNK",
                "YHD",
                "AQS",
                "CXE",
                "IOB",
                "LSE",
                "EBS",
            ],
            "excluded_venue_reasons": {
                code: (
                    "otc_or_deleted"
                    if code in {"OEM", "OQB", "OQX", "PNK", "YHD"}
                    else "outside_us_eu_scope"
                )
                for code in ["OEM", "OQB", "OQX", "PNK", "YHD", "AQS", "CXE", "IOB", "LSE", "EBS"]
            },
            "attempts": attempts,
            "completed_at": completed_at,
        }
        if failed:
            return {
                "status": "incomplete",
                "coverage": coverage,
                **self._active_metadata(parent),
            }
        try:
            candidate = make_catalogue(
                parent=parent,
                operation="full_refresh",
                discovered=list(discovered.values()),
                direct=list(parent["direct"]) if parent else [],
                coverage=coverage,
                full_refresh_at=completed_at,
                created_at=completed_at,
            )
            saved = self.store.publish(candidate, parent["version"] if parent else None)
            return {
                "status": "published",
                "version": saved["version"],
                "coverage": coverage,
                "counts": saved["counts"],
            }
        except CommittedCleanupError as exc:
            return {
                "status": "published",
                "version": exc.candidate["version"],
                "coverage": coverage,
                "counts": exc.candidate["counts"],
                "cleanup_error": "lock_release_error",
            }
        except CatalogueError as exc:
            return {
                "status": "failed",
                "reason": str(exc),
                "coverage": coverage,
                **self._active_metadata(parent),
            }


Catalogue = dict[str, Any]
