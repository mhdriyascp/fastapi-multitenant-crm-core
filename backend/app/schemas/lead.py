from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# 1. Domain Enumeration
# ---------------------------------------------------------------------------
class LeadStatus(str, Enum):
    """Represents the finite state machine for a Lead's lifecycle."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"


# ---------------------------------------------------------------------------
# 2. Base Schema (Shared attributes)
# ---------------------------------------------------------------------------
class LeadBase(BaseModel):
    """Shared properties across all Lead schemas."""
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Lead's given name",
        examples=["Sarah"],
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Lead's family name",
        examples=["Connor"],
    )
    email: EmailStr = Field(
        ...,
        description="Primary business email address",
        examples=["sarah.connor@cyberdyne.com"],
    )
    company: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Associated organization name",
        examples=["Cyberdyne Systems"],
    )
    annual_revenue: float | None = Field(
        default=None,
        ge=0,
        description="Estimated annual revenue in USD; must be non-negative",
        examples=[500000.0],
    )


# ---------------------------------------------------------------------------
# 3. Create Schema (Inbound HTTP POST payload)
# ---------------------------------------------------------------------------
class LeadCreate(LeadBase):
    """Schema for validating lead creation requests."""
    status: LeadStatus = Field(
        default=LeadStatus.NEW,
        description="Initial lifecycle status of the lead",
    )


# ---------------------------------------------------------------------------
# 4. Update Schema (Inbound HTTP PATCH/PUT payload)
# ---------------------------------------------------------------------------
class LeadUpdate(BaseModel):
    """Schema for partial updates (all fields optional)."""
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = None
    company: str | None = Field(default=None, min_length=1, max_length=100)
    annual_revenue: float | None = Field(default=None, ge=0)
    status: LeadStatus | None = None


# ---------------------------------------------------------------------------
# 5. Response Schema (Outbound serialization to client)
# ---------------------------------------------------------------------------
class LeadResponse(LeadBase):
    """Schema for returning a Lead entity over HTTP."""
    id: UUID
    status: LeadStatus
    created_at: datetime
    updated_at: datetime

    # Pydantic v2 configuration to read from SQLAlchemy ORM entities
    model_config = ConfigDict(from_attributes=True)
