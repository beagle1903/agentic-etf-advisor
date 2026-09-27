import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace

import pytest

from etf_advisor.data.research_quality import assess_research_fields, field_max_age
from etf_advisor.data.vanguard import (
    BND_URL,
    MAX_BYTES,
    PROVIDER,
    IssuerSourceError,
    VanguardHoldingsClient,
    parse_holdings,
)
from etf_advisor.data.yahoo import MarketDataError
from etf_advisor.data.yahoo_research import YahooResearchAdapter
from etf_advisor.encoding import decimal_value
from etf_advisor.research.models import ETFResearchSnapshot
from etf_advisor.research.universe import ResearchUniverse, UniverseMember

DATE = datetime(2026, 8, 31, tzinfo=UTC)
NOW = datetime(2026, 9, 27, tzinfo=UTC)


def row(market="100", weight="0.5", name="Treasury"):
    return dict(
        holdingName=name, ticker="T", marketValue=market, percentOfFunds=weight, faceAmount="100"
    )


def payload(rows=None, reserves=None):
    return {
        "latestEffectiveDate": "2026-08-31",
        "2026-08-31": {
            "fixedIncome": rows if rows is not None else [row(str(1000 - i)) for i in range(10)],
            "shortTermReserves": reserves or [],
            "equity": "ignored",
        },
    }


def parse(value):
    return parse_holdings(json.dumps(value).encode())


def test_large_live_equivalent_exact_selection():
    percentages = [
        "1.20466",
        "0.47467",
        "0.41323",
        "0.41271",
        "0.40781",
        "0.4071",
        "0.40688",
        "0.39916",
        "0.39539",
        "0.3842",
    ]
    rows = [row(str(2000000000 - i * 10000000), weight) for i, weight in enumerate(percentages[1:])]
    reserves = [row("3000000000", percentages[0], "MKTLIQ")]
    rows += [row("19970.79", "") for _ in range(1186)]
    rows += [row("-1", "-0.00001") for _ in range(26)]
    rows += [row("1", "0.00001") for _ in range(16300 - 10 - 1186 - 26 - 4)]
    rows += [
        dict(holdingName="Treasury", ticker="T", marketValue="", percentOfFunds="", faceAmount="")
        for _ in range(4)
    ]
    result = parse(payload(rows, reserves))
    assert (
        result.row_count,
        result.placeholders,
        result.blank_percentages,
        result.negative_percentages,
    ) == (16300, 4, 1190, 26)
    assert len(result.holdings) == 10
    assert result.holdings[0].name == "MKTLIQ"
    assert sum(
        (Fraction(decimal_value(item.source_weight_pct_decimal)) for item in result.holdings),
        Fraction(0),
    ) == Fraction(Decimal("4.90581"))
    assert result.concentration == 4.905810000000001
    assert len([item for item in result.holdings if item.name == "Treasury"]) == 9


@pytest.mark.parametrize(
    "change",
    [
        {"marketValue": ""},
        {"marketValue": None},
        {"marketValue": "NaN"},
        {"marketValue": "1" * 101},
        {"marketValue": "1e999"},
        {"percentOfFunds": ""},
        {"percentOfFunds": "-1"},
        {"percentOfFunds": "101"},
        {"percentOfFunds": None},
        {"holdingName": ""},
    ],
)
def test_invalid_selected_or_valued_row_fails(change):
    rows = [row(str(1000 - i)) for i in range(10)]
    rows[0].update(change)
    with pytest.raises(IssuerSourceError):
        parse(payload(rows))


@pytest.mark.parametrize("face", [None, " ", 0])
def test_only_exact_triple_blank_is_placeholder(face):
    rows = [row() for _ in range(10)] + [row("", "")]
    rows[-1]["faceAmount"] = face
    with pytest.raises(IssuerSourceError):
        parse(payload(rows))


def test_ties_cross_collection_repeats_and_negative_rows():
    rows = [row("100", "0.5", f"fixed-{i}") for i in range(9)]
    result = parse(payload([*rows, row("-1", "-1"), row("0", "")], [row("100", "0.5", "reserve")]))
    assert [item.name for item in result.holdings] == [f"fixed-{i}" for i in range(9)] + ["reserve"]
    with pytest.raises(IssuerSourceError):
        parse(payload(rows))
    with pytest.raises(IssuerSourceError):
        parse(payload([row(weight="11") for _ in range(10)]))


