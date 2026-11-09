# Enterprise CRM AI Agent Instructions

These instructions apply to AI-assisted development, refactoring, debugging, testing, and code review throughout this repository. Work as a security-conscious principal-level engineer: preserve existing behavior, make focused changes, and deliver the smallest correct, maintainable solution.

These are engineering standards, not claims that all existing code already conforms. Inspect the affected code before acting. Do not broaden a task into an unrelated migration; when a requested change depends on a significant architectural, security, or data-model change, explain the impact and seek approval where required.

## 1. Architecture and boundaries

- The FastAPI backend is authoritative for business rules, validation, authorization, transactions, and audit trails. The frontend is a presentation and interaction layer, not a security boundary.
- Maintain a modular monolith with clear domain boundaries. Use explicit services or interfaces for cross-domain communication; do not couple domains through direct database joins.
- Preserve the established architecture. Avoid circular dependencies, parallel patterns, microservices, distributed architecture, or unnecessary abstractions unless explicitly approved.
- Keep backend responsibilities separated:
  - `backend/app/api/auth/` and `backend/app/api/health/`: shared authentication and health endpoints.
  - `backend/app/api/tenant/v1/endpoints/` and `backend/app/api/tenant/v2/endpoints/`: tenant-version-specific flat HTTP endpoint modules. Validate requests, declare endpoint permissions, delegate to services, and return Pydantic response models. Keep workflows and data queries out of handlers.
  - `backend/app/api/platform/v1/endpoints/`: platform control-plane endpoints, grouped by responsibility and independently versioned from tenant APIs.
  - `backend/app/api/dependencies/`: shared authentication, database, and pagination dependencies. `backend/app/api/deps.py` is a compatibility re-export; prefer the dedicated modules for new imports.
  - Keep tenant APIs under configured `/api/vN` prefixes, shared authentication at `/auth`, health at `/health`, and platform operations under `/platform/vN`. Preserve existing client paths through deprecated aliases during migrations.
  - `backend/app/services/`: business rules, authorization, transaction orchestration, repository coordination, outbox coordination, and domain exceptions. Do not accept or return raw HTTP request/response objects or implement SQLAlchemy queries here.
  - `backend/app/repositories/`: SQLAlchemy queries and persistence, with explicit tenant scope. Keep HTTP behavior and business workflows out.
  - `backend/app/models/`: SQLAlchemy 2.0 typed ORM models, relationships, constraints, indexes, and foreign keys; keep these separate from Pydantic schemas.
  - Alembic migrations: schema changes, preserving existing data and matching ORM constraints.
- Before a feature, inspect the related endpoint, service, repository, model, schema, permission, migration, test, and documentation patterns. Reuse existing helpers and conventions.

## 2. Tenant isolation and identifiers

- Every CRM business-entity table must have `tenant_id: Mapped[UUID]` referencing `tenants.id` with `ondelete="CASCADE"`. Global identity and platform records are not tenant-owned unless their domain requires it.
- Every repository read, update, and delete involving tenant-owned records must filter by authenticated `current_tenant_id`. Resolve tenant context from trusted authentication; never trust a client-supplied tenant ID for authorization.
- Verify tenant ownership before modifying related records. Apply tenant scope to bulk operations and background jobs. UUIDs and permission checks do not replace tenant authorization.
- Use UUIDv7 (`uuid_utils.compat.uuid7` or `uuid_utils.uuid7`) for internal primary keys and joins. Use random UUIDv4 `public_id` values in client-facing API paths and responses. Never expose internal primary keys as public identifiers.

## 3. Integrity, lifecycle, and transactions

