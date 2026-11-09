import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import RequirePlatformPermission, get_current_context
from app.core.enums import TenantStatus, UserStatus
from app.core.security import TokenManager
from app.schemas.platform_admin import (
    SubscriptionPlanCreate,
    TenantSettingsUpdate,
    TenantSubscriptionUpdate,
)
from main import app

client = TestClient(app)


class _FakeResult:
    def __init__(self, values: list[str]):
        self.values = values

    def scalars(self):
        return self

    def all(self) -> list[str]:
        return self.values


class _FakeDatabase:
    def __init__(self, permissions: list[str], has_mfa: bool = True):
        self.permissions = permissions
        self.has_mfa = has_mfa

    async def scalar(self, _statement):
        return uuid4() if self.has_mfa else None

    async def execute(self, _statement) -> _FakeResult:
        return _FakeResult(self.permissions)


class _FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeContextDatabase:
    def __init__(self, user, membership):
        self.user = user
        self.membership = membership
        self.query_count = 0

    async def execute(self, _statement):
        self.query_count += 1
        value = self.user if self.query_count == 1 else self.membership
        return _FakeScalarResult(value)


def test_platform_docs_are_separate_from_tenant_versioned_schemas() -> None:
    response = client.get("/openapi/platform/v1.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert list(paths)[0] == "/health"
    assert "/auth/login" in paths
    assert "/platform/v1/iam/permissions" in paths
    assert "/platform/v1/operator-candidates" in paths
    assert "/platform/v1/tenants" in paths
    assert {
        "/platform/v1/iam/roles",
        "/platform/v1/iam/roles/{role_public_id}/permissions",
        "/platform/v1/operators",
        "/platform/v1/operators/{user_public_id}",
        "/platform/v1/operators/{user_public_id}/roles",
        "/platform/v1/tenants/{tenant_public_id}",
        "/platform/v1/tenants/{tenant_public_id}/settings",
        "/platform/v1/tenants/{tenant_public_id}/subscription",
        "/platform/v1/plans",
        "/platform/v1/plans/{plan_public_id}",
        "/platform/v1/audit-events",
    }.issubset(paths)
    assert not any(path.startswith("/api/v1/") for path in paths)
    assert not any(path.startswith("/api/v2/") for path in paths)
    assert "/iam/members/" not in paths
    assert "/platform/v1/tenants" not in client.get("/openapi/v1.json").json()["paths"]
    assert "/platform/v1/tenants" not in client.get("/openapi/v2.json").json()["paths"]
    assert client.get("/platform/v1/redoc").status_code == 200
    assert client.get("/scalar/platform/v1").status_code == 200


def test_platform_routes_reject_requests_without_authentication() -> None:
    response = client.get("/platform/v1/tenants")

    assert response.status_code == 401


def test_platform_operator_permission_requires_mfa_and_explicit_grant() -> None:
    user = SimpleNamespace(id=uuid4(), is_platform_admin=False)
    dependency = RequirePlatformPermission("platform.tenant.read")

    with pytest.raises(HTTPException) as mfa_error:
        asyncio.run(dependency(user, _FakeDatabase([], has_mfa=False)))
    assert mfa_error.value.status_code == 403

    context = asyncio.run(dependency(user, _FakeDatabase(["platform.tenant.read"])))
    assert context.permissions == {"platform.tenant.read"}

    with pytest.raises(HTTPException) as permission_error:
        asyncio.run(dependency(user, _FakeDatabase(["platform.plan.read"])))
    assert permission_error.value.status_code == 403


def test_platform_superadmin_also_requires_verified_mfa() -> None:
    user = SimpleNamespace(id=uuid4(), is_platform_admin=True)
    dependency = RequirePlatformPermission("platform.audit.read")

    with pytest.raises(HTTPException) as mfa_error:
        asyncio.run(dependency(user, _FakeDatabase([], has_mfa=False)))
    assert mfa_error.value.status_code == 403

    context = asyncio.run(dependency(user, _FakeDatabase([], has_mfa=True)))
    assert context.permissions == {"*"}


def test_suspended_tenant_removes_tenant_permissions_but_keeps_context(
    monkeypatch,
) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        status=UserStatus.ACTIVE,
        deleted_at=None,
        is_platform_admin=False,
    )
    tenant_id = uuid4()
    membership = SimpleNamespace(
        tenant=SimpleNamespace(status=TenantStatus.SUSPENDED, deleted_at=None),
        membership_roles=[],
    )
    monkeypatch.setattr(
        TokenManager,
        "decode_access_token",
        lambda _token: {"sub": str(user.id), "tid": str(tenant_id)},
    )

    context = asyncio.run(
        get_current_context(
            SimpleNamespace(credentials="test-token"),
            _FakeContextDatabase(user, membership),
        )
    )

    assert context.tenant_id == tenant_id
    assert context.permissions == set()


def test_tenant_settings_reject_unrecognized_fields() -> None:
    with pytest.raises(ValidationError):
        TenantSettingsUpdate.model_validate(
            {"reason": "Brand update", "smtp_password": "must-not-be-accepted"}
        )


def test_plan_entitlements_are_allowlisted_and_typed() -> None:
    with pytest.raises(ValidationError):
        SubscriptionPlanCreate.model_validate(
            {
                "code": "enterprise",
                "name": "Enterprise",
                "reason": "Initial plan setup",
                "entitlements": {"unrestricted_admin": True},
            }
        )

    with pytest.raises(ValidationError):
        SubscriptionPlanCreate.model_validate(
            {
                "code": "enterprise",
                "name": "Enterprise",
                "reason": "Initial plan setup",
                "entitlements": {"max_users": True},
            }
        )


def test_subscription_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        TenantSubscriptionUpdate.model_validate(
            {
                "plan_public_id": "0022e5e3-7d83-44a4-87d7-14f64155c4f6",
                "starts_at": "2026-11-10T09:00:00",
                "reason": "Plan assignment",
            }
        )
