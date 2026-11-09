# Email Outbox and Background Worker

## Components

- `backend/app/core/email.py`: Jinja template rendering, outbox record creation, ARQ enqueue, and SMTP dispatch.
- `backend/app/models/email_outbox.py`: email payload, optional tenant association, attempt tracking, delivery status, and timestamps.
- `backend/app/workers/email_worker.py`: ARQ worker task `process_outbox_email`.
- `backend/app/core/queue.py`: lazily creates the ARQ Redis connection pool.
- `backend/app/templates/email/`: base, invitation, password reset, and email OTP templates.
- `mailpit` in `compose.yaml`: local SMTP sink and browser mailbox.

## Enqueue flow

`EmailService.enqueue` is a classmethod called from within an active SQLAlchemy session:

1. Creates an `EmailOutbox` row (status `PENDING`, default `max_attempts=3`) and flushes it to obtain its UUIDv7 `id`.
2. Pushes the outbox `id` as an ARQ job (`process_outbox_email`) to Redis.
3. If the Redis enqueue raises `RedisError`, the error is logged via `print` and the row remains `PENDING`; the caller's DB transaction still proceeds. The comment in `email.py` mentions a pending-record sweeper for recovery in this case, but **no sweeper implementation exists** in the current worker package. Recovery of rows left pending after a Redis enqueue failure is therefore not automated.

The `EmailOutbox` row is persisted atomically with the calling business operation (e.g. invitation or password-reset request) because both share the same `AsyncSession`. If the outer transaction rolls back, the outbox row is never committed and no email is dispatched.

## Triggered by

| Trigger | Template | Notes |
|---|---|---|
| `MemberService.invite_member` | `workspace_invitation.html` | Enqueued within the invitation DB transaction |
| `AuthService.request_password_reset` | `password_reset.html` | Reset link built from `FRONTEND_BASE_URL` |
| `AuthService.initiate_email_mfa_challenge` | `mfa_otp.html` | OTP code included in the template context |

## Worker dispatch (`process_outbox_email`)

The ARQ worker uses a dedicated SQLAlchemy engine and session (`worker_engine`, `worker_session_maker`) separate from the web API session factory. The task:

1. Loads the `EmailOutbox` row by ID using `SELECT … FOR UPDATE` to prevent concurrent processing.
2. Returns immediately if the row is already `SENT` or not found.
3. Increments `attempts` and sets status to `PROCESSING`.
4. Renders the named Jinja2 template with the stored `template_context`.
5. Sends via `aiosmtplib` using SMTP settings from `config.py`.
6. On success: sets status to `SENT`, records `sent_at`, and commits.
7. On `TemplateError` or `SMTPException`: rolls back, stores `error_message`, and either resets status to `PENDING` (if attempts < `max_attempts`) or sets `FAILED` (if exhausted). Then commits the updated status and re-raises.

Worker configuration (`WorkerSettings`):
- `max_jobs = 10` concurrent jobs.
- `job_timeout = 60` seconds.
- `redis_settings` from `REDIS_URL`.

## Delivery guarantees and limitations

- The outbox table in PostgreSQL is durable; the row is committed as part of the initiating request's transaction.
- PostgreSQL and Redis are separate systems. Adding the outbox row and enqueuing the ARQ job are not a single distributed atomic commit. A Redis enqueue failure leaves the row in `PENDING` with no automated sweeper to retry it.
- When SMTP fails and `attempts < max_attempts`, the status returns to `PENDING`. Re-delivery in this case depends on the job being re-queued or a future sweeper; this is not currently handled automatically.
- Application logs should not contain passwords, access tokens, reset tokens, or OTPs. The `email.py` worker uses `print()` for delivery logging; use the standard `logging` module for new operational log statements.

## Running and configuration

The worker is exposed through the backend script entry point `worker = "arq.cli:cli"` (from `pyproject.toml`) and uses `WorkerSettings` in `email_worker.py`:

```sh
cd backend
uv run worker backend.app.workers.email_worker.WorkerSettings
```

SMTP and frontend/backend URLs are configured through the settings in `backend/app/core/config.py`. Local Mailpit ports are documented in [Local development](../02-setup/local-development.md).
