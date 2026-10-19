"""Synthetic, source-attributed contract vectors; these do not establish live coverage."""

from datetime import UTC, datetime, timedelta

import pytest

from etf_advisor.domain.construction import PortfolioConstructionInput, construct_model_portfolio
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.domain.us_eu import FxReferenceObservation, listing_region
from etf_advisor.explanation.models import (
    ExplanationContractError,
    ExplanationResult,
    GeneratedExplanation,
    GroundedStatement,
    build_explanation_request,
    validate_and_bundle_explanation,
)
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.models import (
    ETFResearchRecord,
    ETFResearchSnapshot,
    MissingReason,
    ResearchField,
    WeightedExposure,
)

NOW = datetime(2026, 10, 19, 10, tzinfo=UTC)


def _field(value: object, unit: str, *, provider: str = "yahoo_finance") -> ResearchField:
    return ResearchField(
        value=value,
        missing_reason=MissingReason.PROVIDER_UNSUPPORTED if value is None else None,
        unit=unit,
        provider=provider,
        source_url="https://example.com/source",
        observed_at=NOW,
        ingested_at=NOW,
        snapshot_version="synthetic-1",
    )


def _record(
    symbol: str, exchange: str, currency: str, category: str, isin: str
) -> ETFResearchRecord:
    holding = WeightedExposure(
        name="Synthetic Holding", weight_pct=10.0, source_weight_pct_decimal="1e1"
    )
    return ETFResearchRecord(
        advisory_contract="us-eu-v1",
        symbol=symbol,
        name=_field(f"Synthetic {symbol}", "text"),
        quote_type=_field("ETF", "classification"),
        market=_field(
            "us_market" if listing_region(exchange) == "US" else "de_market", "classification"
        ),
        category=_field(category, "classification"),
        fund_family=_field("Synthetic family", "text"),
        benchmark=_field(None, "text"),
        expense_ratio_pct=_field(0.1, "percent"),
        average_daily_volume=_field(200_000.0, "shares_per_day"),
        top_holdings=_field([holding], "percent_of_fund"),
        sector_exposures=_field([holding], "percent_of_fund"),
        geography_exposures=_field(None, "percent_of_fund"),
        top_10_concentration_pct=_field(10.0, "percent", provider="yahoo_finance_derived"),
        listing_exchange=_field(exchange, "yahoo_exchange_code"),
        trading_currency=_field(currency, "iso4217"),
        price_unit=_field(currency, "quote_unit"),
        share_class_id=_field(isin, "isin", provider="issuer"),
        economic_group_id=_field(f"issuer:{symbol.lower()}", "issuer_fund_id", provider="issuer"),
        domicile=_field("IE" if currency == "EUR" else "US", "iso3166_alpha2", provider="issuer"),
        fund_base_currency=_field("USD", "iso4217", provider="issuer"),
        share_class_currency=_field("USD", "iso4217", provider="issuer"),
    )


def test_new_contract_roundtrip_and_mixed_currency_construction() -> None:
    snapshot = ETFResearchSnapshot(
        schema_version=2,
        advisory_contract="us-eu-v1",
        snapshot_version="synthetic-1",
        universe_id="synthetic",
        universe_version="1",
        ingested_at=NOW,
        records=[
            _record("SPY", "NYQ", "USD", "Large Blend", "US78462F1030"),
            _record("CSPX.AS", "AMS", "EUR", "Large Growth", "IE00B5BMR087"),
            _record("BND", "NYQ", "USD", "Intermediate Core Bond", "US9219378356"),
        ],
    )
    assert (
        ETFResearchSnapshot.model_validate_json(snapshot.model_dump_json()).content_digest()
        == snapshot.content_digest()
    )
    documents = snapshot.to_source_documents()
    sources = [
        GraphEnrichedSource(
            document_id=doc.document_id, content=doc.content, metadata=doc.metadata, distance=0.1
        )
        for doc in documents
    ]
    profile = InvestorProfile(
        advisory_contract="us-eu-v1",
        base_currency="USD",
        horizon_years=12,
        risk_tolerance="moderate",
        objective="balanced",
        max_drawdown_pct=25,
        initial_investment_minor=100_000,
        recurring_monthly_minor=25_000,
    )
    fx = FxReferenceObservation(
        status="available",
        effective_date=NOW.date(),
        observed_at=NOW,
        rate_decimal="1.1253",
        missing_reason=None,
    )
    evidence = select_candidate_evidence(
        profile,
        sources,
        query="synthetic",
        checked_at=NOW,
        max_age=timedelta(hours=120),
        limit=3,
        fx_reference=fx,
    )
    assert evidence.status == "ready"
    screening = screen_candidate_evidence(evidence)
    assert all(item.verdict == "pass" for item in screening.candidates)
    construction = construct_model_portfolio(
        PortfolioConstructionInput(
            profile=profile,
            policy_calculation=calculate_policy(profile),
            candidate_evidence=evidence,
            candidate_screening=screening,
        )
    )
    assert construction.status == "ready"
    assert construction.draft is not None
    assert construction.draft.initial_total_minor == 100_000
    assert sum(position.initial_base_minor for position in construction.draft.positions) == 100_000
    assert construction.draft.positions[1].trading_currency == "EUR"
    assert construction.draft.positions[1].fx_reference_id == fx.identity()
    request = build_explanation_request(
        profile=profile.model_dump(mode="json"),
        draft_policy=calculate_policy(profile).model_dump(mode="json"),
        candidate_evidence=evidence.model_dump(mode="json"),
        candidate_screening=screening.model_dump(mode="json"),
        portfolio_construction=construction.model_dump(mode="json"),
    )
    explanation = GeneratedExplanation(
        summary=GroundedStatement(
            text="The illustrative initial cash is USD 1000.00.",
            basis="policy_calculation",
            references=["policy.initial_investment"],
        ),
        policy_points=[
            GroundedStatement(
                text="The base currency is USD.",
                basis="policy_calculation",
                references=["policy.base_currency"],
            )
        ],
        evidence_points=[
            GroundedStatement(
                text="SPY has selected source evidence.",
                basis="source_evidence",
                references=[documents[0].document_id],
                subject_symbols=["SPY"],
            )
        ],
        tradeoffs=[
            GroundedStatement(
                text="The illustrative rules require review.",
                basis="policy_calculation",
                references=["policy.notes"],
            )
        ],
    )
    validated = validate_and_bundle_explanation(
        request, ExplanationResult(provider="test", model="offline", explanation=explanation)
    )
    assert validated.advisory_contract == "us-eu-v1"
    explanation.summary.text = "The illustrative initial cash is EUR 1000.00."
    with pytest.raises(ExplanationContractError, match="Monetary amount"):
        validate_and_bundle_explanation(
            request, ExplanationResult(provider="test", model="offline", explanation=explanation)
        )


