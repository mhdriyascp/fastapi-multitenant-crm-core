# AI Agent Instructions and Engineering Standards

## Shared source of truth

The repository-wide agent requirements are maintained in the root [AGENTS.md](../../AGENTS.md). It covers architecture, tenant isolation, identifiers, data lifecycle, RBAC, exceptions, backend/frontend conventions, security, testing, dependency management, migrations, approvals, and the task workflow.

These are standards for new and modified code. They do not claim that every existing module currently conforms; use module documentation to understand known implementation gaps.

## Agent entry points

- **GitHub Copilot / VS Code agents:** root `AGENTS.md`.
- **Claude Code:** root `CLAUDE.md` imports `AGENTS.md`.
- **Cursor:** `.cursor/rules/enterprise-crm.mdc` applies the shared `AGENTS.md` instructions.

Keep detailed rules in `AGENTS.md` to avoid diverging copies. Update this page if agent entry points change.

## Review before changes

Read the relevant architecture and module docs alongside the code. In particular:

- [System architecture](../01-architecture/system-overview.md)
- [RBAC and tenant architecture](../01-architecture/rbac-and-tenancy.md)
- [IAM and RBAC implementation](../03-modules/iam-rbac.md)
- [Database and migrations](../04-database/database-and-migrations.md)
- [Developer commands](../02-setup/developer-commands.md)
