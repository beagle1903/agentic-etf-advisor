"""Issue70 numeric and restored-consumer contracts without external services."""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest
from test_research_snapshot import research_snapshot
from test_workflow import _current_evidence_retriever, valid_profile

from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import CandidateScreeningBundle, screen_candidate_evidence
from etf_advisor.encoding import (
    ResearchIntegrityError,
    binary_token,
    binary_value,
    decimal_token,
    decode_exposures,
    document_fingerprint,
    strict_json,
    upward,
    validate_document,
)
from etf_advisor.rag.evidence import (
    CandidateEvidenceBundle,
    EvidenceRetrievalError,
    HybridCandidateEvidenceRetriever,
    select_candidate_evidence,
)
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource
from etf_advisor.rag.snapshots import SnapshotManifest
from etf_advisor.research.models import ETFResearchSnapshot


def lossless_snapshot(
    version: str = "lossless-a", *, symbols: tuple[str, ...] = ("QQQ", "SPY", "BND")
) -> ETFResearchSnapshot:
    template = research_snapshot()
    records = []
    for symbol in symbols:
        record = template.records[0].model_copy(deep=True)
        record.symbol = symbol
        record.category.value = "Intermediate Core Bond" if symbol == "BND" else "Large Blend"
        for name, field in record.research_fields().items():
            field.snapshot_version = version
            field.source_url = f"https://example.com/{symbol}"
            if name in {"expense_ratio_pct", "top_10_concentration_pct"}:
                field.unit = "percent"
            elif name == "average_daily_volume":
                field.unit = "shares_per_day"
            elif name in {"top_holdings", "sector_exposures", "geography_exposures"}:
                field.unit = "percent_of_fund"
        for exposure in record.top_holdings.value or []:
            exposure.weight_pct = upward(Decimal("46.2723799"))
            exposure.source_weight_pct_decimal = decimal_token(Decimal("46.2723799"))
        for exposure in record.sector_exposures.value or []:
            exposure.source_weight_pct_decimal = decimal_token(Decimal(str(exposure.weight_pct)))
        record.top_10_concentration_pct.value = upward(Decimal("46.2723799"))
        records.append(record)
    return template.model_copy(
        update={"schema_version": 2, "snapshot_version": version, "records": records}
    )


def lossless_evidence() -> CandidateEvidenceBundle:
    snapshot = lossless_snapshot()
    documents = snapshot.to_source_documents()
    return select_candidate_evidence(
        InvestorProfile.model_validate(valid_profile()),
        [
            GraphEnrichedSource(
                document_id=document.document_id,
                content=document.content,
                metadata=document.chroma_metadata(),
            )
            for document in documents
        ],
        query="lossless contract",
        checked_at=snapshot.ingested_at,
        max_age=timedelta(hours=24),
    )


@pytest.mark.parametrize("token", ["46.272379900000004", "0.0", "-0.0", "5e-324", "1e+20"])
def test_binary_tokens_roundtrip_without_adjacent_substitution(token: str) -> None:
    assert binary_token(binary_value(token)) == token


@pytest.mark.parametrize("token", [True, 0.0, " 0.0", "0", "+0.0", "NaN", "inf", "1.00"])
def test_noncanonical_tokens_fail(token: Any) -> None:
    with pytest.raises(ResearchIntegrityError):
        binary_value(token)


@pytest.mark.parametrize("values", [("0.7", "99.3"), ("0", "0"), ("1e-100", "1")])
def test_exact_exposure_sum_and_upward_proofs(values: tuple[str, str]) -> None:
    rows = [
        {
            "name": str(index),
            "symbol": None,
            "weight_pct_token": binary_token(upward(Decimal(value))),
            "source_weight_pct_decimal": decimal_token(Decimal(value)),
        }
        for index, value in enumerate(values)
    ]
    assert len(decode_exposures(rows)) == 2


