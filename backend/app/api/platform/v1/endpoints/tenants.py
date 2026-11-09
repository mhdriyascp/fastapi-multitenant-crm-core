from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import (
    PlatformAdminContext,
    RequirePlatformPermission,
)
from app.api.platform.v1.dependencies import get_platform_admin_service
from app.schemas.platform_admin import (
    PlatformTenantResponse,
    PlatformTenantUpdate,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)
from app.services.platform_admin_service import PlatformAdminService

router = APIRouter()


@router.get(
    "/tenants",
    response_model=list[PlatformTenantResponse],
    summary="List tenant accounts across the platform",
)
async def list_platform_tenants(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.tenant.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> list[PlatformTenantResponse]:
    return await service.list_tenants(offset=offset, limit=limit)


@router.patch(
    "/tenants/{tenant_public_id}",
    response_model=PlatformTenantResponse,
    summary="Update tenant profile or lifecycle status",
)
async def update_platform_tenant(
    tenant_public_id: UUID,
    payload: PlatformTenantUpdate,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.tenant.update")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> PlatformTenantResponse:
    return await service.update_tenant(
        tenant_public_id=tenant_public_id,
        payload=payload,
        actor=context.user,
    )


@router.get(
    "/tenants/{tenant_public_id}/settings",
    response_model=TenantSettingsResponse,
    summary="Read allowlisted tenant settings",
)
async def get_platform_tenant_settings(
    tenant_public_id: UUID,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.tenant.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> TenantSettingsResponse:
    return await service.get_tenant_settings(tenant_public_id)


@router.put(
    "/tenants/{tenant_public_id}/settings",
    response_model=TenantSettingsResponse,
    summary="Replace allowlisted tenant settings",
)
async def update_platform_tenant_settings(
    tenant_public_id: UUID,
    payload: TenantSettingsUpdate,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.tenant_settings.manage")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> TenantSettingsResponse:
    return await service.update_tenant_settings(
        tenant_public_id=tenant_public_id,
        payload=payload,
        actor=context.user,
    )
