"""Typed, field-attributable ETF research snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, TypeVar
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

from etf_advisor.domain.fund_identity import (
    IDENTITY_CONTRACT,
    REGISTRY_PROVIDER,
    RegistryEnvelope,
    canonical_bytes,
    resolve_group,
    valid_key,
)
from etf_advisor.domain.us_eu import listing_region, valid_group_id, valid_isin
from etf_advisor.encoding import (
    FINGERPRINT_KEY,
    ResearchIntegrityError,
    decode_fields,
    document_fingerprint,
    encode_fields,
    reject_schema2_fields,
    schema_version,
    strict_json,
    validate_document,
)
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
    source_weight_pct_decimal: str | None = None

    @model_serializer(mode="wrap")
    def serialize_exposure(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.source_weight_pct_decimal is None:
            result.pop("source_weight_pct_decimal", None)
        return result

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
        return self


class ETFResearchRecord(BaseModel):
    """All material research fields retained for one ETF in one snapshot."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    symbol: str = Field(min_length=1, max_length=12)
    advisory_contract: Literal["us-eu-v1"] | None = None
    identity_contract: Literal["curator-fund-v1"] | None = None
    registry_envelope: RegistryEnvelope | None = None
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
    listing_exchange: ResearchField[str] | None = None
    trading_currency: ResearchField[str] | None = None
    price_unit: ResearchField[str] | None = None
    share_class_id: ResearchField[str] | None = None
    economic_group_id: ResearchField[str] | None = None
    domicile: ResearchField[str] | None = None
    fund_base_currency: ResearchField[str] | None = None
    share_class_currency: ResearchField[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_extensions(cls, value: Any) -> Any:
        if isinstance(value, dict) and (
            ("identity_contract" in value and value["identity_contract"] != IDENTITY_CONTRACT)
            or ("registry_envelope" in value and value["registry_envelope"] is None)
            or ("registry_envelope" in value)
            != (value.get("identity_contract") == IDENTITY_CONTRACT)
        ):
            raise ValueError("Unknown, null or incomplete curator identity contract.")
        if (
            isinstance(value, dict)
            and value.get("advisory_contract") != "us-eu-v1"
            and (
                "advisory_contract" in value
                or any(
                    name in value
                    for name in (
                        "listing_exchange",
                        "trading_currency",
                        "price_unit",
                        "share_class_id",
                        "economic_group_id",
                        "domicile",
                        "fund_base_currency",
                        "share_class_currency",
                    )
                )
            )
        ):
            raise ValueError("Legacy record rejects new-contract fields.")
        return value

    @model_validator(mode="after")
    def validate_contract(self) -> ETFResearchRecord:
        additions = (
            "listing_exchange",
            "trading_currency",
            "price_unit",
            "share_class_id",
            "economic_group_id",
            "domicile",
            "fund_base_currency",
            "share_class_currency",
        )
        if self.advisory_contract == "us-eu-v1":
            if self.identity_contract == IDENTITY_CONTRACT and self.registry_envelope is None:
                raise ValueError("Curator research requires bound proof.")
            if self.identity_contract is None and self.registry_envelope is not None:
                raise ValueError("Issuer research rejects curator proof.")
            if any(getattr(self, name) is None for name in additions):
                raise ValueError("New research requires every explicit source field.")
            units = {
                "listing_exchange": "yahoo_exchange_code",
                "trading_currency": "iso4217",
                "price_unit": "quote_unit",
                "share_class_id": "isin",
                "economic_group_id": (
                    "curator_fund_id"
                    if self.identity_contract == IDENTITY_CONTRACT
                    else "issuer_fund_id"
                ),
                "domicile": "iso3166_alpha2",
                "fund_base_currency": "iso4217",
                "share_class_currency": "iso4217",
            }
            for name, unit in units.items():
                if getattr(self, name).unit != unit:
                    raise ValueError("New research field has invalid unit.")
            assert self.listing_exchange is not None
            assert self.trading_currency is not None
            assert self.price_unit is not None
            assert self.share_class_id is not None
            assert self.economic_group_id is not None
            assert self.domicile is not None
            if any(
                fact.value is not None and fact.provider == "yahoo_finance"
                for fact in (self.share_class_id, self.economic_group_id)
            ):
                raise ValueError("Yahoo cannot establish share-class or economic fund identity.")
            exchange = self.listing_exchange.value
            currency = self.trading_currency.value
            price_unit = self.price_unit.value
            if exchange is not None and (
                not isinstance(exchange, str) or exchange != exchange.upper()
            ):
                raise ValueError("Exchange code is not normalized.")
            if currency is not None and (
                not isinstance(currency, str) or currency not in {"USD", "EUR"}
            ):
                raise ValueError("Trading currency is unsupported.")
            if price_unit is not None and price_unit not in {"USD", "EUR"}:
                raise ValueError("Quote unit is unsupported.")
            if currency is not None and price_unit is not None and currency != price_unit:
                raise ValueError("Trading currency and quote unit conflict.")
            if self.share_class_id.value is not None and (
                not isinstance(self.share_class_id.value, str)
                or not valid_isin(self.share_class_id.value)
            ):
                raise ValueError("Share-class ISIN is invalid.")
            if self.economic_group_id.value is not None and (
                not isinstance(self.economic_group_id.value, str)
                or not (
                    valid_key(self.economic_group_id.value)
                    if self.identity_contract == IDENTITY_CONTRACT
                    else valid_group_id(self.economic_group_id.value)
                    and not self.economic_group_id.value.startswith("curator-fund-v1:")
                )
            ):
                raise ValueError("Economic group identifier is invalid.")
            if (
                self.identity_contract == IDENTITY_CONTRACT
                and self.economic_group_id.value is not None
            ):
                assert self.registry_envelope is not None
                if self.share_class_id.value is None:
                    raise ValueError("Curator group requires proven class ISIN.")
                observed = resolve_group(
                    self.registry_envelope,
                    self.economic_group_id.value,
                    self.share_class_id.value,
                    self.economic_group_id.ingested_at,
                )
                if self.economic_group_id.provider != REGISTRY_PROVIDER:
                    raise ValueError("Curator group requires audited registry provider.")
                fund = next(
                    item
                    for item in self.registry_envelope.snapshot.funds
                    if item.key == self.economic_group_id.value
                )
                sources = {source.id: source for source in self.registry_envelope.snapshot.sources}
                if self.economic_group_id.source_url not in {
                    sources[source_id].url for source_id in fund.current_proof.fund.source_ids
                }:
                    raise ValueError("Curator group requires official Fund-proof URL.")
                if observed != self.economic_group_id.observed_at:
                    raise ValueError("Curator group observation differs from current proof.")
            if self.domicile.value is not None and (
                not isinstance(self.domicile.value, str)
                or not __import__("re").fullmatch(r"[A-Z]{2}", self.domicile.value)
            ):
                raise ValueError("Domicile is invalid.")
            for name in ("fund_base_currency", "share_class_currency"):
                fact = getattr(self, name).value
                if fact is not None and fact not in {"USD", "EUR"}:
                    raise ValueError("Fund or share-class currency is unsupported.")
            region = listing_region(exchange) if isinstance(exchange, str) else None
            if region == "EU" and self.market.value == "us_market":
                raise ValueError("Yahoo market conflicts with EU exchange.")
            if (
                region == "US"
                and self.market.value is not None
                and self.market.value != "us_market"
            ):
                raise ValueError("Yahoo market conflicts with US exchange.")
        elif (
            any(getattr(self, name) is not None for name in additions)
            or self.identity_contract is not None
        ):
            raise ValueError("Legacy research rejects new source fields.")
        return self

    @model_serializer(mode="wrap")
    def serialize_record(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.identity_contract is None:
            result.pop("identity_contract", None)
            result.pop("registry_envelope", None)
        if self.advisory_contract is None:
            result.pop("advisory_contract", None)
            for name in (
                "listing_exchange",
                "trading_currency",
                "price_unit",
                "share_class_id",
                "economic_group_id",
                "domicile",
                "fund_base_currency",
                "share_class_currency",
            ):
                result.pop(name, None)
        return result

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    def research_fields(self) -> dict[str, ResearchField[object]]:
        """Return every field contract keyed by its stable research name."""

        fields: dict[str, ResearchField[object]] = {}
        for field_name in self.__class__.model_fields:
            if field_name in {
                "symbol",
                "advisory_contract",
                "identity_contract",
                "registry_envelope",
            }:
                continue
            value = getattr(self, field_name)
            if isinstance(value, ResearchField):
                fields[field_name] = value
        return fields


class ETFResearchSnapshot(BaseModel):
    """A reproducible universe observation ready for snapshot-scoped indexing."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1)
    advisory_contract: Literal["us-eu-v1"] | None = None
    identity_contract: Literal["curator-fund-v1"] | None = None
    registry_envelope: RegistryEnvelope | None = None
    snapshot_version: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    universe_id: str = Field(min_length=1, max_length=100)
    universe_version: str = Field(min_length=1, max_length=100)
    ingested_at: datetime
    records: list[ETFResearchRecord] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_marker(cls, value: Any) -> Any:
        if isinstance(value, dict) and (
            ("identity_contract" in value and value["identity_contract"] != IDENTITY_CONTRACT)
            or ("registry_envelope" in value and value["registry_envelope"] is None)
            or ("registry_envelope" in value)
            != (value.get("identity_contract") == IDENTITY_CONTRACT)
        ):
            raise ValueError("Unknown, null or incomplete curator snapshot identity.")
        if (
            isinstance(value, dict)
            and "advisory_contract" in value
            and value["advisory_contract"] != "us-eu-v1"
        ):
            raise ValueError("Unknown or null advisory contract.")
        return value

    @model_validator(mode="before")
    @classmethod
    def decode_wire(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        version = schema_version(value.get("schema_version", 1))
        if version == 2:
            records = value.get("records")
            if (
                isinstance(records, list)
                and records
                and all(isinstance(record, ETFResearchRecord) for record in records)
            ):
                return value
            if (
                not isinstance(records, list)
                or not records
                or any(not isinstance(record, dict) or "symbol" not in record for record in records)
            ):
                raise ResearchIntegrityError("schema_encoding")
            copied = dict(value)
            copied["records"] = [
                {
                    "symbol": record["symbol"],
                    **decode_fields(
                        {
                            key: field
                            for key, field in record.items()
                            if key
                            not in {
                                "symbol",
                                "advisory_contract",
                                "identity_contract",
                                "registry_envelope",
                            }
                        }
                    ),
                    **(
                        {"advisory_contract": record["advisory_contract"]}
                        if "advisory_contract" in record
                        else {}
                    ),
                    **(
                        {
                            "identity_contract": record["identity_contract"],
                            "registry_envelope": record["registry_envelope"],
                        }
                        if "identity_contract" in record
                        else {}
                    ),
                }
                for record in records
            ]
            return copied
        for record in value.get("records", []):
            if isinstance(record, dict):
                reject_schema2_fields(
                    {
                        key: field
                        for key, field in record.items()
                        if key
                        not in {
                            "symbol",
                            "advisory_contract",
                            "identity_contract",
                            "registry_envelope",
                        }
                    }
                )
        return value

    @classmethod
    def model_validate_json(
        cls, json_data: str | bytes | bytearray, **kwargs: Any
    ) -> ETFResearchSnapshot:
        text = json_data if isinstance(json_data, str) else bytes(json_data).decode("utf-8")
        return cls.model_validate(strict_json(text), **kwargs)

    @model_serializer(mode="wrap")
    def serialize_snapshot(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.advisory_contract is None:
            result.pop("advisory_contract", None)
        if self.identity_contract is None:
            result.pop("identity_contract", None)
            result.pop("registry_envelope", None)
        if self.schema_version == 2:
            result["records"] = [
                {
                    "symbol": record["symbol"],
                    **encode_fields(
                        {
                            key: field
                            for key, field in record.items()
                            if key
                            not in {
                                "symbol",
                                "advisory_contract",
                                "identity_contract",
                                "registry_envelope",
                            }
                        }
                    ),
                    **(
                        {"advisory_contract": record["advisory_contract"]}
                        if "advisory_contract" in record
                        else {}
                    ),
                    **(
                        {
                            "identity_contract": record["identity_contract"],
                            "registry_envelope": record["registry_envelope"],
                        }
                        if "identity_contract" in record
                        else {}
                    ),
                }
                for record in result["records"]
            ]
        return result

    @field_validator("ingested_at")
    @classmethod
    def normalize_ingested_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Snapshot ingestion timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_snapshot_consistency(self) -> ETFResearchSnapshot:
        if self.advisory_contract == "us-eu-v1" and self.schema_version != 2:
            raise ValueError("New advisory research requires numeric schema 2.")
        if any(record.advisory_contract != self.advisory_contract for record in self.records):
            raise ValueError("Mixed advisory contracts are not a research snapshot.")
        if self.identity_contract == IDENTITY_CONTRACT and (
            self.advisory_contract != "us-eu-v1" or self.registry_envelope is None
        ):
            raise ValueError("Curator identity requires US/EU snapshot and bound proof.")
        if any(
            record.identity_contract != self.identity_contract
            or record.registry_envelope != self.registry_envelope
            for record in self.records
        ):
            raise ValueError("Mixed curator identity proofs are not a research snapshot.")
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
        if self.schema_version == 2:
            for document in self.to_source_documents():
                validate_document(
                    document.document_id, document.content, document.chroma_metadata()
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
        if self.schema_version == 2:
            field_provenance = encode_fields(field_provenance)
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
            "field_provenance_schema_version": self.schema_version,
            "field_provenance_json": json.dumps(
                field_provenance,
                sort_keys=True,
                separators=(",", ":"),
            ),
        }
        if self.advisory_contract == "us-eu-v1":
            metadata["advisory_contract"] = "us-eu-v1"
        if self.identity_contract == IDENTITY_CONTRACT:
            assert self.registry_envelope is not None
            metadata["identity_contract"] = IDENTITY_CONTRACT
            metadata["registry_envelope_json"] = canonical_bytes(
                self.registry_envelope.model_dump(mode="json")
            ).decode("utf-8")
            metadata["registry_envelope_digest"] = self.registry_envelope.digest
        for field_name, research_field in research_fields.items():
            if isinstance(research_field.value, (str, int, float, bool)):
                metadata[field_name] = field_provenance[field_name]["value"]
            metadata[f"{field_name}_status"] = (
                "available"
                if research_field.missing_reason is None
                else research_field.missing_reason.value
            )

        document_id = f"research:{self.snapshot_version}:{digest}:{record.symbol.lower()}"
        content = "\n".join(lines)
        if self.schema_version == 2:
            metadata["numeric_encoding"] = "binary64-text-v1"
            metadata[FINGERPRINT_KEY] = document_fingerprint(document_id, content, metadata)
        return SourceDocument(
            document_id=document_id,
            symbol=record.symbol,
            title=f"{record.symbol} versioned ETF research snapshot",
            content=content,
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
