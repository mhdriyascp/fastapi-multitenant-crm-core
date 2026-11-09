from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.core.enums import MFAMethodType
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserMFAMethod(Base):
    """Stores multi-factor authentication configurations."""

    __tablename__ = "user_mfa_methods"

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
        doc="Target user foreign key",
    )

    method_type: Mapped[MFAMethodType] = mapped_column(
        SQLEnum(MFAMethodType, native_enum=False, length=30),
        nullable=False,
        doc="TOTP, WebAuthn",
    )

    secret_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="AES-256 encrypted TOTP secret key",
    )

    credential_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="WebAuthn credential metadata (public key, counter, transport)",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Verification status (True once first code is successfully confirmed)",
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Designates primary MFA method",
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="mfa_methods",
    )
