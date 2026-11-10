import asyncio
import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.api.dependencies.auth import AuthenticatedContext
from app.api.tenant.v1.endpoints.master_data import require_master_data_permission
from app.core.exceptions import (
    BusinessRuleViolationException,
    EntityNotFoundException,
)
from app.core.master_data_registry import MASTER_DATA_RESOURCES
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.master_data import PlatformMasterDataWriteRequest
from app.services.master_data_service import MasterDataService
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from pydantic import ValidationError
from scripts.seed.master_data import (
    CORE_SHARED_TABLES,
    CORE_TENANT_TABLES,
    CRM_MASTER_TABLES,
)
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.requests import Request

client = TestClient(app)


def _request(path: str, method: str, resource: str) -> Request:
    encoded_path = path.encode()
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "raw_path": encoded_path,
            "query_string": b"",
            "headers": [],
            "server": ("test", 80),
            "client": ("test", 1),
            "scheme": "http",
            "path_params": {"resource": resource},
        }
    )


def test_master_data_endpoints_are_exposed_in_their_versioned_schemas() -> None:
    tenant_paths = client.get("/openapi/v1.json").json()["paths"]
    platform_paths = client.get("/openapi/platform/v1.json").json()["paths"]

    assert {
        "/api/v1/master-data/{resource}",
        "/api/v1/master-data/{resource}/{public_id}",
        "/api/v1/master-data/shared/{resource}",
        "/api/v1/master-data/shared/{resource}/{public_id}",
    } <= tenant_paths.keys()
    assert {
        "/platform/v1/master-data/shared/{resource}",
        "/platform/v1/master-data/shared/{resource}/{public_id}",
    } <= platform_paths.keys()
    assert set(MASTER_DATA_RESOURCES) == (
        CORE_SHARED_TABLES | CORE_TENANT_TABLES | CRM_MASTER_TABLES
    )
    assert {"get", "post"} <= tenant_paths["/api/v1/master-data/{resource}"].keys()
    assert {
        "get",
        "patch",
        "delete",
    } <= tenant_paths["/api/v1/master-data/{resource}/{public_id}"].keys()
    assert {"get", "post"} <= platform_paths[
        "/platform/v1/master-data/shared/{resource}"
    ].keys()
    assert {
        "get",
        "patch",
        "delete",
    } <= platform_paths["/platform/v1/master-data/shared/{resource}/{public_id}"].keys()
    tenant_list_parameters = tenant_paths["/api/v1/master-data/{resource}"]["get"][
        "parameters"
    ]
    assert {parameter["name"] for parameter in tenant_list_parameters} >= {
        "cursor",
        "limit",
    }
    assert "offset" not in {parameter["name"] for parameter in tenant_list_parameters}


def test_tenant_permission_is_resource_specific_and_shared_writes_are_blocked() -> None:
    permission = "crm.account_type.read"
    context = AuthenticatedContext(
        user=SimpleNamespace(id=uuid4(), is_platform_admin=False),
        tenant_id=uuid4(),
        permissions={permission},
    )

    authorized = asyncio.run(
        require_master_data_permission(
            _request("/api/v1/master-data/account_types", "GET", "account_types"),
            context,
        )
    )
    assert authorized is context

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            require_master_data_permission(
                _request(
                    "/api/v1/master-data/shared/countries",
                    "POST",
                    "countries",
                ),
                context,
            )
        )
    assert error.value.status_code == 405


def test_platform_write_requests_require_a_reason() -> None:
    with pytest.raises(ValidationError):
        PlatformMasterDataWriteRequest(values={"code": "USD"})

    with pytest.raises(BusinessRuleViolationException):
        MasterDataService._audit_reason(
            MASTER_DATA_RESOURCES["currencies"],
            "        ",
        )

    assert (
        MasterDataService._audit_reason(
            MASTER_DATA_RESOURCES["currencies"],
            "Adding a currency",
        )
        == "Adding a currency"
    )


def test_create_validation_requires_non_nullable_fields() -> None:
    with pytest.raises(BusinessRuleViolationException, match="Missing required"):
        MasterDataService._validate_values(
            MASTER_DATA_RESOURCES["currencies"],
            {},
            creating=True,
        )


def test_resource_fields_are_explicit_and_exclude_internal_columns() -> None:
    internal_fields = {
        "id",
        "public_id",
        "tenant_id",
        "created_at",
        "created_by_id",
        "updated_at",
        "updated_by_id",
        "deleted_at",
        "deleted_by_id",
    }

    for resource in MASTER_DATA_RESOURCES.values():
        column_names = set(resource.model.__table__.columns.keys())
        assert resource.fields
        assert resource.fields <= column_names
        assert resource.fields.isdisjoint(internal_fields)

    for field in (
        "id",
        "public_id",
        "tenant_id",
        "created_by_id",
        "deleted_at",
    ):
        with pytest.raises(BusinessRuleViolationException, match="Unsupported fields"):
            MasterDataService._validate_values(
                MASTER_DATA_RESOURCES["organizations"],
                {field: str(uuid4())},
                creating=False,
            )


