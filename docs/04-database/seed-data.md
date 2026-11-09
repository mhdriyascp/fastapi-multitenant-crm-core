# Seed Data Status

## Current state

`backend/app/core/constants.py` declares `INITIAL_PERMISSIONS` and `SYSTEM_ROLES` for the IAM/RBAC catalog. These are Python constants used by the seed script; they are not inserted by Alembic migrations or by any application-startup hook.

`backend/scripts/seed_rbac.py` is a standalone CLI script that performs full, idempotent synchronization of permissions and system roles against a live database. It can be run directly:

```sh
cd backend
uv run python scripts/seed_rbac.py
```

The script:
- Inserts missing permissions from `INITIAL_PERMISSIONS` and updates description/action metadata when changed.
- Inserts missing system roles from `SYSTEM_ROLES` and syncs name/description.
- **Two-way permission sync**: adds newly required role→permission links and prunes obsolete ones (links removed from the constant definition are deleted from `role_permissions`).
- Wraps all mutations in a single database transaction; the entire operation rolls back on failure.
- Reads `DATABASE_URL` from the environment (falls back to the local development default).

A database migrated to the current schema is **not automatically seeded**. An operator must run `seed_rbac.py` to populate the RBAC catalog before member invitation and permission checking work correctly.

## Operational guidance

- Run `seed_rbac.py` after migrating a fresh database and after adding new permissions or roles to `constants.py`.
- The script is idempotent and safe to re-run; existing data is updated in-place, not duplicated.
- The two-way sync means removing a permission assignment from a `SYSTEM_ROLES` entry and re-running the script will revoke that link in the database. Review the diff carefully before running against production environments.
- Do not seed credentials, secrets, or environment-specific data.
- Obtain required approval before applying data changes to important environments.

The platform control-plane permission codes (`platform.*`) are also declared in `INITIAL_PERMISSIONS` and are inserted by this script. Dashboard-created platform operator roles and their `role_permissions` are not in `SYSTEM_ROLES` and are not rewritten by system-role synchronization. The built-in role definitions, including the seeded `platform_admin` system role, remain code-managed.

See [IAM and RBAC](../03-modules/iam-rbac.md) for how permissions are resolved and [database and migrations](database-and-migrations.md) for schema history.
