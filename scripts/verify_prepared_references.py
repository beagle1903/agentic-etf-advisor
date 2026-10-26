"""Offline, read-only check of a detached Issue 121 preparation dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from etf_advisor.data.reference_facts import REFERENCE_NAMES, load_reference_facts
from etf_advisor.data.research_quality import assess_research_fields
from etf_advisor.domain.construction import PortfolioConstructionInput, construct_model_portfolio
from etf_advisor.domain.policy import calculate_policy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import screen_candidate_evidence
from etf_advisor.rag.evidence import select_candidate_evidence
from etf_advisor.rag.models import GraphEnrichedSource
from etf_advisor.research.models import ETFResearchSnapshot

MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024
FROZEN_LISTINGS = {("VTI", "PCX"), ("BND", "NMS"), ("VEA", "PCX"), ("VWO", "PCX")}


def summarize(reference: Path, snapshot: Path, checked_at: datetime) -> dict[str, Any]:
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("Check time must be timezone-aware.")
    with snapshot.open("rb") as source:
        payload = source.read(MAX_SNAPSHOT_BYTES + 1)
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Detached snapshot exceeds 16 MiB.")
    parsed = ETFResearchSnapshot.model_validate_json(payload)
    if parsed.advisory_contract != "us-eu-v1" or parsed.schema_version != 2:
        raise ValueError("Expected a detached US/EU schema-2 snapshot.")
    references = load_reference_facts(reference, [symbol for symbol, _ in sorted(FROZEN_LISTINGS)])
    if set(references.records) != FROZEN_LISTINGS:
        raise ValueError("Reference file differs from the frozen four listings.")
    observed = {record.symbol for record in parsed.records}
    if not observed <= {symbol for symbol, _ in references.records}:
        raise ValueError("Snapshot contains a symbol outside the supplied references.")
    health = assess_research_fields(
        parsed,
        checked_at=checked_at,
        max_age=timedelta(hours=120),
        future_tolerance=timedelta(minutes=5),
    )
    profile = InvestorProfile(
        advisory_contract="us-eu-v1",
        base_currency="USD",
        horizon_years=12,
        risk_tolerance="moderate",
        objective="balanced",
        max_drawdown_pct=25,
        initial_investment_minor=100_000,
        recurring_monthly_minor=25_000,
    )
    sources = [
        GraphEnrichedSource(
            document_id=doc.document_id, content=doc.content, metadata=doc.metadata, distance=0.1
        )
        for doc in parsed.to_source_documents()
    ]
    evidence = select_candidate_evidence(
        profile,
        sources,
        query="detached reference preparation",
        checked_at=checked_at,
        max_age=timedelta(hours=120),
        limit=10,
    )
    result: dict[str, Any] = {
        "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "snapshot_sha256": hashlib.sha256(payload).hexdigest(),
        "snapshot_digest": parsed.content_digest(),
        "checked_at": checked_at.isoformat(),
        "reference_listings": len(references.records),
        "reference_fields_available": sum(
            getattr(record, name).value is not None
            for record in references.records.values()
            for name in REFERENCE_NAMES
        ),
        "snapshot_symbols": [record.symbol for record in parsed.records],
        "field_health_current": sum(item.status == "current" for item in health.observations),
        "field_health_total": len(health.observations),
        "evidence_status": evidence.status,
        "screening": [],
        "construction_status": "not_evaluated",
        "construction_reasons": [],
        "position_count": 0,
    }
    if evidence.status == "ready":
        screening = screen_candidate_evidence(evidence)
        result["screening"] = [
            {
                "symbol": item.symbol,
                "verdict": item.verdict,
                "category": next(
                    (
                        record.category.value
                        for record in parsed.records
                        if record.symbol == item.symbol
                    ),
                    None,
                ),
            }
            for item in screening.candidates
        ]
        construction = construct_model_portfolio(
            PortfolioConstructionInput(
                profile=profile,
                policy_calculation=calculate_policy(profile),
                candidate_evidence=evidence,
                candidate_screening=screening,
            )
        )
        result["construction_status"] = construction.status
        result["construction_reasons"] = [error.code for error in construction.errors]
        result["position_count"] = len(construction.draft.positions) if construction.draft else 0
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--checked-at", required=True)
    args = parser.parse_args()
    result = summarize(args.reference, args.snapshot, datetime.fromisoformat(args.checked_at))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
