from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class UserSession(Base):
    """Tracks authenticated user sessions and refresh tokens."""

    __tablename__ = "user_sessions"

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

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Authenticated user",
    )

    tenant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Active organization workspace during this session",
    )

    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Cryptographic hash of the issued refresh token",
    )

    ip_address: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
        doc="Client IPv4 or IPv6 address",
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Client browser and operating system details",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Session expiration timestamp",
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
        doc="Revocation timestamp; NULL if active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Session creation timestamp",
    )

    # ---------------------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------------------
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
    )

    tenant: Mapped["Tenant | None"] = relationship("Tenant")

    @property
    def is_active(self) -> bool:
        """Determines if the session is currently valid and unexpired."""
        return self.revoked_at is None and self.expires_at > datetime.now(UTC)
