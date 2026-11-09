import logging
from uuid import UUID

from app.core.config import settings
from app.core.email import EmailService
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logger = logging.getLogger("enterprise_crm.worker")

# Dedicated async engine for background worker
worker_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
worker_session_maker = async_sessionmaker(worker_engine, expire_on_commit=False)

async def startup(ctx: dict) -> None:
    logger.info("ARQ Email Worker Process initialized and listening on Redis queue...")


async def shutdown(ctx: dict) -> None:
    logger.info("ARQ Email Worker Process shutting down...")
    await worker_engine.dispose()


async def process_outbox_email(ctx: dict, outbox_id_str: str) -> None:
    """Consumes job from Redis queue and dispatches the outbox email."""
    outbox_id = UUID(outbox_id_str)
    async with worker_session_maker() as db:
        await EmailService.dispatch_outbox_record(db=db, outbox_id=outbox_id)


class WorkerSettings:
    """ARQ Worker configuration."""
    functions = [process_outbox_email]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 60
