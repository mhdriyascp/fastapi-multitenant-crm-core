# Email Outbox and Background Worker

## Components

- `backend/app/core/email.py`: Jinja template rendering, outbox creation, ARQ enqueue, and SMTP dispatch.
- `backend/app/models/email_outbox.py`: email payload, tenant association, attempts, status, timestamps, and latest error.
- `backend/app/workers/email_worker.py`: ARQ worker task `process_outbox_email`.
- `backend/app/core/queue.py`: lazily creates the ARQ Redis connection pool.
- `backend/app/templates/email/`: base, invitation, password reset, and email OTP templates.
- `mailpit` in `compose.yaml`: local SMTP sink and browser mailbox.

## Invitation flow

`MemberService.invite_member` creates/associates the user, membership, role associations and audit rows, then calls `EmailService.enqueue` for a workspace invitation. The enqueue method adds an `email_outbox` row to the caller's SQLAlchemy session and queues its ID in ARQ. The request session is committed by the database dependency after the request returns normally.

Redis enqueue errors are caught; the outbox row remains pending and the request continues. The code comments mention a pending-record sweeper, but no sweeper implementation was found in the inspected worker package. Therefore automated recovery of a pending row after enqueue failure is not established by the current code.

The worker loads the row, locks it with `FOR UPDATE`, increments attempts, marks it processing, renders the named template, sends via SMTP, then marks the row sent or failed/pending. The configured maximum-attempt count defaults to three in the model.

## Delivery guarantees and limitations

The outbox table is durable in PostgreSQL, but PostgreSQL and Redis are separate systems; adding the database row and enqueueing a Redis job is not a single distributed atomic commit. The implementation is intended to provide retryable delivery, but the current code does not establish complete at-least-once delivery or automatic recovery in every failure case.

The password-reset and MFA services currently print reset/MFA tokens to process output rather than using this outbox flow. The mere presence of matching email templates does not mean those flows send email today.

Application logs should not contain passwords, access tokens, reset tokens, or OTPs. Existing print-based development output is a current implementation gap, not an operational recommendation.

## Running and configuration

The worker is exposed through the backend script entry point `worker = "arq.cli:cli"` and uses `WorkerSettings` in `email_worker.py`. SMTP and frontend/backend URLs are configured through the settings in `backend/app/core/config.py`. Local Mailpit ports are documented in [Local development](../02-setup/local-development.md).