def _profile(base="USD", initial=100_001, recurring=1):
    return InvestorProfile(
        advisory_contract="us-eu-v1",
        base_currency=base,
        initial_investment_minor=initial,
        recurring_monthly_minor=recurring,
        horizon_years=12,
        risk_tolerance="moderate",
        objective="balanced",
        max_drawdown_pct=25,
    )


def _snapshot(records=None):
    return ETFResearchSnapshot(
        schema_version=2,
        advisory_contract="us-eu-v1",
        snapshot_version="synthetic-1",
        universe_id="synthetic",
        universe_version="1",
        ingested_at=NOW,
        records=records
        or [
            _record("SPY", "NYQ", "USD", "Large Blend", "US78462F1030"),
            _record("CSPX.AS", "AMS", "EUR", "Large Growth", "IE00B5BMR087"),
            _record("BND", "NYQ", "USD", "Intermediate Core Bond", "US9219378356"),
        ],
    )


def _fx(**changes):
    return FxReferenceObservation.model_validate(
        {
            "status": "available",
            "effective_date": NOW.date(),
            "observed_at": NOW,
            "rate_decimal": "1.1253",
            "missing_reason": None,
            **changes,
        }
    )


def _evidence(snapshot=None, profile=None, fx=None, checked_at=NOW):
    return select_candidate_evidence(
        profile or _profile(),
        [
            GraphEnrichedSource(
                document_id=d.document_id,
                content=d.content,
                metadata=d.metadata,
                distance=0.1,
            )
            for d in (snapshot or _snapshot()).to_source_documents()
        ],
        query="synthetic",
        checked_at=checked_at,
        max_age=timedelta(hours=120),
        limit=10,
        fx_reference=fx,
    )


def _inputs(snapshot=None, profile=None, fx=None, checked_at=NOW):
    profile = profile or _profile()
    evidence = _evidence(snapshot, profile, fx, checked_at)
    return PortfolioConstructionInput(
        profile=profile,
        policy_calculation=calculate_policy(profile),
        candidate_evidence=evidence,
        candidate_screening=screen_candidate_evidence(evidence),
    )


@pytest.mark.parametrize("base", ["USD", "EUR"])
@pytest.mark.parametrize(
    "initial,recurring", [(0, 0), (1, 1), (100_001, 501), (100_000_000_000_000, 0)]
)
def test_exact_base_cash_and_conversion_vectors(base, initial, recurring):
    from fractions import Fraction

    from etf_advisor.domain.construction import validate_portfolio_draft

    result = construct_model_portfolio(
        _inputs(profile=_profile(base, initial, recurring), fx=_fx())
    )
    assert result.status == "ready"
    draft = result.draft
    assert sum(p.initial_base_minor for p in draft.positions) == initial
    assert sum(p.recurring_base_minor for p in draft.positions) == recurring
    assert sum(p.weight_bps for p in draft.positions) == 10_000
    for position in draft.positions:
        if position.base_currency == position.trading_currency:
            assert position.fx_reference_id is None
            assert position.initial_trading_minor == position.initial_base_minor
        else:
            for source, actual in [
                (position.initial_base_minor, position.initial_trading_minor),
                (position.recurring_base_minor, position.recurring_trading_minor),
            ]:
                exact = Fraction(source) * (
                    Fraction(11253, 10000) if base == "EUR" else Fraction(10000, 11253)
                )
                assert actual == (2 * exact.numerator + exact.denominator) // (
                    2 * exact.denominator
                )
            assert position.fx_reference_id == _fx().identity()
    assert validate_portfolio_draft(
        _inputs(profile=_profile(base, initial, recurring), fx=_fx()), draft
    ).valid


@pytest.mark.parametrize("value", [True, 1.0, "1", -1, 100_000_000_000_001])
def test_new_cash_rejects_noninteger_or_out_of_range(value):
    with pytest.raises(ValueError):
        _profile(initial=value)


@pytest.mark.parametrize("exchange", ["LSE", "EBS", "PNK", "XXX"])
def test_unsupported_exchange_fails_screening(exchange):
    snapshot = _snapshot()
    snapshot.records[0].listing_exchange.value = exchange
    evidence = _evidence(snapshot)
    assert screen_candidate_evidence(evidence).candidates[0].verdict == "fail"


def test_all_frozen_exchanges_and_missing_market():
    from etf_advisor.catalogue.mapping import EXCHANGE_MAP

    for exchange, (_, region) in EXCHANGE_MAP.items():
        record = _record("SPY", exchange, "USD", "Large Blend", "US78462F1030")
        record.market = _field(None, "classification")
        evidence = _evidence(_snapshot([record]))
        assert screen_candidate_evidence(evidence).candidates[0].verdict == "pass", (
            exchange,
            region,
        )


@pytest.mark.parametrize(
    "field", ["listing_exchange", "quote_type", "trading_currency", "price_unit"]
)
def test_missing_material_identity_remains_unknown(field):
    snapshot = _snapshot()
    original = getattr(snapshot.records[0], field)
    setattr(snapshot.records[0], field, _field(None, original.unit))
    result = screen_candidate_evidence(_evidence(snapshot)).candidates[0]
    assert result.verdict == "unknown"


