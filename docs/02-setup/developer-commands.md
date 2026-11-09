# Developer Command Cheat Sheet

Run backend commands from `backend/` and use Astral `uv` for Python dependency management and execution.

## Backend

```sh
cd backend
uv sync
uv run uvicorn main:app --reload
uv run alembic upgrade head
uv run alembic current
uv run ruff check app
uv run ruff format --check app
uv run pytest
```

No backend test files were present when this guide was written; add focused tests with new behavior. Run `uv run pytest <test-path>` for targeted validation where tests exist.

## Frontend

The frontend scripts are defined in `frontend/package.json`:

```sh
npm ci
npm run dev
npm run lint
npm run build
```

The checked-in lockfile is `frontend/package-lock.json`; use npm and do not regenerate a different lockfile.

## Local infrastructure

From the repository root, start the supporting services:

```sh
docker compose up -d
docker compose ps
docker compose logs -f postgres redis mailpit
```

Compose starts PostgreSQL, pgweb, Redis, and Mailpit only; it does not start the API, frontend, or ARQ worker. For ports and configuration, see [local development](local-development.md).

## Migration safety

Review migration source and target environment before execution. Do not run destructive migrations against important environments without explicit human approval. See [database and migrations](../04-database/database-and-migrations.md).
