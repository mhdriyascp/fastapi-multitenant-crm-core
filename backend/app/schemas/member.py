"""Pydantic schemas for tenant workspace member management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import MembershipStatus


class RoleSummary(BaseModel):
    """Summary of a system or custom role assigned to a workspace member."""

    id: UUID = Field(..., description="Internal role primary key")
    public_id: UUID | None = Field(default=None, description="External public identifier (UUIDv4)")
    code: str = Field(..., description="Machine-readable role code (e.g. 'org_admin')")
    name: str = Field(..., description="Human-readable role name (e.g. 'Organization Administrator')")

    model_config = ConfigDict(from_attributes=True)


class MemberUserSummary(BaseModel):
    """Public profile projection of a member user."""

    id: UUID = Field(..., description="Internal user ID")
    public_id: UUID = Field(..., description="External public identifier (UUIDv4)")
    email: EmailStr = Field(..., description="Member email address")
    first_name: str = Field(..., description="Given name")
    last_name: str = Field(..., description="Family name")

    model_config = ConfigDict(from_attributes=True)


class MemberResponse(BaseModel):
    """Envelope representation of a workspace tenant membership."""

    membership_id: UUID = Field(..., description="Internal membership primary key")
    public_id: UUID | None = Field(default=None, description="External public identifier (UUIDv4)")
    status: MembershipStatus = Field(..., description="Current membership lifecycle state")
    joined_at: datetime | None = Field(default=None, description="Timestamp of invitation acceptance")
    user: MemberUserSummary = Field(..., description="Associated user identity")
    roles: list[RoleSummary] = Field(default_factory=list, description="Roles granted to the member")

    model_config = ConfigDict(from_attributes=True)


class InviteMemberRequest(BaseModel):
    """Request payload for inviting or adding a user to a workspace."""

    email: EmailStr = Field(..., description="Email address to invite")
    first_name: str = Field(..., min_length=1, max_length=100, description="Legal given name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Legal family name")
    role_codes: list[str] = Field(
        default=["member"],
        description="List of role codes to assign (e.g. ['member'], ['org_admin'])",
    )


class UpdateMemberRolesRequest(BaseModel):
    """Request payload for updating member role assignments."""

    role_codes: list[str] = Field(
        ...,
        min_length=1,
        description="New replacement list of role codes to assign to the member",
    )
