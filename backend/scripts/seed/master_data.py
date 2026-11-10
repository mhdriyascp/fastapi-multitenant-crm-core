import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import SHARED_MASTER_DATA_PERMISSION_PREFIXES
from app.core.enums import (
    CommonStatus,
    MembershipStatus,
    RoleAuditAction,
    TenantStatus,
    UserStatus,
)
from app.core.master_data_registry import MASTER_DATA_RESOURCES
from app.core.security import PasswordManager
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
from app.models.identity_master import UserCredential
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
from app.models.membership_role import MembershipRole
from app.models.menu import Menu, MenuPermission
from app.models.permission import Permission
from app.models.platform_admin_audit import PlatformAdminAudit
from app.models.platform_user_role import PlatformUserRole
from app.models.role import Role
from app.models.role_assignment_audit import RoleAssignmentAudit
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User

from .rbac import (
    AsyncSessionLocal,
    seed_permissions,
    seed_platform_roles_and_mappings,
    seed_roles_and_mappings,
)


class DemoUserSettings(BaseSettings):
    """Local-only demo account identities and required unique passwords."""

    platform_admin_email: EmailStr = "platform-admin@example.com"
    platform_admin_password: SecretStr
    platform_support_email: EmailStr = "platform-support@example.com"
    platform_support_password: SecretStr
    organization_owner_email: EmailStr = "owner@demo-organization.example.com"
    organization_owner_password: SecretStr
    organization_admin_email: EmailStr = "admin@demo-organization.example.com"
    organization_admin_password: SecretStr
    organization_member_email: EmailStr = "member@demo-organization.example.com"
    organization_member_password: SecretStr
    organization_viewer_email: EmailStr = "viewer@demo-organization.example.com"
    organization_viewer_password: SecretStr

    model_config = SettingsConfigDict(
        env_prefix="SEED_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@dataclass(frozen=True)
class DemoUserSeed:
    email: str
    password: SecretStr
    first_name: str
    last_name: str
    role_code: str | None
    is_platform_admin: bool = False
    platform_role_code: str | None = None


CRM_REFERENCE_SEEDS: tuple[
    tuple[type[AuditableLifecycleBase], tuple[dict[str, object], ...]], ...
] = (
    (
        AccountType,
        (
            {
                "code": "CUSTOMER",
                "name": "Customer",
                "description": "Active customer account",
            },
            {
                "code": "PROSPECT",
                "name": "Prospect",
                "description": "Potential customer account",
            },
        ),
    ),
    (
        AccountCategory,
        (
            {
                "code": "BUSINESS",
                "name": "Business",
                "description": "Business organization",
            },
        ),
    ),
    (
        AccountGroup,
        (
            {
                "code": "STANDARD",
                "name": "Standard",
                "description": "Standard customer group",
            },
        ),
    ),
    (
        ContactType,
        (
            {"code": "BUSINESS", "name": "Business", "description": "Business contact"},
            {"code": "BILLING", "name": "Billing", "description": "Billing contact"},
        ),
    ),
    (
        AddressType,
        (
            {"code": "BILLING", "name": "Billing", "description": "Billing address"},
            {"code": "SHIPPING", "name": "Shipping", "description": "Shipping address"},
            {"code": "OFFICE", "name": "Office", "description": "Office address"},
        ),
    ),
    (
        CustomerSegment,
        (
            {"code": "SMB", "name": "Small and Medium Business"},
            {"code": "ENTERPRISE", "name": "Enterprise"},
        ),
    ),
    (
        CustomerGroup,
        (
            {
                "code": "GENERAL",
                "name": "General",
                "description": "Default customer group",
            },
        ),
    ),
    (
        LeadSource,
        (
            {"code": "WEBSITE", "name": "Website"},
            {"code": "REFERRAL", "name": "Referral"},
            {"code": "PARTNER", "name": "Partner"},
        ),
    ),
    (
        LeadStatus,
        (
            {
                "code": "NEW",
                "name": "New",
                "sort_order": 10,
                "is_terminal": False,
                "is_converted": False,
            },
            {
                "code": "QUALIFIED",
                "name": "Qualified",
                "sort_order": 20,
                "is_terminal": False,
                "is_converted": False,
            },
            {
                "code": "CONVERTED",
                "name": "Converted",
                "sort_order": 30,
                "is_terminal": True,
                "is_converted": True,
            },
            {
                "code": "DISQUALIFIED",
                "name": "Disqualified",
                "sort_order": 40,
                "is_terminal": True,
                "is_converted": False,
            },
        ),
    ),
    (
        LeadRating,
        (
            {"code": "HOT", "name": "Hot", "score": 80},
            {"code": "WARM", "name": "Warm", "score": 50},
            {"code": "COLD", "name": "Cold", "score": 20},
        ),
    ),
    (
        OpportunityStage,
        (
            {
                "code": "QUALIFICATION",
                "name": "Qualification",
                "probability": Decimal(10),
                "sort_order": 10,
            },
            {
                "code": "PROPOSAL",
                "name": "Proposal",
                "probability": Decimal(50),
                "sort_order": 20,
            },
            {
                "code": "NEGOTIATION",
                "name": "Negotiation",
                "probability": Decimal(80),
                "sort_order": 30,
            },
            {
                "code": "WON",
                "name": "Won",
                "probability": Decimal(100),
                "sort_order": 40,
                "is_closed": True,
                "is_won": True,
            },
            {
                "code": "LOST",
                "name": "Lost",
                "probability": Decimal(0),
                "sort_order": 50,
                "is_closed": True,
                "is_won": False,
            },
        ),
    ),
    (
        OpportunityType,
        (
            {"code": "NEW_BUSINESS", "name": "New Business"},
            {"code": "RENEWAL", "name": "Renewal"},
        ),
    ),
    (
        SalesTerritory,
        ({"code": "DEFAULT", "name": "Default Territory"},),
    ),
    (
        SalesTeam,
        ({"code": "GENERAL", "name": "General Sales Team"},),
    ),
    (
        Competitor,
        ({"code": "OTHER", "name": "Other", "description": "Unlisted competitor"},),
    ),
    (
        LostReason,
        (
            {"code": "PRICE", "name": "Price"},
            {"code": "TIMING", "name": "Timing"},
            {"code": "NO_DECISION", "name": "No Decision"},
        ),
    ),
    (
        CampaignType,
        (
            {"code": "EMAIL", "name": "Email"},
            {"code": "EVENT", "name": "Event"},
        ),
    ),
    (
        ActivityType,
        (
            {"code": "CALL", "name": "Call"},
            {"code": "EMAIL", "name": "Email"},
            {"code": "MEETING", "name": "Meeting"},
        ),
    ),
    (
        CommunicationChannel,
        (
            {"code": "EMAIL", "name": "Email"},
            {"code": "PHONE", "name": "Phone"},
            {"code": "SMS", "name": "SMS"},
        ),
    ),
)

CRM_MASTER_TABLES = frozenset(model.__tablename__ for model, _ in CRM_REFERENCE_SEEDS)
CORE_SHARED_TABLES = frozenset(
    {
        "currencies",
        "countries",
        "states",
        "cities",
        "time_zones",
        "languages",
        "units_of_measure",
        "tax_types",
    }
)
CORE_TENANT_TABLES = frozenset(
    {
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
)


@dataclass(frozen=True)
class MenuSeed:
    """Code-managed definition for one starter navigation item."""

    code: str
    title: str
    path: str | None
    icon: str | None
    sort_order: int
    parent_code: str | None = None
    permission_codes: tuple[str, ...] = ()


_MASTER_DATA_GROUPS = {
    "core_setup": ("Core Setup", 10, "building"),
    "reference_data": ("Reference Data", 20, "globe"),
    "crm_setup": ("CRM Setup", 30, "briefcase"),
}
_MASTER_DATA_GROUP_PERMISSIONS: dict[str, list[str]] = {
    group_code: [] for group_code in _MASTER_DATA_GROUPS
}
_MASTER_DATA_CHILD_SEEDS: list[MenuSeed] = []

for resource_name, resource in MASTER_DATA_RESOURCES.items():
    if resource.permission_prefix.startswith("crm."):
        group_code = "crm_setup"
    elif resource.permission_prefix in SHARED_MASTER_DATA_PERMISSION_PREFIXES:
        group_code = "reference_data"
    else:
        group_code = "core_setup"

    read_permission = f"{resource.permission_prefix}.read"
    _MASTER_DATA_GROUP_PERMISSIONS[group_code].append(read_permission)
    title = resource.permission_prefix.rsplit(".", 1)[-1].replace("_", " ").title()
    path_group = "crm" if group_code == "crm_setup" else "master-data"
    _MASTER_DATA_CHILD_SEEDS.append(
        MenuSeed(
            code=f"resource_{resource_name}",
            title=title,
            path=f"/dashboard/{path_group}/{resource_name}",
            icon=None,
            sort_order=len(
                [
                    seed
                    for seed in _MASTER_DATA_CHILD_SEEDS
                    if seed.parent_code == group_code
                ]
            )
            * 10
            + 10,
            parent_code=group_code,
            permission_codes=(read_permission,),
        )
    )

STARTER_MENU_SEEDS = (
    MenuSeed(
        code="dashboard",
        title="Dashboard",
        path="/dashboard",
        icon="layout-dashboard",
        sort_order=0,
    ),
    MenuSeed(
        code="members",
        title="Members",
        path="/dashboard/iam/members",
        icon="users",
        sort_order=10,
        permission_codes=("iam.membership.read",),
    ),
    MenuSeed(
        code="access_control",
        title="Access Control",
        path=None,
        icon="shield",
        sort_order=20,
        permission_codes=("iam.role.read",),
    ),
    MenuSeed(
        code="roles",
        title="Roles",
        path="/dashboard/iam/roles",
        icon=None,
        sort_order=10,
        parent_code="access_control",
        permission_codes=("iam.role.read",),
    ),
    *(
        MenuSeed(
            code=group_code,
            title=title,
            path=None,
            icon=icon,
            sort_order=sort_order,
            permission_codes=tuple(_MASTER_DATA_GROUP_PERMISSIONS[group_code]),
        )
        for group_code, (title, sort_order, icon) in _MASTER_DATA_GROUPS.items()
        if _MASTER_DATA_GROUP_PERMISSIONS[group_code]
    ),
    *_MASTER_DATA_CHILD_SEEDS,
)


async def seed_record[ModelType: AuditableLifecycleBase](
    session: AsyncSession,
    model: type[ModelType],
    key: dict[str, object],
    values: dict[str, object],
) -> tuple[ModelType, bool]:
    statement = select(model).where(
        *(getattr(model, field) == value for field, value in key.items()),
        model.deleted_at.is_(None),
    )
    record = (await session.execute(statement)).scalar_one_or_none()
    if record is not None:
        return record, False

    record = model(**(key | values))
    session.add(record)
    await session.flush()
    return record, True


async def seed_shared_catalogs(
    session: AsyncSession,
) -> tuple[dict[str, UUID], dict[str, UUID], dict[str, UUID]]:
    currency, _ = await seed_record(
        session,
        Currency,
        {"code": "INR"},
        {"name": "Indian Rupee", "symbol": "INR", "decimal_places": 2},
    )
    country, _ = await seed_record(
        session,
        Country,
        {"code": "IN"},
        {"alpha3_code": "IND", "name": "India", "calling_code": "+91"},
    )
    state, _ = await seed_record(
        session,
        State,
        {"country_id": country.id, "code": "KA"},
        {"name": "Karnataka"},
    )
    city, _ = await seed_record(
        session,
        City,
        {"country_id": country.id, "state_id": state.id, "code": "BLR"},
        {"name": "Bengaluru"},
    )
    timezone, _ = await seed_record(
        session,
        TimeZone,
        {"code": "Asia/Kolkata"},
        {"name": "India Standard Time"},
    )

    for code, name, native_name in (
        ("en", "English", "English"),
        ("hi", "Hindi", "Hindi"),
    ):
        await seed_record(
            session,
            Language,
            {"code": code},
            {"name": name, "native_name": native_name},
        )

    for code, name, symbol, dimension in (
        ("EA", "Each", "ea", "count"),
        ("KGM", "Kilogram", "kg", "mass"),
        ("LTR", "Litre", "L", "volume"),
        ("MTR", "Metre", "m", "length"),
        ("HUR", "Hour", "h", "time"),
    ):
        await seed_record(
            session,
            UnitOfMeasure,
            {"code": code},
            {"name": name, "symbol": symbol, "dimension": dimension},
        )

    tax_type, _ = await seed_record(
        session,
        TaxType,
        {"code": "GST"},
        {
            "name": "Goods and Services Tax",
            "description": "Tax classification; configure rates for the applicable jurisdiction.",
        },
    )
    return (
        {"INR": currency.id},
        {"IN": country.id},
        {
            "KA": state.id,
            "BLR": city.id,
            "Asia/Kolkata": timezone.id,
            "GST": tax_type.id,
        },
    )


async def seed_tenant(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
) -> Tenant:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.slug == slug))
    ).scalar_one_or_none()
    if tenant is not None:
        if tenant.deleted_at is not None:
            raise ValueError(f"Tenant slug {slug!r} belongs to a soft-deleted tenant.")
        if tenant.name != name:
            raise ValueError(
                f"Tenant slug {slug!r} already belongs to {tenant.name!r}, not {name!r}."
            )
        return tenant

    tenant = Tenant(name=name, slug=slug, country_code="IN", timezone="Asia/Kolkata")
    session.add(tenant)
    await session.flush()
    return tenant


