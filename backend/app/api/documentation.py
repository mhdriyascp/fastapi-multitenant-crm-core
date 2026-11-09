"""Versioned OpenAPI, ReDoc, and Scalar documentation routes."""

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse
from scalar_fastapi import add_scalar_reference

from app.core.config import settings

router = APIRouter()


def _filtered_openapi_schema(
    app: FastAPI,
    title: str,
    include_path: Callable[[str], bool],
) -> dict[str, Any]:
    schema = deepcopy(app.openapi())
    schema["info"]["title"] = title
    paths = {
        path: operations
        for path, operations in schema["paths"].items()
        if include_path(path)
    }
    health_paths = ["/health"] if "/health" in paths else []
    schema["paths"] = {
        path: paths[path]
        for path in (
            *health_paths,
            *(path for path in paths if path not in health_paths),
        )
    }
    tags = [
        {"name": "System", "description": "Health and dependency readiness."},
        {"name": "Authentication", "description": "Shared authentication endpoints."},
    ]
    if any(path.startswith(f"{settings.API_V1_STR}/iam/") for path in paths):
        tags.append(
            {"name": "IAM - Members", "description": "Tenant IAM and RBAC endpoints."}
        )
    schema["tags"] = tags
    return schema


def _include_version_paths(path: str, prefix: str) -> bool:
    return (
        path == "/health"
        or path == prefix
        or path.startswith(("/auth/", f"{prefix}/"))
    )


@router.get("/openapi/v1.json", include_in_schema=False)
async def openapi_v1(request: Request) -> dict[str, Any]:
    return _filtered_openapi_schema(
        request.app,
        f"{settings.PROJECT_NAME} API v1",
        lambda path: _include_version_paths(path, settings.API_V1_STR),
    )


@router.get("/openapi/v2.json", include_in_schema=False)
async def openapi_v2(request: Request) -> dict[str, Any]:
    return _filtered_openapi_schema(
        request.app,
        f"{settings.PROJECT_NAME} API v2",
        lambda path: _include_version_paths(path, settings.API_V2_STR),
    )


@router.get("/openapi/platform/v1.json", include_in_schema=False)
async def openapi_platform_v1(request: Request) -> dict[str, Any]:
    schema = _filtered_openapi_schema(
        request.app,
        f"{settings.PROJECT_NAME} Platform Administration API v1",
        lambda path: path == "/health" or path.startswith(("/auth/", "/platform/v1/")),
    )
    schema["tags"] = [
        {"name": "System", "description": "Health and dependency readiness."},
        {"name": "Authentication", "description": "Shared authentication endpoints."},
        {
            "name": "Platform Administration",
            "description": "Restricted platform-wide control-plane operations.",
        },
    ]
    return schema


@router.get("/v1/redoc", include_in_schema=False)
async def redoc_v1() -> HTMLResponse:
    return get_redoc_html(
        openapi_url="/openapi/v1.json",
        title=f"{settings.PROJECT_NAME} API v1",
    )


@router.get("/v2/redoc", include_in_schema=False)
async def redoc_v2() -> HTMLResponse:
    return get_redoc_html(
        openapi_url="/openapi/v2.json",
        title=f"{settings.PROJECT_NAME} API v2",
    )


@router.get("/platform/v1/redoc", include_in_schema=False)
async def redoc_platform_v1() -> HTMLResponse:
    return get_redoc_html(
        openapi_url="/openapi/platform/v1.json",
        title=f"{settings.PROJECT_NAME} Platform Administration API v1",
    )


def register_api_documentation(app: FastAPI) -> None:
    """Mount documentation UIs and their version-filtered schemas."""
    app.include_router(router)
    add_scalar_reference(
        app,
        route="/scalar/v1",
        openapi_url="/openapi/v1.json",
        title=f"{settings.PROJECT_NAME} API v1",
    )
    add_scalar_reference(
        app,
        route="/scalar/v2",
        openapi_url="/openapi/v2.json",
        title=f"{settings.PROJECT_NAME} API v2",
    )
    add_scalar_reference(
        app,
        route="/scalar/platform/v1",
        openapi_url="/openapi/platform/v1.json",
        title=f"{settings.PROJECT_NAME} Platform Administration API v1",
    )