@pytest.mark.parametrize("currency", ["GBp", "GBX", "GBP", "US cents"])
def test_subunit_and_unsupported_currency_rejected(currency):
    record = _snapshot().records[0]
    record.trading_currency.value = currency
    with pytest.raises(ValueError):
        ETFResearchRecord.model_validate(record.model_dump())


def test_conflicting_market_and_non_etf():
    snapshot = _snapshot()
    snapshot.records[1].market.value = "us_market"
    with pytest.raises(ValueError):
        ETFResearchSnapshot.model_validate(snapshot.model_dump())
    snapshot = _snapshot()
    snapshot.records[0].quote_type.value = "EQUITY"
    assert screen_candidate_evidence(_evidence(snapshot)).candidates[0].verdict == "fail"


def test_economic_group_duplicates_unknown_and_conflicts():
    snapshot = _snapshot()
    alternate = _record("ALT.AS", "AMS", "EUR", "Large Blend", "US78462F1030")
    alternate.economic_group_id.value = "issuer:spy"
    snapshot.records.insert(1, alternate)
    result = construct_model_portfolio(_inputs(snapshot, fx=_fx()))
    assert result.status == "ready"
    assert len(result.draft.positions) == 3
    omitted = next(c for c in result.excluded_candidates if c.symbol == "ALT.AS")
    assert omitted.reason_code == "duplicate_economic_exposure"
    assert omitted.selected_representative_id == result.draft.positions[0].document_id
    alternate.economic_group_id.value = "issuer:other"
    result = construct_model_portfolio(_inputs(snapshot, fx=_fx()))
    assert result.errors[0].code == "economic_identity_conflict"
    snapshot = _snapshot()
    snapshot.records[0].economic_group_id = _field(None, "issuer_fund_id", provider="issuer")
    result = construct_model_portfolio(_inputs(snapshot, fx=_fx()))
    assert result.status == "blocked"
    assert result.excluded_candidates[0].reason_code == "economic_identity_unknown"


def test_alternative_group_representative_preserves_feasibility():
    # The first representative would leave no defensive sleeve; keep the second in search.
    snapshot = _snapshot()
    snapshot.records[0].economic_group_id.value = "issuer:bnd"
    result = construct_model_portfolio(_inputs(snapshot, fx=_fx()))
    assert result.status == "blocked"  # only two economic groups cannot meet three-position minimum
    other = _record("OTHER", "NYQ", "USD", "Large Blend", "US4642872000")
    snapshot.records.append(other)
    result = construct_model_portfolio(_inputs(snapshot, fx=_fx()))
    assert result.status == "ready"
    assert [p.symbol for p in result.draft.positions] == ["CSPX.AS", "BND", "OTHER"]


@pytest.mark.parametrize("field", ["share_class_id", "economic_group_id"])
def test_stale_reference_identity_blocks_complete_construction(field):
    snapshot = _snapshot()
    getattr(snapshot.records[0], field).observed_at = NOW - timedelta(hours=120, microseconds=1)
    result = construct_model_portfolio(_inputs(snapshot, fx=_fx()))
    assert result.errors[0].code == "evidence_not_ready"


@pytest.mark.parametrize(
    "fx,expected",
    [
        (None, "fx_missing"),
        (_fx(effective_date=(NOW - timedelta(days=6)).date()), "fx_stale"),
        (_fx(observed_at=NOW + timedelta(minutes=5, microseconds=1)), "fx_future"),
    ],
)
def test_required_fx_has_distinct_blockers(fx, expected):
    result = construct_model_portfolio(_inputs(fx=fx))
    assert result.errors[0].code == expected


def test_same_currency_requires_no_fx_and_unused_fx_does_not_change_selection():
    snapshot = _snapshot()
    snapshot.records[1].trading_currency.value = "USD"
    snapshot.records[1].price_unit.value = "USD"
    result = construct_model_portfolio(_inputs(snapshot))
    assert result.status == "ready"
    assert all(p.fx_reference_id is None for p in result.draft.positions)
    snapshot.records.append(_record("UNUSED", "NYQ", "EUR", "Unsupported", "US4642872000"))
    assert construct_model_portfolio(_inputs(snapshot)).status == "ready"


def test_fx_exact_date_and_future_edges():
    from datetime import time

    edge = datetime.combine(NOW.date(), time.min, tzinfo=UTC) + timedelta(hours=120)
    assert _fx().validate_at(edge) is None
    assert _fx().validate_at(edge + timedelta(microseconds=1)) == "fx_stale"
    assert _fx(observed_at=NOW + timedelta(minutes=5)).validate_at(NOW) is None
    assert (
        _fx(observed_at=NOW + timedelta(minutes=5, microseconds=1)).validate_at(NOW) == "fx_future"
    )


@pytest.mark.parametrize(
    "rate", ["01.2", "1.20", "1e0", "+1", "0", "0.0000001", "1000001", "1.12345678901", "NaN"]
)
def test_fx_rate_canonical_bounds(rate):
    with pytest.raises(ValueError):
        _fx(rate_decimal=rate)


@pytest.mark.parametrize(
    "field,value",
    [
        ("initial_trading_minor", 123),
        ("base_currency", "EUR"),
        ("fx_reference_id", "0" * 64),
        ("economic_group_id", "issuer:changed"),
    ],
)
def test_independent_validator_and_persisted_recomputation_reject_tamper(field, value):
    from etf_advisor.domain.construction import (
        validate_persisted_construction,
        validate_portfolio_draft,
    )

    inputs = _inputs(fx=_fx())
    result = construct_model_portfolio(inputs)
    setattr(result.draft.positions[1], field, value)
    assert not validate_portfolio_draft(inputs, result.draft).valid
    assert validate_persisted_construction(inputs, result).status == "blocked"


def test_document_flat_substitution_and_semantic_downgrade_rejected():
    from etf_advisor.encoding import ResearchIntegrityError, validate_document

    document = _snapshot().to_source_documents()[0]
    for key, value in [
        ("listing_exchange", "AMS"),
        ("economic_group_id", "issuer:changed"),
        ("advisory_contract", None),
    ]:
        metadata = dict(document.metadata)
        if value is None:
            metadata.pop(key)
        else:
            metadata[key] = value
        with pytest.raises((ValueError, ResearchIntegrityError)):
            validate_document(document.document_id, document.content, metadata)


