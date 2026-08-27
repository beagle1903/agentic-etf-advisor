"""Offline retrieval fixtures and deterministic comparison metrics."""

from __future__ import annotations

import json
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path
from typing import Protocol

from etf_advisor.evaluation.models import (
    DatasetProvenance,
    EvaluationCase,
    MetricDeltas,
    RetrievalEvaluationDataset,
    RetrievalEvaluationReport,
    RetrievalMetrics,
)
from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, RetrievedSource

_CONTEXT_FIELDS = ("issuer", "category")


class RetrievalStrategy(Protocol):
    """Search boundary used by the evaluator for real or fixture-backed retrieval."""

    def search(self, query: str, limit: int = 5) -> Sequence[RetrievedSource]: ...


class CuratedSemanticStore:
    """Replay versioned semantic rankings without embeddings or network calls."""

    def __init__(self, dataset: RetrievalEvaluationDataset) -> None:
        self._cases = {case.query: case for case in dataset.cases}
        self._documents = {
            item.source_document.document_id: item.source_document for item in dataset.documents
        }

    def search(self, query: str, limit: int = 5) -> list[RetrievedSource]:
        case = self._cases.get(query)
        if case is None:
            raise ValueError(f"Query is not present in the curated evaluation set: {query}")
        return [
            RetrievedSource(
                document_id=candidate.document_id,
                content=self._documents[candidate.document_id].content,
                metadata=self._documents[candidate.document_id].chroma_metadata(),
                distance=candidate.distance,
            )
            for candidate in case.semantic_candidates[:limit]
        ]


class CuratedRelationshipStore:
    """Replay source-linked graph context from the same versioned dataset."""

    def __init__(self, dataset: RetrievalEvaluationDataset) -> None:
        self._contexts = {
            item.source_document.document_id: item.graph_context
            for item in dataset.documents
            if item.graph_context is not None
        }

    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]:
        return {
            document_id: self._contexts[document_id]
            for document_id in document_ids
            if document_id in self._contexts
        }


def load_evaluation_dataset(path: Path | None = None) -> RetrievalEvaluationDataset:
    """Load and validate a JSON evaluation set from disk or the packaged baseline."""

    if path is None:
        resource = files("etf_advisor.evaluation").joinpath("retrieval_baseline.json")
        raw = resource.read_text(encoding="utf-8")
    else:
        raw = path.read_text(encoding="utf-8")
    return RetrievalEvaluationDataset.model_validate(json.loads(raw))


def run_offline_evaluation(
    dataset: RetrievalEvaluationDataset,
    *,
    limit: int = 3,
) -> RetrievalEvaluationReport:
    """Compare semantic-only and source-linked graph-enriched retrieval."""

    if limit < 1:
        raise ValueError("Evaluation limit must be at least 1.")
    semantic_store = CuratedSemanticStore(dataset)
    hybrid_retriever = HybridRetriever(
        semantic_store,
        CuratedRelationshipStore(dataset),
    )
    semantic_metrics = evaluate_strategy(semantic_store, dataset.cases, limit=limit)
    graph_metrics = evaluate_strategy(hybrid_retriever, dataset.cases, limit=limit)
    documents = [item.source_document for item in dataset.documents]
    observed_at = [document.observed_at for document in documents]
    deltas = MetricDeltas(
        **{
            field: _rounded(getattr(graph_metrics, field) - getattr(semantic_metrics, field))
            for field in MetricDeltas.model_fields
        }
    )
    ranking_lift = max(
        abs(deltas.hit_rate_at_k),
        abs(deltas.recall_at_k),
        abs(deltas.mean_reciprocal_rank),
    )
    conclusion = (
        "Graph enrichment adds correctly linked issuer/category context but does not improve "
        "semantic ranking in this baseline. Do not expand the graph schema on ranking-lift "
        "grounds yet."
        if ranking_lift == 0 and deltas.graph_context_field_accuracy > 0
        else "Review the metric deltas before changing retrieval or graph scope."
    )
    return RetrievalEvaluationReport(
        dataset=DatasetProvenance(
            dataset_id=dataset.dataset_id,
            version=dataset.version,
            document_count=len(documents),
            sources=sorted({document.source for document in documents}),
            observation_start=min(observed_at),
            observation_end=max(observed_at),
        ),
        limit=limit,
        semantic_only=semantic_metrics,
        graph_enriched=graph_metrics,
        deltas=deltas,
        conclusion=conclusion,
    )


def evaluate_strategy(
    strategy: RetrievalStrategy,
    cases: list[EvaluationCase],
    *,
    limit: int,
) -> RetrievalMetrics:
    """Score a strategy against explicit relevance and graph-context judgments."""

    hit_sum = 0.0
    recall_sum = 0.0
    reciprocal_rank_sum = 0.0
    result_count = 0
    attributed_result_count = 0
    expected_context_count = 0
    matched_context_count = 0
    expected_field_count = 0
    correct_field_count = 0

    for case in cases:
        results = list(strategy.search(case.query, limit=limit))
        relevant_ids = set(case.relevant_document_ids)
        retrieved_relevant_ids = {
            result.document_id for result in results if result.document_id in relevant_ids
        }
        hit_sum += float(bool(retrieved_relevant_ids))
        recall_sum += len(retrieved_relevant_ids) / len(relevant_ids)
        reciprocal_rank_sum += _reciprocal_rank(results, relevant_ids)
        result_count += len(results)
        attributed_result_count += sum(_has_provenance(result) for result in results)

        result_contexts = {
            result.document_id: result.graph_context
            for result in results
            if isinstance(result, GraphEnrichedSource) and result.graph_context is not None
        }
        for expected in case.expected_graph_contexts:
            expected_context_count += 1
            actual = result_contexts.get(expected.source_document_id)
            if actual is not None and actual.source_document_id == expected.source_document_id:
                matched_context_count += 1
            for field in _CONTEXT_FIELDS:
                expected_field_count += 1
                if actual is not None and getattr(actual, field) == getattr(expected, field):
                    correct_field_count += 1

    case_count = len(cases)
    return RetrievalMetrics(
        case_count=case_count,
        result_count=result_count,
        hit_rate_at_k=_ratio(hit_sum, case_count),
        recall_at_k=_ratio(recall_sum, case_count),
        mean_reciprocal_rank=_ratio(reciprocal_rank_sum, case_count),
        source_attribution_rate=_ratio(attributed_result_count, result_count),
        graph_context_recall=_ratio(matched_context_count, expected_context_count),
        graph_context_field_accuracy=_ratio(correct_field_count, expected_field_count),
    )


def _reciprocal_rank(results: list[RetrievedSource], relevant_ids: set[str]) -> float:
    for rank, result in enumerate(results, start=1):
        if result.document_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def _has_provenance(result: RetrievedSource) -> bool:
    return all(
        isinstance(result.metadata.get(field), str) and bool(str(result.metadata[field]).strip())
        for field in ("source", "source_url", "observed_at")
    )


def _ratio(numerator: float | int, denominator: int) -> float:
    return _rounded(float(numerator) / denominator) if denominator else 0.0


def _rounded(value: float) -> float:
    return round(value, 6)
