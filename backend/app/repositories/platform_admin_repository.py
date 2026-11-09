"""Persistence operations for the platform administration service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import UserStatus
from app.models.permission import Permission
from app.models.platform_admin_audit import PlatformAdminAudit
from app.models.platform_user_role import PlatformUserRole
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant import Tenant
from app.models.tenant_settings import TenantSettings
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User
from app.models.user_mfa_method import UserMFAMethod


class PlatformAdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def has_verified_mfa(self, user_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(UserMFAMethod.id)
                .where(
                    UserMFAMethod.user_id == user_id,
                    UserMFAMethod.is_verified.is_(True),
                )
                .limit(1)
            )
            is not None
        )

    async def get_platform_permissions_for_user(self, user_id: UUID) -> set[str]:
        result = await self.session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(PlatformUserRole, PlatformUserRole.role_id == Role.id)
            .where(
                PlatformUserRole.user_id == user_id,
                PlatformUserRole.deleted_at.is_(None),
                Role.is_platform.is_(True),
                Role.is_active.is_(True),
                Role.deleted_at.is_(None),
                Permission.is_active.is_(True),
            )
        )
        return set(result.scalars().all())

    async def list_permissions(self) -> list[Permission]:
        result = await self.session.execute(
            select(Permission)
            .where(Permission.is_active.is_(True))
            .order_by(Permission.code)
        )
        return list(result.scalars().all())

    async def get_permissions(self, codes: set[str]) -> list[Permission]:
        if not codes:
            return []
        result = await self.session.execute(
            select(Permission).where(
                Permission.code.in_(codes),
                Permission.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def list_platform_roles(self) -> list[Role]:
        result = await self.session.execute(
            select(Role)
            .where(
                Role.is_platform.is_(True),
                Role.is_active.is_(True),
                Role.deleted_at.is_(None),
            )
            .options(
                selectinload(Role.role_permissions).selectinload(
                    RolePermission.permission
                )
            )
            .order_by(Role.code)
        )
        return list(result.scalars().all())

    async def get_platform_role(
        self, public_id: UUID, *, lock: bool = False
    ) -> Role | None:
        statement = (
            select(Role)
            .where(
                Role.public_id == public_id,
                Role.is_platform.is_(True),
                Role.deleted_at.is_(None),
            )
            .options(
                selectinload(Role.role_permissions).selectinload(
                    RolePermission.permission
                )
            )
        )
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_platform_role(
        self, *, code: str, name: str, description: str | None
    ) -> Role:
        role = Role(
            tenant_id=None,
            code=code,
            name=name,
            description=description,
            is_system=False,
            is_platform=True,
            is_active=True,
        )
        self.session.add(role)
        await self.session.flush()
        return role

    async def platform_role_code_exists(self, code: str) -> bool:
        return bool(
            await self.session.scalar(
                select(Role.id).where(
                    Role.code == code,
                    Role.tenant_id.is_(None),
                )
            )
        )

    async def replace_role_permissions(
        self, *, role_id: UUID, permissions: list[Permission]
    ) -> None:
        from sqlalchemy import delete

        await self.session.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        for permission in permissions:
            self.session.add(
                RolePermission(role_id=role_id, permission_id=permission.id)
            )
        await self.session.flush()

    async def get_user(self, public_id: UUID, *, lock: bool = False) -> User | None:
        statement = select(User).where(
            User.public_id == public_id,
            User.deleted_at.is_(None),
        )
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_operators(self, *, offset: int, limit: int) -> list[User]:
        statement = (
            select(User)
            .where(
                User.deleted_at.is_(None),
                User.status == UserStatus.ACTIVE,
                or_(
                    User.id.in_(
                        select(PlatformUserRole.user_id)
                        .join(Role, Role.id == PlatformUserRole.role_id)
                        .where(
                            PlatformUserRole.deleted_at.is_(None),
                            Role.is_platform.is_(True),
                            Role.is_active.is_(True),
                            Role.deleted_at.is_(None),
                        )
                    ),
                    User.is_platform_admin.is_(True),
                ),
            )
            .order_by(User.email)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_operator_candidates(self, *, offset: int, limit: int) -> list[User]:
        existing_operator_ids = (
            select(PlatformUserRole.user_id)
            .join(Role, Role.id == PlatformUserRole.role_id)
            .where(
                PlatformUserRole.deleted_at.is_(None),
                Role.is_platform.is_(True),
                Role.is_active.is_(True),
                Role.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(
            select(User)
            .where(
                User.status == UserStatus.ACTIVE,
                User.deleted_at.is_(None),
                User.is_platform_admin.is_(False),
                User.id.not_in(existing_operator_ids),
            )
            .order_by(User.email)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_roles(self, user_id: UUID) -> list[PlatformUserRole]:
        result = await self.session.execute(
            select(PlatformUserRole)
            .where(
                PlatformUserRole.user_id == user_id,
                PlatformUserRole.deleted_at.is_(None),
            )
            .options(
                selectinload(PlatformUserRole.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
        )
        return list(result.scalars().all())

    async def get_roles_by_public_ids(self, public_ids: set[UUID]) -> list[Role]:
        if not public_ids:
            return []
        result = await self.session.execute(
            select(Role)
            .where(
                Role.public_id.in_(public_ids),
                Role.is_platform.is_(True),
                Role.is_active.is_(True),
                Role.deleted_at.is_(None),
            )
            .options(
                selectinload(Role.role_permissions).selectinload(
                    RolePermission.permission
                )
            )
        )
        return list(result.scalars().all())

    async def replace_user_roles(
        self, *, user_id: UUID, actor_id: UUID, roles: list[Role]
    ) -> None:
        now = datetime.now(UTC)
        await self.session.execute(
            update(PlatformUserRole)
            .where(
                PlatformUserRole.user_id == user_id,
                PlatformUserRole.deleted_at.is_(None),
            )
            .values(deleted_at=now, deleted_by_id=actor_id)
        )
        for role in roles:
            self.session.add(
                PlatformUserRole(
                    user_id=user_id,
                    role_id=role.id,
                    assigned_by_id=actor_id,
                )
            )
        await self.session.flush()

    async def list_tenants(self, *, offset: int, limit: int) -> list[Tenant]:
        result = await self.session.execute(
            select(Tenant)
            .where(Tenant.deleted_at.is_(None))
            .order_by(Tenant.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_tenant(self, public_id: UUID, *, lock: bool = False) -> Tenant | None:
        statement = select(Tenant).where(
            Tenant.public_id == public_id,
            Tenant.deleted_at.is_(None),
        )
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_tenant(
        self, tenant: Tenant, *, actor_id: UUID, values: dict
    ) -> None:
        for field, value in values.items():
            setattr(tenant, field, value)
        tenant.updated_by_id = actor_id
        await self.session.flush()

    async def get_tenant_settings(self, tenant_id: UUID) -> TenantSettings | None:
        result = await self.session.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def save_tenant_settings(
        self, *, tenant_id: UUID, actor_id: UUID, values: dict
    ) -> TenantSettings:
        settings = await self.get_tenant_settings(tenant_id)
        if settings is None:
            settings = TenantSettings(
                tenant_id=tenant_id,
                updated_by_id=actor_id,
                values=values,
            )
            self.session.add(settings)
        else:
            settings.values = values
            settings.updated_by_id = actor_id
        await self.session.flush()
        return settings

    async def list_plans(self, *, active_only: bool) -> list[SubscriptionPlan]:
        statement = select(SubscriptionPlan).order_by(SubscriptionPlan.code)
        if active_only:
            statement = statement.where(SubscriptionPlan.is_active.is_(True))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def plan_code_exists(self, code: str) -> bool:
        return bool(
            await self.session.scalar(
                select(SubscriptionPlan.id).where(SubscriptionPlan.code == code)
            )
        )

    async def get_plan(
        self, public_id: UUID, *, lock: bool = False
    ) -> SubscriptionPlan | None:
        statement = select(SubscriptionPlan).where(
            SubscriptionPlan.public_id == public_id
        )
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_plan(self, plan: SubscriptionPlan, values: dict) -> None:
        for field, value in values.items():
            setattr(plan, field, value)
        await self.session.flush()

    async def create_plan(self, **values) -> SubscriptionPlan:
        plan = SubscriptionPlan(**values)
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def get_tenant_subscription(
        self, tenant_id: UUID, *, lock: bool = False
    ) -> TenantSubscription | None:
        statement = (
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .options(selectinload(TenantSubscription.plan))
        )
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def save_tenant_subscription(
        self,
        *,
        tenant_id: UUID,
        plan_id: UUID,
        actor_id: UUID,
        status: str,
        starts_at: datetime,
        ends_at: datetime | None,
    ) -> TenantSubscription:
        subscription = await self.get_tenant_subscription(tenant_id, lock=True)
        if subscription is None:
            subscription = TenantSubscription(
                tenant_id=tenant_id,
                plan_id=plan_id,
                updated_by_id=actor_id,
                status=status,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            self.session.add(subscription)
        else:
            subscription.plan_id = plan_id
            subscription.updated_by_id = actor_id
            subscription.status = status
            subscription.starts_at = starts_at
            subscription.ends_at = ends_at
        await self.session.flush()
        result = await self.session.execute(
            select(TenantSubscription)
            .where(TenantSubscription.id == subscription.id)
            .options(
                selectinload(TenantSubscription.plan),
                selectinload(TenantSubscription.tenant),
            )
        )
        return result.scalar_one()

    async def get_tenant_subscription_by_tenant_id(
        self, tenant_id: UUID
    ) -> TenantSubscription | None:
        result = await self.session.execute(
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .options(
                selectinload(TenantSubscription.plan),
                selectinload(TenantSubscription.tenant),
            )
        )
        return result.scalar_one_or_none()

    async def list_audits(self, *, offset: int, limit: int) -> list[PlatformAdminAudit]:
        result = await self.session.execute(
            select(PlatformAdminAudit)
            .options(
                selectinload(PlatformAdminAudit.actor),
                selectinload(PlatformAdminAudit.tenant),
            )
            .order_by(PlatformAdminAudit.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_audit(self, **values) -> PlatformAdminAudit:
        audit = PlatformAdminAudit(**values)
        self.session.add(audit)
        await self.session.flush()
        return audit
