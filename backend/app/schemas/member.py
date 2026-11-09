from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import MembershipStatus


class RoleSummary(BaseModel):
    id: UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class MemberUserSummary(BaseModel):
    id: UUID
    public_id: UUID
    email: EmailStr
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)


class MemberResponse(BaseModel):
    membership_id: UUID
    status: MembershipStatus
    joined_at: datetime | None
    user: MemberUserSummary
    roles: list[RoleSummary]

    model_config = ConfigDict(from_attributes=True)


class InviteMemberRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to invite")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role_codes: list[str] = Field(
        default=["member"],
        description="List of role codes to assign (e.g. ['member'], ['org_admin'])",
    )


class UpdateMemberRolesRequest(BaseModel):
    role_codes: list[str] = Field(..., min_length=1, description="New list of role codes")
