"""Strict, immutable prepared evidence for the distinct US/USD starter scope."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from etf_advisor.catalogue.mapping import US_EXCHANGES
from etf_advisor.encoding import strict_json
from etf_advisor.research.models import ETFResearchRecord, ETFResearchSnapshot
from etf_advisor.research.universe import ResearchUniverse

MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
ARTIFACT_ROOT = Path(".artifacts/issue141-prepared")
STARTER_SYMBOLS = (
    "SPY",
    "IVV",
    "VOO",
    "VTI",
    "ITOT",
    "SCHB",
    "QQQ",
    "VUG",
    "SCHG",
    "IWF",
    "VEA",
    "IEFA",
    "SCHF",
    "VWO",
    "IEMG",
    "SCHE",
    "BND",
    "AGG",
    "SCHZ",
    "SPAB",
)
UNIVERSE_DIGEST = "6b492884c7a7ca9f9cdb065ad4cca675c84b4d020fe3c1d5ab45b112c4edd4f6"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def starter_universe() -> ResearchUniverse:
    text = files("etf_advisor.research").joinpath("us_starter_v1.json").read_text("utf-8")
    universe = ResearchUniverse.model_validate(strict_json(text))
    if (
        universe.universe_id != "us-starter"
        or universe.universe_version != "1"
        or tuple(universe.symbols) != STARTER_SYMBOLS
        or _digest(universe.model_dump(mode="json")) != UNIVERSE_DIGEST
    ):
        raise ValueError("starter_universe_invalid")
    return universe


def universe_digest() -> str:
    return UNIVERSE_DIGEST


class StarterRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, serialize_by_alias=True)
    schema_name: Literal["us-starter-request-v1"] = Field(alias="schema")
    universe_id: Literal["us-starter"] = "us-starter"
    universe_version: Literal["1"] = "1"
    universe_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def check_universe(self) -> StarterRequestV1:
        if self.universe_digest != universe_digest():
            raise ValueError("starter_universe_digest_mismatch")
        return self


class StarterListingProof(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["yahoo_finance"]
    symbol: str
    exchange: str
    quote_type: Literal["ETF"]
    market: Literal["us_market"]
    currency: Literal["USD"]
    source_url: str
    observed_at: datetime
    collected_at: datetime

    @model_validator(mode="after")
    def check_listing(self) -> StarterListingProof:
        if (
            self.exchange not in US_EXCHANGES
            or self.source_url != f"https://finance.yahoo.com/quote/{self.symbol}/"
        ):
            raise ValueError("starter_listing_identity_invalid")
        if any(
            value.tzinfo is None or value.utcoffset() is None
            for value in (self.observed_at, self.collected_at)
        ):
            raise ValueError("starter_listing_time_invalid")
        return self


class StarterOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    status: Literal["collected", "failed", "unattempted"]
    reason: str = Field(min_length=1, max_length=160)
    listing: StarterListingProof | None = None
    duplicate_group: str | None = None

    @model_validator(mode="after")
    def check_outcome(self) -> StarterOutcome:
        if self.status == "collected":
            if self.listing is None or self.listing.symbol != self.symbol:
                raise ValueError("starter_collected_listing_missing")
            if self.duplicate_group != f"yahoo_finance:{self.listing.exchange}:{self.symbol}":
                raise ValueError("starter_duplicate_group_invalid")
        elif self.listing is not None or self.duplicate_group is not None:
            raise ValueError("starter_failed_listing_claim")
        return self


class StarterArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)
    schema_name: Literal["us-starter-artifact-v1"] = Field(alias="schema")
    universe_id: Literal["us-starter"] = "us-starter"
    universe_version: Literal["1"] = "1"
    universe_digest: str
    members: list[str] = Field(min_length=20, max_length=20)
    prepared_at: datetime
    outcomes: list[StarterOutcome] = Field(min_length=20, max_length=20)
    duplicate_assertions: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    snapshot: ETFResearchSnapshot | None = None
    digest: str

    @model_validator(mode="after")
    def check_artifact(self) -> StarterArtifact:
        if self.universe_digest != UNIVERSE_DIGEST or tuple(self.members) != STARTER_SYMBOLS:
            raise ValueError("starter_membership_mismatch")
        if [item.symbol for item in self.outcomes] != self.members:
            raise ValueError("starter_outcome_order_mismatch")
        if self.duplicate_assertions:
            raise ValueError("starter_extra_duplicate_assertions_unsupported")
        collected = [item for item in self.outcomes if item.status == "collected"]
        if (self.snapshot is None) != (not collected):
            raise ValueError("starter_snapshot_presence_mismatch")
        if self.snapshot is not None:
            if (
                self.snapshot.schema_version != 2
                or self.snapshot.advisory_contract is not None
                or self.snapshot.identity_contract is not None
                or self.snapshot.universe_id != self.universe_id
                or self.snapshot.universe_version != self.universe_version
                or [record.symbol for record in self.snapshot.records]
                != [item.symbol for item in collected]
            ):
                raise ValueError("starter_snapshot_identity_mismatch")
            for outcome, record in zip(collected, self.snapshot.records, strict=True):
                assert outcome.listing is not None
                fields = record.research_fields()
                if (
                    fields["quote_type"].value != "ETF"
                    or fields["market"].value != "us_market"
                    or any(
                        field.observed_at != outcome.listing.observed_at
                        for field in fields.values()
                        if field.provider == "yahoo_finance"
                    )
                    or any(
                        field.source_url != outcome.listing.source_url
                        for field in fields.values()
                        if field.provider == "yahoo_finance"
                    )
                ):
                    raise ValueError("starter_snapshot_provenance_mismatch")
        payload = self.model_dump(mode="json", exclude={"digest"})
        if self.digest != _digest(payload):
            raise ValueError("starter_artifact_digest_mismatch")
        return self

    @classmethod
    def load(cls, path: Path) -> StarterArtifact:
        raw = path.read_bytes()
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("starter_artifact_size_limit")
        artifact = cls.model_validate(strict_json(raw.decode("utf-8")))
        if path.name != f"{artifact.digest}.json":
            raise ValueError("starter_artifact_filename_mismatch")
        return artifact


def prepare_from_pass(path: Path, root: Path = ARTIFACT_ROOT) -> Path:
    """Detach source facts once; original observation times are never renewed."""
    source = strict_json(path.read_text("utf-8"))
    if source.get("schema") != "issue141-source-pass-v1" or source.get("status") != "complete":
        raise ValueError("starter_source_pass_incomplete")
    by_symbol = {item["symbol"]: item for item in source["outcomes"]}
    universe = starter_universe()
    if len(by_symbol) != 20 or set(by_symbol) != set(universe.symbols):
        raise ValueError("starter_source_pass_membership")
    prepared_at = datetime.fromisoformat(source["finished_at"]).astimezone(UTC)
    outcomes = []
    records = []
    for symbol in universe.symbols:
        item = by_symbol[symbol]
        if item["status"] == "collected":
            listing = StarterListingProof(
                provider=item["provider"],
                symbol=symbol,
                exchange=item["exchange"],
                quote_type=item["quote_type"],
                market=item["market"],
                currency=item["currency"],
                source_url=item["source_url"],
                observed_at=item["observed_at"],
                collected_at=item["collected_at"],
            )
            outcomes.append(
                StarterOutcome(
                    symbol=symbol,
                    status="collected",
                    reason=item["reason"],
                    listing=listing,
                    duplicate_group=f"yahoo_finance:{listing.exchange}:{symbol}",
                )
            )
            original = ETFResearchRecord.model_validate(item["record"])
            fields = original.research_fields()
            updates = {
                name: field.model_copy(
                    update={"ingested_at": prepared_at, "snapshot_version": "us-starter-1"}
                )
                for name, field in fields.items()
            }
            records.append(
                ETFResearchRecord.model_validate(
                    original.model_copy(update=updates).model_dump(mode="python")
                )
            )
        else:
            outcomes.append(
                StarterOutcome(symbol=symbol, status=item["status"], reason=item["reason"])
            )
    snapshot = (
        ETFResearchSnapshot(
            schema_version=2,
            snapshot_version="us-starter-1",
            universe_id="us-starter",
            universe_version="1",
            ingested_at=prepared_at,
            records=records,
        )
        if records
        else None
    )
    payload = dict(
        schema="us-starter-artifact-v1",
        universe_id="us-starter",
        universe_version="1",
        universe_digest=universe_digest(),
        members=universe.symbols,
        prepared_at=prepared_at,
        outcomes=outcomes,
        duplicate_assertions=[],
        snapshot=snapshot,
    )
    plain = {
        key: value.model_dump(mode="json")
        if isinstance(value, BaseModel)
        else [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in value
        ]
        if isinstance(value, list)
        else value.isoformat().replace("+00:00", "Z")
        if isinstance(value, datetime)
        else value
        for key, value in payload.items()
    }
    artifact = StarterArtifact.model_validate({**plain, "digest": _digest(plain)})
    data = _canonical(artifact.model_dump(mode="json"))
    if len(data) > MAX_ARTIFACT_BYTES:
        raise ValueError("starter_artifact_size_limit")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{artifact.digest}.json"
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError("starter_immutable_artifact_collision")
        return target
    with target.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    return target
