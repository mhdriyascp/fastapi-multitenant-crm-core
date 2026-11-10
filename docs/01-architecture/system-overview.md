# System Architecture and Module Map

## Scope and status

The repository is a full-stack monorepo. The backend is a FastAPI application organized as a modular monolith; the frontend is a Next.js application. This document describes the inspected implementation, not a guarantee that every architectural boundary is complete.

## Repository map

| Path | Responsibility | Current implementation |
|---|---|---|
| `backend/main.py` | FastAPI app construction, middleware, exception registration, and app-level setup | Creates the app and includes the assembled API router and documentation routes |
| `backend/app/api/router.py` | Top-level API router assembly | Mounts shared auth, tenant versions, the separate `/platform/v1` control plane, and health |
| `backend/app/api/auth/` | Shared authentication routes | Version-independent `/auth/*` login, session, MFA, and identity operations |
| `backend/app/api/tenant/v1/` | Tenant API v1 | Includes tenant IAM member operations under `/api/v1/iam/members/*` |
| `backend/app/api/tenant/v2/` | Tenant API v2 | Versioned router currently has no endpoint modules registered |
| `backend/app/api/platform/v1/` | Platform control-plane API v1 | Independently versioned `/platform/v1/*` operations, split into IAM, operators, tenants, plans, and audit modules |
| `backend/app/api/health/` | Readiness endpoints | Single `/health` endpoint |
| `backend/app/api/documentation.py` | API documentation routes and schema filtering | Owns versioned OpenAPI, ReDoc, and Scalar configuration |
| `backend/app/api/dependencies/` | Shared API dependencies | Authentication and database sessions |
| `backend/app/services/` | Authentication, member, and platform-control-plane use cases | `PlatformAdminService` delegates platform persistence to `PlatformAdminRepository`; other services still query directly |
| `backend/app/repositories/` | Database persistence operations | Member and platform administration repositories; adoption is partial |
| `backend/app/models/` | SQLAlchemy ORM entities | Identity, tenant, membership, RBAC, platform operator, plan, subscription, tenant settings, audit, MFA, and email-outbox records |
| `backend/app/schemas/` | Pydantic request/response contracts | Auth, member, and platform administration schemas |
| `backend/app/core/` | Settings, database, security, enums, exceptions, Redis/ARQ, email, and constants | Shared platform services and configuration |
| `backend/app/workers/` | Background workers | ARQ email-outbox worker |
| `backend/alembic/` | Database migrations | Initial IAM schema, email outbox, and platform control-plane tables |
| `backend/scripts/seed/` | Initial setup seed package | RBAC, master data, navigation menus, and local demo-user seed commands |
| `frontend/src/app/` | Next.js App Router UI | Root page checks and displays backend/PostgreSQL/Redis health; this is not yet a full CRM interface |
| `compose.yaml` | Local infrastructure containers | PostgreSQL, pgweb, Redis, and Mailpit; it does not start the API or frontend |
| `docs/` | Project documentation | Architecture decisions, module guides, and operations guides |

## Runtime route topology

The API has shared authentication and health paths, tenant-versioned APIs, and a separately versioned platform control plane. The default docs pages and Swagger UI are disabled.

### Shared authentication API

`backend/app/api/auth/router.py` is mounted once at `/auth`, independent of API version. Authentication, token/session operations, profile, workspace selection, password reset, and MFA therefore use the same paths alongside either version:

- `/auth/register`, `/auth/login`, `/auth/refresh`, and `/auth/logout`
- `/auth/me`, `/auth/workspaces`, and `/auth/switch-workspace`
- `/auth/password/*` and `/auth/mfa/*`

These routes are not duplicated beneath `/api/v1` or `/api/v2`.

### Tenant IAM/RBAC API v1

Tenant IAM member operations are implemented in `backend/app/api/tenant/v1/endpoints/members.py` and mounted at `/api/v1/iam/members/*`. Core and CRM master-data operations are mounted at `/api/v1/master-data/*`; shared catalogs are read-only to tenant callers and are administered through `/platform/v1/master-data/shared/*`. See [master-data APIs](../03-modules/master-data-apis.md). Version 2 does not yet expose tenant endpoints.

### API v1 — `/api/v1`

`backend/app/api/tenant/v1/router.py` is mounted at `settings.API_V1_STR` (default `/api/v1`). It registers tenant member and core/CRM master-data operations.

### API v2 — `/api/v2`

`backend/app/api/tenant/v2/router.py` is mounted at `settings.API_V2_STR` (default `/api/v2`) and currently has no endpoint modules registered.

### Platform control plane — `/platform/v1`

`backend/app/api/platform/v1/router.py` assembles platform-only operations from `endpoints/iam.py`, `operators.py`, `tenants.py`, `plans.py`, `audit.py`, and `master_data.py`. It is not nested under tenant API versions. All routes authenticate the global identity independently of tenant context and require verified MFA; tenant membership permissions do not authorize platform operations. Suspended/cancelled tenants lose tenant permissions without blocking account-level authentication or platform recovery.

