from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import redis.asyncio as aioredis
from app.api.auth.router import router as auth_router
from app.api.v1.router import api_router as api_v1_router
from app.core.config import settings
from app.core.database.session import engine
from app.core.exception_handlers import register_exception_handlers
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Convert SQLAlchemy asyncpg URL to raw PostgreSQL DSN for direct ping
RAW_POSTGRES_DSN = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


# ---------------------------------------------------------------------------
# Application Lifecycle (Lifespan Context Manager)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and graceful shutdown lifecycle events."""
    print("🚀 Initializing CRM Backend Services...")
    yield
    print("🛑 Shutting down CRM Backend Services...")
    # Cleanly dispose of SQLAlchemy connection pool
    await engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI Application Factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Register Centralized Exception Handlers
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# CORS Middleware Configuration
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# CORS Middleware Configuration (Dynamic from .env)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------
# 1. Version-Agnostic Authentication & Identity Gateway (/auth/*)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# 2. Versioned Domain Business APIs (/api/v1/*)
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------
class ServiceStatus(BaseModel):
    status: str
    details: str | None = None


class HealthResponse(BaseModel):
    status: str
    environment: str
    services: dict[str, ServiceStatus]


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
)
async def health_check() -> Any:
    """Verifies that the API server, database, and cache are operational."""
    services: dict[str, ServiceStatus] = {}

    # 1. Verify PostgreSQL Connectivity
    try:
        conn = await asyncpg.connect(RAW_POSTGRES_DSN, timeout=3.0)
        val = await conn.fetchval("SELECT 1")
        await conn.close()
        services["postgres"] = ServiceStatus(
            status="healthy" if val == 1 else "unhealthy"
        )
    except Exception as exc:
        services["postgres"] = ServiceStatus(status="unhealthy", details=str(exc))

    # 2. Verify Redis Connectivity
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        pong = await redis_client.ping()
        await redis_client.aclose()
        services["redis"] = ServiceStatus(
            status="healthy" if pong is True else "unhealthy"
        )
    except Exception as exc:
        services["redis"] = ServiceStatus(status="unhealthy", details=str(exc))

    overall_healthy = all(s.status == "healthy" for s in services.values())
    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        environment=settings.ENVIRONMENT,
        services=services,
    )
