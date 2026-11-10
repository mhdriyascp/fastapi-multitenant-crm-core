"""
Core IAM & RBAC constants for platform-level roles and permissions.
Scoped strictly to the foundational 10-table identity system.
"""

# ---------------------------------------------------------------------------
# Predefined System Role Codes
# ---------------------------------------------------------------------------
ROLE_PLATFORM_ADMIN = "platform_admin"  # Superadmin / Cross-tenant operator
ROLE_ORG_OWNER = "org_owner"  # Workspace owner with billing & tenant authority
ROLE_ORG_ADMIN = "org_admin"  # Workspace administrator
ROLE_MEMBER = "member"  # Standard authenticated tenant member
ROLE_VIEWER = "viewer"  # Read-only tenant member


# ---------------------------------------------------------------------------
# Canonical IAM & RBAC Permissions Matrix
# Format: (module, resource, action, code, description)
# ---------------------------------------------------------------------------
INITIAL_PERMISSIONS: list[tuple[str, str, str, str, str]] = [
    # Platform control plane (operator-only)
    ("Platform", "Tenant", "Read", "platform.tenant.read", "View tenant accounts"),
    (
        "Platform",
        "Tenant",
        "Update",
        "platform.tenant.update",
        "Update tenant status and profile",
    ),
    (
        "Platform",
        "TenantSettings",
        "Manage",
        "platform.tenant_settings.manage",
        "Manage allowlisted tenant settings",
    ),
    (
        "Platform",
        "Plan",
        "Read",
        "platform.plan.read",
        "View platform subscription plans",
    ),
    (
        "Platform",
        "Plan",
        "Manage",
        "platform.plan.manage",
        "Manage plans and tenant plan assignments",
    ),
    (
        "Platform",
        "Permission",
        "Read",
        "platform.permission.read",
        "Browse the platform permission catalog",
    ),
    ("Platform", "Role", "Read", "platform.role.read", "View platform operator roles"),
    (
        "Platform",
        "Role",
        "Manage",
        "platform.role.manage",
        "Create platform operator roles and grant permissions",
    ),
    (
        "Platform",
        "Operator",
        "Read",
        "platform.operator.read",
        "View platform operator accounts",
    ),
    (
        "Platform",
        "Operator",
        "Manage",
        "platform.operator.manage",
        "Assign platform operator roles",
    ),
    (
        "Platform",
        "Audit",
        "Read",
        "platform.audit.read",
        "Read platform administration audit events",
    ),
    # 1. Global Users & Accounts
    (
        "IAM",
        "User",
        "Create",
        "iam.user.create",
        "Provision new user accounts directly",
    ),
    ("IAM", "User", "Read", "iam.user.read", "View user profiles and basic identities"),
    (
        "IAM",
        "User",
        "Update",
        "iam.user.update",
        "Update user account profile information",
    ),
    (
        "IAM",
        "User",
        "Delete",
        "iam.user.delete",
        "Deactivate or soft-delete user accounts",
    ),
    (
        "IAM",
        "User",
        "Purge",
        "iam.user.purge",
        "Permanently hard-delete user accounts (superadmin only)",
    ),
    # 2. Tenants / Organizations
    (
        "IAM",
        "Tenant",
        "Create",
        "iam.tenant.create",
        "Provision new tenant organizations/workspaces",
    ),
    (
        "IAM",
        "Tenant",
        "Read",
        "iam.tenant.read",
        "View tenant workspace details and settings",
    ),
    (
        "IAM",
        "Tenant",
        "Update",
        "iam.tenant.update",
        "Update tenant profile, domain, and configurations",
    ),
    (
        "IAM",
        "Tenant",
        "Delete",
        "iam.tenant.delete",
        "Deactivate or soft-delete tenant workspace",
    ),
    (
        "IAM",
        "Tenant",
        "Purge",
        "iam.tenant.purge",
        "Permanently hard-delete tenant (superadmin only)",
    ),
    # 3. Tenant Memberships & Invitations
    (
        "IAM",
        "Membership",
        "Create",
        "iam.membership.create",
        "Create or invite new users to the tenant workspace",
    ),
    (
        "IAM",
        "Membership",
        "Read",
        "iam.membership.read",
        "View members and invitations within the tenant",
    ),
    (
        "IAM",
        "Membership",
        "Update",
        "iam.membership.update",
        "Change member status (suspend, reactivate)",
    ),
    (
        "IAM",
        "Membership",
        "Delete",
        "iam.membership.delete",
        "Revoke or remove a user's tenant membership",
    ),
    # 4. Roles & Permissions (RBAC Management)
    (
        "IAM",
        "Role",
        "Create",
        "iam.role.create",
        "Create custom roles within the tenant",
    ),
    (
        "IAM",
        "Role",
        "Read",
        "iam.role.read",
        "View system roles and custom tenant roles",
    ),
    (
        "IAM",
        "Role",
        "Update",
        "iam.role.update",
        "Modify custom tenant role details and permission sets",
    ),
    ("IAM", "Role", "Delete", "iam.role.delete", "Delete custom tenant roles"),
    # Permissions Catalog (Global - Update restricted to Superadmin)
    (
        "IAM",
        "Permission",
        "Read",
        "iam.permission.read",
        "Browse available application permissions",
    ),
    (
        "IAM",
        "Permission",
        "Update",
        "iam.permission.update",
        "Modify permission metadata or active state (superadmin only)",
    ),
    # 5. Role Assignments (Membership Roles)
    (
        "IAM",
        "RoleAssignment",
        "Assign",
        "iam.role_assignment.assign",
        "Assign roles to tenant members",
    ),
    (
        "IAM",
        "RoleAssignment",
        "Revoke",
        "iam.role_assignment.revoke",
        "Revoke roles from tenant members",
    ),
    # 6. Sessions & Security Devices
    (
        "IAM",
        "Session",
        "Read",
        "iam.session.read",
        "View active login sessions for user or tenant",
    ),
    (
        "IAM",
        "Session",
        "Revoke",
        "iam.session.revoke",
        "Terminate/revoke active login sessions",
    ),
    (
        "IAM",
        "MFA",
        "Manage",
        "iam.mfa.manage",
        "Configure and manage MFA credentials (TOTP/WebAuthn)",
    ),
    # 7. Audit Logs
    (
        "IAM",
        "Audit",
        "Read",
        "iam.audit.read",
        "View role assignment and security audit history",
    ),
]

