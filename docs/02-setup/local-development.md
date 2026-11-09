# Local Development and Runtime Configuration

## Containerized infrastructure

`compose.yaml` starts infrastructure services only; it does not build or run the FastAPI backend or Next.js frontend.

| Service | Purpose | Default host port | Health/readiness |
|---|---|---:|---|
| `postgres` | PostgreSQL 16 with pgvector image | 5432 | `pg_isready` |
| `pgweb` | PostgreSQL browser UI | 8081 | Waits for PostgreSQL health |
| `redis` | Redis 7 with append-only persistence | 6379 | `redis-cli ping` |
| `mailpit` | Local SMTP capture and mailbox UI | SMTP 1025; UI 8025 | HTTP info endpoint |

PostgreSQL and Redis data use named Docker volumes. Compose allows environment overrides for database name/user/password and service ports. Its fallback database credentials are for local development only; provide secure environment-specific values outside development and do not commit secrets.

## Backend configuration

`backend/app/core/config.py` loads case-sensitive settings from the environment and `.env` (extra values are ignored). Relevant settings include:

- Application/API: `PROJECT_NAME`, `ENVIRONMENT`, `DEBUG`, `API_V1_STR`.
- URLs/CORS: `BACKEND_BASE_URL`, `FRONTEND_BASE_URL`, `CORS_ORIGINS`.
- Services: `DATABASE_URL`, `REDIS_URL`.
- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS`, `EMAILS_FROM_EMAIL`, `EMAILS_FROM_NAME`.
- Security lifetimes: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, `MFA_OTP_EXPIRE_SECONDS`.

Use the asynchronous PostgreSQL URL expected by SQLAlchemy/asyncpg in `DATABASE_URL`. The API health check probes PostgreSQL and Redis only; it does not report SMTP/Mailpit or worker readiness.

## Application processes

- API entry module: `backend/main.py`; it mounts auth, versioned routes, and `/health`.
- Email worker: `backend/app/workers/email_worker.py`, configured through ARQ.
- Frontend: `frontend/`, Next.js App Router. The current homepage requests `${NEXT_PUBLIC_API_URL}/health`, defaulting to `http://localhost:8000`.

## Tooling

- Python dependencies and commands use Astral `uv` from `backend/`.
- Frontend scripts are defined in `frontend/package.json`; use the package manager matching the existing frontend lockfile.
- Alembic migrations are under `backend/alembic/versions/`.

See [Database and migrations](../04-database/database-and-migrations.md) and [Email outbox](../03-modules/email-and-background-work.md) for those subsystems.
