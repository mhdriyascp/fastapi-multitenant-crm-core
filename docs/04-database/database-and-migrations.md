# Database Model and Migrations

## Database runtime

The backend uses SQLAlchemy's asynchronous engine and `AsyncSession`, configured from `DATABASE_URL` in `backend/app/core/config.py`. `backend/app/core/database/session.py` creates the engine and session factory. The FastAPI dependency yields a session, commits on normal completion, and rolls back when an exception escapes.

`backend/alembic/env.py` configures Alembic. Schema migrations are under `backend/alembic/versions/`.

## Persisted models

The model package currently includes:

- `users`, `tenants`, and `tenant_memberships`: global identities, workspaces, and user-to-workspace associations.
- `user_profiles`, `user_credentials`, `user_devices`, and `user_preferences`: optional extended profile data, authentication credentials, remembered device metadata, and global user preferences. Existing basic names/contact fields remain on `users` for API compatibility.
- `roles`, `permissions`, `role_permissions`, and `membership_roles`: RBAC catalog and assignments.
- `platform_user_roles`: platform operator role assignments. Tenant role assignments remain tied to `tenant_memberships`; the project intentionally does not use a single unscoped `user_roles` table.
- `teams` and `team_members`: tenant-owned teams and memberships. Composite foreign keys ensure a team assignment's user and team belong to the same tenant.
- `role_assignment_audits`: append-style role assignment/revocation history.
- `user_sessions`: hashed refresh tokens, tenant context, expiry, and revocation.
- `user_mfa_methods`: MFA method configuration (`email_otp`, `totp`, `webauthn`).
- `email_outbox`: email jobs, template payloads, delivery state, and attempt tracking.
- `platform_user_roles` and `platform_admin_audits`: platform operator grants and privileged action history.
- `subscription_plans`, `tenant_subscriptions`, and `tenant_settings`: platform-managed plan metadata, one current plan assignment per tenant, and allowlisted tenant preferences.
- `organizations`, `legal_entities`, `branches`, `departments`, `designations`, `teams`, `locations`, `business_units`, `cost_centers`, and `fiscal_years`: tenant-owned organization and operations structure.
- `currencies`, `countries`, `states`, `cities`, `time_zones`, `languages`, `units_of_measure`, and `tax_types`: shared reference catalogs. `tax_rates` stores tenant-specific rates and effective dates.


## Migration history

1. `2026_11_06_1637-3d40adf3e0fb_create_initial_10_table_iam_schema.py` creates the initial ten identity/IAM tables.
2. `2026_11_09_1554-8b29044d45d4_create_email_outbox_table.py` adds the email outbox.
3. `2026_11_10_0900-1c7d91e52a4f_platform_control_plane.py` adds platform operator roles/assignments, audit events, plans, tenant subscriptions/settings, and `roles.is_platform`.
4. `2026_11_10_1030-7f2c9e6d4a81_core_master_data.py` adds the organization, geographic, currency, language, unit, fiscal-year, and tax master tables.
5. `2026_11_10_1145-a92f5d6e8b31_identity_access_masters.py` adds user profile, credential, device, preference, and team membership tables. It copies existing password hashes into `user_credentials` before removing `users.hashed_password`.

These migration files are the schema evidence. Confirm the target database revision and inspect migration upgrade/downgrade code before applying a migration; this document does not assert that a particular database has been migrated.

## Identifier and lifecycle patterns

Most persisted identity/IAM models use UUIDv7 internal primary keys from `uuid_utils` and UUIDv4 `public_id` columns. Some current service/API schemas still use internal IDs, so public-ID-only API usage is not yet consistent.

`AuditableLifecycleBase` (in `app.models.base`) provides UTC `created_at`, nullable `updated_at`/`updated_by_id`, nullable indexed `deleted_at`/`deleted_by_id`, and a `status` column (`CommonStatus.ACTIVE` / `CommonStatus.INACTIVE`). The `User` model and `Role` model define their own timestamp and status columns rather than inheriting from this base.

`TenantMembership` has a plain `UniqueConstraint("tenant_id", "user_id")` (not a partial index on `deleted_at`). Soft-deleted memberships therefore block re-inviting the same user unless the existing soft-deleted row is handled first.

Role code uniqueness uses PostgreSQL partial indexes: `uq_roles_tenant_code` (where `tenant_id IS NOT NULL`) and `uq_roles_global_code` (where `tenant_id IS NULL`). These indexes are **not** filtered on `deleted_at`.

The initial users email and username indexes are non-partial unique indexes. Tenant slug is unique. The permission catalog has unique permission codes. Membership-role and role-permission associations have uniqueness constraints.

These conventions vary by model. Review the model and migration before relying on a global convention.

## RBAC seed data

Permissions and system roles defined in `backend/app/core/constants.py` are not inserted by Alembic migrations. The standalone script `backend/scripts/seed_rbac.py` performs idempotent synchronization. See [seed data](seed-data.md) for instructions and operational guidance.

## Data-access boundary status

The platform administration service uses `PlatformAdminRepository` for SQLAlchemy reads/writes. Other services still issue some SQLAlchemy queries directly.

## Platform control-plane persistence notes

- `platform_user_roles` uses `deleted_at`/`deleted_by_id`; its unique partial index covers only active assignments.
- `platform_admin_audits` records actor, optional tenant, public resource identifier, reason, and before/after JSON state. API mutations write the audit event in the same request transaction.
- `tenant_settings` has one JSONB row per tenant. The API validates its current allowlist (`locale`, `date_format`, and `branding`) before persistence.
- `subscription_plans` stores price and entitlements as platform catalog data; `tenant_subscriptions` stores a tenant's current plan and status. These records are not a billing ledger or payment integration.

Apply the migration and seed the expanded permission catalog using the documented `uv` commands in [Seed data](seed-data.md). Do not apply a migration to production without reviewing its upgrade/downgrade and taking the required database backup.
