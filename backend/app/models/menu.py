"""Global application navigation menus and their RBAC requirements."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.permission import Permission


class Menu(Base):
    """A globally configured navigation item."""

    __tablename__ = "menus"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True,
        index=True,
        default=uuid4,
        nullable=False,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("menus.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
    )

    parent: Mapped["Menu | None"] = relationship(
        "Menu",
        remote_side="Menu.id",
        back_populates="children",
    )
    children: Mapped[list["Menu"]] = relationship(
        "Menu",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="Menu.sort_order",
    )
    menu_permissions: Mapped[list["MenuPermission"]] = relationship(
        "MenuPermission",
        back_populates="menu",
        cascade="all, delete-orphan",
    )


class MenuPermission(Base):
    """A permission that makes a menu item visible to its holder."""

    __tablename__ = "menu_permissions"
    __table_args__ = (
        UniqueConstraint(
            "menu_id",
            "permission_id",
            name="uq_menu_permissions_menu_permission",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    menu_id: Mapped[UUID] = mapped_column(
        ForeignKey("menus.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    menu: Mapped[Menu] = relationship("Menu", back_populates="menu_permissions")
    permission: Mapped["Permission"] = relationship(
        "Permission",
        back_populates="menu_permissions",
    )
