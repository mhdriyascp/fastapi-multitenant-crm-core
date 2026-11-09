from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.user import User


class PlatformUserRole(Base):
    """Active platform-operator role assignment for a user."""

    __tablename__ = "platform_user_roles"
    __table_args__ = (
        Index(
            "uq_platform_user_role_active",
            "user_id",
            "role_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_platform_user_roles_user_active", "user_id", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True
    )
    deleted_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    role: Mapped["Role"] = relationship()
