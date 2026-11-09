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

The backend is organized as a modular monolith. API routers are the HTTP boundary, services coordinate application behavior, SQLAlchemy models define persisted entities, and Alembic manages schema migrations.

## Current Implementation

- `backend/main.py` mounts version-independent authentication at `/auth` and the versioned API under the configured API prefix (`/api/v1` by default).
- Authentication routes are in `backend/app/api/auth/router.py`. Versioned domain endpoints are grouped under `backend/app/api/v1/endpoints/`; the versioned router currently registers the members endpoint.
- `backend/app/services/` contains authentication and member services. These services currently issue SQLAlchemy queries directly; a dedicated `backend/app/repositories/` package does not yet exist.
- The leads endpoint module exists, but is not currently included by the versioned API router. Its `LeadRepository`, in `backend/app/api/dependencies/lead_storage.py`, is an in-memory implementation rather than a database-backed repository.
- SQLAlchemy models are in `backend/app/models/`, and Alembic migrations are in `backend/alembic/`.
- The frontend is a Next.js application rooted at `frontend/src/app/`.
- `compose.yaml` starts PostgreSQL, pgweb, Redis, and Mailpit for local infrastructure; it does not start the API or frontend.
- The frontend root page currently displays API/database/Redis health rather than CRM workflows.

## Consequences

- Full-stack features can be changed and reviewed in one commit history, while backend and frontend commands and dependencies remain separately managed.
- Backend module boundaries can evolve independently within the monolith without requiring separate deployment units.
- The repository and service boundaries are not yet consistently implemented: database access currently lives in services, and lead storage is in-memory. New work should follow the intended service/repository separation where applicable; migrating existing code is a separate change.
- API documentation and tests should reflect registered routes, not merely endpoint modules present in the source tree.

## Related Documentation

- [Documentation index](../README.md)
- [System architecture and module map](system-overview.md)
- [Identity and authentication](../03-modules/identity-and-authentication.md)
- [IAM and RBAC](../03-modules/iam-rbac.md)
- [CRM leads](../03-modules/crm-leads.md)
- [Database and migrations](../04-database/database-and-migrations.md)
- [Email outbox and background worker](../03-modules/email-and-background-work.md)
- [Local development and configuration](../02-setup/local-development.md)
