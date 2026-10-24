"""Build source-grounded ETF evidence bundles for workflow review."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_serializer,
    model_validator,
)

from etf_advisor.catalogue.research_scope import CatalogueRequestV1
from etf_advisor.clock import Clock
from etf_advisor.data.ecb_fx import FxReferenceProvider
from etf_advisor.data.quality import (
    FreshnessStatus,
    MarketDataHealthReport,
    assess_observations,
)
from etf_advisor.domain.profile import InvestmentObjective, InvestorProfile, RiskTolerance
from etf_advisor.domain.us_eu import FxReferenceObservation
from etf_advisor.encoding import (
    AdvisoryWireModel,
    ResearchIntegrityError,
    StrictWireModel,
    document_schema,
    integrity_diagnostic,
    schema_version,
    strict_json,
    validate_document,
)
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, MetadataValue

MAX_CANDIDATE_LIMIT = 50


class EvidenceRetrievalError(RuntimeError):
    """Raised when the source-evidence adapter cannot produce a safe result."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class EvidenceStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"


class SourceProvenance(BaseModel):
    """The minimum timestamped provenance needed for freshness checks."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=12)
    source: str = Field(min_length=1, max_length=80)
    source_url: str = Field(min_length=1, max_length=1000)
    observed_at: datetime
    advisory_contract: Literal["us-eu-v1"] | None = None
    quote_type: str | None = Field(default=None, min_length=1, max_length=40)
    market: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return _validated_http_source_url(value)

    @field_validator("observed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Source observation timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("quote_type")
    @classmethod
    def require_etf_quote_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("market")
    @classmethod
    def require_us_market(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_legacy_identity(self) -> SourceProvenance:
        if self.advisory_contract is None and (
            self.quote_type != "ETF" or self.market != "us_market"
        ):
            raise ValueError("Legacy source quote_type must be ETF and market must be us_market.")
        return self


class CandidateEvidence(AdvisoryWireModel):
    """One retrievable ETF fact bundle with its original source identity."""

    legacy_extension_fields = frozenset({"listing_exchange", "trading_currency"})

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    document_id: str = Field(min_length=1, max_length=300)
    symbol: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=12000)
    source: str = Field(min_length=1, max_length=80)
    source_url: str = Field(min_length=1, max_length=1000)
    observed_at: datetime
    advisory_contract: Literal["us-eu-v1"] | None = None
    quote_type: str | None = Field(default=None, min_length=1, max_length=40)
    market: str | None = Field(default=None, min_length=1, max_length=80)
    listing_exchange: str | None = None
    trading_currency: str | None = None
    distance: float | None = None
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)
    fund_family: str | None = None
    category: str | None = None
    graph_context: GraphContext | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return _validated_http_source_url(value)

    @field_validator("observed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Candidate evidence timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @field_validator("quote_type")
    @classmethod
    def require_etf_quote_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("market")
    @classmethod
    def require_us_market(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None

    @model_serializer(mode="wrap")
    def serialize_candidate(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.advisory_contract is None:
            for name in ("advisory_contract", "listing_exchange", "trading_currency"):
                result.pop(name, None)
        return result

    @model_validator(mode="after")
    def validate_graph_context_identity(self) -> CandidateEvidence:
        version = validate_document(self.document_id, self.content, self.metadata)
        marker = self.metadata.get("advisory_contract")
        if marker != self.advisory_contract:
            raise ValueError("Candidate advisory contract differs from source metadata.")
        if marker == "us-eu-v1":
            if self.listing_exchange != self.metadata.get(
                "listing_exchange"
            ) or self.trading_currency != self.metadata.get("trading_currency"):
                raise ValueError("Candidate listing or currency differs from source metadata.")
        elif self.quote_type != "ETF" or self.market != "us_market":
            raise ValueError("Legacy candidate requires ETF and US market.")
        if version == 2:
            expected_attributes = {
                "symbol": self.symbol,
                "source": self.source,
                "source_url": self.source_url,
                "observed_at": self.observed_at.isoformat().replace("+00:00", "Z"),
                "name": self.name,
                "fund_family": self.fund_family,
                "category": self.category,
            }
            for key, value in expected_attributes.items():
                metadata_value = self.metadata.get(key, self.symbol if key == "name" else None)
                if metadata_value != value:
                    raise ValueError(
                        "Candidate identity or classification differs from source metadata."
                    )
            if (
                str(self.metadata.get("quote_type")).strip().upper()
                if self.metadata.get("quote_type") is not None
                else None
            ) != self.quote_type or (
                str(self.metadata.get("market")).strip().lower()
                if self.metadata.get("market") is not None
                else None
            ) != self.market:
                raise ValueError(
                    "Candidate instrument classification differs from source metadata."
                )
        if self.graph_context is None:
            return self
        if self.graph_context.schema_version != version:
            raise ValueError("Candidate graph encoding differs from its source document.")
        if version == 2:
            expected_name = str(self.metadata.get("name", self.symbol))
            if self.name != expected_name or self.graph_context.etf_name != expected_name:
                raise ValueError("Candidate names differ from the source document.")
            for field_name in ("fund_family", "category"):
                expected = self.metadata.get(field_name)
                if (
                    getattr(self, field_name) != expected
                    or getattr(self.graph_context, field_name) != expected
                ):
                    raise ValueError(
                        "Candidate graph classifications differ from the source document."
                    )
            provenance = strict_json(str(self.metadata["field_provenance_json"]))[
                "sector_exposures"
            ]
            expected_status = (
                "available"
                if provenance["missing_reason"] is None
                else provenance["missing_reason"]
            )
            expected_weights = {
                " ".join(item["name"].replace("_", " ").split()): item["weight_pct_token"]
                for item in provenance["value"] or []
            }
            actual_weights = {
                item.name: item.weight_pct_token for item in self.graph_context.sector_exposures
            }
            if (
                self.graph_context.sector_exposures_status != expected_status
                or expected_weights != actual_weights
            ):
                raise ValueError("Candidate graph sector facts differ from source provenance.")
        if self.graph_context.source_document_id != self.document_id:
            raise ValueError("Candidate graph context must reference its source document ID.")
        if self.graph_context.symbol.strip().upper() != self.symbol:
            raise ValueError("Candidate graph context symbol must match its source symbol.")
        return self


class CatalogueEvidenceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: CatalogueRequestV1
    retrieved_listing_ids: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_membership(self) -> CatalogueEvidenceContext:
        if self.retrieved_listing_ids != [
            member.listing_id for member in self.request.scope.members
        ]:
            raise ValueError("Catalogue retrieval omitted or reordered scope members.")
        return self


class CandidateEvidenceBundle(StrictWireModel):
    """Review-ready evidence, including freshness results and explicit blockers."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    query: str = Field(min_length=1, max_length=2000)
    objective: InvestmentObjective
    risk_tolerance: RiskTolerance
    excluded_sectors: list[str]
    requested_limit: int = Field(ge=1, le=MAX_CANDIDATE_LIMIT)
    checked_at: datetime
    status: EvidenceStatus
    candidates: list[CandidateEvidence]
    health: MarketDataHealthReport
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    snapshot_version: str | None = None
    snapshot_digest: str | None = None
    schema_version: int = 1
    advisory_contract: Literal["us-eu-v1"] | None = None
    fx_reference: FxReferenceObservation | None = None
    catalogue_context: CatalogueEvidenceContext | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_encoding(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        versions = {
            document_schema(
                item.metadata if isinstance(item, CandidateEvidence) else item.get("metadata", {})
            )
            for item in value.get("candidates", [])
        }
        if len(versions) > 1:
            raise ValueError("Evidence cannot mix research encodings.")
        identities = [
            (item.document_id, item.symbol)
            if isinstance(item, CandidateEvidence)
            else (item.get("document_id"), item.get("symbol"))
            for item in value.get("candidates", [])
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("Evidence candidate identities must be unique.")
        if len({identity[0] for identity in identities}) != len(identities):
            raise ValueError("Evidence document identities must be unique.")
        if len({identity[1] for identity in identities}) != len(identities):
            raise ValueError("Evidence symbols must be unique.")
        marker = value.get("advisory_contract")
        if "catalogue_context" in value and (
            value["catalogue_context"] is None or marker != "us-eu-v1"
        ):
            raise ValueError("Catalogue evidence requires a non-null US/EU context.")
        # An empty blocked result has no candidate encoding to infer. Retain the
        # explicitly selected semantic contract; nonempty candidates remain authoritative.
        version = next(iter(versions), 2 if marker == "us-eu-v1" else 1)
        if "schema_version" in value and schema_version(value["schema_version"]) != version:
            raise ValueError("Evidence schema differs from its candidates.")
        if version == 2 and "schema_version" not in value:
            raise ValueError("Schema-2 evidence requires an explicit bundle marker.")
        if marker == "us-eu-v1":
            if version != 2 or "fx_reference" not in value:
                raise ValueError("New advisory evidence requires schema 2 and FX status.")
        elif "advisory_contract" in value or "fx_reference" in value:
            raise ValueError("Legacy evidence rejects new-contract fields.")
        if any(
            (
                item.advisory_contract
                if isinstance(item, CandidateEvidence)
                else item.get("advisory_contract")
            )
            != marker
            for item in value.get("candidates", [])
        ):
            raise ValueError("Evidence candidates mix advisory contracts.")
        return value

    @model_serializer(mode="wrap")
    def serialize_bundle(self, handler: Any) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        if self.schema_version == 1:
            result.pop("schema_version", None)
        if self.advisory_contract is None:
            result.pop("advisory_contract", None)
            result.pop("fx_reference", None)
        if self.catalogue_context is None:
            result.pop("catalogue_context", None)
        return result

    @field_validator("checked_at")
    @classmethod
    def normalize_checked_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Evidence check timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_ready_bundle(self) -> CandidateEvidenceBundle:
        if self.catalogue_context is not None and self.requested_limit > 10:
            raise ValueError("Catalogue shortlist capacity cannot exceed ten.")
        if self.checked_at != self.health.checked_at:
            raise ValueError("Evidence and health checks must use the same timestamp.")
        if self.health.checked_at.tzinfo is None or self.health.checked_at.utcoffset() is None:
            raise ValueError("Health-check timestamps must be timezone-aware.")
        for observation in self.health.observations:
            _validated_http_source_url(observation.source_url)
            if (
                observation.observed_at.tzinfo is None
                or observation.observed_at.utcoffset() is None
            ):
                raise ValueError("Health observation timestamps must be timezone-aware.")
        recomputed_health = assess_observations(
            self.health.observations,
            checked_at=self.health.checked_at,
            max_age=timedelta(hours=self.health.max_age_hours),
            future_tolerance=timedelta(minutes=self.health.future_tolerance_minutes),
        )
        if recomputed_health != self.health:
            raise ValueError("Evidence health must match recomputed freshness classifications.")
        if self.status == EvidenceStatus.BLOCKED and not self.errors:
            raise ValueError("Blocked evidence must include at least one error.")
        if self.status == EvidenceStatus.READY:
            if self.errors or not self.candidates:
                raise ValueError("Ready evidence must contain candidates and no errors.")
            if not self.health.healthy or not self.health.observations:
                raise ValueError("Ready evidence must have a healthy source report.")
            if any(
                observation.status != FreshnessStatus.CURRENT
                for observation in self.health.observations
            ):
                raise ValueError("Ready evidence cannot contain unhealthy source observations.")
            health_sources = {
                (
                    observation.symbol.strip().upper(),
                    observation.source,
                    observation.source_url,
                    observation.observed_at,
                )
                for observation in self.health.observations
            }
            if self.schema_version == 2:
                candidate_sources = {
                    (
                        candidate.symbol,
                        candidate.source,
                        candidate.source_url,
                        candidate.observed_at,
                    )
                    for candidate in self.candidates
                }
                if (
                    health_sources != candidate_sources
                    or len(self.health.observations) != len(self.candidates)
                    or (
                        self.catalogue_context is None
                        and len(self.candidates) > self.requested_limit
                    )
                ):
                    raise ValueError(
                        "Schema-2 evidence has duplicate or omitted candidate observations."
                    )
                if self.catalogue_context is not None:
                    request = self.catalogue_context.request
                    if (
                        len(self.candidates) != len(request.scope.members)
                        or [candidate.symbol for candidate in self.candidates]
                        != [member.symbol for member in request.scope.members]
                        or any(
                            candidate.document_id != f"research:{request.snapshot_version}:"
                            f"{request.snapshot_digest}:{member.symbol.lower()}"
                            for candidate, member in zip(
                                self.candidates, request.scope.members, strict=True
                            )
                        )
                    ):
                        raise ValueError("Catalogue evidence must contain the complete scope.")
            for candidate in self.candidates:
                candidate_source = (
                    candidate.symbol,
                    candidate.source,
                    candidate.source_url,
                    candidate.observed_at,
                )
                if candidate_source not in health_sources:
                    raise ValueError(
                        "Every ready candidate must have a matching current health observation."
                    )
        return self

    @model_validator(mode="after")
    def validate_snapshot_identity(self) -> CandidateEvidenceBundle:
        if self.status != EvidenceStatus.READY:
            return self
        identities = {
            (candidate.metadata.get("snapshot_version"), candidate.metadata.get("snapshot_digest"))
            for candidate in self.candidates
        }
        if identities == {(None, None)}:
            # Legacy/local adapters have no published catalog. Label their query-specific
            # evidence explicitly; do not manufacture a published research-snapshot identity.
            expected_version = "local-synthetic-v1"
            expected_digest = hashlib.sha256(
                json.dumps(
                    [candidate.model_dump(mode="json") for candidate in self.candidates],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
        elif len(identities) == 1:
            version, snapshot_digest = next(iter(identities))
            if (
                not isinstance(version, str)
                or not version.strip()
                or not isinstance(snapshot_digest, str)
                or len(snapshot_digest) != 64
                or any(c not in "0123456789abcdef" for c in snapshot_digest)
            ):
                raise ValueError("Incomplete research snapshot identity.")
            expected_version, expected_digest = version, snapshot_digest
        else:
            raise ValueError("Mixed research snapshot identities.")
        if (self.snapshot_version is not None or self.snapshot_digest is not None) and (
            self.snapshot_version != expected_version or self.snapshot_digest != expected_digest
        ):
            raise ValueError("Evidence snapshot identity mismatch.")
        if self.catalogue_context is not None and (
            expected_version != self.catalogue_context.request.snapshot_version
            or expected_digest != self.catalogue_context.request.snapshot_digest
        ):
            raise ValueError("Catalogue evidence differs from pinned snapshot.")
        self.snapshot_version, self.snapshot_digest = expected_version, expected_digest
        return self


class CandidateEvidenceRetriever(Protocol):
    """Replaceable boundary for retrieving evidence inside the graph."""

    def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> CandidateEvidenceBundle: ...


class HybridSearch(Protocol):
    """The part of hybrid retrieval needed by the evidence adapter."""

    def search(self, query: str, limit: int = 5) -> list[GraphEnrichedSource]: ...


class HybridCandidateEvidenceRetriever:
    """Turn hybrid search results into freshness-checked review evidence."""

    def __init__(
        self,
        hybrid_search: HybridSearch,
        *,
        clock: Clock,
        max_age: timedelta,
        future_tolerance: timedelta = timedelta(minutes=5),
        fx_provider: FxReferenceProvider | None = None,
        catalogue_reader: Any | None = None,
    ) -> None:
        _validate_freshness_window(max_age, future_tolerance)
        self._hybrid_search = hybrid_search
        self._clock = clock
        self._max_age = max_age
        self._future_tolerance = future_tolerance
        self._fx_provider = fx_provider
        self._catalogue_reader = catalogue_reader

    def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> CandidateEvidenceBundle:
        _validate_limit(limit)
        if profile.catalogue_request is not None and limit > 10:
            raise EvidenceRetrievalError(
                "Catalogue shortlist capacity cannot exceed ten.", code="retrieval_unavailable"
            )
        query = build_candidate_query(profile)
        try:
            if profile.catalogue_request is not None:
                if self._catalogue_reader is None:
                    raise EvidenceRetrievalError(
                        "Catalogue reader unavailable.", code="retrieval_unavailable"
                    )
                results = self._catalogue_reader.load_catalogue_scope(profile.catalogue_request)
            else:
                results = self._hybrid_search.search(query, limit=limit)
        except Exception as exc:
            diagnostic = integrity_diagnostic(exc)
            if getattr(exc, "code", None) is None:
                diagnostic = integrity_diagnostic(
                    EvidenceRetrievalError("", code="retrieval_unavailable")
                )
            raise EvidenceRetrievalError(diagnostic["message"], code=diagnostic["code"]) from None

        try:
            checked_at = self._clock()
            fx_reference = None
            if profile.advisory_contract == "us-eu-v1":
                needs_rate = any(
                    result.metadata.get("advisory_contract") == "us-eu-v1"
                    and result.metadata.get("trading_currency") != profile.base_currency
                    for result in results
                )
                if needs_rate and self._fx_provider is not None:
                    try:
                        fx_reference = self._fx_provider.fetch_eur_usd()
                    except Exception:
                        fx_reference = FxReferenceObservation(
                            status="missing",
                            observed_at=checked_at,
                            effective_date=None,
                            rate_decimal=None,
                            missing_reason="source_unavailable",
                        )
                else:
                    fx_reference = FxReferenceObservation(
                        status="missing",
                        observed_at=checked_at,
                        effective_date=None,
                        rate_decimal=None,
                        missing_reason="source_unavailable" if needs_rate else "not_requested",
                    )
            return select_candidate_evidence(
                profile,
                results,
                query=query,
                checked_at=checked_at,
                max_age=self._max_age,
                future_tolerance=self._future_tolerance,
                limit=limit,
                fx_reference=fx_reference,
            )
        except Exception as exc:
            diagnostic = integrity_diagnostic(exc)
            raise EvidenceRetrievalError(
                "Source evidence validation failed. " + diagnostic["message"],
                code=diagnostic["code"],
            ) from None


def build_candidate_query(profile: InvestorProfile) -> str:
    """Create a deterministic, non-advisory retrieval query from the profile."""

    objective_text = {
        InvestmentObjective.INCOME: "income-oriented",
        InvestmentObjective.BALANCED: "balanced growth and defensive",
        InvestmentObjective.GROWTH: "long-horizon growth",
    }[profile.objective]
    exclusion_text = ""
    if profile.excluded_sectors:
        exclusion_text = (
            " Reported sector exposure must be checked against these exclusions: "
            + ", ".join(profile.excluded_sectors)
            + "."
        )
    listing_scope = "US and EU" if profile.advisory_contract == "us-eu-v1" else "US"
    return (
        f"{listing_scope}-listed ETF research evidence for {objective_text} objectives and "
        f"{profile.risk_tolerance.value} risk tolerance. Return attributable reported "
        f"category, fund family, expense ratio, latest close, and source timestamps."
        f"{exclusion_text}"
    )


def select_candidate_evidence(
    profile: InvestorProfile,
    results: Sequence[GraphEnrichedSource],
    *,
    query: str,
    checked_at: datetime,
    max_age: timedelta,
    future_tolerance: timedelta = timedelta(minutes=5),
    limit: int = 5,
    fx_reference: FxReferenceObservation | None = None,
) -> CandidateEvidenceBundle:
    """Validate and preserve ranked source evidence without making ETF recommendations."""

    _validate_limit(limit)
    _validate_freshness_window(max_age, future_tolerance)
    if profile.catalogue_request is not None and limit > 10:
        raise ValueError("Catalogue shortlist capacity cannot exceed ten.")
    if not query.strip():
        raise ValueError("Evidence query must not be empty.")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("checked_at must be timezone-aware.")

    if profile.catalogue_request is not None:
        request = profile.catalogue_request
        expected_ids = [
            f"research:{request.snapshot_version}:{request.snapshot_digest}:{member.symbol.lower()}"
            for member in request.scope.members
        ]
        if [result.document_id for result in results] != expected_ids:
            raise ResearchIntegrityError("catalogue_scope_integrity")
        bounded_results = list(results)
    else:
        bounded_results = list(results[:limit])
    marker = profile.advisory_contract
    if any(result.metadata.get("advisory_contract") != marker for result in bounded_results):
        raise ResearchIntegrityError("schema_encoding")
    versions = {
        schema_version(result.metadata.get("field_provenance_schema_version", 1))
        for result in bounded_results
    }
    if len(versions) > 1:
        raise ResearchIntegrityError("schema_encoding")
    lossless = versions == {2}
    errors: list[str] = []
    warnings: list[str] = []
    parsed: list[tuple[GraphEnrichedSource, SourceProvenance]] = []

    for result in bounded_results:
        try:
            parsed.append((result, _provenance_from_result(result)))
        except ValidationError as exc:
            if result.document_id.startswith("research:"):
                errors.append(integrity_diagnostic(exc)["message"])
            else:
                errors.append(
                    f"{result.document_id}: source provenance is invalid: "
                    f"{_validation_error_summary(exc)}"
                )
        except ValueError as exc:
            errors.append(
                integrity_diagnostic(exc)["message"]
                if result.document_id.startswith("research:")
                else f"{result.document_id}: {exc}"
            )

    health = assess_observations(
        [provenance for _, provenance in parsed],
        checked_at=checked_at,
        max_age=max_age,
        future_tolerance=future_tolerance,
    )
    if any(item.status != FreshnessStatus.CURRENT for item in health.observations):
        errors.append("Source evidence is blocked until every observation is current.")

    candidates: list[CandidateEvidence] = []
    seen_symbols: set[str] = set()
    for (result, provenance), observation_health in zip(parsed, health.observations, strict=True):
        if observation_health.status != FreshnessStatus.CURRENT:
            continue
        if provenance.symbol in seen_symbols:
            if lossless:
                raise ResearchIntegrityError("schema_encoding")
            warnings.append(
                f"Duplicate source result for {provenance.symbol} omitted; semantic order keeps "
                "the first result."
            )
            continue
        seen_symbols.add(provenance.symbol)
        graph_context = result.graph_context
        if graph_context is not None and (
            graph_context.source_document_id != result.document_id
            or graph_context.symbol.strip().upper() != provenance.symbol
        ):
            if lossless:
                raise ResearchIntegrityError("document_integrity")
            warnings.append(
                f"Graph context for {provenance.symbol} was omitted because it does not match "
                "the source document."
            )
            graph_context = None
        new_fields: dict[str, Any] = (
            {
                "advisory_contract": marker,
                "listing_exchange": _optional_metadata_text(result.metadata, "listing_exchange"),
                "trading_currency": _optional_metadata_text(result.metadata, "trading_currency"),
            }
            if marker
            else {}
        )
        try:
            candidates.append(
                CandidateEvidence(
                    document_id=result.document_id,
                    symbol=provenance.symbol,
                    name=(
                        _optional_metadata_text(result.metadata, "name")
                        or (graph_context.etf_name if graph_context else None)
                        or provenance.symbol
                    ),
                    content=result.content,
                    source=provenance.source,
                    source_url=provenance.source_url,
                    observed_at=provenance.observed_at,
                    **new_fields,
                    quote_type=provenance.quote_type,
                    market=provenance.market,
                    distance=result.distance,
                    metadata=dict(result.metadata),
                    fund_family=(
                        _optional_metadata_text(result.metadata, "fund_family")
                        or (graph_context.fund_family if graph_context else None)
                    ),
                    category=(
                        _optional_metadata_text(result.metadata, "category")
                        or (graph_context.category if graph_context else None)
                    ),
                    graph_context=graph_context,
                )
            )
        except ValidationError as exc:
            if result.document_id.startswith("research:"):
                errors.append(integrity_diagnostic(exc)["message"])
            else:
                errors.append(
                    f"{result.document_id}: evidence fields are invalid: "
                    f"{_validation_error_summary(exc)}"
                )

    if not bounded_results:
        errors.append("No source evidence matched the research query.")
    elif not candidates and not errors:
        errors.append("No usable source evidence remained after validation.")
    if profile.excluded_sectors:
        sector_contexts = [candidate.graph_context for candidate in candidates]
        if sector_contexts and all(
            context is not None and context.sector_exposures_status == "available"
            for context in sector_contexts
        ):
            warnings.append(
                "Structured sector exposure context is attached for deterministic sector "
                "exclusions validation against field provenance."
            )
        else:
            warnings.append(
                "One or more candidates lack available structured sector exposure context; "
                "deterministic screening of sector exclusions will preserve an unknown result."
            )

    status = EvidenceStatus.READY if candidates and not errors else EvidenceStatus.BLOCKED
    extra_fields: dict[str, Any] = (
        {
            "advisory_contract": marker,
            "fx_reference": fx_reference
            or FxReferenceObservation(
                status="missing",
                observed_at=checked_at,
                effective_date=None,
                rate_decimal=None,
                missing_reason="not_requested",
            ),
        }
        if marker
        else {}
    )
    bundle_fields: dict[str, Any] = dict(
        schema_version=(
            document_schema(candidates[0].metadata) if candidates else (2 if marker else 1)
        ),
        **extra_fields,
        query=query,
        objective=profile.objective,
        risk_tolerance=profile.risk_tolerance,
        excluded_sectors=list(profile.excluded_sectors),
        requested_limit=limit,
        checked_at=checked_at,
        status=status,
        candidates=candidates,
        health=health,
        errors=errors,
        warnings=warnings,
    )
    if profile.catalogue_request is not None:
        bundle_fields["catalogue_context"] = CatalogueEvidenceContext(
            request=profile.catalogue_request,
            retrieved_listing_ids=[
                member.listing_id for member in profile.catalogue_request.scope.members
            ],
        )
    return CandidateEvidenceBundle.model_validate(bundle_fields)


def _provenance_from_result(result: GraphEnrichedSource) -> SourceProvenance:
    observed_at_value = result.metadata.get("observed_at")
    if not isinstance(observed_at_value, str) or not observed_at_value.strip():
        raise ValueError("source metadata must include observed_at.")
    try:
        observed_at = datetime.fromisoformat(observed_at_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("source metadata observed_at is not a valid ISO timestamp.") from exc
    return SourceProvenance(
        symbol=_required_metadata_text(result, "symbol"),
        source=_required_metadata_text(result, "source"),
        source_url=_required_metadata_text(result, "source_url"),
        observed_at=observed_at,
        advisory_contract="us-eu-v1"
        if result.metadata.get("advisory_contract") == "us-eu-v1"
        else None,
        quote_type=_optional_metadata_text(result.metadata, "quote_type"),
        market=_optional_metadata_text(result.metadata, "market"),
    )


def _required_metadata_text(result: GraphEnrichedSource, key: str) -> str:
    value = result.metadata.get(key)
    if value is None or isinstance(value, bool):
        raise ValueError(f"source metadata must include non-empty {key}.")
    text = str(value).strip()
    if not text:
        raise ValueError(f"source metadata must include non-empty {key}.")
    return text


def _optional_metadata_text(metadata: dict[str, MetadataValue], key: str) -> str | None:
    value = metadata.get(key)
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return text or None


def _validation_error_summary(error: ValidationError) -> str:
    details: list[str] = []
    for item in error.errors(include_url=False):
        location = ".".join(str(part) for part in item["loc"]) or "value"
        details.append(f"{location}: {item['msg']}")
    return "; ".join(details)


def _validated_http_source_url(value: str) -> str:
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Source URLs must use HTTP(S) and include a host.")
    return normalized


def _validate_limit(limit: int) -> None:
    if limit < 1 or limit > MAX_CANDIDATE_LIMIT:
        raise ValueError(f"Candidate limit must be between 1 and {MAX_CANDIDATE_LIMIT}.")


def _validate_freshness_window(max_age: timedelta, future_tolerance: timedelta) -> None:
    if max_age <= timedelta(0):
        raise ValueError("max_age must be positive.")
    if future_tolerance < timedelta(0):
        raise ValueError("future_tolerance cannot be negative.")
