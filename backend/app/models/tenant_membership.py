from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.core.enums import MembershipStatus
from app.models.base import AuditableLifecycleBase

if TYPE_CHECKING:
    from app.models.membership_role import MembershipRole
    from app.models.tenant import Tenant
    from app.models.user import User


class TenantMembership(AuditableLifecycleBase):
    """
    Connects global users to tenant workspaces.
    Tracks membership lifecycle, invitations, and role assignments.
    """

    __tablename__ = "tenant_memberships"

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),
    )
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid7,
        index=True,
        doc="Internal primary key (UUIDv7)",
    )
    
    public_id: Mapped[UUID] = mapped_column(
        unique=True,
        index=True,
        default=uuid4,
        nullable=False,
        doc="External public identifier (UUIDv4)",
    )

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Organization ID",
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID",
    )

    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        doc="Timestamp when the user accepted the invitation",
    )

    invited_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Admin user who issued the invitation",
    )
    
    status: Mapped[MembershipStatus] = mapped_column(
        SQLEnum(MembershipStatus, native_enum=False, length=30),
        default=MembershipStatus.INVITED,
        nullable=False,
        index=True,
        doc="Invited, active, suspended, removed",
    )

    # ---------------------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------------------
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="memberships",
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="memberships",
    )

    inviter: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[invited_by],
    )

    membership_roles: Mapped[list["MembershipRole"]] = relationship(
        "MembershipRole",
        back_populates="membership",
        cascade="all, delete-orphan",
    )
