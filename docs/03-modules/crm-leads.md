# CRM Leads

## Current status

Lead request/response schemas and CRUD-style endpoint code exist, but the feature is not currently registered with the FastAPI application. The current versioned router in `backend/app/api/v1/router.py` includes only the members router.

The implementation is a prototype using a process-local in-memory `LeadRepository`, not SQLAlchemy persistence. Data is lost when the process restarts and is not shared across worker processes. The store is a class-level dictionary without tenant partitioning.

## Defined endpoint operations

`backend/app/api/v1/endpoints/leads.py` defines operations relative to a router prefix that has not been configured or mounted:

- POST `/`: create a lead.
- GET `/`: list leads, with offset pagination, optional lifecycle status, and a search string.
- GET `/{lead_id}`: retrieve a lead.
- PATCH `/{lead_id}`: partially update a lead.
- DELETE `/{lead_id}`: delete a lead.

Do not treat these as reachable API paths until the router is explicitly included by the application.

## Data contract and behavior

`backend/app/schemas/lead.py` defines `LeadStatus` as `new`, `contacted`, `qualified`, `converted`, or `lost`. Create validation requires names and an email; company and non-negative annual revenue are optional. `LeadUpdate` fields are optional.

The in-memory repository:

- Uses UUIDv4 for its `id` and has no separate `public_id`.
- Enforces email uniqueness across the whole in-memory store, without tenant scope.
- Filters list results in memory and applies offset/limit slicing.
- Updates the `updated_at` timestamp when it receives non-empty update data.
- Physically removes a lead on delete.
- Does not provide a database model, migration, transaction boundary, or authorization dependency.

The endpoint currently relies on that repository directly and does not apply the IAM permission dependencies used by member endpoints.

## Before exposing this feature

Treat current code as a scaffold. Registering it as a production CRM API requires a separately scoped implementation decision addressing persistent storage, authenticated tenant context and query isolation, public identifiers, RBAC permissions, lifecycle/delete semantics, migration/indexes, and tests. The engineering constraints are summarized in [AGENTS.md](../../AGENTS.md).

## Related code

- Endpoint: `backend/app/api/v1/endpoints/leads.py`
- Repository prototype: `backend/app/api/dependencies/lead_storage.py`
- Schemas: `backend/app/schemas/lead.py`
- Router registration: `backend/app/api/v1/router.py`
