"""Issue 99 evaluation gate tests against production evidence and finance boundaries."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files
from pathlib import Path

from typer.testing import CliRunner

from etf_advisor.cli import app
from etf_advisor.evaluation.analysis import (
    compare_case,
    load_analysis_dataset,
    run_analysis_baseline,
    run_analysis_case,
)


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
