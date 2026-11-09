from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthenticatedContext, RequirePermission
from app.api.dependencies.database import get_db
from app.schemas.member import (
    InviteMemberRequest,
    MemberResponse,
    RoleSummary,
    UpdateMemberRolesRequest,
)
from app.services.member_service import MemberService

router = APIRouter()


@router.get(
    "/",
    response_model=list[MemberResponse],
    summary="List workspace members",
)
async def list_workspace_members(
    context: AuthenticatedContext = Depends(RequirePermission("iam.membership.read")),
    db: AsyncSession = Depends(get_db),
) -> list[MemberResponse]:
    """Retrieve all members belonging to the caller's active tenant workspace."""
    service = MemberService(db)
    return await service.list_members(tenant_id=context.tenant_id)


@router.post(
    "/invite",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite or add a user to the workspace",
)
async def invite_workspace_member(
    payload: InviteMemberRequest,
    context: AuthenticatedContext = Depends(RequirePermission("iam.membership.create")),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    """Invite a user into the active workspace with assigned roles."""
    service = MemberService(db)
    return await service.invite_member(
        tenant_id=context.tenant_id,
        inviter_id=context.user.id,
        payload=payload,
    )


@router.delete(
    "/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from the workspace",
)
async def remove_workspace_member(
    membership_id: UUID,
    context: AuthenticatedContext = Depends(RequirePermission("iam.membership.delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke access for a workspace member."""
    service = MemberService(db)
    await service.remove_member(
        tenant_id=context.tenant_id,
        membership_id=membership_id,
        actor_id=context.user.id,
    )


@router.get(
    "/roles",
    response_model=list[RoleSummary],
    summary="List assignable workspace roles",
)
async def list_workspace_roles(
    context: AuthenticatedContext = Depends(RequirePermission("iam.role.read")),
    db: AsyncSession = Depends(get_db),
) -> list[RoleSummary]:
    """List roles that can be assigned to members in the caller's workspace."""
    service = MemberService(db)
    return await service.list_assignable_roles(tenant_id=context.tenant_id)


@router.patch(
    "/{membership_id}/roles",
    response_model=MemberResponse,
    summary="Update a member's assigned roles",
)
async def update_member_roles(
    membership_id: UUID,
    payload: UpdateMemberRolesRequest,
    context: AuthenticatedContext = Depends(
        RequirePermission("iam.role_assignment.assign")
    ),
    db: AsyncSession = Depends(get_db),
) -> MemberResponse:
    """Modify roles for a workspace member and record an audit trail."""
    service = MemberService(db)
    return await service.update_member_roles(
        tenant_id=context.tenant_id,
        membership_id=membership_id,
        actor_id=context.user.id,
        payload=payload,
    )
