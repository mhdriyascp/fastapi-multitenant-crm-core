"""create shared and tenant core master data

Revision ID: 7f2c9e6d4a81
Revises: 1c7d91e52a4f
Create Date: 2026-11-10 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import Constraint

from alembic import op

revision: str = "7f2c9e6d4a81"
down_revision: str | Sequence[str] | None = "1c7d91e52a4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _common_columns(*, tenant_scoped: bool = False) -> list[sa.Column | Constraint]:
    columns = [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
    ]
    if tenant_scoped:
        columns.append(sa.Column("tenant_id", sa.Uuid(), nullable=False))
    columns.extend(
        [
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by_id", sa.Uuid(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_by_id", sa.Uuid(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_by_id", sa.Uuid(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.ForeignKeyConstraint(
                ["created_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["updated_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["deleted_by_id"], ["users.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        ]
    )
    if tenant_scoped:
        columns.append(
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE")
        )
    return columns


def _create_common_indexes(
    table_name: str,
    *,
    tenant_scoped: bool = False,
    indexed_columns: tuple[str, ...] = (),
) -> None:
    op.create_index(
        f"ix_{table_name}_public_id", table_name, ["public_id"], unique=True
    )
    op.create_index(
        f"ix_{table_name}_deleted_at", table_name, ["deleted_at"], unique=False
    )
    op.create_index(f"ix_{table_name}_status", table_name, ["status"], unique=False)
    if tenant_scoped:
        op.create_index(
            f"ix_{table_name}_tenant_id", table_name, ["tenant_id"], unique=False
        )
    for column in indexed_columns:
        op.create_index(f"ix_{table_name}_{column}", table_name, [column], unique=False)


def upgrade() -> None:
    op.create_table(
        "currencies",
        *_common_columns(),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=True),
        sa.Column("decimal_places", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "decimal_places >= 0 AND decimal_places <= 6",
            name="ck_currencies_decimal_places",
        ),
    )
    op.create_table(
        "countries",
        *_common_columns(),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("alpha3_code", sa.String(length=3), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("calling_code", sa.String(length=10), nullable=True),
    )
    op.create_table(
        "time_zones",
        *_common_columns(),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
    )
    op.create_table(
        "languages",
        *_common_columns(),
        sa.Column("code", sa.String(length=35), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("native_name", sa.String(length=100), nullable=True),
    )
    op.create_table(
        "units_of_measure",
        *_common_columns(),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=True),
        sa.Column("dimension", sa.String(length=50), nullable=True),
    )
    op.create_table(
        "tax_types",
        *_common_columns(),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "states",
        *_common_columns(),
        sa.Column("country_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "cities",
        *_common_columns(),
        sa.Column("country_id", sa.Uuid(), nullable=False),
        sa.Column("state_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=30), nullable=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["state_id"], ["states.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "organizations",
        *_common_columns(tenant_scoped=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=30), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("country_id", sa.Uuid(), nullable=True),
        sa.Column("default_currency_id", sa.Uuid(), nullable=True),
        sa.Column("timezone_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["default_currency_id"], ["currencies.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["timezone_id"], ["time_zones.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "legal_entities",
        *_common_columns(tenant_scoped=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("tax_identifier", sa.String(length=100), nullable=True),
        sa.Column("country_id", sa.Uuid(), nullable=True),
        sa.Column("default_currency_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["default_currency_id"], ["currencies.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "locations",
        *_common_columns(tenant_scoped=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("address_line_1", sa.String(length=255), nullable=True),
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
        sa.Column("country_id", sa.Uuid(), nullable=False),
        sa.Column("state_id", sa.Uuid(), nullable=True),
        sa.Column("city_id", sa.Uuid(), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("timezone_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["state_id"], ["states.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["timezone_id"], ["time_zones.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "branches",
        *_common_columns(tenant_scoped=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("legal_entity_id", sa.Uuid(), nullable=True),
        sa.Column("location_id", sa.Uuid(), nullable=True),
        sa.Column("parent_branch_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["legal_entity_id"], ["legal_entities.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["parent_branch_id"], ["branches.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "departments",
        *_common_columns(tenant_scoped=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("parent_department_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["parent_department_id"], ["departments.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "designations",
        *_common_columns(tenant_scoped=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "teams",
        *_common_columns(tenant_scoped=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("parent_team_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["parent_team_id"], ["teams.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "business_units",
        *_common_columns(tenant_scoped=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("parent_business_unit_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["parent_business_unit_id"], ["business_units.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "cost_centers",
        *_common_columns(tenant_scoped=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("business_unit_id", sa.Uuid(), nullable=True),
        sa.Column("default_currency_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["business_unit_id"], ["business_units.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["default_currency_id"], ["currencies.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "fiscal_years",
        *_common_columns(tenant_scoped=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.CheckConstraint("ends_on >= starts_on", name="ck_fiscal_year_dates"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
    )
    op.create_table(
        "tax_rates",
        *_common_columns(tenant_scoped=True),
        sa.Column("legal_entity_id", sa.Uuid(), nullable=True),
        sa.Column("tax_type_id", sa.Uuid(), nullable=False),
        sa.Column("country_id", sa.Uuid(), nullable=False),
        sa.Column("state_id", sa.Uuid(), nullable=True),
        sa.Column("city_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "rate >= 0 AND rate <= 100", name="ck_tax_rates_rate_percent"
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_tax_rates_effective_dates",
        ),
        sa.ForeignKeyConstraint(
            ["legal_entity_id"], ["legal_entities.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["tax_type_id"], ["tax_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["state_id"], ["states.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="RESTRICT"),
    )

    for table_name, index_name, code_columns in (
        ("currencies", "uq_currencies_code_active", ("code",)),
        ("countries", "uq_countries_code_active", ("code",)),
        ("time_zones", "uq_time_zones_code_active", ("code",)),
        ("languages", "uq_languages_code_active", ("code",)),
        ("units_of_measure", "uq_units_of_measure_code_active", ("code",)),
        ("tax_types", "uq_tax_types_code_active", ("code",)),
        (
            "organizations",
            "uq_organizations_tenant_code_active",
            ("tenant_id", "code"),
        ),
        (
            "legal_entities",
            "uq_legal_entities_tenant_code_active",
            ("tenant_id", "code"),
        ),
        ("branches", "uq_branches_tenant_code_active", ("tenant_id", "code")),
        (
            "departments",
            "uq_departments_tenant_code_active",
            ("tenant_id", "code"),
        ),
        (
            "designations",
            "uq_designations_tenant_code_active",
            ("tenant_id", "code"),
        ),
        ("teams", "uq_teams_tenant_code_active", ("tenant_id", "code")),
        ("locations", "uq_locations_tenant_code_active", ("tenant_id", "code")),
        (
            "business_units",
            "uq_business_units_tenant_code_active",
            ("tenant_id", "code"),
        ),
        (
            "cost_centers",
            "uq_cost_centers_tenant_code_active",
            ("tenant_id", "code"),
        ),
        (
            "fiscal_years",
            "uq_fiscal_years_tenant_code_active",
            ("tenant_id", "code"),
        ),
        (
            "tax_rates",
            "uq_tax_rates_tenant_code_start_active",
            ("tenant_id", "code", "valid_from"),
        ),
    ):
        op.create_index(
            index_name,
            table_name,
            list(code_columns),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        )

    op.create_index(
        "uq_countries_alpha3_active",
        "countries",
        ["alpha3_code"],
        unique=True,
        postgresql_where=sa.text("alpha3_code IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "uq_states_country_code_active",
        "states",
        ["country_id", "code"],
        unique=True,
        postgresql_where=sa.text("code IS NOT NULL AND deleted_at IS NULL"),
    )

    _create_common_indexes("currencies")
    _create_common_indexes("countries")
    _create_common_indexes("time_zones")
    _create_common_indexes("languages")
    _create_common_indexes("units_of_measure")
    _create_common_indexes("tax_types")
    _create_common_indexes("states", indexed_columns=("country_id",))
    _create_common_indexes("cities", indexed_columns=("country_id", "state_id"))
    _create_common_indexes(
        "organizations",
        tenant_scoped=True,
        indexed_columns=("country_id",),
    )
    _create_common_indexes(
        "legal_entities",
        tenant_scoped=True,
        indexed_columns=("organization_id",),
    )
    _create_common_indexes(
        "locations",
        tenant_scoped=True,
        indexed_columns=("organization_id", "country_id", "state_id", "city_id"),
    )
    _create_common_indexes(
        "branches",
        tenant_scoped=True,
        indexed_columns=("organization_id", "legal_entity_id", "location_id"),
    )
    _create_common_indexes(
        "departments",
        tenant_scoped=True,
        indexed_columns=("organization_id",),
    )
    _create_common_indexes(
        "designations",
        tenant_scoped=True,
    )
    _create_common_indexes(
        "teams",
        tenant_scoped=True,
        indexed_columns=("organization_id", "department_id"),
    )
    _create_common_indexes(
        "business_units",
        tenant_scoped=True,
        indexed_columns=("organization_id",),
    )
    _create_common_indexes(
        "cost_centers",
        tenant_scoped=True,
        indexed_columns=("organization_id", "business_unit_id"),
    )
    _create_common_indexes(
        "fiscal_years",
        tenant_scoped=True,
        indexed_columns=("organization_id",),
    )
    _create_common_indexes(
        "tax_rates",
        tenant_scoped=True,
        indexed_columns=(
            "legal_entity_id",
            "tax_type_id",
            "country_id",
            "state_id",
            "city_id",
        ),
    )


def downgrade() -> None:
    for table_name in (
        "tax_rates",
        "fiscal_years",
        "cost_centers",
        "business_units",
        "teams",
        "designations",
        "departments",
        "branches",
        "locations",
        "legal_entities",
        "organizations",
        "cities",
        "states",
        "tax_types",
        "units_of_measure",
        "languages",
        "time_zones",
        "countries",
        "currencies",
    ):
        op.drop_table(table_name)
