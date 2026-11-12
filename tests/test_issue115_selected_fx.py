"""Selected FX staging uses the same real construction prefix as the graph."""

from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from test_us_eu_contract import NOW, _evidence, _fx, _profile, _snapshot
from test_workflow import review_decision

from etf_advisor.domain.construction import PortfolioConstructionPolicy
from etf_advisor.domain.revision import digest
from etf_advisor.domain.screening import CandidateScreeningPolicy
from etf_advisor.domain.us_eu import FxReferenceObservation
from etf_advisor.graph.revision import _sealed_values, operation_digest, validate_revision_state
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.evidence import EvidenceRetrievalError, HybridCandidateEvidenceRetriever
from etf_advisor.rag.models import GraphEnrichedSource


def _run(
    *,
    policy=None,
    screening_policy=None,
    base="USD",
    initial=100_001,
    recurring=1,
    rate=None,
    snapshot=None,
):
    snapshot = snapshot or _snapshot()

    class Search:
        calls = 0

        def search(self, query, *, limit):
            self.calls += 1
            return [
                GraphEnrichedSource(
                    document_id=doc.document_id, content=doc.content, metadata=doc.metadata
                )
                for doc in snapshot.to_source_documents()
            ]

    class Provider:
        calls = 0

        def fetch_eur_usd(self):
            self.calls += 1
            return rate or _fx()

    search, provider = Search(), Provider()
    retriever = HybridCandidateEvidenceRetriever(
        search, clock=lambda: NOW, max_age=timedelta(hours=120), fx_provider=provider
    )
    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=retriever,
        construction_policy=policy or PortfolioConstructionPolicy(),
        screening_policy=screening_policy or CandidateScreeningPolicy(),
        clock=lambda: NOW,
    )
    state = graph.invoke(
        {
            "profile": _profile(base=base, initial=initial, recurring=recurring).model_dump(
                mode="json"
            )
        },
        {
            "configurable": {
                "thread_id": f"selected-{base}-{initial}-{recurring}-{policy is not None}"
            }
        },
    )
    return state, search.calls, provider.calls


@pytest.mark.parametrize("base", ["USD", "EUR"])
def test_selected_foreign_fetches_once_with_zero_cash_and_binds_receipt(base):
    state, search_calls, fx_calls = _run(base=base, initial=0, recurring=0)
    assert (search_calls, fx_calls) == (1, 1)
    assert state["status"] == "awaiting_human_review"
    assert state["candidate_evidence"]["fx_staging"] == "selected-subset-v1"
    positions = state["portfolio_construction"]["draft"]["positions"]
    assert [p["symbol"] for p in positions] == ["SPY", "CSPX.AS", "BND"]
    assert sum(p["weight_bps"] for p in positions) == 10_000
    assert all(p["initial_base_minor"] == 0 and p["recurring_base_minor"] == 0 for p in positions)
    ledger = validate_revision_state(state)
    assert ledger.revisions[0].receipts[0].status == "succeeded"
    assert ledger.revisions[0].inputs["fx_staging"] == "selected-subset-v1"


def test_plain_hybrid_uses_selected_defaults_and_explicit_legacy_retains_raw_pool():
    snapshot = _snapshot()

    class Search:
        def search(self, query, *, limit):
            return [
                GraphEnrichedSource(
                    document_id=doc.document_id, content=doc.content, metadata=doc.metadata
                )
                for doc in snapshot.to_source_documents()
            ]

    class Provider:
        calls = 0

        def fetch_eur_usd(self):
            self.calls += 1
            return _fx()

    provider = Provider()
    retriever = HybridCandidateEvidenceRetriever(
        Search(), clock=lambda: NOW, max_age=timedelta(hours=120), fx_provider=provider
    )
    fresh = retriever.retrieve(_profile(), limit=3)
    assert fresh.fx_staging == "selected-subset-v1"
    assert fresh.fx_reference == _fx()
    historical = retriever.retrieve_legacy(_profile(), limit=3)
    assert historical.fx_staging is None
    assert "fx_staging" not in historical.model_dump(mode="json")
    assert historical.fx_reference == _fx()
    assert provider.calls == 2


