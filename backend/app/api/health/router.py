import asyncio

from aiosmtplib import SMTP
from aiosmtplib.errors import SMTPException
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database.session import engine
from app.core.redis import get_redis_client

router = APIRouter()


class ServiceStatus(BaseModel):
    status: str
    details: str | None = None


class HealthResponse(BaseModel):
    status: str
    environment: str
    services: dict[str, ServiceStatus]


async def _check_postgres() -> ServiceStatus:
    try:
        async with asyncio.timeout(3):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return ServiceStatus(status="healthy")
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        return ServiceStatus(status="unhealthy", details=str(exc))


async def _check_redis() -> ServiceStatus:
    try:
        redis = get_redis_client()
        pong = await asyncio.wait_for(redis.ping(), timeout=3)
        return ServiceStatus(
            status="healthy" if pong is True else "unhealthy",
            details=(
                None if pong is True else "Redis ping returned an unexpected response."
            ),
        )
    except Exception as exc:
        return ServiceStatus(status="unhealthy", details=str(exc))


async def _check_smtp() -> ServiceStatus:
    if bool(settings.SMTP_USER) != bool(settings.SMTP_PASSWORD):
        return ServiceStatus(
            status="unhealthy",
            details="SMTP username and password must be configured together.",
        )

    try:
        async with SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_TLS,
            timeout=3,
        ) as smtp:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        return ServiceStatus(status="healthy")
    except (OSError, TimeoutError, SMTPException, ValueError) as exc:
        return ServiceStatus(status="unhealthy", details=str(exc))


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": HealthResponse,
            "description": "One or more dependencies are unavailable.",
        }
    },
    tags=["System"],
    summary="Check readiness of PostgreSQL, Redis, and SMTP",
    description=(
        "Checks database, cache, and SMTP connectivity. Returns 200 when all "
        "dependencies are ready, or 503 when one or more checks fail."
    ),
)
async def health_check(response: Response) -> HealthResponse:
    """Reports readiness of PostgreSQL, Redis, and configured SMTP."""
    postgres, redis, smtp = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_smtp(),
    )
    services = {"postgres": postgres, "redis": redis, "smtp": smtp}
    overall_healthy = all(service.status == "healthy" for service in services.values())
    if not overall_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        environment=settings.ENVIRONMENT,
        services=services,
    )
