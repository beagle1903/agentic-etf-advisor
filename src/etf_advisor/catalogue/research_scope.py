"""Immutable, bounded Yahoo catalogue membership for explicit research requests."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from etf_advisor.catalogue.mapping import EXCHANGE_MAP, MAP_VERSION
from etf_advisor.catalogue.service import catalogue_projection, validate_catalogue

MAX_SCOPE_MEMBERS = 100
MAX_CATALOGUE_BYTES = 32 * 1024 * 1024


def _digest(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ScopeError(ValueError):
    """A requested scope cannot be safely researched as specified."""


class ScopeFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, serialize_by_alias=True)

    region: Literal["US", "EU"] | None = None
    country: str | None = Field(default=None, max_length=30)
    exchange: str | None = Field(default=None, max_length=12)
    text: str = Field(default="", max_length=100)
    listing_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize(self) -> ScopeFilters:
        object.__setattr__(self, "country", self.country.casefold() if self.country else None)
        object.__setattr__(self, "exchange", self.exchange.upper() if self.exchange else None)
        object.__setattr__(self, "text", " ".join(self.text.split()).casefold())
        if self.exchange is not None and self.exchange not in EXCHANGE_MAP:
            raise ValueError("unsupported_exchange")
        if len(self.listing_ids) != len(set(self.listing_ids)) or any(
            re.fullmatch(r"[0-9a-f]{64}", item) is None for item in self.listing_ids
        ):
            raise ValueError("invalid_listing_ids")
        object.__setattr__(self, "listing_ids", sorted(self.listing_ids))
        return self


class ScopeMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    listing_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    symbol: str = Field(min_length=1, max_length=12)
    exchange: str
    selected_origin: Literal["discovered", "direct"]
    observed_at: str


class CatalogueScopeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, serialize_by_alias=True)

    schema_id: Literal["catalogue-research-scope-v1"] = Field(
        default="catalogue-research-scope-v1", alias="schema"
    )
    catalogue_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    mapping_version: Literal["yahoo-listing-map-v1"] = "yahoo-listing-map-v1"
    filters: ScopeFilters
    members: list[ScopeMember] = Field(min_length=1, max_length=MAX_SCOPE_MEMBERS)
    coverage: dict[str, Any]
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity(self) -> CatalogueScopeV1:
        ids = [member.listing_id for member in self.members]
        symbols = [member.symbol for member in self.members]
        if ids != sorted(set(ids)) or len(symbols) != len(set(symbols)):
            raise ValueError("scope_membership_conflict")
        if any(member.exchange not in EXCHANGE_MAP for member in self.members):
            raise ValueError("unsupported_exchange")
        if self.digest != _digest(self.model_dump(mode="json", exclude={"digest"})):
            raise ValueError("scope_digest_mismatch")
        return self


class CatalogueRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, serialize_by_alias=True)

    schema_id: Literal["catalogue-selection-v1"] = Field(
        default="catalogue-selection-v1", alias="schema"
    )
    scope: CatalogueScopeV1
    snapshot_version: str = Field(min_length=1, max_length=100)
    snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


def plan_catalogue_scope(
    catalogue: dict[str, Any],
    filters: ScopeFilters | dict[str, Any],
    limit: int = MAX_SCOPE_MEMBERS,
) -> CatalogueScopeV1:
    """Resolve the complete validated projection; never use truncated search results."""
    if type(limit) is not int or not 1 <= limit <= MAX_SCOPE_MEMBERS:
        raise ScopeError("invalid_scope_limit")
    if len(json.dumps(catalogue, allow_nan=False).encode("utf-8")) > MAX_CATALOGUE_BYTES:
        raise ScopeError("catalogue_input_limit_exceeded")
    filter_input = filters.model_dump(mode="json") if isinstance(filters, ScopeFilters) else filters
    if len(json.dumps(filter_input, allow_nan=False).encode("utf-8")) > MAX_CATALOGUE_BYTES:
        raise ScopeError("catalogue_input_limit_exceeded")
    validate_catalogue(catalogue)
    selected_filters = ScopeFilters.model_validate(filters)
    rows = catalogue_projection(catalogue)
    matched = [
        row
        for row in rows
        if (
            selected_filters.region is None
            or row["observation"]["region"] == selected_filters.region
        )
        and (
            selected_filters.country is None
            or row["observation"]["country"] == selected_filters.country
        )
        and (
            selected_filters.exchange is None
            or row["observation"]["exchange"] == selected_filters.exchange
        )
        and (
            not selected_filters.text
            or selected_filters.text in row["observation"]["symbol"].casefold()
            or selected_filters.text in (row["observation"]["display_name"] or "").casefold()
        )
    ]
    matched_ids = {row["listing_id"] for row in matched}
    if selected_filters.listing_ids:
        if not set(selected_filters.listing_ids) <= matched_ids:
            raise ScopeError("requested_listing_not_in_filtered_catalogue")
        matched = [row for row in matched if row["listing_id"] in selected_filters.listing_ids]
    if not matched:
        raise ScopeError("empty_scope: matched=0")
    if len(matched) > limit:
        raise ScopeError(f"scope_limit_exceeded: matched={len(matched)} limit={limit}")
    unsupported = [row for row in matched if len(row["observation"]["symbol"]) > 12]
    if unsupported:
        raise ScopeError(f"unsupported_research_symbols: count={len(unsupported)}")
    members = [
        ScopeMember(
            listing_id=row["listing_id"],
            symbol=row["observation"]["symbol"],
            exchange=row["observation"]["exchange"],
            selected_origin=row["selected_origin"],
            observed_at=row["observation"]["observed_at"],
        )
        for row in matched
    ]
    coverage = {
        "discovered": catalogue["counts"]["discovered"],
        "direct": catalogue["counts"]["direct"],
        "direct_only": catalogue["counts"]["direct_only"],
        "overlap": catalogue["counts"]["overlap"],
        "combined": catalogue["counts"]["combined"],
        "matched": len(matched_ids),
        "requested": len(members),
        "full_refresh_at": catalogue["full_refresh_at"],
        "provider": catalogue["coverage"],
    }
    body = dict(
        schema="catalogue-research-scope-v1",
        catalogue_version=catalogue["version"],
        mapping_version=MAP_VERSION,
        filters=selected_filters.model_dump(mode="json"),
        members=[member.model_dump(mode="json") for member in members],
        coverage=coverage,
    )
    return CatalogueScopeV1.model_validate({**body, "digest": _digest(body)})
