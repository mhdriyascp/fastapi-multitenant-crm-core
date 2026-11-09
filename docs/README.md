# Enterprise CRM Documentation Hub

This documentation is organized by topic and reflects the current code. Where intended architecture differs from implemented behavior, the guides call out the gap rather than presenting a target as a fact.

```text
docs/
├── README.md
├── 00-overview/
├── 01-architecture/
├── 02-setup/
├── 03-modules/
├── 04-database/
└── 05-ai-and-standards/
```

## 00 — Overview

- [Product and technology overview](00-overview/README.md)

## 01 — Architecture

- [System architecture and module map](01-architecture/system-overview.md)
- [ADR-001: Repository structure](01-architecture/ADR-001-repository-structure.md)
- [RBAC and tenant architecture](01-architecture/rbac-and-tenancy.md)

## 02 — Setup

- [Local development and configuration](02-setup/local-development.md)
- [Developer command cheat sheet](02-setup/developer-commands.md)

## 03 — Modules

- [Identity and authentication](03-modules/identity-and-authentication.md)
- [IAM and RBAC implementation](03-modules/iam-rbac.md)
- [CRM leads](03-modules/crm-leads.md)
- [Email outbox and background worker](03-modules/email-and-background-work.md)

## 04 — Database

- [Database model and migrations](04-database/database-and-migrations.md)
- [Seed data status](04-database/seed-data.md)

## 05 — AI and standards

- [AI agent instruction entry points](05-ai-and-standards/README.md)

## Current implementation notes

The backend is an early-stage modular monolith. Authentication and member administration use PostgreSQL, while leads use a process-local in-memory store and their router is not mounted. There is no dedicated `app/repositories/` package yet; authentication and member services currently contain ORM queries. See [system architecture](01-architecture/system-overview.md) for the verified route topology and gaps.
