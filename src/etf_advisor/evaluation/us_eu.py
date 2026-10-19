"""Separate synthetic US/EU contract replay; never a live coverage or returns claim."""

from copy import deepcopy
from datetime import date, datetime, timedelta
from importlib.resources import files
from typing import Any

from etf_advisor.domain.construction import PortfolioConstructionInput, construct_model_portfolio
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.domain.us_eu import FxReferenceObservation
from etf_advisor.encoding import strict_json
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.models import ETFResearchSnapshot


def run_us_eu_baseline() -> dict[str, Any]:
    dataset = strict_json(
        files("etf_advisor.evaluation").joinpath("us_eu_baseline.json").read_text(encoding="utf-8")
    )
    if dataset["dataset_version"] != "us-eu-contract-v1":
        raise ValueError("Unsupported US/EU evaluation version.")
    results = []
    for case in dataset["cases"]:
        payload = deepcopy(dataset["snapshot"])
        records = payload["records"]
        profile = InvestorProfile.model_validate({**dataset["profile"], **case.get("profile", {})})
        fx: FxReferenceObservation | None = FxReferenceObservation.model_validate(
            dataset["fx_reference"]
        )
        scenario = case["scenario"]
        if scenario == "missing_fx":
            fx = None
        elif scenario == "stale_fx":
            fx = FxReferenceObservation.model_validate(
                {
                    **dataset["fx_reference"],
                    "effective_date": date.fromisoformat(dataset["fx_reference"]["effective_date"])
                    - timedelta(days=6),
                }
            )
        elif scenario == "unknown_identity":
            records[0]["economic_group_id"].update(
                value=None, missing_reason="provider_unsupported"
            )
        elif scenario == "duplicate_group":
            records[0]["economic_group_id"]["value"] = records[2]["economic_group_id"]["value"]
        elif scenario == "unsupported_category":
            records[2]["category"]["value"] = "Unsupported European Bond"
        elif scenario == "same_currency":
            records[1]["trading_currency"]["value"] = profile.base_currency
            records[1]["price_unit"]["value"] = profile.base_currency
            fx = None
        elif scenario != "mixed":
            raise ValueError("Unknown US/EU evaluation scenario.")
        documents = ETFResearchSnapshot.model_validate(payload).to_source_documents()
        evidence = select_candidate_evidence(
            profile,
            [
                GraphEnrichedSource(
                    document_id=d.document_id, content=d.content, metadata=d.metadata
                )
                for d in documents
            ],
            query="Synthetic contract replay",
            checked_at=datetime.fromisoformat(dataset["checked_at"]),
            max_age=timedelta(hours=120),
            limit=3,
            fx_reference=fx,
        )
        bundle = construct_model_portfolio(
            PortfolioConstructionInput(
                profile=profile,
                policy_calculation=calculate_policy(profile),
                candidate_evidence=evidence,
                candidate_screening=screen_candidate_evidence(evidence),
            )
        )
        actual = {
            "status": bundle.status,
            "reason": bundle.errors[0].code.value if bundle.errors else None,
        }
        results.append(
            {
                "case_id": case["case_id"],
                "expected": case["expected"],
                "actual": actual,
                "passed": actual == case["expected"],
                "construction": bundle.model_dump(mode="json"),
            }
        )
    return {
        "dataset_version": dataset["dataset_version"],
        "limitations": dataset["limitations"],
        "passed": all(case["passed"] for case in results),
        "cases": results,
    }
