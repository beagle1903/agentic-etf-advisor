"""Pure, bounded curator Fund proof and immutable registry validation."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from etf_advisor.domain.us_eu import valid_isin
from etf_advisor.encoding import strict_json

IDENTITY_CONTRACT = "curator-fund-v1"
REGISTRY_PROVIDER = "audited_curator_registry_v1"
MAX_REGISTRY_BYTES = 128 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
UTC_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _uuid(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("registry UUID must be text")
    parsed = UUID(value)
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("registry UUID must be canonical lowercase v4")
    return value


def valid_key(value: str, registry_id: str | None = None) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.split(":")
    if len(parts) != 3 or parts[0] != IDENTITY_CONTRACT:
        return False
    try:
        _uuid(parts[1])
        _uuid(parts[2])
    except ValueError:
        return False
    return registry_id is None or parts[1] == registry_id


def new_key(registry_id: str, identifier: str) -> str:
    """Construct a key through the caller's injected identifier boundary."""
    _uuid(registry_id)
    _uuid(identifier)
    return f"{IDENTITY_CONTRACT}:{registry_id}:{identifier}"


def _sorted_unique(values: list[str], *, allow_empty: bool = True) -> list[str]:
    if (not allow_empty and not values) or values != sorted(set(values)):
        raise ValueError("registry references must be sorted, unique and complete")
    return values


def _context_key(context: Context) -> bytes:
    return canonical_bytes(context.model_dump(mode="json"))


def _contexts_sorted(values: list[Any], attribute: str = "context") -> bool:
    keys = [_context_key(getattr(item, attribute)) for item in values]
    return keys == sorted(set(keys))


def _diagnostic(context: Context) -> str:
    text = " ".join(
        filter(
            None, (context.issuer_legal_name, context.umbrella_legal_name, context.fund_legal_name)
        )
    )
    return "".join(
        char for char in unicodedata.normalize("NFKC", text).casefold() if char.isalnum()
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)

    @model_validator(mode="before")
    @classmethod
    def bound_text(cls, value: Any) -> Any:
        def visit(item: Any) -> None:
            if isinstance(item, str) and len(item) > 1000:
                raise ValueError("registry text limit exceeded")
            if isinstance(item, dict):
                for child in item.values():
                    visit(child)
            elif isinstance(item, list):
                for child in item:
                    visit(child)

        visit(value)
        return value


class Actor(StrictModel):
    identity: str = Field(min_length=1)
    role: str = Field(min_length=1)
    authorization_reference: str = Field(min_length=1)
    review_disposition: str = Field(min_length=1)


class Source(StrictModel):
    id: str = Field(min_length=1)
    authority: Literal["issuer", "exchange"]
    provider: str = Field(min_length=1)
    url: str = Field(min_length=1)
    body_sha256: str
    locator: str = Field(min_length=1)
    observed_at: datetime
    collected_at: datetime
    effective_date: date | None
    published_at: datetime | None
    publication_date: date | None
    current_applicability: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def official_url_shape(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("registry source requires HTTPS URL")
        return value

    @field_validator("body_sha256")
    @classmethod
    def body_digest(cls, value: str) -> str:
        if SHA.fullmatch(value) is None:
            raise ValueError("invalid source digest")
        return value

    @field_validator("observed_at", "collected_at", "published_at", mode="before")
    @classmethod
    def timestamp(cls, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime) and value.utcoffset() == timedelta(0):
            return value
        if not isinstance(value, str) or UTC_INSTANT.fullmatch(value) is None:
            raise ValueError("registry timestamps require canonical UTC instants")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @field_validator("effective_date", "publication_date", mode="before")
    @classmethod
    def calendar_date(cls, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
            raise ValueError("registry date must use YYYY-MM-DD")
        return date.fromisoformat(value)

    @model_validator(mode="after")
    def chronology(self) -> Source:
        if self.collected_at < self.observed_at:
            raise ValueError("source collection precedes observation")
        if self.published_at is not None and self.published_at > self.observed_at:
            raise ValueError("source publication follows observation")
        return self


class Context(StrictModel):
    issuer_legal_name: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    umbrella_legal_name: str | None
    fund_legal_name: str = Field(min_length=1)


class Assertion(StrictModel):
    context: Context
    source_ids: list[str]

    @field_validator("source_ids")
    @classmethod
    def ordered_sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, allow_empty=False)


class MembershipAssertion(Assertion):
    isin: str

    @field_validator("isin")
    @classmethod
    def isin_checksum(cls, value: str) -> str:
        if not valid_isin(value):
            raise ValueError("invalid class ISIN")
        return value


class ContextLink(StrictModel):
    from_context: Context
    to_context: Context
    source_ids: list[str]

    @field_validator("source_ids")
    @classmethod
    def ordered_sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, allow_empty=False)


