"""Fixed, synthetic Issue 99 fixture replay through existing production boundaries."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from etf_advisor.domain.construction import (
    PortfolioConstructionInput,
    PortfolioConstructionPolicy,
    construct_model_portfolio,
)
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestmentObjective, InvestorProfile, RiskTolerance
from etf_advisor.domain.screening import (
    ScreeningContractError,
    ScreeningFieldFreshnessError,
    screen_candidate_evidence,
)
from etf_advisor.evaluation.explanation_offline import (
    load_explanation_evaluation_dataset,
    run_offline_explanation_evaluation,
)
from etf_advisor.evaluation.models import MetricDeltas, RetrievalMetrics
from etf_advisor.evaluation.offline import (
    CuratedRelationshipStore,
    CuratedSemanticStore,
    evaluate_strategy,
    load_evaluation_dataset,
    run_offline_evaluation,
)
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, SectorExposure
from etf_advisor.research.models import MissingReason, ResearchField, WeightedExposure

OBSERVED = datetime(2026, 9, 1, 20, tzinfo=UTC)
CHECKED = datetime(2026, 9, 2, 8, tzinfo=UTC)
VERSION = "issue99-analysis-v1"
LIMITATION = "Frozen offline fixture replay; no live Yahoo, model, suitability or return claim."
CASE_IDS = (
    "balanced",
    "conservative",
    "aggressive",
    "one-cent",
    "zero-cash",
    "sector-reported",
    "sector-unsupported",
    "missing-fee",
    "missing-category",
    "stale-document",
    "stale-field",
    "conflicting-fee",
    "insufficient-two",
    "position-infeasible",
    "concentration-fail",
    "listing-us-usd",
    "listing-eu-eur",
    "listing-eu-usd",
)
EVIDENCE_ONLY_CASE_IDS = frozenset({"listing-us-usd", "listing-eu-eur", "listing-eu-usd"})
BASE = {
    "SPY": "Large Blend",
    "VTI": "Large Blend",
    "QQQ": "Large Growth",
    "VEA": "Foreign Large Blend",
    "BND": "Intermediate Core Bond",
}
EU = {"VWCE.DE": ("de_market", "EUR", "Germany"), "CSPX.AS": ("nl_market", "USD", "Netherlands")}
RETRIEVAL_SHA = "9d159ac7eb6b4bae9eec36aaf829bd22dacdf8efac42964c8c369c344b2a5a4e"
EXPLANATION_SHA = "09694077a2174f556180b9db6802112be921169593e1df4616562652c7bc6fb4"


class AnalysisCase(BaseModel):
    """Frozen expected outcome and explicitly named deviation from the base fixture."""

    model_config = ConfigDict(extra="forbid")

    id: str
    expected_stage: str
    expected_status: str
    risk: str = "moderate"
    objective: str = "balanced"
    initial_usd: float = 1000
    recurring_usd: float = 250
    exclusions: list[str] = Field(default_factory=list)
    candidate_symbols: list[str] = Field(default_factory=lambda: list(BASE))
    max_position_weight_bps: int = 8000
    symbols: list[str] = Field(default_factory=list)
    weights_bps: list[int] = Field(default_factory=list)
    initial_cents: list[int] = Field(default_factory=list)
    recurring_cents: list[int] = Field(default_factory=list)
    excluded: dict[str, str] = Field(default_factory=dict)
    screening: dict[str, str] = Field(default_factory=dict)
    reason: str | None = None


class AnalysisDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    version: int
    cases: list[AnalysisCase]


def load_analysis_dataset(path: Path | None = None) -> AnalysisDataset:
    raw = (
        path.read_text(encoding="utf-8")
        if path
        else files("etf_advisor.evaluation")
        .joinpath("analysis_baseline.json")
        .read_text(encoding="utf-8")
    )
    dataset = AnalysisDataset.model_validate_json(raw)
    ids = [case.id for case in dataset.cases]
    if tuple(ids) != CASE_IDS:
        raise ValueError("Analysis dataset IDs/order differ from the frozen 18-case matrix.")
    return dataset


def _source(symbol: str, case_id: str) -> GraphEnrichedSource:
    """Build a synthetic source with canonical provenance; never infer a decision."""

    market, currency, listing = EU.get(symbol, ("us_market", "USD", "United States"))
    category = BASE.get(symbol, "Foreign Large Blend")
    document_at = CHECKED - timedelta(hours=25) if case_id == "stale-document" else OBSERVED
    url = f"https://finance.yahoo.com/quote/{symbol}/"
    missing = {"expense_ratio_pct"} if case_id == "missing-fee" and symbol == "SPY" else set()
    if case_id == "missing-category" and symbol == "BND":
        missing.add("category")
    concentration = 61.0 if case_id == "concentration-fail" and symbol == "SPY" else 40.0
    technology = 10.0 if case_id == "sector-reported" and symbol == "SPY" else 0.0
    values: dict[str, Any] = {
        "market": market,
        "quote_type": "ETF",
        "category": category,
        "expense_ratio_pct": 0.1,
        "average_daily_volume": 1_000_000,
        "top_10_concentration_pct": concentration,
        "sector_exposures": [WeightedExposure(name="Technology", weight_pct=technology)],
    }
    units = {
        "market": "classification",
        "quote_type": "classification",
        "category": "classification",
        "expense_ratio_pct": "percent",
        "average_daily_volume": "shares_per_day",
        "top_10_concentration_pct": "percent",
        "sector_exposures": "percent",
    }
    metadata: dict[str, str | int | float | bool] = {
        "symbol": symbol,
        "name": f"{symbol} synthetic ETF",
        "source": "yahoo_finance",
        "source_url": url,
        "observed_at": document_at.isoformat(),
        "market": market,
        "quote_type": "ETF",
        "currency": currency,
        "listing_country": listing,
    }
    provenance: dict[str, dict[str, Any]] = {}
    for field, value in values.items():
        observed = (
            CHECKED - timedelta(hours=25)
            if case_id == "stale-field" and symbol == "SPY" and field == "expense_ratio_pct"
            else document_at
        )
        entry = ResearchField[Any](
            value=None if field in missing else value,
            missing_reason=MissingReason.NOT_REPORTED if field in missing else None,
            unit=units[field],
            provider="yahoo_finance",
            source_url=url,
            observed_at=observed,
            ingested_at=CHECKED,
            snapshot_version=VERSION,
        )
        provenance[field] = entry.model_dump(mode="json")
        metadata[f"{field}_status"] = "not_reported" if field in missing else "available"
        if field not in missing and isinstance(value, (str, int, float, bool)):
            metadata[field] = value
    if case_id == "conflicting-fee" and symbol == "SPY":
        metadata["expense_ratio_pct"] = 0.2
    metadata["field_provenance_json"] = json.dumps(
        provenance, sort_keys=True, separators=(",", ":")
    )
    return GraphEnrichedSource(
        document_id=f"issue99-{symbol.lower()}",
        content=f"Synthetic {symbol} attributed fixture; no observed market claim.",
        metadata=metadata,
        graph_context=GraphContext(
            source_document_id=f"issue99-{symbol.lower()}",
            symbol=symbol,
            etf_name=f"{symbol} synthetic ETF",
            category=None if "category" in missing else category,
            sector_exposures_status="available",
            sector_exposures=[SectorExposure(name="Technology", weight_pct=technology)],
        ),
    )


def run_analysis_case(case: AnalysisCase) -> dict[str, Any]:
    profile = InvestorProfile(
        horizon_years=15,
        risk_tolerance=RiskTolerance(case.risk),
        objective=InvestmentObjective(case.objective),
        max_drawdown_pct=30,
        initial_investment_usd=case.initial_usd,
        recurring_monthly_usd=case.recurring_usd,
        excluded_sectors=case.exclusions,
    )
    sources = [_source(symbol, case.id) for symbol in case.candidate_symbols]
    evidence = select_candidate_evidence(
        profile,
        sources,
        query="Issue 99 fixed synthetic replay",
        checked_at=CHECKED,
        max_age=timedelta(hours=24),
        limit=len(sources),
    )
    actual: dict[str, Any] = {
        "stage": "evidence",
        "status": evidence.status.value,
        "reason": evidence.errors[0] if evidence.errors else None,
        "sources": [
            {
                "symbol": source.metadata["symbol"],
                "source": source.metadata["source"],
                "source_url": source.metadata["source_url"],
                "observed_at": source.metadata["observed_at"],
                "listing_country": source.metadata["listing_country"],
                "currency": source.metadata["currency"],
                "market": source.metadata["market"],
            }
            for source in sources
        ],
        "candidate_symbols": [item.symbol for item in evidence.candidates],
    }
    if evidence.status != "ready" or case.id in EVIDENCE_ONLY_CASE_IDS:
        return actual
    try:
        screening = screen_candidate_evidence(evidence)
    except ScreeningFieldFreshnessError as exc:
        actual.update(
            stage="screening",
            status="blocked",
            reason=exc.code,
            field=exc.citation.field_name,
            symbol=exc.citation.symbol,
        )
        return actual
    except ScreeningContractError:
        actual.update(stage="screening", status="blocked", reason="screening_contract_error")
        return actual
    actual["screening"] = {
        item.symbol: {
            "verdict": item.verdict.value,
            "reasons": [rule.reason_code.value for rule in item.rules],
        }
        for item in screening.candidates
    }
    policy = PortfolioConstructionPolicy(max_position_weight_bps=case.max_position_weight_bps)
    result = construct_model_portfolio(
        PortfolioConstructionInput(
            profile=profile,
            policy_calculation=calculate_policy(profile),
            candidate_evidence=evidence,
            candidate_screening=screening,
            construction_policy=policy,
        )
    )
    actual.update(
        stage="construction",
        status=result.status,
        reason=result.errors[0].code.value if result.errors else None,
        excluded={item.symbol: item.reason_code.value for item in result.excluded_candidates},
        validation={item.name.value: item.passed for item in result.validation.checks},
    )
    if result.draft:
        actual["draft"] = {
            "symbols": [item.symbol for item in result.draft.positions],
            "weights_bps": [item.weight_bps for item in result.draft.positions],
            "initial_cents": [item.initial_usd_cents for item in result.draft.positions],
            "recurring_cents": [item.recurring_usd_cents for item in result.draft.positions],
            "weight_total_bps": result.draft.total_weight_bps,
            "initial_total_cents": result.draft.initial_total_cents,
            "recurring_total_cents": result.draft.recurring_total_cents,
            "sleeve_weight_bps": {
                key.value: value for key, value in result.draft.sleeve_weight_bps.items()
            },
        }
    else:
        actual["draft"] = None
    return actual


def compare_case(case: AnalysisCase, actual: dict[str, Any]) -> list[str]:
    """Compare frozen expectations; any missing or different observation fails the gate."""

    failures = []
    for key, expected in (("stage", case.expected_stage), ("status", case.expected_status)):
        if actual.get(key) != expected:
            failures.append(f"{key}: expected {expected}, actual {actual.get(key)}")
    if case.reason and actual.get("reason") != case.reason:
        failures.append(f"reason: expected {case.reason}, actual {actual.get('reason')}")
    sources = actual.get("sources", [])
    if [item.get("symbol") for item in sources] != case.candidate_symbols:
        failures.append("source symbols/order differ")
    for item in sources:
        symbol = item.get("symbol")
        expected_market, expected_currency, expected_country = EU.get(
            symbol, ("us_market", "USD", "United States")
        )
        if item.get("source") != "yahoo_finance":
            failures.append(f"{symbol} source provider differs")
        if item.get("source_url") != f"https://finance.yahoo.com/quote/{symbol}/":
            failures.append(f"{symbol} source URL differs")
        if item.get("observed_at") != (
            (CHECKED - timedelta(hours=25) if case.id == "stale-document" else OBSERVED).isoformat()
        ):
            failures.append(f"{symbol} observation timestamp differs")
        if (item.get("market"), item.get("currency"), item.get("listing_country")) != (
            expected_market,
            expected_currency,
            expected_country,
        ):
            failures.append(f"{symbol} listing/currency differs")
    if case.id in {"listing-eu-eur", "listing-eu-usd"} and "market" not in str(
        actual.get("reason")
    ):
        failures.append("EU diagnostic did not reject the listing market")
    if case.expected_stage == "construction":
        draft = actual.get("draft")
        if case.expected_status == "blocked" and draft is not None:
            failures.append("blocked case has draft")
        if case.expected_status == "ready":
            if not isinstance(draft, dict):
                failures.append("ready case has no draft")
            else:
                expected_vectors = (
                    ("symbols", case.symbols),
                    ("weights_bps", case.weights_bps),
                    ("initial_cents", case.initial_cents),
                    ("recurring_cents", case.recurring_cents),
                )
                if any(
                    len(values) != len(case.symbols) or not values for _, values in expected_vectors
                ):
                    failures.append("ready case has missing or incomplete frozen vectors")
                for list_key, expected_list in expected_vectors:
                    if draft.get(list_key) != expected_list:
                        failures.append(f"{list_key} differs from frozen expectation")
                cents = round(case.initial_usd * 100), round(case.recurring_usd * 100)
                for total_key, expected_total in (
                    ("weight_total_bps", 10000),
                    ("initial_total_cents", cents[0]),
                    ("recurring_total_cents", cents[1]),
                ):
                    if draft.get(total_key) != expected_total:
                        failures.append(
                            f"{total_key}: expected {expected_total}, actual {draft.get(total_key)}"
                        )
                for sum_key, total in (
                    ("weights_bps", 10000),
                    ("initial_cents", cents[0]),
                    ("recurring_cents", cents[1]),
                ):
                    if sum(draft.get(sum_key, [])) != total:
                        failures.append(f"{sum_key} does not reconcile")
                if actual.get("validation") and not all(actual["validation"].values()):
                    failures.append("production validation failed")
        if actual.get("excluded") != case.excluded:
            failures.append("excluded candidates differ")
    for symbol, expected_reason in case.screening.items():
        if expected_reason not in actual.get("screening", {}).get(symbol, {}).get("reasons", []):
            failures.append(f"{symbol} screening reason differs")
    return failures


def _checked_fixture(name: str, digest: str) -> str:
    raw = files("etf_advisor.evaluation").joinpath(name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise ValueError(f"Frozen {name} digest differs: {actual}")
    return actual


def _retrieval_expectations(case_ids: list[str]) -> dict[str, Any]:
    """Load fixed metric values captured before the repaired evaluator runs."""

    raw = (
        files("etf_advisor.evaluation")
        .joinpath("retrieval_expected_metrics.json")
        .read_text(encoding="utf-8")
    )
    expected: dict[str, Any] = json.loads(raw)
    if (
        expected.get("version") != 1
        or expected.get("retrieval_dataset_version") != 3
        or expected.get("retrieval_dataset_sha256") != RETRIEVAL_SHA
        or expected.get("limit") != 3
        or list(expected.get("cases", {})) != case_ids
        or set(expected.get("aggregate", {})) != {"semantic_only", "graph_enriched", "deltas"}
    ):
        raise ValueError("Frozen retrieval metric expectation identity or case matrix differs.")
    metric_fields = set(RetrievalMetrics.model_fields)
    delta_fields = set(MetricDeltas.model_fields)
    for pair in [*expected["cases"].values(), expected["aggregate"]]:
        if not isinstance(pair, dict) or not {"semantic_only", "graph_enriched"} <= set(pair):
            raise ValueError("Frozen retrieval metric variants are missing.")
        for variant in ("semantic_only", "graph_enriched"):
            values = pair[variant]
            if not isinstance(values, dict) or set(values) != metric_fields:
                raise ValueError("Frozen retrieval metric fields are incomplete.")
            RetrievalMetrics.model_validate(values)
    deltas = expected["aggregate"]["deltas"]
    if not isinstance(deltas, dict) or set(deltas) != delta_fields:
        raise ValueError("Frozen retrieval delta fields are incomplete.")
    MetricDeltas.model_validate(deltas)
    return expected


def _metric_failures(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    failures = []
    for variant, expected_values in expected.items():
        actual_values = actual.get(variant)
        if not isinstance(actual_values, dict):
            failures.append(f"{variant} metrics missing")
            continue
        for field, expected_value in expected_values.items():
            if actual_values.get(field) != expected_value:
                actual_value = actual_values.get(field)
                failures.append(
                    f"{variant}.{field}: expected {expected_value}, actual {actual_value}"
                )
    return failures


def run_analysis_baseline(dataset: AnalysisDataset | None = None) -> dict[str, Any]:
    """Return complete deterministic readout; caller must fail on passed=False."""

    dataset = dataset or load_analysis_dataset()
    retrieval_digest = _checked_fixture("retrieval_baseline.json", RETRIEVAL_SHA)
    explanation_digest = _checked_fixture("explanation_baseline.json", EXPLANATION_SHA)
    retrieval_dataset = load_evaluation_dataset()
    explanation_dataset = load_explanation_evaluation_dataset()
    if retrieval_dataset.version != 3 or explanation_dataset.version != 3:
        raise ValueError("Frozen original dataset version differs")
    retrieval = run_offline_evaluation(retrieval_dataset, limit=3)
    retrieval_expectations = _retrieval_expectations(
        [case.case_id for case in retrieval_dataset.cases]
    )
    explanation = run_offline_explanation_evaluation(explanation_dataset)
    semantic = CuratedSemanticStore(retrieval_dataset)
    graph = HybridRetriever(semantic, CuratedRelationshipStore(retrieval_dataset))
    retrieval_cases = []
    for case in retrieval_dataset.cases:
        semantic_metrics = evaluate_strategy(semantic, [case], limit=3)
        graph_metrics = evaluate_strategy(graph, [case], limit=3)
        retrieved = list(graph.search(case.query, limit=3))
        actual_metrics = {
            "semantic_only": semantic_metrics.model_dump(mode="json"),
            "graph_enriched": graph_metrics.model_dump(mode="json"),
        }
        expected_metrics = retrieval_expectations["cases"][case.case_id]
        failures = _metric_failures(expected_metrics, actual_metrics)
        retrieval_cases.append(
            {
                "id": case.case_id,
                "expected": {
                    "relevant_document_ids": case.relevant_document_ids,
                    "graph_context_ids": [
                        item.source_document_id for item in case.expected_graph_contexts
                    ],
                    "metrics": expected_metrics,
                },
                "actual": {
                    **actual_metrics,
                    "results": [
                        {
                            "document_id": item.document_id,
                            "source": item.metadata.get("source"),
                            "source_url": item.metadata.get("source_url"),
                            "observed_at": item.metadata.get("observed_at"),
                        }
                        for item in retrieved
                    ],
                },
                "passed": not failures,
                "failures": failures,
                "limitation": LIMITATION,
            }
        )
    actual_aggregate = retrieval.model_dump(mode="json")
    aggregate_failures = _metric_failures(retrieval_expectations["aggregate"], actual_aggregate)
    analysis_cases = []
    for analysis_case in dataset.cases:
        actual = run_analysis_case(analysis_case)
        failures = compare_case(analysis_case, actual)
        analysis_cases.append(
            {
                "id": analysis_case.id,
                "expected": analysis_case.model_dump(mode="json"),
                "actual": actual,
                "passed": not failures,
                "failures": failures,
                "limitation": LIMITATION,
            }
        )
    all_count = len(retrieval_cases) + len(explanation.cases) + len(analysis_cases)
    correct = (
        sum(bool(item["passed"]) for item in retrieval_cases)
        + sum(item.passed for item in explanation.cases)
        + sum(bool(item["passed"]) for item in analysis_cases)
    )
    explanation_report = explanation.model_dump(mode="json")
    explanation_sources = [
        {
            "document_id": item.document_id,
            "source": item.source,
            "source_url": item.source_url,
            "observed_at": item.observed_at.isoformat(),
        }
        for item in explanation_dataset.request.candidate_evidence.candidates
    ]
    for result in explanation_report["cases"]:
        result["sources"] = explanation_sources
        result["limitation"] = LIMITATION
    return {
        "dataset_id": dataset.dataset_id,
        "version": dataset.version,
        "fixture_kind": "frozen_offline_replay",
        "analysis_source_provenance": {
            "provider": "yahoo_finance (synthetic attribution only)",
            "base_observed_at": OBSERVED.isoformat(),
            "checked_at": CHECKED.isoformat(),
            "max_source_age_hours": 24,
            "snapshot_version": VERSION,
        },
        "original_datasets": {
            "retrieval": {"version": 3, "sha256": retrieval_digest},
            "explanation": {"version": 3, "sha256": explanation_digest},
        },
        "metrics": {
            "case_count": all_count,
            "correct_count": correct,
            "case_agreement": round(correct / all_count, 6),
        },
        "retrieval": {
            "aggregate": actual_aggregate,
            "expected_aggregate": retrieval_expectations["aggregate"],
            "aggregate_failures": aggregate_failures,
            "cases": retrieval_cases,
        },
        "explanation": explanation_report,
        "analysis": analysis_cases,
        "unmeasured": [
            "live store or Yahoo coverage",
            "embedding/semantic quality beyond frozen rankings",
            "live model explanation quality",
            "future EU eligibility/currency support",
            "investment performance, suitability, returns, overlap and diversification quality",
        ],
        "passed": (
            correct == 37
            and all_count == 37
            and not aggregate_failures
            and explanation.metrics.passed
        ),
    }