def test_unmarked_historical_evidence_and_receipt_digests_are_frozen():
    from etf_advisor.domain.revision import RevisionInputs
    from etf_advisor.domain.screening import CandidateScreeningPolicy

    evidence = _evidence(profile=_profile(), fx=_fx()).model_dump(mode="json")
    inputs = RevisionInputs(
        profile=_profile(),
        screening_policy=CandidateScreeningPolicy(),
        construction_policy=PortfolioConstructionPolicy(),
        candidate_limit=3,
        with_evidence=True,
        with_explanation=False,
        explanation_instruction="",
    ).model_dump(mode="json")
    assert "fx_staging" not in evidence and "fx_staging" not in inputs
    assert digest(evidence) == "4b9907643ea86751929b6adb1a791c52f8fb984365f8a9e2ee8911d43131f954"
    assert digest(inputs) == "dcdc23eedab038ba7ecff50daaa611ad4f08b528007742ba73b93f03d2687903"
    ledger = SimpleNamespace(thread_id="historical-thread")
    revision = SimpleNamespace(revision_id="historical-revision", inputs=inputs)
    assert operation_digest(ledger, revision, "retrieve_candidate_evidence") == (
        "6c8281cdd6b48af754d7c44c9598e8caf4fd8290f86c7305c47051fa0ea9a87b"
    )


def test_nondefault_two_position_policy_skips_unselected_foreign():
    policy = PortfolioConstructionPolicy(min_positions=2, max_positions=2)
    state, search_calls, fx_calls = _run(policy=policy)
    assert (search_calls, fx_calls) == (1, 0)
    assert state["status"] == "awaiting_human_review"
    assert state["candidate_evidence"]["fx_reference"]["missing_reason"] == "not_requested"
    assert [p["symbol"] for p in state["portfolio_construction"]["draft"]["positions"]] == [
        "SPY",
        "BND",
    ]
    validate_revision_state(state)


@pytest.mark.parametrize("case", ["screened_out", "position_cap", "category_zero_sleeve"])
def test_preselection_blockers_make_no_fx_call(case):
    policy = PortfolioConstructionPolicy()
    screening = CandidateScreeningPolicy()
    if case == "screened_out":
        screening = CandidateScreeningPolicy(max_expense_ratio_pct=0)
    elif case == "position_cap":
        policy = PortfolioConstructionPolicy(max_position_weight_bps=3_000)
    else:
        policy = PortfolioConstructionPolicy(
            category_sleeves={
                "growth": ["Unrepresented Growth"],
                "defensive": ["Intermediate Core Bond"],
            }
        )
    state, search_calls, fx_calls = _run(policy=policy, screening_policy=screening)
    assert (search_calls, fx_calls) == (1, 0)
    assert state["status"] == "construction_blocked"
    assert state["candidate_evidence"]["fx_reference"]["missing_reason"] == "not_requested"


def test_duplicate_economic_group_blocks_before_fx():
    snapshot = _snapshot()
    snapshot.records[1].economic_group_id.value = snapshot.records[0].economic_group_id.value
    state, search_calls, fx_calls = _run(snapshot=snapshot)
    assert (search_calls, fx_calls) == (1, 0)
    assert state["status"] == "construction_blocked"
    assert state["candidate_evidence"]["fx_reference"]["missing_reason"] == "not_requested"


