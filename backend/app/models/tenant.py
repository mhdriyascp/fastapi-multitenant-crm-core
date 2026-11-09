from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.core.enums import TenantStatus
from app.models.base import AuditableLifecycleBase

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.tenant_membership import TenantMembership


class Tenant(AuditableLifecycleBase):
    """
    Stores corporate workspace / organization details.
    Inherits id (UUID7), public_id (UUID4), audit timestamps, and soft-delete fields.
    """

    __tablename__ = "tenants"
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid7,
        index=True,
        doc="Internal primary key (UUIDv7)",
    )
    
    public_id: Mapped[UUID] = mapped_column(
        unique=True,
        index=True,
        default=uuid4,
        nullable=False,
        doc="External public identifier (UUIDv4)",
    )
    
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Legal or commercial name of the organization",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="URL identifier (e.g. 'acme-corp')",
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Registered corporate name",
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Primary billing/contact email for the organization",
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        doc="Organization contact phone number",
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Organization official website",
    )

    country_code: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        doc="ISO 3166-1 alpha-2 country code",
    )

    timezone: Mapped[str] = mapped_column(
        String(100),
        default="UTC",
        nullable=False,
        doc="Default operational timezone",
    )

    # Overriding the default string status with TenantStatus Enum
    status: Mapped[TenantStatus] = mapped_column(
        SQLEnum(TenantStatus, native_enum=False, length=30),
        default=TenantStatus.TRIAL,
        nullable=False,
        index=True,
        doc="Trial, active, suspended, cancelled",
    )

    # ---------------------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------------------
    memberships: Mapped[list["TenantMembership"]] = relationship(
        "TenantMembership",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
