# Seed Data Status

## Current state

`backend/app/core/constants.py` declares `INITIAL_PERMISSIONS` and `SYSTEM_ROLES` for the IAM/RBAC catalog. These are Python constants; no seed-data engine, Alembic data migration, CLI command, or application-startup hook invoking them was found in the current repository.

The initial Alembic migration creates the IAM tables but does not insert these permissions or roles. Consequently, a database upgraded to the current schema is not necessarily populated with the predefined roles/permissions required for member authorization and workspace provisioning.

## Operational guidance

- Do not assume the constants have been inserted into a database.
- Before adding seed data, decide on an explicit, repeatable, idempotent mechanism and define how updates/deletes and existing tenant customizations are handled.
- Keep reference-data changes coordinated with schema and permission changes.
- Do not seed credentials, secrets, or environment-specific data.
- Review data migrations and obtain required approval before applying them to important environments.

See [IAM and RBAC](../03-modules/iam-rbac.md) for how permissions are resolved and [database and migrations](database-and-migrations.md) for schema history.
