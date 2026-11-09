from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from uuid_utils.compat import uuid7

from app.models.base import Base


class TenantSettings(Base):
    """Allowlisted runtime preferences managed for a tenant."""

    __tablename__ = "tenant_settings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(UTC)
    )
