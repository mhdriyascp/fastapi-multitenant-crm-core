from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.core.enums import UserStatus

# 1. Correct import from app.models.base
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.identity_master import (
        UserCredential,
        UserDevice,
        UserPreference,
        UserProfile,
    )
    from app.models.tenant_membership import TenantMembership
    from app.models.user_mfa_method import UserMFAMethod
    from app.models.user_session import UserSession


class User(Base):
    """
    Global user account model.
    Represents an identity across the platform, independent of tenant associations.
    """

    __tablename__ = "users"

    # ---------------------------------------------------------------------------
    # Primary & Public Keys
    # ---------------------------------------------------------------------------
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid7,
        index=True,
        doc="Internal primary key (UUIDv7, time-ordered)",
    )

    public_id: Mapped[UUID] = mapped_column(
        unique=True,
        index=True,
        default=uuid4,
        nullable=False,
        doc="External public identifier (UUIDv4)",
    )

    # ---------------------------------------------------------------------------
    # Identity & Credentials
    # ---------------------------------------------------------------------------
    username: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
        doc="Optional unique handle / username",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Primary login email address",
    )

    # ---------------------------------------------------------------------------
    # Profile Information
    # ---------------------------------------------------------------------------
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="User's legal given name",
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="User's legal family name",
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        doc="E.164 international phone number format",
    )

    profile_image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="S3 or CDN storage URL for profile picture",
    )

    # ---------------------------------------------------------------------------
    # Lifecycle & Flags
    # ---------------------------------------------------------------------------
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="True once the email address verification flow is completed",
    )

    is_platform_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Global superadmin with access across all tenants",
    )

    # ---------------------------------------------------------------------------
    # Audit & Security Timestamps
    # ---------------------------------------------------------------------------
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        doc="Timestamp of the most recent successful login",
    )

    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        doc="Timestamp of the last password modification; used for token revocation",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Account registration timestamp",
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
        doc="Last account modification timestamp (NULL until first update)",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
        doc="Soft-delete timestamp; NULL if active",
    )

    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, native_enum=False, length=30),
        default=UserStatus.ACTIVE,
        nullable=False,
        index=True,
        doc="Account lifecycle state",
    )

    # ---------------------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------------------
    memberships: Mapped[list["TenantMembership"]] = relationship(
        "TenantMembership",
        foreign_keys="TenantMembership.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    mfa_methods: Mapped[list["UserMFAMethod"]] = relationship(
        "UserMFAMethod",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    credentials: Mapped[list["UserCredential"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    devices: Mapped[list["UserDevice"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    preferences: Mapped["UserPreference | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # ---------------------------------------------------------------------------
    # Convenience Properties
    # ---------------------------------------------------------------------------
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_active(self) -> bool:
        """Helper returning True if account is in active status and not soft-deleted."""
        return self.status == UserStatus.ACTIVE and self.deleted_at is None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
