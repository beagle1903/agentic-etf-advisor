import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from etf_advisor.research.models import (
    ETFResearchRecord,
    ETFResearchSnapshot,
    MissingReason,
    ResearchField,
    WeightedExposure,
)
from etf_advisor.research.universe import load_research_universe


def research_field[T](
    value: T | None,
    *,
    version: str = "snapshot-v1",
    missing_reason: MissingReason | None = None,
    provider: str = "test_provider",
) -> ResearchField[T]:
    observed_at = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    return ResearchField[T](
        value=value,
        unit="text",
        provider=provider,
        source_url="https://example.com/SPY",
        observed_at=observed_at,
        ingested_at=observed_at,
        snapshot_version=version,
        missing_reason=missing_reason,
    )


def research_record(*, version: str = "snapshot-v1") -> ETFResearchRecord:
    holdings = [WeightedExposure(name="Example Corp", symbol="EX", weight_pct=12.5)]
    return ETFResearchRecord(
        symbol="spy",
        name=research_field("Example ETF", version=version),
        quote_type=research_field("ETF", version=version),
        market=research_field("us_market", version=version),
        category=research_field("Large Blend", version=version),
        fund_family=research_field("Example Funds", version=version),
        benchmark=research_field(
            None,
            version=version,
            missing_reason=MissingReason.NOT_REPORTED,
        ),
        expense_ratio_pct=research_field(0.03, version=version),
        average_daily_volume=research_field(12_000_000.0, version=version),
        top_holdings=research_field(holdings, version=version),
        sector_exposures=research_field(holdings, version=version),
        geography_exposures=research_field(
            None,
            version=version,
            missing_reason=MissingReason.PROVIDER_UNSUPPORTED,
        ),
        top_10_concentration_pct=research_field(
            12.5,
            version=version,
            provider="yahoo_finance_derived",
        ),
    )


def research_snapshot() -> ETFResearchSnapshot:
    return ETFResearchSnapshot(
        snapshot_version="snapshot-v1",
        universe_id="test-universe",
        universe_version="1.0.0",
        ingested_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
        records=[research_record()],
    )


def test_packaged_research_universe_is_versioned_and_reproducible() -> None:
    universe = load_research_universe()

    assert universe.universe_id == "us-etf-research-core"
    assert universe.universe_version == "1.0.0"
    assert universe.symbols == ["SPY", "VTI", "QQQ", "BND", "VEA", "VWO"]


def test_snapshot_renders_explicit_missingness_and_stable_version_metadata() -> None:
    snapshot = research_snapshot()
    document = snapshot.to_source_documents()[0]

    assert snapshot.content_digest() == snapshot.content_digest()
    digest = snapshot.content_digest()
    assert document.document_id == f"research:snapshot-v1:{digest}:spy"
    assert document.metadata["snapshot_version"] == "snapshot-v1"
    assert document.metadata["benchmark_status"] == "not_reported"
    assert document.metadata["geography_exposures_status"] == "provider_unsupported"
    assert "Benchmark: not reported (not_reported)" in document.content

    provenance = json.loads(str(document.metadata["field_provenance_json"]))
    assert document.metadata["field_provenance_schema_version"] == 1
    assert provenance["top_10_concentration_pct"] == {
        "ingested_at": "2026-08-29T12:00:00Z",
        "missing_reason": None,
        "observed_at": "2026-08-29T12:00:00Z",
        "provider": "yahoo_finance_derived",
        "snapshot_version": "snapshot-v1",
        "source_url": "https://example.com/SPY",
        "unit": "text",
        "value": 12.5,
    }
    assert provenance["benchmark"]["missing_reason"] == "not_reported"


def test_same_version_different_content_has_distinct_document_identity() -> None:
    first = research_snapshot()
    second = first.model_copy(deep=True)
    second.records[0].name.value = "Changed ETF name"

    first_document = first.to_source_documents()[0]
    second_document = second.to_source_documents()[0]

    assert first.content_digest() != second.content_digest()
    assert first_document.document_id != second_document.document_id


def test_research_field_requires_value_xor_missing_reason() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        research_field(None)
    with pytest.raises(ValidationError, match="exactly one"):
        research_field("value", missing_reason=MissingReason.NOT_REPORTED)


def test_research_field_preserves_source_clock_ahead_of_ingestion() -> None:
    ingested_at = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)

    field = ResearchField[str](
        value="Example ETF",
        unit="text",
        provider="test_provider",
        source_url="https://example.com/SPY",
        observed_at=datetime(2026, 8, 29, 12, 4, tzinfo=UTC),
        ingested_at=ingested_at,
        snapshot_version="snapshot-v1",
    )

    assert field.ingested_at == ingested_at
    assert field.observed_at > field.ingested_at


def test_snapshot_rejects_cross_version_fields() -> None:
    with pytest.raises(ValidationError, match="different snapshot version"):
        ETFResearchSnapshot(
            snapshot_version="snapshot-v2",
            universe_id="test-universe",
            universe_version="1.0.0",
            ingested_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
            records=[research_record(version="snapshot-v1")],
        )