class Response:
    def __init__(self, body, status=200, encoding=None):
        self.body, self.status, self.encoding = body, status, encoding
        self.closed = False

    def getheader(self, name):
        return self.encoding if name == "Content-Encoding" else None

    def read(self, amount):
        chunk, self.body = self.body[:amount], self.body[amount:]
        return chunk

    def close(self):
        self.closed = True


class Transport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def open(self, **kwargs):
        assert kwargs["connect_timeout"] == 5 and kwargs["read_timeout"] == 10
        assert kwargs["deadline"] > 0
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.parametrize(
    "response",
    [
        Response(b"{}", 302),
        Response(b"{}", 404),
        Response(b"{}", encoding="gzip"),
        Response(b'{"a":1,"a":2}'),
        Response(b"private raw body"),
        Response(b"x" * (MAX_BYTES + 1)),
    ],
)
def test_http_terminal_failure_is_sanitized_and_closed(response):
    transport = Transport([response])
    with pytest.raises(IssuerSourceError) as error:
        VanguardHoldingsClient(transport=transport).fetch()
    assert "private" not in str(error.value)
    assert transport.calls == 1 and response.closed


def test_http_retries_and_elapsed_are_bounded():
    body = json.dumps(payload()).encode()
    transport = Transport([OSError("secret"), Response(b"", 503), Response(body)])
    assert VanguardHoldingsClient(transport=transport).fetch().row_count == 10
    assert transport.calls == 3
    with pytest.raises(IssuerSourceError, match="issuer_unavailable"):
        VanguardHoldingsClient(transport=Transport([OSError()] * 3)).fetch()
    times = iter([0, 91])
    with pytest.raises(IssuerSourceError, match="issuer_elapsed_limit"):
        VanguardHoldingsClient(transport=Transport([]), monotonic=lambda: next(times)).fetch()


class Issuer:
    def __init__(self, fail=False):
        self.calls, self.fail = 0, fail

    def fetch(self):
        self.calls += 1
        if self.fail:
            raise IssuerSourceError("issuer_shape")
        return parse(payload())


def snapshot(symbol="BND", holdings=None, fail=False):
    issuer = Issuer(fail)
    info = dict(
        longName="ETF",
        quoteType="ETF",
        market="us_market",
        category="Intermediate-Term Bond",
        fundFamily="Vanguard",
        netExpenseRatio=0.03,
        averageVolume=1000000,
        regularMarketTime=NOW.timestamp(),
    )
    ticker = SimpleNamespace(
        info=info,
        funds_data=SimpleNamespace(fund_overview={}, top_holdings=holdings, sector_weightings={}),
    )
    adapter = YahooResearchAdapter(
        clock=lambda: NOW, ticker_factory=lambda _: ticker, issuer_client=issuer
    )
    universe = ResearchUniverse(
        universe_id="test",
        universe_version="1",
        members=[UniverseMember(symbol=symbol, role="test")],
    )
    return adapter.fetch_snapshot(universe, snapshot_version="issuer-test"), issuer


def test_atomic_fallback_calls_and_schema2_roundtrip():
    value, issuer = snapshot()
    assert issuer.calls == 1
    record = value.records[0]
    assert record.top_holdings.provider == record.top_10_concentration_pct.provider == PROVIDER
    assert record.top_holdings.source_url == BND_URL
    assert (
        ETFResearchSnapshot.model_validate_json(value.model_dump_json()).content_digest()
        == value.content_digest()
    )
    assert snapshot("SPY")[1].calls == 0
    assert (
        snapshot(holdings=[dict(Name="Reported", Symbol="T", holdingPercent="0.01")])[1].calls == 0
    )
    with pytest.raises(MarketDataError, match="issuer_source_error"):
        snapshot(fail=True)


