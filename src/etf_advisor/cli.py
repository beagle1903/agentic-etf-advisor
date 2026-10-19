"""Small command-line entry points for testable local development."""

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from importlib.util import find_spec
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import typer
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import ValidationError

from etf_advisor.clock import Clock, system_utc_now
from etf_advisor.config import settings
from etf_advisor.data.ecb_fx import EcbFxClient
from etf_advisor.data.models import ETFObservation
from etf_advisor.data.quality import (
    MarketDataHealthReport,
    MarketDataQualityError,
    assess_observations,
)
from etf_advisor.data.reference_facts import load_reference_facts
from etf_advisor.data.research_quality import assess_research_fields
from etf_advisor.data.vanguard import VanguardHoldingsClient
from etf_advisor.data.yahoo import MarketDataError, YahooFinanceAdapter
from etf_advisor.data.yahoo_research import YahooResearchAdapter
from etf_advisor.encoding import ResearchIntegrityError, integrity_diagnostic
from etf_advisor.evaluation import (
    load_evaluation_dataset,
    load_explanation_evaluation_dataset,
    run_offline_evaluation,
    run_offline_explanation_evaluation,
)
from etf_advisor.evaluation.analysis import load_analysis_dataset, run_analysis_baseline
from etf_advisor.evaluation.us_eu import run_us_eu_baseline
from etf_advisor.explanation.provider import (
    ProviderConfigurationError,
    create_explanation_generator,
)
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.chroma_store import ChromaDocumentStore, ChromaUnavailable
from etf_advisor.rag.evidence import MAX_CANDIDATE_LIMIT, HybridCandidateEvidenceRetriever
from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.indexing import IndexConsistencyError, index_documents
from etf_advisor.rag.neo4j_store import Neo4jGraphStore, Neo4jUnavailable
from etf_advisor.rag.snapshots import (
    ActiveSnapshotIdentity,
    SnapshotPublicationReport,
    publish_research_snapshot,
    verify_snapshot_documents,
)
from etf_advisor.research.models import ETFResearchSnapshot
from etf_advisor.research.snapshot_io import (
    default_snapshot_path,
    load_research_snapshot,
    persist_research_snapshot,
)
from etf_advisor.research.universe import load_research_universe

app = typer.Typer(no_args_is_help=True)
catalogue_app = typer.Typer(
    no_args_is_help=True, help="Local US/EU Yahoo listing catalogue (research only)."
)
app.add_typer(catalogue_app, name="catalogue")


def _catalogue_service() -> Any:
    from etf_advisor.catalogue import CatalogueService, CatalogueStore
    from etf_advisor.catalogue.yahoo import YahooCatalogueProvider

    provider = YahooCatalogueProvider()
    return CatalogueService(CatalogueStore(), provider, provider)


@catalogue_app.command("refresh")
def catalogue_refresh(force: bool = typer.Option(False, help="Bypass 24-hour reuse.")) -> None:
    """Boundedly enumerate all mapped provider partitions and publish only a complete result."""
    from etf_advisor.catalogue import CatalogueError

    try:
        result = _catalogue_service().refresh(force=force)
        typer.echo(json.dumps(result, indent=2))
        if result["status"] not in ("published", "reused"):
            raise typer.Exit(code=1)
    except CatalogueError as exc:
        typer.echo(json.dumps({"status": "failed", "reason": str(exc)}))
        raise typer.Exit(code=1) from exc


@catalogue_app.command("search")
def catalogue_search(
    text: str,
    limit: int = typer.Option(25, min=1, max=100),
    live: bool = typer.Option(False, help="Show non-exhaustive live suggestions."),
) -> None:
    """Search the local combined listing projection; live suggestions never publish."""
    from etf_advisor.catalogue import CatalogueError, CatalogueStore

    try:
        if live:
            result = _catalogue_service().suggestions(text)
        else:
            from etf_advisor.catalogue.service import CatalogueService

            result = CatalogueService(CatalogueStore(), None, None).local_search(text, limit)  # type: ignore[arg-type]
        typer.echo(json.dumps(result, indent=2))
    except CatalogueError as exc:
        typer.echo(json.dumps({"status": "failed", "reason": str(exc)}))
        raise typer.Exit(code=1) from exc


