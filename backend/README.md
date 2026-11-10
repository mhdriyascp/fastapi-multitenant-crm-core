# ⚙️ Enterprise CRM & IAM — Backend Service

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0%20(Async)-d71f00.svg)](https://www.sqlalchemy.org/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16%20(pgvector)-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis 7](https://img.shields.io/badge/Redis-7-dc382d.svg?logo=redis&logoColor=white)](https://redis.io/)
[![ARQ Queue](https://img.shields.io/badge/Worker-ARQ%20Async-brightgreen.svg)](https://arq-docs.helpmanual.io/)
[![uv](https://img.shields.io/badge/Package%20Manager-Astral%20uv-DE5FE9.svg)](https://github.com/astral-sh/uv)

The backend service is a production-grade, multi-tenant modular monolith built with FastAPI and SQLAlchemy 2.0 (Async). It serves as the authoritative boundary for authentication, tenant isolation, role-based access control (RBAC), and transactional background jobs.

---

## 📑 Table of Contents

- [Architectural Topology](#-architectural-topology)
- [Request & Authorization Lifecycle](#-request--authorization-lifecycle)
- [Project Directory Layout](#-project-directory-layout)
- [Quick Start](#-quick-start)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [Active API Endpoints](#-active-api-endpoints)
- [Background Worker & Outbox](#-background-worker--outbox)
- [Developer Commands](#-developer-commands)
- [Documentation Index](#-documentation-index)

---

## 🏛️ Architectural Topology

```mermaid
flowchart TD
    Client["🌐 Client Requests\n(Web / API Consumers)"]

    subgraph FastAPI_Backend["FastAPI Backend (backend/)"]
        direction TB
        Main["📄 main.py\nMiddleware · Exception Handlers · Router Mounting"]

        subgraph Routers["API Routers"]
            AuthR["🔐 /auth\n(app/api/auth/router.py)"]
            V1R["🏢 /api/v1\nVersion-specific routes"]
            V2R["🏢 /api/v2\nVersion-specific routes"]
            IAMR["🏢 /api/v1/iam/members\nTenant IAM/RBAC"]
            HealthR["💚 /health\n(PostgreSQL · Redis · SMTP Readiness)"]
        end

        subgraph Guards["Security & Dependencies (app/api/dependencies/)"]
            TokenGuard["🔑 TokenManager\nJWT Decode & Validate"]
            ContextGuard["🛡️ AuthenticatedContext\nTenant Resolution"]
            RBACGuard["🛑 RequirePermission\nExact Code / Wildcard Match"]
        end

        subgraph Services["Domain Services (app/services/)"]
            AuthSvc["AuthService\nIdentity · Tokens · MFA · Reset"]
            MemberSvc["MemberService\nMemberships · Role Assignment · Auditing"]
        end

        subgraph Persistence["Data & Models (app/models/)"]
            ORM["SQLAlchemy 2.0 Models\nUUIDv7 PKs · Audit Trails · Soft Deletes"]
            OutboxTable["Transactional email_outbox"]
        end
    end

    subgraph Infrastructure["Infrastructure (compose.yaml)"]
        Postgres[("🐘 PostgreSQL 16\n(crm_db)")]
        RedisDB[("⚡ Redis 7\n(Sessions · Tokens · ARQ)")]
        Worker["👷 ARQ Worker Process\n(app/workers/email_worker.py)"]
        Mailpit["📬 Mailpit / SMTP\n(Mock Mailbox :8025)"]
    end

    Client -->|HTTP REST| Main
    Main --> AuthR
    Main --> V1R
    Main --> HealthR

    V1R --> RBACGuard
    RBACGuard --> ContextGuard
    ContextGuard --> TokenGuard

    AuthR --> AuthSvc
    V1R --> MemberSvc

    AuthSvc --> ORM
    AuthSvc --> RedisDB
    AuthSvc -->|Enqueue| OutboxTable

    MemberSvc --> ORM
    MemberSvc -->|Enqueue| OutboxTable

    ORM --> Postgres
    OutboxTable --> Postgres

    Worker -->|Poll Jobs| RedisDB
    Worker -->|Lock & Fetch| OutboxTable
    Worker -->|Deliver| Mailpit
```

---

## 🔄 Request & Authorization Lifecycle

IAM/RBAC uses versioned routes under `/api/v1/iam/members/*`. No member routes are mounted outside the tenant API versions.

```mermaid
sequenceDiagram
    autonumber
    actor User as Client
    participant Router as API Router
    participant Deps as get_current_context
    participant DB as PostgreSQL
    participant Service as Domain Service

    User->>Router: GET /api/v1/iam/members/ (Bearer JWT)
    Router->>Deps: Resolve AuthenticatedContext & RequirePermission
    Deps->>Deps: Verify Bearer token signature & expiry
    Deps->>DB: Query User (status == ACTIVE, deleted_at IS NULL)
    alt User is Platform Admin
        Deps-->>Router: Grant Wildcard Permission ("*")
    else Standard Member with Tenant Claim
        Deps->>DB: Load TenantMembership + Roles + Permissions
        Deps->>Deps: Verify required code (e.g. 'iam.membership.read')
        Deps-->>Router: Return AuthenticatedContext(user, tenant_id, perms)
    end
    Router->>Service: Call MemberService.list_members(tenant_id)
    Service->>DB: SELECT * FROM tenant_memberships WHERE tenant_id = :id
    DB-->>Service: Return member records
    Service-->>Router: Return Pydantic MemberResponse list
    Router-->>User: HTTP 200 OK [JSON]
```

---

## 📂 Project Directory Layout

```text
backend/
├── main.py                        # Application entry point, lifespan, routers & middleware
├── alembic.ini                    # Alembic configuration
├── pyproject.toml                 # Dependencies, build targets & worker script config
├── uv.lock                        # Deterministic dependency lockfile
├── alembic/                       # Database migrations
│   ├── env.py                     # Async Alembic execution environment
│   └── versions/                  # Versioned DDL migration scripts
├── scripts/
│   └── seed/                      # Initial setup seed package
│       ├── __main__.py            # Complete initial-setup CLI
│       ├── master_data.py         # Shared/tenant masters, menus, demo users
│       └── rbac.py                # RBAC synchronization
└── app/
    ├── api/
    │   ├── router.py              # Top-level router assembly
    │   ├── auth/router.py         # Version-independent auth endpoints (/auth/*)
    │   ├── health/router.py       # Database, Redis & SMTP readiness probe
    │   ├── dependencies/
    │   │   ├── auth.py            # Authentication context and permission guards
    │   │   ├── database.py        # Async database session dependency
    │   ├── tenant/
    │   │   ├── v1/router.py       # Tenant v1 routes
    │   │   ├── v1/endpoints/
    │   │   │   ├── members.py     # Versioned tenant IAM/RBAC operations
    │   │   └── v2/router.py       # Tenant v2 route assembly
    │   └── platform/v1/
    │       ├── router.py          # Platform control-plane route assembly
    │       └── endpoints/         # IAM, operators, tenants, plans, and audit
    ├── core/
    │   ├── config.py              # Pydantic BaseSettings loading from .env
    │   ├── constants.py           # INITIAL_PERMISSIONS, SYSTEM_ROLES
    │   ├── database/session.py    # AsyncEngine, sessionmaker, get_db_session
    │   ├── email.py               # EmailService: template rendering & outbox enqueue
    │   ├── enums.py               # UserStatus, MembershipStatus, EmailOutboxStatus
    │   ├── exceptions.py          # Domain exceptions (AppException, EntityNotFoundException)
    │   ├── exception_handlers.py  # Centralized FastAPI exception formatters
    │   ├── queue.py               # Redis pool for ARQ job queueing
    │   ├── redis.py               # Redis connection dependency
    │   └── security.py            # Argon2id password hashing, JWT token manager
    ├── models/                    # SQLAlchemy 2.0 ORM Declarative Models
    │   ├── base.py                # Base declarative root & AuditableLifecycleBase
    │   ├── email_outbox.py        # Outbox staging table with attempts tracking
    │   ├── membership_role.py     # Membership-to-Role junction
    │   ├── permission.py          # Granular capability catalog
    │   ├── role.py                # Global & custom tenant roles
    │   ├── role_assignment_audit.py # Immutable audit logs for role modifications
    │   ├── role_permission.py     # Role-to-Permission mapping
    │   ├── tenant.py              # Customer workspace / organization
    │   ├── tenant_membership.py   # User-to-tenant relationship
    │   ├── user.py                # Global user accounts
    │   ├── user_mfa_method.py     # Email OTP & MFA configuration
    │   └── user_session.py        # Active session tracking & refresh tokens
    ├── schemas/                   # Pydantic v2 Request & Response contracts
    │   ├── auth.py                # Register, login, MFA, tokens, profile schemas
    │   └── member.py              # Member invite, role update, summary schemas
    ├── repositories/              # SQLAlchemy persistence operations (adoption is partial)
    ├── services/                  # Business Logic Layer
    │   ├── auth_service.py        # User registration, authentication, MFA, password reset
    │   └── member_service.py      # Member invitations, removals, role management
    ├── templates/email/           # Jinja2 HTML Email Templates
    │   ├── base.html              # Standard branded base wrapper
    │   ├── mfa_otp.html           # 6-digit verification code email
    │   ├── password_reset.html    # Password reset action link email
    │   └── workspace_invitation.html # Member onboarding email
    └── workers/
        └── email_worker.py        # ARQ Worker background dispatcher
```

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.12+
- [Astral `uv`](https://docs.astral.sh/uv/)
- Docker & Docker Compose (for PostgreSQL, Redis, Mailpit)

### 2. Install Dependencies

```sh
cd backend
uv sync
```

### 3. Start Local Supporting Services

From the project root:

```sh
docker compose up -d
```

### 4. Apply Migrations & Seed Initial Setup

```sh
# Apply Alembic schema migrations
uv run alembic upgrade head

# Configure six distinct SEED_*_PASSWORD values in .env before seeding
# Seed RBAC, master data, menus, and demo users
uv run python -m scripts.seed
```

### 5. Launch Development Server

```sh
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API v1 Reference (ReDoc): [http://localhost:8000/v1/redoc](http://localhost:8000/v1/redoc)
- API v2 Reference (ReDoc): [http://localhost:8000/v2/redoc](http://localhost:8000/v2/redoc)
- API v1 Reference (Scalar): [http://localhost:8000/scalar/v1](http://localhost:8000/scalar/v1)
- API v2 Reference (Scalar): [http://localhost:8000/scalar/v2](http://localhost:8000/scalar/v2)
- Platform v1 Reference (ReDoc): [http://localhost:8000/platform/v1/redoc](http://localhost:8000/platform/v1/redoc)
- Platform v1 Reference (Scalar): [http://localhost:8000/scalar/platform/v1](http://localhost:8000/scalar/platform/v1)
- Tenant v1 docs include member routes; tenant v2 currently has no tenant-specific routes. Both include shared Auth and health. Platform docs include shared Auth and health plus platform routes. Root docs pages and Swagger remain disabled.
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 6. Run ARQ Background Worker (Separate Terminal)

```sh
uv run worker backend.app.workers.email_worker.WorkerSettings
```

---

## ⚙️ Configuration & Environment Variables

Settings are managed in `app/core/config.py` using `pydantic-settings`. Configure them via a `.env` file in `backend/`:

| Variable | Description | Default |
|---|---|---|
| `PROJECT_NAME` | Name of the service | `Enterprise CRM & IAM` |
| `ENVIRONMENT` | Runtime environment (`development`, `production`) | `development` |
| `DEBUG` | Enable debug logs & reload behavior | `True` |
| `API_V1_STR` | Versioned API route prefix | `/api/v1` |
| `API_V2_STR` | Version 2 API route prefix | `/api/v2` |
| `BACKEND_BASE_URL` | Public routable backend URL | `http://127.0.0.1:8000` |
| `FRONTEND_BASE_URL` | Frontend URL for email action links | `http://localhost:3000` |
| `CORS_ORIGINS` | Allowed origins (JSON array or comma-separated) | `["http://localhost:3000", ...]` |
| `DATABASE_URL` | PostgreSQL connection string (`asyncpg`) | `postgresql+asyncpg://crm_admin:admin%402k26@localhost:5432/crm_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SMTP_HOST` | SMTP server host | `localhost` (Mailpit: 1025) |
| `SMTP_PORT` | SMTP port | `1025` |
| `SMTP_USER` | SMTP username | `None` |
| `SMTP_PASSWORD` | SMTP password | `None` |
| `SMTP_TLS` | Enable TLS/STARTTLS | `False` |
| `EMAILS_FROM_EMAIL` | Sender address | `noreply@crm.local` |
| `EMAILS_FROM_NAME` | Sender display name | `Enterprise CRM` |
| `JWT_SECRET_KEY` | HMAC signing secret for JWTs | *(dev default — change in prod)* |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token session lifespan | `30` |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | Password reset token validity | `15` |
| `MFA_OTP_EXPIRE_SECONDS` | MFA 6-digit OTP validity | `300` (5 minutes) |

---

## 📡 Active API Endpoints

### 🔐 Authentication Gateway (`/auth/*`)

| Method | Path | Summary | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register new user; optional initial workspace | None |
| `POST` | `/auth/login` | Authenticate credentials; returns tokens or MFA challenge | None |
| `POST` | `/auth/refresh` | Rotate refresh token & issue new JWT access token | None |
| `POST` | `/auth/logout` | Revoke active user session | None |
| `GET` | `/auth/me` | Fetch profile of authenticated user | Bearer Token |
| `GET` | `/auth/workspaces` | List active workspaces user belongs to | Bearer Token |
| `POST` | `/auth/switch-workspace` | Switch active tenant context & issue tenant JWT | Bearer Token |
| `POST` | `/auth/password/forgot` | Request password reset email (outbox-driven) | None |
| `POST` | `/auth/password/reset` | Confirm password reset with token | None |
| `POST` | `/auth/mfa/verify-otp` | Verify 6-digit email OTP to complete login | None |
| `POST` | `/auth/mfa/email/toggle` | Enable or disable email OTP MFA | Bearer Token |

### 🏢 Tenant Workspace Members Administration

Canonical tenant IAM/RBAC endpoints are mounted under `/api/v1/iam/members/*`. Authentication remains shared at `/auth/*`.

| Method | Path | Required Permission | Description |
|---|---|---|---|
| `GET` | `/api/v1/iam/members/` | `iam.membership.read` | List active workspace members |
| `POST` | `/api/v1/iam/members/invite` | `iam.membership.create` | Invite user with initial role assignments |
| `DELETE` | `/api/v1/iam/members/{membership_id}` | `iam.membership.delete` | Soft-delete workspace membership (revokes access) |
| `GET` | `/api/v1/iam/members/roles` | `iam.role.read` | List assignable workspace roles |
| `PATCH` | `/api/v1/iam/members/{membership_id}/roles` | `iam.role_assignment.assign` | Update member's assigned roles with audit log |

### 💚 Health Check

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Checks PostgreSQL, Redis, and configured SMTP connectivity; returns 503 when any check fails |

This shared endpoint is listed first in tenant and platform API documentation pages.

### 🛡️ Platform Control Plane

Platform operations are independently mounted under `/platform/v1/*`; they do not
appear in tenant v1 or v2 schemas. The platform API includes IAM roles and
permissions, operator assignments, tenant lifecycle/settings, plan and
subscription management, and audit events. See the [IAM and RBAC guide](../docs/03-modules/iam-rbac.md#platform-control-plane)
for the endpoint-by-endpoint route and permission inventory.

---

## 📬 Background Worker & Outbox

The email subsystem guarantees transactional integrity:

```mermaid
flowchart LR
    API["API Request\n(e.g., Invite Member)"]
    DB[("PostgreSQL\nTransaction")]
    Outbox["email_outbox\nRow (PENDING)"]
    Redis["Redis\nQueue"]
    Worker["ARQ Worker"]
    Mail["Mailpit / SMTP"]

    API -->|1. Atomic Insert| DB
    DB --- Outbox
    API -->|2. Enqueue Job ID| Redis
    Redis -->|3. Consume Job| Worker
    Worker -->|4. SELECT FOR UPDATE| DB
    Worker -->|5. Render & Send| Mail
    Worker -->|6. UPDATE status='SENT'| DB
```

If the database transaction aborts, no outbox row is saved and no email is sent.

---

## 🛠️ Developer Commands

```sh
# Linting & Formatting
uv run ruff check app
uv run ruff format --check app

# Testing
uv run pytest

# Migrations
uv run alembic current
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description_of_change"

# Complete initial setup
uv run python -m scripts.seed

# RBAC only
uv run python -m scripts.seed.rbac
```

---

## 📖 Documentation Index

For detailed architectural and module guides, refer to [`docs/`](../docs/README.md):

- [Architecture & Module Map](../docs/01-architecture/system-overview.md)
- [RBAC & Multi-Tenancy Architecture](../docs/01-architecture/rbac-and-tenancy.md)
- [Local Setup & Services](../docs/02-setup/local-development.md)
- [Developer Command Cheat Sheet](../docs/02-setup/developer-commands.md)
- [Identity & Authentication Specification](../docs/03-modules/identity-and-authentication.md)
- [IAM & RBAC Implementation Guide](../docs/03-modules/iam-rbac.md)
- [Email Outbox & ARQ Worker Guide](../docs/03-modules/email-and-background-work.md)
- [Database Models & Migrations](../docs/04-database/database-and-migrations.md)
- [RBAC Seed Data Status](../docs/04-database/seed-data.md)
- [AI Agent Rules & Coding Standards](../AGENTS.md)