def test_catalogue_omits_foreign_raw_pool_before_fx():
    from test_issue105_catalogue import _large_construction

    inputs, previous = _large_construction("balanced", "moderate", shortlist_limit=3)
    assert previous.status == "ready"
    assert any(c.trading_currency == "USD" for c in inputs.candidate_evidence.candidates)
    assert previous.catalogue_selection is not None
    shortlist = set(previous.catalogue_selection.shortlist_ids)
    assert all(
        c.trading_currency == "EUR"
        for c in inputs.candidate_evidence.candidates
        if c.document_id in shortlist
    )
    profile = inputs.profile.model_copy(update={"base_currency": "EUR"})
    profile = type(inputs.profile).model_validate(profile.model_dump(mode="json"))
    sources = [
        GraphEnrichedSource(
            document_id=c.document_id,
            content=c.content,
            metadata=c.metadata,
            graph_context=c.graph_context,
        )
        for c in inputs.candidate_evidence.candidates
    ]

    class CatalogueReader:
        calls = 0

        def load_catalogue_scope(self, request):
            self.calls += 1
            assert request == profile.catalogue_request
            return sources

    class Provider:
        calls = 0

        def fetch_eur_usd(self):
            self.calls += 1
            raise AssertionError("Omitted USD listings must not trigger ECB")

    reader, provider = CatalogueReader(), Provider()
    retriever = HybridCandidateEvidenceRetriever(
        object(),
        clock=lambda: inputs.candidate_evidence.checked_at,
        max_age=timedelta(hours=120),
        fx_provider=provider,
        catalogue_reader=reader,
    )
    graph = build_graph(
        checkpointer=InMemorySaver(),
        candidate_retriever=retriever,
        candidate_limit=3,
        clock=lambda: inputs.candidate_evidence.checked_at,
    )
    state = graph.invoke(
        {"profile": profile.model_dump(mode="json")},
        {"configurable": {"thread_id": "catalogue-shortlist-no-fx"}},
    )
    assert state["status"] == "awaiting_human_review"
    assert (reader.calls, provider.calls) == (1, 0)
    assert state["candidate_evidence"]["fx_reference"]["missing_reason"] == "not_requested"
    assert all(
        p["trading_currency"] == "EUR"
        for p in state["portfolio_construction"]["draft"]["positions"]
    )


def test_selected_foreign_provider_failure_is_construction_blocker():
    missing = FxReferenceObservation(
        status="missing",
        observed_at=NOW,
        effective_date=None,
        rate_decimal=None,
        missing_reason="source_unavailable",
    )
    state, search_calls, fx_calls = _run(rate=missing)
    assert (search_calls, fx_calls) == (1, 1)
    assert state["status"] == "construction_blocked"
    assert state["candidate_evidence"]["fx_reference"]["missing_reason"] == "source_unavailable"
    validate_revision_state(state)


def test_provider_source_unavailable_observation_keeps_original_timestamp():
    observed = NOW + timedelta(minutes=1)
    missing = FxReferenceObservation(
        status="missing",
        observed_at=observed,
        effective_date=None,
        rate_decimal=None,
        missing_reason="source_unavailable",
    )
    state, search_calls, fx_calls = _run(rate=missing)
    assert (search_calls, fx_calls) == (1, 1)
    assert state["status"] == "construction_blocked"
    assert (
        datetime.fromisoformat(
            state["candidate_evidence"]["fx_reference"]["observed_at"].replace("Z", "+00:00")
        )
        == observed
    )
    assert state["candidate_evidence"]["fx_reference"]["missing_reason"] == "source_unavailable"
    validate_revision_state(state)


def test_required_provider_not_requested_is_rejected_as_unavailable():
    invalid = FxReferenceObservation(
        status="missing",
        observed_at=NOW,
        effective_date=None,
        rate_decimal=None,
        missing_reason="not_requested",
    )
    state, search_calls, fx_calls = _run(rate=invalid)
    assert (search_calls, fx_calls) == (1, 1)
    assert state["status"] == "construction_blocked"
    assert state["candidate_evidence"]["fx_reference"]["missing_reason"] == "source_unavailable"


def test_rehashed_skip_to_available_fx_is_rejected_against_producing_policy():
    state, _, _ = _run(policy=PortfolioConstructionPolicy(min_positions=2, max_positions=2))
    tampered = deepcopy(state)
    evidence = tampered["candidate_evidence"]
    evidence["fx_reference"] = _fx().model_dump(mode="json")
    revision = tampered["revision_ledger"]["revisions"][0]
    artifact = tampered["revision_ledger"]["artifacts"][revision["artifacts"]["candidate_evidence"]]
    artifact["value"] = evidence
    artifact["digest"] = digest(evidence)
    revision["receipts"][0]["output_digest"] = artifact["digest"]
    tampered["revision_digest"] = digest(_sealed_values(tampered))
    with pytest.raises(ValueError, match="Unselected FX observation"):
        validate_revision_state(tampered)


