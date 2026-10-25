"""Actual Streamlit catalogue preparation and production graph orchestration."""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_dashboard import DurableMemoryCheckpointStore
from test_issue105_catalogue import _isin
from test_us_eu_contract import _record

from etf_advisor.catalogue.research_job import ResearchJobStore
from etf_advisor.catalogue.service import validate_catalogue
from etf_advisor.domain.us_eu import FxReferenceObservation
from etf_advisor.encoding import document_fingerprint
from etf_advisor.rag.models import GraphContext, RetrievedSource
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity, SnapshotManifest

FIXTURE = Path(__file__).parent / "fixtures" / "issue105_catalogue_240.json"


class _Catalogue:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data

    def read(self):
        return self.data

    def read_version(self, version: str, *, max_bytes: int):
        assert version == self.data["version"]
        assert max_bytes == 32 * 1024 * 1024
        return self.data


class _Documents:
    def __init__(self) -> None:
        self.rows: dict[str, Any] = {}

    def stage_snapshot(self, documents):
        self.rows = {item.document_id: item for item in documents}
        return len(documents)

    def document_records(self, ids):
        return {
            key: RetrievedSource(
                document_id=key,
                content=self.rows[key].content,
                metadata=self.rows[key].chroma_metadata(),
            )
            for key in ids
            if key in self.rows
        }

    def missing_document_ids(self, ids):
        return [key for key in ids if key not in self.rows]

    def document_metadatas(self, ids):
        return {key: self.rows[key].chroma_metadata() for key in ids if key in self.rows}


class _Graph:
    def __init__(self) -> None:
        self.active: ActiveSnapshotIdentity | None = None
        self.documents: list[Any] = []

    def active_snapshot_identity(self):
        return self.active

    def snapshot_digest(self, version):
        return (
            self.active.snapshot_digest
            if self.active and self.active.snapshot_version == version
            else None
        )

    def publish_snapshot(
        self,
        documents,
        *,
        snapshot_version,
        universe_id,
        universe_version,
        snapshot_digest,
        expected_prior=None,
    ):
        assert self.active == expected_prior
        assert universe_id == "catalogue-research-v1"
        assert universe_version
        self.documents = list(documents)
        self.active = ActiveSnapshotIdentity(snapshot_version, snapshot_digest)
        return len(documents)

    def snapshot_manifest(self, version):
        if self.active is None or self.active.snapshot_version != version:
            return None
        return SnapshotManifest(
            snapshot_version=version,
            snapshot_digest=self.active.snapshot_digest,
            document_count=len(self.documents),
            document_ids=tuple(doc.document_id for doc in self.documents),
            schema_version=2,
            fingerprints={
                doc.document_id: document_fingerprint(
                    doc.document_id, doc.content, doc.chroma_metadata()
                )
                for doc in self.documents
            },
        )

    def find_contexts(self, ids):
        contexts = {}
        for doc in self.documents:
            if doc.document_id not in ids:
                continue
            metadata = doc.chroma_metadata()
            sector = json.loads(metadata["field_provenance_json"])["sector_exposures"]
            contexts[doc.document_id] = GraphContext(
                source_document_id=doc.document_id,
                schema_version=2,
                symbol=doc.symbol,
                etf_name=metadata["name"],
                fund_family=metadata["fund_family"],
                category=metadata["category"],
                sector_exposures_status="available",
                sector_exposures=[
                    {"name": item["name"], "weight_pct_token": item["weight_pct_token"]}
                    for item in sector["value"]
                ],
            )
        return contexts

    def verify_snapshot(self, version):
        assert self.active and self.active.snapshot_version == version

    def close(self):
        pass


