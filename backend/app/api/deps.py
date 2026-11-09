from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database.session import get_db_session
from app.core.enums import MembershipStatus, UserStatus
from app.core.security import TokenManager
from app.models.membership_role import MembershipRole
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant_membership import TenantMembership
from app.models.user import User

# Standard RFC 6750 Bearer authentication scheme
security_scheme = HTTPBearer(auto_error=True)

# ---------------------------------------------------------------------------
# 1. Database Dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an active AsyncSession."""
    async for session in get_db_session():
        yield session


# ---------------------------------------------------------------------------
# 2. Authentication Context
# ---------------------------------------------------------------------------
class AuthenticatedContext:
    """Carries the authenticated user identity and active tenant permissions."""

    def __init__(
        self,
        user: User,
        tenant_id: UUID | None,
        permissions: set[str],
    ):
        self.user = user
        self.tenant_id = tenant_id
        self.permissions = permissions

    @property
    def is_platform_admin(self) -> bool:
        return self.user.is_platform_admin


async def get_current_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthenticatedContext:
    """
    Decodes the Bearer JWT, validates user lifecycle, and resolves effective permissions.
    Usable across /auth, /api/v1, /api/v2 without alteration.
    """
    token = credentials.credentials

    # 1. Decode & Verify JWT
    try:
        payload = TokenManager.decode_access_token(token)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tid"]) if payload.get("tid") else None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Query User & Verify Account Lifecycle
    user_query = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = user_query.scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive, suspended, or deleted.",
        )

    # Platform administrators have wildcard access across the system
    if user.is_platform_admin:
        return AuthenticatedContext(user=user, tenant_id=tenant_id, permissions={"*"})

    # 3. Resolve Workspace-Scoped Permissions (if tenant context is present)
    effective_permissions: set[str] = set()

    if tenant_id:
        membership_query = await db.execute(
            select(TenantMembership)
            .where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user.id,
                TenantMembership.status == MembershipStatus.ACTIVE,
                TenantMembership.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantMembership.membership_roles)
                .selectinload(MembershipRole.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
        )
        membership = membership_query.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active tenant membership not found for this workspace.",
            )

        # Collect permissions from all assigned active roles
        for mr in membership.membership_roles:
            if mr.role and mr.role.is_active and not mr.role.deleted_at:
                for rp in mr.role.role_permissions:
                    if rp.permission and rp.permission.is_active:
                        effective_permissions.add(rp.permission.code)

    return AuthenticatedContext(
        user=user,
        tenant_id=tenant_id,
        permissions=effective_permissions,
    )


# ---------------------------------------------------------------------------
# 3. Reusable RBAC Permission Guard
# ---------------------------------------------------------------------------
class RequirePermission:
    """
    Dependency factory enforcing granular RBAC capability on any route.
    Usage:
        @router.post("/leads", dependencies=[Depends(RequirePermission("crm.lead.create"))])
    """

    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def __call__(
        self,
        context: Annotated[AuthenticatedContext, Depends(get_current_context)],
    ) -> AuthenticatedContext:
        # Wildcard permission bypass (e.g. platform administrators)
        if "*" in context.permissions:
            return context

        if self.permission_code not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required permission: '{self.permission_code}'.",
            )

        return context
