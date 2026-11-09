"""Database dependencies for API endpoints."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_db_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an active async database session."""
    async for session in get_db_session():
        yield session
