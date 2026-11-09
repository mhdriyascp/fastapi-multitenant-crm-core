"""Use cases for the platform administration control plane."""

from datetime import UTC, datetime
from uuid import UUID

from app.core.enums import UserStatus
from app.core.exceptions import (
    BusinessRuleViolationException,
    EntityConflictException,
    EntityNotFoundException,
    PermissionDeniedException,
)
from app.models.permission import Permission
from app.models.platform_admin_audit import PlatformAdminAudit
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.schemas.platform_admin import (
    PlatformAuditResponse,
    PlatformOperatorListItem,
    PlatformOperatorResponse,
    PlatformPermissionResponse,
    PlatformRoleCreate,
    PlatformRolePermissionsUpdate,
    PlatformRoleResponse,
    PlatformTenantResponse,
    PlatformTenantUpdate,
    SubscriptionPlanCreate,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
    TenantSettingsResponse,
    TenantSettingsUpdate,
    TenantSubscriptionResponse,
    TenantSubscriptionUpdate,
)


class PlatformAdminService:
    def __init__(self, repository: PlatformAdminRepository):
        self.repository = repository

    @staticmethod
    def _role_response(role: Role) -> PlatformRoleResponse:
        return PlatformRoleResponse(
            public_id=role.public_id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            permission_codes=sorted(
                rp.permission.code
                for rp in role.role_permissions
                if rp.permission is not None and rp.permission.is_active
            ),
        )

    @staticmethod
    def _tenant_response(tenant: Tenant) -> PlatformTenantResponse:
        return PlatformTenantResponse(
            public_id=tenant.public_id,
            name=tenant.name,
            slug=tenant.slug,
            email=tenant.email,
            status=tenant.status,
        )

    async def _assignable_codes(self, actor_permissions: set[str]) -> set[str]:
        catalog = await self.repository.list_permissions()
        all_codes = {permission.code for permission in catalog}
        if "*" in actor_permissions:
            return all_codes
        return actor_permissions & all_codes

    async def _permissions_for_codes(
        self, codes: set[str], actor_permissions: set[str]
    ) -> list[Permission]:
        if not codes:
            return []
        assignable = await self._assignable_codes(actor_permissions)
        if codes - assignable:
            raise PermissionDeniedException(
                "Platform operators cannot grant permissions they do not hold.",
                details={"permission_codes": sorted(codes - assignable)},
            )
        permissions = await self.repository.get_permissions(codes)
        found = {permission.code for permission in permissions}
        if found != codes:
            raise BusinessRuleViolationException(
                "One or more permission codes are unknown or inactive.",
                code="INVALID_PLATFORM_PERMISSION",
            )
        return permissions

    async def list_permissions(self) -> list[PlatformPermissionResponse]:
        return [
            PlatformPermissionResponse.model_validate(permission)
            for permission in await self.repository.list_permissions()
        ]

    async def list_roles(self) -> list[PlatformRoleResponse]:
        return [
            self._role_response(role)
            for role in await self.repository.list_platform_roles()
        ]

    async def create_role(
        self, *, payload: PlatformRoleCreate, actor: User, actor_permissions: set[str]
    ) -> PlatformRoleResponse:
        if await self.repository.platform_role_code_exists(payload.code):
            raise EntityConflictException(
                f"Platform role code '{payload.code}' already exists."
            )
        if len(payload.permission_codes) != len(set(payload.permission_codes)):
            raise BusinessRuleViolationException(
                "Duplicate permission codes are not allowed."
            )
        permissions = await self._permissions_for_codes(
            set(payload.permission_codes), actor_permissions
        )
        role = await self.repository.create_platform_role(
            code=payload.code,
            name=payload.name,
            description=payload.description,
        )
        await self.repository.replace_role_permissions(
            role_id=role.id, permissions=permissions
        )
        await self._audit(
            actor=actor,
            action="platform.role.created",
            resource_type="platform_role",
            resource_public_id=role.public_id,
            reason=payload.reason,
            after_state={
                "code": role.code,
                "name": role.name,
                "permission_codes": sorted(payload.permission_codes),
            },
        )
        return PlatformRoleResponse(
            public_id=role.public_id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            permission_codes=sorted(payload.permission_codes),
        )

    async def update_role_permissions(
        self,
        *,
        role_public_id: UUID,
        payload: PlatformRolePermissionsUpdate,
        actor: User,
        actor_permissions: set[str],
    ) -> PlatformRoleResponse:
        role = await self.repository.get_platform_role(role_public_id, lock=True)
        if role is None:
            raise EntityNotFoundException("Platform role", role_public_id)
        if not role.is_active:
            raise BusinessRuleViolationException(
                "Inactive platform roles cannot be edited."
            )
        if len(payload.permission_codes) != len(set(payload.permission_codes)):
            raise BusinessRuleViolationException(
                "Duplicate permission codes are not allowed."
            )
        new_permissions = await self._permissions_for_codes(
            set(payload.permission_codes), actor_permissions
        )
        previous_codes = sorted(
            rp.permission.code
            for rp in role.role_permissions
            if rp.permission is not None and rp.permission.is_active
        )
        await self.repository.replace_role_permissions(
            role_id=role.id,
            permissions=new_permissions,
        )
        await self._audit(
            actor=actor,
            action="platform.role.permissions_updated",
            resource_type="platform_role",
            resource_public_id=role.public_id,
            reason=payload.reason,
            before_state={"permission_codes": previous_codes},
            after_state={"permission_codes": sorted(payload.permission_codes)},
        )
        return PlatformRoleResponse(
            public_id=role.public_id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            permission_codes=sorted(payload.permission_codes),
        )

    async def list_operators(
        self, *, offset: int, limit: int
    ) -> list[PlatformOperatorListItem]:
        users = await self.repository.list_operators(offset=offset, limit=limit)
        return [
            PlatformOperatorListItem(
                public_id=user.public_id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_platform_admin=user.is_platform_admin,
            )
            for user in users
        ]

    async def list_operator_candidates(
        self, *, offset: int, limit: int
    ) -> list[PlatformOperatorListItem]:
        users = await self.repository.list_operator_candidates(
            offset=offset,
            limit=limit,
        )
        return [
            PlatformOperatorListItem(
                public_id=user.public_id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_platform_admin=False,
            )
            for user in users
        ]

    async def get_operator(self, user_public_id: UUID) -> PlatformOperatorResponse:
        user = await self.repository.get_user(user_public_id)
        if user is None:
            raise EntityNotFoundException("Platform operator", user_public_id)
        assignments = await self.repository.get_user_roles(user.id)
        if not assignments and not user.is_platform_admin:
            raise EntityNotFoundException("Platform operator", user_public_id)
        roles = [
            self._role_response(assignment.role)
            for assignment in assignments
            if assignment.role is not None and assignment.role.is_active
        ]
        return PlatformOperatorResponse(
            public_id=user.public_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            roles=roles,
        )

    async def replace_operator_roles(
        self,
        *,
        user_public_id: UUID,
        role_public_ids: list[UUID],
        reason: str,
        actor: User,
        actor_permissions: set[str],
    ) -> PlatformOperatorResponse:
        if len(role_public_ids) != len(set(role_public_ids)):
            raise BusinessRuleViolationException(
                "Duplicate role identifiers are not allowed."
            )
        user = await self.repository.get_user(user_public_id, lock=True)
        if user is None or user.status != UserStatus.ACTIVE:
            raise EntityNotFoundException("Active platform operator", user_public_id)
        if user.is_platform_admin:
            raise BusinessRuleViolationException(
                "The built-in platform administrator is managed through "
                "bootstrap procedures."
            )
        roles = await self.repository.get_roles_by_public_ids(set(role_public_ids))
        if len(roles) != len(role_public_ids):
            raise EntityNotFoundException("Platform role", role_public_ids)
        assignable = await self._assignable_codes(actor_permissions)
        role_permissions = {
            rp.permission.code
            for role in roles
            for rp in role.role_permissions
            if rp.permission is not None and rp.permission.is_active
        }
        if role_permissions - assignable:
            raise PermissionDeniedException(
                (
                    "Platform operators cannot assign roles with permissions "
                    "they do not hold."
                ),
                details={"permission_codes": sorted(role_permissions - assignable)},
            )
        previous = await self.repository.get_user_roles(user.id)
        previous_roles = sorted(
            assignment.role.code
            for assignment in previous
            if assignment.role is not None
        )
        await self.repository.replace_user_roles(
            user_id=user.id,
            actor_id=actor.id,
            roles=roles,
        )
        await self._audit(
            actor=actor,
            action="platform.operator.roles_updated",
            resource_type="platform_operator",
            resource_public_id=user.public_id,
            reason=reason,
            before_state={"role_codes": previous_roles},
            after_state={"role_codes": sorted(role.code for role in roles)},
        )
        return await self.get_operator(user_public_id)

    async def list_tenants(
        self, *, offset: int, limit: int
    ) -> list[PlatformTenantResponse]:
        return [
            self._tenant_response(tenant)
            for tenant in await self.repository.list_tenants(offset=offset, limit=limit)
        ]

    async def update_tenant(
        self, *, tenant_public_id: UUID, payload: PlatformTenantUpdate, actor: User
    ) -> PlatformTenantResponse:
        tenant = await self.repository.get_tenant(tenant_public_id, lock=True)
        if tenant is None:
            raise EntityNotFoundException("Tenant", tenant_public_id)
        before = {"name": tenant.name, "status": tenant.status.value}
        updates = payload.model_dump(exclude={"reason"}, exclude_unset=True)
        if not updates:
            raise BusinessRuleViolationException(
                "Provide at least one tenant field to update."
            )
        await self.repository.update_tenant(tenant, actor_id=actor.id, values=updates)
        await self._audit(
            actor=actor,
            tenant_id=tenant.id,
            action="platform.tenant.updated",
            resource_type="tenant",
            resource_public_id=tenant.public_id,
            reason=payload.reason,
            before_state=before,
            after_state={"name": tenant.name, "status": tenant.status.value},
        )
        return self._tenant_response(tenant)

    async def get_tenant_settings(
        self, tenant_public_id: UUID
    ) -> TenantSettingsResponse:
        tenant = await self.repository.get_tenant(tenant_public_id)
        if tenant is None:
            raise EntityNotFoundException("Tenant", tenant_public_id)
        settings = await self.repository.get_tenant_settings(tenant.id)
        return TenantSettingsResponse(
            tenant_public_id=tenant.public_id,
            values=settings.values if settings else {},
            updated_at=settings.updated_at if settings else None,
        )

    async def update_tenant_settings(
        self,
        *,
        tenant_public_id: UUID,
        payload: TenantSettingsUpdate,
        actor: User,
    ) -> TenantSettingsResponse:
        tenant = await self.repository.get_tenant(tenant_public_id, lock=True)
        if tenant is None:
            raise EntityNotFoundException("Tenant", tenant_public_id)
        previous = await self.repository.get_tenant_settings(tenant.id)
        before_state = previous.values if previous else {}
        values = payload.model_dump(mode="json", exclude={"reason"})
        settings = await self.repository.save_tenant_settings(
            tenant_id=tenant.id,
            actor_id=actor.id,
            values=values,
        )
        await self._audit(
            actor=actor,
            tenant_id=tenant.id,
            action="platform.tenant.settings_updated",
            resource_type="tenant_settings",
            resource_public_id=tenant.public_id,
            reason=payload.reason,
            before_state=before_state,
            after_state=values,
        )
        return TenantSettingsResponse(
            tenant_public_id=tenant.public_id,
            values=settings.values,
            updated_at=settings.updated_at,
        )

    async def list_plans(
        self, *, include_inactive: bool
    ) -> list[SubscriptionPlanResponse]:
        return [
            SubscriptionPlanResponse.model_validate(plan)
            for plan in await self.repository.list_plans(
                active_only=not include_inactive
            )
        ]

    async def create_plan(
        self, *, payload: SubscriptionPlanCreate, actor: User
    ) -> SubscriptionPlanResponse:
        if await self.repository.plan_code_exists(payload.code):
            raise EntityConflictException(
                f"Subscription plan code '{payload.code}' already exists."
            )
        values = payload.model_dump(exclude={"reason"})
        plan = await self.repository.create_plan(**values)
        await self._audit(
            actor=actor,
            action="platform.plan.created",
            resource_type="subscription_plan",
            resource_public_id=plan.public_id,
            reason=payload.reason,
            after_state=values,
        )
        return SubscriptionPlanResponse.model_validate(plan)

    async def update_plan(
        self,
        *,
        plan_public_id: UUID,
        payload: SubscriptionPlanUpdate,
        actor: User,
    ) -> SubscriptionPlanResponse:
        plan = await self.repository.get_plan(plan_public_id, lock=True)
        if plan is None:
            raise EntityNotFoundException("Subscription plan", plan_public_id)
        before = {
            "name": plan.name,
            "description": plan.description,
            "price_minor": plan.price_minor,
            "currency": plan.currency,
            "entitlements": plan.entitlements,
            "is_active": plan.is_active,
        }
        updates = payload.model_dump(exclude={"reason"}, exclude_unset=True)
        updates = {key: value for key, value in updates.items() if value is not None}
        if not updates:
            raise BusinessRuleViolationException(
                "Provide at least one plan field to update."
            )
        await self.repository.update_plan(plan, updates)
        await self._audit(
            actor=actor,
            action="platform.plan.updated",
            resource_type="subscription_plan",
            resource_public_id=plan.public_id,
            reason=payload.reason,
            before_state=before,
            after_state={**before, **updates},
        )
        return SubscriptionPlanResponse.model_validate(plan)

    async def get_tenant_subscription(
        self, tenant_public_id: UUID
    ) -> TenantSubscriptionResponse | None:
        tenant = await self.repository.get_tenant(tenant_public_id)
        if tenant is None:
            raise EntityNotFoundException("Tenant", tenant_public_id)
        subscription = await self.repository.get_tenant_subscription_by_tenant_id(
            tenant.id
        )
        if subscription is None:
            return None
        return TenantSubscriptionResponse(
            public_id=subscription.public_id,
            tenant_public_id=tenant.public_id,
            plan=SubscriptionPlanResponse.model_validate(subscription.plan),
            status=subscription.status,
            starts_at=subscription.starts_at,
            ends_at=subscription.ends_at,
        )

    async def assign_tenant_plan(
        self,
        *,
        tenant_public_id: UUID,
        payload: TenantSubscriptionUpdate,
        actor: User,
    ) -> TenantSubscriptionResponse:
        tenant = await self.repository.get_tenant(tenant_public_id, lock=True)
        if tenant is None:
            raise EntityNotFoundException("Tenant", tenant_public_id)
        plan = await self.repository.get_plan(payload.plan_public_id, lock=True)
        if plan is None or not plan.is_active:
            raise EntityNotFoundException(
                "Active subscription plan", payload.plan_public_id
            )
        starts_at = payload.starts_at or datetime.now(UTC)
        if payload.ends_at is not None and payload.ends_at <= starts_at:
            raise BusinessRuleViolationException(
                "Subscription end time must be after start time."
            )
        previous = await self.repository.get_tenant_subscription(tenant.id)
        before_state = (
            {
                "plan_public_id": str(previous.plan.public_id),
                "status": previous.status,
                "starts_at": previous.starts_at.isoformat(),
                "ends_at": previous.ends_at.isoformat() if previous.ends_at else None,
            }
            if previous
            else None
        )
        subscription = await self.repository.save_tenant_subscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            actor_id=actor.id,
            status=payload.status,
            starts_at=starts_at,
            ends_at=payload.ends_at,
        )
        await self._audit(
            actor=actor,
            tenant_id=tenant.id,
            action="platform.tenant.plan_assigned",
            resource_type="tenant_subscription",
            resource_public_id=subscription.public_id,
            reason=payload.reason,
            before_state=before_state,
            after_state={
                "plan_public_id": str(plan.public_id),
                "status": subscription.status,
                "starts_at": starts_at.isoformat(),
                "ends_at": payload.ends_at.isoformat() if payload.ends_at else None,
            },
        )
        return TenantSubscriptionResponse(
            public_id=subscription.public_id,
            tenant_public_id=tenant.public_id,
            plan=SubscriptionPlanResponse.model_validate(subscription.plan),
            status=subscription.status,
            starts_at=subscription.starts_at,
            ends_at=subscription.ends_at,
        )

    async def list_audits(
        self, *, offset: int, limit: int
    ) -> list[PlatformAuditResponse]:
        audits = await self.repository.list_audits(offset=offset, limit=limit)
        return [
            PlatformAuditResponse(
                public_id=audit.public_id,
                actor_public_id=audit.actor.public_id if audit.actor else None,
                tenant_public_id=audit.tenant.public_id if audit.tenant else None,
                action=audit.action,
                resource_type=audit.resource_type,
                resource_public_id=audit.resource_public_id,
                reason=audit.reason,
                before_state=audit.before_state,
                after_state=audit.after_state,
                created_at=audit.created_at,
            )
            for audit in audits
        ]

    async def _audit(
        self,
        *,
        actor: User,
        action: str,
        resource_type: str,
        resource_public_id: UUID | None,
        reason: str,
        tenant_id: UUID | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
    ) -> PlatformAdminAudit:
        return await self.repository.add_audit(
            actor_id=actor.id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_public_id=resource_public_id,
            reason=reason,
            before_state=before_state,
            after_state=after_state,
        )
