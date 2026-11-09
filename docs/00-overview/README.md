# Enterprise CRM Overview

## Product context

This repository contains an early-stage enterprise CRM platform with identity and access management foundations. The current backend provides registration and authentication flows, tenant/workspace membership administration, role assignment, and health reporting. CRM lead schemas and endpoint code exist, but that route is not currently mounted and its storage is an in-memory prototype.

The current frontend is a Next.js health-status page, not yet a full CRM dashboard. Read the [system architecture](../01-architecture/system-overview.md) and [module guides](../03-modules/) for implementation details and limitations.

## Technology stack

| Area | Technology in project manifests/code |
|---|---|
| Backend runtime | Python `>=3.12` |
| API | FastAPI |
| Validation and settings | Pydantic v2, `pydantic-settings` |
| Persistence | SQLAlchemy async, PostgreSQL, asyncpg |
| Schema management | Alembic |
| Cache and queue broker | Redis |
| Background jobs | ARQ |
| Authentication | JWT (`PyJWT`), Argon2 password hashing |
| Email | aiosmtplib, Jinja2 templates, PostgreSQL outbox |
| Frontend | Next.js 16, React 19, TypeScript 5 |
| Local infrastructure | Docker Compose, PostgreSQL/pgvector image, Redis, pgweb, Mailpit |

Dependency versions are defined by `backend/pyproject.toml` and `frontend/package.json`; consult those manifests and lockfiles for the resolved versions.

## Repository

- `backend/`: FastAPI application, SQLAlchemy models, migrations, and worker.
- `frontend/`: Next.js App Router application.
- `docs/`: architecture, setup, module, database, and agent-standard documentation.
- `compose.yaml`: local database, Redis, pgweb, and Mailpit services.

## Source of truth

The implementation and its migrations define current behavior. Repository-wide AI-agent engineering standards are in [AGENTS.md](../../AGENTS.md); they are requirements for new and changed code, not a statement that all existing code already complies.
