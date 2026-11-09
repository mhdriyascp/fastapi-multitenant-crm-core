# System Architecture and Module Map

## Scope and status

The repository is a full-stack monorepo. The backend is a FastAPI application organized as a modular monolith; the frontend is a Next.js application. This document describes the inspected implementation, not a guarantee that every architectural boundary is complete.

## Repository map

| Path | Responsibility | Current implementation |
|---|---|---|
| `backend/main.py` | FastAPI app construction, middleware, exception registration, and top-level route mounting | Mounts `/auth`, the configured versioned API prefix (default `/api/v1`), and `/health` |
| `backend/app/api/` | HTTP routes and FastAPI dependencies | Authentication, member endpoints, and an unmounted leads endpoint module |
| `backend/app/services/` | Authentication and member use-case orchestration | `AuthService` and `MemberService`; both currently execute SQLAlchemy queries directly |
| `backend/app/models/` | SQLAlchemy ORM entities | Identity, tenant, membership, role, permission, session, MFA, audit, and email-outbox records |
| `backend/app/schemas/` | Pydantic request/response contracts | Auth, member, and lead schemas |
| `backend/app/core/` | Settings, database, security, enums, exceptions, Redis/ARQ, email, and constants | Shared platform services and configuration |
| `backend/app/workers/` | Background workers | ARQ email-outbox worker |
| `backend/alembic/` | Database migrations | Initial IAM schema and email outbox table |
| `frontend/src/app/` | Next.js App Router UI | Root page checks and displays backend/PostgreSQL/Redis health; this is not yet a full CRM interface |
| `compose.yaml` | Local infrastructure containers | PostgreSQL, pgweb, Redis, and Mailpit; it does not start the API or frontend |
| `docs/` | Project documentation | Architecture decisions, module guides, and operations guides |

## Runtime route topology

`backend/main.py` mounts:

- `backend/app/api/auth/router.py` under `/auth`.
- `backend/app/api/v1/router.py` under `settings.API_V1_STR` (default `/api/v1`).
- A `/health` endpoint that probes PostgreSQL and Redis.

The versioned router currently includes only `members.router`, with prefix `/iam/members`. Therefore the registered member route paths are under `/api/v1/iam/members`. The auth routes are mounted at `/auth`, not under the versioned API prefix.

`backend/app/api/v1/endpoints/leads.py` exists but is not included in the versioned router. `backend/app/api/v1/auth/router.py` also exists but is not mounted by `main.py`; the active auth router is `backend/app/api/auth/router.py`.

## Request and data flow

### Authenticated member request

1. FastAPI resolves `get_current_context` from `backend/app/api/deps.py`.
2. The dependency decodes the bearer JWT, loads the user, and resolves the `tid` workspace claim.
3. For non-platform administrators with a tenant claim, the dependency checks the active tenant membership and loads role/permission relationships.
4. `RequirePermission` checks for the requested permission code; platform admins receive a wildcard permission set.
5. The endpoint delegates to `MemberService`, which currently performs direct SQLAlchemy queries and writes.
6. The `get_db_session` dependency commits after normal request completion and rolls back if an exception escapes.

This is the current flow; it does not establish that all service/repository separation, domain-exception, or tenant-isolation targets are already met.

## Domain and platform modules

- **Identity/authentication:** registration, login, refresh/logout, profile, workspace selection, password reset, and email OTP MFA. See [Identity and authentication](../03-modules/identity-and-authentication.md).
- **IAM/RBAC:** users are associated to workspaces by memberships; memberships carry roles; roles map to global permission records. Member APIs expose member listing, invitations, membership removal, role listing, and role assignment updates. See [IAM and RBAC](../03-modules/iam-rbac.md) and [RBAC architecture](rbac-and-tenancy.md).
- **Leads:** schemas and CRUD-style endpoint/repository code are present, but the router is not mounted and persistence is in-memory. See [CRM leads](../03-modules/crm-leads.md).
- **Email:** invitation email outbox, ARQ enqueue, worker dispatch, Jinja templates, and SMTP. See [Email outbox](../03-modules/email-and-background-work.md).
- **Database:** async SQLAlchemy session management and Alembic migrations. See [Database and migrations](../04-database/database-and-migrations.md).

## Intended boundaries versus current gaps

The engineering direction is to keep HTTP handling in routers, business workflows in services, and persistence queries in repositories. Current code differs in several material ways:

- No `backend/app/repositories/` package exists. `AuthService` and `MemberService` query through `AsyncSession` directly.
- The leads repository is a plain in-memory class under `backend/app/api/dependencies/`; it has no tenant context or SQL persistence.
- Several service methods raise FastAPI `HTTPException` directly. The exception layer currently handles `AppException`, request-validation errors, and unhandled errors; a `PermissionDeniedException` class is not currently defined.
- `backend/app/iam/dependencies.py` duplicates the auth-context/permission dependency pattern in `backend/app/api/deps.py`. The mounted member routes import the latter.
- `INITIAL_PERMISSIONS` and `SYSTEM_ROLES` define constants, but no seed/startup invocation was found in the app startup path.
- The active `/auth` router and the unmounted `/api/v1/auth` router are separate modules; verify route registration before relying on changes in the latter.
- Current APIs expose internal UUIDs in some request/response paths (for example membership IDs and workspace IDs); the public-ID-only standard is not consistently implemented.

These are documentation of current implementation gaps, not authorization to migrate them as part of an unrelated task.
