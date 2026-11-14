"""Cross-case starter regression sensitivity; invented data, no live source calls."""

from __future__ import annotations

import json
import socket
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import etf_advisor.cli as cli
import etf_advisor.clock as clock
import etf_advisor.data.starter_collection as collection
import etf_advisor.evaluation.starter as starter
import etf_advisor.research.us_starter as preparation
from etf_advisor.checkpoint import MemoryCheckpointStore, PostgresCheckpointStore
from etf_advisor.data.fund_identity_registry import LocalFundIdentityRegistry
from etf_advisor.data.yahoo_research import YahooResearchAdapter
from etf_advisor.explanation.provider import LangChainExplanationGenerator
from etf_advisor.rag.chroma_store import ChromaDocumentStore
from etf_advisor.rag.neo4j_store import Neo4jGraphStore


def test_frozen_matrix_and_counts() -> None:
    report = starter.run_starter_baseline()
    assert report["passed"] and report["failed_cases"] == 0
    assert (
        report["corpus_sha256"]
        == "016a64e11db61e62a5d5201cf516963a5a0be82f7a85f78ea813db31991a71c0"
    )
    assert len(report["cases"]) == 12
    for case in report["cases"][:9]:
        assert case["evidence_status"] == "ready"
        assert len(case["source_outcomes"]) == 20
        assert all(outcome["reason"] == "synthetic_fixture" for outcome in case["source_outcomes"])
        count = 3 if case["shortlist_capacity"] == 3 else 5
        assert case["counts"] == dict(
            requested=20,
            collected=20,
            screened=20,
            eligible=20,
            excluded=0,
            shortlisted=case["shortlist_capacity"],
            selected=count,
        )
        actual = case["actual"]
        assert sum(actual["weights_bps"]) == 10000
        assert sum(actual["initial_cents"]) == 100000
        assert sum(actual["recurring_cents"]) == 25000
        for pair in case["holdings_diagnostics"]:
            assert pair["checked_at"] == "2026-11-05T13:00:00Z"
            for side in (pair["left"], pair["right"]):
                assert side["row_sum_pp"] == {"numerator": "10", "denominator": "1"}
                assert side["provider"] == "yahoo_finance"
                assert side["source_url"] == f"https://finance.yahoo.com/quote/{side['symbol']}/"
                assert side["observed_at"] == "2026-11-05T12:00:00Z"
    missing, unsupported, holdings = report["cases"][-3:]
    assert missing["counts"] == dict(
        requested=20, collected=20, screened=20, eligible=16, excluded=4, shortlisted=5, selected=0
    )
    assert {e["reason_code"] for e in missing["exclusions"]} == {"category_missing"}
    assert unsupported["counts"] == dict(
        requested=20, collected=20, screened=20, eligible=0, excluded=20, shortlisted=0, selected=0
    )
    assert all(c["verdict"] == "unknown" for c in unsupported["screening"]["candidates"])
    assert holdings["counts"]["selected"] == 5
    assert any(pair["overlap_pp"] is None for pair in holdings["holdings_diagnostics"])
    assert any(pair["status"] == "available" for pair in holdings["holdings_diagnostics"])