@pytest.mark.parametrize("values", [("60", "60"), ("100", "1e-100")])
def test_exact_total_overflow_fails(values: tuple[str, str]) -> None:
    rows = [
        {
            "name": str(index),
            "weight_pct_token": binary_token(upward(Decimal(value))),
            "source_weight_pct_decimal": decimal_token(Decimal(value)),
        }
        for index, value in enumerate(values)
    ]
    with pytest.raises(ResearchIntegrityError):
        decode_exposures(rows)


def test_snapshot_schema2_exact_roundtrip_and_schema1_golden_shape() -> None:
    snapshot = lossless_snapshot()
    payload = snapshot.model_dump(mode="json")
    assert payload["records"][0]["top_10_concentration_pct"]["value"] == "46.272379900000004"
    assert (
        ETFResearchSnapshot.model_validate_json(snapshot.model_dump_json()).model_dump(mode="json")
        == payload
    )
    old = research_snapshot()
    # Golden values were verified against the approved schema-1 base 148eba7.
    assert (
        old.content_digest() == "fd60a860136310c1a3ea126eab376625c8998ba77e33350c072d0d4903c318e4"
    )
    assert sha256(old.model_dump_json().encode()).hexdigest() == (
        "13e3cd6e3ff1d45ff7be5f329f2dad4377d1f35bf97eca3725c82cb58feee328"
    )
    assert "source_weight_pct_decimal" not in old.model_dump_json()
    assert (
        ETFResearchSnapshot.model_validate_json(old.model_dump_json()).content_digest()
        == old.content_digest()
    )


def test_schema1_checkpoint_artifact_json_retains_baseline_golden_digests() -> None:
    evidence = _current_evidence_retriever().retrieve(
        InvestorProfile.model_validate(valid_profile())
    )
    screened = screen_candidate_evidence(evidence)
    assert sha256(evidence.model_dump_json().encode()).hexdigest() == (
        "4f782c7bed20dcae038f03830ee87c65f1b9c6c7be8b4b3544763d066db288d0"
    )
    assert sha256(screened.model_dump_json().encode()).hexdigest() == (
        "7294144ed3aacf148bbf5a1cda7cfee78d63c4c599b04db5fc1db01dcb265621"
    )


@pytest.mark.parametrize("marker", [True, 2.0, "2", None, 3])
def test_snapshot_evidence_and_screening_reject_coercive_version(marker: Any) -> None:
    for model, payload in (
        (ETFResearchSnapshot, lossless_snapshot().model_dump(mode="json")),
        (CandidateEvidenceBundle, lossless_evidence().model_dump(mode="json")),
        (
            CandidateScreeningBundle,
            screen_candidate_evidence(lossless_evidence()).model_dump(mode="json"),
        ),
    ):
        payload["schema_version"] = marker
        with pytest.raises(ValueError):
            model.model_validate(payload)


def test_duplicate_json_keys_fail_before_dispatch() -> None:
    with pytest.raises(ResearchIntegrityError):
        strict_json('{"schema_version":1,"schema_version":2}')
    with pytest.raises(ResearchIntegrityError):
        ETFResearchSnapshot.model_validate_json('{"schema_version":1,"schema_version":2}')


def test_duplicate_encoding_keys_fail_at_consumer_json_entrypoints() -> None:
    from etf_advisor.dashboard import ReviewPayload
    from etf_advisor.domain.construction import PortfolioConstructionInput
    from etf_advisor.explanation import ExplanationRequest

    raw = '{"candidate_evidence":{"schema_version":1,"schema_version":2}}'
    for model in (ReviewPayload, PortfolioConstructionInput, ExplanationRequest):
        with pytest.raises(ResearchIntegrityError):
            model.model_validate_json(raw)


def test_document_adjacent_native_unit_and_content_mutations_fail() -> None:
    document = lossless_snapshot().to_source_documents()[0]
    metadata = document.chroma_metadata()
    assert validate_document(document.document_id, document.content, metadata) == 2
    for field, replacement in (
        ("top_10_concentration_pct", "46.2723799"),
        ("top_10_concentration_pct", 46.272379900000004),
    ):
        changed = {**metadata, field: replacement}
        changed["document_fingerprint"] = document_fingerprint(
            document.document_id, document.content, changed
        )
        with pytest.raises(ValueError):
            validate_document(document.document_id, document.content, changed)
    changed_content = document.content + " corrupted"
    changed = {
        **metadata,
        "document_fingerprint": document_fingerprint(
            document.document_id, changed_content, metadata
        ),
    }
    with pytest.raises(ValueError):
        validate_document(document.document_id, changed_content, changed)


