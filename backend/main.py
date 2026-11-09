import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.documentation import register_api_documentation
from app.api.router import api_router
from app.core.config import settings
from app.core.database.session import engine
from app.core.exception_handlers import register_exception_handlers

logger = logging.getLogger("enterprise_crm")


# ---------------------------------------------------------------------------
# Application Lifecycle (Lifespan Context Manager)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and graceful shutdown lifecycle events."""
    logger.info("Initializing CRM Backend Services...")
    yield
    logger.info("Shutting down CRM Backend Services...")
    # Cleanly dispose of SQLAlchemy connection pool
    await engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI Application Factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
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


app.include_router(api_router)
register_api_documentation(app)