@pytest.mark.parametrize(
    "mutation",
    ["selection", "weight", "initial_cash", "monthly_cash", "status", "reason", "unavailable_zero"],
)
def test_mutated_expectations_are_visible_cli_failures(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    dataset = starter.load_starter_dataset()
    expected = dataset["cases"][0]["expected"]
    if mutation == "selection":
        expected["selected_ids"][0] = expected["selected_ids"][0].removesuffix("spy") + "ivv"
    elif mutation in {"weight", "initial_cash", "monthly_cash"}:
        field = {
            "weight": "weights_bps",
            "initial_cash": "initial_cents",
            "monthly_cash": "recurring_cents",
        }[mutation]
        before = sum(expected[field])
        expected[field][0] += 1
        expected[field][1] -= 1
        assert sum(expected[field]) == before
    elif mutation == "status":
        expected["status"] = "blocked"
    elif mutation == "reason":
        dataset["cases"][-3]["expected"]["reason"] = "insufficient_eligible_candidates"
    else:
        pair = dataset["cases"][-1]["expected"]["pairs"][0]
        assert pair["overlap_pp"] is None
        pair["overlap_pp"] = {"numerator": "0", "denominator": "1"}
    # Only the affected case needs replay; the complete matrix is checked separately.
    index = -3 if mutation == "reason" else (-1 if mutation == "unavailable_zero" else 0)
    dataset["cases"] = [dataset["cases"][index]]
    monkeypatch.setattr(starter, "load_starter_dataset", lambda: dataset)
    result = CliRunner().invoke(cli.app, ["evaluate-starter"])
    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert not report["passed"] and report["failed_cases"] == 1
    failure = next(case for case in report["cases"] if not case["passed"])
    assert failure["mismatches"]
    assert failure["expected"] != failure["actual"]


@pytest.mark.parametrize("field", ["weights_bps", "initial_cents", "recurring_cents", "pairs"])
def test_actual_regressions_fail_the_real_cli(monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    dataset = starter.load_starter_dataset()
    dataset["cases"] = [dataset["cases"][-1 if field == "pairs" else 0]]
    monkeypatch.setattr(starter, "load_starter_dataset", lambda: dataset)
    if field == "pairs":
        original_pairs = starter.selected_reported_holdings_overlaps

        def wrong_pairs(*args: Any, **kwargs: Any) -> Any:
            pairs = original_pairs(*args, **kwargs)
            assert pairs[0]["overlap_pp"] is None
            pairs[0]["overlap_pp"] = {"numerator": "0", "denominator": "1"}
            return pairs

        monkeypatch.setattr(starter, "selected_reported_holdings_overlaps", wrong_pairs)
    else:
        original_construct = starter.construct_model_portfolio
        position_field = {
            "weights_bps": "weight_bps",
            "initial_cents": "initial_usd_cents",
            "recurring_cents": "recurring_usd_cents",
        }[field]

        def wrong_construction(*args: Any, **kwargs: Any) -> Any:
            bundle = original_construct(*args, **kwargs)
            assert bundle.draft is not None
            positions = list(bundle.draft.positions)
            for index, delta in ((0, 1), (1, -1)):
                positions[index] = positions[index].model_copy(
                    update={position_field: getattr(positions[index], position_field) + delta}
                )
            return bundle.model_copy(
                update={"draft": bundle.draft.model_copy(update={"positions": positions})}
            )

        monkeypatch.setattr(starter, "construct_model_portfolio", wrong_construction)
    result = CliRunner().invoke(cli.app, ["evaluate-starter"])
    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    case = report["cases"][0]
    assert report["failed_cases"] == 1 and case["mismatches"] == [field]
    if field != "pairs":
        assert sum(case["expected"][field]) == sum(case["actual"][field])


def test_missing_null_field_is_not_equal_to_absence() -> None:
    assert starter.score_starter_case({"reason": None}, {}) == ["reason"]


def test_repeated_detached_replay_forbids_external_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = starter.load_starter_dataset()
    original = deepcopy(dataset)
    calls: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        calls.append("forbidden")
        pytest.fail("Replay crossed a forbidden external/clock/file boundary")

    for cls in (
        MemoryCheckpointStore,
        PostgresCheckpointStore,
        LocalFundIdentityRegistry,
        ChromaDocumentStore,
        Neo4jGraphStore,
        LangChainExplanationGenerator,
        YahooResearchAdapter,
    ):
        monkeypatch.setattr(cls, "__init__", forbidden)
    monkeypatch.setattr(collection, "run_pass", forbidden)
    monkeypatch.setattr(preparation, "prepare_from_pass", forbidden)
    monkeypatch.setattr(preparation.StarterArtifact, "load", forbidden)
    original_clock = clock.system_utc_now
    for name, module in list(sys.modules.items()):
        if name.startswith("etf_advisor") and module is not None:
            for attr, value in list(vars(module).items()):
                if value is original_clock:
                    monkeypatch.setattr(module, attr, forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    for attr in ("read_text", "read_bytes", "write_text", "write_bytes"):
        monkeypatch.setattr(Path, attr, forbidden)
    first = starter.canonical_report(starter.run_starter_baseline(dataset))
    detached = json.loads(json.dumps(dataset))
    second = starter.canonical_report(starter.run_starter_baseline(detached))
    assert first == second
    assert json.loads(first)["passed"]
    assert dataset == original
    assert calls == []


def test_cli_success_and_controlled_invalid_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    result = CliRunner().invoke(cli.app, ["evaluate-starter"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["passed"]
    monkeypatch.setattr(
        cli, "run_starter_baseline", lambda: (_ for _ in ()).throw(ValueError("bad fixture"))
    )
    result = CliRunner().invoke(cli.app, ["evaluate-starter"])
    assert result.exit_code == 1
    assert "Starter evaluation failed: bad fixture" in result.output