def test_flattened_status_cannot_contradict_retained_numeric_provenance() -> None:
    document = lossless_snapshot().to_source_documents()[0]
    metadata = document.chroma_metadata()
    metadata["top_10_concentration_pct_status"] = "not_reported"
    metadata["document_fingerprint"] = document_fingerprint(
        document.document_id, document.content, metadata
    )
    with pytest.raises(ResearchIntegrityError):
        validate_document(document.document_id, document.content, metadata)


def test_schema2_evidence_and_screening_roundtrip_and_encoding_mixture_fail() -> None:
    evidence = lossless_evidence()
    assert evidence.status == "ready"
    screened = screen_candidate_evidence(evidence)
    assert screened.candidates[0].rules[5].observed_value == "46.272379900000004"
    assert CandidateScreeningBundle.model_validate(screened.model_dump(mode="json")) == screened
    payload = evidence.model_dump(mode="json")
    for marker in (None, 1):
        changed = deepcopy(payload)
        changed["schema_version"] = marker
        with pytest.raises(ValueError):
            CandidateEvidenceBundle.model_validate(changed)
    changed = deepcopy(payload)
    changed.pop("schema_version")
    with pytest.raises(ValueError):
        CandidateEvidenceBundle.model_validate(changed)


@pytest.mark.parametrize("token", ["0.0", "-0.0", "5e-324"])
def test_zero_signed_zero_and_small_exact_exposure_tokens(token: str) -> None:
    from fractions import Fraction

    exact = Decimal.from_float(float(token))
    rows = decode_exposures(
        [
            {
                "name": "small",
                "weight_pct_token": token,
                "source_weight_pct_decimal": decimal_token(exact),
            }
        ]
    )
    assert binary_token(rows[0]["weight_pct"]) == token
    assert Fraction(Decimal(rows[0]["source_weight_pct_decimal"])) == Fraction(exact)


@pytest.mark.parametrize("damage", ["missing", "wrong", "duplicate", "native"])
def test_exposure_decimal_proof_is_mandatory_and_exact(damage: str) -> None:
    row: dict[str, Any] = {
        "name": "holding",
        "weight_pct_token": "46.272379900000004",
        "source_weight_pct_decimal": "462723799e-7",
    }
    if damage == "missing":
        row.pop("source_weight_pct_decimal")
    elif damage == "wrong":
        row["source_weight_pct_decimal"] = "462723799e-8"
    elif damage == "duplicate":
        row["weight_pct"] = 46.272379900000004
    else:
        row["source_weight_pct_decimal"] = 46.2723799
    with pytest.raises(ResearchIntegrityError):
        decode_exposures([row])


@pytest.mark.parametrize("field,damage", [("unit", "ratio"), ("status", "missing")])
def test_schema2_field_unit_and_status_contradictions_fail(field: str, damage: str) -> None:
    payload = lossless_snapshot().model_dump(mode="json")
    payload["records"][0]["top_10_concentration_pct"][field] = damage
    with pytest.raises(ValueError):
        ETFResearchSnapshot.model_validate(payload)


@pytest.mark.parametrize("marker", [True, 2.0, "2", None, 0, 3])
def test_graph_manifest_and_document_versions_require_exact_int(marker: Any) -> None:
    context = {
        "schema_version": marker,
        "source_document_id": "research:a:QQQ",
        "symbol": "QQQ",
        "etf_name": "ETF",
    }
    with pytest.raises(ValueError):
        GraphContext.model_validate(context)
    with pytest.raises(ValueError):
        SnapshotManifest("a", "digest", 1, ("research:a:QQQ",), marker)
    document = lossless_snapshot().to_source_documents()[0]
    metadata = document.chroma_metadata()
    metadata["field_provenance_schema_version"] = marker
    with pytest.raises(ValueError):
        validate_document(document.document_id, document.content, metadata)


