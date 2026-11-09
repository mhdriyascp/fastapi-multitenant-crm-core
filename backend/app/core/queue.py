from app.core.config import settings
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

arq_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Returns a singleton ARQ Redis connection pool."""
    global arq_pool
    if arq_pool is None:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
        arq_pool = await create_pool(redis_settings)
    return arq_pool
