from typing import Annotated
from uuid import UUID

from app.api.deps import get_db
from app.core.enums import MembershipStatus, UserStatus
from app.core.security.tokens import TokenManager
from app.models.membership_role import MembershipRole
from app.models.role_permission import RolePermission
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Standard RFC 6750 Bearer scheme
security_scheme = HTTPBearer(auto_error=True)


class AuthenticatedContext:
    """Carries the authenticated user identity and active tenant context."""
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
    Decodes the Bearer token, validates the user lifecycle, and builds
    the user's effective permissions for the active workspace.
    Completely decoupled from route versions.
    """
    token = credentials.credentials

    # 1. Decode & Cryptographically Verify Token
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

    # 2. Fetch User & Verify State
    user_query = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = user_query.scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive, suspended, or deleted.",
        )

    # Superadmins bypass permission checks
    if user.is_platform_admin:
        return AuthenticatedContext(user=user, tenant_id=tenant_id, permissions={"*"})

    # 3. Resolve Tenant-Scoped Permissions
    effective_permissions: set[str] = set()

    if tenant_id:
        # Load membership along with assigned roles and their associated permissions
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
                .selectinload(RolePermission.role_permissions)
            )
        )
        membership = membership_query.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active tenant membership not found for this workspace.",
            )

        # Flatten all permission codes from active roles
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


class RequirePermission:
    """
    Dependency factory enforcing RBAC requirements on any route.
    Usable across v1, v2, v3, or background tasks without modification.
    """

    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def __call__(
        self,
        context: Annotated[AuthenticatedContext, Depends(get_current_context)],
    ) -> AuthenticatedContext:
        # Superadmin wildcard bypass
        if "*" in context.permissions:
            return context

        if self.permission_code not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required permission: '{self.permission_code}'.",
            )

        return context