async def seed_core_tenant_masters(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    organization_name: str,
    country_id: UUID,
    currency_id: UUID,
    state_id: UUID,
    city_id: UUID,
    timezone_id: UUID,
    tax_type_id: UUID,
) -> int:
    tenant_values = {"tenant_id": tenant_id}
    organization, created = await seed_record(
        session,
        Organization,
        tenant_values | {"code": "DEMO_ORG"},
        {
            "name": organization_name,
            "legal_name": organization_name,
            "country_id": country_id,
            "default_currency_id": currency_id,
            "timezone_id": timezone_id,
        },
    )
    created_count = int(created)
    legal_entity, created = await seed_record(
        session,
        LegalEntity,
        tenant_values | {"code": "DEMO_LEGAL"},
        {
            "organization_id": organization.id,
            "name": f"{organization_name} Legal Entity",
            "country_id": country_id,
            "default_currency_id": currency_id,
        },
    )
    created_count += int(created)
    location, created = await seed_record(
        session,
        Location,
        tenant_values | {"code": "HQ"},
        {
            "organization_id": organization.id,
            "name": "Head Office",
            "country_id": country_id,
            "state_id": state_id,
            "city_id": city_id,
            "timezone_id": timezone_id,
        },
    )
    created_count += int(created)
    _, created = await seed_record(
        session,
        Branch,
        tenant_values | {"code": "MAIN"},
        {
            "organization_id": organization.id,
            "legal_entity_id": legal_entity.id,
            "location_id": location.id,
            "name": "Main Branch",
        },
    )
    created_count += int(created)
    department, created = await seed_record(
        session,
        Department,
        tenant_values | {"code": "SALES"},
        {"organization_id": organization.id, "name": "Sales"},
    )
    created_count += int(created)

    for model, code, name, extra in (
        (Designation, "ACCOUNT_MANAGER", "Account Manager", {}),
        (
            Team,
            "SALES",
            "Sales Team",
            {"organization_id": organization.id, "department_id": department.id},
        ),
        (
            BusinessUnit,
            "CORE",
            "Core Business",
            {"organization_id": organization.id},
        ),
        (
            CostCenter,
            "GENERAL",
            "General Cost Center",
            {
                "organization_id": organization.id,
                "business_unit_id": None,
                "default_currency_id": currency_id,
            },
        ),
    ):
        _, created = await seed_record(
            session,
            model,
            tenant_values | {"code": code},
            {"name": name} | extra,
        )
        created_count += int(created)

    _, created = await seed_record(
        session,
        FiscalYear,
        tenant_values | {"code": "FY2026"},
        {
            "organization_id": organization.id,
            "name": "Fiscal Year 2026",
            "starts_on": date(2026, 1, 1),
            "ends_on": date(2026, 12, 31),
        },
    )
    created_count += int(created)

    _, created = await seed_record(
        session,
        TaxRate,
        tenant_values | {"code": "DEMO-GST-0", "valid_from": date(2026, 1, 1)},
        {
            "tax_type_id": tax_type_id,
            "country_id": country_id,
            "name": "Inactive demo tax rate - configure before use",
            "rate": Decimal(0),
            "valid_to": None,
            "status": CommonStatus.INACTIVE,
        },
    )
    created_count += int(created)
    return created_count


