from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.master_data import Team
    from app.models.user import User


class UserProfile(Base):
    """Optional extended profile details for a global user account."""

    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    preferred_name: Mapped[str | None] = mapped_column(String(100))
    pronouns: Mapped[str | None] = mapped_column(String(50))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    locale: Mapped[str | None] = mapped_column(String(35))
    timezone: Mapped[str | None] = mapped_column(String(100))
    biography: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (Index("ix_user_profiles_user_id", "user_id", unique=True),)

    user: Mapped[User] = relationship(back_populates="profile")


class UserCredential(Base):
    """Password credential material, separated from the account record."""

    __tablename__ = "user_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "credential_type", name="uq_user_credential_type"),
        CheckConstraint(
            "credential_type <> 'password' OR password_hash IS NOT NULL",
            name="ck_user_password_credential_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credential_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="password"
    )
    password_hash: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(UTC)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="credentials")


class UserDevice(Base):
    """Known device metadata associated with a user; no raw fingerprint is stored."""

    __tablename__ = "user_devices"
    __table_args__ = (
        Index(
            "uq_user_devices_user_fingerprint_active",
            "user_id",
            "fingerprint_hash",
            unique=True,
            postgresql_where=text(
                "fingerprint_hash IS NOT NULL AND revoked_at IS NULL"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(120))
    device_type: Mapped[str | None] = mapped_column(String(50))
    platform: Mapped[str | None] = mapped_column(String(100))
    fingerprint_hash: Mapped[str | None] = mapped_column(String(128))
    is_trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(UTC)
    )

    user: Mapped[User] = relationship(back_populates="devices")


class UserPreference(Base):
    """Per-user application preferences, separate from tenant settings."""

    __tablename__ = "user_preferences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (Index("ix_user_preferences_user_id", "user_id", unique=True),)

    user: Mapped[User] = relationship(back_populates="preferences")


class TeamMember(Base):
    """A user's tenant membership in a tenant-owned team."""

    __tablename__ = "team_members"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["teams.tenant_id", "teams.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["tenant_memberships.tenant_id", "tenant_memberships.user_id"],
            ondelete="CASCADE",
        ),
        Index(
            "uq_team_members_team_user_active",
            "tenant_id",
            "team_id",
            "user_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_team_members_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=lambda: datetime.now(UTC)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    deleted_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    team: Mapped[Team] = relationship(back_populates="members")
    user: Mapped[User] = relationship(foreign_keys=[user_id])
