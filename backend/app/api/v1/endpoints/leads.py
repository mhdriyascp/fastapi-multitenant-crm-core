from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies.lead_storage import LeadRepository, get_lead_repository
from app.api.dependencies.pagination import PaginationParams
from app.core.exceptions import BusinessRuleViolationException
from app.schemas.lead import LeadCreate, LeadResponse, LeadStatus, LeadUpdate

router = APIRouter()


@router.post(
    "/",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lead",
)
async def create_lead(
    payload: LeadCreate,
    repo: LeadRepository = Depends(get_lead_repository),
) -> Any:
    return repo.create(payload)


@router.get(
    "/",
    response_model=list[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="List all leads with pagination and filtering",
)
async def list_leads(
    pagination: PaginationParams = Depends(),
    status_filter: LeadStatus | None = Query(
        default=None,
        alias="status",
        description="Filter leads by lifecycle status",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
        description="Search term matching first name, last name, or email",
    ),
    repo: LeadRepository = Depends(get_lead_repository),
) -> Any:
    return repo.list(
        skip=pagination.skip,
        limit=pagination.limit,
        status=status_filter,
        search=search,
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a lead by ID",
)
async def get_lead(
    lead_id: UUID,
    repo: LeadRepository = Depends(get_lead_repository),
) -> Any:
    return repo.get_by_id(lead_id)


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a lead partially",
)
async def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    repo: LeadRepository = Depends(get_lead_repository),
) -> Any:
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise BusinessRuleViolationException("No valid fields provided for update.")

    return repo.update(lead_id, payload)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a lead",
)
async def delete_lead(
    lead_id: UUID,
    repo: LeadRepository = Depends(get_lead_repository),
) -> Response:
    repo.delete(lead_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
