"""add platform control plane tables

Revision ID: 1c7d91e52a4f
Revises: 8b29044d45d4
Create Date: 2026-11-10 09:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1c7d91e52a4f"
down_revision: Union[str, Sequence[str], None] = "8b29044d45d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column(
            "is_platform", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.alter_column("roles", "is_platform", server_default=None)

    op.create_table(
        "platform_user_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_user_roles_user_id", "platform_user_roles", ["user_id"]
    )
    op.create_index(
        "ix_platform_user_roles_role_id", "platform_user_roles", ["role_id"]
    )
    op.create_index(
        "ix_platform_user_roles_deleted_at", "platform_user_roles", ["deleted_at"]
    )
    op.create_index(
        "ix_platform_user_roles_user_active",
        "platform_user_roles",
        ["user_id", "deleted_at"],
    )
    op.create_index(
        "ix_platform_user_roles_public_id",
        "platform_user_roles",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        "uq_platform_user_role_active",
        "platform_user_roles",
        ["user_id", "role_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "platform_admin_audits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_public_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_admin_audits_actor_id", "platform_admin_audits", ["actor_id"]
    )
    op.create_index(
        "ix_platform_admin_audits_tenant_id", "platform_admin_audits", ["tenant_id"]
    )
    op.create_index(
        "ix_platform_admin_audits_resource",
        "platform_admin_audits",
        ["resource_type", "resource_public_id"],
    )
    op.create_index(
        "ix_platform_admin_audits_created_at",
        "platform_admin_audits",
        ["created_at"],
    )
    op.create_index(
        "ix_platform_admin_audits_public_id",
        "platform_admin_audits",
        ["public_id"],
        unique=True,
    )

    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "entitlements", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subscription_plans_code", "subscription_plans", ["code"], unique=True
    )
    op.create_index(
        "ix_subscription_plans_public_id",
        "subscription_plans",
        ["public_id"],
        unique=True,
    )

    op.create_table(
        "tenant_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_settings_tenant_id",
        "tenant_settings",
        ["tenant_id"],
        unique=True,
    )
    op.create_index(
        "ix_tenant_settings_public_id", "tenant_settings", ["public_id"], unique=True
    )

    op.create_table(
        "tenant_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_subscriptions_tenant_id",
        "tenant_subscriptions",
        ["tenant_id"],
        unique=True,
    )
    op.create_index(
        "ix_tenant_subscriptions_plan_id", "tenant_subscriptions", ["plan_id"]
    )
    op.create_index(
        "ix_tenant_subscriptions_public_id",
        "tenant_subscriptions",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        "ix_tenant_subscriptions_tenant_active",
        "tenant_subscriptions",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tenant_subscriptions_tenant_active", table_name="tenant_subscriptions"
    )
    op.drop_index(
        "ix_tenant_subscriptions_public_id", table_name="tenant_subscriptions"
    )
    op.drop_index("ix_tenant_subscriptions_plan_id", table_name="tenant_subscriptions")
    op.drop_index(
        "ix_tenant_subscriptions_tenant_id", table_name="tenant_subscriptions"
    )
    op.drop_table("tenant_subscriptions")

    op.drop_index("ix_tenant_settings_public_id", table_name="tenant_settings")
    op.drop_index("ix_tenant_settings_tenant_id", table_name="tenant_settings")
    op.drop_table("tenant_settings")

    op.drop_index("ix_subscription_plans_public_id", table_name="subscription_plans")
    op.drop_index("ix_subscription_plans_code", table_name="subscription_plans")
    op.drop_table("subscription_plans")

    op.drop_index(
        "ix_platform_admin_audits_public_id", table_name="platform_admin_audits"
    )
    op.drop_index(
        "ix_platform_admin_audits_created_at", table_name="platform_admin_audits"
    )
    op.drop_index(
        "ix_platform_admin_audits_resource", table_name="platform_admin_audits"
    )
    op.drop_index(
        "ix_platform_admin_audits_tenant_id", table_name="platform_admin_audits"
    )
    op.drop_index(
        "ix_platform_admin_audits_actor_id", table_name="platform_admin_audits"
    )
    op.drop_table("platform_admin_audits")

    op.drop_index("uq_platform_user_role_active", table_name="platform_user_roles")
    op.drop_index("ix_platform_user_roles_public_id", table_name="platform_user_roles")
    op.drop_index(
        "ix_platform_user_roles_user_active", table_name="platform_user_roles"
    )
    op.drop_index("ix_platform_user_roles_deleted_at", table_name="platform_user_roles")
    op.drop_index("ix_platform_user_roles_role_id", table_name="platform_user_roles")
    op.drop_index("ix_platform_user_roles_user_id", table_name="platform_user_roles")
    op.drop_table("platform_user_roles")

    op.drop_column("roles", "is_platform")