async def seed_crm_masters(session: AsyncSession, tenant_id: UUID) -> int:
    created_count = 0
    for model, records in CRM_REFERENCE_SEEDS:
        for values in records:
            key = {"tenant_id": tenant_id, "code": values["code"]}
            _, created = await seed_record(session, model, key, values)
            created_count += int(created)
    return created_count


async def seed_menus(
    session: AsyncSession,
    permissions: dict[str, Permission],
) -> tuple[int, int]:
    """Idempotently sync starter menu records and their permission links."""
    seeded_count = 0
    permission_link_count = 0
    menus_by_code: dict[str, Menu] = {}

    for seed in STARTER_MENU_SEEDS:
        menu = (
            await session.execute(select(Menu).where(Menu.code == seed.code))
        ).scalar_one_or_none()
        parent_id = (
            menus_by_code[seed.parent_code].id if seed.parent_code is not None else None
        )
        if menu is None:
            menu = Menu(
                code=seed.code,
                title=seed.title,
                path=seed.path,
                icon=seed.icon,
                sort_order=seed.sort_order,
                parent_id=parent_id,
                is_active=True,
            )
            session.add(menu)
            await session.flush()
            seeded_count += 1
        else:
            menu.title = seed.title
            menu.path = seed.path
            menu.icon = seed.icon
            menu.sort_order = seed.sort_order
            menu.parent_id = parent_id
            menu.is_active = True
            await session.flush()

        menus_by_code[seed.code] = menu
        expected_permission_ids: set[UUID] = set()
        for permission_code in seed.permission_codes:
            permission = permissions.get(permission_code)
            if permission is None:
                raise ValueError(
                    f"Cannot seed menu {seed.code!r}: permission "
                    f"{permission_code!r} is missing from the permission catalog."
                )
            expected_permission_ids.add(permission.id)

        existing_permission_ids = set(
            (
                await session.scalars(
                    select(MenuPermission.permission_id).where(
                        MenuPermission.menu_id == menu.id
                    )
                )
            ).all()
        )
        permission_ids_to_add = expected_permission_ids - existing_permission_ids
        permission_ids_to_remove = existing_permission_ids - expected_permission_ids

        session.add_all(
            MenuPermission(menu_id=menu.id, permission_id=permission_id)
            for permission_id in permission_ids_to_add
        )
        if permission_ids_to_remove:
            await session.execute(
                delete(MenuPermission).where(
                    MenuPermission.menu_id == menu.id,
                    MenuPermission.permission_id.in_(permission_ids_to_remove),
                )
            )
        await session.flush()
        permission_link_count += len(permission_ids_to_add)

    return seeded_count, permission_link_count


