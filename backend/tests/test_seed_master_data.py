import pytest
from app.core.constants import (
    INITIAL_PERMISSIONS,
    MASTER_DATA_PERMISSION_CODES,
    MASTER_DATA_PERMISSION_RESOURCES,
    SHARED_MASTER_DATA_READ_PERMISSION_CODES,
    SYSTEM_ROLES,
    TENANT_MASTER_DATA_PERMISSION_CODES,
)
from app.core.master_data_registry import MASTER_DATA_RESOURCES
from pydantic import ValidationError
from scripts.seed.__main__ import parse_args
from scripts.seed.master_data import (
    CORE_SHARED_TABLES,
    CORE_TENANT_TABLES,
    CRM_MASTER_TABLES,
    STARTER_MENU_SEEDS,
    DemoUserSettings,
)
from scripts.seed.rbac import PLATFORM_ROLE_SEEDS


def test_seed_catalogs_cover_all_core_and_crm_master_tables() -> None:
    assert CORE_SHARED_TABLES | CORE_TENANT_TABLES == {
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
        "currencies",
        "countries",
        "states",
        "cities",
        "time_zones",
        "languages",
        "units_of_measure",
        "tax_types",
        "tax_rates",
    }
    assert CRM_MASTER_TABLES == {
        "account_types",
        "account_categories",
        "account_groups",
        "contact_types",
        "address_types",
        "customer_segments",
        "customer_groups",
        "lead_sources",
        "lead_statuses",
        "lead_ratings",
        "opportunity_stages",
        "opportunity_types",
        "sales_territories",
        "sales_teams",
        "competitors",
        "lost_reasons",
        "campaign_types",
        "activity_types",
        "communication_channels",
    }


def test_permissions_cover_master_resources_and_are_granted_to_owner_and_admin() -> (
    None
):
    permissions_by_code = {
        permission[3]: permission for permission in INITIAL_PERMISSIONS
    }
    expected_codes = {
        f"{permission_prefix}.{action}"
        for _, _, permission_prefix in MASTER_DATA_PERMISSION_RESOURCES
        for action in ("create", "read", "update", "delete")
    }
    assert set(MASTER_DATA_PERMISSION_CODES) == expected_codes
    assert expected_codes <= permissions_by_code.keys()

    tenant_and_shared_read_codes = set(TENANT_MASTER_DATA_PERMISSION_CODES) | set(
        SHARED_MASTER_DATA_READ_PERMISSION_CODES
    )
    roles_by_code = {role["code"]: role for role in SYSTEM_ROLES}
    for role_code in ("org_owner", "org_admin"):
        role_permissions = set(roles_by_code[role_code]["permissions"])
        assert tenant_and_shared_read_codes <= role_permissions
        assert (expected_codes - tenant_and_shared_read_codes).isdisjoint(
            role_permissions
        )
    for role_code in ("member", "viewer"):
        assert expected_codes.isdisjoint(roles_by_code[role_code]["permissions"])

    assert "master_data.country.read" in permissions_by_code
    assert "crm.account_type.create" in permissions_by_code
    assert "crm.account.create" not in permissions_by_code


def test_starter_menus_cover_master_data_and_use_seeded_rbac_permissions() -> None:
    menu_codes = [menu.code for menu in STARTER_MENU_SEEDS]
    seeded_permission_codes = {
        permission_code
        for menu in STARTER_MENU_SEEDS
        for permission_code in menu.permission_codes
    }
    catalog_permission_codes = {permission[3] for permission in INITIAL_PERMISSIONS}
    resource_menu_codes = {
        menu.code for menu in STARTER_MENU_SEEDS if menu.code.startswith("resource_")
    }

    assert len(menu_codes) == len(set(menu_codes))
    assert resource_menu_codes == {
        f"resource_{resource_name}" for resource_name in MASTER_DATA_RESOURCES
    }
    assert seeded_permission_codes <= catalog_permission_codes

    for role in SYSTEM_ROLES:
        role_permissions = set(role["permissions"])
        visible_menu_codes = {
            menu.code
            for menu in STARTER_MENU_SEEDS
            if not menu.permission_codes
            or "*" in role_permissions
            or bool(set(menu.permission_codes) & role_permissions)
        }

        assert "dashboard" in visible_menu_codes
        assert "members" in visible_menu_codes
        assert ("access_control" in visible_menu_codes) == (
            "iam.role.read" in role_permissions or "*" in role_permissions
        )
        assert ("core_setup" in visible_menu_codes) == (
            "org_owner" == role["code"]
            or "org_admin" == role["code"]
            or "*" in role_permissions
        )
        assert ("crm_setup" in visible_menu_codes) == (
            "org_owner" == role["code"]
            or "org_admin" == role["code"]
            or "*" in role_permissions
        )


def test_demo_user_seed_requires_separate_passwords_and_safe_email_defaults() -> None:
    with pytest.raises(ValidationError):
        DemoUserSettings(_env_file=None)

    demo_settings = DemoUserSettings(
        _env_file=None,
        platform_admin_password="unique-platform-secret",
        platform_support_password="unique-platform-support-secret",
        organization_owner_password="unique-owner-secret",
        organization_admin_password="unique-admin-secret",
        organization_member_password="unique-member-secret",
        organization_viewer_password="unique-viewer-secret",
    )

    assert str(demo_settings.platform_admin_email) == "platform-admin@example.com"
    assert str(demo_settings.platform_support_email) == "platform-support@example.com"
    assert (
        str(demo_settings.organization_owner_email)
        == "owner@demo-organization.example.com"
    )
    assert "unique-platform-secret" not in repr(demo_settings)


def test_demo_user_email_can_be_configured_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEED_PLATFORM_ADMIN_EMAIL", "custom-admin@example.com")
    demo_settings = DemoUserSettings(
        _env_file=None,
        platform_admin_password="unique-platform-secret",
        platform_support_password="unique-platform-support-secret",
        organization_owner_password="unique-owner-secret",
        organization_admin_password="unique-admin-secret",
        organization_member_password="unique-member-secret",
        organization_viewer_password="unique-viewer-secret",
    )

    assert str(demo_settings.platform_admin_email) == "custom-admin@example.com"


def test_platform_support_role_grants_only_approved_read_permissions() -> None:
    role_by_code = {str(role["code"]): role for role in PLATFORM_ROLE_SEEDS}
    support_role = role_by_code["platform_support"]
    permission_codes = {permission[3] for permission in INITIAL_PERMISSIONS}

    assert support_role["permissions"] == [
        "platform.tenant.read",
        "platform.audit.read",
    ]
    assert set(support_role["permissions"]) <= permission_codes


def test_initial_seed_cli_includes_demo_users_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.argv", ["scripts.seed"])
    assert parse_args().include_demo_users is True

    monkeypatch.setattr("sys.argv", ["scripts.seed", "--without-demo-users"])
    assert parse_args().include_demo_users is False
