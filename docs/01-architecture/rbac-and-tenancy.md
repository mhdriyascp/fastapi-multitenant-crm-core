# RBAC and Tenant Architecture

## Model

The current identity model separates global users from workspaces:

```text
User ──< TenantMembership >── Tenant
              │
              └──< MembershipRole >── Role ──< RolePermission >── Permission
```

- A `TenantMembership` links a global user to one tenant and carries membership status.
- A `Role` with `tenant_id IS NULL` is global; a role with a tenant ID belongs to that tenant.
- `MembershipRole` assigns roles to a membership.
- `RolePermission` maps roles to permission catalog entries.
- `RoleAssignmentAudit` records role assignment/revocation actor, action, reason, and timestamp.

The model and route details are in [IAM and RBAC implementation](../03-modules/iam-rbac.md).

## Request authorization flow

The mounted member routes use `get_current_context` and `RequirePermission` in `backend/app/api/deps.py`:

1. Validate the bearer token and load an active user.
2. Read the optional tenant identifier from the token's `tid` claim.
3. Give platform administrators a wildcard permission set.
4. For a tenant-scoped user, require an active membership and load role and permission relationships.
5. At the route dependency, check for the required permission code.
6. Pass the resulting tenant context to the member service.

The permissions used by the registered member endpoints are `iam.membership.read`, `iam.membership.create`, `iam.membership.delete`, `iam.role.read`, and `iam.role_assignment.assign`.

## Current implementation boundaries

- Member API checks are explicit, but the same dependency/guard pattern is duplicated in `backend/app/iam/dependencies.py`.
- Services currently issue ORM queries directly; there is no dedicated repository package.
- The member service performs tenant filters on membership operations, but tenant-scoping must still be verified per query and feature.
- Permission and predefined role constants are declared in `backend/app/core/constants.py`; automatic database seeding was not found in application startup.
- The role model's current role-code indexes distinguish global from tenant roles, but do not filter on `deleted_at`.
- Not all application routes use `RequirePermission`; authentication routes have their own authentication semantics.

This describes observed implementation and is not a security certification. For requirements on new work, see [AGENTS.md](../../AGENTS.md).