class _Collector:
    def __init__(self, members) -> None:
        self.indices = {member.listing_id: index for index, member in enumerate(members)}
        self.calls: list[str] = []

    def collect(self, listing, snapshot_version, references, budget, *, clock):
        index = self.indices[listing.listing_id]
        now = clock()
        category = (
            "Intermediate Core Bond"
            if index % 3 == 0
            else "Large Blend"
            if index % 3 == 1
            else "Large Growth"
        )
        record = _record(
            listing.symbol,
            listing.exchange,
            "USD" if listing.exchange == "PCX" else "EUR",
            category,
            _isin(index),
        )
        updates = {
            name: field.model_copy(
                update={
                    "snapshot_version": snapshot_version,
                    "observed_at": now - timedelta(minutes=1),
                    "ingested_at": now,
                }
            )
            for name, field in record.research_fields().items()
        }
        self.calls.append(listing.symbol)
        return record.model_copy(update=updates)


def test_app_over_limit_preview_shows_measured_count_without_stale_scope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    import etf_advisor.catalogue.research_job as jobs
    import etf_advisor.catalogue.store as catalogue_store
    import etf_advisor.dashboard_app as dashboard_app

    catalogue = validate_catalogue(json.loads(FIXTURE.read_text(encoding="utf-8")))
    ids = [row["listing_id"] for row in catalogue["direct"][:101]]
    monkeypatch.setattr(catalogue_store, "CatalogueStore", lambda: _Catalogue(catalogue))
    monkeypatch.setattr(jobs, "ResearchJobStore", lambda: ResearchJobStore(tmp_path))

    def forbidden(*args, **kwargs):
        raise AssertionError("over-limit preview invoked research or publication")

    monkeypatch.setattr(dashboard_app, "begin_catalogue_research", forbidden)
    monkeypatch.setattr(dashboard_app, "publish_catalogue_research", forbidden)
    app = testing.AppTest.from_file(str(Path(dashboard_app.__file__))).run(timeout=60)
    next(item for item in app.sidebar.selectbox if item.label == "Advisory scope").set_value(
        "US / EU catalogue research"
    )
    app.run(timeout=60)
    listing_input = next(
        item
        for item in app.sidebar.text_input
        if item.label == "Exact listing IDs (comma separated)"
    )
    listing_input.set_value(",".join(ids[:40]))
    next(item for item in app.sidebar.button if item.label == "Preview catalogue scope").click()
    app.run(timeout=60)
    assert not app.exception
    assert app.session_state["catalogue_scope_preview"].coverage["requested"] == 40
    listing_input = next(
        item
        for item in app.sidebar.text_input
        if item.label == "Exact listing IDs (comma separated)"
    )
    listing_input.set_value(",".join(ids))
    next(item for item in app.sidebar.button if item.label == "Preview catalogue scope").click()
    app.run(timeout=60)
    assert not app.exception
    assert "catalogue_scope_preview" not in app.session_state
    assert "catalogue_research_job_id" not in app.session_state
    assert next(
        item for item in app.sidebar.button if item.label == "Begin catalogue research job"
    ).disabled
    assert any("matched=101" in item.value and "limit=100" in item.value for item in app.error)

    class BrokenStore:
        def read(self):
            raise RuntimeError("private-provider-payload")

    monkeypatch.setattr(catalogue_store, "CatalogueStore", lambda: BrokenStore())
    next(item for item in app.sidebar.button if item.label == "Preview catalogue scope").click()
    app.run(timeout=60)
    assert not app.exception
    assert "catalogue_scope_preview" not in app.session_state
    assert all("private-provider-payload" not in item.value for item in app.error)
    assert any("Scope unavailable" in item.value for item in app.error)


def test_fresh_app_session_reopens_partial_job_without_automatic_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    import etf_advisor.catalogue.research_job as jobs
    import etf_advisor.catalogue.store as catalogue_store
    import etf_advisor.data.yahoo_research as yahoo_research

    catalogue = validate_catalogue(json.loads(FIXTURE.read_text(encoding="utf-8")))
    ids = [row["listing_id"] for row in catalogue["direct"][:6]]
    from etf_advisor.catalogue.research_scope import plan_catalogue_scope

    scope = plan_catalogue_scope(catalogue, {"listing_ids": ids})
    store = ResearchJobStore(tmp_path)
    collector = _Collector(scope.members)
    monkeypatch.setattr(catalogue_store, "CatalogueStore", lambda: _Catalogue(catalogue))
    monkeypatch.setattr(jobs, "ResearchJobStore", lambda: store)
    monkeypatch.setattr(
        yahoo_research, "YahooCatalogueResearchCollector", lambda **kwargs: collector
    )
    script = Path(__file__).parents[1] / "src/etf_advisor/dashboard_app.py"

    first = testing.AppTest.from_file(str(script)).run(timeout=60)
    next(item for item in first.sidebar.selectbox if item.label == "Advisory scope").set_value(
        "US / EU catalogue research"
    )
    first.run(timeout=60)
    next(
        item
        for item in first.sidebar.text_input
        if item.label == "Exact listing IDs (comma separated)"
    ).set_value(",".join(ids))
    next(item for item in first.sidebar.button if item.label == "Preview catalogue scope").click()
    first.run(timeout=60)
    next(
        item for item in first.sidebar.button if item.label == "Begin catalogue research job"
    ).click()
    first.run(timeout=60)
    job_id = first.session_state["catalogue_research_job_id"]
    next(
        item for item in first.sidebar.button if item.label == "Collect next catalogue batch"
    ).click()
    first.run(timeout=60)
    partial = store.read(job_id)
    assert len(partial.cached) == 5
    assert len(collector.calls) == 5
    cache = {key: value.model_dump(mode="json") for key, value in partial.cached.items()}
    identity = (partial.snapshot_version, partial.generation)

    fresh = testing.AppTest.from_file(str(script)).run(timeout=60)
    next(item for item in fresh.sidebar.selectbox if item.label == "Advisory scope").set_value(
        "US / EU catalogue research"
    )
    fresh.run(timeout=60)
    assert "catalogue_research_job_id" not in fresh.session_state
    assert len(collector.calls) == 5
    next(
        item for item in fresh.sidebar.text_input if item.label == "Saved catalogue research job ID"
    ).set_value(job_id)
    next(
        item for item in fresh.sidebar.button if item.label == "Load saved catalogue research job"
    ).click()
    fresh.run(timeout=60)
    assert not fresh.exception
    assert fresh.session_state["catalogue_research_job_id"] == job_id
    loaded = store.read(job_id)
    assert (loaded.snapshot_version, loaded.generation) == identity
    assert {key: value.model_dump(mode="json") for key, value in loaded.cached.items()} == cache
    assert len(collector.calls) == 5
    next(
        item for item in fresh.sidebar.button if item.label == "Collect next catalogue batch"
    ).click()
    fresh.run(timeout=60)
    complete = store.read(job_id)
    assert len(complete.cached) == 6
    assert {
        key: value.model_dump(mode="json") for key, value in complete.cached.items() if key in cache
    } == cache
    assert len(collector.calls) == 6
    assert collector.calls[-1] == next(
        member.symbol for member in scope.members if member.listing_id not in cache
    )

    missing_id, corrupt_id = str(uuid4()), str(uuid4())
    (tmp_path / f"{corrupt_id}.json").write_text("private-invalid-manifest", encoding="utf-8")
    for invalid_id in ("not-a-job-id", missing_id, corrupt_id):
        next(
            item
            for item in fresh.sidebar.text_input
            if item.label == "Saved catalogue research job ID"
        ).set_value(invalid_id)
        next(
            item
            for item in fresh.sidebar.button
            if item.label == "Load saved catalogue research job"
        ).click()
        fresh.run(timeout=60)
        assert "catalogue_research_job_id" not in fresh.session_state
        assert len(collector.calls) == 6
        assert all("private-invalid-manifest" not in item.value for item in fresh.error)
        assert any(
            "Saved research job is unavailable or invalid" in item.value for item in fresh.error
        )


