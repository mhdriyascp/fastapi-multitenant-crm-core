# IAM and Role-Based Access Control

## Scope and implementation

Identity and access management models are in `backend/app/models/`; member-management API routes live in `backend/app/api/v1/endpoints/members.py`. The versioned router registers this module at `/api/v1/iam/members`. The service is `MemberService` in `backend/app/services/member_service.py`.

The RBAC dependency used by these routes is defined in `backend/app/api/deps.py`. A similar implementation also exists in `backend/app/iam/dependencies.py`; the mounted member router uses `app.api.deps`.

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

Role codes have global and tenant-scoped unique indexes in the initial migration. The permission catalog has unique permission codes. Membership, membership-role, and role-permission associations also have uniqueness constraints.

`backend/app/core/constants.py` declares permission tuples and role definitions, including `platform_admin`, `org_owner`, `org_admin`, `member`, and `viewer`. The inspected application startup does not invoke a seeding routine for these constants; do not assume the definitions have been inserted into a database.

## Permission resolution

For authenticated requests, `get_current_context`:

1. Decodes `sub` and optional `tid` from the bearer token.
2. Loads an active, non-soft-deleted user.
3. Gives `is_platform_admin` users a wildcard permission set (`{"*"}`).
4. For a non-platform administrator with a tenant ID, loads an active membership and follows membership roles to active roles and active permissions.
5. Returns `AuthenticatedContext(user, tenant_id, permissions)`.

`RequirePermission("iam.membership.read")` checks for an exact code, except that `*` bypasses the check. If the token has no tenant claim, the current dependency returns an empty permission set for non-platform admins.

## Registered member operations

| Method | Registered path | Permission dependency | Operation |
|---|---|---|---|
| GET | `/api/v1/iam/members/` | `iam.membership.read` | List tenant members |
| POST | `/api/v1/iam/members/invite` | `iam.membership.create` | Create/associate user, membership, requested roles, audit rows, and invitation outbox record |
| DELETE | `/api/v1/iam/members/{membership_id}` | `iam.membership.delete` | Mark membership deleted and change its status |
| GET | `/api/v1/iam/members/roles` | `iam.role.read` | List active global and tenant roles except platform-admin |
| PATCH | `/api/v1/iam/members/{membership_id}/roles` | `iam.role_assignment.assign` | Replace assigned role codes and record assignment/revocation audit rows |

The route/service currently uses internal UUID membership/role identifiers in some paths/responses rather than exclusively using UUIDv4 public IDs.

## Audit behavior

`RoleAssignmentAudit` stores membership, role, action (`assigned` or `revoked`), actor, timestamp, and optional reason. Invitation creates assignment audit rows. Updating roles writes rows for additions/removals. The role association itself is deleted on revoke; the audit row retains a record of the event.

Removing a member sets `deleted_at` and `deleted_by_id`; the current code sets a membership status via `MembershipStatus.REVOKED` with a fallback to `SUSPENDED`. It does not set a generic `"archived"` status.

## Current gaps and cautions

- `MemberService` currently contains direct SQLAlchemy statements and raises `HTTPException`; a repository layer and domain-only exception boundary are not yet consistently implemented.
- `RequirePermission` is attached to the five member endpoints, but not every route in the application has an explicit permission dependency. For example, `/auth/mfa/email/toggle` only depends on the authenticated context.
- Role definitions are constants, not automatically seeded by startup code found in the inspected implementation.
- Permission code definitions include IAM permissions. No CRM lead routes are currently mounted with `crm.lead.*` permission checks.
- `PermissionDeniedException` is named in engineering standards but is not defined in the current `app.core.exceptions` module.
- This document describes the current guard behavior, not a comprehensive security audit. Verify tenant scope and authorization separately for any new endpoint or query.

## Related code

- Route: `backend/app/api/v1/endpoints/members.py`
- Context/guard: `backend/app/api/deps.py`
- Service: `backend/app/services/member_service.py`
- Constants: `backend/app/core/constants.py`
- Enums: `backend/app/core/enums.py`
- Models: `role.py`, `permission.py`, `role_permission.py`, `tenant_membership.py`, `membership_role.py`, `role_assignment_audit.py`
- Schema/migration overview: [Database and migrations](../04-database/database-and-migrations.md)
