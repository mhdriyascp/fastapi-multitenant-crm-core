from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from app.core.config import settings

# Global async redis connection pool
redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """Returns a singleton Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency for injecting Redis client."""
    client = get_redis_client()
    yield client