class CurrentProof(StrictModel):
    fund: Assertion
    inventory: Assertion
    memberships: list[MembershipAssertion]
    current_context_links: list[ContextLink]
    lineage_source_ids: list[str]

    @field_validator("lineage_source_ids")
    @classmethod
    def ordered_sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value)

    @model_validator(mode="after")
    def ordered_assertions(self) -> CurrentProof:
        ids = [item.isin for item in self.memberships]
        if ids != sorted(set(ids)):
            raise ValueError("membership proofs must be sorted and unique")
        links = [
            (
                canonical_bytes(item.from_context.model_dump(mode="json")),
                canonical_bytes(item.to_context.model_dump(mode="json")),
            )
            for item in self.current_context_links
        ]
        if links != sorted(set(links)):
            raise ValueError("current-context links must be sorted and unique")
        return self


class Alias(Assertion):
    pass


class Member(StrictModel):
    isin: str
    status: Literal["active", "authorized", "closed", "unknown"]
    source_ids: list[str]

    @field_validator("isin")
    @classmethod
    def isin_checksum(cls, value: str) -> str:
        if not valid_isin(value):
            raise ValueError("invalid class ISIN")
        return value

    @field_validator("source_ids")
    @classmethod
    def ordered_sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, allow_empty=False)


class Fund(StrictModel):
    key: str
    status: Literal["active", "suspended", "retired"]
    context: Context
    current_proof: CurrentProof
    aliases: list[Alias]
    members: list[Member]
    lifecycle_source_ids: list[str]
    related_keys: list[str]

    @field_validator("lifecycle_source_ids", "related_keys")
    @classmethod
    def ordered_refs(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value)

    @model_validator(mode="after")
    def ordered_entries(self) -> Fund:
        ids = [member.isin for member in self.members]
        if ids != sorted(set(ids)) or not _contexts_sorted(self.aliases):
            raise ValueError("Fund members or aliases must be sorted and unique")
        if self.current_proof.fund.context != self.context:
            raise ValueError("current Fund proof context mismatch")
        active = {member.isin for member in self.members if member.status == "active"}
        proved = {member.isin for member in self.current_proof.memberships}
        if self.status == "active" and (not active or active != proved):
            raise ValueError("active memberships require exact current proof")
        return self


def _active_fund_uses_context(fund: Fund, context: Context) -> bool:
    if fund.status != "active":
        return False
    proof = fund.current_proof
    return (
        fund.context == context
        or any(alias.context == context for alias in fund.aliases)
        or proof.inventory.context == context
        or any(item.context == context for item in proof.memberships)
        or any(item.from_context == context for item in proof.current_context_links)
    )


class Comparison(StrictModel):
    left_key: str
    right_key: str
    disposition: Literal["same", "distinct", "unresolved"]
    source_ids: list[str]

    @field_validator("source_ids")
    @classmethod
    def ordered_sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, allow_empty=False)


class Transition(StrictModel):
    key: str
    before_digest: str | None
    after_digest: str
    operations: list[
        Literal["issue", "refresh", "rename", "membership", "suspend", "retire", "succession"]
    ]
    source_ids: list[str]

    @field_validator("source_ids")
    @classmethod
    def ordered_sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, allow_empty=False)

    @model_validator(mode="after")
    def validate_transition(self) -> Transition:
        if self.operations != sorted(set(self.operations)) or not self.operations:
            raise ValueError("transition operations must be sorted and nonempty")
        for value in (self.before_digest, self.after_digest):
            if value is not None and SHA.fullmatch(value) is None:
                raise ValueError("invalid transition entry digest")
        return self


