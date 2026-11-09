from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import (
    PlatformAdminContext,
    RequirePlatformPermission,
)
from app.api.platform.v1.dependencies import get_platform_admin_service
from app.schemas.platform_admin import (
    PlatformPermissionResponse,
    PlatformRoleCreate,
    PlatformRolePermissionsUpdate,
    PlatformRoleResponse,
)
from app.services.platform_admin_service import PlatformAdminService

router = APIRouter()


@router.get(
    "/iam/permissions",
    response_model=list[PlatformPermissionResponse],
    summary="List the code-defined permission catalog",
)
async def list_platform_permissions(
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.permission.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> list[PlatformPermissionResponse]:
    return await service.list_permissions()


@router.get(
    "/iam/roles",
    response_model=list[PlatformRoleResponse],
    summary="List platform operator roles",
)
async def list_platform_roles(
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.role.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> list[PlatformRoleResponse]:
    return await service.list_roles()


@router.post(
    "/iam/roles",
    response_model=PlatformRoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a platform operator role",
)
async def create_platform_role(
    payload: PlatformRoleCreate,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.role.manage")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> PlatformRoleResponse:
    return await service.create_role(
        payload=payload,
        actor=context.user,
        actor_permissions=context.permissions,
    )


@router.put(
    "/iam/roles/{role_public_id}/permissions",
    response_model=PlatformRoleResponse,
    summary="Replace permissions granted by a platform role",
)
async def replace_platform_role_permissions(
    role_public_id: UUID,
    payload: PlatformRolePermissionsUpdate,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.role.manage")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> PlatformRoleResponse:
    return await service.update_role_permissions(
        role_public_id=role_public_id,
        payload=payload,
        actor=context.user,
        actor_permissions=context.permissions,
    )
