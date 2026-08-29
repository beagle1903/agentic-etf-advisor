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
) -> ResearchField[T]:
    observed_at = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    return ResearchField[T](
        value=value,
        unit="text",
        provider="test_provider",
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
        top_10_concentration_pct=research_field(12.5, version=version),
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
    assert document.document_id == "research:snapshot-v1:spy"
    assert document.metadata["snapshot_version"] == "snapshot-v1"
    assert document.metadata["benchmark_status"] == "not_reported"
    assert document.metadata["geography_exposures_status"] == "provider_unsupported"
    assert "Benchmark: not reported (not_reported)" in document.content


def test_research_field_requires_value_xor_missing_reason() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        research_field(None)
    with pytest.raises(ValidationError, match="exactly one"):
        research_field("value", missing_reason=MissingReason.NOT_REPORTED)


def test_snapshot_rejects_cross_version_fields() -> None:
    with pytest.raises(ValidationError, match="different snapshot version"):
        ETFResearchSnapshot(
            snapshot_version="snapshot-v2",
            universe_id="test-universe",
            universe_version="1.0.0",
            ingested_at=datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
            records=[research_record(version="snapshot-v1")],
        )
