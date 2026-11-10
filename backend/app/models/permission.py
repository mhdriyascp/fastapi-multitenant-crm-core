from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.menu import MenuPermission
    from app.models.role_permission import RolePermission


class Permission(Base):
    """
    Stores granular application permissions.
    Catalog table shared globally across all platform modules.
    """

    __tablename__ = "permissions"

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

    module: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Domain module (e.g. 'CRM', 'ERP', 'HR', 'SCM')",
    )

    resource: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Domain resource (e.g. 'Customer', 'Invoice', 'Employee')",
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Operation capability (e.g. 'Create', 'Read', 'Update', 'Delete', 'Approve')",
    )

    code: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
        doc="Canonical permission slug (e.g. 'iam.membership.read')",
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Explanation of the access this permission grants",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Permission status flag",
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
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )
    menu_permissions: Mapped[list["MenuPermission"]] = relationship(
        "MenuPermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )
