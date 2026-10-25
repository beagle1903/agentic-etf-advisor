import hashlib
import json
from importlib.resources import files

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from etf_advisor.cli import app
from etf_advisor.evaluation.models import RetrievalEvaluationDataset
from etf_advisor.evaluation.offline import load_evaluation_dataset, run_offline_evaluation


def test_offline_evaluation_compares_ranking_and_context_deterministically() -> None:
    dataset = load_evaluation_dataset()

    first = run_offline_evaluation(dataset)
    second = run_offline_evaluation(dataset)

    assert first == second
    assert first.dataset.dataset_id == "retrieval-baseline"
    assert first.dataset.version == 3
    assert first.dataset.document_count == 7
    assert first.dataset.sources == ["Yahoo Finance"]
    assert first.dataset.observation_start.isoformat() == "2026-08-26T20:00:00+00:00"
    assert first.dataset.observation_end.isoformat() == "2026-08-28T20:00:00+00:00"
    assert first.semantic_only.hit_rate_at_k == 1.0
    assert first.semantic_only.recall_at_k == 1.0
    assert first.semantic_only.mean_reciprocal_rank == 0.9
    assert first.semantic_only.source_attribution_rate == 1.0
    assert first.semantic_only.graph_context_recall == 0.0
    assert first.semantic_only.sector_context_coverage == 0.0
    assert first.semantic_only.sector_constraint_exact_match_rate == 0.0
    assert first.graph_enriched.graph_context_recall == 1.0
    assert first.graph_enriched.graph_context_field_accuracy == 1.0
    assert first.graph_enriched.sector_context_coverage == 1.0
    assert first.graph_enriched.sector_constraint_exact_match_rate == 1.0
    assert first.deltas.mean_reciprocal_rank == 0.0
    assert first.deltas.graph_context_field_accuracy == 1.0
    assert first.deltas.sector_constraint_exact_match_rate == 1.0
    assert "without changing semantic ranking" in first.conclusion


def test_original_controls_and_case_level_paired_sources() -> None:
    resource = files("etf_advisor.evaluation")
    baseline_digest = hashlib.sha256(resource.joinpath("retrieval_baseline.json").read_bytes())
    assert baseline_digest.hexdigest() == (
        "9d159ac7eb6b4bae9eec36aaf829bd22dacdf8efac42964c8c369c344b2a5a4e"
    )
    assert (
        hashlib.sha256(
            resource.joinpath("retrieval_expected_metrics.json").read_bytes()
        ).hexdigest()
        == "af28ed7c9889e2e399fc2d8f871889bc1dbbc9ae195c9dd8b1884989dab90415"
    )
    report = run_offline_evaluation(load_evaluation_dataset())
    assert len(report.cases) == 5
    for case in report.cases:
        expected = [(item.document_id, item.distance) for item in case.semantic_candidates]
        for results in (case.semantic_only_results, case.graph_enriched_results):
            assert [(item.document_id, item.distance) for item in results] == expected
            assert [item.rank for item in results] == [1, 2, 3]
            assert all(item.source == "Yahoo Finance" for item in results)
            assert all(item.source_url and item.observed_at for item in results)
            assert all(item.snapshot_identity is None for item in results)
            assert all(item.field_provenance is None for item in results)
        assert all(item.graph_context is None for item in case.semantic_only_results)
        assert case.deltas.mean_reciprocal_rank == 0
    sector = report.cases[-1]
    assert sector.case_id == "technology-sector-threshold"
    assert sector.graph_enriched_results[0].observed_at == "2026-08-28T20:00:00Z"
    assert sector.graph_enriched_results[0].sector_exposures_status == "available"
    assert sector.semantic_only_results[0].sector_exposures_status is None
    assert sector.deltas.sector_constraint_exact_match_rate == 1


def test_missing_graph_context_lowers_context_metrics() -> None:
    payload = load_evaluation_dataset().model_dump(mode="json")
    vti = next(
        document
        for document in payload["documents"]
        if document["source_document"]["symbol"] == "VTI"
    )
    vti["graph_context"] = None

    report = run_offline_evaluation(RetrievalEvaluationDataset.model_validate(payload))

    assert report.graph_enriched.graph_context_recall == 0.666667
    assert report.graph_enriched.graph_context_field_accuracy == 0.666667


def test_incorrect_graph_context_lowers_field_accuracy() -> None:
    payload = load_evaluation_dataset().model_dump(mode="json")
    vti = next(
        document
        for document in payload["documents"]
        if document["source_document"]["symbol"] == "VTI"
    )
    vti["graph_context"]["category"] = "Incorrect Category"

    report = run_offline_evaluation(RetrievalEvaluationDataset.model_validate(payload))

    assert report.graph_enriched.graph_context_recall == 1.0
    assert report.graph_enriched.graph_context_field_accuracy == 0.833333


def test_incorrect_sector_weight_fails_exact_constraint_match() -> None:
    payload = load_evaluation_dataset().model_dump(mode="json")
    qqq = next(
        document
        for document in payload["documents"]
        if document["source_document"]["document_id"].endswith("QQQ:2026-08-28:sectors")
    )
    technology = next(
        exposure
        for exposure in qqq["graph_context"]["sector_exposures"]
        if exposure["name"] == "technology"
    )
    technology["weight_pct"] = 39.0

    report = run_offline_evaluation(RetrievalEvaluationDataset.model_validate(payload))

    assert report.graph_enriched.sector_context_coverage == 1.0
    assert report.graph_enriched.sector_constraint_exact_match_rate == 0.0
    assert report.conclusion == "Review the metric deltas before changing retrieval or graph scope."


def test_dataset_validation_rejects_naive_observation_timestamp() -> None:
    payload = load_evaluation_dataset().model_dump(mode="json")
    payload["documents"][0]["source_document"]["observed_at"] = "2026-08-26T20:00:00"

    with pytest.raises(ValidationError, match="timestamps must be timezone-aware"):
        RetrievalEvaluationDataset.model_validate(payload)


@pytest.mark.parametrize(
    "invalid_change",
    ["duplicate", "unknown", "missing_provenance", "invalid_source_url"],
)
def test_dataset_validation_rejects_invalid_references_and_provenance(
    invalid_change: str,
) -> None:
    payload = load_evaluation_dataset().model_dump(mode="json")
    if invalid_change == "duplicate":
        payload["documents"].append(payload["documents"][0])
    elif invalid_change == "unknown":
        payload["cases"][0]["semantic_candidates"][0]["document_id"] = "unknown-document"
    elif invalid_change == "missing_provenance":
        del payload["documents"][0]["source_document"]["source_url"]
    else:
        payload["documents"][0]["source_document"]["source_url"] = "not-a-url"

    with pytest.raises(ValidationError):
        RetrievalEvaluationDataset.model_validate(payload)


def test_evaluate_retrieval_cli_emits_stable_json_offline() -> None:
    runner = CliRunner()

    first = runner.invoke(app, ["evaluate-retrieval"])
    second = runner.invoke(app, ["evaluate-retrieval"])

    assert first.exit_code == 0
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert report["dataset"]["dataset_id"] == "retrieval-baseline"
    assert report["semantic_only"]["mean_reciprocal_rank"] == 0.9
    assert report["deltas"]["mean_reciprocal_rank"] == 0.0
    assert report["deltas"]["sector_context_coverage"] == 1.0
    assert report["deltas"]["sector_constraint_exact_match_rate"] == 1.0
