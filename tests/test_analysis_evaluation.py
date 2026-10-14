"""Issue 99 evaluation gate tests against production evidence and finance boundaries."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from etf_advisor.cli import app
from etf_advisor.evaluation import analysis
from etf_advisor.evaluation.analysis import (
    compare_case,
    load_analysis_dataset,
    run_analysis_baseline,
    run_analysis_case,
)
from etf_advisor.evaluation.offline import (
    CuratedRelationshipStore,
    CuratedSemanticStore,
    load_evaluation_dataset,
)
from etf_advisor.rag.models import GraphContext, RetrievedSource


def test_frozen_replay_is_complete_and_repeatable() -> None:
    first = run_analysis_baseline()
    second = run_analysis_baseline()
    assert first == second
    assert first["metrics"] == {"case_count": 37, "correct_count": 37, "case_agreement": 1.0}
    assert len(first["retrieval"]["cases"]) == 5
    assert len(first["explanation"]["cases"]) == 14
    assert len(first["analysis"]) == 18
    assert first["analysis_source_provenance"]["max_source_age_hours"] == 24
    assert first["analysis"][0]["actual"]["sources"][0]["observed_at"] == (
        "2026-09-01T20:00:00+00:00"
    )
    assert all(item["passed"] for item in first["analysis"])


def test_original_fixtures_retain_frozen_lf_bytes() -> None:
    expected = {
        "retrieval_baseline.json": (
            "9d159ac7eb6b4bae9eec36aaf829bd22dacdf8efac42964c8c369c344b2a5a4e"
        ),
        "explanation_baseline.json": (
            "09694077a2174f556180b9db6802112be921169593e1df4616562652c7bc6fb4"
        ),
    }
    for name, digest in expected.items():
        raw = files("etf_advisor.evaluation").joinpath(name).read_bytes()
        assert b"\r\n" not in raw
        assert hashlib.sha256(raw).hexdigest() == digest


def test_frozen_contract_paths_block_stale_conflicting_and_eu_sources() -> None:
    cases = {case.id: case for case in load_analysis_dataset().cases}
    assert run_analysis_case(cases["stale-field"])["reason"] == "field_stale"
    assert run_analysis_case(cases["conflicting-fee"])["reason"] == "screening_contract_error"
    for case_id in ("listing-eu-eur", "listing-eu-usd"):
        actual = run_analysis_case(cases[case_id])
        assert actual["status"] == "blocked"
        assert "market" in actual["reason"]
        assert actual["candidate_symbols"] == []


def test_changed_frozen_expectation_fails_cli(tmp_path: Path) -> None:
    path = tmp_path / "changed.json"
    data = load_analysis_dataset().model_dump(mode="json")
    data["cases"][0]["weights_bps"] = [2000] * 5
    path.write_text(json.dumps(data), encoding="utf-8")
    result = CliRunner().invoke(app, ["evaluate-analysis", "--dataset", str(path)])
    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert report["metrics"]["correct_count"] == 36
    assert report["analysis"][0]["failures"] == ["weights_bps differs from frozen expectation"]


def test_actual_production_outcome_mismatch_propagates() -> None:
    case = next(case for case in load_analysis_dataset().cases if case.id == "balanced")
    actual = run_analysis_case(case)
    assert compare_case(case, actual) == []
    actual["draft"]["initial_total_cents"] -= 1
    assert any("initial_total_cents" in issue for issue in compare_case(case, actual))


def _cli_report(dataset: Path | None = None) -> tuple[int, dict[str, Any]]:
    args = ["evaluate-analysis"]
    if dataset is not None:
        args += ["--dataset", str(dataset)]
    result = CliRunner().invoke(app, args)
    return result.exit_code, json.loads(result.stdout)


def test_expected_stage_cannot_skip_construction(tmp_path: Path) -> None:
    data = load_analysis_dataset().model_dump(mode="json")
    data["cases"][0]["expected_stage"] = "evidence"
    data["cases"][0]["expected_status"] = "ready"
    path = tmp_path / "expected_stage.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    exit_code, report = _cli_report(path)
    assert exit_code == 1
    assert report["metrics"]["correct_count"] == 36
    assert report["analysis"][0]["actual"]["stage"] == "construction"
    assert any("stage" in failure for failure in report["analysis"][0]["failures"])


def test_every_ready_case_has_complete_fixed_allocation_vectors() -> None:
    ready_cases = [
        case
        for case in load_analysis_dataset().cases
        if case.expected_status == "ready" and case.expected_stage == "construction"
    ]
    assert len(ready_cases) == 8
    for case in ready_cases:
        actual = run_analysis_case(case)
        assert compare_case(case, actual) == []
        assert len(case.symbols) in (4, 5)
        assert all(
            len(vector) == len(case.symbols)
            for vector in (case.weights_bps, case.initial_cents, case.recurring_cents)
        )
        weights = actual["draft"]["weights_bps"]
        weights[0] += 1
        weights[1] -= 1
        assert sum(weights) == 10_000
        assert "weights_bps differs from frozen expectation" in compare_case(case, actual)


def test_sum_preserving_cents_regression_fails_cli(tmp_path: Path) -> None:
    data = load_analysis_dataset().model_dump(mode="json")
    aggressive = next(case for case in data["cases"] if case["id"] == "aggressive")
    aggressive["initial_cents"][0] += 1
    aggressive["initial_cents"][1] -= 1
    aggressive["recurring_cents"][0] -= 1
    aggressive["recurring_cents"][1] += 1
    path = tmp_path / "wrong_cents.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    exit_code, report = _cli_report(path)
    assert exit_code == 1
    failures = next(item["failures"] for item in report["analysis"] if item["id"] == "aggressive")
    assert "initial_cents differs from frozen expectation" in failures
    assert "recurring_cents differs from frozen expectation" in failures


def test_missing_allocation_vector_fails_cli(tmp_path: Path) -> None:
    data = load_analysis_dataset().model_dump(mode="json")
    aggressive = next(case for case in data["cases"] if case["id"] == "aggressive")
    aggressive["weights_bps"] = []
    path = tmp_path / "missing_vector.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    exit_code, report = _cli_report(path)
    assert exit_code == 1
    failures = next(item["failures"] for item in report["analysis"] if item["id"] == "aggressive")
    assert "ready case has missing or incomplete frozen vectors" in failures


def test_relevant_rank_reorder_fails_mrr_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    original = CuratedSemanticStore.search

    def reordered(
        self: CuratedSemanticStore,
        query: str,
        limit: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedSource]:
        results = original(self, query, limit, where)
        if query == next(
            case.query
            for case in load_evaluation_dataset().cases
            if case.case_id == "total-market-specificity"
        ):
            results[1], results[2] = results[2], results[1]
        return results

    monkeypatch.setattr(CuratedSemanticStore, "search", reordered)
    exit_code, report = _cli_report()
    assert exit_code == 1
    case = next(
        item for item in report["retrieval"]["cases"] if item["id"] == "total-market-specificity"
    )
    assert any("mean_reciprocal_rank" in failure for failure in case["failures"])
    assert case["actual"]["semantic_only"]["hit_rate_at_k"] == 1.0
    assert case["actual"]["semantic_only"]["recall_at_k"] == 1.0


@pytest.mark.parametrize(
    ("mutation", "case_id", "field"),
    [
        ("field", "broad-us-equity", "graph_context_field_accuracy"),
        ("context", "broad-us-equity", "graph_context_recall"),
        ("coverage", "technology-sector-threshold", "sector_context_coverage"),
    ],
)
def test_graph_metric_regressions_fail_cli(
    monkeypatch: pytest.MonkeyPatch, mutation: str, case_id: str, field: str
) -> None:
    original = CuratedRelationshipStore.find_contexts
    target = (
        "yahoo-finance:QQQ:2026-08-28:sectors"
        if mutation == "coverage"
        else "yahoo-finance:SPY:2026-08-26"
    )

    def changed(self: CuratedRelationshipStore, document_ids: list[str]) -> dict[str, GraphContext]:
        contexts = original(self, document_ids)
        if target in contexts:
            if mutation == "context":
                del contexts[target]
            elif mutation == "field":
                contexts[target] = contexts[target].model_copy(update={"category": "Wrong"})
            else:
                contexts[target] = contexts[target].model_copy(
                    update={"sector_exposures_status": None, "sector_exposures": []}
                )
        return contexts

    monkeypatch.setattr(CuratedRelationshipStore, "find_contexts", changed)
    exit_code, report = _cli_report()
    assert exit_code == 1
    case = next(item for item in report["retrieval"]["cases"] if item["id"] == case_id)
    assert any(field in failure for failure in case["failures"])


def test_missing_actual_metric_fails_closed() -> None:
    assert analysis._metric_failures(
        {"graph_enriched": {"mean_reciprocal_rank": 1.0}},
        {"graph_enriched": {}},
    ) == ["graph_enriched.mean_reciprocal_rank: expected 1.0, actual None"]


def test_aggregate_metric_regression_fails_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    original = analysis.run_offline_evaluation

    def changed(*args: Any, **kwargs: Any) -> Any:
        report = original(*args, **kwargs)
        semantic = report.semantic_only.model_copy(update={"mean_reciprocal_rank": 0.8})
        return report.model_copy(update={"semantic_only": semantic})

    monkeypatch.setattr(analysis, "run_offline_evaluation", changed)
    exit_code, report = _cli_report()
    assert exit_code == 1
    assert report["metrics"]["correct_count"] == 37
    assert any(
        "mean_reciprocal_rank" in failure for failure in report["retrieval"]["aggregate_failures"]
    )
