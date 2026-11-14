"""Independent synthetic expectations for offline starter regression agreement only."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta
from importlib.resources import files
from typing import Any

from etf_advisor.dashboard_overlap import selected_reported_holdings_overlaps
from etf_advisor.domain.construction import (
    PortfolioConstructionInput,
    PortfolioConstructionPolicy,
    construct_model_portfolio,
)
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.encoding import strict_json
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.us_starter import StarterArtifact, StarterRequestV1


def load_starter_dataset() -> dict[str, Any]:
    """Load the separate frozen corpus, without any user/source artifact lookup."""
    dataset: dict[str, Any] = strict_json(
        files("etf_advisor.evaluation")
        .joinpath("starter_baseline.json")
        .read_text(encoding="utf-8")
    )
    if dataset["dataset_version"] != "starter-regression-v1" or len(dataset["cases"]) != 12:
        raise ValueError("Unsupported starter regression corpus.")
    return dataset


def canonical_report(report: dict[str, Any]) -> str:
    return json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)


def case_artifact(dataset: dict[str, Any], case: dict[str, Any]) -> StarterArtifact:
    """Apply only the corpus's explicit controlled field deviations to its fixed pool."""
    payload = deepcopy(dataset["artifact"])
    for change in case.get("field_changes", []):
        record = next(r for r in payload["snapshot"]["records"] if r["symbol"] == change["symbol"])
        record[change["field"]].update(change["update"])
    payload.pop("digest")
    payload["digest"] = hashlib.sha256(canonical_report(payload).encode()).hexdigest()
    return StarterArtifact.model_validate(payload)


def score_starter_case(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Compare every frozen field; unavailable and numeric zero are distinct."""
    return [
        key
        for key in sorted(expected.keys() | actual.keys())
        if key not in expected or key not in actual or expected[key] != actual[key]
    ]


def run_starter_baseline(dataset: dict[str, Any] | None = None) -> dict[str, Any]:
    """Replay embedded prepared evidence through unchanged pure production interfaces."""
    dataset = load_starter_dataset() if dataset is None else dataset
    cases = []
    for case in dataset["cases"]:
        artifact = case_artifact(dataset, case)
        assert artifact.snapshot is not None
        request = StarterRequestV1(
            schema="us-starter-request-v1",
            universe_digest=artifact.universe_digest,
            artifact_digest=artifact.digest,
        )
        profile = InvestorProfile.model_validate(
            {
                **dataset["profile"],
                **case["profile"],
                "starter_request": request.model_dump(mode="json"),
            }
        )
        documents = artifact.snapshot.to_source_documents()
        evidence = select_candidate_evidence(
            profile,
            [
                GraphEnrichedSource(
                    document_id=d.document_id, content=d.content, metadata=d.chroma_metadata()
                )
                for d in documents
            ],
            query="Invented starter regression evidence; not observed Yahoo data",
            checked_at=datetime.fromisoformat(dataset["checked_at"]),
            max_age=timedelta(hours=120),
            future_tolerance=timedelta(minutes=5),
            limit=case["limit"],
            starter_artifact=artifact,
        )
        screening = screen_candidate_evidence(evidence)
        construction = construct_model_portfolio(
            PortfolioConstructionInput(
                profile=profile,
                policy_calculation=calculate_policy(profile),
                candidate_evidence=evidence,
                candidate_screening=screening,
                construction_policy=PortfolioConstructionPolicy(
                    starter_shortlist_algorithm="sleeve-category-feasible-v2"
                ),
            )
        )
        positions = construction.draft.positions if construction.draft else []
        selected_ids = [p.document_id for p in positions]
        pairs = selected_reported_holdings_overlaps(evidence.model_dump(mode="json"), selected_ids)
        actual = {
            "stage": "construction" if evidence.status == "ready" else "evidence",
            "status": construction.status,
            "reason": construction.errors[0].code.value if construction.errors else None,
            "selected_ids": selected_ids,
            "weights_bps": [p.weight_bps for p in positions],
            "initial_cents": [p.initial_usd_cents for p in positions],
            "recurring_cents": [p.recurring_usd_cents for p in positions],
            "pairs": [_pair_expectation(pair) for pair in pairs],
        }
        mismatches = score_starter_case(case["expected"], actual)
        if artifact.digest != case["expected_artifact_digest"]:
            mismatches.append("fixture_artifact_digest")
        selection = construction.starter_selection or {}
        excluded = [item.model_dump(mode="json") for item in construction.excluded_candidates]
        cases.append(
            {
                "case_id": case["case_id"],
                "expected": case["expected"],
                "actual": actual,
                "passed": not mismatches,
                "mismatches": mismatches,
                "counts": {
                    "requested": len(artifact.members),
                    "collected": len(documents),
                    "screened": len(screening.candidates),
                    "eligible": selection.get("usable_count"),
                    "excluded": len(excluded),
                    "shortlisted": len(selection.get("shortlist_ids", [])),
                    "selected": len(positions),
                },
                "shortlist_capacity": case["limit"],
                "source_outcomes": [
                    outcome.model_dump(mode="json") for outcome in artifact.outcomes
                ],
                "evidence_status": evidence.status,
                "screening": screening.model_dump(mode="json"),
                "exclusions": excluded,
                "selection": selection,
                "holdings_diagnostics": pairs,
                "holdings_scope": (
                    "partial reported rows only; percentage points, not portfolio exposure"
                ),
                "evidence_checked_at": evidence.model_dump(mode="json")["checked_at"],
                "artifact_digest": artifact.digest,
            }
        )
    failures = sum(not case["passed"] for case in cases)
    return {
        "dataset_version": dataset["dataset_version"],
        "corpus_sha256": hashlib.sha256(canonical_report(dataset).encode()).hexdigest(),
        "limitations": dataset["limitations"],
        "passed": failures == 0,
        "failed_cases": failures,
        "cases": cases,
    }


def _pair_expectation(pair: dict[str, Any]) -> dict[str, Any]:
    return {
        "left_id": pair["left"]["document_id"],
        "right_id": pair["right"]["document_id"],
        "status": pair["status"],
        "reason_codes": pair["reason_codes"],
        "overlap_pp": pair["overlap_pp"],
        "left_row_sum_pp": pair["left"]["row_sum_pp"],
        "right_row_sum_pp": pair["right"]["row_sum_pp"],
    }