def test_null_and_mixed_contracts_reject_across_envelopes():
    from etf_advisor.domain.construction import PortfolioConstructionBundle
    from etf_advisor.domain.policy import PolicyCalculation
    from etf_advisor.domain.screening import CandidateScreeningBundle
    from etf_advisor.rag.evidence import CandidateEvidenceBundle

    inputs = _inputs(fx=_fx())
    result = construct_model_portfolio(inputs)
    for model, payload in [
        (InvestorProfile, _profile().model_dump(mode="json")),
        (PolicyCalculation, inputs.policy_calculation.model_dump(mode="json")),
        (CandidateEvidenceBundle, inputs.candidate_evidence.model_dump(mode="json")),
        (CandidateScreeningBundle, inputs.candidate_screening.model_dump(mode="json")),
        (PortfolioConstructionBundle, result.model_dump(mode="json")),
    ]:
        payload["advisory_contract"] = None
        with pytest.raises(ValueError):
            model.model_validate(payload)


def test_new_policy_cash_ui_exact_input_and_revision_patch():
    from etf_advisor.dashboard_app import _build_feedback_items, _decimal_minor

    assert _decimal_minor("1000000000000.00") == 100_000_000_000_000
    assert _decimal_minor("0.01") == 1
    for value in ["NaN", "1e2", "1.001", "-1", "1,000"]:
        with pytest.raises(ValueError):
            _decimal_minor(value)
    feedback = _build_feedback_items(
        ["profile"],
        {
            "profile": {
                "base_currency": "EUR",
                "initial_decimal_input": "0.01",
                "recurring_decimal_input": "0.00",
            }
        },
    )
    assert feedback[0]["patch"] == {
        "base_currency": "EUR",
        "initial_investment_minor": 1,
        "recurring_monthly_minor": 0,
    }


def _reference_record():
    from etf_advisor.data.reference_facts import REFERENCE_NAMES, ReferenceFactsRecord

    record = _snapshot().records[0]
    return ReferenceFactsRecord(
        symbol="SPY", exchange="NYQ", **{name: getattr(record, name) for name in REFERENCE_NAMES}
    )


def _collected(reference, *, at=NOW, version="fresh-1"):
    from types import SimpleNamespace

    from test_yahoo_research import FakeTicker, one_member_universe

    from etf_advisor.data.reference_facts import LocalReferenceFacts
    from etf_advisor.data.yahoo_research import YahooResearchAdapter

    ticker = SimpleNamespace(
        info={
            **FakeTicker.info,
            "exchange": "NYQ",
            "currency": "USD",
            "regularMarketTime": int(NOW.timestamp()),
        },
        funds_data=FakeTicker.funds_data,
    )
    return YahooResearchAdapter(
        clock=lambda: at,
        ticker_factory=lambda symbol: ticker,
        advisory_contract="us-eu-v1",
        reference_facts=LocalReferenceFacts({("SPY", "NYQ"): reference}),
    ).fetch_snapshot(one_member_universe(), snapshot_version=version)


def test_reference_fresh_collection_rebinds_only_publication_coordinates(tmp_path):
    from copy import deepcopy

    from etf_advisor.data.reference_facts import (
        REFERENCE_NAMES,
        ReferenceFactsFile,
        load_reference_facts,
    )
    from etf_advisor.research.snapshot_io import load_research_snapshot, persist_research_snapshot

    record = _reference_record()
    for name in REFERENCE_NAMES:
        field = getattr(record, name)
        field.snapshot_version = "T0"
        field.ingested_at = NOW - timedelta(days=1)
    before = deepcopy(record.model_dump(mode="json"))
    path = tmp_path / "references.json"
    path.write_text(
        ReferenceFactsFile(schema_version=1, records=[record]).model_dump_json(), encoding="utf-8"
    )
    original_bytes = path.read_bytes()
    provider = load_reference_facts(path, ["SPY"])
    record = provider.lookup("SPY", "NYQ")
    t1 = _collected(record)
    t2 = _collected(record, at=NOW + timedelta(hours=1), version="fresh-2")
    assert record.model_dump(mode="json") == before
    assert path.read_bytes() == original_bytes
    assert t1.content_digest() != t2.content_digest()
    for snapshot in (t1, t2):
        for name in REFERENCE_NAMES:
            field = getattr(snapshot.records[0], name)
            original = before[name]
            retained = field.model_dump(mode="json")
            for key in ("value", "missing_reason", "unit", "provider", "source_url", "observed_at"):
                assert retained[key] == original[key]
            assert field.snapshot_version == snapshot.snapshot_version
            assert field.ingested_at == snapshot.ingested_at
        assert (
            ETFResearchSnapshot.model_validate_json(snapshot.model_dump_json()).content_digest()
            == snapshot.content_digest()
        )
    payload = tmp_path / "canonical.json"
    persist_research_snapshot(t1, payload)
    path.write_text("broken later input", encoding="utf-8")
    assert load_research_snapshot(payload).model_dump(mode="json") == t1.model_dump(mode="json")
    tampered = t1.model_dump(mode="json")
    tampered["records"][0]["share_class_id"]["snapshot_version"] = "T0"
    with pytest.raises(ValueError):
        ETFResearchSnapshot.model_validate(tampered)


@pytest.mark.parametrize(
    "offset,healthy",
    [
        (timedelta(hours=-120), True),
        (timedelta(hours=-120, microseconds=-1), False),
        (timedelta(minutes=5), True),
        (timedelta(minutes=5, microseconds=1), False),
    ],
)
def test_reference_source_freshness_not_refreshed_by_collection(offset, healthy):
    from etf_advisor.data.research_quality import assess_research_fields

    reference = _reference_record()
    reference.share_class_id.observed_at = NOW + offset
    snapshot = _collected(reference)
    result = assess_research_fields(
        snapshot,
        checked_at=NOW,
        max_age=timedelta(hours=120),
        future_tolerance=timedelta(minutes=5),
    )
    assert result.healthy is healthy
    assert snapshot.records[0].share_class_id.observed_at == NOW + offset


