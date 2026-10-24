"""Frozen Issue105 scope and truthful cached-finalization boundary tests."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar

import pytest
from test_us_eu_contract import _record

from etf_advisor.catalogue.research_job import (
    ResearchJobPolicy,
    ResearchJobStore,
    advance_catalogue_research,
    begin_catalogue_research,
    finalize_catalogue_research,
    retry_catalogue_research,
)
from etf_advisor.catalogue.research_scope import ScopeError, plan_catalogue_scope
from etf_advisor.catalogue.service import validate_catalogue
from etf_advisor.data.yahoo_research import YahooResearchAdapter
from etf_advisor.domain.construction import (
    ConstructionReason,
    PortfolioConstructionInput,
    construct_model_portfolio,
    validate_persisted_construction,
)
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.domain.us_eu import valid_isin
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.models import ETFResearchSnapshot
from etf_advisor.research.universe import ResearchUniverse, UniverseMember

FIXTURE = Path(__file__).parent / "fixtures" / "issue105_catalogue_240.json"
CREATED = datetime(2026, 10, 23, 8, tzinfo=UTC)
COLLECTED = datetime(2026, 10, 24, 8, tzinfo=UTC)


def catalogue() -> dict[str, object]:
    return validate_catalogue(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_large_versioned_scope_never_truncates_and_preserves_coverage() -> None:
    cat = catalogue()
    assert cat["counts"]["combined"] == 240
    with pytest.raises(ScopeError, match="scope_limit_exceeded: matched=240 limit=100"):
        plan_catalogue_scope(cat, {})
    with pytest.raises(ScopeError, match="empty_scope"):
        plan_catalogue_scope(cat, {"text": "does-not-exist"})
    selected = [
        row["listing_id"]
        for row in cat["direct"]
        if row["symbol"].startswith("U") and int(row["symbol"][1:]) < 100
    ]
    scope = plan_catalogue_scope(cat, {"listing_ids": selected})
    assert len(scope.members) == 100
    assert scope.coverage["combined"] == 240
    assert scope.coverage["discovered"] == 0
    assert scope.coverage["direct"] == 240
    assert scope.coverage["direct_only"] == 240
    assert scope.coverage["overlap"] == 0
    assert scope.coverage["matched"] == 240
    assert scope.coverage["requested"] == 100
    assert scope.coverage["provider"] == {"status": "not_run", "partitions": []}
    assert scope.members[0].listing_id < scope.members[-1].listing_id
    assert any(member.symbol == "U099" for member in scope.members)
    with pytest.raises(ScopeError, match="scope_limit_exceeded: matched=100 limit=99"):
        plan_catalogue_scope(cat, {"listing_ids": selected}, limit=99)
    selected_101 = [row["listing_id"] for row in cat["direct"][:101]]
    with pytest.raises(ScopeError, match="scope_limit_exceeded: matched=101 limit=100"):
        plan_catalogue_scope(cat, {"listing_ids": selected_101})
    with pytest.raises(ScopeError, match="invalid_scope_limit"):
        plan_catalogue_scope(cat, {"listing_ids": selected[:1]}, limit=0)


def test_oversized_or_malformed_catalogue_rejects_before_scope(monkeypatch) -> None:
    from etf_advisor.catalogue import research_scope

    cat = catalogue()
    monkeypatch.setattr(research_scope, "MAX_CATALOGUE_BYTES", 100)
    with pytest.raises(ScopeError, match="catalogue_input_limit_exceeded"):
        plan_catalogue_scope(cat, {})
    monkeypatch.setattr(research_scope, "MAX_CATALOGUE_BYTES", 32 * 1024 * 1024)
    with pytest.raises(ValueError):
        plan_catalogue_scope({**cat, "mapping_version": "wrong"}, {})


def test_overlap_and_provider_limit_counts_are_pinned(tmp_path: Path) -> None:
    from test_catalogue import row, service

    from etf_advisor.dashboard_app import _catalogue_coverage_summary

    svc, provider, store = service(tmp_path)
    provider.lookups["VWCE.DE"] = [row("VWCE.DE", "GER")]
    assert svc.add_direct("VWCE.DE")["publication"] == "published"
    provider.rows[("de", "GER")] = [row("VWCE.DE", "GER")]
    assert svc.refresh(force=True)["status"] == "published"
    cat = store.read()
    assert cat is not None
    scope = plan_catalogue_scope(cat, {})
    counts = _catalogue_coverage_summary(scope.coverage)
    assert {
        key: counts[key]
        for key in (
            "discovered",
            "direct",
            "direct_only",
            "overlap",
            "combined",
            "matched",
            "requested",
        )
    } == {
        "discovered": 1,
        "direct": 1,
        "direct_only": 0,
        "overlap": 1,
        "combined": 1,
        "matched": 1,
        "requested": 1,
    }
    assert counts["provider_status"] == "provider_partitions_complete"
    assert counts["provider_partitions"] == 42
    assert counts["unsupported_eu_countries"] == list(cat["coverage"]["unsupported_eu_countries"])
    assert counts["excluded_venues"] == cat["coverage"]["excluded_venues"]


def test_directory_symbol_outside_research_limit_reports_unsupported(tmp_path: Path) -> None:
    from test_catalogue import row, service

    symbol = "ABCDEFGHIJKLM"
    svc, provider, store = service(tmp_path)
    provider.lookups[symbol] = [row(symbol, "PCX")]
    assert svc.add_direct(symbol)["publication"] == "published"
    cat = store.read()
    assert cat is not None
    with pytest.raises(ScopeError, match="unsupported_research_symbols: count=1"):
        plan_catalogue_scope(cat, {})


class _FakeFunds:
    fund_overview: ClassVar[dict[str, str]] = {
        "categoryName": "Large Blend",
        "family": "Fixture Funds",
    }
    top_holdings: ClassVar[list[dict[str, object]]] = [
        {"Symbol": "AAA", "Name": "Alpha", "Holding Percent": 0.1},
        {"Symbol": "BBB", "Name": "Beta", "Holding Percent": 0.1},
    ]
    sector_weightings: ClassVar[dict[str, float]] = {"technology": 0.2}


class _Collector:
    def __init__(self, source_at: datetime) -> None:
        self.source_at = source_at
        self.calls: list[str] = []
        self.fail_symbol: str | None = None

    def collect(self, listing, snapshot_version, references, budget, *, clock):
        self.calls.append(listing.symbol)
        if self.fail_symbol == listing.symbol:
            raise RuntimeError("fixture transient failure")
        source_at = self.source_at

        class Ticker:
            funds_data = _FakeFunds()

            def __init__(self):
                self.info = {
                    "longName": f"Fixture {listing.symbol}",
                    "quoteType": "ETF",
                    "market": "us_market" if listing.exchange == "PCX" else "de_market",
                    "category": "Large Blend",
                    "fundFamily": "Fixture Funds",
                    "netExpenseRatio": 0.03,
                    "averageDailyVolume10Day": 1_000_000,
                    "regularMarketTime": int(source_at.timestamp()),
                    "exchange": listing.exchange,
                    "currency": "USD" if listing.exchange == "PCX" else "EUR",
                }

        adapter = YahooResearchAdapter(
            clock=clock,
            ticker_factory=lambda symbol: Ticker(),
            max_attempts=1,
            advisory_contract="us-eu-v1",
            reference_facts=references,
        )
        universe = ResearchUniverse(
            universe_id="fixture",
            universe_version="1",
            members=[UniverseMember(symbol=listing.symbol, role="fixture")],
        )
        return adapter.fetch_snapshot(universe, snapshot_version=snapshot_version).records[0]


def test_late_complete_finalization_reuses_cache_and_exact_coordinates(tmp_path: Path) -> None:
    cat = catalogue()
    chosen = [row["listing_id"] for row in cat["direct"] if row["symbol"] in {"U119", "E119.DE"}]
    scope = plan_catalogue_scope(cat, {"listing_ids": chosen})
    store = ResearchJobStore(tmp_path)
    job = begin_catalogue_research(
        scope, [], ResearchJobPolicy(batch_size=2), clock=lambda: CREATED, store=store
    )
    collector = _Collector(COLLECTED - timedelta(minutes=1))
    job = advance_catalogue_research(
        job.job_id, job.generation, collector=collector, store=store, clock=lambda: COLLECTED
    )
    assert len(job.cached) == 2
    original = {key: value.model_dump(mode="json") for key, value in job.cached.items()}
    snapshot = finalize_catalogue_research(
        job.job_id, store=store, clock=lambda: COLLECTED + timedelta(minutes=1)
    )
    assert snapshot.ingested_at == COLLECTED + timedelta(minutes=1)
    assert all(
        field.ingested_at == snapshot.ingested_at
        for record in snapshot.records
        for field in record.research_fields().values()
    )
    assert all(
        field.observed_at == COLLECTED - timedelta(minutes=1)
        for record in snapshot.records
        for field in record.research_fields().values()
    )
    assert {
        key: value.model_dump(mode="json") for key, value in store.read(job.job_id).cached.items()
    } == original
    assert (
        finalize_catalogue_research(
            job.job_id, store=store, clock=lambda: COLLECTED + timedelta(days=20)
        ).content_digest()
        == snapshot.content_digest()
    )
    assert collector.calls == [member.symbol for member in scope.members]


def test_failure_keeps_success_and_exact_retry_only_failed_member(tmp_path: Path) -> None:
    from etf_advisor.dashboard_app import _catalogue_job_summary

    cat = catalogue()
    scope = plan_catalogue_scope(
        cat,
        {
            "listing_ids": [
                row["listing_id"] for row in cat["direct"] if row["symbol"] in {"U118", "U119"}
            ]
        },
    )
    store = ResearchJobStore(tmp_path)
    job = begin_catalogue_research(
        scope, [], ResearchJobPolicy(batch_size=2), clock=lambda: CREATED, store=store
    )
    collector = _Collector(CREATED - timedelta(minutes=1))
    collector.fail_symbol = scope.members[1].symbol
    job = advance_catalogue_research(
        job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
    )
    assert len(job.cached) == 1
    assert job.attempts[scope.members[1].listing_id][-1].status == "failed"
    assert {
        key: _catalogue_job_summary(job)[key]
        for key in ("requested", "researched", "pending", "failed")
    } == {"requested": 2, "researched": 1, "pending": 1, "failed": 1}
    assert (
        advance_catalogue_research(
            job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
        )
        == job
    )
    first_cache = job.cached[scope.members[0].listing_id].model_dump(mode="json")
    collector.fail_symbol = None
    job = retry_catalogue_research(
        job.job_id,
        scope.members[1].listing_id,
        job.attempts[scope.members[1].listing_id][-1].attempt_id,
        job.generation,
        collector=collector,
        store=store,
        clock=lambda: CREATED,
    )
    assert len(job.cached) == 2
    assert job.cached[scope.members[0].listing_id].model_dump(mode="json") == first_cache
    assert collector.calls.count(scope.members[0].symbol) == 1
    assert collector.calls.count(scope.members[1].symbol) == 2


def _isin(index: int) -> str:
    stem = f"US{index:09d}"
    return next(stem + str(digit) for digit in range(10) if valid_isin(stem + str(digit)))


def _large_construction(
    objective: str,
    risk: str,
    *,
    alternative_case: bool = False,
    excluded_sectors: list[str] | None = None,
    contradiction: bool = False,
    shortlist_limit: int = 10,
):
    from etf_advisor.catalogue.research_scope import CatalogueRequestV1
    from etf_advisor.domain.us_eu import FxReferenceObservation

    cat = catalogue()
    scope = plan_catalogue_scope(
        cat,
        {
            "listing_ids": [
                row["listing_id"] for row in cat["direct"][: 4 if alternative_case else 40]
            ]
        },
    )
    version = "synthetic-issue105-v1"
    records = []
    for index, member in enumerate(scope.members):
        category = (
            (
                "Intermediate Core Bond"
                if index == 1
                else "Large Blend"
                if index in {0, 2}
                else "Large Growth"
            )
            if alternative_case
            else (
                "Unsupported"
                if index < 10
                else "Intermediate Core Bond"
                if index % 3 == 0
                else "Large Blend"
                if index % 3 == 1
                else "Large Growth"
            )
        )
        record = _record(
            member.symbol,
            member.exchange,
            "USD" if member.exchange == "PCX" else "EUR",
            category,
            _isin(index),
        )
        if contradiction and index == 35:
            record = record.model_copy(
                update={
                    "share_class_id": record.share_class_id.model_copy(update={"value": _isin(11)})
                }
            )
        if alternative_case and index in {0, 1}:
            record = record.model_copy(
                update={
                    "economic_group_id": record.economic_group_id.model_copy(
                        update={"value": "issuer:000"}
                    )
                }
            )
        updates = {
            name: field.model_copy(update={"snapshot_version": version})
            for name, field in record.research_fields().items()
        }
        records.append(record.model_copy(update=updates))
    snapshot = ETFResearchSnapshot(
        schema_version=2,
        advisory_contract="us-eu-v1",
        snapshot_version=version,
        universe_id="catalogue-research-v1",
        universe_version=scope.digest,
        ingested_at=records[0].name.ingested_at,
        records=records,
    )
    request = CatalogueRequestV1(
        scope=scope, snapshot_version=version, snapshot_digest=snapshot.content_digest()
    )
    profile = InvestorProfile(
        advisory_contract="us-eu-v1",
        base_currency="USD",
        horizon_years=12,
        risk_tolerance=risk,
        objective=objective,
        max_drawdown_pct=25,
        initial_investment_minor=100_001,
        recurring_monthly_minor=501,
        excluded_sectors=excluded_sectors or [],
        catalogue_request=request,
    )
    sources = [
        GraphEnrichedSource(
            document_id=doc.document_id,
            content=doc.content,
            metadata=doc.metadata,
            distance=None,
        )
        for doc in snapshot.to_source_documents()
    ]
    checked = records[0].name.observed_at
    fx = FxReferenceObservation(
        status="available",
        effective_date=checked.date(),
        observed_at=checked,
        rate_decimal="1.1253",
        missing_reason=None,
    )
    evidence = select_candidate_evidence(
        profile,
        sources,
        query="synthetic catalogue",
        checked_at=checked,
        max_age=timedelta(hours=120),
        limit=shortlist_limit,
        fx_reference=fx,
    )
    screening = screen_candidate_evidence(evidence)
    inputs = PortfolioConstructionInput(
        profile=profile,
        policy_calculation=calculate_policy(profile),
        candidate_evidence=evidence,
        candidate_screening=screening,
    )
    return inputs, construct_model_portfolio(inputs)


def test_full_40_pool_shortlists_after_first_ten_and_preserves_exact_totals() -> None:
    inputs, result = _large_construction("balanced", "moderate")
    assert len(inputs.candidate_evidence.candidates) == 40
    assert len(inputs.candidate_screening.candidates) == 40
    assert result.status == "ready"
    assert result.catalogue_selection is not None
    report = result.catalogue_selection
    assert report.usable_count == 30
    assert len(report.dispositions) == 40
    assert len(report.shortlist_ids) == 10
    assert all(item.reason == "category_unsupported" for item in report.dispositions[:10])
    assert all(position.document_id in report.shortlist_ids for position in result.draft.positions)
    assert result.draft.total_weight_bps == 10_000
    assert sum(position.initial_base_minor for position in result.draft.positions) == 100_001
    assert sum(position.recurring_base_minor for position in result.draft.positions) == 501
    assert construct_model_portfolio(inputs).model_dump(mode="json") == result.model_dump(
        mode="json"
    )
    assert validate_persisted_construction(inputs, result) == result


def test_contrasting_profiles_change_catalogue_shortlist_targets() -> None:
    _, growth = _large_construction("growth", "aggressive")
    _, income = _large_construction("income", "conservative")
    assert growth.catalogue_selection is not None
    assert income.catalogue_selection is not None
    assert growth.catalogue_selection.target_bps != income.catalogue_selection.target_bps
    assert growth.catalogue_selection.shortlist_ids != income.catalogue_selection.shortlist_ids


def test_exclusions_and_full_pool_identity_conflict_are_not_hidden_by_shortlist() -> None:
    _, baseline = _large_construction("balanced", "moderate")
    _, excluded = _large_construction(
        "balanced", "moderate", excluded_sectors=["Synthetic Holding"]
    )
    assert baseline.catalogue_selection is not None
    assert excluded.catalogue_selection is not None
    assert baseline.catalogue_selection.usable_count == 30
    assert excluded.catalogue_selection.usable_count == 0
    assert excluded.status == "blocked"
    assert len(excluded.catalogue_selection.dispositions) == 40
    assert all(not item.shortlisted for item in excluded.catalogue_selection.dispositions)
    _, conflict = _large_construction("balanced", "moderate", contradiction=True)
    assert conflict.status == "blocked"
    assert any(
        error.code == ConstructionReason.ECONOMIC_IDENTITY_CONFLICT for error in conflict.errors
    )


def test_bounded_shortlist_can_be_infeasible_despite_full_pool_alternative() -> None:
    _, bounded = _large_construction(
        "balanced", "moderate", alternative_case=True, shortlist_limit=3
    )
    _, feasible = _large_construction(
        "balanced", "moderate", alternative_case=True, shortlist_limit=4
    )
    assert bounded.status == "blocked"
    assert feasible.status == "ready"
    assert bounded.catalogue_selection is not None
    assert feasible.catalogue_selection is not None
    assert bounded.catalogue_selection.usable_count == 4
    assert len(bounded.catalogue_selection.shortlist_ids) == 3
    assert len(feasible.catalogue_selection.shortlist_ids) == 4
    assert any(error.code == ConstructionReason.MISSING_SLEEVE_COVERAGE for error in bounded.errors)


def test_alternative_representative_is_retained_but_final_groups_are_unique() -> None:
    inputs, result = _large_construction("balanced", "moderate", alternative_case=True)
    assert result.catalogue_selection is not None
    assert result.catalogue_selection.usable_count == 4
    assert len(result.catalogue_selection.shortlist_ids) == 4
    assert len(result.catalogue_selection.shortlist_ids) <= 10
    symbols = {
        candidate.document_id: candidate.symbol
        for candidate in inputs.candidate_evidence.candidates
    }
    assert [symbols[document_id] for document_id in result.catalogue_selection.shortlist_ids] == [
        "E098.DE",
        "U061",
        "U076",
        "U011",
    ]
    first, alternative = inputs.candidate_evidence.candidates[:2]
    assert first.document_id in result.catalogue_selection.shortlist_ids
    assert alternative.document_id in result.catalogue_selection.shortlist_ids
    assert result.status == "ready"
    assert result.draft is not None
    groups = [position.economic_group_id for position in result.draft.positions]
    assert len(groups) == len(set(groups))
    assert alternative.document_id in {position.document_id for position in result.draft.positions}
    assert first.document_id not in {position.document_id for position in result.draft.positions}
    assert inputs.profile.catalogue_request is not None
    assert (
        plan_catalogue_scope(
            catalogue(),
            {
                "listing_ids": [
                    member.listing_id
                    for member in reversed(inputs.profile.catalogue_request.scope.members)
                ]
            },
        )
        == inputs.profile.catalogue_request.scope
    )


def test_transport_request_deadline_and_receive_body_are_enforced(monkeypatch) -> None:
    import types

    from etf_advisor.data import yahoo_budget

    actual_calls: list[dict[str, object]] = []

    class Session:
        def __init__(self, **kwargs):
            pass

        def request(self, method, url, **kwargs):
            actual_calls.append(kwargs)
            callback = kwargs["content_callback"]
            if callback(b"123") != 3:
                raise RuntimeError("curl_receive_aborted")
            if callback(b"456") != 3:
                raise RuntimeError("curl_receive_aborted")
            return types.SimpleNamespace(content=b"original")

    real_import = yahoo_budget.importlib.import_module

    def fake_import(name):
        if name == "yfinance":
            return types.SimpleNamespace(__version__="1.7.0")
        if name == "curl_cffi.requests":
            return types.SimpleNamespace(Session=Session)
        return real_import(name)

    monkeypatch.setattr(yahoo_budget.importlib, "import_module", fake_import)
    now = [0.0]
    budget = yahoo_budget.YahooRequestBudget(
        deadline=5,
        max_requests=1,
        request_timeout=10,
        max_response_bytes=6,
        monotonic=lambda: now[0],
    )
    session = yahoo_budget.bounded_yahoo_session(budget)
    assert session.request("GET", "https://example.invalid").content == b"123456"
    assert actual_calls[0]["timeout"] == 5
    with pytest.raises(yahoo_budget.YahooBudgetError, match="request_limit"):
        session.request("GET", "https://example.invalid")
    assert len(actual_calls) == 1

    oversized = yahoo_budget.YahooRequestBudget(
        deadline=5,
        max_response_bytes=5,
        monotonic=lambda: now[0],
    )
    with pytest.raises(yahoo_budget.YahooBudgetError, match="receive_limit"):
        yahoo_budget.bounded_yahoo_session(oversized).request("GET", "https://example.invalid")
    assert oversized.breached
    expired = yahoo_budget.YahooRequestBudget(deadline=0, monotonic=lambda: now[0])
    with pytest.raises(yahoo_budget.YahooBudgetError, match="deadline"):
        yahoo_budget.bounded_yahoo_session(expired).request("GET", "https://example.invalid")


def test_finalization_precommit_and_lost_ack_recover_truthfully(
    tmp_path: Path, monkeypatch
) -> None:
    from etf_advisor.catalogue.research_job import ResearchJobError

    cat = catalogue()
    scope = plan_catalogue_scope(cat, {"listing_ids": [cat["direct"][0]["listing_id"]]})
    store = ResearchJobStore(tmp_path)
    job = begin_catalogue_research(
        scope, [], ResearchJobPolicy(), clock=lambda: CREATED, store=store
    )
    collector = _Collector(CREATED - timedelta(minutes=1))
    job = advance_catalogue_research(
        job.job_id, job.generation, collector=collector, store=store, clock=lambda: CREATED
    )
    original_write = store.write

    def precommit(candidate, *, expected_generation):
        if candidate.finalization is not None:
            raise OSError("precommit crash")
        return original_write(candidate, expected_generation=expected_generation)

    monkeypatch.setattr(store, "write", precommit)
    with pytest.raises(OSError, match="precommit"):
        finalize_catalogue_research(job.job_id, store=store, clock=lambda: CREATED)
    assert store.read(job.job_id).finalization is None
    monkeypatch.setattr(store, "write", original_write)
    destination = CREATED + timedelta(minutes=2)

    def postcommit(candidate, *, expected_generation):
        result = original_write(candidate, expected_generation=expected_generation)
        if candidate.finalization is not None:
            raise OSError("ack lost")
        return result

    monkeypatch.setattr(store, "write", postcommit)
    with pytest.raises(OSError, match="ack lost"):
        finalize_catalogue_research(job.job_id, store=store, clock=lambda: destination)
    committed = store.read(job.job_id)
    assert committed.finalization is not None
    monkeypatch.setattr(store, "write", original_write)
    recovered = finalize_catalogue_research(
        job.job_id, store=store, clock=lambda: CREATED + timedelta(days=9)
    )
    assert recovered.ingested_at == destination
    assert recovered.content_digest() == committed.finalization["digest"]
    assert collector.calls == [scope.members[0].symbol]
    with pytest.raises(ResearchJobError, match="job_generation_or_state_conflict"):
        advance_catalogue_research(
            job.job_id, job.generation, collector=collector, store=store, clock=lambda: destination
        )
