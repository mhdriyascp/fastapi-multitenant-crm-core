"""Registry of migrated core and CRM lookup models exposed by the APIs."""

from dataclasses import dataclass
from typing import Literal

from app.models.base import AuditableLifecycleBase
from app.models.crm import (
    AccountCategory,
    AccountGroup,
    AccountType,
    ActivityType,
    AddressType,
    CampaignType,
    CommunicationChannel,
    Competitor,
    ContactType,
    CustomerGroup,
    CustomerSegment,
    LeadRating,
    LeadSource,
    LeadStatus,
    LostReason,
    OpportunityStage,
    OpportunityType,
    SalesTeam,
    SalesTerritory,
)
from app.models.master_data import (
    Branch,
    BusinessUnit,
    City,
    CostCenter,
    Country,
    Currency,
    Department,
    Designation,
    FiscalYear,
    Language,
    LegalEntity,
    Location,
    Organization,
    State,
    TaxRate,
    TaxType,
    Team,
    TimeZone,
    UnitOfMeasure,
)

MasterDataScope = Literal["tenant", "shared"]


@dataclass(frozen=True)
class MasterDataResource:
    model: type[AuditableLifecycleBase]
    permission_prefix: str
    scope: MasterDataScope
    fields: frozenset[str]


COMMON_CODE_NAME_STATUS = frozenset({"code", "name", "status"})
COMMON_DESCRIPTION = frozenset({"description"})

MASTER_DATA_FIELDS: dict[str, frozenset[str]] = {
    "organizations": COMMON_CODE_NAME_STATUS
    | frozenset(
        {
            "legal_name",
            "email",
            "phone_number",
            "website",
            "country_id",
            "default_currency_id",
            "timezone_id",
        }
    ),
    "legal_entities": COMMON_CODE_NAME_STATUS
    | frozenset(
        {
            "organization_id",
            "registration_number",
            "tax_identifier",
            "country_id",
            "default_currency_id",
        }
    ),
    "branches": COMMON_CODE_NAME_STATUS
    | frozenset(
        {"organization_id", "legal_entity_id", "location_id", "parent_branch_id"}
    ),
    "departments": COMMON_CODE_NAME_STATUS
    | COMMON_DESCRIPTION
    | frozenset({"organization_id", "parent_department_id"}),
    "designations": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION | frozenset({"grade"}),
    "teams": COMMON_CODE_NAME_STATUS
    | frozenset({"organization_id", "department_id", "parent_team_id"}),
    "locations": COMMON_CODE_NAME_STATUS
    | frozenset(
        {
            "organization_id",
            "address_line_1",
            "address_line_2",
            "country_id",
            "state_id",
            "city_id",
            "postal_code",
            "timezone_id",
        }
    ),
    "business_units": COMMON_CODE_NAME_STATUS
    | COMMON_DESCRIPTION
    | frozenset({"organization_id", "parent_business_unit_id"}),
    "cost_centers": COMMON_CODE_NAME_STATUS
    | COMMON_DESCRIPTION
    | frozenset({"organization_id", "business_unit_id", "default_currency_id"}),
    "fiscal_years": COMMON_CODE_NAME_STATUS
    | frozenset({"organization_id", "starts_on", "ends_on"}),
    "tax_rates": COMMON_CODE_NAME_STATUS
    | frozenset(
        {
            "legal_entity_id",
            "tax_type_id",
            "country_id",
            "state_id",
            "city_id",
            "rate",
            "valid_from",
            "valid_to",
        }
    ),
    "currencies": COMMON_CODE_NAME_STATUS | frozenset({"symbol", "decimal_places"}),
    "countries": COMMON_CODE_NAME_STATUS | frozenset({"alpha3_code", "calling_code"}),
    "states": frozenset({"country_id", "code", "name", "status"}),
    "cities": frozenset({"country_id", "state_id", "code", "name", "status"}),
    "time_zones": COMMON_CODE_NAME_STATUS,
    "languages": COMMON_CODE_NAME_STATUS | frozenset({"native_name"}),
    "units_of_measure": COMMON_CODE_NAME_STATUS | frozenset({"symbol", "dimension"}),
    "tax_types": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "account_types": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "account_categories": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "account_groups": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "contact_types": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "address_types": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "customer_segments": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "customer_groups": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "lead_sources": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "lead_statuses": COMMON_CODE_NAME_STATUS
    | COMMON_DESCRIPTION
    | frozenset({"sort_order", "is_terminal", "is_converted"}),
    "lead_ratings": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION | frozenset({"score"}),
    "opportunity_stages": COMMON_CODE_NAME_STATUS
    | COMMON_DESCRIPTION
    | frozenset({"probability", "sort_order", "is_closed", "is_won"}),
    "opportunity_types": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "sales_territories": COMMON_CODE_NAME_STATUS
    | COMMON_DESCRIPTION
    | frozenset({"parent_territory_id"}),
    "sales_teams": COMMON_CODE_NAME_STATUS
    | COMMON_DESCRIPTION
    | frozenset({"manager_user_id"}),
    "competitors": COMMON_CODE_NAME_STATUS
    | COMMON_DESCRIPTION
    | frozenset({"website"}),
    "lost_reasons": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "campaign_types": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "activity_types": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
    "communication_channels": COMMON_CODE_NAME_STATUS | COMMON_DESCRIPTION,
}

