"""Small command-line entry points for testable local development."""

import json
from typing import Any
from uuid import uuid4

import typer
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from etf_advisor.config import settings
from etf_advisor.data.yahoo import MarketDataError, YahooFinanceAdapter
from etf_advisor.graph.workflow import build_graph
from etf_advisor.rag.chroma_store import ChromaDocumentStore, ChromaUnavailable

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Run local Agentic ETF Advisor workflows."""


def _print_state(label: str, state: dict[str, Any]) -> None:
    typer.echo(label)
    typer.echo(json.dumps(state, indent=2, default=str))


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
) -> None:
    """Fetch timestamped Yahoo snapshots and upsert them into Chroma."""

    requested_symbols = [symbol.strip() for symbol in symbols.split(",")]
    try:
        documents = YahooFinanceAdapter().fetch_source_documents(requested_symbols)
        store = ChromaDocumentStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=settings.chroma_collection,
        )
        count = store.upsert(documents)
    except (MarketDataError, ChromaUnavailable, OSError, RuntimeError) as exc:
        typer.echo(f"Ingestion failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Upserted {count} source document(s) into '{settings.chroma_collection}'.")
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


if __name__ == "__main__":
    app()
