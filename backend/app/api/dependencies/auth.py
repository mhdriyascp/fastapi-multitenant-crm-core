"""Shared authentication and authorization dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.database import get_db
from app.core.enums import MembershipStatus, TenantStatus, UserStatus
from app.core.security import TokenManager
from app.models.membership_role import MembershipRole
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.repositories.platform_admin_repository import PlatformAdminRepository

security_scheme = HTTPBearer(auto_error=True)


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


class PlatformAdminContext:
    """Authenticated platform principal with current platform-scoped permissions."""

    def __init__(self, user: User, permissions: set[str]):
        self.user = user
        self.permissions = permissions


async def get_current_platform_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Authenticate a platform request without resolving tenant context."""
    try:
        payload = TokenManager.decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repository = PlatformAdminRepository(db)
    user = await repository.get_user_by_id(user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive, suspended, or deleted.",
        )
    return user


async def get_current_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthenticatedContext:
    """Resolve the authenticated user and effective tenant permissions."""
    try:
        payload = TokenManager.decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tid"]) if payload.get("tid") else None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_query = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = user_query.scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive, suspended, or deleted.",
        )

    if user.is_platform_admin:
        return AuthenticatedContext(user=user, tenant_id=tenant_id, permissions={"*"})

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
                selectinload(TenantMembership.tenant),
                selectinload(TenantMembership.membership_roles)
                .selectinload(MembershipRole.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission),
            )
        )
        membership = membership_query.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active tenant membership not found for this workspace.",
            )

        if (
            membership.tenant is None
            or membership.tenant.deleted_at is not None
            or membership.tenant.status
            in {TenantStatus.SUSPENDED, TenantStatus.CANCELLED}
        ):
            return AuthenticatedContext(
                user=user,
                tenant_id=tenant_id,
                permissions=set(),
            )

        for membership_role in membership.membership_roles:
            if (
                membership_role.role
                and membership_role.role.is_active
                and not membership_role.role.deleted_at
            ):
                for role_permission in membership_role.role.role_permissions:
                    if (
                        role_permission.permission
                        and role_permission.permission.is_active
                    ):
                        effective_permissions.add(role_permission.permission.code)

    return AuthenticatedContext(
        user=user,
        tenant_id=tenant_id,
        permissions=effective_permissions,
    )


class RequirePermission:
    """Dependency factory enforcing a tenant-scoped permission."""

    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    def __call__(
        self,
        context: Annotated[AuthenticatedContext, Depends(get_current_context)],
    ) -> AuthenticatedContext:
        if "*" in context.permissions:
            return context

        if self.permission_code not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Access denied. Missing required permission: "
                    f"'{self.permission_code}'."
                ),
            )

        return context


class RequirePlatformPermission:
    """Require a platform permission and verified MFA for control-plane access."""

    def __init__(self, permission_code: str):
        self.permission_code = permission_code

    async def __call__(
        self,
        user: Annotated[User, Depends(get_current_platform_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> PlatformAdminContext:
        repository = PlatformAdminRepository(db)
        if not await repository.has_verified_mfa(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verified MFA is required for platform administration.",
            )

        if user.is_platform_admin:
            return PlatformAdminContext(user, {"*"})

        permissions = await repository.get_platform_permissions_for_user(user.id)
        if self.permission_code not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Access denied. Missing platform permission: "
                    f"'{self.permission_code}'."
                ),
            )
        return PlatformAdminContext(user, permissions)
