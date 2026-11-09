
# Base model definitions for SQLAlchemy ORM.
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid_utils.compat import uuid7

from app.core.enums import CommonStatus


# ---------------------------------------------------------------------------
# 1. Root Declarative Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Root declarative base for all SQLAlchemy models."""


# ---------------------------------------------------------------------------
# 2. Shared Auditable Lifecycle Base (for models that reuse audit columns)
# ---------------------------------------------------------------------------
class AuditableLifecycleBase(Base):
    """
    Abstract base entity providing:
    - created_at, created_by_id
    - updated_at, updated_by_id (default NULL)
    - deleted_at, deleted_by_id (soft-delete),status
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
    )

    updated_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
        doc="User who last modified the record (NULL if never modified)",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
    )

    deleted_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        default=None,
        nullable=True,
    )
    
    status: Mapped[CommonStatus] = mapped_column(
        SQLEnum(CommonStatus, native_enum=False, length=30),
        default=CommonStatus.ACTIVE,
        nullable=False,
        index=True,
        doc="Current status of the record (active, inactive)",
    )


    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