class InventoryRow(StrictModel):
    key: str | None
    isin: str | None
    source_locator: str = Field(min_length=1)
    before_status: Literal["active", "authorized", "closed", "unknown"] | None
    after_status: Literal["active", "authorized", "closed", "unknown"] | None
    disposition: Literal["unchanged", "added", "closed", "changed", "unresolved"]
    source_ids: list[str]

    @field_validator("source_ids")
    @classmethod
    def ordered_sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, allow_empty=False)

    @model_validator(mode="after")
    def validate_row(self) -> InventoryRow:
        if self.isin is not None and not valid_isin(self.isin):
            raise ValueError("invalid inventory ISIN")
        if self.disposition == "unchanged" and self.before_status != self.after_status:
            raise ValueError("unchanged inventory row changes status")
        if self.disposition == "added" and (
            self.before_status is not None or self.after_status is None
        ):
            raise ValueError("added inventory row is incomplete")
        if self.disposition == "closed" and self.after_status != "closed":
            raise ValueError("closed inventory row lacks closure")
        return self


class InventoryCheck(StrictModel):
    context: Context
    source_ids: list[str]
    rows: list[InventoryRow]

    @field_validator("source_ids")
    @classmethod
    def ordered_sources(cls, value: list[str]) -> list[str]:
        return _sorted_unique(value, allow_empty=False)

    @model_validator(mode="after")
    def ordered_rows(self) -> InventoryCheck:
        keys = [(row.key or "", row.isin or "", row.source_locator) for row in self.rows]
        if keys != sorted(set(keys)):
            raise ValueError("inventory rows must be sorted and unique")
        return self


class Audit(StrictModel):
    curator: Actor
    reviewer: Actor
    attested_at: datetime
    compared_parent_digest: str | None
    comparisons: list[Comparison]
    transitions: list[Transition]
    inventory_checks: list[InventoryCheck]

    @field_validator("attested_at", mode="before")
    @classmethod
    def timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime) and value.utcoffset() == timedelta(0):
            return value
        if not isinstance(value, str) or UTC_INSTANT.fullmatch(value) is None:
            raise ValueError("attestation requires canonical UTC instant")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @model_validator(mode="after")
    def independent(self) -> Audit:
        if self.curator.identity == self.reviewer.identity:
            raise ValueError("curator and reviewer must be distinct")
        if (
            self.curator.role != "curator"
            or self.reviewer.role != "reviewer"
            or self.curator.review_disposition != "approve"
            or self.reviewer.review_disposition != "approve"
        ):
            raise ValueError(
                "registry publication requires curator and independent reviewer approval"
            )
        pairs = [(item.left_key, item.right_key) for item in self.comparisons]
        keys = [item.key for item in self.transitions]
        contexts = [_context_key(item.context) for item in self.inventory_checks]
        if (
            pairs != sorted(set(pairs))
            or keys != sorted(set(keys))
            or contexts != sorted(set(contexts))
        ):
            raise ValueError("audit arrays must be sorted and unique")
        return self


