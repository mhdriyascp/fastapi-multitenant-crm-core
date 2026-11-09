# Identity and Authentication

## Scope

The active authentication router is `backend/app/api/auth/router.py`; `backend/main.py` mounts it under `/auth`. Business operations are implemented by `AuthService` in `backend/app/services/auth_service.py`. Request and response models are in `backend/app/schemas/auth.py`.

There is a separate `backend/app/api/v1/auth/router.py` module, but it is not included by `main.py` or the current versioned router. Its endpoints are not active application routes unless registration changes.

## Active endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create user; optionally create an organization/workspace; return tokens |
| POST | `/auth/login` | Authenticate credentials; returns tokens or an email-MFA challenge |
| POST | `/auth/refresh` | Rotate the refresh token and issue a new access token |
| POST | `/auth/logout` | Revoke the session associated with a refresh token |
| GET | `/auth/me` | Return the authenticated user's profile |
| GET | `/auth/workspaces` | List active workspaces where the user has membership |
| POST | `/auth/switch-workspace` | Validate a workspace membership and rotate session credentials for that workspace |
| POST | `/auth/password/forgot` | Request a reset token; response is generic to avoid account enumeration |
| POST | `/auth/password/reset` | Set a new password with a reset token and revoke active sessions |
| POST | `/auth/mfa/verify-otp` | Verify an email OTP and create a session |
| POST | `/auth/mfa/email/toggle` | Enable or disable email OTP MFA after password confirmation |

## Authentication and session flow

- Password hashes are generated and checked by `PasswordManager` using Argon2.
- Access tokens are JWTs containing the internal user ID in `sub`, public user ID in `puid`, and optional tenant ID in `tid`. The configured access-token lifetime defaults to 15 minutes.
- Refresh tokens are opaque random strings. The database stores their SHA-256 hash in `user_sessions`; refresh rotates the stored hash. The configured refresh lifetime defaults to 30 days.
- Session records include user, optional tenant, expiry, revoked time, IP address, and user-agent.
- `get_current_context` in `backend/app/api/deps.py` validates a bearer JWT, confirms the user is active and not soft-deleted, and resolves the optional tenant membership and permission set.
- Password reset tokens and pending email-MFA challenges are stored in Redis with a 15-minute and 5-minute TTL respectively. Incorrect MFA codes are limited to five attempts in the service flow.

## Current email/reset limitations

- The password-reset service currently stores the token in Redis and prints the reset link/token to process output. It does not enqueue a password-reset email through `EmailService`.
- The email-MFA challenge service currently prints the OTP and challenge token to process output; it does not send an email using the email outbox.
- Email OTP MFA is stored as a `UserMFAMethod` with `method_type=email_otp`. The toggle service marks the method verified when enabled; the current flow does not require a separate enrollment OTP confirmation before setting that state.

Treat these as current development implementation facts, not recommended production behavior. Do not copy tokens or OTPs into logs or documentation.

## Related code

- Router: `backend/app/api/auth/router.py`
- Service: `backend/app/services/auth_service.py`
- Schemas: `backend/app/schemas/auth.py`
- Auth dependency and permission guard: `backend/app/api/deps.py`
- Security helpers: `backend/app/core/security.py`
- Models: `user.py`, `user_session.py`, `user_mfa_method.py`, `tenant.py`, `tenant_membership.py`

See also [IAM and RBAC](iam-rbac.md), [Database and migrations](../04-database/database-and-migrations.md), and [Email outbox](email-and-background-work.md).