@pytest.mark.parametrize(
    "delta,healthy",
    [
        (timedelta(hours=1080), True),
        (timedelta(hours=1080, microseconds=1), False),
        (timedelta(microseconds=-1), False),
    ],
)
def test_publication_exact_issuer_age_and_future(delta, healthy):
    value, _ = snapshot()
    # Make all unrelated fields current so only the issuer field boundary is exercised.
    check = DATE + delta
    for _name, field in value.records[0].research_fields().items():
        if field.provider != PROVIDER:
            field.observed_at = check
    report = assess_research_fields(
        value, checked_at=check, max_age=timedelta(hours=120), future_tolerance=timedelta(minutes=5)
    )
    assert report.healthy is healthy


@pytest.mark.parametrize(
    "symbol,field,provider,url",
    [
        ("SPY", "top_holdings", PROVIDER, BND_URL),
        ("BND", "category", PROVIDER, BND_URL),
        ("BND", "top_holdings", "yahoo_finance", BND_URL),
        ("BND", "top_holdings", PROVIDER, BND_URL + "?x=1"),
    ],
)
def test_freshness_allowlist_exact(symbol, field, provider, url):
    assert field_max_age(
        symbol=symbol,
        field_name=field,
        provider=provider,
        source_url=url,
        observed_at=DATE,
        default=timedelta(hours=120),
    ) == timedelta(hours=120)


def test_row_and_shape_bounds():
    with pytest.raises(IssuerSourceError, match="issuer_row_limit"):
        parse(payload([row()] * 25001))
    for bad in (
        {},
        {"latestEffectiveDate": "2026-08-31", "2026-08-30": {}},
        {"latestEffectiveDate": "2026-02-30", "2026-02-30": {}},
        {
            "latestEffectiveDate": "2026-08-31",
            "2026-08-31": {"fixedIncome": {}, "shortTermReserves": []},
        },
    ):
        with pytest.raises(IssuerSourceError):
            parse(bad)


@pytest.mark.parametrize(
    "delta,valid", [(timedelta(hours=1080), True), (timedelta(hours=1080, microseconds=1), False)]
)
def test_screening_recomputes_issuer_field_window(delta, valid):
    from test_workflow import valid_profile

    from etf_advisor.domain.profile import InvestorProfile
    from etf_advisor.domain.screening import ScreeningFieldFreshnessError, screen_candidate_evidence
    from etf_advisor.rag.evidence import select_candidate_evidence
    from etf_advisor.rag.models import GraphEnrichedSource

    value, _ = snapshot()
    check = DATE + delta
    for field in value.records[0].research_fields().values():
        if field.provider != PROVIDER:
            field.observed_at = check
    profile = InvestorProfile.model_validate(valid_profile())
    documents = value.to_source_documents()
    evidence = select_candidate_evidence(
        profile,
        [
            GraphEnrichedSource(
                document_id=item.document_id, content=item.content, metadata=item.chroma_metadata()
            )
            for item in documents
        ],
        query="BND",
        checked_at=check,
        max_age=timedelta(hours=120),
    )
    if valid:
        bundle = screen_candidate_evidence(evidence)
        assert bundle.candidates[0].verdict == "pass"
        assert any("1080" in rule.message for rule in bundle.candidates[0].rules)
    else:
        with pytest.raises(ScreeningFieldFreshnessError):
            screen_candidate_evidence(evidence)


@pytest.mark.parametrize(
    "name,changed",
    [("top_holdings", "url"), ("top_10_concentration_pct", "date"), ("top_holdings", "provider")],
)
def test_pair_provenance_contradiction_fails_before_publication(name, changed):
    value, _ = snapshot()
    field = getattr(value.records[0], name)
    if changed == "url":
        field.source_url += "?wrong"
    elif changed == "date":
        field.observed_at += timedelta(days=1)
    else:
        field.provider = "yahoo_finance"
    with pytest.raises(ValueError, match="issuer_provenance_pair"):
        assess_research_fields(
            value,
            checked_at=NOW,
            max_age=timedelta(hours=120),
            future_tolerance=timedelta(minutes=5),
        )


