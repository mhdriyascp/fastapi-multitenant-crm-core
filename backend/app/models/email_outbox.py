from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid_utils import uuid7

from app.core.enums import EmailOutboxStatus
from app.models.base import Base


class EmailOutbox(Base):
    """
    Transactional Outbox for all outbound system and tenant emails.
    Guarantees at-least-once delivery, auditability, and atomic DB operations.
    """

    __tablename__ = "email_outbox"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        index=True,
        doc="Internal identifier (UUIDv7, time-ordered)",
    )

    # Optional tenant context (NULL for global identity emails like password reset & OTP)
    tenant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Associated organization workspace",
    )

    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Recipient email address",
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Rendered email subject line",
    )

    template_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Jinja2 template filename (e.g. password_reset.html)",
    )

    template_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Variables required to render the email template",
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of dispatch attempts",
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum retry attempts before permanently marking as FAILED",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Latest dispatch error or exception trace",
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of successful delivery via SMTP",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    
    # Delivery status & retry tracking
    status: Mapped[str] = mapped_column(
        String(30),
        default=EmailOutboxStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Optimized index for worker polling of pending/stalled messages
    __table_args__ = (
        Index("ix_email_outbox_status_created", "status", "created_at"),
    )
