import app.models  # noqa: F401
from app.models.base import Base


def test_requested_identity_access_tables_are_registered() -> None:
    expected_tables = {
        "users",
        "user_profiles",
        "user_credentials",
        "roles",
        "permissions",
        "role_permissions",
        "membership_roles",
        "platform_user_roles",
        "user_sessions",
        "user_devices",
        "user_preferences",
        "teams",
        "team_members",
    }

    assert expected_tables <= set(Base.metadata.tables)


def test_password_hash_is_stored_in_user_credentials_not_users() -> None:
    assert "hashed_password" not in Base.metadata.tables["users"].c
    credentials = Base.metadata.tables["user_credentials"]
    assert "password_hash" in credentials.c
    assert "user_id" in credentials.c
    assert any(
        constraint.name == "uq_user_credential_type"
        for constraint in credentials.constraints
    )


def test_team_membership_requires_matching_tenant_team_and_user_membership() -> None:
    team_members = Base.metadata.tables["team_members"]
    composite_targets = {
        tuple(element.target_fullname for element in constraint.elements)
        for constraint in team_members.foreign_key_constraints
        if len(constraint.elements) == 2
    }

    assert ("teams.tenant_id", "teams.id") in composite_targets
    assert (
        "tenant_memberships.tenant_id",
        "tenant_memberships.user_id",
    ) in composite_targets
    assert any(
        index.name == "uq_team_members_team_user_active"
        and index.unique
        for index in team_members.indexes
    )
