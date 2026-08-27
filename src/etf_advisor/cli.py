"""Small command-line entry points for testable local development."""

import json
from typing import Any
from uuid import uuid4

import typer
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from etf_advisor.graph.workflow import build_graph

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


if __name__ == "__main__":
    app()