@pytest.mark.parametrize(
    "delta,healthy", [(timedelta(hours=1080), True), (timedelta(hours=1080, microseconds=1), False)]
)
def test_cli_and_api_publication_share_age_boundary(delta, healthy):
    from test_snapshot_publication import FakeChromaStore, FakeSnapshotGraphStore

    from etf_advisor.cli import _assess_research_snapshot
    from etf_advisor.data.quality import MarketDataQualityError
    from etf_advisor.rag.snapshots import publish_research_snapshot

    value, _ = snapshot()
    value.universe_id, value.universe_version = "test-universe", "1.0.0"
    check = DATE + delta
    for field in value.records[0].research_fields().values():
        if field.provider != PROVIDER:
            field.observed_at = check
    assert _assess_research_snapshot(value, clock=lambda: check).healthy is healthy
    chroma, graph = FakeChromaStore(), FakeSnapshotGraphStore()
    if healthy:
        assert (
            publish_research_snapshot(value, chroma, graph, clock=lambda: check).chroma_count == 1
        )
    else:
        with pytest.raises(MarketDataQualityError):
            publish_research_snapshot(value, chroma, graph, clock=lambda: check)
        assert chroma.upsert_calls == graph.publish_calls == 0


def test_market_value_ranking_never_uses_decimal_context_rounding():
    lower = "1000000000000000000000000000000000000001"
    upper = "1000000000000000000000000000000000000002"
    rows = [row(lower, "0.1", "lower"), row(upper, "0.1", "upper")]
    rows += [row("1", "0.1") for _ in range(8)]
    assert [item.name for item in parse(payload(rows)).holdings][:2] == ["upper", "lower"]


def test_default_transport_fixes_host_path_and_socket_timeout(monkeypatch):
    from etf_advisor.data import vanguard

    calls = []
    response = Response(b"{}")

    class Connection:
        def __init__(self, host, timeout):
            calls.append((host, timeout))
            self.sock = self

        def connect(self):
            calls.append("connect")

        def settimeout(self, timeout):
            calls.append(("read_timeout", timeout))

        def request(self, method, path, headers):
            calls.append((method, path, headers))

        def getresponse(self):
            return response

        def close(self):
            calls.append("close")

    monkeypatch.setattr(vanguard.http.client, "HTTPSConnection", Connection)
    transport = vanguard.HTTPSHoldingsTransport()
    result = transport.open(connect_timeout=5, read_timeout=10, deadline=transport.monotonic() + 90)
    assert calls == [
        ("advisors.vanguard.com", 5),
        "connect",
        ("read_timeout", 10),
        (
            "GET",
            "/investments/products/api/funds/0928/holdings/latest",
            {"Accept": "application/json", "Accept-Encoding": "identity"},
        ),
    ]
    result.close()
    assert response.closed and calls[-1] == "close"


@pytest.mark.parametrize("count", [9, 11])
def test_self_consistent_issuer_count_rejected_by_publication_and_screening(count):
    from test_snapshot_publication import FakeChromaStore, FakeSnapshotGraphStore
    from test_workflow import valid_profile

    from etf_advisor.cli import _assess_research_snapshot
    from etf_advisor.domain.profile import InvestorProfile
    from etf_advisor.domain.screening import ScreeningContractError, screen_candidate_evidence
    from etf_advisor.encoding import upward
    from etf_advisor.rag.evidence import select_candidate_evidence
    from etf_advisor.rag.models import GraphEnrichedSource
    from etf_advisor.rag.snapshots import publish_research_snapshot

    value, _ = snapshot()
    record = value.records[0]
    holdings = record.top_holdings.value
    assert holdings is not None
    record.top_holdings.value = holdings[:count] if count < 10 else [*holdings, holdings[-1]]
    # Schema2 recomputes concentration from the first ten, including oversized lists.
    record.top_10_concentration_pct.value = upward(Fraction(min(count, 10), 2))
    value.universe_id, value.universe_version = "test-universe", "1.0.0"
    documents = value.to_source_documents()
    profile = InvestorProfile.model_validate(valid_profile())
    evidence = select_candidate_evidence(
        profile,
        [
            GraphEnrichedSource(
                document_id=item.document_id, content=item.content, metadata=item.chroma_metadata()
            )
            for item in documents
        ],
        query="BND",
        checked_at=NOW,
        max_age=timedelta(hours=120),
    )
    with pytest.raises(ValueError, match="issuer_holdings_count"):
        _assess_research_snapshot(value, clock=lambda: NOW)
    chroma, graph = FakeChromaStore(), FakeSnapshotGraphStore()
    with pytest.raises(ValueError, match="issuer_holdings_count"):
        publish_research_snapshot(value, chroma, graph, clock=lambda: NOW)
    assert chroma.upsert_calls == graph.publish_calls == 0
    with pytest.raises(ScreeningContractError, match="issuer_provenance_pair"):
        screen_candidate_evidence(evidence)