class RegistrySnapshot(StrictModel):
    schema_version: Literal[1]
    policy: Literal["curator-fund-v1"]
    registry_id: str
    generation: int = Field(gt=0)
    parent_digest: str | None
    recorded_at: datetime
    sources: list[Source] = Field(max_length=256)
    funds: list[Fund] = Field(max_length=32)
    audit: Audit

    @field_validator("registry_id")
    @classmethod
    def uuid(cls, value: str) -> str:
        return _uuid(value)

    @field_validator("recorded_at", mode="before")
    @classmethod
    def timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime) and value.utcoffset() == timedelta(0):
            return value
        if not isinstance(value, str) or UTC_INSTANT.fullmatch(value) is None:
            raise ValueError("registry record requires canonical UTC instant")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @model_validator(mode="after")
    def internal_integrity(self) -> RegistrySnapshot:
        if self.parent_digest is not None and SHA.fullmatch(self.parent_digest) is None:
            raise ValueError("invalid parent digest")
        if (self.generation == 1) != (self.parent_digest is None):
            raise ValueError("generation/parent mismatch")
        if self.audit.compared_parent_digest != self.parent_digest:
            raise ValueError("audit parent mismatch")
        if self.audit.attested_at > self.recorded_at or any(
            source.collected_at > self.recorded_at for source in self.sources
        ):
            raise ValueError("registry recording precedes source collection or attestation")
        if len(canonical_bytes(self.model_dump(mode="json"))) > MAX_REGISTRY_BYTES:
            raise ValueError("registry snapshot exceeds 128 KiB")
        source_ids = [source.id for source in self.sources]
        fund_keys = [fund.key for fund in self.funds]
        if source_ids != sorted(set(source_ids)) or fund_keys != sorted(set(fund_keys)):
            raise ValueError("sources and Funds must be sorted and unique")
        if sum(len(fund.members) for fund in self.funds) > 256:
            raise ValueError("registry member limit exceeded")
        if any(not valid_key(key, self.registry_id) for key in fund_keys):
            raise ValueError("Fund key does not match registry")
        by_key = {fund.key: fund for fund in self.funds}
        sources = set(source_ids)

        def refs(values: list[str], *, required: bool = False) -> None:
            if (required and not values) or not set(values) <= sources:
                raise ValueError("unresolved or missing registry source")

        active_isins: set[str] = set()
        contexts: set[bytes] = set()
        for fund in self.funds:
            refs(fund.lifecycle_source_ids)
            if not set(fund.related_keys) <= set(fund_keys) or fund.key in fund.related_keys:
                raise ValueError("invalid related Fund keys")
            for alias in fund.aliases:
                refs(alias.source_ids, required=True)
            for member in fund.members:
                refs(member.source_ids, required=True)
                if fund.status == "active" and member.status == "active":
                    if member.isin in active_isins:
                        raise ValueError("active ISIN belongs to multiple Funds")
                    active_isins.add(member.isin)
            proof = fund.current_proof
            refs(proof.fund.source_ids, required=fund.status == "active")
            refs(proof.inventory.source_ids, required=fund.status == "active")
            refs(proof.lineage_source_ids)
            if fund.status == "active":
                context_key = _context_key(fund.context)
                if context_key in contexts:
                    raise ValueError("duplicate active legal Fund context")
                contexts.add(context_key)
            required_links = {
                _context_key(item.context)
                for item in [proof.inventory, *proof.memberships]
                if item.context != fund.context
            }
            actual_links = {_context_key(item.from_context) for item in proof.current_context_links}
            if fund.status == "active" and required_links != actual_links:
                raise ValueError("current assertion context requires exact link")
            for assertion in proof.memberships:
                refs(assertion.source_ids, required=True)
            for link in proof.current_context_links:
                refs(link.source_ids, required=True)
                if link.to_context != fund.context or link.from_context == fund.context:
                    raise ValueError("invalid current context link")
        for comparison in self.audit.comparisons:
            refs(comparison.source_ids, required=True)
            if (
                comparison.left_key not in by_key
                or comparison.right_key not in by_key
                or comparison.left_key >= comparison.right_key
            ):
                raise ValueError("invalid comparison pair")
            if (
                comparison.disposition != "distinct"
                and by_key[comparison.left_key].status
                == by_key[comparison.right_key].status
                == "active"
            ):
                raise ValueError("unresolved same-Fund collision")
        for transition in self.audit.transitions:
            refs(transition.source_ids, required=True)
            if transition.key not in by_key:
                raise ValueError("transition key is unknown")
            if transition.after_digest != digest(by_key[transition.key].model_dump(mode="json")):
                raise ValueError("transition after digest differs from bound Fund")
        for check in self.audit.inventory_checks:
            refs(check.source_ids, required=True)
            for row in check.rows:
                refs(row.source_ids, required=True)
                if row.source_locator not in {
                    source.locator for source in self.sources if source.id in row.source_ids
                }:
                    raise ValueError("inventory row locator lacks source backing")
                if row.key is not None and row.key not in by_key:
                    raise ValueError("inventory key is unknown")
                if (row.key is None or row.isin is None) and row.disposition != "unresolved":
                    raise ValueError("unmapped inventory row must be unresolved")
                if row.key is not None and row.isin is not None:
                    fund = by_key[row.key]
                    matched_member = next(
                        (item for item in fund.members if item.isin == row.isin), None
                    )
                    expected = (
                        matched_member.status
                        if fund.context == check.context and matched_member is not None
                        else None
                    )
                    if row.after_status != expected:
                        raise ValueError("inventory after status differs from bound Fund")
                if row.disposition == "unresolved" and (
                    (row.key is not None and by_key[row.key].status == "active")
                    or any(_active_fund_uses_context(fund, check.context) for fund in self.funds)
                ):
                    raise ValueError("unresolved inventory cannot leave Fund active")
        return self


class RegistryEnvelope(StrictModel):
    digest: str
    snapshot: RegistrySnapshot

    @model_validator(mode="after")
    def verify_digest(self) -> RegistryEnvelope:
        if self.digest != digest(self.snapshot.model_dump(mode="json")):
            raise ValueError("registry digest mismatch")
        return self

    @classmethod
    def from_json(cls, text: str) -> RegistryEnvelope:
        return cls.model_validate(strict_json(text))