@pytest.mark.parametrize(
    "mutation", ["ingestion", "version", "identifier", "unknown", "association"]
)
def test_reference_input_rejected_before_rebinding(tmp_path, mutation):
    import json

    from etf_advisor.data.reference_facts import load_reference_facts

    payload = {"schema_version": 1, "records": [_reference_record().model_dump(mode="json")]}
    record = payload["records"][0]
    if mutation == "ingestion":
        record["share_class_id"]["ingested_at"] = "2026-10-19T10:00:00"
    elif mutation == "version":
        record["share_class_id"]["snapshot_version"] = ""
    elif mutation == "identifier":
        record["share_class_id"]["value"] = "IE00INVALID0"
    elif mutation == "unknown":
        record["extra"] = True
    else:
        record["symbol"] = "OTHER"
    path = tmp_path / "refs.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        load_reference_facts(path, ["SPY"])


def test_reference_duplicate_keys_nonfinite_and_listing_duplicates_rejected(tmp_path):
    import json

    from etf_advisor.data.reference_facts import load_reference_facts

    record = _reference_record().model_dump(mode="json")
    for text in [
        '{"schema_version":1,"schema_version":1,"records":[]}',
        '{"schema_version":NaN,"records":[]}',
        json.dumps({"schema_version": 1, "records": [record, record]}),
    ]:
        path = tmp_path / "refs.json"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError):
            load_reference_facts(path, ["SPY"])


@pytest.mark.parametrize(
    "payload",
    [
        b'<Cube><Cube time="2026-10-19"><Cube currency="USD" rate="1.1253"/></Cube></Cube>',
        b'<Cube><Cube time="2026-10-19"><Cube currency="USD" rate="1.1253"/>'
        b'<Cube currency="USD" rate="1.2"/></Cube></Cube>',
        b'<!DOCTYPE Cube [<!ENTITY rate "1.1253">]><Cube time="2026-10-19">'
        b'<Cube currency="USD" rate="&rate;"/></Cube>',
        b'<Cube time="2026-10-19"><Cube currency="USD" rate="1.12530"/></Cube>',
        b'<Cube><Cube time="2026-10-19"/><Cube time="2026-10-19"/></Cube>',
        b'<Cube time="2026-10-19"><Cube currency="EUR" rate="1.1253"/></Cube>',
        b"X" * 65_537,
    ],
    ids=[
        "valid",
        "duplicate-usd",
        "entity",
        "noncanonical",
        "duplicate-date",
        "missing-usd",
        "oversize",
    ],
)
def test_ecb_parser_bounded_and_strict(payload):
    from etf_advisor.data.ecb_fx import parse_ecb_daily

    if (
        payload
        == b'<Cube><Cube time="2026-10-19"><Cube currency="USD" rate="1.1253"/></Cube></Cube>'
    ):
        assert parse_ecb_daily(payload, NOW) == _fx()
    else:
        with pytest.raises(ValueError):
            parse_ecb_daily(payload, NOW)


def test_ecb_transport_fixed_one_attempt_bound_and_redirect_rejection(monkeypatch):
    from io import BytesIO
    from urllib.error import URLError

    from etf_advisor.data import ecb_fx
    from etf_advisor.domain.us_eu import FX_URL

    calls = []

    class Response(BytesIO):
        status = 200
        url = FX_URL

    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, timeout))
            return Response(b'<Cube time="2026-10-19"><Cube currency="USD" rate="1.1253"/></Cube>')

    def opener(*handlers):
        assert len(handlers) == 1
        assert handlers[0].redirect_request(None, None, 302, "", None, "https://other.test") is None
        return Opener()

    monkeypatch.setattr(ecb_fx, "build_opener", opener)
    assert ecb_fx.EcbFxClient(lambda: NOW).fetch_eur_usd() == _fx()
    assert calls == [(FX_URL, 10)]

    def fail(*args, **kwargs):
        calls.append("failed")
        raise URLError("private detail")

    monkeypatch.setattr(Opener, "open", fail)
    with pytest.raises(ValueError, match="ECB reference rate unavailable"):
        ecb_fx.EcbFxClient(lambda: NOW).fetch_eur_usd()
    assert calls.count("failed") == 1


def test_hybrid_retrieval_fetches_fx_once_only_when_needed():
    from etf_advisor.rag.evidence import HybridCandidateEvidenceRetriever

    class Search:
        def search(self, query, *, limit):
            return [
                GraphEnrichedSource(
                    document_id=d.document_id, content=d.content, metadata=d.metadata
                )
                for d in snapshot.to_source_documents()
            ]

    class Provider:
        calls = 0

        def fetch_eur_usd(self):
            self.calls += 1
            return _fx()

    snapshot = _snapshot()
    provider = Provider()
    adapter = HybridCandidateEvidenceRetriever(
        Search(), clock=lambda: NOW, max_age=timedelta(hours=120), fx_provider=provider
    )
    assert adapter.retrieve(_profile(), limit=3).fx_reference == _fx()
    assert provider.calls == 1
    snapshot.records[1].trading_currency.value = "USD"
    snapshot.records[1].price_unit.value = "USD"
    evidence = adapter.retrieve(_profile(), limit=3)
    assert evidence.fx_reference.missing_reason == "not_requested"
    assert provider.calls == 1