@pytest.mark.parametrize("reverse", [False, True])
def test_same_identity_mixed_schema_evidence_and_screening_fail_in_both_orders(
    reverse: bool,
) -> None:
    snapshot = lossless_snapshot()
    old = snapshot.model_copy(deep=True, update={"schema_version": 1})
    for record in old.records:
        for name in ("top_holdings", "sector_exposures", "geography_exposures"):
            for exposure in getattr(record, name).value or []:
                exposure.source_weight_pct_decimal = None
    old_document = old._to_source_document(old.records[0], digest=snapshot.content_digest())
    old_evidence = select_candidate_evidence(
        InvestorProfile.model_validate(valid_profile()),
        [
            GraphEnrichedSource(
                document_id=old_document.document_id,
                content=old_document.content,
                metadata=old_document.chroma_metadata(),
            )
        ],
        query="old evidence",
        checked_at=snapshot.ingested_at,
        max_age=timedelta(hours=24),
    )
    first = snapshot.to_source_documents()[0]
    sources = [
        GraphEnrichedSource(
            document_id=first.document_id, content=first.content, metadata=first.chroma_metadata()
        ),
        GraphEnrichedSource(
            document_id=old_document.document_id,
            content=old_document.content,
            metadata=old_document.chroma_metadata(),
        ),
    ]
    if reverse:
        sources.reverse()
    retriever = HybridCandidateEvidenceRetriever(
        SimpleNamespace(search=lambda *args, **kwargs: sources),
        clock=lambda: snapshot.ingested_at,
        max_age=timedelta(hours=24),
    )
    with pytest.raises(EvidenceRetrievalError) as mixed:
        retriever.retrieve(InvestorProfile.model_validate(valid_profile()))
    assert mixed.value.code == "schema_encoding"
    evidence = lossless_evidence().model_dump(mode="json")
    evidence["candidates"] = [
        evidence["candidates"][0],
        old_evidence.model_dump(mode="json")["candidates"][0],
    ]
    if reverse:
        evidence["candidates"].reverse()
    with pytest.raises(ValueError):
        CandidateEvidenceBundle.model_validate(evidence)
    screening = screen_candidate_evidence(lossless_evidence()).model_dump(mode="json")
    old_result = deepcopy(screening["candidates"][0])
    old_result["schema_version"] = 1
    screening["candidates"] = [screening["candidates"][0], old_result]
    if reverse:
        screening["candidates"].reverse()
    with pytest.raises(ValueError):
        CandidateScreeningBundle.model_validate(screening)


@pytest.mark.parametrize("artifact", ["candidate_evidence", "candidate_screening"])
@pytest.mark.parametrize("marker", [None, 1])
def test_restored_consumers_block_mixed_or_downgraded_schema_before_provider(
    artifact: str, marker: int | None
) -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    from etf_advisor.dashboard import review_payload
    from etf_advisor.domain.construction import PortfolioConstructionPolicy
    from etf_advisor.domain.screening import CandidateScreeningPolicy
    from etf_advisor.graph import nodes
    from etf_advisor.graph.revision import RevisionRuntime
    from etf_advisor.graph.workflow import build_graph

    evidence = lossless_evidence()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        clock=lambda: evidence.checked_at,
        candidate_retriever=SimpleNamespace(retrieve=lambda *args, **kwargs: evidence),
    )
    state = dict(
        graph.invoke(
            {"profile": valid_profile()}, {"configurable": {"thread_id": "lossless-restore"}}
        )
    )
    assert state["status"] == "awaiting_human_review"
    state[artifact]["schema_version"] = marker
    if artifact == "candidate_evidence":
        screened = nodes.screen_candidates(state, policy=CandidateScreeningPolicy())
        assert screened["status"] == "screening_blocked"
        runtime = RevisionRuntime(
            clock=lambda: evidence.checked_at, identifier_factory=lambda: "unused", inputs={}
        )
        with pytest.raises(ValueError):
            runtime.validate_output(state, "retrieve_candidate_evidence")
    constructed = nodes.construct_portfolio(state, policy=PortfolioConstructionPolicy())
    assert constructed["status"] == "construction_blocked"
    generator = SimpleNamespace(
        generate=lambda *args: pytest.fail("invalid state reached provider")
    )
    explained = nodes.draft_explanation(state, generator=generator)
    assert explained["status"] == "explanation_blocked"
    with pytest.raises(ValueError):
        review_payload(state)