@pytest.mark.parametrize("construction_blocked", [False, True])
def test_rehashed_skipped_fx_timestamp_mismatch_is_rejected(construction_blocked):
    policy = (
        PortfolioConstructionPolicy(max_position_weight_bps=3_000)
        if construction_blocked
        else PortfolioConstructionPolicy(min_positions=2, max_positions=2)
    )
    state, _, fx_calls = _run(policy=policy)
    assert fx_calls == 0
    assert state["status"] == (
        "construction_blocked" if construction_blocked else "awaiting_human_review"
    )
    tampered = deepcopy(state)
    evidence = tampered["candidate_evidence"]
    evidence["fx_reference"]["observed_at"] = (NOW + timedelta(days=1)).isoformat()
    revision = tampered["revision_ledger"]["revisions"][0]
    artifact = tampered["revision_ledger"]["artifacts"][revision["artifacts"]["candidate_evidence"]]
    artifact["value"] = evidence
    artifact["digest"] = digest(evidence)
    revision["receipts"][0]["output_digest"] = artifact["digest"]
    tampered["revision_digest"] = digest(_sealed_values(tampered))
    with pytest.raises(ValueError, match="Skipped FX timestamp"):
        validate_revision_state(tampered)


def test_downstream_new_foreign_selection_blocks_without_new_retrieval():
    snapshot = _snapshot()

    class Search:
        calls = 0

        def search(self, query, *, limit):
            self.calls += 1
            return [
                GraphEnrichedSource(
                    document_id=doc.document_id, content=doc.content, metadata=doc.metadata
                )
                for doc in snapshot.to_source_documents()
            ]

    class Provider:
        calls = 0

        def fetch_eur_usd(self):
            self.calls += 1
            return _fx()

    search, provider = Search(), Provider()
    retriever = HybridCandidateEvidenceRetriever(
        search, clock=lambda: NOW, max_age=timedelta(hours=120), fx_provider=provider
    )
    saver = InMemorySaver()
    config = {"configurable": {"thread_id": "skip-to-foreign"}}
    graph = build_graph(
        checkpointer=saver,
        candidate_retriever=retriever,
        construction_policy=PortfolioConstructionPolicy(min_positions=2, max_positions=2),
        clock=lambda: NOW,
    )
    first = graph.invoke({"profile": _profile().model_dump(mode="json")}, config)
    assert first["status"] == "awaiting_human_review"
    original = deepcopy(first["candidate_evidence"])
    revised = graph.invoke(
        Command(
            resume={
                **review_decision(
                    first,
                    "edit",
                    [
                        {
                            "kind": "construction_policy",
                            "patch": {"max_positions": 3, "min_positions": 3},
                        }
                    ],
                ),
                "submitted_at": NOW.isoformat(),
            }
        ),
        config,
    )
    assert revised["status"] == "construction_blocked"
    assert revised["candidate_evidence"] == original
    assert revised["portfolio_construction"]["errors"][0]["code"] == "fx_missing"
    assert (search.calls, provider.calls) == (1, 0)
    validate_revision_state(revised)


