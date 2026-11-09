from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.core.enums import RoleAuditAction
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.tenant_membership import TenantMembership
    from app.models.user import User


class RoleAssignmentAudit(Base):
    """Maintains the immutable history of role assignments and removals."""

    __tablename__ = "role_assignment_audits"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid7,
        index=True,
        doc="Internal identifier (UUIDv7)",
    )

    public_id: Mapped[UUID] = mapped_column(
        unique=True,
        index=True,
        default=uuid4,
        nullable=False,
        doc="External identifier (UUIDv4)",
    )

    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target tenant membership",
    )

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target role",
    )

    action: Mapped[RoleAuditAction] = mapped_column(
        SQLEnum(RoleAuditAction, native_enum=False, length=30),
        nullable=False,
        doc="Assigned, revoked",
    )

    performed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Administrator who performed the action",
    )

    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Action timestamp",
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Business reason for role change",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Creation timestamp",
    )

    # ---------------------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------------------
    membership: Mapped["TenantMembership"] = relationship("TenantMembership")
    role: Mapped["Role"] = relationship("Role")
    actor: Mapped["User | None"] = relationship("User", foreign_keys=[performed_by])
