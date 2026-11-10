"""Platform APIs for managing globally shared master-data catalogs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    PlatformAdminContext,
    RequirePlatformPermission,
    get_current_platform_user,
)
from app.api.dependencies.database import get_db
from app.core.exceptions import EntityNotFoundException
from app.core.master_data_registry import MASTER_DATA_RESOURCES
from app.models.user import User
from app.schemas.master_data import (
    MasterDataPage,
    MasterDataRecord,
    PlatformMasterDataWriteRequest,
)
from app.services.master_data_service import MasterDataService


async def require_shared_catalog_permission(
    request: Request,
    user: Annotated[User, Depends(get_current_platform_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformAdminContext:
    resource_name = str(request.path_params.get("resource", ""))
    resource = MASTER_DATA_RESOURCES.get(resource_name)
    if resource is None or resource.scope != "shared":
        raise EntityNotFoundException("Shared master-data resource", resource_name)

    action_by_method = {
        "GET": "read",
        "POST": "create",
        "PATCH": "update",
        "DELETE": "delete",
    }
    action = action_by_method.get(request.method)
    if action is None:
        raise EntityNotFoundException("Shared master-data operation", request.method)
    permission = f"platform.{resource.permission_prefix}.{action}"
    return await RequirePlatformPermission(permission)(user, db)


SharedCatalogContext = Annotated[
    PlatformAdminContext, Depends(require_shared_catalog_permission)
]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
router = APIRouter(
    prefix="/master-data/shared",
    tags=["Platform - Shared Master Data"],
    dependencies=[Depends(require_shared_catalog_permission)],
)


@router.get(
    "/{resource}",
    response_model=MasterDataPage,
    summary="List a global reference catalog",
)
async def list_shared_catalog(
    resource: str,
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[
        str | None,
        Query(max_length=256, description="Opaque cursor from the previous page."),
    ] = None,
) -> MasterDataPage:
    return await MasterDataService(db).list_records(
        resource,
        tenant_id=None,
        limit=limit,
        cursor=cursor,
    )


@router.post(
    "/{resource}",
    response_model=MasterDataRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create a global reference",
    description="A reason is required and is recorded in the platform audit trail.",
)
async def create_shared_catalog_record(
    resource: str,
    payload: PlatformMasterDataWriteRequest,
    context: SharedCatalogContext,
    db: DatabaseSession,
) -> MasterDataRecord:
    return await MasterDataService(db).create_record(
        resource,
        payload.values,
        tenant_id=None,
        actor_id=context.user.id,
        reason=payload.reason,
    )


@router.get(
    "/{resource}/{public_id}",
    response_model=MasterDataRecord,
    summary="Get a global reference",
)
async def get_shared_catalog_record(
    resource: str,
    public_id: UUID,
    db: DatabaseSession,
) -> MasterDataRecord:
    return await MasterDataService(db).get_record(
        resource,
        public_id,
        tenant_id=None,
    )


@router.patch(
    "/{resource}/{public_id}",
    response_model=MasterDataRecord,
    summary="Update a global reference",
)
async def update_shared_catalog_record(
    resource: str,
    public_id: UUID,
    payload: PlatformMasterDataWriteRequest,
    context: SharedCatalogContext,
    db: DatabaseSession,
) -> MasterDataRecord:
    return await MasterDataService(db).update_record(
        resource,
        public_id,
        payload.values,
        tenant_id=None,
        actor_id=context.user.id,
        reason=payload.reason,
    )


@router.delete(
    "/{resource}/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a global reference",
    description="A reason of at least 8 characters is required and audited.",
)
async def delete_shared_catalog_record(
    resource: str,
    public_id: UUID,
    context: SharedCatalogContext,
    db: DatabaseSession,
    reason: Annotated[str, Query(min_length=8, max_length=500)],
) -> Response:
    await MasterDataService(db).delete_record(
        resource,
        public_id,
        tenant_id=None,
        actor_id=context.user.id,
        reason=reason,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
