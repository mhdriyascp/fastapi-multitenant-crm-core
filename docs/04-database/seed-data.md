# Seed Data and Initial Setup

## Seed package

Seed commands are organized under `backend/scripts/seed/`. They are explicit
operations, not part of application startup. From `backend/`, run the complete
initial setup after applying migrations:

```sh
uv run python -m scripts.seed
```

The full command synchronizes RBAC, seeds shared and tenant master data,
creates navigation menus, and provisions local demo accounts. Demo accounts
require six distinct passwords in `backend/.env`; user seeding is restricted
to development and test environments. Use `--without-demo-users` to omit
accounts.

To synchronize only permissions and system roles:

```sh
uv run python -m scripts.seed.rbac
```

The RBAC command:
- Inserts missing permissions from `INITIAL_PERMISSIONS` and updates description/action metadata when changed.
- Inserts missing system roles from `SYSTEM_ROLES` and syncs name/description.
- **Two-way permission sync**: adds newly required role→permission links and prunes obsolete ones (links removed from the constant definition are deleted from `role_permissions`).
- Wraps all mutations in a single database transaction; the entire operation rolls back on failure.

A database migrated to the current schema is **not automatically seeded**.
Run the full seed or RBAC-only command before member invitation and permission
checking rely on the RBAC catalog.

## Operational guidance

- Run the full seed after migrating a fresh local database. Use the RBAC-only
  command after adding permissions or roles to `constants.py` when master data
  and demo accounts do not need to be synchronized.
- Both commands are idempotent; existing data is updated in-place, not duplicated.
- The two-way sync means removing a permission assignment from a `SYSTEM_ROLES` entry and re-running the script will revoke that link in the database. Review the diff carefully before running against production environments.
- Demo-account passwords are read from local environment configuration and
  stored only as password hashes. Never commit or share real password values.
- Obtain required approval before applying data changes to important environments.

The platform control-plane permission codes (`platform.*`) are declared in
`INITIAL_PERMISSIONS`. Dashboard-created platform operator roles and their
`role_permissions` are not in `SYSTEM_ROLES` and are not rewritten by
synchronization. Built-in role definitions, including `platform_admin`, remain
code-managed.

See [IAM and RBAC](../03-modules/iam-rbac.md) for how permissions are resolved and [database and migrations](database-and-migrations.md) for schema history.

## Core and CRM master-data seed

After applying migrations through the CRM master-data revision and configuring
the six distinct demo account passwords described below, seed the shared
reference catalogs, tenant master data, menus, and demo users:

```sh
cd backend
uv run alembic upgrade navigation@head
uv run python -m scripts.seed
```

The navigation upgrade creates the `menus` and `menu_permissions` tables. It
does not apply the separate ERP migration.

The standard seed command creates the platform admin and four
demo-organization users. Use `--without-demo-users` only when you need to seed
master data without accounts.

The command is idempotent and uses `SEED_TENANT_NAME` and `SEED_TENANT_SLUG`
when provided; otherwise it targets the `Demo Organization` tenant with slug
`demo-organization`. It creates the tenant only if that slug is unused and
fails rather than renaming a different tenant or reactivating a deleted one.
Tenant-specific records are scoped to that tenant. Existing non-deleted
reference rows are preserved rather than overwritten.

The seed inserts examples into each core and CRM lookup/master table. It does
not create CRM transactions or ERP data. Global shared references in this seed
include India, INR, Karnataka, Bengaluru, Asia/Kolkata, English, Hindi, common
units of measure, and GST classification. The sample tax rate is inactive and
must be configured for the applicable jurisdiction before use.

The permission catalog gains `master_data.*` and `crm.*` create/read/update/delete
permissions for core and CRM master resources. These permissions are assigned
to the existing `org_owner` and `org_admin` system roles; `member` and `viewer`
receive none of the new grants. Existing platform-admin wildcard synchronization
continues to include all catalog permissions. This seeds permission records and
role mappings only. The core/CRM master-data API and its route permissions are
documented in [master-data APIs](../03-modules/master-data-apis.md).

The same command idempotently seeds a global starter navigation catalog:
Dashboard and Members are available to all built-in tenant roles; Access
Control, Core Setup, Reference Data, and CRM Setup are linked to their matching
read permissions and appear only when a login user's effective role grants
those permissions. Each migrated master-data resource gets a sorted child
menu. These are shared definitions, not per-user copies; the authenticated
menu endpoint filters them at request time. The current frontend does not yet
implement these `/dashboard/...` pages.

### Local demo accounts

The login emails and six distinct passwords (12-128 characters each) are
configurable in the ignored `backend/.env` file. The email defaults are shown
below; change them before the first seed run if you prefer different demo
logins. Each password must be unique:

```env
SEED_PLATFORM_ADMIN_EMAIL=platform-admin@example.com
SEED_PLATFORM_ADMIN_PASSWORD=replace-with-unique-platform-secret
SEED_PLATFORM_SUPPORT_EMAIL=platform-support@example.com
SEED_PLATFORM_SUPPORT_PASSWORD=replace-with-unique-platform-support-secret
SEED_ORGANIZATION_OWNER_EMAIL=owner@demo-organization.example.com
SEED_ORGANIZATION_OWNER_PASSWORD=replace-with-unique-owner-secret
SEED_ORGANIZATION_ADMIN_EMAIL=admin@demo-organization.example.com
SEED_ORGANIZATION_ADMIN_PASSWORD=replace-with-unique-admin-secret
SEED_ORGANIZATION_MEMBER_EMAIL=member@demo-organization.example.com
SEED_ORGANIZATION_MEMBER_PASSWORD=replace-with-unique-member-secret
SEED_ORGANIZATION_VIEWER_EMAIL=viewer@demo-organization.example.com
SEED_ORGANIZATION_VIEWER_PASSWORD=replace-with-unique-viewer-secret
```

Replace all password placeholders with real secrets; do not commit or share
them. The configured email addresses are the accounts' login names. Then run
the standard seed command (shown above).

The seed creates a platform superadmin (`platform-admin@example.com`) and
one platform support operator (`platform-support@example.com`), plus four
active users in the seeded Demo Organization:
`owner@demo-organization.example.com`, `admin@demo-organization.example.com`,
`member@demo-organization.example.com`, and
`viewer@demo-organization.example.com`. Each receives the corresponding
built-in role. Account passwords are stored as Argon2 hashes and never
printed. The seed does not reset passwords or elevate an existing account
whose platform-admin flag does not match.

The support operator is a separate, non-superadmin account assigned the
code-managed `platform_support` role. It can read tenant accounts and platform
audit events only; it has no tenant membership and cannot update tenants,
manage plans, or assign operator roles. The platform role and its permission links are synchronized on each seed run.
New account-to-role assignments are recorded in `platform_admin_audits`. An
existing account without this role is not automatically promoted by the seed.

Demo-user creation is restricted to `ENVIRONMENT=development` or `test`.
Creating the demo users activates the seeded organization if it is still in
the initial trial state; suspended or cancelled organizations are not
reactivated. Platform admin and support users must enable and verify MFA
before platform administration is available. For each platform account, log
in, enable email OTP using `POST /auth/mfa/email/toggle` with that account's
password, then log in again and complete the OTP challenge. Email delivery
requires the local SMTP/Mailpit setup.
