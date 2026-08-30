"""Build source-grounded ETF evidence bundles for workflow review."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from etf_advisor.clock import Clock
from etf_advisor.data.quality import (
    FreshnessStatus,
    MarketDataHealthReport,
    assess_observations,
)
from etf_advisor.domain.profile import InvestmentObjective, InvestorProfile, RiskTolerance
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, MetadataValue

MAX_CANDIDATE_LIMIT = 50


class EvidenceRetrievalError(RuntimeError):
    """Raised when the source-evidence adapter cannot produce a safe result."""


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
    quote_type: str = Field(min_length=1, max_length=40)
    market: str = Field(min_length=1, max_length=80)

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
    def require_etf_quote_type(cls, value: str) -> str:
        if value.strip().upper() != "ETF":
            raise ValueError("Source metadata quote_type must identify an ETF.")
        return "ETF"

    @field_validator("market")
    @classmethod
    def require_us_market(cls, value: str) -> str:
        if value.strip().lower() != "us_market":
            raise ValueError("Source metadata market must identify a US listing.")
        return "us_market"


class CandidateEvidence(BaseModel):
    """One retrievable ETF fact bundle with its original source identity."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    document_id: str = Field(min_length=1, max_length=300)
    symbol: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=12000)
    source: str = Field(min_length=1, max_length=80)
    source_url: str = Field(min_length=1, max_length=1000)
    observed_at: datetime
    quote_type: str = Field(min_length=1, max_length=40)
    market: str = Field(min_length=1, max_length=80)
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
    def require_etf_quote_type(cls, value: str) -> str:
        if value.strip().upper() != "ETF":
            raise ValueError("Candidate evidence quote_type must identify an ETF.")
        return "ETF"

    @field_validator("market")
    @classmethod
    def require_us_market(cls, value: str) -> str:
        if value.strip().lower() != "us_market":
            raise ValueError("Candidate evidence market must identify a US listing.")
        return "us_market"


class CandidateEvidenceBundle(BaseModel):
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

    @field_validator("checked_at")
    @classmethod
    def normalize_checked_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Evidence check timestamps must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_ready_bundle(self) -> CandidateEvidenceBundle:
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
    ) -> None:
        _validate_freshness_window(max_age, future_tolerance)
        self._hybrid_search = hybrid_search
        self._clock = clock
        self._max_age = max_age
        self._future_tolerance = future_tolerance

    def retrieve(self, profile: InvestorProfile, *, limit: int = 5) -> CandidateEvidenceBundle:
        _validate_limit(limit)
        query = build_candidate_query(profile)
        try:
            results = self._hybrid_search.search(query, limit=limit)
        except Exception as exc:
            raise EvidenceRetrievalError("Source evidence retrieval failed.") from exc

        try:
            checked_at = self._clock()
            return select_candidate_evidence(
                profile,
                results,
                query=query,
                checked_at=checked_at,
                max_age=self._max_age,
                future_tolerance=self._future_tolerance,
                limit=limit,
            )
        except Exception as exc:
            raise EvidenceRetrievalError("Source evidence validation failed.") from exc


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
    return (
        f"US-listed ETF research evidence for {objective_text} objectives and "
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
) -> CandidateEvidenceBundle:
    """Validate and preserve ranked source evidence without making ETF recommendations."""

    _validate_limit(limit)
    _validate_freshness_window(max_age, future_tolerance)
    if not query.strip():
        raise ValueError("Evidence query must not be empty.")
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("checked_at must be timezone-aware.")

    bounded_results = list(results[:limit])
    errors: list[str] = []
    warnings: list[str] = []
    parsed: list[tuple[GraphEnrichedSource, SourceProvenance]] = []

    for result in bounded_results:
        try:
            parsed.append((result, _provenance_from_result(result)))
        except ValidationError as exc:
            errors.append(
                f"{result.document_id}: source provenance is invalid: "
                f"{_validation_error_summary(exc)}"
            )
        except ValueError as exc:
            errors.append(f"{result.document_id}: {exc}")

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
            warnings.append(
                f"Graph context for {provenance.symbol} was omitted because it does not match "
                "the source document."
            )
            graph_context = None
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
                "Structured sector exposure evidence is available for every candidate, but "
                "deterministic exclusion screening is deferred; no exclusion claim is made."
            )
        else:
            warnings.append(
                "Sector exclusions remain unverified because one or more candidates lack "
                "available structured sector exposure evidence."
            )

    status = EvidenceStatus.READY if candidates and not errors else EvidenceStatus.BLOCKED
    return CandidateEvidenceBundle(
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
        quote_type=_required_metadata_text(result, "quote_type"),
        market=_required_metadata_text(result, "market"),
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
