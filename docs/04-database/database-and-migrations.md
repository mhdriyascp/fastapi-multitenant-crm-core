# Database Model and Migrations

## Database runtime

The backend uses SQLAlchemy's asynchronous engine and `AsyncSession`, configured from `DATABASE_URL` in `backend/app/core/config.py`. `backend/app/core/database/session.py` creates the engine and session factory. The FastAPI dependency yields a session, commits on normal completion, and rolls back when an exception escapes.

`backend/alembic/env.py` configures Alembic. Schema migrations are under `backend/alembic/versions/`.

## Persisted models

The model package currently includes:

- `users`, `tenants`, and `tenant_memberships`: global identities, workspaces, and user-to-workspace associations.
- `roles`, `permissions`, `role_permissions`, and `membership_roles`: RBAC catalog and assignments.
- `role_assignment_audits`: append-style role assignment/revocation history.
- `user_sessions`: hashed refresh tokens, tenant context, expiry, and revocation.
- `user_mfa_methods`: MFA method configuration.
- `email_outbox`: email jobs and delivery state.

There is no SQLAlchemy lead model in `backend/app/models/`; leads are currently held in memory (see [CRM leads](../03-modules/crm-leads.md)).

## Migration history

1. `2026_11_06_1637-3d40adf3e0fb_create_initial_10_table_iam_schema.py` creates the initial ten identity/IAM tables.
2. `2026_11_09_1554-8b29044d45d4_create_email_outbox_table.py` adds the email outbox.

These migration files are the schema evidence. Confirm the target database revision and inspect migration upgrade/downgrade code before applying a migration; this document does not assert that a particular database has been migrated.

## Identifier and lifecycle patterns

Most persisted identity/IAM models use UUIDv7 internal primary keys from `uuid_utils` and UUIDv4 `public_id` columns. Some current service/API schemas still use internal IDs, so public-ID-only API usage is not yet consistent.

`AuditableLifecycleBase` provides UTC `created_at`, nullable update fields, nullable indexed `deleted_at`, nullable `deleted_by_id`, and a common active/inactive status for inheriting entities. Other models define their own timestamp/status columns. `TenantMembership` has a unique `(tenant_id, user_id)` constraint; the initial users email and username indexes are unique; tenant slug is unique. The role model defines separate partial unique indexes for global and per-tenant role codes.

These conventions vary by model. In particular, not every table is tenant-owned, not every uniqueness index is partial on `deleted_at`, and lifecycle behavior differs by entity. Review the model and migration before relying on a global convention.

## Data-access boundary status

No dedicated `backend/app/repositories/` package currently exists. `AuthService` and `MemberService` issue SQLAlchemy queries directly. The class named `LeadRepository` is an in-memory implementation in the API dependency package, not a database repository.