MASTER_DATA_RESOURCES: dict[str, MasterDataResource] = {
    model.__tablename__: MasterDataResource(
        model,
        permission,
        scope,
        MASTER_DATA_FIELDS[model.__tablename__],
    )
    for model, permission, scope in (
        (Organization, "master_data.organization", "tenant"),
        (LegalEntity, "master_data.legal_entity", "tenant"),
        (Branch, "master_data.branch", "tenant"),
        (Department, "master_data.department", "tenant"),
        (Designation, "master_data.designation", "tenant"),
        (Team, "master_data.team", "tenant"),
        (Location, "master_data.location", "tenant"),
        (BusinessUnit, "master_data.business_unit", "tenant"),
        (CostCenter, "master_data.cost_center", "tenant"),
        (FiscalYear, "master_data.fiscal_year", "tenant"),
        (TaxRate, "master_data.tax_rate", "tenant"),
        (Currency, "master_data.currency", "shared"),
        (Country, "master_data.country", "shared"),
        (State, "master_data.state", "shared"),
        (City, "master_data.city", "shared"),
        (TimeZone, "master_data.time_zone", "shared"),
        (Language, "master_data.language", "shared"),
        (UnitOfMeasure, "master_data.unit_of_measure", "shared"),
        (TaxType, "master_data.tax_type", "shared"),
        (AccountType, "crm.account_type", "tenant"),
        (AccountCategory, "crm.account_category", "tenant"),
        (AccountGroup, "crm.account_group", "tenant"),
        (ContactType, "crm.contact_type", "tenant"),
        (AddressType, "crm.address_type", "tenant"),
        (CustomerSegment, "crm.customer_segment", "tenant"),
        (CustomerGroup, "crm.customer_group", "tenant"),
        (LeadSource, "crm.lead_source", "tenant"),
        (LeadStatus, "crm.lead_status", "tenant"),
        (LeadRating, "crm.lead_rating", "tenant"),
        (OpportunityStage, "crm.opportunity_stage", "tenant"),
        (OpportunityType, "crm.opportunity_type", "tenant"),
        (SalesTerritory, "crm.sales_territory", "tenant"),
        (SalesTeam, "crm.sales_team", "tenant"),
        (Competitor, "crm.competitor", "tenant"),
        (LostReason, "crm.lost_reason", "tenant"),
        (CampaignType, "crm.campaign_type", "tenant"),
        (ActivityType, "crm.activity_type", "tenant"),
        (CommunicationChannel, "crm.communication_channel", "tenant"),
    )
}
