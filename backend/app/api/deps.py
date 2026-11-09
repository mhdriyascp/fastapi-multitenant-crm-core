"""Compatibility exports for API dependencies.

Prefer imports from ``app.api.dependencies`` in new endpoint modules.
"""

from app.api.dependencies.auth import (
    AuthenticatedContext,
    PlatformAdminContext,
    RequirePermission,
    RequirePlatformPermission,
    get_current_context,
    get_current_platform_user,
    security_scheme,
)
from app.api.dependencies.database import get_db

__all__ = [
    "AuthenticatedContext",
    "PlatformAdminContext",
    "RequirePermission",
    "RequirePlatformPermission",
    "get_current_context",
    "get_current_platform_user",
    "get_db",
    "security_scheme",
]
