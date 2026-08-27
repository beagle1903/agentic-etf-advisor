"""Attributable documents and retrieval results."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

type MetadataValue = str | int | float | bool


class SourceDocument(BaseModel):
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


class GraphContext(BaseModel):
    """Normalized Neo4j neighborhood linked to one retrieved source document."""

    model_config = ConfigDict(extra="forbid")

    source_document_id: str
    symbol: str
    etf_name: str
    fund_family: str | None = None
    category: str | None = None


class GraphEnrichedSource(RetrievedSource):
    """Semantic result with optional relationship context from Neo4j."""

    graph_context: GraphContext | None = None