MASTER_DATA_PERMISSION_RESOURCES: tuple[tuple[str, str, str], ...] = (
    ("Master Data", "Organization", "master_data.organization"),
    ("Master Data", "Legal Entity", "master_data.legal_entity"),
    ("Master Data", "Branch", "master_data.branch"),
    ("Master Data", "Department", "master_data.department"),
    ("Master Data", "Designation", "master_data.designation"),
    ("Master Data", "Team", "master_data.team"),
    ("Master Data", "Location", "master_data.location"),
    ("Master Data", "Business Unit", "master_data.business_unit"),
    ("Master Data", "Cost Center", "master_data.cost_center"),
    ("Master Data", "Fiscal Year", "master_data.fiscal_year"),
    ("Master Data", "Currency", "master_data.currency"),
    ("Master Data", "Country", "master_data.country"),
    ("Master Data", "State", "master_data.state"),
    ("Master Data", "City", "master_data.city"),
    ("Master Data", "Time Zone", "master_data.time_zone"),
    ("Master Data", "Language", "master_data.language"),
    ("Master Data", "Unit of Measure", "master_data.unit_of_measure"),
    ("Master Data", "Tax Type", "master_data.tax_type"),
    ("Master Data", "Tax Rate", "master_data.tax_rate"),
    ("CRM", "Account Type", "crm.account_type"),
    ("CRM", "Account Category", "crm.account_category"),
    ("CRM", "Account Group", "crm.account_group"),
    ("CRM", "Contact Type", "crm.contact_type"),
    ("CRM", "Address Type", "crm.address_type"),
    ("CRM", "Customer Segment", "crm.customer_segment"),
    ("CRM", "Customer Group", "crm.customer_group"),
    ("CRM", "Lead Source", "crm.lead_source"),
    ("CRM", "Lead Status", "crm.lead_status"),
    ("CRM", "Lead Rating", "crm.lead_rating"),
    ("CRM", "Opportunity Stage", "crm.opportunity_stage"),
    ("CRM", "Opportunity Type", "crm.opportunity_type"),
    ("CRM", "Sales Territory", "crm.sales_territory"),
    ("CRM", "Sales Team", "crm.sales_team"),
    ("CRM", "Competitor", "crm.competitor"),
    ("CRM", "Lost Reason", "crm.lost_reason"),
    ("CRM", "Campaign Type", "crm.campaign_type"),
    ("CRM", "Activity Type", "crm.activity_type"),
    ("CRM", "Communication Channel", "crm.communication_channel"),
)
MASTER_DATA_ACTIONS: tuple[tuple[str, str], ...] = (
    ("Create", "create"),
    ("Read", "read"),
    ("Update", "update"),
    ("Delete", "delete"),
)
MASTER_DATA_PERMISSION_CODES = tuple(
    f"{permission_prefix}.{action_code}"
    for _, _, permission_prefix in MASTER_DATA_PERMISSION_RESOURCES
    for _, action_code in MASTER_DATA_ACTIONS
)
SHARED_MASTER_DATA_PERMISSION_PREFIXES = frozenset(
    {
        "master_data.currency",
        "master_data.country",
        "master_data.state",
        "master_data.city",
        "master_data.time_zone",
        "master_data.language",
        "master_data.unit_of_measure",
        "master_data.tax_type",
    }
)
TENANT_MASTER_DATA_PERMISSION_CODES = tuple(
    f"{permission_prefix}.{action_code}"
    for _, _, permission_prefix in MASTER_DATA_PERMISSION_RESOURCES
    if permission_prefix not in SHARED_MASTER_DATA_PERMISSION_PREFIXES
    for _, action_code in MASTER_DATA_ACTIONS
)
SHARED_MASTER_DATA_READ_PERMISSION_CODES = tuple(
    f"{permission_prefix}.read"
    for _, _, permission_prefix in MASTER_DATA_PERMISSION_RESOURCES
    if permission_prefix in SHARED_MASTER_DATA_PERMISSION_PREFIXES
)

