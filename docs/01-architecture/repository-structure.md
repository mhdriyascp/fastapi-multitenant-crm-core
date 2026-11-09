# ADR 001: Modular Monorepo Structure

## Status

Accepted

## Context

The Enterprise CRM is developed as a full-stack application with a FastAPI backend and a Next.js frontend. A single repository keeps changes across the two applications reviewable together while allowing each side to use its own runtime and dependency tooling.

## Decision

Use a modular monorepo with these top-level areas:

- `backend/`: Python 3.12 application, dependencies managed with Astral `uv`.
- `frontend/`: Next.js application using TypeScript and React.
- `docs/`: architecture decision records and other project documentation.
- `backend/scripts/`: operational scripts (e.g. RBAC seed).

The backend is organized as a modular monolith. API routers are the HTTP boundary, services coordinate application behavior, SQLAlchemy models define persisted entities, and Alembic manages schema migrations.

## Current Implementation

- `backend/main.py` mounts shared authentication at `/auth`, tenant APIs under configured `/api/v1` and `/api/v2` prefixes, and the platform control plane independently at `/platform/v1`.
- API routing is organized under `backend/app/api/tenant/v1/`, `tenant/v2/`, `platform/v1/`, `auth/`, and `health/`. Tenant member operations are mounted only under `/api/v1/iam/members/*`.
- Shared API dependencies are grouped under `backend/app/api/dependencies/` for authentication and database sessions.
- `backend/app/services/` contains authentication, member, and platform services. Several services still issue SQLAlchemy queries directly; repository adoption is partial.
- SQLAlchemy models are in `backend/app/models/`, and Alembic migrations are in `backend/alembic/`.
- `backend/scripts/seed_rbac.py` is a standalone CLI script that idempotently seeds permissions and system roles into the database. It must be run explicitly after migrations; it is not invoked at application startup.
- The frontend is a Next.js application rooted at `frontend/src/app/`.
- `compose.yaml` starts PostgreSQL, pgweb, Redis, and Mailpit for local infrastructure; it does not start the API or frontend.
- The frontend root page currently displays API/database/Redis health rather than CRM workflows.

## Consequences

- Full-stack features can be changed and reviewed in one commit history, while backend and frontend commands and dependencies remain separately managed.
- Backend module boundaries can evolve independently within the monolith without requiring separate deployment units.
- The repository and service boundaries are not yet consistently implemented: database access currently lives in services. New work should follow the intended service/repository separation where applicable; migrating existing code is a separate change.
- API documentation and tests should reflect registered routes, not merely endpoint modules present in the source tree.

## Related Documentation

- [Documentation index](../README.md)
- [System architecture and module map](system-overview.md)
- [Identity and authentication](../03-modules/identity-and-authentication.md)
- [IAM and RBAC](../03-modules/iam-rbac.md)
- [Database and migrations](../04-database/database-and-migrations.md)
- [Email outbox and background worker](../03-modules/email-and-background-work.md)
- [Local development and configuration](../02-setup/local-development.md)
- [Seed data](../04-database/seed-data.md)
