"""Deterministic replay evaluation for explanation and safety validation."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from etf_advisor.evaluation.explanation_models import (
    ExplanationDimensionScore,
    ExplanationEvaluationCase,
    ExplanationEvaluationCaseResult,
    ExplanationEvaluationDataset,
    ExplanationEvaluationDecision,
    ExplanationEvaluationDimension,
    ExplanationEvaluationMetrics,
    ExplanationEvaluationReport,
)
from etf_advisor.explanation.models import validate_and_bundle_explanation


def load_explanation_evaluation_dataset(
    path: Path | None = None,
) -> ExplanationEvaluationDataset:
    """Load and validate a JSON evaluation set or the packaged baseline."""

    if path is None:
        resource = files("etf_advisor.evaluation").joinpath("explanation_baseline.json")
        raw = resource.read_text(encoding="utf-8")
    else:
        raw = path.read_text(encoding="utf-8")
    return ExplanationEvaluationDataset.model_validate(json.loads(raw))


def run_offline_explanation_evaluation(
    dataset: ExplanationEvaluationDataset,
) -> ExplanationEvaluationReport:
    """Replay curated outputs through the exact production pre-review validator."""

    results = [_evaluate_case(dataset, case) for case in dataset.cases]
    correct_count = sum(result.passed for result in results)
    dimension_scores = {
        dimension: _score_dimension(results, dimension)
        for dimension in ExplanationEvaluationDimension
    }
    passed = correct_count == len(results)
    failures = [result.case_id for result in results if not result.passed]
    conclusion = (
        "All curated explanation and safety cases matched the expected fail-closed decision."
        if passed
        else "Explanation evaluation gate failed for: " + ", ".join(failures) + "."
    )
    return ExplanationEvaluationReport(
        dataset_id=dataset.dataset_id,
        version=dataset.version,
        metrics=ExplanationEvaluationMetrics(
            case_count=len(results),
            correct_count=correct_count,
            decision_accuracy=_ratio(correct_count, len(results)),
            citation_validity=dimension_scores[ExplanationEvaluationDimension.CITATION_VALIDITY],
            claim_support=dimension_scores[ExplanationEvaluationDimension.CLAIM_SUPPORT],
            subject_source_agreement=dimension_scores[
                ExplanationEvaluationDimension.SUBJECT_SOURCE_AGREEMENT
            ],
            refusal_behavior=dimension_scores[ExplanationEvaluationDimension.REFUSAL_BEHAVIOR],
            unsafe_language=dimension_scores[ExplanationEvaluationDimension.UNSAFE_LANGUAGE],
            prompt_injection_resistance=dimension_scores[
                ExplanationEvaluationDimension.PROMPT_INJECTION_RESISTANCE
            ],
            passed=passed,
        ),
        cases=results,
        conclusion=conclusion,
    )


def _evaluate_case(
    dataset: ExplanationEvaluationDataset,
    case: ExplanationEvaluationCase,
) -> ExplanationEvaluationCaseResult:
    if case.provider_refusal:
        actual = ExplanationEvaluationDecision.REJECT
        reason = "provider_refusal"
    else:
        try:
            if case.result is None:  # Defensive after dataset validation.
                raise ValueError("Missing provider result.")
            validate_and_bundle_explanation(dataset.request, case.result)
        except ValueError as exc:
            actual = ExplanationEvaluationDecision.REJECT
            reason = _sanitized_reason(exc)
        else:
            actual = ExplanationEvaluationDecision.ACCEPT
            reason = "accepted"
    return ExplanationEvaluationCaseResult(
        case_id=case.case_id,
        dimensions=case.dimensions,
        expected_decision=case.expected_decision,
        actual_decision=actual,
        passed=actual == case.expected_decision,
        reason=reason,
    )


def _score_dimension(
    results: list[ExplanationEvaluationCaseResult],
    dimension: ExplanationEvaluationDimension,
) -> ExplanationDimensionScore:
    scoped = [result for result in results if dimension in result.dimensions]
    correct_count = sum(result.passed for result in scoped)
    return ExplanationDimensionScore(
        case_count=len(scoped),
        correct_count=correct_count,
        accuracy=_ratio(correct_count, len(scoped)),
    )


def _sanitized_reason(error: ValueError) -> str:
    message = str(error).casefold()
    if "unknown source reference" in message or "unknown grounding reference" in message:
        return "invalid_grounding_reference"
    if "subjects do not match" in message:
        return "subject_source_mismatch"
    if "prohibited financial claims" in message:
        return "unsafe_financial_language"
    if "numeric claim absent" in message:
        return "unsupported_numeric_claim"
    return "validation_error"


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0
