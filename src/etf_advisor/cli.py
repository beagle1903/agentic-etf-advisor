"""Small command-line entry points for testable local development."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import typer
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from etf_advisor.config import settings
from etf_advisor.data.quality import MarketDataQualityError, assess_observations
from etf_advisor.data.yahoo import MarketDataError, YahooFinanceAdapter
from etf_advisor.evaluation import load_evaluation_dataset, run_offline_evaluation
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.chroma_store import ChromaDocumentStore, ChromaUnavailable
from etf_advisor.rag.hybrid import HybridRetriever
from etf_advisor.rag.indexing import IndexConsistencyError, index_documents
from etf_advisor.rag.neo4j_store import Neo4jGraphStore, Neo4jUnavailable

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Run local Agentic ETF Advisor workflows."""


def _print_state(label: str, state: dict[str, Any]) -> None:
    typer.echo(label)
    typer.echo(json.dumps(state, indent=2, default=str))


def _yahoo_adapter() -> YahooFinanceAdapter:
    return YahooFinanceAdapter(
        max_attempts=settings.yahoo_max_attempts,
        retry_backoff_seconds=settings.yahoo_retry_backoff_seconds,
    )


@app.command()
def demo() -> None:
    """Run a deterministic profile -> review -> approval lifecycle."""

    graph = build_graph(checkpointer=InMemorySaver())
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
    _print_state("Paused for human review:", paused)

    completed = graph.invoke(Command(resume={"action": "approve"}), config=config)
    _print_state("Resumed after approval:", completed)


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
        health = assess_observations(
            observations,
            checked_at=datetime.now(UTC),
            max_age=timedelta(hours=settings.market_data_max_age_hours),
            future_tolerance=timedelta(minutes=settings.market_data_future_tolerance_minutes),
        )
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
        report = assess_observations(
            observations,
            checked_at=datetime.now(UTC),
            max_age=timedelta(hours=settings.market_data_max_age_hours),
            future_tolerance=timedelta(minutes=settings.market_data_future_tolerance_minutes),
        )
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


if __name__ == "__main__":
    app()