@catalogue_app.command("lookup")
def catalogue_lookup(
    symbol: str, add: bool = typer.Option(False, help="Publish verified direct observation.")
) -> None:
    """Verify one exact Yahoo ETF symbol; optionally add it to the local catalogue."""
    from etf_advisor.catalogue import CatalogueError

    try:
        service = _catalogue_service()
        result = service.add_direct(symbol) if add else service.direct_lookup(symbol)
        typer.echo(json.dumps(result, indent=2))
        verification = result.get("verification")
        rejected = (
            verification.get("verification") == "rejected"
            if isinstance(verification, dict)
            else verification == "rejected"
        )
        if rejected or result.get("publication") == "failed":
            raise typer.Exit(code=1)
    except CatalogueError as exc:
        typer.echo(json.dumps({"status": "failed", "reason": str(exc)}))
        raise typer.Exit(code=1) from exc


@dataclass
class _ResearchFieldObservation:
    """Expose one research field to the shared timestamp quality boundary."""

    symbol: str
    source: str
    source_url: str
    observed_at: datetime


@app.callback()
def main() -> None:
    """Run local Agentic ETF Advisor workflows."""


def _print_state(label: str, state: dict[str, Any]) -> None:
    typer.echo(label)
    # The audit ledger contains the exact checkpoint capability and retained history.
    # Keep it out of demo console output; presentation consumes current artifacts only.
    visible = {key: value for key, value in state.items() if key != "revision_ledger"}
    typer.echo(json.dumps(visible, indent=2, default=str))


def _yahoo_adapter() -> YahooFinanceAdapter:
    return YahooFinanceAdapter(
        max_attempts=settings.yahoo_max_attempts,
        retry_backoff_seconds=settings.yahoo_retry_backoff_seconds,
    )


def _assess_market_data(
    observations: list[ETFObservation],
    *,
    clock: Clock,
) -> MarketDataHealthReport:
    """Capture one injected instant for all observations in a command."""

    return assess_observations(
        observations,
        checked_at=clock(),
        max_age=timedelta(hours=settings.market_data_max_age_hours),
        future_tolerance=timedelta(minutes=settings.market_data_future_tolerance_minutes),
    )


def _assess_research_snapshot(
    snapshot: ETFResearchSnapshot,
    *,
    clock: Clock,
) -> MarketDataHealthReport:
    """Apply the shared freshness boundary to source-reported research timestamps."""

    return assess_research_fields(
        snapshot,
        checked_at=clock(),
        max_age=timedelta(hours=settings.market_data_max_age_hours),
        future_tolerance=timedelta(minutes=settings.market_data_future_tolerance_minutes),
    )


