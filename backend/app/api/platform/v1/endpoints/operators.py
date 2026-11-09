from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import (
    PlatformAdminContext,
    RequirePlatformPermission,
)
from app.api.platform.v1.dependencies import get_platform_admin_service
from app.schemas.platform_admin import (
    PlatformOperatorListItem,
    PlatformOperatorResponse,
    PlatformOperatorRoleUpdate,
)
from app.services.platform_admin_service import PlatformAdminService

router = APIRouter()


@router.get(
    "/operators",
    response_model=list[PlatformOperatorListItem],
    summary="List users with platform operator access",
)
async def list_platform_operators(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.operator.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> list[PlatformOperatorListItem]:
    return await service.list_operators(offset=offset, limit=limit)


@router.get(
    "/operator-candidates",
    response_model=list[PlatformOperatorListItem],
    summary="List active users who can be assigned platform roles",
)
async def list_platform_operator_candidates(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.operator.manage")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> list[PlatformOperatorListItem]:
    return await service.list_operator_candidates(offset=offset, limit=limit)


@router.get(
    "/operators/{user_public_id}",
    response_model=PlatformOperatorResponse,
    summary="Get platform operator role assignments",
)
async def get_platform_operator(
    user_public_id: UUID,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.operator.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> PlatformOperatorResponse:
    return await service.get_operator(user_public_id)


@router.put(
    "/operators/{user_public_id}/roles",
    response_model=PlatformOperatorResponse,
    summary="Replace platform operator role assignments",
)
async def replace_platform_operator_roles(
    user_public_id: UUID,
    payload: PlatformOperatorRoleUpdate,
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.operator.manage")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> PlatformOperatorResponse:
    return await service.replace_operator_roles(
        user_public_id=user_public_id,
        role_public_ids=payload.role_public_ids,
        reason=payload.reason,
        actor=context.user,
        actor_permissions=context.permissions,
    )
