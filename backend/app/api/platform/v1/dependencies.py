"""Dependencies shared by platform API endpoint modules."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.services.platform_admin_service import PlatformAdminService


def get_platform_admin_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformAdminService:
    return PlatformAdminService(PlatformAdminRepository(db))