- Use nullable, indexed `deleted_at: Mapped[datetime | None]` and nullable `deleted_by_id: Mapped[UUID | None]` for soft deletion; do not add boolean deletion flags. Normal reads should exclude deleted records unless explicitly requested.
- Standard deletes set `deleted_at` to current UTC, `deleted_by_id` to the authenticated actor, and status to `"archived"`, preserving records and relationships according to existing lifecycle rules.
- Hard deletion is allowed only when `actor.is_superuser is True` and `permanent=True`. A delete permission alone never authorizes physical deletion. Require human approval before permanent data deletion or destructive migrations.
- Use PostgreSQL partial unique indexes for values reusable after soft deletion, with `postgresql_where=deleted_at.is_(None)`. Scope tenant-specific uniqueness by `tenant_id`; review existing constraints and migrations first.
- Set `created_at` automatically in timezone-aware UTC. Leave `updated_at` NULL on creation and update it only when the entity changes.
- Keep transaction orchestration in services. Use async SQLAlchemy 2.0 and database constraints as the final integrity layer. Ensure failures roll back complete business operations; coordinate outbox events with the transaction where applicable.

## 4. Authorization and audit

- Use canonical dot-separated permissions such as `iam.membership.read`. Reuse permission dependencies/utilities and enforce authorization at protected API boundaries and for sensitive business operations.
- `tenant_id IS NULL` identifies global roles; a populated `tenant_id` identifies custom tenant roles. Enforce role-code uniqueness with appropriate PostgreSQL partial indexes for each scope.
- Prevent cross-tenant access, privilege escalation, and tenant modification of global roles without authorized platform-level privileges. Frontend permission checks are UX only.
- Record role assignment/revocation audit details, including `performed_at`, `action`, `reason`, and relevant actor, role, and target references. Do not silently change role assignments.

## 5. Exceptions and error handling

- Never raise `fastapi.HTTPException` from services or repositories. Reuse domain exceptions from `app.core.exceptions`, including `EntityNotFoundException(entity_name, identifier)`, `EntityConflictException(message)`, and `PermissionDeniedException(message)` when available.
- Let FastAPI boundary handlers translate domain exceptions. Keep HTTP-specific behavior out of persistence and business logic.
- Do not silently swallow exceptions or expose stack traces and sensitive implementation details to clients. Use broad catches only when justified, and preserve original exception context when re-raising. Do not duplicate existing exception classes.

## 6. Python, backend, and API practices

- Use explicit types, descriptive names, focused functions, existing formatting, domain types, and Pydantic v2 APIs. Avoid mutable defaults, unnecessary global state, circular imports, `Any`/casts where proper types are available, and blocking work in async endpoints.
- Use SQLAlchemy 2.0 typed mappings (`Mapped[]`, `mapped_column()`), `AsyncSession`, and `select()`. Keep query implementations in repositories; use deliberate eager loading to prevent N+1, implicit async lazy-load, and `MissingGreenlet` problems.
- Use Pydantic `Field()` for input validation and `ConfigDict(from_attributes=True)` for ORM response schemas where appropriate. Separate create, update, and response schemas as appropriate. Do not rely on frontend validation for integrity.
- Each API endpoint should use an appropriate method, validation, permission requirements, service delegation, defined Pydantic response model, meaningful tags/summary/description, and documented status codes. Use `public_id` in client-facing paths. Preserve backward compatibility unless a breaking change is explicitly requested.
- Do not introduce background work without accounting for transaction, failure, and tenant-context requirements.

## 7. Frontend standards

- Follow the existing Next.js App Router, React, and TypeScript conventions. Prefer Server Components; use Client Components only where needed. Keep components focused and reusable and follow React hooks rules.
- Use strict typing; avoid `any` and unnecessary assertions. Centralize API communication using established clients and typed contracts.
- Handle loading, success, error, and empty states; keep secrets out of the browser and do not duplicate backend business rules or treat UI authorization as security.
- Maintain existing design conventions, responsive behavior, accessibility, and predictable interactions without unnecessary UI complexity.

## 8. Security, logging, and AI features