def test_research_error_diagnostics_never_echo_identity_or_private_metadata() -> None:
    document = lossless_snapshot().to_source_documents()[0]
    private = "private-source-marker"
    metadata = document.chroma_metadata()
    metadata["source_url"] = private
    result = select_candidate_evidence(
        InvestorProfile.model_validate(valid_profile()),
        [
            GraphEnrichedSource(
                document_id="research:" + private, content=document.content, metadata=metadata
            )
        ],
        query="research",
        checked_at=lossless_snapshot().ingested_at,
        max_age=timedelta(hours=24),
    )
    assert result.status == "blocked"
    assert private not in result.model_dump_json()


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate",
        "foreign",
        "null_ids",
        "short_content",
        "native_content",
        "null_metadata",
        "null_array",
    ],
)
def test_immutable_chroma_readback_rejects_malformed_bounded_arrays(damage: str) -> None:
    from etf_advisor.rag.chroma_store import ChromaDocumentStore

    document = lossless_snapshot().to_source_documents()[0]
    payload: dict[str, Any] = {
        "ids": [document.document_id],
        "documents": [document.content],
        "metadatas": [document.chroma_metadata()],
    }
    if damage == "duplicate":
        payload["ids"] *= 2
    elif damage == "foreign":
        payload["ids"] = ["research:foreign"]
    elif damage == "null_ids":
        payload["ids"] = [None]
    elif damage == "short_content":
        payload["documents"] = []
    elif damage == "native_content":
        payload["documents"] = [42]
    elif damage == "null_metadata":
        payload["metadatas"] = [None]
    else:
        payload["metadatas"] = None
    store = ChromaDocumentStore(
        client=SimpleNamespace(
            get_or_create_collection=lambda **kwargs: SimpleNamespace(get=lambda **kwargs: payload)
        )
    )
    with pytest.raises((RuntimeError, ValueError)):
        store.document_records([document.document_id])


@pytest.mark.parametrize("damage", ["omitted", "duplicate", "graph_join"])
def test_schema2_replacement_retriever_cannot_hide_omissions_duplicates_or_bad_joins(
    damage: str,
) -> None:
    from etf_advisor.graph import nodes

    snapshot = lossless_snapshot()
    evidence = lossless_evidence()
    if damage == "omitted":
        altered = evidence.model_copy(update={"candidates": evidence.candidates[:-1]})
        blocked = nodes.retrieve_candidate_evidence(
            {"profile": valid_profile()},
            retriever=SimpleNamespace(retrieve=lambda *args, **kwargs: altered),
            limit=5,
        )
        assert blocked["status"] == "evidence_blocked"
        assert blocked["candidate_evidence"] == {}
        return
    document = snapshot.to_source_documents()[0]
    source = GraphEnrichedSource(
        document_id=document.document_id,
        content=document.content,
        metadata=document.chroma_metadata(),
    )
    sources = [source, source]
    if damage == "graph_join":
        source.graph_context = GraphContext(
            schema_version=2,
            source_document_id="wrong-join",
            symbol=source.metadata["symbol"],
            etf_name="ETF",
        )
        sources = [source]
    retriever = HybridCandidateEvidenceRetriever(
        SimpleNamespace(search=lambda *args, **kwargs: sources),
        clock=lambda: snapshot.ingested_at,
        max_age=timedelta(hours=24),
    )
    blocked = nodes.retrieve_candidate_evidence(
        {"profile": valid_profile()},
        retriever=retriever,
        limit=5,
    )
    assert blocked["status"] == "evidence_blocked"
    assert blocked["candidate_evidence"] == {}