@app.command()
def dashboard(
    port: int = typer.Option(8501, min=1024, max=65535, help="Local Streamlit port."),
) -> None:
    """Start the local profile and human-review dashboard."""

    if find_spec("streamlit") is None:
        typer.echo("Dashboard dependency is missing. Run: uv sync --extra dashboard", err=True)
        raise typer.Exit(code=1)
    app_path = Path(__file__).with_name("dashboard_app.py")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        check=False,
    )
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@app.command()
def demo(
    with_evidence: bool = typer.Option(
        False,
        "--with-evidence",
        help="Retrieve current source evidence from local Chroma and Neo4j before review.",
    ),
    candidate_limit: int = typer.Option(
        5,
        min=1,
        max=MAX_CANDIDATE_LIMIT,
        help="Maximum source-grounded ETF evidence candidates to attach to review.",
    ),
    with_explanation: bool = typer.Option(
        False,
        "--with-explanation",
        help="Generate a provider-backed grounded explanation before human review.",
    ),
) -> None:
    """Run a profile -> evidence -> review -> approval lifecycle."""

    graph_store: Neo4jGraphStore | None = None
    try:
        if with_explanation and not with_evidence:
            raise ProviderConfigurationError("--with-explanation requires --with-evidence.")
        candidate_retriever: HybridCandidateEvidenceRetriever | None = None
        if with_evidence:
            semantic_store = ChromaDocumentStore(
                host=settings.chroma_host,
                port=settings.chroma_port,
                collection_name=settings.chroma_collection,
            )
            graph_store = Neo4jGraphStore(
                uri=settings.neo4j_uri,
                auth=settings.neo4j_credentials(),
            )
            candidate_retriever = HybridCandidateEvidenceRetriever(
                HybridRetriever(semantic_store, graph_store),
                clock=system_utc_now,
                max_age=timedelta(hours=settings.market_data_max_age_hours),
                future_tolerance=timedelta(minutes=settings.market_data_future_tolerance_minutes),
                fx_provider=EcbFxClient(system_utc_now),
            )

        explanation_generator = create_explanation_generator(settings) if with_explanation else None

        graph = build_graph(
            checkpointer=InMemorySaver(),
            candidate_retriever=candidate_retriever,
            candidate_limit=candidate_limit,
            explanation_generator=explanation_generator,
        )
        config = {"configurable": {"thread_id": str(uuid4())}}
        profile = {
            "horizon_years": 12,
            "risk_tolerance": "moderate",
            "objective": "balanced",
            "max_drawdown_pct": 25,
            "initial_investment_usd": 25_000,
            "recurring_monthly_usd": 500,
            "excluded_sectors": [],
        }

        paused = graph.invoke({"profile": profile}, config=config)
        if paused.get("status") != "awaiting_human_review":
            _print_state("Workflow stopped before human review:", paused)
            raise typer.Exit(code=1)
        _print_state("Paused for human review:", paused)

        completed = graph.invoke(
            Command(
                resume={
                    "action": "approve",
                    "decision_id": str(uuid4()),
                    "revision_id": paused["revision_ledger"]["revisions"][-1]["revision_id"],
                    "submitted_at": system_utc_now().isoformat(),
                }
            ),
            config=config,
        )
        _print_state("Resumed after approval:", completed)
    except typer.Exit:
        raise
    except (
        ChromaUnavailable,
        Neo4jUnavailable,
        OSError,
        ProviderConfigurationError,
        RuntimeError,
        ValueError,
    ) as exc:
        typer.echo(f"Demo failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        if graph_store is not None:
            graph_store.close()


@app.command()
def ingest(
    symbols: str = typer.Option(
        "SPY,QQQ,VTI,BND",
        help="Comma-separated symbols to snapshot from Yahoo Finance.",
    ),
    with_graph: bool = typer.Option(
        False,
        "--with-graph",
        help="Also index the same stable source documents and ETF relationships in Neo4j.",
    ),
) -> None:
    """Fetch timestamped Yahoo snapshots and upsert them into local retrieval stores."""

    requested_symbols = [symbol.strip() for symbol in symbols.split(",")]
    graph_store: Neo4jGraphStore | None = None
    try:
        adapter = _yahoo_adapter()
        observations = adapter.fetch(requested_symbols)
        health = _assess_market_data(observations, clock=system_utc_now)
        health.require_healthy()
        documents = [adapter.to_source_document(observation) for observation in observations]
        store = ChromaDocumentStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=settings.chroma_collection,
        )
        if with_graph:
            graph_store = Neo4jGraphStore(
                uri=settings.neo4j_uri,
                auth=settings.neo4j_credentials(),
            )
        report = index_documents(documents, store, graph_store)
    except (
        IndexConsistencyError,
        MarketDataQualityError,
        MarketDataError,
        ChromaUnavailable,
        Neo4jUnavailable,
        OSError,
        RuntimeError,
    ) as exc:
        typer.echo(f"Ingestion failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        if graph_store is not None:
            graph_store.close()

    typer.echo(
        f"Upserted {report.chroma_count} source document(s) into '{settings.chroma_collection}'."
    )
    if with_graph:
        typer.echo(
            f"Indexed {report.neo4j_count} source document(s) and ETF relationships in Neo4j."
        )
    for document in documents:
        typer.echo(
            json.dumps(
                {
                    "document_id": document.document_id,
                    "symbol": document.symbol,
                    "observed_at": document.observed_at.isoformat(),
                    "source_url": document.source_url,
                }
            )
        )


def _publication_diagnostic(stage: str, error: Exception) -> dict[str, str]:
    """Describe a failed publication without exposing provider or store exception text."""

    if isinstance(error, IndexConsistencyError):
        return integrity_diagnostic(ResearchIntegrityError("document_integrity"))
    if isinstance(error, ResearchIntegrityError):
        return integrity_diagnostic(error)
    if isinstance(error, ValidationError):
        integrity_codes = {
            "schema_encoding",
            "numeric_provenance",
            "document_integrity",
            "manifest_integrity",
            "projection_integrity",
            "retrieval_unavailable",
        }
        for item in error.errors(include_url=False):
            context = item.get("ctx")
            cause = context.get("error") if isinstance(context, dict) else None
            if getattr(cause, "code", None) in integrity_codes:
                return integrity_diagnostic(error)
    if isinstance(error, MarketDataQualityError):
        return {
            "code": "market_data_quality",
            "message": "Market-data health check failed. Publish current validated source fields.",
        }
    if stage == "source_fetch" or isinstance(error, MarketDataError):
        return {
            "code": "source_failure",
            "message": "Research source fetch failed. Check provider availability and retry.",
        }
    if stage in {"universe_load", "payload_load", "snapshot_validation"}:
        return {
            "code": "input_validation",
            "message": "Research input validation failed. Check the selected universe or payload.",
        }
    if stage == "payload_save":
        return {
            "code": "local_io_failure",
            "message": "Canonical snapshot payload could not be saved. Check local storage.",
        }
    return {
        "code": "store_failure",
        "message": "Research store operation failed. Check local stores and retry.",
    }


@app.command("publish-research-universe")
def publish_research_universe(
    universe_path: Annotated[
        Path | None,
        typer.Option(
            "--universe",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Optional versioned universe JSON; defaults to the packaged six-ETF baseline.",
        ),
    ] = None,
    snapshot_version: Annotated[
        str | None,
        typer.Option(
            "--snapshot-version",
            help="Explicit version for reproducible reruns; defaults to a UTC timestamp.",
        ),
    ] = None,
    snapshot_file: Annotated[
        Path | None,
        typer.Option(
            "--snapshot-file",
            dir_okay=False,
            help=(
                "Canonical snapshot payload to reuse or create; defaults to an ignored "
                ".artifacts path keyed by snapshot version."
            ),
        ),
    ] = None,
    advisory_contract: Annotated[
        str | None,
        typer.Option("--advisory-contract", help="Explicit opt-in semantic contract: us-eu-v1."),
    ] = None,
    reference_facts: Annotated[
        Path | None,
        typer.Option(
            "--reference-facts",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Attributed local reference facts for fresh us-eu-v1 collection.",
        ),
    ] = None,
) -> None:
    """Fetch, validate, stage, and atomically activate the curated research universe."""

    graph_store: Neo4jGraphStore | None = None
    stage = "graph_connect"
    try:
        if advisory_contract not in (None, "us-eu-v1") or (
            reference_facts is not None and advisory_contract != "us-eu-v1"
        ):
            raise ValueError("Unsupported advisory contract or reference-facts option.")
        version = snapshot_version or system_utc_now().strftime("%Y%m%dT%H%M%SZ")
        payload_path = snapshot_file or default_snapshot_path(version)
        graph_store = Neo4jGraphStore(
            uri=settings.neo4j_uri,
            auth=settings.neo4j_credentials(),
        )
        stage = "graph_lookup"
        active_identity = graph_store.active_snapshot_identity()
        existing_digest = graph_store.snapshot_digest(version)
        if existing_digest is not None:
            requested_identity = ActiveSnapshotIdentity(version, existing_digest)
            if active_identity == requested_identity:
                supplied: ETFResearchSnapshot | None = None
                if payload_path.exists():
                    stage = "payload_load"
                    supplied = load_research_snapshot(payload_path)
                    if (
                        advisory_contract is not None
                        and supplied.advisory_contract != advisory_contract
                    ):
                        raise ValueError("Retry payload advisory contract differs from request.")
                    if (
                        supplied.snapshot_version != version
                        or supplied.content_digest() != existing_digest
                    ):
                        raise IndexConsistencyError(
                            "Active retry payload conflicts with immutable identity."
                        )
                stage = "graph_readback"
                manifest = graph_store.snapshot_manifest(version)
                if manifest is None or (
                    manifest.snapshot_version != version
                    or manifest.snapshot_digest != existing_digest
                ):
                    raise IndexConsistencyError(
                        "Neo4j did not return the active snapshot's immutable manifest."
                    )
                stage = "chroma_connect"
                chroma_store = ChromaDocumentStore(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                    collection_name=settings.chroma_collection,
                    create_if_missing=False,
                )
                stage = "chroma_readback"
                missing = chroma_store.missing_document_ids(list(manifest.document_ids))
                if missing:
                    raise IndexConsistencyError(
                        f"Chroma is missing {len(missing)} active snapshot document(s)."
                    )
                expected_documents = None
                if not manifest.fingerprints:
                    if supplied is not None:
                        stage = "payload_load"
                        expected_documents = supplied.to_source_documents()
                    else:
                        stage = "graph_readback"
                        expected_documents = graph_store.snapshot_documents(version)
                stage = "chroma_readback"
                verified_count = verify_snapshot_documents(
                    requested_identity,
                    list(manifest.document_ids),
                    chroma_store,
                    manifest=manifest,
                    expected_documents=expected_documents,
                )
                stage = "graph_readback"
                graph_store.verify_snapshot(version)
                if graph_store.active_snapshot_identity() != requested_identity:
                    raise IndexConsistencyError(
                        "The active research snapshot changed during retry verification."
                    )
                report = SnapshotPublicationReport(
                    snapshot_version=version,
                    snapshot_digest=existing_digest,
                    previous_snapshot_version=version,
                    chroma_count=verified_count,
                    neo4j_count=manifest.document_count,
                    already_active=True,
                )
            elif not payload_path.exists():
                stage = "payload_load"
                raise ValueError(
                    "The immutable snapshot version already exists, but its canonical payload "
                    "is unavailable. Retry with the original --snapshot-file."
                )
            else:
                stage = "payload_load"
                snapshot = load_research_snapshot(payload_path)
                if (
                    advisory_contract is not None
                    and snapshot.advisory_contract != advisory_contract
                ):
                    raise ValueError("Retry payload advisory contract differs from request.")
                if (
                    snapshot.snapshot_version != version
                    or snapshot.content_digest() != existing_digest
                ):
                    raise ValueError("Inactive retry payload conflicts with immutable identity.")
                stage = "snapshot_validation"
                _assess_research_snapshot(snapshot, clock=system_utc_now).require_healthy()
                stage = "chroma_connect"
                chroma_store = ChromaDocumentStore(
                    host=settings.chroma_host,
                    port=settings.chroma_port,
                    collection_name=settings.chroma_collection,
                )
                stage = "snapshot_publish"
                report = publish_research_snapshot(
                    snapshot,
                    chroma_store,
                    graph_store,
                    clock=system_utc_now,
                    max_age=timedelta(hours=settings.market_data_max_age_hours),
                    future_tolerance=timedelta(
                        minutes=settings.market_data_future_tolerance_minutes
                    ),
                )
        else:
            stage = "universe_load"
            universe = load_research_universe(universe_path)
            persist_payload = False
            if payload_path.exists():
                stage = "payload_load"
                snapshot = load_research_snapshot(payload_path)
                if (
                    advisory_contract is not None
                    and snapshot.advisory_contract != advisory_contract
                ):
                    raise ValueError("Canonical payload advisory contract differs from request.")
                if snapshot.snapshot_version != version:
                    raise ValueError(
                        "The canonical snapshot payload does not match --snapshot-version."
                    )
                if snapshot.universe_id != universe.universe_id:
                    raise ValueError(
                        "The canonical snapshot payload does not match the selected universe."
                    )
            else:
                stage = "source_fetch"
                adapter = YahooResearchAdapter(
                    issuer_client=VanguardHoldingsClient(),
                    clock=system_utc_now,
                    max_attempts=settings.yahoo_max_attempts,
                    retry_backoff_seconds=settings.yahoo_retry_backoff_seconds,
                    advisory_contract=advisory_contract,
                    reference_facts=load_reference_facts(reference_facts, universe.symbols)
                    if advisory_contract == "us-eu-v1"
                    else None,
                )
                snapshot = adapter.fetch_snapshot(universe, snapshot_version=version)
                persist_payload = True
            stage = "snapshot_validation"
            _assess_research_snapshot(snapshot, clock=system_utc_now).require_healthy()
            if persist_payload:
                stage = "payload_save"
                persist_research_snapshot(snapshot, payload_path)
            stage = "chroma_connect"
            chroma_store = ChromaDocumentStore(
                host=settings.chroma_host,
                port=settings.chroma_port,
                collection_name=settings.chroma_collection,
            )
            stage = "snapshot_publish"
            report = publish_research_snapshot(
                snapshot,
                chroma_store,
                graph_store,
                clock=system_utc_now,
                max_age=timedelta(hours=settings.market_data_max_age_hours),
                future_tolerance=timedelta(minutes=settings.market_data_future_tolerance_minutes),
            )
    except (
        IndexConsistencyError,
        MarketDataQualityError,
        MarketDataError,
        ChromaUnavailable,
        Neo4jUnavailable,
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        diagnostic = _publication_diagnostic(stage, exc)
        typer.echo(
            "Research-universe publication failed "
            f"at {stage}: {diagnostic['code']}: {diagnostic['message']}",
            err=True,
        )
        raise typer.Exit(code=1) from exc
    finally:
        if graph_store is not None:
            graph_store.close()

    typer.echo(json.dumps(asdict(report), indent=2))


@app.command("prepare-chroma-legacy-visibility")
def prepare_chroma_legacy_visibility(
    apply: Annotated[
        bool,
        typer.Option(
            "--apply",
            help=(
                "Write and verify visibility metadata. Requires all collection readers and "
                "writers to be quiesced until the command finishes."
            ),
        ),
    ] = False,
    page_size: Annotated[
        int,
        typer.Option(
            "--page-size",
            min=1,
            max=10_000,
            help="Maximum document metadata rows read or written per bounded page.",
        ),
    ] = 100,
) -> None:
    """Preview or explicitly prepare safe no-snapshot Chroma visibility."""

    try:
        store = ChromaDocumentStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=settings.chroma_collection,
            create_if_missing=False,
        )
        report = store.prepare_legacy_visibility(apply=apply, page_size=page_size)
    except (ChromaUnavailable, OSError, RuntimeError, ValueError) as exc:
        typer.echo(f"Chroma legacy visibility preparation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(asdict(report), indent=2))


@app.command("data-health")
def data_health(
    symbols: str = typer.Option(
        "SPY,QQQ,VTI,BND",
        help="Comma-separated Yahoo Finance symbols to inspect without persisting them.",
    ),
) -> None:
    """Report source timestamps and freshness without writing to retrieval stores."""

    requested_symbols = [symbol.strip() for symbol in symbols.split(",")]
    try:
        observations = _yahoo_adapter().fetch(requested_symbols)
        report = _assess_market_data(observations, clock=system_utc_now)
    except (MarketDataError, OSError, RuntimeError, ValueError) as exc:
        typer.echo(f"Market-data health check failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(report.model_dump_json(indent=2))
    if not report.healthy:
        raise typer.Exit(code=1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Natural-language retrieval query."),
    limit: int = typer.Option(5, min=1, max=50, help="Maximum number of sources to return."),
) -> None:
    """Search the Chroma source collection and print attributable results."""

    try:
        store = ChromaDocumentStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=settings.chroma_collection,
        )
        results = store.search(query, limit=limit)
    except (ChromaUnavailable, OSError, RuntimeError, ValueError) as exc:
        typer.echo(f"Search failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps([result.model_dump(mode="json") for result in results], indent=2))


@app.command("hybrid-search")
def hybrid_search(
    query: str = typer.Argument(..., help="Natural-language retrieval query."),
    limit: int = typer.Option(5, min=1, max=50, help="Maximum number of sources to return."),
) -> None:
    """Search Chroma and attach source-linked ETF relationship context from Neo4j."""

    graph_store: Neo4jGraphStore | None = None
    try:
        semantic_store = ChromaDocumentStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=settings.chroma_collection,
        )
        graph_store = Neo4jGraphStore(
            uri=settings.neo4j_uri,
            auth=settings.neo4j_credentials(),
        )
        results = HybridRetriever(semantic_store, graph_store).search(query, limit=limit)
    except (ChromaUnavailable, Neo4jUnavailable, OSError, RuntimeError, ValueError) as exc:
        typer.echo(f"Hybrid search failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    finally:
        if graph_store is not None:
            graph_store.close()

    typer.echo(json.dumps([result.model_dump(mode="json") for result in results], indent=2))


@app.command("evaluate-retrieval")
def evaluate_retrieval(
    dataset_path: Annotated[
        Path | None,
        typer.Option(
            "--dataset",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Optional evaluation JSON; defaults to the packaged offline baseline.",
        ),
    ] = None,
    limit: int = typer.Option(3, min=1, max=50, help="Maximum candidates scored per case."),
) -> None:
    """Compare semantic-only and graph-enriched retrieval on curated offline cases."""

    try:
        dataset = load_evaluation_dataset(dataset_path)
        report = run_offline_evaluation(dataset, limit=limit)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(f"Retrieval evaluation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(report.model_dump_json(indent=2))


@app.command("evaluate-explanations")
def evaluate_explanations(
    dataset_path: Annotated[
        Path | None,
        typer.Option(
            "--dataset",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Optional evaluation JSON; defaults to the packaged offline baseline.",
        ),
    ] = None,
) -> None:
    """Replay explanation and safety cases through the production review gate."""

    try:
        dataset = load_explanation_evaluation_dataset(dataset_path)
        report = run_offline_explanation_evaluation(dataset)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(f"Explanation evaluation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(report.model_dump_json(indent=2))
    if not report.metrics.passed:
        raise typer.Exit(code=1)


@app.command("evaluate-analysis")
def evaluate_analysis(
    dataset_path: Annotated[
        Path | None,
        typer.Option(
            "--dataset",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Optional 18-case analysis JSON; defaults to the frozen Issue 99 set.",
        ),
    ] = None,
) -> None:
    """Replay 37 fixed cases offline and fail when any frozen expectation differs."""

    try:
        report = run_analysis_baseline(load_analysis_dataset(dataset_path))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        typer.echo(f"Analysis evaluation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise typer.Exit(code=1)


@app.command("evaluate-us-eu")
def evaluate_us_eu() -> None:
    """Replay the separate synthetic US/EU contract baseline without network or providers."""
    report = run_us_eu_baseline()
    typer.echo(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