def test_inherited_foreign_fx_survives_base_only_review_and_offline_descendant():
    from etf_advisor.dashboard import review_payload

    snapshot = _snapshot()

    class Search:
        calls = 0

        def search(self, query, *, limit):
            self.calls += 1
            return [
                GraphEnrichedSource(
                    document_id=doc.document_id, content=doc.content, metadata=doc.metadata
                )
                for doc in snapshot.to_source_documents()
            ]

    class Provider:
        calls = 0

        def fetch_eur_usd(self):
            self.calls += 1
            return _fx()

    search, provider = Search(), Provider()
    retriever = HybridCandidateEvidenceRetriever(
        search, clock=lambda: NOW, max_age=timedelta(hours=120), fx_provider=provider
    )
    saver = InMemorySaver()
    config = {"configurable": {"thread_id": "foreign-to-base-multihop"}}
    graph = build_graph(checkpointer=saver, candidate_retriever=retriever, clock=lambda: NOW)
    first = graph.invoke({"profile": _profile().model_dump(mode="json")}, config)
    assert first["status"] == "awaiting_human_review"
    assert [p["symbol"] for p in first["portfolio_construction"]["draft"]["positions"]] == [
        "SPY",
        "CSPX.AS",
        "BND",
    ]
    origin = validate_revision_state(first).revisions[0]
    evidence_id = origin.artifacts["candidate_evidence"]
    evidence_digest = first["revision_ledger"]["artifacts"][evidence_id]["digest"]
    checked_at = first["candidate_evidence"]["checked_at"]
    second = graph.invoke(
        Command(
            resume={
                **review_decision(
                    first,
                    "edit",
                    [
                        {
                            "kind": "construction_policy",
                            "patch": {"min_positions": 2, "max_positions": 2},
                        }
                    ],
                ),
                "submitted_at": NOW.isoformat(),
            }
        ),
        config,
    )
    assert second["status"] == "awaiting_human_review"
    assert [p["symbol"] for p in second["portfolio_construction"]["draft"]["positions"]] == [
        "SPY",
        "BND",
    ]
    third = graph.invoke(
        Command(
            resume={
                **review_decision(
                    second,
                    "edit",
                    [
                        {
                            "kind": "screening_policy",
                            "patch": {"max_expense_ratio_pct": 0.5},
                        }
                    ],
                ),
                "submitted_at": NOW.isoformat(),
            }
        ),
        config,
    )
    assert third["status"] == "awaiting_human_review"
    assert [p["symbol"] for p in third["portfolio_construction"]["draft"]["positions"]] == [
        "SPY",
        "BND",
    ]
    ledger = validate_revision_state(third)
    assert all(
        revision.artifacts["candidate_evidence"] == evidence_id for revision in ledger.revisions
    )
    assert third["revision_ledger"]["artifacts"][evidence_id]["digest"] == evidence_digest
    assert third["candidate_evidence"]["checked_at"] == checked_at
    assert (search.calls, provider.calls) == (1, 1)

    def forbidden():
        raise AssertionError("Offline restore must not read the clock or an adapter")

    restored = build_graph(checkpointer=saver, clock=forbidden)
    detached = dict(restored.get_state(config).values)
    detached["__interrupt__"] = restored.get_state(config).interrupts
    assert review_payload(detached)["portfolio_construction"]["status"] == "ready"
    assert (search.calls, provider.calls) == (1, 1)


@pytest.mark.parametrize("ambiguous", [False, True])
def test_marked_retrieval_retry_needs_exact_request(ambiguous):
    snapshot = _snapshot()

    class Search:
        calls = 0

        def search(self, query, *, limit):
            self.calls += 1
            return [
                GraphEnrichedSource(
                    document_id=doc.document_id, content=doc.content, metadata=doc.metadata
                )
                for doc in snapshot.to_source_documents()
            ]

    class Provider:
        calls = 0

        def fetch_eur_usd(self):
            self.calls += 1
            return _fx()

    class FailingOnce(HybridCandidateEvidenceRetriever):
        attempts = 0

        def retrieve_selected(self, profile, *, limit, selection):
            self.attempts += 1
            if self.attempts == 1:
                if ambiguous:
                    raise RuntimeError("simulated lost response")
                raise EvidenceRetrievalError("synthetic failure", code="retrieval_unavailable")
            return super().retrieve_selected(profile, limit=limit, selection=selection)

    search, provider = Search(), Provider()
    retriever = FailingOnce(
        search, clock=lambda: NOW, max_age=timedelta(hours=120), fx_provider=provider
    )
    saver = InMemorySaver()
    config = {"configurable": {"thread_id": "selected-retry-" + str(ambiguous)}}
    graph = build_graph(checkpointer=saver, candidate_retriever=retriever, clock=lambda: NOW)
    if ambiguous:
        with pytest.raises(RuntimeError, match="lost response"):
            graph.invoke({"profile": _profile().model_dump(mode="json")}, config)
        first = graph.get_state(config).values
    else:
        first = graph.invoke({"profile": _profile().model_dump(mode="json")}, config)
    prior = validate_revision_state(first).revisions[0].receipts[0]
    assert prior.status == ("started" if ambiguous else "failed")
    assert (search.calls, provider.calls) == (0, 0)
    restored = build_graph(checkpointer=saver, candidate_retriever=retriever, clock=lambda: NOW)
    if ambiguous:
        assert restored.invoke(None, config)["status"] == "revision_blocked"
        assert retriever.attempts == 1
    result = restored.invoke(
        {
            "retry_request": {
                "action": "retry",
                "revision_id": prior.revision_id,
                "operation_id": prior.operation_id,
            }
        },
        config,
    )
    assert result["status"] == "awaiting_human_review"
    receipts = validate_revision_state(result).revisions[0].receipts
    assert [receipt.status for receipt in receipts] == [prior.status, "succeeded"]
    assert (retriever.attempts, search.calls, provider.calls) == (2, 1, 1)
