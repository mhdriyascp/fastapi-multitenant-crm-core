# IAM and Role-Based Access Control

## Scope and implementation

Identity and access management models are in `backend/app/models/`; member-management routes live in `backend/app/api/tenant/v1/endpoints/members.py` and are registered under `/api/v1/iam/members/*`. They are not mounted outside a tenant API version. The service is `MemberService` in `backend/app/services/member_service.py`.

The RBAC dependency used by these routes is defined in `backend/app/api/dependencies/auth.py`. `backend/app/api/deps.py` remains as a compatibility re-export for existing imports.

## Data model

| Entity/table | Purpose |
|---|---|
| `users` | Global user identity and credentials |
| `tenants` | Organization/workspace |
| `tenant_memberships` | User-to-tenant membership and lifecycle |
| `roles` | Global roles (`tenant_id IS NULL`) and tenant-specific roles |
| `permissions` | Global catalog of module/resource/action capability codes |
| `role_permissions` | Many-to-many role-to-permission assignments |
| `membership_roles` | Many-to-many membership-to-role assignments |
| `role_assignment_audits` | Assignment and revocation history |
| `platform_user_roles` | Soft-revocable assignments of platform operator roles to global users |
| `platform_admin_audits` | Actor, reason, timestamp, and before/after state for platform mutations |

`Role.is_platform` identifies platform-control-plane roles separately from tenant roles. Platform roles remain global (`tenant_id IS NULL`) but cannot be used as tenant roles by the platform authorization dependency. Active operator assignments have a PostgreSQL partial unique index so a revoked assignment can later be restored. The permission catalog has unique permission codes.

`backend/app/core/constants.py` declares permission tuples and role definitions, including `platform_admin`, `org_owner`, `org_admin`, `member`, and `viewer`. These constants are populated into the database by the seed script `backend/scripts/seed_rbac.py`; the script must be run explicitly and is not invoked at application startup. See [Seed data](../04-database/seed-data.md).

## Permission resolution

For authenticated requests, `get_current_context` in `backend/app/api/dependencies/auth.py`:

1. Decodes `sub` and optional `tid` from the bearer token.
2. Loads an active, non-soft-deleted user.
3. Gives `is_platform_admin` users a wildcard permission set (`{"*"}`).
4. For a non-platform administrator with a tenant ID, loads an active membership and follows membership roles to active roles and active permissions.
5. Returns `AuthenticatedContext(user, tenant_id, permissions)`.

`RequirePermission("iam.membership.read")` checks for an exact code, except that `*` bypasses the check. If the token has no tenant claim, the current dependency returns an empty permission set for non-platform admins.

## Platform control plane

The control plane has its own versioned namespace and documentation and is not mounted under tenant API versions:

- API prefix: `/platform/v1`
- ReDoc: `/platform/v1/redoc`; OpenAPI: `/openapi/platform/v1.json`
- Scalar: `/scalar/platform/v1`
- Shared `/auth/*` endpoints are used for sign-in; the control-plane schema also includes `/health`.

Every control-plane operation uses `RequirePlatformPermission`, which authenticates the global user without depending on tenant context and requires a verified MFA method. A platform superadmin (`users.is_platform_admin`) is explicitly granted the platform wildcard. Other users need an active `platform_user_roles` assignment and the requested code on one of its active `RolePermission` links. Tenant membership and tenant-scoped roles do not grant platform access.

