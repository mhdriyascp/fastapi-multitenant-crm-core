from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.tenant_membership import TenantMembership
    from app.models.user import User


class MembershipRole(Base):
    """Assigns one or multiple roles to a tenant membership."""

    __tablename__ = "membership_roles"

    __table_args__ = (
        UniqueConstraint("membership_id", "role_id", name="uq_membership_role"),
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

    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant membership foreign key",
    )

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Assigned role foreign key",
    )

    assigned_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Administrator who assigned this role",
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Timestamp when role was assigned",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Creation timestamp",
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
        doc="Last update timestamp (NULL until updated)",
    )

    # ---------------------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------------------
    membership: Mapped["TenantMembership"] = relationship(
        "TenantMembership",
        back_populates="membership_roles",
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="membership_roles",
    )

    assigner: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_by],
    )
