from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import (
    PlatformAdminContext,
    RequirePlatformPermission,
)
from app.api.platform.v1.dependencies import get_platform_admin_service
from app.schemas.platform_admin import (
    SubscriptionPlanCreate,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
    TenantSubscriptionResponse,
    TenantSubscriptionUpdate,
)
from app.services.platform_admin_service import PlatformAdminService

router = APIRouter()


@router.get(
    "/plans",
    response_model=list[SubscriptionPlanResponse],
    summary="List subscription plans",
)
async def list_subscription_plans(
    include_inactive: bool = False,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.plan.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> list[SubscriptionPlanResponse]:
    return await service.list_plans(include_inactive=include_inactive)


@router.post(
    "/plans",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subscription plan",
)
async def create_subscription_plan(
    payload: SubscriptionPlanCreate,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.plan.manage")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> SubscriptionPlanResponse:
    return await service.create_plan(payload=payload, actor=context.user)


@router.patch(
    "/plans/{plan_public_id}",
    response_model=SubscriptionPlanResponse,
    summary="Update or deactivate a subscription plan",
)
async def update_subscription_plan(
    plan_public_id: UUID,
    payload: SubscriptionPlanUpdate,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.plan.manage")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> SubscriptionPlanResponse:
    return await service.update_plan(
        plan_public_id=plan_public_id,
        payload=payload,
        actor=context.user,
    )


@router.get(
    "/tenants/{tenant_public_id}/subscription",
    response_model=TenantSubscriptionResponse | None,
    summary="Get a tenant's current plan assignment",
)
async def get_tenant_subscription(
    tenant_public_id: UUID,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.plan.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> TenantSubscriptionResponse | None:
    return await service.get_tenant_subscription(tenant_public_id)


@router.put(
    "/tenants/{tenant_public_id}/subscription",
    response_model=TenantSubscriptionResponse,
    summary="Assign or replace a tenant's plan",
)
async def assign_tenant_subscription(
    tenant_public_id: UUID,
    payload: TenantSubscriptionUpdate,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.plan.manage")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> TenantSubscriptionResponse:
    return await service.assign_tenant_plan(
        tenant_public_id=tenant_public_id,
        payload=payload,
        actor=context.user,
    )
