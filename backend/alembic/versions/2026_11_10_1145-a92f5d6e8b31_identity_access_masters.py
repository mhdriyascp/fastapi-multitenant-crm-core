"""normalize user credentials and add identity access master tables

Revision ID: a92f5d6e8b31
Revises: 7f2c9e6d4a81
Create Date: 2026-11-10 11:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a92f5d6e8b31"
down_revision: str | Sequence[str] | None = "7f2c9e6d4a81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_name", sa.String(length=100), nullable=True),
        sa.Column("pronouns", sa.String(length=50), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("locale", sa.String(length=35), nullable=True),
        sa.Column("timezone", sa.String(length=100), nullable=True),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_profiles_public_id", "user_profiles", ["public_id"], unique=True
    )
    op.create_index(
        "ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True
    )

    op.create_table(
        "user_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("credential_type", sa.String(length=30), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "credential_type <> 'password' OR password_hash IS NOT NULL",
            name="ck_user_password_credential_hash",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "credential_type", name="uq_user_credential_type"
        ),
    )
    op.create_index(
        "ix_user_credentials_public_id", "user_credentials", ["public_id"], unique=True
    )
    op.create_index(
        "ix_user_credentials_user_id", "user_credentials", ["user_id"], unique=False
    )

    op.create_table(
        "user_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("device_type", sa.String(length=50), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("fingerprint_hash", sa.String(length=128), nullable=True),
        sa.Column("is_trusted", sa.Boolean(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_devices_public_id", "user_devices", ["public_id"], unique=True
    )
    op.create_index(
        "ix_user_devices_user_id", "user_devices", ["user_id"], unique=False
    )
    op.create_index(
        "uq_user_devices_user_fingerprint_active",
        "user_devices",
        ["user_id", "fingerprint_hash"],
        unique=True,
        postgresql_where=sa.text("fingerprint_hash IS NOT NULL AND revoked_at IS NULL"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_preferences_public_id", "user_preferences", ["public_id"], unique=True
    )
    op.create_index(
        "ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=True
    )

    op.create_unique_constraint("uq_teams_tenant_id_id", "teams", ["tenant_id", "id"])
    op.create_table(
        "team_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_id", sa.Uuid(), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "team_id"],
            ["teams.tenant_id", "teams.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["tenant_memberships.tenant_id", "tenant_memberships.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_team_members_public_id", "team_members", ["public_id"], unique=True
    )
    op.create_index(
        "ix_team_members_tenant_id", "team_members", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_team_members_user_id", "team_members", ["user_id"], unique=False
    )
    op.create_index(
        "ix_team_members_deleted_at", "team_members", ["deleted_at"], unique=False
    )
    op.create_index(
        "uq_team_members_team_user_active",
        "team_members",
        ["tenant_id", "team_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.execute(
        sa.text(
            "INSERT INTO user_credentials "
            "(id, public_id, user_id, credential_type, password_hash, created_at) "
            "SELECT id, gen_random_uuid(), id, 'password', hashed_password, "
            "CURRENT_TIMESTAMP FROM users WHERE hashed_password IS NOT NULL"
        )
    )
    op.drop_column("users", "hashed_password")


def downgrade() -> None:
    op.add_column(
        "users", sa.Column("hashed_password", sa.String(length=255), nullable=True)
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE users AS u "
            "SET hashed_password = c.password_hash "
            "FROM user_credentials AS c "
            "WHERE c.user_id = u.id AND c.credential_type = 'password'"
        )
    )

    op.drop_index("uq_team_members_team_user_active", table_name="team_members")
    op.drop_index("ix_team_members_deleted_at", table_name="team_members")
    op.drop_index("ix_team_members_user_id", table_name="team_members")
    op.drop_index("ix_team_members_tenant_id", table_name="team_members")
    op.drop_index("ix_team_members_public_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_constraint("uq_teams_tenant_id_id", "teams", type_="unique")

    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_index("ix_user_preferences_public_id", table_name="user_preferences")
    op.drop_table("user_preferences")
    op.drop_index("uq_user_devices_user_fingerprint_active", table_name="user_devices")
    op.drop_index("ix_user_devices_user_id", table_name="user_devices")
    op.drop_index("ix_user_devices_public_id", table_name="user_devices")
    op.drop_table("user_devices")
    op.drop_index("ix_user_credentials_user_id", table_name="user_credentials")
    op.drop_index("ix_user_credentials_public_id", table_name="user_credentials")
    op.drop_table("user_credentials")
    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_index("ix_user_profiles_public_id", table_name="user_profiles")
    op.drop_table("user_profiles")