def test_app_prepares_40_and_creates_review_with_outside_six_member(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    testing = pytest.importorskip("streamlit.testing.v1")
    import etf_advisor.catalogue.research_job as jobs
    import etf_advisor.catalogue.store as catalogue_store
    import etf_advisor.dashboard as dashboard
    import etf_advisor.data.yahoo_research as yahoo_research
    import etf_advisor.rag.chroma_store as chroma_store
    import etf_advisor.rag.neo4j_store as neo4j_store
    from etf_advisor.dashboard_app import (
        _catalogue_coverage_summary,
        _catalogue_job_summary,
        _catalogue_selection_summary,
    )

    catalogue = validate_catalogue(json.loads(FIXTURE.read_text(encoding="utf-8")))
    selected = catalogue["direct"][:40]
    ids = [row["listing_id"] for row in selected]
    documents, graph = _Documents(), _Graph()
    checkpoint_store = DurableMemoryCheckpointStore()
    store = ResearchJobStore(tmp_path)
    from etf_advisor.catalogue.research_scope import plan_catalogue_scope

    scope = plan_catalogue_scope(catalogue, {"listing_ids": ids})
    collector = _Collector(scope.members)
    monkeypatch.setattr(catalogue_store, "CatalogueStore", lambda: _Catalogue(catalogue))
    monkeypatch.setattr(jobs, "ResearchJobStore", lambda: store)
    monkeypatch.setattr(
        yahoo_research, "YahooCatalogueResearchCollector", lambda **kwargs: collector
    )
    monkeypatch.setattr(chroma_store, "ChromaDocumentStore", lambda **kwargs: documents)
    monkeypatch.setattr(neo4j_store, "Neo4jGraphStore", lambda **kwargs: graph)
    monkeypatch.setattr(dashboard, "CatalogueStore", lambda: _Catalogue(catalogue))
    monkeypatch.setattr(dashboard, "ChromaDocumentStore", lambda **kwargs: documents)
    monkeypatch.setattr(dashboard, "Neo4jGraphStore", lambda **kwargs: graph)
    monkeypatch.setattr(
        dashboard, "PostgresCheckpointStore", lambda *args, **kwargs: checkpoint_store
    )

    class Fx:
        def __init__(self, clock):
            self.clock = clock

        def fetch_eur_usd(self):
            at = self.clock()
            return FxReferenceObservation(
                status="available",
                effective_date=at.date(),
                observed_at=at,
                rate_decimal="1.1253",
                missing_reason=None,
            )

    monkeypatch.setattr(dashboard, "EcbFxClient", Fx)
    script = Path(__file__).parents[1] / "src/etf_advisor/dashboard_app.py"
    app = testing.AppTest.from_file(str(script)).run(timeout=60)
    next(item for item in app.sidebar.selectbox if item.label == "Advisory scope").set_value(
        "US / EU catalogue research"
    )
    app.run(timeout=60)
    next(
        item
        for item in app.sidebar.text_input
        if item.label == "Exact listing IDs (comma separated)"
    ).set_value(",".join(ids))
    next(item for item in app.sidebar.button if item.label == "Preview catalogue scope").click()
    app.run(timeout=60)
    assert not app.exception
    assert app.session_state["catalogue_scope_preview"].coverage["requested"] == 40
    preview_counts = _catalogue_coverage_summary(
        app.session_state["catalogue_scope_preview"].coverage
    )
    assert {
        key: preview_counts[key]
        for key in (
            "discovered",
            "direct",
            "direct_only",
            "overlap",
            "combined",
            "matched",
            "requested",
            "provider_status",
            "provider_partitions",
        )
    } == {
        "discovered": 0,
        "direct": 240,
        "direct_only": 240,
        "overlap": 0,
        "combined": 240,
        "matched": 240,
        "requested": 40,
        "provider_status": "not_run",
        "provider_partitions": 0,
    }
    assert len(preview_counts["unsupported_eu_countries"]) == 7
    assert len(preview_counts["excluded_venues"]) == 10
    next(
        item for item in app.sidebar.button if item.label == "Begin catalogue research job"
    ).click()
    app.run(timeout=60)
    assert not app.exception
    started_job = store.read(app.session_state["catalogue_research_job_id"])
    assert {
        key: _catalogue_job_summary(started_job)[key]
        for key in (
            "requested",
            "researched",
            "pending",
            "failed",
            "generation",
            "finalized",
            "publication",
        )
    } == {
        "requested": 40,
        "researched": 0,
        "pending": 40,
        "failed": 0,
        "generation": 0,
        "finalized": False,
        "publication": "not_started",
    }
    for _ in range(8):
        next(
            item for item in app.sidebar.button if item.label == "Collect next catalogue batch"
        ).click()
        app.run(timeout=60)
        assert not app.exception
    job = store.read(app.session_state["catalogue_research_job_id"])
    assert len(job.cached) == 40
    assert _catalogue_job_summary(job)["generation"] == 80
    assert _catalogue_job_summary(job)["researched"] == 40
    assert _catalogue_job_summary(job)["pending"] == 0
    next(
        item for item in app.sidebar.button if item.label == "Finalize complete catalogue snapshot"
    ).click()
    app.run(timeout=60)
    assert not app.exception
    assert _catalogue_job_summary(store.read(job.job_id))["generation"] == 81
    assert _catalogue_job_summary(store.read(job.job_id))["finalized"] is True
    next(
        item for item in app.sidebar.button if item.label == "Publish complete catalogue snapshot"
    ).click()
    app.run(timeout=60)
    assert not app.exception
    published = _catalogue_job_summary(store.read(job.job_id))
    assert published["generation"] == 83
    assert published["publication"] == "succeeded"
    next(
        item for item in app.sidebar.button if item.label == "Use published scope for new review"
    ).click()
    app.run(timeout=60)
    from etf_advisor.catalogue.research_scope import CatalogueScopeV1, _digest
    from etf_advisor.catalogue.retrieval import CatalogueSnapshotReader

    CatalogueSnapshotReader(_Catalogue(catalogue), documents, graph).load_catalogue_scope(
        app.session_state["catalogue_review_request"]
    )
    next(
        item for item in app.sidebar.checkbox if item.label == "Attach local source evidence"
    ).set_value(True)
    next(
        item for item in app.sidebar.checkbox if item.label == "Keep review in local PostgreSQL"
    ).set_value(True)
    next(item for item in app.sidebar.button if item.label == "Create review draft").click()
    app.run(timeout=60)
    assert not app.exception
    assert not app.error, {
        k: v
        for k, v in app.session_state["dashboard_run"].state.items()
        if k
        in {
            "status",
            "candidate_evidence",
            "candidate_screening",
            "portfolio_construction",
            "profile_errors",
            "candidate_errors",
            "evidence_errors",
        }
    }
    state = app.session_state["dashboard_run"].state
    assert state["status"] == "awaiting_human_review"
    assert len(state["candidate_evidence"]["candidates"]) == 40
    report = state["portfolio_construction"]["catalogue_selection"]
    assert len(report["shortlist_ids"]) <= 10
    summary = _catalogue_selection_summary(report)
    assert summary["usable_before_shortlist"] == 40
    assert summary["shortlisted"] == 5
    assert summary["capacity"] == 5
    assert summary["final_positions"] == len(state["portfolio_construction"]["draft"]["positions"])
    assert summary["requested_dispositions"] == 40
    assert summary["omitted"] == 35
    assert summary["unknown"] == 0
    assert sum(summary["reason_counts"].values()) == 40
    assert summary["not_evaluated_reason"] is None
    assert state["portfolio_construction"]["draft"]["total_weight_bps"] == 10_000
    assert any(
        position["symbol"] not in {"SPY", "VTI", "QQQ", "BND", "VEA", "VWO"}
        for position in state["portfolio_construction"]["draft"]["positions"]
    )
    assert len(collector.calls) == 40
    from etf_advisor.graph.revision import validate_revision_state

    comparison_before = json.dumps(
        {k: v for k, v in state.items() if k != "__interrupt__"}, sort_keys=True
    )
    outside = next(
        candidate
        for candidate in state["candidate_evidence"]["candidates"]
        if candidate["symbol"] not in {"SPY", "VTI", "QQQ", "BND", "VEA", "VWO"}
    )
    next(
        item for item in app.multiselect if item.label == "Choose candidates to compare"
    ).set_value([outside["document_id"]])
    app.run(timeout=60)
    assert not app.exception
    assert any(outside["symbol"] in str(item.value) for item in app.dataframe)
    assert (
        json.dumps({k: v for k, v in state.items() if k != "__interrupt__"}, sort_keys=True)
        == comparison_before
    )
    assert len(collector.calls) == 40
    overlap_other = next(
        candidate
        for candidate in state["candidate_evidence"]["candidates"]
        if candidate["document_id"] != outside["document_id"]
    )
    next(
        item
        for item in app.multiselect
        if item.label == "Choose two candidates for reported-holdings overlap"
    ).set_value([outside["document_id"], overlap_other["document_id"]])
    app.run(timeout=60)
    assert not app.exception
    assert any("Reported holdings only; lists may be partial" in item.value for item in app.caption)
    assert any("Reported overlap" in str(item.value) for item in (*app.markdown, *app.warning))
    assert (
        json.dumps({k: v for k, v in state.items() if k != "__interrupt__"}, sort_keys=True)
        == comparison_before
    )

    restored = json.loads(json.dumps({k: v for k, v in state.items() if k != "__interrupt__"}))
    validate_revision_state(restored, app.session_state["dashboard_run"].thread_id)
    assert restored["status"] == "awaiting_human_review"
    assert len(collector.calls) == 40
    token = app.session_state["dashboard_run"].thread_id

    def forbidden(*args, **kwargs):
        raise AssertionError("offline restore invoked an external adapter")

    with monkeypatch.context() as offline_patches:
        offline_patches.setattr(_Catalogue, "read_version", forbidden)
        offline_patches.setattr(_Documents, "document_records", forbidden)
        offline_patches.setattr(_Graph, "find_contexts", forbidden)
        offline_patches.setattr(Fx, "fetch_eur_usd", forbidden)
        offline_patches.setattr(_Collector, "collect", forbidden)
        offline = dashboard.load_dashboard_run(token, checkpoint_store=checkpoint_store)
        app.session_state["dashboard_run"] = offline
        app.run(timeout=60)
        assert not app.exception
        picker = next(
            item
            for item in app.multiselect
            if item.label == "Choose two candidates for reported-holdings overlap"
        )
        picker.set_value([outside["document_id"], overlap_other["document_id"]])
        app.run(timeout=60)
        assert not app.exception
        assert any("Reported overlap" in str(item.value) for item in (*app.markdown, *app.warning))
    assert offline.state["status"] == "awaiting_human_review"
    assert len(offline.state["candidate_evidence"]["candidates"]) == 40
    assert len(collector.calls) == 40
    request = app.session_state["catalogue_review_request"]
    reader = CatalogueSnapshotReader(_Catalogue(catalogue), documents, graph)
    expected_order = [member.symbol for member in request.scope.members]
    original_records = documents.document_records
    with monkeypatch.context() as permuted_provider:
        permuted_provider.setattr(
            documents,
            "document_records",
            lambda ids: dict(reversed(list(original_records(ids).items()))),
        )
        assert [row.metadata["symbol"] for row in reader.load_catalogue_scope(request)] == (
            expected_order
        )
    broken_scope = request.scope.model_copy(update={"digest": "0" * 64})
    with pytest.raises(ValueError):
        reader.load_catalogue_scope(request.model_copy(update={"scope": broken_scope}))
    scope_payload = request.scope.model_dump(mode="json", exclude={"digest"})
    scope_payload["members"] = scope_payload["members"][:-1]
    scope_payload["digest"] = _digest(scope_payload)
    changed_membership = CatalogueScopeV1.model_validate(scope_payload)
    with pytest.raises(ValueError):
        reader.load_catalogue_scope(request.model_copy(update={"scope": changed_membership}))
    with pytest.raises(ValueError):
        reader.load_catalogue_scope(
            request.model_copy(update={"snapshot_version": "different-version"})
        )
    first_id = graph.documents[0].document_id
    original_document = documents.rows[first_id]
    documents.rows[first_id] = original_document.model_copy(update={"content": "altered"})
    with pytest.raises(ValueError):
        reader.load_catalogue_scope(request)
    documents.rows[first_id] = original_document
    with monkeypatch.context() as missing_row:
        missing_row.setattr(documents, "document_records", lambda ids: {})
        with pytest.raises(ValueError):
            reader.load_catalogue_scope(request)
    with monkeypatch.context() as extra_row:
        extra_row.setattr(
            documents,
            "document_records",
            lambda ids: {**original_records(ids), "extra": original_records(ids)[first_id]},
        )
        with pytest.raises(ValueError):
            reader.load_catalogue_scope(request)
    with monkeypatch.context() as universe_change:
        universe_change.setattr(
            documents,
            "document_records",
            lambda ids: {
                **original_records(ids),
                first_id: original_records(ids)[first_id].model_copy(
                    update={
                        "metadata": {
                            **original_records(ids)[first_id].metadata,
                            "universe_id": "wrong-universe",
                        }
                    }
                ),
            },
        )
        with pytest.raises(ValueError):
            reader.load_catalogue_scope(request)
    with monkeypatch.context() as manifest_change:
        manifest_change.setattr(
            graph,
            "snapshot_manifest",
            lambda version: SnapshotManifest(
                snapshot_version=version,
                snapshot_digest=request.snapshot_digest,
                document_count=1,
                document_ids=(first_id,),
                schema_version=2,
                fingerprints={first_id: "0" * 64},
            ),
        )
        with pytest.raises(ValueError):
            reader.load_catalogue_scope(request)
    original_contexts = graph.find_contexts
    with monkeypatch.context() as graph_change:
        graph_change.setattr(
            graph,
            "find_contexts",
            lambda ids: {
                **original_contexts(ids),
                first_id: original_contexts(ids)[first_id].model_copy(
                    update={"source_document_id": "other"}
                ),
            },
        )
        with pytest.raises(ValueError):
            reader.load_catalogue_scope(request)
    original_identity = graph.active
    graph.active = ActiveSnapshotIdentity("changed", request.snapshot_digest)
    with pytest.raises(ValueError):
        reader.load_catalogue_scope(request)
    graph.active = original_identity
    tampered = json.loads(json.dumps(restored))
    tampered["portfolio_construction"]["catalogue_selection"]["shortlist_ids"].reverse()
    with pytest.raises(ValueError):
        validate_revision_state(tampered, token)
    request_tampered = json.loads(json.dumps(restored))
    request_tampered["profile"]["catalogue_request"]["snapshot_version"] = "other"
    with pytest.raises(ValueError):
        validate_revision_state(request_tampered, token)
    receipt_tampered = json.loads(json.dumps(restored))
    receipt_tampered["revision_ledger"]["revisions"][-1]["receipts"][-1]["input_digest"] = "0" * 64
    with pytest.raises(ValueError):
        validate_revision_state(receipt_tampered, token)
    unknown_report = {
        **report,
        "usable_count": None,
        "not_evaluated_reason": "upstream_contract_mismatch",
        "dispositions": [
            {**report["dispositions"][0], "reason": "candidate_screening_unknown"},
            {**report["dispositions"][1], "reason": "bounded_shortlist_omission"},
        ],
    }
    unknown_summary = _catalogue_selection_summary(unknown_report)
    assert unknown_summary["unknown"] == 1
    assert unknown_summary["omitted"] == 1
    assert unknown_summary["usable_before_shortlist"] is None
    assert unknown_summary["not_evaluated_reason"] == "upstream_contract_mismatch"