@pytest.mark.parametrize("stage", ["headers", "body"])
def test_watchdog_interrupts_slow_trickle_inside_transport(stage, monkeypatch):
    import socket

    from etf_advisor.data import vanguard

    events = []

    class FakeTimer:
        def __init__(self, delay, callback):
            assert delay == 90
            self.callback = callback

        def start(self):
            events.append("armed")

        def cancel(self):
            events.append("cancelled")

    timers = []

    def timer_factory(delay, callback):
        timer = FakeTimer(delay, callback)
        timers.append(timer)
        return timer

    class SlowResponse(Response):
        def read(self, amount):
            # Even continuous bytes cannot reset this timer, unlike socket idle timeouts.
            timers[0].callback()
            assert "shutdown" in events
            raise OSError("private slow body")

    response = SlowResponse(b"{}")

    class Connection:
        def __init__(self, *args, **kwargs):
            self.sock = self

        def connect(self):
            pass

        def settimeout(self, seconds):
            assert seconds == 10

        def request(self, *args, **kwargs):
            pass

        def shutdown(self, how):
            assert how == socket.SHUT_RDWR
            events.append("shutdown")

        def getresponse(self):
            if stage == "headers":
                timers[0].callback()
                assert "shutdown" in events
                raise OSError("private slow headers")
            # Mirror http.client handing ownership to a response/file object.
            self.sock = None
            return response

        def close(self):
            events.append("closed")

    monkeypatch.setattr(vanguard.http.client, "HTTPSConnection", Connection)
    transport = vanguard.HTTPSHoldingsTransport(monotonic=lambda: 0, timer_factory=timer_factory)
    client = VanguardHoldingsClient(transport=transport, monotonic=lambda: 0)
    with pytest.raises(IssuerSourceError, match=r"^issuer_elapsed_limit$"):
        client.fetch()
    assert events.count("armed") == 1
    assert "cancelled" in events and "closed" in events


@pytest.mark.parametrize("stage", ["headers", "body"])
def test_real_socket_shutdown_interrupts_continuous_trickle(stage, monkeypatch):
    import socket
    from threading import Event, Thread, Timer

    from etf_advisor.data import vanguard

    reader, writer = socket.socketpair()
    stopped = Event()
    interrupted = Event()
    stream = reader.makefile("rb")
    response = Response(b"{}")

    def trickle():
        try:
            while not stopped.wait(0.005):
                writer.sendall(b"x")
        except OSError:
            pass

    worker = Thread(target=trickle, daemon=True)

    def timer_factory(seconds, callback):
        assert seconds == 90

        def expire():
            interrupted.set()
            callback()

        timer = Timer(0.05, expire)
        timer.daemon = True
        return timer

    class Connection:
        def __init__(self, *args, **kwargs):
            self.sock = reader

        def connect(self):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            if stage == "headers":
                stream.read(65536)
            else:
                response.read = stream.read
                self.sock = None
            return response

        def close(self):
            reader.close()

    monkeypatch.setattr(vanguard.http.client, "HTTPSConnection", Connection)
    transport = vanguard.HTTPSHoldingsTransport(monotonic=lambda: 0, timer_factory=timer_factory)
    worker.start()
    try:
        with pytest.raises(IssuerSourceError, match=r"^issuer_elapsed_limit$"):
            VanguardHoldingsClient(transport=transport, monotonic=lambda: 0).fetch()
        assert interrupted.is_set()
    finally:
        stopped.set()
        writer.close()
        stream.close()
        reader.close()
        worker.join(timeout=1)
    assert not worker.is_alive()