async def _seed_demo_user(
    session: AsyncSession,
    seed: DemoUserSeed,
) -> tuple[User, bool]:
    email = str(seed.email).strip().lower()
    password = seed.password.get_secret_value()
    if len(password) < 12 or len(password) > 128:
        raise ValueError(
            f"The password configured for {email!r} must be 12-128 characters."
        )

    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    created = user is None
    if user is None:
        user = User(
            email=email,
            first_name=seed.first_name,
            last_name=seed.last_name,
            status=UserStatus.ACTIVE,
            is_verified=True,
            is_platform_admin=seed.is_platform_admin,
        )
        session.add(user)
        await session.flush()
        session.add(
            UserCredential(
                user_id=user.id,
                credential_type="password",
                password_hash=PasswordManager.hash_password(password),
            )
        )
        await session.flush()
        return user, created

    if user.deleted_at is not None or user.status != UserStatus.ACTIVE:
        raise ValueError(f"Demo account {email!r} exists but is not active.")
    if user.is_platform_admin != seed.is_platform_admin:
        raise ValueError(
            f"Demo account {email!r} has an unexpected platform-admin flag."
        )
    credential = (
        await session.execute(
            select(UserCredential).where(
                UserCredential.user_id == user.id,
                UserCredential.credential_type == "password",
                UserCredential.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if credential is None or credential.password_hash is None:
        raise ValueError(
            f"Demo account {email!r} has no active password credential. "
            "The seed will not reset existing accounts."
        )
    return user, created


async def seed_demo_users(
    session: AsyncSession,
    tenant: Tenant,
    demo_settings: DemoUserSettings,
    platform_roles: dict[str, Role],
) -> tuple[int, int]:
    """Create local demo identities and assign explicit bootstrap roles."""
    seeds = (
        DemoUserSeed(
            email=str(demo_settings.platform_admin_email),
            password=demo_settings.platform_admin_password,
            first_name="Platform",
            last_name="Administrator",
            role_code=None,
            is_platform_admin=True,
        ),
        DemoUserSeed(
            email=str(demo_settings.platform_support_email),
            password=demo_settings.platform_support_password,
            first_name="Platform",
            last_name="Support",
            role_code=None,
            platform_role_code="platform_support",
        ),
        DemoUserSeed(
            email=str(demo_settings.organization_owner_email),
            password=demo_settings.organization_owner_password,
            first_name="Demo",
            last_name="Owner",
            role_code="org_owner",
        ),
        DemoUserSeed(
            email=str(demo_settings.organization_admin_email),
            password=demo_settings.organization_admin_password,
            first_name="Demo",
            last_name="Admin",
            role_code="org_admin",
        ),
        DemoUserSeed(
            email=str(demo_settings.organization_member_email),
            password=demo_settings.organization_member_password,
            first_name="Demo",
            last_name="Member",
            role_code="member",
        ),
        DemoUserSeed(
            email=str(demo_settings.organization_viewer_email),
            password=demo_settings.organization_viewer_password,
            first_name="Demo",
            last_name="Viewer",
            role_code="viewer",
        ),
    )
    emails = [str(seed.email).strip().lower() for seed in seeds]
    if len(emails) != len(set(emails)):
        raise ValueError("Each demo account must use a distinct email address.")
    passwords = [seed.password.get_secret_value() for seed in seeds]
    if len(passwords) != len(set(passwords)):
        raise ValueError("Each demo account must use a distinct password.")
    if settings.ENVIRONMENT.lower() not in {"development", "test"}:
        raise ValueError(
            "Demo platform and tenant users can only be seeded when "
            "ENVIRONMENT is development or test."
        )
    if tenant.status == TenantStatus.TRIAL:
        tenant.status = TenantStatus.ACTIVE
        await session.flush()
    elif tenant.status != TenantStatus.ACTIVE:
        raise ValueError(
            "The demo organization must be active before demo users can be seeded."
        )

    seeded_users = 0
    seeded_memberships = 0
    owner_user: User | None = None
    platform_admin_user: User | None = None
    role_cache: dict[str, Role] = {}
    for seed in seeds:
        user, created = await _seed_demo_user(session, seed)
        seeded_users += int(created)
        if seed.is_platform_admin:
            platform_admin_user = user
        if seed.platform_role_code is not None:
            if platform_admin_user is None:
                raise ValueError(
                    "The platform administrator must be seeded before platform "
                    "operator accounts."
                )
            platform_role = platform_roles.get(seed.platform_role_code)
            if platform_role is None:
                raise ValueError(
                    f"Required platform role {seed.platform_role_code!r} is not seeded."
                )
            assignment = (
                await session.execute(
                    select(PlatformUserRole).where(
                        PlatformUserRole.user_id == user.id,
                        PlatformUserRole.role_id == platform_role.id,
                        PlatformUserRole.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if assignment is None:
                if not created:
                    raise ValueError(
                        f"Demo platform operator {user.email!r} already exists "
                        "without its seeded role. The seed will not grant "
                        "platform access to an existing account."
                    )
                existing_role_codes = list(
                    (
                        await session.execute(
                            select(Role.code)
                            .join(
                                PlatformUserRole,
                                PlatformUserRole.role_id == Role.id,
                            )
                            .where(
                                PlatformUserRole.user_id == user.id,
                                PlatformUserRole.deleted_at.is_(None),
                                Role.is_platform.is_(True),
                                Role.deleted_at.is_(None),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                session.add(
                    PlatformUserRole(
                        user_id=user.id,
                        role_id=platform_role.id,
                        assigned_by_id=platform_admin_user.id,
                    )
                )
                session.add(
                    PlatformAdminAudit(
                        actor_id=platform_admin_user.id,
                        action="platform.operator.roles_updated",
                        resource_type="platform_operator",
                        resource_public_id=user.public_id,
                        reason="Initial demo platform operator seed",
                        before_state={"role_codes": sorted(existing_role_codes)},
                        after_state={
                            "role_codes": sorted(
                                {*existing_role_codes, platform_role.code}
                            )
                        },
                    )
                )
                await session.flush()
        if seed.role_code is None:
            continue
        if seed.role_code not in role_cache:
            role = (
                await session.execute(
                    select(Role).where(
                        Role.code == seed.role_code,
                        Role.tenant_id.is_(None),
                        Role.is_active.is_(True),
                        Role.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if role is None:
                raise ValueError(
                    f"Required system role {seed.role_code!r} is not seeded."
                )
            role_cache[seed.role_code] = role

        membership = (
            await session.execute(
                select(TenantMembership).where(
                    TenantMembership.tenant_id == tenant.id,
                    TenantMembership.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if membership is None:
            membership = TenantMembership(
                tenant_id=tenant.id,
                user_id=user.id,
                status=MembershipStatus.ACTIVE,
                joined_at=datetime.now(UTC),
                created_by_id=owner_user.id if owner_user is not None else user.id,
            )
            session.add(membership)
            await session.flush()
            seeded_memberships += 1
        elif (
            membership.deleted_at is not None
            or membership.status != MembershipStatus.ACTIVE
        ):
            raise ValueError(
                f"Demo account {user.email!r} has a non-active membership "
                "in the demo organization."
            )

        role = role_cache[seed.role_code]
        role_assignment = (
            await session.execute(
                select(MembershipRole).where(
                    MembershipRole.membership_id == membership.id,
                    MembershipRole.role_id == role.id,
                )
            )
        ).scalar_one_or_none()
        if role_assignment is None:
            actor_id = owner_user.id if owner_user is not None else None
            session.add(
                MembershipRole(
                    membership_id=membership.id,
                    role_id=role.id,
                    assigned_by=actor_id,
                )
            )
            session.add(
                RoleAssignmentAudit(
                    membership_id=membership.id,
                    role_id=role.id,
                    action=RoleAuditAction.ASSIGNED,
                    performed_by=actor_id,
                    reason="Initial demo organization seed",
                )
            )
            await session.flush()

        if seed.role_code == "org_owner":
            owner_user = user

    return seeded_users, seeded_memberships


async def main(*, include_demo_users: bool = True) -> None:
    demo_settings = DemoUserSettings() if include_demo_users else None
    async with AsyncSessionLocal() as session:
        async with session.begin():
            permissions = await seed_permissions(session)
            await seed_roles_and_mappings(session, permissions)
            platform_roles = await seed_platform_roles_and_mappings(
                session,
                permissions,
            )
            menu_count, menu_permission_count = await seed_menus(
                session,
                permissions,
            )
            tenant = await seed_tenant(
                session,
                name=os.getenv("SEED_TENANT_NAME", "Demo Organization"),
                slug=os.getenv("SEED_TENANT_SLUG", "demo-organization"),
            )
            demo_user_count = 0
            demo_membership_count = 0
            if demo_settings is not None:
                demo_user_count, demo_membership_count = await seed_demo_users(
                    session,
                    tenant,
                    demo_settings,
                    platform_roles,
                )
            currencies, countries, references = await seed_shared_catalogs(session)
            core_count = await seed_core_tenant_masters(
                session,
                tenant.id,
                organization_name=tenant.name,
                country_id=countries["IN"],
                currency_id=currencies["INR"],
                state_id=references["KA"],
                city_id=references["BLR"],
                timezone_id=references["Asia/Kolkata"],
                tax_type_id=references["GST"],
            )
            crm_count = await seed_crm_masters(session, tenant.id)
        permission_count = len(permissions)

    print(f"Seeded master data for tenant {tenant.name!r} ({tenant.slug}).")
    print(f"Core tenant master rows added: {core_count}")
    print(f"CRM lookup rows added: {crm_count}")
    print(f"Permission catalog entries synchronized: {permission_count}")
    print(f"Starter menus added: {menu_count}")
    print(f"Menu permission links added: {menu_permission_count}")
    if include_demo_users:
        print(f"Demo users added: {demo_user_count}")
        print(f"Demo organization memberships added: {demo_membership_count}")
