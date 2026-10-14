"""Optional yfinance transport with per-request deadline enforcement."""

from __future__ import annotations

import importlib
import time
from typing import Any

from .service import CatalogueError


class YahooCatalogueProvider:
    version = "yfinance-1.7.0"

    def __init__(self) -> None:
        try:
            session_base: Any = importlib.import_module("curl_cffi.requests").Session
        except ImportError as exc:
            raise CatalogueError("yfinance_unavailable: install the rag extra") from exc
        yf = importlib.import_module("yfinance")
        if yf.__version__ != "1.7.0":
            raise CatalogueError("unreviewed_yfinance_version")

        class BoundedSession(session_base):  # type: ignore[misc]
            deadline: float = 0

            def request(self, method: Any, url: str, **kwargs: Any) -> Any:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("catalogue_deadline")
                original = kwargs.get("timeout", 30)
                kwargs["timeout"] = min(float(original), 10.0, remaining)
                return super().request(method, url, **kwargs)

        self._yf = yf
        self._session = BoundedSession(impersonate="chrome")

    def page(
        self, country: str, exchange: str, offset: int, size: int, deadline: float
    ) -> dict[str, Any]:
        self._session.deadline = deadline
        q = self._yf.ETFQuery(
            "and",
            [
                self._yf.ETFQuery("eq", ["region", country]),
                self._yf.ETFQuery("eq", ["exchange", exchange]),
            ],
        )
        result = self._yf.screen(
            q, offset=offset, size=size, sortField="ticker", sortAsc=True, session=self._session
        )
        if not isinstance(result, dict):
            raise CatalogueError("invalid_provider_page")
        return result

    def search(self, query: str, limit: int, deadline: float) -> list[dict[str, Any]]:
        self._session.deadline = deadline
        result = self._yf.Search(
            query,
            max_results=limit,
            news_count=0,
            lists_count=0,
            include_cb=False,
            include_nav_links=False,
            include_research=False,
            include_cultural_assets=False,
            enable_fuzzy_query=False,
            recommended=0,
            session=self._session,
            timeout=min(10.0, max(0.001, deadline - time.monotonic())),
        )
        return list(result.quotes)