INITIAL_PERMISSIONS.extend(
    (
        module,
        resource,
        action,
        f"{permission_prefix}.{action_code}",
        f"{action} {resource.lower()} master data",
    )
    for module, resource, permission_prefix in MASTER_DATA_PERMISSION_RESOURCES
    for action, action_code in MASTER_DATA_ACTIONS
)

PLATFORM_MASTER_DATA_PERMISSION_CODES = tuple(
    f"platform.{permission_prefix}.{action_code}"
    for _, _, permission_prefix in MASTER_DATA_PERMISSION_RESOURCES
    if permission_prefix in SHARED_MASTER_DATA_PERMISSION_PREFIXES
    for _, action_code in MASTER_DATA_ACTIONS
)
INITIAL_PERMISSIONS.extend(
    (
        "Platform",
        resource,
        action,
        f"platform.{permission_prefix}.{action_code}",
        f"{action} global {resource.lower()} master data",
    )
    for module, resource, permission_prefix in MASTER_DATA_PERMISSION_RESOURCES
    if module == "Master Data"
    and permission_prefix in SHARED_MASTER_DATA_PERMISSION_PREFIXES
    for action, action_code in MASTER_DATA_ACTIONS
)


# ---------------------------------------------------------------------------
# Predefined Global System Roles
# ---------------------------------------------------------------------------
SYSTEM_ROLES: list[dict] = [
    {
        "name": "Platform Administrator",
        "code": ROLE_PLATFORM_ADMIN,
        "description": "System superadmin with complete operational authority across all tenants",
        "is_system": True,
        # Platform admin receives wildcard access across the entire platform
        "permissions": ["*"],
    },
    {
        "name": "Organization Owner",
        "code": ROLE_ORG_OWNER,
        "description": "Primary workspace owner with full control over members, roles, settings, and billing",
        "is_system": True,
        "permissions": [
            "iam.user.read",
            "iam.tenant.read",
            "iam.tenant.update",
            "iam.tenant.delete",
            "iam.membership.create",
            "iam.membership.read",
            "iam.membership.update",
            "iam.membership.delete",
            "iam.role.create",
            "iam.role.read",
            "iam.role.update",
            "iam.role.delete",
            "iam.permission.read",  # <-- Read only, cannot edit system permissions
            "iam.role_assignment.assign",
            "iam.role_assignment.revoke",
            "iam.session.read",
            "iam.session.revoke",
            "iam.mfa.manage",
            "iam.audit.read",
            *TENANT_MASTER_DATA_PERMISSION_CODES,
            *SHARED_MASTER_DATA_READ_PERMISSION_CODES,
        ],
    },
    {
        "name": "Organization Administrator",
        "code": ROLE_ORG_ADMIN,
        "description": "Workspace administrator capable of managing members, roles, and day-to-day operations",
        "is_system": True,
        "permissions": [
            "iam.user.read",
            "iam.tenant.read",
            "iam.membership.create",
            "iam.membership.read",
            "iam.membership.update",
            "iam.membership.delete",
            "iam.role.read",
            "iam.permission.read",  # <-- Read only
            "iam.role_assignment.assign",
            "iam.role_assignment.revoke",
            "iam.session.read",
            "iam.session.revoke",
            "iam.audit.read",
            *TENANT_MASTER_DATA_PERMISSION_CODES,
            *SHARED_MASTER_DATA_READ_PERMISSION_CODES,
        ],
    },
    {
        "name": "Member",
        "code": ROLE_MEMBER,
        "description": "Standard tenant user with access to view workspace info and manage own profile",
        "is_system": True,
        "permissions": [
            "iam.user.read",
            "iam.user.update",
            "iam.tenant.read",
            "iam.membership.read",
            "iam.session.read",
            "iam.session.revoke",
            "iam.mfa.manage",
        ],
    },
    {
        "name": "Viewer",
        "code": ROLE_VIEWER,
        "description": "Read-only workspace member",
        "is_system": True,
        "permissions": [
            "iam.tenant.read",
            "iam.membership.read",
        ],
    },
]
