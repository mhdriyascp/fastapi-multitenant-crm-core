from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import AuditableLifecycleBase

if TYPE_CHECKING:
    from app.models.membership_role import MembershipRole
    from app.models.role_permission import RolePermission
    from app.models.tenant import Tenant
    from app.models.user import User


class Role(AuditableLifecycleBase):
    """
    Stores predefined global system roles and organization-specific custom roles.
    Inherits id (UUID7), public_id (UUID4), audit timestamps, and soft-delete fields.
    """

    __tablename__ = "roles"

    __table_args__ = (
        # 1. Uniqueness of role code within each specific tenant
        Index(
            "uq_roles_tenant_code",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=mapped_column("tenant_id").is_not(None),
        ),
        # 2. Uniqueness of role code across global system roles (where tenant_id IS NULL)
        Index(
            "uq_roles_global_code",
            "code",
            unique=True,
            postgresql_where=mapped_column("tenant_id").is_(None),
        ),
    )
    
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

    tenant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="NULL for global platform roles; tenant ID for custom tenant roles",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Role human-readable name (e.g., 'Sales Executive', 'Accountant')",
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Role machine code (e.g., 'org_owner', 'sales_executive')",
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Role scope and responsibility description",
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Platform-defined role that cannot be deleted or modified by tenants",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Role availability flag",
    )

    # ---------------------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------------------
    tenant: Mapped["Tenant | None"] = relationship(
        "Tenant",
        back_populates="roles",
    )

    creator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="[Role.created_by_id]",
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )

    membership_roles: Mapped[list["MembershipRole"]] = relationship(
        "MembershipRole",
        back_populates="role",
        cascade="all, delete-orphan",
    )