Platform permission codes are declared in `INITIAL_PERMISSIONS` and seeded with `uv run python scripts/seed_rbac.py`. Permission definitions are code-managed; the API exposes a read-only catalog. Superadmins can manage platform roles and grants in the dashboard. For a non-superadmin operator, role grants and role assignments are constrained to permissions the actor already holds, preventing privilege escalation through the control plane.

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/platform/v1/iam/permissions` | `platform.permission.read` | Browse the code-defined permission catalog |
| GET/POST | `/platform/v1/iam/roles` | `platform.role.read` / `platform.role.manage` | List and create platform operator roles |
| PUT | `/platform/v1/iam/roles/{role_public_id}/permissions` | `platform.role.manage` | Replace a role's permission grants |
| GET | `/platform/v1/operators` | `platform.operator.read` | List active platform operators |
| GET | `/platform/v1/operator-candidates` | `platform.operator.manage` | List active existing users eligible for platform-role assignment |
| GET | `/platform/v1/operators/{user_public_id}` | `platform.operator.read` | Read an operator's assignments |
| PUT | `/platform/v1/operators/{user_public_id}/roles` | `platform.operator.manage` | Replace a user's platform operator roles |
| GET/PATCH | `/platform/v1/tenants` and `/platform/v1/tenants/{tenant_public_id}` | `platform.tenant.read` / `platform.tenant.update` | List tenants and update profile/lifecycle status |
| GET/PUT | `/platform/v1/tenants/{tenant_public_id}/settings` | `platform.tenant.read` / `platform.tenant_settings.manage` | Read or replace allowlisted locale/date/branding settings |
| GET/POST/PATCH | `/platform/v1/plans` and `/platform/v1/plans/{plan_public_id}` | `platform.plan.read` / `platform.plan.manage` | Read and manage plan catalog metadata |
| GET/PUT | `/platform/v1/tenants/{tenant_public_id}/subscription` | `platform.plan.read` / `platform.plan.manage` | Read or assign a tenant plan |
| GET | `/platform/v1/audit-events` | `platform.audit.read` | Read privileged platform mutation history |

Privileged write requests require a reason and write audit events in the same database transaction as their state changes. Public routes and responses use UUIDv4 public identifiers. Suspending or cancelling a tenant removes tenant permissions on subsequent requests while keeping account-level authentication and platform recovery available. Tenant settings are deliberately restricted to locale, date format, and branding; arbitrary secrets and infrastructure configuration are not editable through this API.

Plan prices and entitlements are catalog metadata only: this implementation does not charge customers, reconcile invoices, or integrate a payment processor. Operators can assign roles only to an existing active user; the protected operator-candidates endpoint lists eligible accounts, while invitation/provisioning is outside this API. The built-in superadmin flag is not changeable through dashboard endpoints and must be provisioned through a controlled bootstrap process.

## Registered member operations

| Method | Canonical path | Permission dependency | Operation |
|---|---|---|---|
| GET | `/api/v1/iam/members/` | `iam.membership.read` | List tenant members (non-deleted, all statuses) |
| POST | `/api/v1/iam/members/invite` | `iam.membership.create` | Create/associate user, membership, requested roles, audit rows, and invitation outbox record |
| DELETE | `/api/v1/iam/members/{membership_id}` | `iam.membership.delete` | Soft-delete the membership and set status to `REVOKED` |
| GET | `/api/v1/iam/members/roles` | `iam.role.read` | List active global and tenant roles except `platform_admin` |
| PATCH | `/api/v1/iam/members/{membership_id}/roles` | `iam.role_assignment.assign` | Replace assigned role codes and record assignment/revocation audit rows |

The route and service currently use internal UUID membership and role identifiers in some paths and responses rather than exclusively using UUIDv4 public IDs.

Tenant v2 does not yet expose member routes. Shared authentication remains under `/auth/*`, and shared health remains under `/health`.

## Member removal behavior

`MemberService.remove_member` performs a soft-delete:
- Sets `deleted_at` to current UTC.
- Sets `deleted_by_id` to the authenticated actor.
- Sets `membership.status` to `MembershipStatus.REVOKED` (`"revoked"` string value). The fallback `getattr(..., MembershipStatus.SUSPENDED)` in the code is defensive; `REVOKED` exists in the enum.
- Prevents self-removal: an actor cannot remove their own membership.

## Audit behavior

`RoleAssignmentAudit` stores membership, role, action (`assigned` or `revoked`), actor (`performed_by`), timestamp, and optional reason. Invitation creates assignment audit rows for each role. Updating roles writes rows for additions and removals. The `MembershipRole` row is physically deleted on revoke; the audit row retains the event record.

## Current gaps and cautions

- `MemberService` currently contains direct SQLAlchemy statements even though `MemberRepository` exists; repository adoption is incomplete. Domain exceptions (`EntityNotFoundException`, `EntityConflictException`, `BusinessRuleViolationException`, `PermissionDeniedException`) are used instead of `HTTPException` for service-level failures.
- `RequirePermission` is attached to the five member endpoints, but not every route in the application has an explicit permission dependency. For example, `/auth/mfa/email/toggle` only depends on the authenticated context.
- Role and permission constants are seeded by `backend/scripts/seed_rbac.py`, which must be run explicitly; there is no automatic startup seeding.
- Tenant member APIs and the platform control plane have different authorization dependencies; do not use tenant `RequirePermission` as a substitute for `RequirePlatformPermission`.
- The platform control plane does not provide payment processing, plan-to-feature enforcement in tenant business services, invitation/provisioning, or secret/infrastructure configuration management.
- This document describes the current guard behavior, not a comprehensive security audit. Verify tenant scope and authorization separately for any new endpoint or query.

## Related code

- Route: `backend/app/api/tenant/v1/endpoints/members.py`
- Context/guard: `backend/app/api/dependencies/auth.py`
- Service: `backend/app/services/member_service.py`
- Constants: `backend/app/core/constants.py`
- Seed script: `backend/scripts/seed_rbac.py`
- Enums: `backend/app/core/enums.py`
- Models: `role.py`, `permission.py`, `role_permission.py`, `tenant_membership.py`, `membership_role.py`, `role_assignment_audit.py`
- Schema/migration overview: [Database and migrations](../04-database/database-and-migrations.md)
