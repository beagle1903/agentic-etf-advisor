"""Exact complete retrieval for an explicitly pinned catalogue research scope."""

from __future__ import annotations

from typing import Protocol

from etf_advisor.catalogue.research_scope import (
    CatalogueRequestV1,
    CatalogueScopeV1,
    plan_catalogue_scope,
)
from etf_advisor.encoding import ResearchIntegrityError, document_fingerprint, validate_document
from etf_advisor.rag.models import GraphContext, GraphEnrichedSource, RetrievedSource
from etf_advisor.rag.snapshots import ActiveSnapshotIdentity, SnapshotManifest


class VersionedCatalogue(Protocol):
    def read_version(self, version: str, *, max_bytes: int) -> dict[str, object]: ...


class ExactDocuments(Protocol):
    def document_records(self, document_ids: list[str]) -> dict[str, RetrievedSource]: ...


class ExactGraph(Protocol):
    def active_snapshot_identity(self) -> ActiveSnapshotIdentity | None: ...

    def snapshot_manifest(self, snapshot_version: str) -> SnapshotManifest | None: ...

    def find_contexts(self, document_ids: list[str]) -> dict[str, GraphContext]: ...

    def verify_snapshot(self, snapshot_version: str) -> None: ...


class CatalogueSnapshotReader:
    def __init__(
        self, catalogue: VersionedCatalogue, documents: ExactDocuments, graph: ExactGraph
    ) -> None:
        self._catalogue = catalogue
        self._documents = documents
        self._graph = graph

    def load_catalogue_scope(self, request: CatalogueRequestV1) -> list[GraphEnrichedSource]:
        request = CatalogueRequestV1.model_validate(request.model_dump(mode="json"))
        original = self._catalogue.read_version(
            request.scope.catalogue_version, max_bytes=32 * 1024 * 1024
        )
        resolved = plan_catalogue_scope(original, request.scope.filters, limit=100)
        if resolved != request.scope:
            raise ResearchIntegrityError("catalogue_scope_integrity")
        identity = ActiveSnapshotIdentity(request.snapshot_version, request.snapshot_digest)
        if self._graph.active_snapshot_identity() != identity:
            raise ResearchIntegrityError("projection_integrity")
        manifest = self._graph.snapshot_manifest(request.snapshot_version)
        expected_ids = [
            f"research:{request.snapshot_version}:{request.snapshot_digest}:{member.symbol.lower()}"
            for member in request.scope.members
        ]
        if (
            manifest is None
            or manifest.snapshot_digest != request.snapshot_digest
            or manifest.schema_version != 2
            or manifest.document_count != len(expected_ids)
            or set(manifest.document_ids) != set(expected_ids)
            or set(manifest.fingerprints) != set(expected_ids)
        ):
            raise ResearchIntegrityError("manifest_integrity")
        rows = self._documents.document_records(expected_ids)
        if set(rows) != set(expected_ids):
            raise ResearchIntegrityError("document_integrity")
        contexts = self._graph.find_contexts(expected_ids)
        if set(contexts) != set(expected_ids):
            raise ResearchIntegrityError("graph_context_integrity")
        results: list[GraphEnrichedSource] = []
        for member, document_id in zip(request.scope.members, expected_ids, strict=True):
            row = rows[document_id]
            metadata = row.metadata
            if (
                metadata.get("snapshot_version") != request.snapshot_version
                or metadata.get("snapshot_digest") != request.snapshot_digest
                or metadata.get("universe_id") != "catalogue-research-v1"
                or metadata.get("universe_version") != request.scope.digest
                or metadata.get("advisory_contract") != "us-eu-v1"
                or metadata.get("symbol") != member.symbol
                or metadata.get("listing_exchange") != member.exchange
                or metadata.get("field_provenance_schema_version") != 2
                or contexts[document_id].source_document_id != document_id
                or contexts[document_id].symbol != member.symbol
            ):
                raise ResearchIntegrityError("catalogue_document_identity")
            if (
                validate_document(
                    document_id,
                    row.content,
                    metadata,
                    expected_fingerprint=manifest.fingerprints[document_id],
                )
                != 2
                or document_fingerprint(document_id, row.content, metadata)
                != manifest.fingerprints[document_id]
            ):
                raise ResearchIntegrityError("document_integrity")
            results.append(
                GraphEnrichedSource(
                    document_id=document_id,
                    content=row.content,
                    metadata=metadata,
                    distance=None,
                    graph_context=contexts[document_id],
                )
            )
        self._graph.verify_snapshot(request.snapshot_version)
        if self._graph.active_snapshot_identity() != identity:
            raise ResearchIntegrityError("projection_integrity")
        return results


def validate_scope_against_catalogue(
    scope: CatalogueScopeV1, catalogue: VersionedCatalogue
) -> None:
    """Reusable strict pinned-scope check before a new research job."""
    raw = catalogue.read_version(scope.catalogue_version, max_bytes=32 * 1024 * 1024)
    if plan_catalogue_scope(raw, scope.filters) != scope:
        raise ResearchIntegrityError("catalogue_scope_integrity")