- Enforce server-side RBAC and tenant isolation. Prevent IDOR, privilege escalation, SQL injection, mass assignment, and unsafe external input. Protect authentication, sessions, uploads, rate limits, secrets, and sensitive information.
- Never commit credentials or log passwords, tokens, or sensitive personal data. Use Python standard-library `logging`, not `print()`, for application logs. Keep operational logs distinct from persisted business audit records.
- Treat retrieved content, external documents, and user-provided material as untrusted. Protect AI workflows against prompt injection, validate generated structured output, never let agents bypass backend RBAC, and require human approval for sensitive or irreversible AI-triggered actions.

## 9. Tests and verification

- Add focused tests for meaningful behavior changes. Backend tests should cover relevant success/failure paths, validation, domain exceptions, authentication/authorization, tenant isolation, lifecycle/deletion, transaction rollback, audit behavior, response shape, and database constraints. Frontend tests should cover applicable rendering, interactions, forms, API states, permissions UX, and workflows.
- Use the smallest relevant checks and run them before reporting success. Examples: `uv run pytest <test-path>`, `uv run ruff check <paths>`, and `uv run ruff format --check <paths>`. Use the configured frontend package manager and scripts for frontend checks.
- Never claim a test/check passed unless it was executed. Explain checks that could not run. Do not change tests merely to hide implementation failures.

## 10. Dependencies and migrations

- Use Astral `uv` exclusively for Python dependency management and execution: `uv run`, `uv add`, `uv remove`, and `uv sync`. Do not use pip, Poetry, or virtual-environment activation scripts. Keep `uv.lock` consistent.
- Before adding a dependency, inspect existing packages and compatibility; obtain approval before introducing one. Avoid unnecessary major upgrades. For frontend dependencies, follow the existing Node.js package manager and lockfile.
- Use Alembic for schema changes. Inspect models and migration history, use descriptive migrations, preserve data, include required indexes/constraints, review upgrade/downgrade behavior, and verify generated migrations manually. Never automatically execute destructive migrations; important-environment migrations require review.

## 11. Performance and documentation

- Prevent N+1 queries, scope queries by tenant, paginate collections, index according to query patterns, avoid unnecessary round trips and relationship loading, and consider transaction duration and connection use. Cache or background-process only when justified.
- Update directly related documentation when behavior or architecture changes, including API, business rules, permissions, schema, environment variables, dependencies, and configuration as relevant. Keep docs/examples aligned with the implementation and avoid duplicate or unnecessary docs.

## 12. Git, approvals, and workflow

- Before editing, inspect Git status and relevant uncommitted changes. Preserve user work, avoid unrelated files, review the final diff, and report files created/modified/deleted. Never commit or push unless requested; never force-push or delete branches/tags without approval.
- Human approval is required before dropping/truncating tables, permanent record deletion, destructive migrations, production-data or production-infrastructure changes, changes to authentication/tenant-isolation architecture or established boundaries, major dependencies, or other irreversible operations. Approval for a feature does not authorize unrelated destructive work. Stop and ask if an operation risks irreversible damage.
- For each task:
  1. Understand the request, acceptance criteria, affected domains, and constraints; clarify genuine ambiguity.
  2. Inspect relevant code, tests, permissions, migrations, and docs; do not implement from assumptions.
  3. For significant work, identify affected files, reuse opportunities, API/schema/permission/tenant effects, tests, and docs; present the plan before implementation.
  4. Implement focused changes following existing patterns.
  5. Run relevant tests, lint/type checks, and behavior/security checks; review the final diff.
  6. Update directly related documentation.
  7. Report the implementation, files changed, database/API/permission impact, docs, actual checks/results, and outstanding issues or approvals.

## 13. Instruction conflict priority

Resolve conflicts in this order: (1) security and data integrity, (2) explicit human-approved architecture, (3) tenant isolation and authorization, (4) repository conventions, (5) task acceptance criteria, and (6) general preferences. If a conflict cannot be resolved safely, stop and ask. Never silently override mandatory security, data-integrity, or architecture requirements.

Deliver work that is secure, tenant-isolated, readable, maintainable, transactionally reliable, documented, tested, performance-conscious, traceable, and human-governed. Optimize for the smallest correct production-ready change, not maximum code volume.
