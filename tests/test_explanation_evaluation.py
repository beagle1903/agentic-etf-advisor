import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from etf_advisor.cli import app
from etf_advisor.evaluation.explanation_models import ExplanationEvaluationDataset
from etf_advisor.evaluation.explanation_offline import (
    load_explanation_evaluation_dataset,
    run_offline_explanation_evaluation,
)


def test_offline_explanation_evaluation_is_deterministic_and_passes_all_dimensions() -> None:
    dataset = load_explanation_evaluation_dataset()

    first = run_offline_explanation_evaluation(dataset)
    second = run_offline_explanation_evaluation(dataset)

    assert first == second
    assert first.dataset_id == "explanation-safety-baseline"
    assert first.version == 1
    assert first.metrics.case_count == 8
    assert first.metrics.correct_count == 8
    assert first.metrics.decision_accuracy == 1.0
    assert first.metrics.citation_validity.accuracy == 1.0
    assert first.metrics.claim_support.accuracy == 1.0
    assert first.metrics.subject_source_agreement.accuracy == 1.0
    assert first.metrics.refusal_behavior.accuracy == 1.0
    assert first.metrics.unsafe_language.accuracy == 1.0
    assert first.metrics.prompt_injection_resistance.accuracy == 1.0
    assert first.metrics.passed is True
    assert all(case.passed for case in first.cases)


def test_unexpected_validator_decision_fails_the_gate_and_dimension_score() -> None:
    payload = load_explanation_evaluation_dataset().model_dump(mode="json")
    safe_case = next(
        case for case in payload["cases"] if case["case_id"] == "grounded-safe-response"
    )
    safe_case["expected_decision"] = "reject"
    dataset = ExplanationEvaluationDataset.model_validate(payload)

    report = run_offline_explanation_evaluation(dataset)

    assert report.metrics.passed is False
    assert report.metrics.correct_count == 7
    assert report.metrics.citation_validity.accuracy == 0.5
    assert report.metrics.prompt_injection_resistance.accuracy == 0.5
    assert report.cases[0].actual_decision == "accept"
    assert report.cases[0].passed is False
    assert "grounded-safe-response" in report.conclusion


def test_dataset_requires_every_quality_dimension() -> None:
    payload = load_explanation_evaluation_dataset().model_dump(mode="json")
    for case in payload["cases"]:
        case["dimensions"] = [
            dimension for dimension in case["dimensions"] if dimension != "refusal_behavior"
        ]
    payload["cases"] = [case for case in payload["cases"] if case["dimensions"]]

    with pytest.raises(ValidationError, match="missing dimensions: refusal_behavior"):
        ExplanationEvaluationDataset.model_validate(payload)


def test_dataset_rejects_result_and_refusal_in_the_same_case() -> None:
    payload = load_explanation_evaluation_dataset().model_dump(mode="json")
    payload["cases"][0]["provider_refusal"] = True

    with pytest.raises(ValidationError, match="exactly one provider result or provider refusal"):
        ExplanationEvaluationDataset.model_validate(payload)


def test_dataset_rejects_duplicate_case_ids() -> None:
    payload = load_explanation_evaluation_dataset().model_dump(mode="json")
    payload["cases"][1]["case_id"] = payload["cases"][0]["case_id"]

    with pytest.raises(ValidationError, match="duplicate case IDs"):
        ExplanationEvaluationDataset.model_validate(payload)


def test_explanation_evaluation_cli_emits_stable_json_offline() -> None:
    runner = CliRunner()

    first = runner.invoke(app, ["evaluate-explanations"])
    second = runner.invoke(app, ["evaluate-explanations"])

    assert first.exit_code == 0
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert report["dataset_id"] == "explanation-safety-baseline"
    assert report["metrics"]["decision_accuracy"] == 1.0
    assert report["metrics"]["passed"] is True


def test_explanation_evaluation_cli_exits_nonzero_when_gate_fails(tmp_path: Path) -> None:
    path = tmp_path / "regression.json"
    payload = load_explanation_evaluation_dataset().model_dump(mode="json")
    payload["cases"][0]["expected_decision"] = "reject"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = CliRunner().invoke(app, ["evaluate-explanations", "--dataset", str(path)])

    assert result.exit_code == 1
    assert json.loads(result.stdout)["metrics"]["passed"] is False
