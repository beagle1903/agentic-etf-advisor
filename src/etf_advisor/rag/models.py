"""Attributable documents and retrieval results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

from etf_advisor.encoding import StrictWireModel, binary_value, schema_version

type MetadataValue = str | int | float | bool
type SectorExposureStatus = Literal[
    "available",
    "not_reported",
    "source_error",
    "provider_unsupported",
    "not_applicable",
]


class SourceDocument(StrictWireModel):
    """A chunk that can be stored in a vector database with provenance."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=300)
    symbol: str = Field(min_length=1, max_length=12)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=12000)
    source: str = Field(min_length=1, max_length=80)
    source_url: str = Field(min_length=1, max_length=1000)
    observed_at: datetime
    document_type: str = Field(default="source", min_length=1, max_length=80)
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("observed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Source document observation timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    def chroma_metadata(self) -> dict[str, MetadataValue]:
        """Return scalar metadata accepted by Chroma."""

        base: dict[str, MetadataValue] = {
            "symbol": self.symbol,
            "source": self.source,
            "source_url": self.source_url,
            "observed_at": self.observed_at.isoformat().replace("+00:00", "Z"),
            "document_type": self.document_type,
        }
        base.update(self.metadata)
        return base


class RetrievedSource(BaseModel):
    """A source document returned by semantic retrieval."""

    document_id: str
    content: str
    metadata: dict[str, MetadataValue]
    distance: float | None = None


class SectorExposure(BaseModel):
    """One normalized, source-reported ETF sector exposure."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    name: str = Field(min_length=1, max_length=200)
    weight_pct: float = Field(ge=0, le=100)
    weight_pct_token: str | None = None

    @model_validator(mode="before")
    @classmethod
    def decode_weight(cls, value: Any) -> Any:
        if isinstance(value, dict) and "weight_pct_token" in value:
            if "weight_pct" in value:
                raise ValueError("Graph weights cannot contain duplicate numeric encodings.")
            return {**value, "weight_pct": binary_value(value["weight_pct_token"], maximum=100)}
        return value

    @model_serializer(mode="wrap")
    def serialize_weight(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.weight_pct_token is None:
            result.pop("weight_pct_token", None)
        else:
            result.pop("weight_pct", None)
        return result

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.replace("_", " ").split())
        if not normalized:
            raise ValueError("Sector exposure names cannot be blank.")
        return normalized


class GraphContext(StrictWireModel):
    """Normalized Neo4j neighborhood linked to one retrieved source document."""

    model_config = ConfigDict(extra="forbid")

    source_document_id: str
    schema_version: int = 1
    symbol: str
    etf_name: str
    fund_family: str | None = None
    category: str | None = None
    sector_exposures_status: SectorExposureStatus | None = None
    sector_exposures: list[SectorExposure] = Field(default_factory=list, max_length=100)

    @model_validator(mode="before")
    @classmethod
    def validate_encoding(cls, value: Any) -> Any:
        if isinstance(value, dict):
            version = schema_version(value.get("schema_version", 1))
            for item in value.get("sector_exposures", []):
                token = isinstance(item, dict) and "weight_pct_token" in item
                if token != (version == 2):
                    raise ValueError("Graph sector encoding must match its schema.")
        return value

    @model_serializer(mode="wrap")
    def serialize_context(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.schema_version == 1:
            result.pop("schema_version", None)
        return result

    @model_validator(mode="after")
    def validate_sector_projection(self) -> GraphContext:
        names = [exposure.name.casefold() for exposure in self.sector_exposures]
        if len(names) != len(set(names)):
            raise ValueError("Graph sector exposures must have unique normalized names.")
        if self.sector_exposures_status == "available" and not self.sector_exposures:
            raise ValueError("Available graph sector exposure context cannot be empty.")
        if self.sector_exposures_status != "available" and self.sector_exposures:
            raise ValueError("Graph sector exposures require an available source status.")
        self.sector_exposures.sort(key=lambda item: (-item.weight_pct, item.name.casefold()))
        return self


class GraphEnrichedSource(RetrievedSource):
    """Semantic result with optional relationship context from Neo4j."""

    graph_context: GraphContext | None = None
