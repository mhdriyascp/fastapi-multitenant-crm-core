# Local Development and Runtime Configuration

## Containerized infrastructure

`compose.yaml` starts infrastructure services only; it does not build or run the FastAPI backend or Next.js frontend.

| Service | Purpose | Default host port | Health/readiness |
|---|---|---:|---|
| `postgres` | PostgreSQL 16 with pgvector image | 5432 | `pg_isready` |
| `pgweb` | PostgreSQL browser UI | 8081 | Waits for PostgreSQL health |
| `redis` | Redis 7 with append-only persistence | 6379 | `redis-cli ping` |
| `mailpit` | Local SMTP capture and mailbox UI | SMTP 1025; UI 8025 | HTTP info endpoint |

PostgreSQL and Redis data use named Docker volumes (`crm_postgres_data`, `crm_redis_data`). Compose allows environment overrides for database name/user/password and service ports via environment variables (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`, `REDIS_PORT`, `PGWEB_PORT`, `MAILPIT_SMTP_PORT`, `MAILPIT_WEB_PORT`). Fallback credentials are for local development only; provide secure environment-specific values outside development and do not commit secrets.

## Backend configuration

`backend/app/core/config.py` loads case-sensitive settings from the environment and `.env` (extra values are ignored). Relevant settings include:

- Application/API: `PROJECT_NAME`, `ENVIRONMENT`, `DEBUG`, `API_V1_STR`, `API_V2_STR`.
- URLs/CORS: `BACKEND_BASE_URL`, `FRONTEND_BASE_URL`, `CORS_ORIGINS`.
- Services: `DATABASE_URL`, `REDIS_URL`.
- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS`, `EMAILS_FROM_EMAIL`, `EMAILS_FROM_NAME`.
- Security lifetimes: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, `MFA_OTP_EXPIRE_SECONDS`.

Use the asynchronous PostgreSQL URL expected by SQLAlchemy/asyncpg in `DATABASE_URL` (e.g. `postgresql+asyncpg://...`). Health checks probe PostgreSQL, Redis, and the configured SMTP server (including SMTP authentication when credentials are configured). They return `200 healthy` only when all checks pass, and `503 degraded` otherwise. Worker-process readiness is not checked by the API health endpoint.

## Application processes

- **API**: entry module `backend/main.py`; authentication is shared at `/auth`; tenant APIs are versioned at `/api/v1` and `/api/v2`; platform APIs are independently versioned at `/platform/v1`. Tenant member operations are under `/api/v1/iam/members`; no member routes are exposed outside tenant versions. The single shared health endpoint is `/health`.
- **API documentation**: ReDoc is available at `/v1/redoc` and `/v2/redoc`; Scalar is available at `/scalar/v1` and `/scalar/v2`. The v1 schema contains its tenant member routes, and both schemas contain shared authentication and health endpoints plus only their respective versioned routes. The schemas are `/openapi/v1.json` and `/openapi/v2.json`. Swagger (`/docs`), root ReDoc (`/redoc`), root Scalar (`/scalar`), and default `/openapi.json` are disabled.
- **Platform control plane**: platform-only operations are mounted independently at `/platform/v1`; use `/platform/v1/redoc`, `/scalar/platform/v1`, and `/openapi/platform/v1.json`. Shared `/auth` is used for login. Every platform operation requires a verified MFA method and the corresponding `platform.*` permission. Tenant API versions do not contain duplicate platform endpoints.
- **Documentation ordering**: Each versioned ReDoc and Scalar reference lists that version's health-readiness endpoint first. It checks PostgreSQL, Redis, and SMTP and reports `200 healthy` only when all three are reachable; otherwise it returns `503 degraded`.
- **Health endpoint**: `GET /health` runs PostgreSQL, Redis, and SMTP readiness checks, returning `503` if any dependency is unavailable. It is shown once at the top of both versioned API documentation pages.
- **Email worker**: `backend/app/workers/email_worker.py`, configured through ARQ (`WorkerSettings`). Run with `uv run worker backend.app.workers.email_worker.WorkerSettings` from `backend/`.
- **RBAC seed**: `backend/scripts/seed_rbac.py` populates permissions and system roles, including the code-defined `platform.*` permission catalog; run after migrations and whenever `constants.py` changes.
- **Frontend**: `frontend/`, Next.js App Router. The current homepage requests `${NEXT_PUBLIC_API_URL}/health`, defaulting to `http://localhost:8000`.

## Tooling

- Python dependencies and commands use Astral `uv` from `backend/`.
- Frontend scripts are defined in `frontend/package.json`; use npm (the existing lockfile is `package-lock.json`).
- Alembic migrations are under `backend/alembic/versions/`.

See [Database and migrations](../04-database/database-and-migrations.md), [Seed data](../04-database/seed-data.md), and [Email outbox](../03-modules/email-and-background-work.md) for those subsystems.
