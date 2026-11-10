"""create global navigation menus

Revision ID: 5a41c9d8b210
Revises: c31d4f7a8e52
Create Date: 2026-11-10 10:31:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5a41c9d8b210"
down_revision: str | Sequence[str] | None = "c31d4f7a8e52"
branch_labels: str | Sequence[str] | None = ("navigation",)
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "menus",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column(
            "sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["menus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menus_code", "menus", ["code"], unique=True)
    op.create_index("ix_menus_parent_id", "menus", ["parent_id"], unique=False)
    op.create_index("ix_menus_public_id", "menus", ["public_id"], unique=True)

    op.create_table(
        "menu_permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("menu_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["menu_id"], ["menus.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "menu_id",
            "permission_id",
            name="uq_menu_permissions_menu_permission",
        ),
    )
    op.create_index(
        "ix_menu_permissions_menu_id",
        "menu_permissions",
        ["menu_id"],
        unique=False,
    )
    op.create_index(
        "ix_menu_permissions_permission_id",
        "menu_permissions",
        ["permission_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_menu_permissions_permission_id", table_name="menu_permissions")
    op.drop_index("ix_menu_permissions_menu_id", table_name="menu_permissions")
    op.drop_table("menu_permissions")
    op.drop_index("ix_menus_public_id", table_name="menus")
    op.drop_index("ix_menus_parent_id", table_name="menus")
    op.drop_index("ix_menus_code", table_name="menus")
    op.drop_table("menus")