- ReDoc: `/platform/v1/redoc`; Scalar: `/scalar/platform/v1`; schema: `/openapi/platform/v1.json`.
- Its schema includes shared authentication and `/health` plus only `/platform/v1/*` operations.
- Platform superadmins are explicitly recognized by `users.is_platform_admin`; other operators need separately assigned `platform_user_roles`.
- Platform permission definitions remain code-managed and are seeded from `INITIAL_PERMISSIONS`. Delegated operators can grant or assign only permissions they themselves hold.
- Dashboard-managed writes require a reason and are audited transactionally. Tenant settings are allowlisted; plan records are metadata, not payment processing.

### Platform and documentation routes

- The single shared `/health` endpoint probes PostgreSQL, Redis, and configured SMTP. It returns `200 healthy` only when every dependency check succeeds; otherwise it returns `503 degraded`.
- `/v1/redoc` and `/v2/redoc` provide versioned ReDoc; `/scalar/v1` and `/scalar/v2` provide the corresponding Scalar references. Each version uses its isolated schema at `/openapi/v1.json` or `/openapi/v2.json`.
- Tenant schemas include shared `/auth/*` and `/health` paths plus only their own version-prefixed API operations. The v1 schema includes `/api/v1/iam/members/*`; v2 currently has no member routes.
- Platform control-plane documentation is independently available at `/platform/v1/redoc` and `/scalar/platform/v1`; its OpenAPI schema is `/openapi/platform/v1.json`.
- Router composition lives in `backend/app/api/router.py`; health logic, platform endpoints, and documentation/schema generation live in dedicated API modules. `backend/main.py` does not define individual business or documentation routes.
- Each schema lists the same shared `/health` endpoint first, before shared and version-specific operations. It appears once in each document and checks PostgreSQL, Redis, and SMTP.
- `/docs`, `/redoc`, `/scalar`, `/scalar/common`, and `/openapi.json` are unavailable.

## Request and data flow

### Authenticated member request

1. FastAPI resolves `get_current_context` from `backend/app/api/dependencies/auth.py`.
2. The dependency decodes the bearer JWT, loads the user, and resolves the `tid` workspace claim.
3. For non-platform administrators with a tenant claim, the dependency checks the active tenant membership and loads role/permission relationships.
4. `RequirePermission` checks for the requested permission code; platform admins receive a wildcard permission set.
5. The endpoint delegates to `MemberService`, which currently performs direct SQLAlchemy queries and writes.
6. The `get_db_session` dependency commits after normal request completion and rolls back if an exception escapes.

This is the current flow; it does not establish that all service/repository separation, domain-exception, or tenant-isolation targets are already met.

## Domain and platform modules

- **Identity/authentication:** registration, login, refresh/logout, profile, workspace selection, password reset, and email OTP MFA. See [Identity and authentication](../03-modules/identity-and-authentication.md).
- **IAM/RBAC:** users are associated to workspaces by memberships; memberships carry roles; roles map to global permission records. Member APIs expose member listing, invitations, membership removal, role listing, and role assignment updates. See [IAM and RBAC](../03-modules/iam-rbac.md) and [RBAC architecture](rbac-and-tenancy.md).
- **Platform administration:** isolated operator RBAC, tenant lifecycle/settings, plan metadata and assignment, and privileged audit events. It does not provide billing/payment processing or operator invitations. See [IAM and RBAC](../03-modules/iam-rbac.md).
- **Email:** invitation, password-reset, and MFA email outbox; ARQ enqueue; worker dispatch; Jinja templates; and SMTP. See [Email outbox](../03-modules/email-and-background-work.md).
- **Database:** async SQLAlchemy session management and Alembic migrations. See [Database and migrations](../04-database/database-and-migrations.md).
- **Initial setup seed:** `backend/scripts/seed/` contains the explicit seed package. Run `uv run python -m scripts.seed` after migrations for initial setup, or `uv run python -m scripts.seed.rbac` for RBAC only. See [Seed data](../04-database/seed-data.md).

## Intended boundaries versus current gaps

The engineering direction is to keep HTTP handling in routers, business workflows in services, and persistence queries in repositories. Current code differs in several material ways:

- Repository usage is partial: the platform administration service uses `PlatformAdminRepository`; `AuthService` and `MemberService` still query through `AsyncSession` directly.
- Domain exceptions (`EntityNotFoundException`, `EntityConflictException`, `BusinessRuleViolationException`, `PermissionDeniedException`, `AuthenticationException`) are defined in `app.core.exceptions` and raised by services. `register_exception_handlers` formats them into standardized JSON error responses.
- `INITIAL_PERMISSIONS` and `SYSTEM_ROLES` constants are synchronized by `backend/scripts/seed/rbac.py` as part of the complete initial-setup seed or through the RBAC-only module command; there is no startup-time seeding.
- Current APIs expose internal UUIDs in some request/response paths (for example membership IDs and workspace IDs in the workspace listing); the public-ID-only standard is not consistently implemented.

These are documentation of current implementation gaps, not authorization to migrate them as part of an unrelated task.
