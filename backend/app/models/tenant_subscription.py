from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.subscription_plan import SubscriptionPlan
    from app.models.tenant import Tenant


class TenantSubscription(Base):
    """Current plan assignment for a tenant (billing is handled externally)."""

    __tablename__ = "tenant_subscriptions"
    __table_args__ = (
        Index("ix_tenant_subscriptions_tenant_active", "tenant_id", "status"),
    )

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
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(UTC)
    )

    tenant: Mapped["Tenant"] = relationship()
    plan: Mapped["SubscriptionPlan"] = relationship()
