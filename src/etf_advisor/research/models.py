"""Typed, field-attributable ETF research snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import TypeVar
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from etf_advisor.rag.models import MetadataValue, SourceDocument

ResearchValue = TypeVar("ResearchValue")


class MissingReason(StrEnum):
    """Why a source-backed research field has no usable value."""

    NOT_REPORTED = "not_reported"
    SOURCE_ERROR = "source_error"
    PROVIDER_UNSUPPORTED = "provider_unsupported"
    NOT_APPLICABLE = "not_applicable"


class WeightedExposure(BaseModel):
    """One holding, sector, or geography weight in percentage points."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    name: str = Field(min_length=1, max_length=300)
    weight_pct: float = Field(ge=0, le=100)
    symbol: str | None = Field(default=None, min_length=1, max_length=24)

    @field_validator("name", "symbol")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class ResearchField[ResearchValue](BaseModel):
    """One value with complete provenance or one explicit missing-data reason."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    value: ResearchValue | None = None
    unit: str = Field(min_length=1, max_length=80)
    provider: str = Field(min_length=1, max_length=80)
    source_url: str = Field(min_length=1, max_length=1000)
    observed_at: datetime
    ingested_at: datetime
    snapshot_version: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    missing_reason: MissingReason | None = None

    @field_validator("unit", "provider")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Research field source URLs must use HTTP(S) and include a host.")
        return normalized

    @field_validator("observed_at", "ingested_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Research field timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_value_or_missing_reason(self) -> ResearchField[ResearchValue]:
        if (self.value is None) == (self.missing_reason is None):
            raise ValueError("Provide exactly one of value or missing_reason.")
        if self.ingested_at < self.observed_at:
            raise ValueError("Research field ingestion cannot precede its observation.")
        return self


class ETFResearchRecord(BaseModel):
    """All material research fields retained for one ETF in one snapshot."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    symbol: str = Field(min_length=1, max_length=12)
    name: ResearchField[str]
    quote_type: ResearchField[str]
    market: ResearchField[str]
    category: ResearchField[str]
    fund_family: ResearchField[str]
    benchmark: ResearchField[str]
    expense_ratio_pct: ResearchField[float]
    average_daily_volume: ResearchField[float]
    top_holdings: ResearchField[list[WeightedExposure]]
    sector_exposures: ResearchField[list[WeightedExposure]]
    geography_exposures: ResearchField[list[WeightedExposure]]
    top_10_concentration_pct: ResearchField[float]

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    def research_fields(self) -> dict[str, ResearchField[object]]:
        """Return every field contract keyed by its stable research name."""

        fields: dict[str, ResearchField[object]] = {}
        for field_name in self.__class__.model_fields:
            if field_name == "symbol":
                continue
            value = getattr(self, field_name)
            if isinstance(value, ResearchField):
                fields[field_name] = value
        return fields


class ETFResearchSnapshot(BaseModel):
    """A reproducible universe observation ready for snapshot-scoped indexing."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    snapshot_version: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    universe_id: str = Field(min_length=1, max_length=100)
    universe_version: str = Field(min_length=1, max_length=100)
    ingested_at: datetime
    records: list[ETFResearchRecord] = Field(min_length=1)

    @field_validator("ingested_at")
    @classmethod
    def normalize_ingested_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Snapshot ingestion timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_snapshot_consistency(self) -> ETFResearchSnapshot:
        symbols = [record.symbol for record in self.records]
        if len(symbols) != len(set(symbols)):
            raise ValueError("Research snapshot symbols must be unique.")
        for record in self.records:
            for field_name, research_field in record.research_fields().items():
                if research_field.snapshot_version != self.snapshot_version:
                    raise ValueError(
                        f"{record.symbol}.{field_name} belongs to a different snapshot version."
                    )
                if research_field.ingested_at != self.ingested_at:
                    raise ValueError(
                        f"{record.symbol}.{field_name} has a different ingestion timestamp."
                    )
        return self

    def content_digest(self) -> str:
        """Return a stable digest for review and publication readback."""

        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_source_documents(self) -> list[SourceDocument]:
        """Render one attributable, snapshot-scoped research document per ETF."""

        digest = self.content_digest()
        return [self._to_source_document(record, digest=digest) for record in self.records]

    def _to_source_document(self, record: ETFResearchRecord, *, digest: str) -> SourceDocument:
        source_url = record.name.source_url
        research_fields = record.research_fields()
        observed_at = max(field.observed_at for field in research_fields.values())
        field_provenance = {
            field_name: research_field.model_dump(mode="json")
            for field_name, research_field in research_fields.items()
        }
        lines = [
            f"ETF symbol: {record.symbol}",
            f"Research snapshot: {self.snapshot_version}",
            f"Curated universe: {self.universe_id} ({self.universe_version})",
        ]
        for field_name, research_field in research_fields.items():
            lines.append(_render_field(field_name, research_field))

        metadata: dict[str, MetadataValue] = {
            "symbol": record.symbol,
            "source": record.name.provider,
            "source_url": source_url,
            "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
            "ingested_at": self.ingested_at.isoformat().replace("+00:00", "Z"),
            "snapshot_version": self.snapshot_version,
            "snapshot_digest": digest,
            "universe_id": self.universe_id,
            "universe_version": self.universe_version,
            "document_type": "etf_research_snapshot",
            "field_provenance_schema_version": 1,
            "field_provenance_json": json.dumps(
                field_provenance,
                sort_keys=True,
                separators=(",", ":"),
            ),
        }
        for field_name, research_field in research_fields.items():
            if isinstance(research_field.value, (str, int, float, bool)):
                metadata[field_name] = research_field.value
            metadata[f"{field_name}_status"] = (
                "available"
                if research_field.missing_reason is None
                else research_field.missing_reason.value
            )

        return SourceDocument(
            document_id=(f"research:{self.snapshot_version}:{digest}:{record.symbol.lower()}"),
            symbol=record.symbol,
            title=f"{record.symbol} versioned ETF research snapshot",
            content="\n".join(lines),
            source=record.name.provider,
            source_url=source_url,
            observed_at=observed_at,
            document_type="etf_research_snapshot",
            metadata=metadata,
        )


def _render_field(field_name: str, research_field: ResearchField[object]) -> str:
    label = field_name.replace("_", " ").title()
    if research_field.missing_reason is not None:
        return f"{label}: not reported ({research_field.missing_reason.value})"
    value = research_field.value
    if isinstance(value, list):
        rendered = ", ".join(
            f"{item.name} ({item.weight_pct:g}%)" + (f" [{item.symbol}]" if item.symbol else "")
            for item in value
            if isinstance(item, WeightedExposure)
        )
        return f"{label}: {rendered or 'none'}"
    return f"{label}: {value} {research_field.unit}".rstrip()