def test_managed_graph_restore_and_revision_keep_bound_fx_and_receipts():
    from copy import deepcopy

    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from test_workflow import review_decision as make_decision

    from etf_advisor.dashboard import review_payload
    from etf_advisor.graph.revision import validate_revision_state
    from etf_advisor.graph.workflow import build_graph

    def review_decision(*args):
        return {**make_decision(*args), "submitted_at": NOW.isoformat()}

    class Retriever:
        calls = 0

        def retrieve(self, profile, *, limit):
            self.calls += 1
            evidence = _evidence(profile=profile, fx=_fx())
            evidence.requested_limit = limit
            return evidence

    adapter = Retriever()
    saver = InMemorySaver()
    config = {"configurable": {"thread_id": "us-eu-synthetic"}, "recursion_limit": 100}
    graph = build_graph(checkpointer=saver, candidate_retriever=adapter, clock=lambda: NOW)
    state = graph.invoke({"profile": _profile().model_dump(mode="json")}, config)
    assert state["status"] == "awaiting_human_review"
    expected = deepcopy(state["candidate_evidence"])
    ledger = validate_revision_state(state)
    receipt = ledger.revisions[0].receipts[0]
    assert receipt.status == "succeeded"
    assert ledger.artifacts[receipt.output_id].value["fx_reference"] == _fx().model_dump(
        mode="json"
    )
    restored = build_graph(checkpointer=saver, clock=lambda: NOW + timedelta(days=100))
    retained = dict(restored.get_state(config).values)
    retained["__interrupt__"] = restored.get_state(config).interrupts
    assert retained["candidate_evidence"] == expected
    assert (
        review_payload(retained)["candidate_evidence"]["fx_reference"]["rate_decimal"] == "1.1253"
    )
    assert adapter.calls == 1
    # A downstream construction-only revision reuses evidence and its original check time.
    state = graph.invoke(
        Command(
            resume=review_decision(
                state, "edit", [{"kind": "construction_policy", "patch": {"max_positions": 4}}]
            )
        ),
        config,
    )
    assert state["status"] == "awaiting_human_review"
    assert state["candidate_evidence"] == expected, state.get("errors")
    assert adapter.calls == 1
    # A base change explicitly supplies cash and obtains a new retrieval receipt.
    state = graph.invoke(
        Command(
            resume=review_decision(
                state,
                "edit",
                [
                    {
                        "kind": "profile",
                        "patch": {
                            "base_currency": "EUR",
                            "initial_investment_minor": 1,
                            "recurring_monthly_minor": 0,
                        },
                    }
                ],
            )
        ),
        config,
    )
    assert state["status"] == "awaiting_human_review"
    assert state["portfolio_construction"]["draft"]["base_currency"] == "EUR"
    assert adapter.calls == 2
    ledger = validate_revision_state(state)
    assert ledger.revisions[-1].receipts[0].input_digest != receipt.input_digest
    state = graph.invoke(Command(resume=review_decision(state)), config)
    assert state["status"] == "approved"
    assert adapter.calls == 2


def test_base_currency_revision_requires_both_amounts_and_contract_is_frozen():
    from etf_advisor.domain.construction import PortfolioConstructionPolicy
    from etf_advisor.domain.revision import ReviewDecision, RevisionInputs, plan_revision
    from etf_advisor.domain.screening import CandidateScreeningPolicy

    inputs = RevisionInputs(
        profile=_profile(),
        screening_policy=CandidateScreeningPolicy(),
        construction_policy=PortfolioConstructionPolicy(),
        candidate_limit=3,
        with_evidence=True,
        with_explanation=False,
        explanation_instruction="",
    ).model_dump(mode="json")
    for patch in [{"base_currency": "EUR"}, {"advisory_contract": None}]:
        decision = ReviewDecision(
            decision_id="test",
            revision_id="test",
            action="edit",
            disposition="revise",
            note="Explicit",
            submitted_at=NOW,
            feedback=[{"kind": "profile", "patch": patch}],
        )
        with pytest.raises(ValueError):
            plan_revision(decision, inputs)


def test_new_usd_vectors_match_legacy_exactly_and_legacy_dumps_omit_extensions():
    snapshot = _snapshot()
    snapshot.records[1].trading_currency.value = "USD"
    snapshot.records[1].price_unit.value = "USD"
    snapshot.records[1].listing_exchange.value = "NYQ"
    snapshot.records[1].market.value = "us_market"
    new = construct_model_portfolio(
        _inputs(snapshot, profile=_profile(initial=100_001, recurring=501))
    )
    raw = snapshot.model_dump(mode="json")
    raw.pop("advisory_contract")
    names = [
        "listing_exchange",
        "trading_currency",
        "price_unit",
        "share_class_id",
        "economic_group_id",
        "domicile",
        "fund_base_currency",
        "share_class_currency",
    ]
    for record in raw["records"]:
        record.pop("advisory_contract")
        for name in names:
            record.pop(name)
    legacy_snapshot = ETFResearchSnapshot.model_validate(raw)
    profile = InvestorProfile(
        horizon_years=12,
        risk_tolerance="moderate",
        objective="balanced",
        max_drawdown_pct=25,
        initial_investment_usd=1000.01,
        recurring_monthly_usd=5.01,
    )
    evidence = _evidence(legacy_snapshot, profile)
    old = construct_model_portfolio(
        PortfolioConstructionInput(
            profile=profile,
            policy_calculation=calculate_policy(profile),
            candidate_evidence=evidence,
            candidate_screening=screen_candidate_evidence(evidence),
        )
    )
    assert old.status == new.status == "ready"
    for legacy, tagged in zip(old.draft.positions, new.draft.positions, strict=True):
        assert (legacy.weight_bps, legacy.initial_usd_cents, legacy.recurring_usd_cents) == (
            tagged.weight_bps,
            tagged.initial_base_minor,
            tagged.recurring_base_minor,
        )
    for model in [profile, calculate_policy(profile), evidence, old]:
        assert "advisory_contract" not in model.model_dump(mode="json")


