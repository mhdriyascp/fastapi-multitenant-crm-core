# Core and CRM master-data APIs

The tenant v1 API exposes CRUD operations for migrated core and CRM lookup
tables. CRM transactions such as accounts, leads, opportunities, activities,
campaigns, and quotes are not included. ERP tables are not included until their
migration is applied and an API scope is approved.
All collection endpoints use keyset pagination: `limit` is 1–100 (default 50)
and `cursor` is an optional opaque continuation value. Responses include
`next_cursor` when another page is available. Pass it as `cursor` to continue;
clients should not inspect or construct it.

## Tenant-owned resources

Tenant-owned resources use the authenticated tenant from the access token; the
API does not accept a client-supplied `tenant_id`.

| API path resource | Permission prefix |
|---|---|
| `organizations` | `master_data.organization` |
| `legal_entities` | `master_data.legal_entity` |
| `branches` | `master_data.branch` |
| `departments` | `master_data.department` |
| `designations` | `master_data.designation` |
| `teams` | `master_data.team` |
| `locations` | `master_data.location` |
| `business_units` | `master_data.business_unit` |
| `cost_centers` | `master_data.cost_center` |
| `fiscal_years` | `master_data.fiscal_year` |
| `tax_rates` | `master_data.tax_rate` |
| `account_types`, `account_categories`, `account_groups` | `crm.account_type`, `crm.account_category`, `crm.account_group` |
| `contact_types`, `address_types` | `crm.contact_type`, `crm.address_type` |
| `customer_segments`, `customer_groups` | `crm.customer_segment`, `crm.customer_group` |
| `lead_sources`, `lead_statuses`, `lead_ratings` | `crm.lead_source`, `crm.lead_status`, `crm.lead_rating` |
| `opportunity_stages`, `opportunity_types` | `crm.opportunity_stage`, `crm.opportunity_type` |
| `sales_territories`, `sales_teams` | `crm.sales_territory`, `crm.sales_team` |
| `competitors`, `lost_reasons` | `crm.competitor`, `crm.lost_reason` |
| `campaign_types`, `activity_types`, `communication_channels` | `crm.campaign_type`, `crm.activity_type`, `crm.communication_channel` |

Use the corresponding `.create`, `.read`, `.update`, and `.delete`
permissions. `org_owner` and `org_admin` receive these permissions. Delete is a
soft delete; deleted rows are omitted from normal reads.

```text
GET    /api/v1/master-data/{resource}
POST   /api/v1/master-data/{resource}
GET    /api/v1/master-data/{resource}/{public_id}
PATCH  /api/v1/master-data/{resource}/{public_id}
DELETE /api/v1/master-data/{resource}/{public_id}
```

Create and update bodies are resource-specific in their `values` keys:

```json
{
  "values": {
    "code": "NEW_STATUS",
    "name": "New status"
  }
}
```

The response contains the resource name, public UUID, resource fields, and
timestamps. Foreign-key values in request/response data use referenced public
UUIDs; internal IDs and tenant IDs are not exposed. The service validates
fields against an explicit public-field allowlist for each resource, resolves
related records within the active tenant (or shared catalog), and rejects
attempts to write lifecycle or tenant fields.

## Shared catalogs

The shared catalogs are `currencies`, `countries`, `states`, `cities`,
`time_zones`, `languages`, `units_of_measure`, and `tax_types`. Tenant users
with the matching `master_data.*.read` permission can list and get these
records:

```text
GET /api/v1/master-data/shared/{resource}
GET /api/v1/master-data/shared/{resource}/{public_id}
```

Only platform administrators with verified MFA and the
`platform.master_data.{resource}.{action}` permission can create, update, or
soft-delete shared rows. Mutations require an audit reason of at least eight
characters; the before/after state and actor are recorded in
`platform_admin_audits` in the same transaction. Include `reason` with
platform create/update requests; DELETE requests pass it as a query parameter.
The platform API also provides list/get:

```text
/platform/v1/master-data/shared/{resource}
/platform/v1/master-data/shared/{resource}/{public_id}
```

```json
{
  "reason": "Adding the supported currency",
  "values": {
    "code": "USD",
    "name": "US Dollar"
  }
}
```

Global shared data mutations affect all tenants. These endpoints are scoped to
the current migrated tables; they do not create or mutate ERP data.
