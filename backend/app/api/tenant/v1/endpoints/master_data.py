"""Tenant APIs for tenant-owned masters and read-only shared catalogs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    AuthenticatedContext,
    RequirePermission,
    get_current_context,
)
from app.api.dependencies.database import get_db
from app.core.exceptions import EntityNotFoundException
from app.core.master_data_registry import MASTER_DATA_RESOURCES
from app.schemas.master_data import (
    MasterDataPage,
    MasterDataRecord,
    MasterDataWriteRequest,
)
from app.services.master_data_service import MasterDataService

router = APIRouter()


async def require_master_data_permission(
    request: Request,
    context: Annotated[AuthenticatedContext, Depends(get_current_context)],
) -> AuthenticatedContext:
    resource_name = str(request.path_params.get("resource", ""))
    resource = MASTER_DATA_RESOURCES.get(resource_name)
    if resource is None:
        raise EntityNotFoundException("Master-data resource", resource_name)

    is_shared_route = "/master-data/shared/" in request.url.path
    expected_scope = "shared" if is_shared_route else "tenant"
    if resource.scope != expected_scope:
        raise EntityNotFoundException("Master-data resource", resource_name)
    if is_shared_route and request.method != "GET":
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Shared catalogs are read-only for tenant APIs.",
        )

    action_by_method = {
        "GET": "read",
        "POST": "create",
        "PATCH": "update",
        "DELETE": "delete",
    }
    action = action_by_method.get(request.method)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Unsupported operation for master data.",
        )
    return RequirePermission(f"{resource.permission_prefix}.{action}")(context)


MasterDataContext = Annotated[
    AuthenticatedContext, Depends(require_master_data_permission)
]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/shared/{resource}",
    response_model=MasterDataPage,
    summary="List a shared reference catalog",
    description="Lists active shared catalog rows using public IDs. Tenant users cannot mutate shared catalogs.",
)
async def list_shared_catalog(
    resource: str,
    context: MasterDataContext,
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[
        str | None,
        Query(max_length=256, description="Opaque cursor from the previous page."),
    ] = None,
) -> MasterDataPage:
    return await MasterDataService(db).list_records(
        resource,
        tenant_id=context.tenant_id,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/shared/{resource}/{public_id}",
    response_model=MasterDataRecord,
    summary="Get a shared reference",
)
async def get_shared_catalog_record(
    resource: str,
    public_id: UUID,
    context: MasterDataContext,
    db: DatabaseSession,
) -> MasterDataRecord:
    return await MasterDataService(db).get_record(
        resource,
        public_id,
        tenant_id=context.tenant_id,
    )


@router.get(
    "/{resource}",
    response_model=MasterDataPage,
    summary="List tenant master records",
    description="Lists active records scoped to the authenticated tenant.",
)
async def list_tenant_master_records(
    resource: str,
    context: MasterDataContext,
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[
        str | None,
        Query(max_length=256, description="Opaque cursor from the previous page."),
    ] = None,
) -> MasterDataPage:
    return await MasterDataService(db).list_records(
        resource,
        tenant_id=context.tenant_id,
        limit=limit,
        cursor=cursor,
    )


@router.post(
    "/{resource}",
    response_model=MasterDataRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant master record",
)
async def create_tenant_master_record(
    resource: str,
    payload: MasterDataWriteRequest,
    context: MasterDataContext,
    db: DatabaseSession,
) -> MasterDataRecord:
    return await MasterDataService(db).create_record(
        resource,
        payload.values,
        tenant_id=context.tenant_id,
        actor_id=context.user.id,
    )


@router.get(
    "/{resource}/{public_id}",
    response_model=MasterDataRecord,
    summary="Get a tenant master record",
)
async def get_tenant_master_record(
    resource: str,
    public_id: UUID,
    context: MasterDataContext,
    db: DatabaseSession,
) -> MasterDataRecord:
    return await MasterDataService(db).get_record(
        resource,
        public_id,
        tenant_id=context.tenant_id,
    )


@router.patch(
    "/{resource}/{public_id}",
    response_model=MasterDataRecord,
    summary="Update a tenant master record",
)
async def update_tenant_master_record(
    resource: str,
    public_id: UUID,
    payload: MasterDataWriteRequest,
    context: MasterDataContext,
    db: DatabaseSession,
) -> MasterDataRecord:
    return await MasterDataService(db).update_record(
        resource,
        public_id,
        payload.values,
        tenant_id=context.tenant_id,
        actor_id=context.user.id,
    )


@router.delete(
    "/{resource}/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a tenant master record",
)
async def delete_tenant_master_record(
    resource: str,
    public_id: UUID,
    context: MasterDataContext,
    db: DatabaseSession,
) -> Response:
    await MasterDataService(db).delete_record(
        resource,
        public_id,
        tenant_id=context.tenant_id,
        actor_id=context.user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