def _explanation_pair():
    inputs = _inputs(fx=_fx())
    result = construct_model_portfolio(inputs)
    request = build_explanation_request(
        profile=inputs.profile.model_dump(mode="json"),
        draft_policy=inputs.policy_calculation.model_dump(mode="json"),
        candidate_evidence=inputs.candidate_evidence.model_dump(mode="json"),
        candidate_screening=inputs.candidate_screening.model_dump(mode="json"),
        portfolio_construction=result.model_dump(mode="json"),
    )
    statement = GroundedStatement(
        text="The illustrative initial amount is USD 1000.01.",
        basis="policy_calculation",
        references=["policy.initial_investment"],
    )
    explanation = GeneratedExplanation(
        summary=statement,
        policy_points=[
            GroundedStatement(
                text="The illustrative policy requires human review.",
                basis="policy_calculation",
                references=["policy.notes"],
            )
        ],
        evidence_points=[
            GroundedStatement(
                text="SPY has source evidence.",
                basis="source_evidence",
                references=[inputs.candidate_evidence.candidates[0].document_id],
                subject_symbols=["SPY"],
            )
        ],
        tradeoffs=[
            GroundedStatement(
                text="The policy does not forecast outcomes.",
                basis="policy_calculation",
                references=["policy.notes"],
            )
        ],
    )
    return request, explanation


@pytest.mark.parametrize(
    "text,refs",
    [
        ("The initial amount is EUR 1000.01.", ["policy.initial_investment"]),
        ("The initial amount is $1000.01.", ["policy.initial_investment"]),
        ("The initial amount is 1000.01.", ["policy.initial_investment"]),
        ("The initial amount is USD 25.", ["profile.max_drawdown_pct"]),
        ("The initial amount is JPY 1000.01.", ["policy.initial_investment"]),
    ],
)
def test_new_monetary_grounding_rejects_wrong_labels_and_unrelated_numbers(text, refs):
    request, explanation = _explanation_pair()
    explanation.summary.text = text
    explanation.summary.references = refs
    with pytest.raises(ExplanationContractError):
        validate_and_bundle_explanation(
            request, ExplanationResult(provider="test", model="offline", explanation=explanation)
        )


def test_separate_us_eu_baseline_all_expectations_pass():
    from etf_advisor.evaluation.us_eu import run_us_eu_baseline

    report = run_us_eu_baseline()
    assert report["dataset_version"] == "us-eu-contract-v1"
    assert report["passed"]
    assert len(report["cases"]) == 10


def test_script_entry_creates_and_renders_us_eu_cash():
    """Execute the Streamlit script, where helper-definition order matters."""
    from pathlib import Path

    testing = pytest.importorskip("streamlit.testing.v1")
    script = Path(__file__).parents[1] / "src/etf_advisor/dashboard_app.py"
    app = testing.AppTest.from_file(str(script)).run()
    next(item for item in app.sidebar.selectbox if item.label == "Advisory scope").set_value(
        "US / EU (us-eu-v1)"
    )
    app.run()
    next(item for item in app.sidebar.selectbox if item.label == "Base currency").set_value("EUR")
    next(
        item for item in app.sidebar.text_input if item.label == "Initial amount (base currency)"
    ).set_value("0.01")
    next(
        item
        for item in app.sidebar.text_input
        if item.label == "Recurring monthly amount (base currency)"
    ).set_value("0.00")
    next(item for item in app.sidebar.button if item.label == "Create review draft").click()
    app.run(timeout=10)
    assert not app.exception
    assert not app.error
    run = app.session_state["dashboard_run"]
    assert run.state["status"] == "awaiting_human_review"
    assert run.state["profile"]["initial_investment_minor"] == 1
    assert run.state["profile"]["recurring_monthly_minor"] == 0
    assert run.state["profile"]["base_currency"] == "EUR"
    cash = next(table.value for table in app.dataframe if "Cash flow" in table.value.columns)
    assert list(cash["Total"]) == ["EUR 0.01", "EUR 0.00"]


def test_script_entry_renders_and_submits_us_eu_profile_revision():
    from pathlib import Path

    from etf_advisor.dashboard import DashboardOptions, start_dashboard_run

    testing = pytest.importorskip("streamlit.testing.v1")
    run = start_dashboard_run(_profile().model_dump(mode="json"), DashboardOptions())
    script = Path(__file__).parents[1] / "src/etf_advisor/dashboard_app.py"
    app = testing.AppTest.from_file(str(script))
    app.session_state["dashboard_run"] = run
    app.run(timeout=10)
    assert not app.exception
    next(item for item in app.radio if item.label == "Decision").set_value("Edit")
    app.run(timeout=10)
    next(item for item in app.multiselect if item.label == "Typed feedback").set_value(["profile"])
    app.run(timeout=10)
    next(item for item in app.selectbox if item.label == "Revised base currency").set_value("EUR")
    next(
        item for item in app.text_input if item.label == "Revised initial amount (base currency)"
    ).set_value("0.01")
    next(
        item for item in app.text_input if item.label == "Revised monthly amount (base currency)"
    ).set_value("0.00")
    next(item for item in app.text_area if item.label == "Reviewer note").set_value(
        "Explicit EUR cash revision."
    )
    next(item for item in app.button if item.label == "Submit decision").click()
    app.run(timeout=10)
    assert not app.exception
    assert not app.error
    run = app.session_state["dashboard_run"]
    assert run.state["status"] == "awaiting_human_review"
    assert run.state["profile"]["base_currency"] == "EUR"
    assert run.state["profile"]["initial_investment_minor"] == 1
    assert run.state["profile"]["recurring_monthly_minor"] == 0
    assert len(run.state["revision_ledger"]["revisions"]) == 2


def _empty_contract_sources(scenario):
    if scenario == "zero_results":
        return []
    snapshot = _snapshot([_record("SPY", "NYQ", "USD", "Large Blend", "US78462F1030")])
    if scenario == "all_stale":
        for field in snapshot.records[0].research_fields().values():
            field.observed_at = NOW - timedelta(hours=121)
    document = snapshot.to_source_documents()[0]
    metadata = dict(document.metadata)
    if scenario == "all_invalid":
        metadata["observed_at"] = "invalid-source-timestamp"
    return [
        GraphEnrichedSource(
            document_id=document.document_id, content=document.content, metadata=metadata
        )
    ]


