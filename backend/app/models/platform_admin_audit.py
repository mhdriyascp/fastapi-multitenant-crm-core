from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class PlatformAdminAudit(Base):
    """Append-only audit event for privileged platform control-plane changes."""

    __tablename__ = "platform_admin_audits"
    __table_args__ = (
        Index(
            "ix_platform_admin_audits_resource", "resource_type", "resource_public_id"
        ),
        Index("ix_platform_admin_audits_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tenant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_public_id: Mapped[UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    actor: Mapped["User | None"] = relationship("User", foreign_keys=[actor_id])
    tenant: Mapped["Tenant | None"] = relationship("Tenant", foreign_keys=[tenant_id])
