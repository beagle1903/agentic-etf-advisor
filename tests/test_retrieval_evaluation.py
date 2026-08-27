import json

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
    assert first.dataset.version == 2
    assert first.dataset.document_count == 4
    assert first.dataset.sources == ["Yahoo Finance"]
    assert first.dataset.observation_start.isoformat() == "2026-08-26T20:00:00+00:00"
    assert first.semantic_only.hit_rate_at_k == 1.0
    assert first.semantic_only.recall_at_k == 1.0
    assert first.semantic_only.mean_reciprocal_rank == 0.875
    assert first.semantic_only.source_attribution_rate == 1.0
    assert first.semantic_only.graph_context_recall == 0.0
    assert first.graph_enriched.graph_context_recall == 1.0
    assert first.graph_enriched.graph_context_field_accuracy == 1.0
    assert first.deltas.mean_reciprocal_rank == 0.0
    assert first.deltas.graph_context_field_accuracy == 1.0
    assert "does not improve semantic ranking" in first.conclusion


def test_missing_graph_context_lowers_context_metrics() -> None:
    payload = load_evaluation_dataset().model_dump(mode="json")
    vti = next(
        document
        for document in payload["documents"]
        if document["source_document"]["symbol"] == "VTI"
    )
    vti["graph_context"] = None

    report = run_offline_evaluation(RetrievalEvaluationDataset.model_validate(payload))

    assert report.graph_enriched.graph_context_recall == 0.6
    assert report.graph_enriched.graph_context_field_accuracy == 0.6


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
    assert report.graph_enriched.graph_context_field_accuracy == 0.8


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
    assert report["semantic_only"]["mean_reciprocal_rank"] == 0.875
    assert report["deltas"]["mean_reciprocal_rank"] == 0.0