@pytest.mark.parametrize("scenario", ["zero_results", "all_invalid", "all_stale"])
def test_us_eu_empty_candidate_outcomes_remain_blocked_and_roundtrip(scenario):
    from etf_advisor.rag.evidence import CandidateEvidenceBundle

    bundle = select_candidate_evidence(
        _profile(),
        _empty_contract_sources(scenario),
        query="synthetic-empty",
        checked_at=NOW,
        max_age=timedelta(hours=120),
        limit=3,
    )
    assert bundle.status == "blocked"
    assert bundle.candidates == []
    assert bundle.schema_version == 2
    assert bundle.advisory_contract == "us-eu-v1"
    assert bundle.errors
    assert bundle.fx_reference.missing_reason == "not_requested"
    assert CandidateEvidenceBundle.model_validate_json(bundle.model_dump_json()) == bundle
    assert CandidateEvidenceBundle.model_validate(bundle.model_dump(mode="json")) == bundle
    for update in [{"schema_version": 1}, {"advisory_contract": None}]:
        with pytest.raises(ValueError):
            CandidateEvidenceBundle.model_validate({**bundle.model_dump(mode="json"), **update})
    for key in ["schema_version", "advisory_contract"]:
        removed = bundle.model_dump(mode="json")
        removed.pop(key)
        with pytest.raises(ValueError):
            CandidateEvidenceBundle.model_validate(removed)


@pytest.mark.parametrize("scenario", ["zero_results", "all_invalid", "all_stale"])
def test_us_eu_empty_candidates_follow_graph_guardrail_and_restore_without_calls(scenario):
    from langgraph.checkpoint.memory import InMemorySaver

    from etf_advisor.graph.revision import validate_revision_state
    from etf_advisor.graph.workflow import build_graph
    from etf_advisor.rag.evidence import HybridCandidateEvidenceRetriever

    class Search:
        calls = 0

        def search(self, query, *, limit):
            self.calls += 1
            return _empty_contract_sources(scenario)

    class ExternalCalls:
        fx_calls = 0
        explanation_calls = 0

        def fetch_eur_usd(self):
            self.fx_calls += 1
            raise AssertionError("No FX request is needed for empty or USD-only results.")

        def generate(self, request):
            self.explanation_calls += 1
            raise AssertionError("Blocked evidence must not reach explanation.")

    search = Search()
    external = ExternalCalls()
    retriever = HybridCandidateEvidenceRetriever(
        search, clock=lambda: NOW, max_age=timedelta(hours=120), fx_provider=external
    )
    saver = InMemorySaver()
    config = {"configurable": {"thread_id": "empty-" + scenario}}
    graph = build_graph(
        checkpointer=saver,
        candidate_retriever=retriever,
        explanation_generator=external,
        clock=lambda: NOW,
    )
    state = graph.invoke({"profile": _profile().model_dump(mode="json")}, config)
    assert state["status"] == "evidence_blocked"
    assert state["candidate_evidence"]["status"] == "blocked"
    assert state["candidate_evidence"]["schema_version"] == 2
    assert state["candidate_evidence"]["candidates"] == []
    assert state["evidence_errors"]
    assert {error["type"] for error in state["evidence_errors"]} == {"evidence_guardrail"}
    assert not state.get("candidate_screening")
    assert not state.get("portfolio_construction")
    assert not state.get("draft_explanation")
    assert not state.get("__interrupt__")

    def no_clock():
        raise AssertionError("Restoration must not consult the current clock.")

    restored = build_graph(checkpointer=saver, clock=no_clock)
    retained = dict(restored.get_state(config).values)
    assert retained["candidate_evidence"] == state["candidate_evidence"]
    assert retained["status"] == "evidence_blocked"
    assert validate_revision_state(retained).revisions[-1].receipts[0].status == "failed"
    assert search.calls == 1
    assert external.fx_calls == external.explanation_calls == 0


def test_legacy_empty_evidence_preserves_exact_wire_dump():
    import json

    from etf_advisor.rag.evidence import CandidateEvidenceBundle

    profile = InvestorProfile(
        horizon_years=12,
        risk_tolerance="moderate",
        objective="balanced",
        max_drawdown_pct=25,
        initial_investment_usd=1000,
    )
    bundle = select_candidate_evidence(
        profile, [], query="synthetic-empty", checked_at=NOW, max_age=timedelta(hours=120), limit=3
    )
    expected = {
        "query": "synthetic-empty",
        "objective": "balanced",
        "risk_tolerance": "moderate",
        "excluded_sectors": [],
        "requested_limit": 3,
        "checked_at": "2026-10-19T10:00:00Z",
        "status": "blocked",
        "candidates": [],
        "health": {
            "checked_at": "2026-10-19T10:00:00Z",
            "max_age_hours": 120.0,
            "future_tolerance_minutes": 5.0,
            "healthy": False,
            "observations": [],
        },
        "errors": ["No source evidence matched the research query."],
        "warnings": [],
        "snapshot_version": None,
        "snapshot_digest": None,
    }
    assert bundle.model_dump(mode="json") == expected
    assert bundle.model_dump_json() == json.dumps(expected, separators=(",", ":"))
    assert (
        CandidateEvidenceBundle.model_validate_json(bundle.model_dump_json()).model_dump(
            mode="json"
        )
        == expected
    )
    with pytest.raises(ValueError):
        CandidateEvidenceBundle.model_validate({**expected, "schema_version": 2})


def test_nonempty_candidate_encoding_remains_authoritative_after_empty_fix():
    from etf_advisor.rag.evidence import CandidateEvidenceBundle

    payload = _evidence(fx=_fx()).model_dump(mode="json")
    assert payload["candidates"]
    with pytest.raises(ValueError, match="Evidence schema differs from its candidates"):
        CandidateEvidenceBundle.model_validate({**payload, "schema_version": 1})
    without_schema = dict(payload)
    without_schema.pop("schema_version")
    with pytest.raises(ValueError, match="explicit bundle marker"):
        CandidateEvidenceBundle.model_validate(without_schema)
    without_semantic = dict(payload)
    without_semantic.pop("advisory_contract")
    with pytest.raises(ValueError):
        CandidateEvidenceBundle.model_validate(without_semantic)