def current_sources(
    envelope: RegistryEnvelope, key: str, checked_at: datetime
) -> tuple[Source, ...]:
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("proof check time must be UTC aware")
    if checked_at.utcoffset() != timedelta(0):
        raise ValueError("proof check time must be UTC")
    fund = next((item for item in envelope.snapshot.funds if item.key == key), None)
    if fund is None or fund.status != "active":
        raise ValueError("Fund is not active in bound registry")
    proof = fund.current_proof
    ids = set(proof.fund.source_ids) | set(proof.inventory.source_ids)
    ids.update(source_id for item in proof.memberships for source_id in item.source_ids)
    ids.update(source_id for item in proof.current_context_links for source_id in item.source_ids)
    if not ids:
        raise ValueError("current Fund proof is empty")
    lookup = {source.id: source for source in envelope.snapshot.sources}
    current = tuple(lookup[source_id] for source_id in sorted(ids))
    for source in current:
        if (
            not checked_at - timedelta(hours=120)
            <= source.observed_at
            <= checked_at + timedelta(minutes=5)
        ):
            raise ValueError("current Fund proof is stale or future")
    return current


def resolve_group(
    envelope: RegistryEnvelope, key: str, isin: str, checked_at: datetime
) -> datetime:
    if not valid_key(key, envelope.snapshot.registry_id) or not valid_isin(isin):
        raise ValueError("invalid curator Fund/class identity")
    fund = next((item for item in envelope.snapshot.funds if item.key == key), None)
    if (
        fund is None
        or fund.status != "active"
        or not any(member.isin == isin and member.status == "active" for member in fund.members)
    ):
        raise ValueError("class is not active in bound Fund")
    return min(source.observed_at for source in current_sources(envelope, key, checked_at))


