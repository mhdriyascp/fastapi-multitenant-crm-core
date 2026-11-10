# Enterprise CRM — Documentation Hub

> Documentation is organized by topic and always reflects the **inspected implementation**. Where the intended architecture differs from what is currently built, guides call out the gap explicitly.

---

## 🗺️ Documentation Map

```mermaid
flowchart LR
    HUB["📚 docs/"]

    HUB --> OV["00-overview/\nProduct & stack"]
    HUB --> AR["01-architecture/\nSystem design"]
    HUB --> SE["02-setup/\nLocal dev"]
    HUB --> MO["03-modules/\nFeature guides"]
    HUB --> DB["04-database/\nSchema & data"]
    HUB --> AI["05-ai-and-standards/\nAgent rules"]

    AR --> AR1["system-overview.md"]
    AR --> AR2["rbac-and-tenancy.md"]
    AR --> AR3["repository-structure.md"]

    SE --> SE1["local-development.md"]
    SE --> SE2["developer-commands.md"]

    MO --> MO1["identity-and-authentication.md"]
    MO --> MO2["iam-rbac.md"]
    MO --> MO4["email-and-background-work.md"]
    MO --> MO5["master-data-apis.md"]

    DB --> DB1["database-and-migrations.md"]
    DB --> DB2["seed-data.md"]
```

---

## 00 — Overview

| Document | Description |
|---|---|
| [Product and technology overview](00-overview/README.md) | What is built, the full tech stack, and current implementation status |

---

## 01 — Architecture

| Document | Description |
|---|---|
| [System architecture and module map](01-architecture/system-overview.md) | Repository layout, active route topology, request/data flow, and known gaps |
| [RBAC and tenant architecture](01-architecture/rbac-and-tenancy.md) | Role model, permission resolution flow, and tenancy boundaries |
| [ADR-001: Repository structure](01-architecture/repository-structure.md) | Architecture decision record for the monorepo layout |

---

## 02 — Setup

| Document | Description |
|---|---|
| [Local development and configuration](02-setup/local-development.md) | Infrastructure services, environment variables, and application processes |
| [Developer command cheat sheet](02-setup/developer-commands.md) | All `uv`, `npm`, `docker compose`, migration, seed, and worker commands |

---

## 03 — Modules

| Document | Description |
|---|---|
| [Identity and authentication](03-modules/identity-and-authentication.md) | Registration, login, MFA, password reset, session management |
| [IAM and RBAC implementation](03-modules/iam-rbac.md) | Member management, role assignment, audit trail |
| [Core and CRM master-data APIs](03-modules/master-data-apis.md) | Tenant CRUD and platform-managed global reference catalogs |
| [Email outbox and background worker](03-modules/email-and-background-work.md) | Transactional email system, ARQ worker, delivery guarantees |

---

## 04 — Database

| Document | Description |
|---|---|
| [Database model and migrations](04-database/database-and-migrations.md) | Persisted models, Alembic migration history, identifier and lifecycle patterns |
| [Seed data and RBAC seeder](04-database/seed-data.md) | Initial setup seed package, demo accounts, and RBAC-only command |

---

## 05 — AI and Standards

| Document | Description |
|---|---|
| [AI agent instructions](05-ai-and-standards/README.md) | Agent entry points and links to engineering standards |

---

## 📌 Current Implementation Notes

```mermaid
flowchart TD
    subgraph LIVE["✅ Implemented & Active"]
        A1["Auth flows\n/auth/*"]
        A2["Tenant API v1\n/api/v1/iam/members"]
        A3["Versioned APIs\nTenant /api/v1 · /api/v2\nPlatform /platform/v1"]
        A4["Email outbox\nInvitation · Password reset · MFA OTP"]
        A5["Shared health check\n/health"]
        A6["Versioned docs\nReDoc + Scalar"]
        A7["Domain exceptions\nDecoupled from HTTPException"]
    end

    subgraph PARTIAL["⚠️ Exists but Not Mounted / Incomplete"]
        B2["Repositories\nMember and platform repositories exist\nService adoption is partial"]
        B3["Public IDs\nNot consistently used in all responses"]
    end

    subgraph TODO["🔲 Not Yet Implemented"]
        C1["Initial setup seeding\nMust run scripts.seed manually"]
        C2["Outbox sweeper\nStalled PENDING rows not auto-recovered"]
        C3["Frontend CRM UI\nCurrently a health-status page only"]
    end
```

The backend is an early-stage modular monolith. See [system architecture](01-architecture/system-overview.md) for the verified route topology and all known gaps.
