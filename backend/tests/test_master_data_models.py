import app.models  # noqa: F401
from app.models.base import Base

TENANT_MASTER_TABLES = {
    "organizations",
    "legal_entities",
    "branches",
    "departments",
    "designations",
    "teams",
    "locations",
    "business_units",
    "cost_centers",
    "fiscal_years",
    "tax_rates",
}

SHARED_REFERENCE_TABLES = {
    "currencies",
    "countries",
    "states",
    "cities",
    "time_zones",
    "languages",
    "units_of_measure",
    "tax_types",
}


def test_core_master_data_models_are_registered_with_expected_tenant_scope() -> None:
    assert TENANT_MASTER_TABLES | SHARED_REFERENCE_TABLES <= set(Base.metadata.tables)

    for table_name in TENANT_MASTER_TABLES:
        table = Base.metadata.tables[table_name]
        assert "tenant_id" in table.c
        assert "public_id" in table.c
        assert table.c.id.default.arg.__name__ == "uuid7"
        assert table.c.public_id.default.arg.__name__ == "uuid4"
        assert "deleted_at" in table.c
        tenant_foreign_key = next(iter(table.c.tenant_id.foreign_keys))
        assert tenant_foreign_key.target_fullname == "tenants.id"
        assert tenant_foreign_key.ondelete == "CASCADE"

    for table_name in SHARED_REFERENCE_TABLES:
        table = Base.metadata.tables[table_name]
        assert "tenant_id" not in table.c
        assert "public_id" in table.c
        assert table.c.id.default.arg.__name__ == "uuid7"
        assert table.c.public_id.default.arg.__name__ == "uuid4"


def test_core_master_data_business_codes_are_unique_for_active_records() -> None:
    active_code_indexes = {
        "uq_organizations_tenant_code_active",
        "uq_legal_entities_tenant_code_active",
        "uq_branches_tenant_code_active",
        "uq_departments_tenant_code_active",
        "uq_designations_tenant_code_active",
        "uq_teams_tenant_code_active",
        "uq_locations_tenant_code_active",
        "uq_business_units_tenant_code_active",
        "uq_cost_centers_tenant_code_active",
        "uq_fiscal_years_tenant_code_active",
        "uq_currencies_code_active",
        "uq_countries_code_active",
        "uq_time_zones_code_active",
        "uq_languages_code_active",
        "uq_units_of_measure_code_active",
        "uq_tax_types_code_active",
        "uq_tax_rates_tenant_code_start_active",
    }
    indexes = {
        index.name: index
        for table_name in TENANT_MASTER_TABLES | SHARED_REFERENCE_TABLES
        for index in Base.metadata.tables[table_name].indexes
    }

    assert active_code_indexes <= indexes.keys()
    assert all(
        "deleted_at IS NULL"
        in str(indexes[name].dialect_options["postgresql"]["where"])
        for name in active_code_indexes
    )