def validate_publication(
    envelope: RegistryEnvelope,
    parent: RegistryEnvelope | None,
    *,
    expected_parent_digest: str | None,
    checked_at: datetime,
) -> None:
    """Validate candidate changes against the actual retained parent before CAS."""
    if checked_at.tzinfo is None or checked_at.utcoffset() != timedelta(0):
        raise ValueError("registry publication check time must be UTC")
    snapshot = envelope.snapshot
    if expected_parent_digest != (parent.digest if parent else None):
        raise ValueError("stale registry parent CAS")
    if snapshot.parent_digest != expected_parent_digest:
        raise ValueError("candidate parent digest mismatch")
    if snapshot.generation != (parent.snapshot.generation + 1 if parent else 1):
        raise ValueError("registry generation is not consecutive")
    if parent is not None and snapshot.registry_id != parent.snapshot.registry_id:
        raise ValueError("registry lineage changed")
    if parent is not None and snapshot.recorded_at < parent.snapshot.recorded_at:
        raise ValueError("registry recording precedes actual parent")
    if snapshot.recorded_at > checked_at + timedelta(minutes=5):
        raise ValueError("future registry generation")
    if snapshot.audit.attested_at > checked_at + timedelta(minutes=5):
        raise ValueError("future registry attestation")
    previous = {fund.key: fund for fund in parent.snapshot.funds} if parent else {}
    proposed = {fund.key: fund for fund in snapshot.funds}
    if not set(previous) <= set(proposed):
        raise ValueError("retained Fund/tombstone deleted")
    prior_sources = {source.id: source for source in parent.snapshot.sources} if parent else {}
    next_sources = {source.id: source for source in snapshot.sources}
    for source_id, source in prior_sources.items():
        if next_sources.get(source_id) != source:
            raise ValueError("retained source edited or deleted")
    changed = {
        key for key, fund in proposed.items() if key not in previous or fund != previous[key]
    }
    transitions = {item.key: item for item in snapshot.audit.transitions}
    if set(transitions) != changed:
        raise ValueError("transition coverage differs from actual Fund changes")
    for key in changed:
        before, after = previous.get(key), proposed[key]
        event = transitions[key]
        if event.before_digest != (digest(before.model_dump(mode="json")) if before else None):
            raise ValueError("transition before digest differs from actual parent")
        if event.after_digest != digest(after.model_dump(mode="json")):
            raise ValueError("transition after digest differs from candidate")
        required: set[str] = set()
        if before is None:
            required.add("issue")
        else:
            if before.status == "retired" and after.status != "retired":
                raise ValueError("retired Fund reactivated")
            if before.status == "suspended" and after.status == "active":
                raise ValueError("suspended Fund reactivation is not authorized")
            if before.context != after.context:
                required.add("rename")
                if not any(alias.context == before.context for alias in after.aliases):
                    raise ValueError("rename omitted former-context alias")
                if not after.current_proof.lineage_source_ids:
                    raise ValueError("rename lacks continuity evidence")
            if before.status != after.status:
                required.add("retire" if after.status == "retired" else "suspend")
            if before.members != after.members:
                required.add("membership")
            if before.related_keys != after.related_keys:
                required.add("succession")
            if not required:
                required.add("refresh")
            if not set(before.lifecycle_source_ids) <= set(after.lifecycle_source_ids):
                raise ValueError("historical Fund source deleted")
            if not set(before.current_proof.lineage_source_ids) <= set(
                after.current_proof.lineage_source_ids
            ):
                raise ValueError("historical lineage source deleted")
            before_aliases = {canonical_bytes(a.model_dump(mode="json")) for a in before.aliases}
            after_aliases = {canonical_bytes(a.model_dump(mode="json")) for a in after.aliases}
            if not before_aliases <= after_aliases:
                raise ValueError("historical alias changed or deleted")
            old_members = {member.isin: member for member in before.members}
            new_members = {member.isin: member for member in after.members}
            if not set(old_members) <= set(new_members):
                raise ValueError("historical class removed")
            for isin, old in old_members.items():
                if not set(old.source_ids) <= set(new_members[isin].source_ids):
                    raise ValueError("historical class source removed")
        if set(event.operations) != required:
            raise ValueError("transition operations differ from actual change")
        if "succession" in required and (
            not after.related_keys
            or not event.source_ids
            or any(related not in transitions for related in after.related_keys)
        ):
            raise ValueError("succession lacks affected transitions")
    # Every new key needs a source-backed disposition against every retained/new key.
    new_keys = set(proposed) - set(previous)
    pairs = {
        (left, right)
        for left in proposed
        for right in proposed
        if left < right and (left in new_keys or right in new_keys)
    }
    compared = {(item.left_key, item.right_key): item for item in snapshot.audit.comparisons}
    if not pairs <= set(compared):
        raise ValueError("issuance omitted retained/new Fund comparison")
    for pair in pairs:
        if compared[pair].disposition != "distinct":
            raise ValueError("unresolved Fund issuance comparison")
    touched_contexts = {
        _context_key(fund.context)
        for key in changed
        for fund in (previous.get(key), proposed[key])
        if fund is not None
    }
    checks = {_context_key(item.context): item for item in snapshot.audit.inventory_checks}
    if set(checks) != touched_contexts:
        raise ValueError("inventory coverage differs from touched contexts")
    for context_key, check in checks.items():
        before_rows = {
            (key, member.isin): member.status
            for key, fund in previous.items()
            if _context_key(fund.context) == context_key
            for member in fund.members
        }
        after_rows = {
            (key, member.isin): member.status
            for key, fund in proposed.items()
            if _context_key(fund.context) == context_key
            for member in fund.members
        }
        registered = set(before_rows) | set(after_rows)
        observed = {
            (row.key, row.isin)
            for row in check.rows
            if row.key is not None and row.isin is not None
        }
        if registered != observed or len(observed) != sum(
            row.key is not None and row.isin is not None for row in check.rows
        ):
            raise ValueError("inventory mapped rows differ from touched class rows")
        for row in check.rows:
            if row.key is None or row.isin is None:
                if row.disposition != "unresolved":
                    raise ValueError("unmapped inventory row must be unresolved")
                if any(_active_fund_uses_context(fund, check.context) for fund in snapshot.funds):
                    raise ValueError("unresolved inventory leaves affected Fund active")
                continue
            pair = (row.key, row.isin)
            if row.before_status != before_rows.get(pair) or row.after_status != after_rows.get(
                pair
            ):
                raise ValueError("inventory status contradicts actual parent/candidate")
            if row.disposition == "unresolved" and (
                proposed[row.key].status == "active"
                or any(_active_fund_uses_context(fund, check.context) for fund in snapshot.funds)
            ):
                raise ValueError("unresolved inventory leaves Fund active")
            expected_disposition = (
                "added"
                if row.before_status is None
                else "unchanged"
                if row.before_status == row.after_status
                else "closed"
                if row.after_status == "closed"
                else "changed"
            )
            if row.disposition not in {expected_disposition, "unresolved"}:
                raise ValueError("inventory disposition contradicts actual class transition")
    for fund in snapshot.funds:
        if fund.status == "active":
            current_sources(envelope, fund.key, checked_at)
