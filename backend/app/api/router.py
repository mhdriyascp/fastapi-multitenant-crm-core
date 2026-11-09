"""Top-level API router assembly."""

from fastapi import APIRouter

from app.api.auth.router import router as auth_router
from app.api.health.router import router as health_router
from app.api.platform.v1.router import router as platform_router
from app.api.tenant.v1.router import api_router as api_v1_router
from app.api.tenant.v2.router import api_router as api_v2_router
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(platform_router)
api_router.include_router(api_v1_router, prefix=settings.API_V1_STR)
api_router.include_router(api_v2_router, prefix=settings.API_V2_STR)
api_router.include_router(health_router)
