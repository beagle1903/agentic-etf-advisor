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
