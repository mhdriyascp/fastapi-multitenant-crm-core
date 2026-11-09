from datetime import UTC, datetime
from email.message import EmailMessage
from importlib import import_module
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.enums import EmailOutboxStatus
from app.core.queue import get_arq_pool
from app.models.email_outbox import EmailOutbox
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.exceptions import TemplateError
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("enterprise_crm.email")

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailService:
    """Enterprise transactional outbox and email renderer."""

    @classmethod
    def render_template(cls, template_name: str, context: dict[str, Any]) -> str:
        template = jinja_env.get_template(template_name)
        full_context = {
            "project_name": settings.PROJECT_NAME,
            "frontend_base_url": settings.FRONTEND_BASE_URL.rstrip("/"),
            **context,
        }
        return template.render(**full_context)

    # ---------------------------------------------------------------------------
    # Outbox Enqueue (Called in Web API Transactions)
    # ---------------------------------------------------------------------------
    @classmethod
    async def enqueue(
        cls,
        db: AsyncSession,
        recipient: str,
        subject: str,
        template_name: str,
        template_context: dict[str, Any],
        tenant_id: UUID | None = None,
    ) -> EmailOutbox:
        """
        Atomically records an email in PostgreSQL and pushes the outbox ID to ARQ.
        If the surrounding DB transaction rolls back, no email is ever sent.
        """
        outbox = EmailOutbox(
            tenant_id=tenant_id,
            recipient=recipient.strip(),
            subject=subject.strip(),
            template_name=template_name,
            template_context=template_context,
            status=EmailOutboxStatus.PENDING.value,
        )
        db.add(outbox)
        await db.flush()  # Ensures outbox.id (UUIDv7) is generated

        # Enqueue job to Redis
        try:
            pool = await get_arq_pool()
            await pool.enqueue_job("process_outbox_email", str(outbox.id))
        except RedisError as exc:
            # Row remains in PENDING; background retry will pick it up
            logger.warning(f"Failed to enqueue email job to Redis: {exc}")

        return outbox

    # ---------------------------------------------------------------------------
    # Worker Dispatcher (Executed in ARQ Background Process)
    # ---------------------------------------------------------------------------
    @classmethod
    async def dispatch_outbox_record(cls, db: AsyncSession, outbox_id: UUID) -> None:
        """Fetches outbox row, dispatches via SMTP, and records delivery status."""
        query = await db.execute(
            select(EmailOutbox).where(EmailOutbox.id == outbox_id).with_for_update()
        )
        outbox = query.scalar_one_or_none()
        if not outbox or outbox.status == EmailOutboxStatus.SENT.value:
            return

        outbox.attempts += 1
        outbox.status = EmailOutboxStatus.PROCESSING.value
        await db.flush()

        # Import aiosmtplib here to avoid import-time dependency issues in environments without SMTP support
        aiosmtplib = import_module("aiosmtplib")
        try:
            # 1. Render template
            html_content = cls.render_template(
                template_name=outbox.template_name,
                context=outbox.template_context,
            )

            # 2. Build MIME message
            msg = EmailMessage()
            msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            msg["To"] = outbox.recipient
            msg["Subject"] = outbox.subject
            msg.set_content(html_content, subtype="html")

            # 3. SMTP Send
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER or None,
                password=settings.SMTP_PASSWORD or None,
                start_tls=settings.SMTP_TLS,
            )

            # 4. Mark success
            outbox.status = EmailOutboxStatus.SENT.value
            outbox.sent_at = datetime.now(UTC)
            outbox.error_message = None
            await db.commit()
            logger.info(
                f"[EMAIL DELIVERED] To: {outbox.recipient} | Subject: '{outbox.subject}'"
            )

        except (TemplateError, aiosmtplib.errors.SMTPException) as exc:
            await db.rollback()
            outbox.error_message = str(exc)
            if outbox.attempts >= outbox.max_attempts:
                outbox.status = EmailOutboxStatus.FAILED.value
                logger.error(f"[EMAIL PERMANENTLY FAILED] Outbox ID {outbox_id}: {exc}")
            else:
                outbox.status = EmailOutboxStatus.PENDING.value
                logger.warning(f"[EMAIL RETRY SCHEDULED] Outbox ID {outbox_id}: {exc}")
            db.add(outbox)
            await db.commit()
            raise exc