def test_cursor_encoding_round_trips_and_rejects_malformed_values() -> None:
    created_at = datetime(2026, 11, 10, 10, 30, tzinfo=UTC)
    public_id = uuid4()
    cursor = MasterDataService._encode_cursor(created_at, public_id)

    assert MasterDataService._decode_cursor(cursor) == (created_at, public_id)

    with pytest.raises(BusinessRuleViolationException, match="Invalid pagination"):
        MasterDataService._decode_cursor("not-a-valid-cursor")


@pytest.mark.asyncio
async def test_master_data_database_isolation_lifecycle_and_cursor_pagination() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run the database integration test.")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must target a database with 'test' in its name.")

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            outer_transaction = await connection.begin()
            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            ) as session:
                try:
                    actor = User(
                        email=f"master-data-test-{uuid4()}@example.com",
                        first_name="Master",
                        last_name="Data Test",
                    )
                    tenant_a = Tenant(
                        name="Master Data Test A",
                        slug=f"master-data-test-a-{uuid4()}",
                    )
                    tenant_b = Tenant(
                        name="Master Data Test B",
                        slug=f"master-data-test-b-{uuid4()}",
                    )
                    session.add_all([actor, tenant_a, tenant_b])
                    await session.flush()

                    service = MasterDataService(session)
                    organization_a = await service.create_record(
                        "organizations",
                        {"code": "ORG-A", "name": "Organization A"},
                        tenant_id=tenant_a.id,
                        actor_id=actor.id,
                    )
                    organization_a_second = await service.create_record(
                        "organizations",
                        {"code": "ORG-A2", "name": "Organization A2"},
                        tenant_id=tenant_a.id,
                        actor_id=actor.id,
                    )
                    organization_b = await service.create_record(
                        "organizations",
                        {"code": "ORG-B", "name": "Organization B"},
                        tenant_id=tenant_b.id,
                        actor_id=actor.id,
                    )

                    first_page = await service.list_records(
                        "organizations",
                        tenant_id=tenant_a.id,
                        limit=1,
                        cursor=None,
                    )
                    assert len(first_page.items) == 1
                    assert first_page.next_cursor is not None
                    second_page = await service.list_records(
                        "organizations",
                        tenant_id=tenant_a.id,
                        limit=1,
                        cursor=first_page.next_cursor,
                    )
                    assert [item.public_id for item in second_page.items] == [
                        (
                            {organization_a.public_id, organization_a_second.public_id}
                            - {first_page.items[0].public_id}
                        ).pop()
                    ]
                    assert second_page.next_cursor is None
                    with pytest.raises(EntityNotFoundException):
                        await service.get_record(
                            "organizations",
                            organization_b.public_id,
                            tenant_id=tenant_a.id,
                        )

                    with pytest.raises(EntityNotFoundException):
                        await service.create_record(
                            "branches",
                            {
                                "organization_id": str(organization_b.public_id),
                                "code": "BR-A",
                                "name": "Cross-tenant Branch",
                            },
                            tenant_id=tenant_a.id,
                            actor_id=actor.id,
                        )
                    with pytest.raises(BusinessRuleViolationException):
                        await service.update_record(
                            "organizations",
                            organization_a.public_id,
                            {"tenant_id": str(tenant_b.id)},
                            tenant_id=tenant_a.id,
                            actor_id=actor.id,
                        )

                    updated = await service.update_record(
                        "organizations",
                        organization_a.public_id,
                        {"name": "Updated Organization A"},
                        tenant_id=tenant_a.id,
                        actor_id=actor.id,
                    )
                    assert updated.data["name"] == "Updated Organization A"
                    await service.delete_record(
                        "organizations",
                        organization_a.public_id,
                        tenant_id=tenant_a.id,
                        actor_id=actor.id,
                    )
                    with pytest.raises(EntityNotFoundException):
                        await service.get_record(
                            "organizations",
                            organization_a.public_id,
                            tenant_id=tenant_a.id,
                        )
                    remaining = await service.list_records(
                        "organizations",
                        tenant_id=tenant_a.id,
                        limit=10,
                        cursor=None,
                    )
                    assert [item.public_id for item in remaining.items] == [
                        organization_a_second.public_id
                    ]
                finally:
                    await session.rollback()
            await outer_transaction.rollback()
    finally:
        await engine.dispose()
