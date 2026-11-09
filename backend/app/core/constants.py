"""
Core IAM & RBAC constants for platform-level roles and permissions.
Scoped strictly to the foundational 10-table identity system.
"""

# ---------------------------------------------------------------------------
# Predefined System Role Codes
# ---------------------------------------------------------------------------
ROLE_PLATFORM_ADMIN = "platform_admin"  # Superadmin / Cross-tenant operator
ROLE_ORG_OWNER = "org_owner"            # Workspace owner with billing & tenant authority
ROLE_ORG_ADMIN = "org_admin"            # Workspace administrator
ROLE_MEMBER = "member"                  # Standard authenticated tenant member
ROLE_VIEWER = "viewer"                  # Read-only tenant member


# ---------------------------------------------------------------------------
# Canonical IAM & RBAC Permissions Matrix
# Format: (module, resource, action, code, description)
# ---------------------------------------------------------------------------
INITIAL_PERMISSIONS: list[tuple[str, str, str, str, str]] = [
    # 1. Global Users & Accounts
    ("IAM", "User", "Create", "iam.user.create", "Provision new user accounts directly"),
    ("IAM", "User", "Read", "iam.user.read", "View user profiles and basic identities"),
    ("IAM", "User", "Update", "iam.user.update", "Update user account profile information"),
    ("IAM", "User", "Delete", "iam.user.delete", "Deactivate or soft-delete user accounts"),
    ("IAM", "User", "Purge", "iam.user.purge", "Permanently hard-delete user accounts (superadmin only)"),

    # 2. Tenants / Organizations
    ("IAM", "Tenant", "Create", "iam.tenant.create", "Provision new tenant organizations/workspaces"),
    ("IAM", "Tenant", "Read", "iam.tenant.read", "View tenant workspace details and settings"),
    ("IAM", "Tenant", "Update", "iam.tenant.update", "Update tenant profile, domain, and configurations"),
    ("IAM", "Tenant", "Delete", "iam.tenant.delete", "Deactivate or soft-delete tenant workspace"),
    ("IAM", "Tenant", "Purge", "iam.tenant.purge", "Permanently hard-delete tenant (superadmin only)"),

    # 3. Tenant Memberships & Invitations
    ("IAM", "Membership", "Create", "iam.membership.create", "Create or invite new users to the tenant workspace"),
    ("IAM", "Membership", "Read", "iam.membership.read", "View members and invitations within the tenant"),
    ("IAM", "Membership", "Update", "iam.membership.update", "Change member status (suspend, reactivate)"),
    ("IAM", "Membership", "Delete", "iam.membership.delete", "Revoke or remove a user's tenant membership"),

    # 4. Roles & Permissions (RBAC Management)
    ("IAM", "Role", "Create", "iam.role.create", "Create custom roles within the tenant"),
    ("IAM", "Role", "Read", "iam.role.read", "View system roles and custom tenant roles"),
    ("IAM", "Role", "Update", "iam.role.update", "Modify custom tenant role details and permission sets"),
    ("IAM", "Role", "Delete", "iam.role.delete", "Delete custom tenant roles"),
    
    # Permissions Catalog (Global - Update restricted to Superadmin)
    ("IAM", "Permission", "Read", "iam.permission.read", "Browse available application permissions"),
    ("IAM", "Permission", "Update", "iam.permission.update", "Modify permission metadata or active state (superadmin only)"),

    # 5. Role Assignments (Membership Roles)
    ("IAM", "RoleAssignment", "Assign", "iam.role_assignment.assign", "Assign roles to tenant members"),
    ("IAM", "RoleAssignment", "Revoke", "iam.role_assignment.revoke", "Revoke roles from tenant members"),

    # 6. Sessions & Security Devices
    ("IAM", "Session", "Read", "iam.session.read", "View active login sessions for user or tenant"),
    ("IAM", "Session", "Revoke", "iam.session.revoke", "Terminate/revoke active login sessions"),
    ("IAM", "MFA", "Manage", "iam.mfa.manage", "Configure and manage MFA credentials (TOTP/WebAuthn)"),

    # 7. Audit Logs
    ("IAM", "Audit", "Read", "iam.audit.read", "View role assignment and security audit history"),
]


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
            "iam.permission.read",       # <-- Read only, cannot edit system permissions
            "iam.role_assignment.assign",
            "iam.role_assignment.revoke",
            "iam.session.read",
            "iam.session.revoke",
            "iam.mfa.manage",
            "iam.audit.read",
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
            "iam.permission.read",       # <-- Read only
            "iam.role_assignment.assign",
            "iam.role_assignment.revoke",
            "iam.session.read",
            "iam.session.revoke",
            "iam.audit.read",
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
