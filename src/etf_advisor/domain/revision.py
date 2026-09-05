"""Pure typed review planning and JSON integrity contracts (ADR 0015)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from etf_advisor.domain.construction import PortfolioConstructionPolicy
from etf_advisor.domain.profile import InvestorProfile
from etf_advisor.domain.screening import CandidateScreeningPolicy
from etf_advisor.rag.evidence import MAX_CANDIDATE_LIMIT

STAGES = (
    "validate_profile",
    "retrieve_candidate_evidence",
    "screen_candidates",
    "construct_portfolio",
    "draft_explanation",
    "human_review",
)
ARTIFACTS = (
    "draft_policy",
    "candidate_evidence",
    "candidate_screening",
    "portfolio_construction",
    "draft_explanation",
)
ERRORS = (
    "validation_errors",
    "evidence_errors",
    "screening_errors",
    "construction_errors",
    "explanation_errors",
)
CLASSES = ("profile", "evidence", "screening_policy", "construction_policy", "explanation")
type Stage = Literal[
    "validate_profile",
    "retrieve_candidate_evidence",
    "screen_candidates",
    "construct_portfolio",
    "draft_explanation",
    "human_review",
]
type OperationStage = Literal["retrieve_candidate_evidence", "draft_explanation"]
type Identifier = Annotated[str, Field(min_length=1, max_length=128)]
type Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
type Note = Annotated[str, Field(min_length=1, max_length=2000, pattern=r"\S")]


def digest(value: object) -> str:
    """Hash canonical JSON; reject NaN and non-JSON objects."""
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @field_validator("submitted_at", "created_at", "started_at", "completed_at", check_fields=False)
    @classmethod
    def utc_time(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.utcoffset() is None:
                raise ValueError("Audit timestamps must be timezone-aware.")
            return value.astimezone(UTC)
        return None


class RevisionInputs(Contract):
    profile: InvestorProfile
    screening_policy: CandidateScreeningPolicy
    construction_policy: PortfolioConstructionPolicy
    candidate_limit: int = Field(ge=1, le=MAX_CANDIDATE_LIMIT, strict=True)
    with_evidence: bool = Field(strict=True)
    with_explanation: bool = Field(strict=True)
    explanation_instruction: str = Field(max_length=2000)

    @model_validator(mode="after")
    def dependencies(self) -> RevisionInputs:
        if self.with_explanation and not self.with_evidence:
            raise ValueError("Explanation requires evidence.")
        if self.explanation_instruction and not self.with_explanation:
            raise ValueError("Instruction targets a disabled provider.")
        return self


class ProfileFeedback(Contract):
    kind: Literal["profile"]
    patch: dict[str, JsonValue] = Field(min_length=1)


class EvidenceFeedback(Contract):
    kind: Literal["evidence"]
    refresh: Literal[True]
    candidate_limit: int = Field(ge=1, le=MAX_CANDIDATE_LIMIT, strict=True)


class ScreeningFeedback(Contract):
    kind: Literal["screening_policy"]
    patch: dict[str, JsonValue] = Field(min_length=1)


class ConstructionFeedback(Contract):
    kind: Literal["construction_policy"]
    patch: dict[str, JsonValue] = Field(min_length=1)


class ExplanationFeedback(Contract):
    kind: Literal["explanation"]
    instruction: Note


type Feedback = Annotated[
    ProfileFeedback
    | EvidenceFeedback
    | ScreeningFeedback
    | ConstructionFeedback
    | ExplanationFeedback,
    Field(discriminator="kind"),
]


class ReviewDecision(Contract):
    decision_id: Identifier
    revision_id: Identifier
    action: Literal["approve", "edit", "reject"]
    disposition: Literal["revise", "close"] | None = None
    note: str = Field(default="", max_length=2000)
    feedback: list[Feedback] = Field(default_factory=list, max_length=5)
    submitted_at: datetime

    @model_validator(mode="after")
    def coherent(self) -> ReviewDecision:
        if self.submitted_at.utcoffset() is None:
            raise ValueError("Decision time must be timezone-aware.")
        if self.action == "approve":
            if self.disposition is not None or self.feedback:
                raise ValueError("Approval cannot mutate a draft.")
        elif not self.note.strip():
            raise ValueError("Non-approval requires a reviewer note.")
        elif self.action == "edit" and self.disposition != "revise":
            raise ValueError("Edit requires revise disposition.")
        elif self.action == "reject" and self.disposition is None:
            raise ValueError("Reject requires an explicit disposition.")
        if self.disposition == "revise" and not self.feedback:
            raise ValueError("Revision requires typed feedback.")
        if self.disposition == "close" and self.feedback:
            raise ValueError("Close cannot carry mutation feedback.")
        kinds = [item.kind for item in self.feedback]
        if len(set(kinds)) != len(kinds):
            raise ValueError("Duplicate feedback classes are ambiguous.")
        return self


class RevisionPlan(Contract):
    restart_stage: Stage
    invalidated: list[str]
    feedback_classes: list[str]
    inputs: dict[str, Any]
    planning_digest: Digest


def plan_revision(decision: ReviewDecision, inputs: dict[str, Any]) -> RevisionPlan:
    """Validate every patch against complete inputs before choosing the earliest stage."""
    decision = ReviewDecision.model_validate(decision.model_dump(mode="json"))
    inputs = RevisionInputs.model_validate(inputs).model_dump(mode="json")
    if decision.disposition != "revise":
        raise ValueError("Only revision decisions have a restart plan.")
    updated = dict(inputs)
    for item in decision.feedback:
        if item.kind == "profile":
            updated["profile"] = InvestorProfile.model_validate(
                {**inputs["profile"], **item.patch}
            ).model_dump(mode="json")
        elif item.kind == "evidence":
            updated["candidate_limit"] = item.candidate_limit
        elif item.kind == "screening_policy":
            updated["screening_policy"] = CandidateScreeningPolicy.model_validate(
                {**inputs["screening_policy"], **item.patch}
            ).model_dump(mode="json")
        elif item.kind == "construction_policy":
            updated["construction_policy"] = PortfolioConstructionPolicy.model_validate(
                {**inputs["construction_policy"], **item.patch}
            ).model_dump(mode="json")
        else:
            updated["explanation_instruction"] = item.instruction
        if item.kind != "profile" and not inputs["with_evidence"]:
            raise ValueError("Feedback targets a disabled stage.")
        if item.kind == "explanation" and not inputs["with_explanation"]:
            raise ValueError("Explanation generation is disabled.")
    kinds = sorted((item.kind for item in decision.feedback), key=CLASSES.index)
    index = CLASSES.index(kinds[0])
    content = {
        "restart_stage": STAGES[index],
        "invalidated": [*ARTIFACTS[index:], *ERRORS[index:], "review_decision", "final_message"],
        "feedback_classes": kinds,
        "inputs": updated,
    }
    return RevisionPlan.model_validate({**content, "planning_digest": digest(content)})


class Artifact(Contract):
    artifact_id: Identifier
    digest: Digest
    value: dict[str, Any]

    @model_validator(mode="after")
    def valid_digest(self) -> Artifact:
        if digest(self.value) != self.digest:
            raise ValueError("Artifact digest mismatch.")
        return self


class OperationReceipt(Contract):
    thread_id: Identifier
    revision_id: Identifier
    stage: OperationStage
    attempt: int = Field(ge=1, strict=True)
    operation_id: Identifier
    input_digest: Digest
    status: Literal["started", "succeeded", "failed"]
    output_id: Identifier | None = None
    output_digest: Digest | None = None
    started_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def coherent(self) -> OperationReceipt:
        if self.started_at.utcoffset() is None:
            raise ValueError("Operation time must be timezone-aware.")
        if self.status == "started":
            if self.completed_at is not None or self.output_id or self.output_digest:
                raise ValueError("Started receipt cannot have a result.")
        else:
            if (
                self.completed_at is None
                or self.completed_at.utcoffset() is None
                or self.completed_at < self.started_at
            ):
                raise ValueError("Invalid completion time.")
            if self.status == "succeeded" and not (self.output_id and self.output_digest):
                raise ValueError("Success requires output identity.")
            if self.status == "failed" and (self.output_id or self.output_digest):
                raise ValueError("Failed receipt cannot have a successful output.")
        return self


class RetryRequest(Contract):
    revision_id: Identifier
    operation_id: Identifier
    action: Literal["retry"]


class Revision(Contract):
    revision_id: Identifier
    sequence: int = Field(ge=1, strict=True)
    parent_revision_id: Identifier | None = None
    triggering_decision_id: Identifier | None = None
    review_decision_id: Identifier | None = None
    created_at: datetime
    completed_at: datetime | None = None
    status: str
    inputs: dict[str, Any]
    profile_version_id: Identifier
    profile_digest: Digest
    plan: RevisionPlan | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    receipts: list[OperationReceipt] = Field(default_factory=list)
    operations: dict[OperationStage, Identifier] = Field(default_factory=dict)


class RevisionLedger(Contract):
    thread_id: Identifier
    revisions: list[Revision] = Field(min_length=1)
    artifacts: dict[str, Artifact] = Field(default_factory=dict)
    decisions: dict[str, ReviewDecision] = Field(default_factory=dict)
