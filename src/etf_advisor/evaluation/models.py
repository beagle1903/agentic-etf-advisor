"""JSON-serializable contracts for retrieval evaluation datasets and reports."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from etf_advisor.rag.models import GraphContext, SourceDocument


class EvaluationDocument(BaseModel):
    """One source-attributable document and its curated graph projection."""

    model_config = ConfigDict(extra="forbid")

    source_document: SourceDocument
    graph_context: GraphContext | None = None

    @model_validator(mode="after")
    def validate_graph_link(self) -> EvaluationDocument:
        source_url = urlsplit(self.source_document.source_url)
        if source_url.scheme not in {"http", "https"} or not source_url.netloc:
            raise ValueError("Evaluation documents require an attributable HTTP(S) source URL.")
        if self.source_document.observed_at.tzinfo is None:
            raise ValueError("Evaluation document observation timestamps must be timezone-aware.")
        if (
            self.graph_context is not None
            and self.graph_context.source_document_id != self.source_document.document_id
        ):
            raise ValueError("Graph context must reference its source document ID.")
        return self


class EvaluationCandidate(BaseModel):
    """A deterministic semantic candidate and its recorded distance."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    distance: float | None = Field(default=None, ge=0)


class SectorConstraintJudgment(BaseModel):
    """Expected structured matches for one sector exposure threshold."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    sector: str = Field(min_length=1, max_length=200)
    minimum_weight_pct: float = Field(ge=0, le=100)
    expected_matching_document_ids: list[str] = Field(min_length=1)

    @field_validator("sector")
    @classmethod
    def normalize_sector(cls, value: str) -> str:
        normalized = " ".join(value.replace("_", " ").split())
        if not normalized:
            raise ValueError("Sector constraint names cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_unique_matches(self) -> SectorConstraintJudgment:
        if any(not document_id.strip() for document_id in self.expected_matching_document_ids):
            raise ValueError("Sector constraint document IDs cannot be blank.")
        if len(self.expected_matching_document_ids) != len(
            set(self.expected_matching_document_ids)
        ):
            raise ValueError("Sector constraint judgments cannot repeat document IDs.")
        return self


class EvaluationCase(BaseModel):
    """A query, ranked candidates, and explicit relevance/context judgments."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    semantic_candidates: list[EvaluationCandidate] = Field(min_length=1)
    relevant_document_ids: list[str] = Field(min_length=1)
    expected_graph_contexts: list[GraphContext] = Field(default_factory=list)
    sector_constraint_judgments: list[SectorConstraintJudgment] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_case_ids(self) -> EvaluationCase:
        candidate_ids = [candidate.document_id for candidate in self.semantic_candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"Evaluation case '{self.case_id}' has duplicate candidates.")
        if len(self.relevant_document_ids) != len(set(self.relevant_document_ids)):
            raise ValueError(f"Evaluation case '{self.case_id}' has duplicate relevance IDs.")
        context_ids = [context.source_document_id for context in self.expected_graph_contexts]
        if len(context_ids) != len(set(context_ids)):
            raise ValueError(f"Evaluation case '{self.case_id}' has duplicate context judgments.")
        if not set(context_ids).issubset(self.relevant_document_ids):
            raise ValueError("Graph context judgments must refer to relevant documents.")
        candidate_id_set = set(candidate_ids)
        for judgment in self.sector_constraint_judgments:
            if not set(judgment.expected_matching_document_ids).issubset(candidate_id_set):
                raise ValueError(
                    "Sector constraint judgments must refer to semantic candidate documents."
                )
        return self


class RetrievalEvaluationDataset(BaseModel):
    """Versioned offline inputs shared by both retrieval variants."""

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    documents: list[EvaluationDocument] = Field(min_length=1)
    cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> RetrievalEvaluationDataset:
        document_ids = [item.source_document.document_id for item in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("Evaluation dataset has duplicate document IDs.")
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Evaluation dataset has duplicate case IDs.")
        queries = [case.query for case in self.cases]
        if len(queries) != len(set(queries)):
            raise ValueError("Evaluation dataset has duplicate queries.")

        known_ids = set(document_ids)
        for case in self.cases:
            referenced_ids = {
                *(candidate.document_id for candidate in case.semantic_candidates),
                *case.relevant_document_ids,
                *(context.source_document_id for context in case.expected_graph_contexts),
                *(
                    document_id
                    for judgment in case.sector_constraint_judgments
                    for document_id in judgment.expected_matching_document_ids
                ),
            }
            unknown_ids = sorted(referenced_ids - known_ids)
            if unknown_ids:
                raise ValueError(
                    f"Evaluation case '{case.case_id}' references unknown documents: "
                    f"{', '.join(unknown_ids)}"
                )
        return self


class DatasetProvenance(BaseModel):
    """Compact provenance summary carried into every evaluation report."""

    dataset_id: str
    version: int
    document_count: int
    sources: list[str]
    observation_start: datetime
    observation_end: datetime


class RetrievalMetrics(BaseModel):
    """Deterministic aggregate metrics for one retrieval variant."""

    case_count: int
    result_count: int
    hit_rate_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float
    source_attribution_rate: float
    graph_context_recall: float
    graph_context_field_accuracy: float
    sector_context_coverage: float
    sector_constraint_exact_match_rate: float


class MetricDeltas(BaseModel):
    """Graph-enriched minus semantic-only metric values."""

    hit_rate_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float
    source_attribution_rate: float
    graph_context_recall: float
    graph_context_field_accuracy: float
    sector_context_coverage: float
    sector_constraint_exact_match_rate: float


class RetrievalEvaluationReport(BaseModel):
    """Stable comparison report with no wall-clock dependency."""

    dataset: DatasetProvenance
    limit: int
    semantic_only: RetrievalMetrics
    graph_enriched: RetrievalMetrics
    deltas: MetricDeltas
    conclusion: str
