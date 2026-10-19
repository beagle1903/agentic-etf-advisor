"""Strict local input for attributed share-class and fund identities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from etf_advisor.domain.us_eu import listing_region, valid_group_id, valid_isin
from etf_advisor.encoding import strict_json
from etf_advisor.research.models import MissingReason, ResearchField

REFERENCE_NAMES = (
    "share_class_id",
    "economic_group_id",
    "domicile",
    "fund_base_currency",
    "share_class_currency",
)
REFERENCE_UNITS = ("isin", "issuer_fund_id", "iso3166_alpha2", "iso4217", "iso4217")


class ReferenceFactsRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=12)
    exchange: str = Field(min_length=1, max_length=8)
    share_class_id: ResearchField[str]
    economic_group_id: ResearchField[str]
    domicile: ResearchField[str]
    fund_base_currency: ResearchField[str]
    share_class_currency: ResearchField[str]

    @model_validator(mode="after")
    def validate_facts(self) -> ReferenceFactsRecord:
        if (
            self.symbol != self.symbol.strip().upper()
            or self.exchange != self.exchange.strip().upper()
            or listing_region(self.exchange) is None
        ):
            raise ValueError("Reference listing is unrecognized or unnormalized.")
        for name, unit in zip(REFERENCE_NAMES, REFERENCE_UNITS, strict=True):
            fact = getattr(self, name)
            if fact.unit != unit:
                raise ValueError("Reference fact unit is invalid.")
        if self.share_class_id.value is not None and not valid_isin(self.share_class_id.value):
            raise ValueError("Reference ISIN checksum is invalid.")
        if self.economic_group_id.value is not None and not valid_group_id(
            self.economic_group_id.value
        ):
            raise ValueError("Reference economic group is invalid.")
        if self.domicile.value is not None and (
            len(self.domicile.value) != 2
            or not self.domicile.value.isalpha()
            or not self.domicile.value.isupper()
        ):
            raise ValueError("Reference domicile is invalid.")
        for name in ("fund_base_currency", "share_class_currency"):
            if (value := getattr(self, name).value) is not None and value not in {"USD", "EUR"}:
                raise ValueError("Reference currency is unsupported.")
        for name in ("share_class_id", "economic_group_id"):
            fact = getattr(self, name)
            if fact.value is not None and fact.provider == "yahoo_finance":
                raise ValueError("Yahoo cannot establish fund identity.")
        return self


class ReferenceFactsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = Field(strict=True)
    records: list[ReferenceFactsRecord] = Field(max_length=10)

    @model_validator(mode="after")
    def validate_file(self) -> ReferenceFactsFile:
        if self.schema_version != 1:
            raise ValueError("Unsupported reference file version.")
        keys = [(record.symbol, record.exchange) for record in self.records]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate reference listing.")
        return self


class ReferenceFactsProvider(Protocol):
    def lookup(self, symbol: str, exchange: str) -> ReferenceFactsRecord | None: ...


@dataclass(frozen=True)
class LocalReferenceFacts:
    records: dict[tuple[str, str], ReferenceFactsRecord]

    def lookup(self, symbol: str, exchange: str) -> ReferenceFactsRecord | None:
        return self.records.get((symbol, exchange))


def load_reference_facts(path: Path | None, universe_symbols: list[str]) -> LocalReferenceFacts:
    if path is None:
        return LocalReferenceFacts({})
    with path.open("rb") as source:
        payload = source.read(1_048_577)
    if len(payload) > 1_048_576:
        raise ValueError("Reference file exceeds the one-MiB input bound.")
    parsed = ReferenceFactsFile.model_validate(strict_json(payload.decode("utf-8")))
    allowed = set(universe_symbols)
    if any(record.symbol not in allowed for record in parsed.records):
        raise ValueError("Reference record is outside the selected universe.")
    return LocalReferenceFacts(
        {(record.symbol, record.exchange): record for record in parsed.records}
    )


def bound_reference_fields(
    record: ReferenceFactsRecord | None,
    *,
    symbol: str,
    observed_at: datetime,
    ingested_at: datetime,
    snapshot_version: str,
) -> dict[str, ResearchField[str]]:
    """Retain source facts while assigning this fresh snapshot's publication coordinates."""

    output: dict[str, ResearchField[str]] = {}
    if record is not None:
        record = ReferenceFactsRecord.model_validate(record.model_dump(mode="python"))
        if record.symbol != symbol:
            raise ValueError("Reference facts belong to a different symbol.")
    for name, unit in zip(REFERENCE_NAMES, REFERENCE_UNITS, strict=True):
        if record is None:
            output[name] = ResearchField[str](
                unit=unit,
                provider="reference_facts",
                source_url=f"https://finance.yahoo.com/quote/{symbol}/",
                observed_at=observed_at,
                ingested_at=ingested_at,
                snapshot_version=snapshot_version,
                missing_reason=MissingReason.PROVIDER_UNSUPPORTED,
            )
        else:
            fact: ResearchField[str] = getattr(record, name)
            output[name] = ResearchField[str].model_validate(
                {
                    **fact.model_dump(mode="python"),
                    "ingested_at": ingested_at,
                    "snapshot_version": snapshot_version,
                }
            )
    return output
