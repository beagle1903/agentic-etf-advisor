# Local development runbook

## Bootstrap

```powershell
Copy-Item .env.example .env
uv sync
uv run pytest
```

Install the optional integrations when the next slice needs them:

```powershell
uv sync --extra checkpoint --extra dashboard --extra observability --extra providers --extra rag
```

## Quality checks

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Run the graph demo

```powershell
uv run etf-advisor demo
```

## Exercise hybrid retrieval

With Chroma and Neo4j healthy, index one shared source bundle and query it:

```powershell
uv sync --extra rag
uv run etf-advisor ingest --symbols SPY,QQQ --with-graph
uv run etf-advisor hybrid-search "broad US equity exposure"
```

Both writes are idempotent because they use the same stable source document IDs. If one
local service fails during ingestion, restore it and rerun the same command; the command
verifies that every requested ID exists in both stores before reporting success.

## Run the offline retrieval baseline

The packaged curated dataset needs no services, credentials, model downloads, or network:

```powershell
uv run etf-advisor evaluate-retrieval
```

To score a reviewed replacement dataset with the same schema:

```powershell
uv run etf-advisor evaluate-retrieval --dataset .\path\to\retrieval-evaluation.json
```

The report is deterministic for a given dataset version and limit. Treat zero ranking delta
as zero measured ranking lift even when graph-context metrics improve.

## Start infrastructure

```powershell
docker compose up -d chroma neo4j postgres
docker compose ps
```

Neo4j Bolt is exposed on host port `17687` because the standard `7687` port is in a
Windows-reserved range on the original development machine.

Stop containers while preserving named-volume data:

```powershell
docker compose stop
```

Do not use `docker compose down --volumes` unless deletion of local database data is
explicitly intended.

## Secrets

Copy `.env.example` to `.env` and place credentials only in `.env` or a secret manager.
The `.env` file is ignored by Git. Never paste real keys into documentation, tests, Docker
images, or workflow files.
