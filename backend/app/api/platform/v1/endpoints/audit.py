from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import (
    PlatformAdminContext,
    RequirePlatformPermission,
)
from app.api.platform.v1.dependencies import get_platform_admin_service
from app.schemas.platform_admin import PlatformAuditResponse
from app.services.platform_admin_service import PlatformAdminService

router = APIRouter()


@router.get(
    "/audit-events",
    response_model=list[PlatformAuditResponse],
    summary="Read platform administration audit events",
)
async def list_platform_audit_events(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    context: PlatformAdminContext = Depends(
        RequirePlatformPermission("platform.audit.read")
    ),
    service: PlatformAdminService = Depends(get_platform_admin_service),
) -> list[PlatformAuditResponse]:
    return await service.list_audits(offset=offset, limit=limit)
