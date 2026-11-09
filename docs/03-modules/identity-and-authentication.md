# Identity and Authentication Specification

This document details the authentication and identity mechanisms implemented in `backend/app/api/auth/router.py`, `backend/app/services/auth_service.py`, and `backend/app/core/security.py`.

---

## 📑 Table of Contents

- [Scope & Active Routes](#-scope--active-routes)
- [Registration & Tenant Provisioning Flow](#-registration--tenant-provisioning-flow)
- [Login & Email OTP MFA Challenge Flow](#-login--email-otp-mfa-challenge-flow)
- [Password Reset Flow](#-password-reset-flow)
- [Session Token Rotation & Workspace Switching](#-session-token-rotation--workspace-switching)
- [Security & Cryptographic Standards](#-security--cryptographic-standards)
- [Current Implementation Boundaries & Gaps](#-current-implementation-boundaries--gaps)
- [Related Code & References](#-related-code--references)

---

## 🌐 Scope & Active Routes

The active authentication router is `backend/app/api/auth/router.py`, mounted at `/auth` in `backend/main.py`.

| Method | Path | Summary | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Create user; optionally provision initial tenant & assign owner role | None |
| `POST` | `/auth/login` | Authenticate credentials; returns tokens or email-MFA challenge | None |
| `POST` | `/auth/refresh` | Rotate refresh token and issue new JWT access token | None |
| `POST` | `/auth/logout` | Revoke active user session | None |
| `GET` | `/auth/me` | Return profile of currently authenticated user | Bearer Token |
| `GET` | `/auth/workspaces` | List active workspaces where user holds membership | Bearer Token |
| `POST` | `/auth/switch-workspace` | Switch active workspace context and issue tenant-scoped JWT | Bearer Token |
| `POST` | `/auth/password/forgot` | Request password reset email via transactional outbox | None |
| `POST` | `/auth/password/reset` | Set new password using token and revoke all active sessions | None |
| `POST` | `/auth/mfa/verify-otp` | Verify 6-digit email OTP to complete login | None |
| `POST` | `/auth/mfa/email/toggle` | Enable or disable email OTP MFA (requires password) | Bearer Token |

---

## 📝 Registration & Tenant Provisioning Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Router as /auth/register
    participant Service as AuthService
    participant Hasher as PasswordManager
    participant DB as PostgreSQL
    participant Tokens as TokenManager

    Client->>Router: POST /auth/register {email, password, organization_name}
    Router->>Service: register_user(payload)
    Service->>DB: Check email & username uniqueness
    Service->>Hasher: hash_password(password) using Argon2id
    Service->>DB: INSERT INTO users (status='active', is_verified=false)
    opt If organization_name provided
        Service->>DB: INSERT INTO tenants (name, slug)
        Service->>DB: INSERT INTO tenant_memberships (user_id, tenant_id, status='active')
        Service->>DB: Link role 'org_owner' in membership_roles
    end
    Service->>Tokens: generate_refresh_token() & create_access_token()
    Service->>DB: INSERT INTO user_sessions (refresh_token_hash, expires_at)
    Service-->>Router: Return AuthSuccessResponse (user profile, tokens, active_tenant_id)
    Router-->>Client: HTTP 201 Created [JSON]
```

---

## 🔐 Login & Email OTP MFA Challenge Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Router as /auth/login
    participant Service as AuthService
    participant DB as PostgreSQL
    participant Redis as Redis Cache
    participant Outbox as EmailService (Outbox)

    Client->>Router: POST /auth/login {email, password}
    Router->>Service: authenticate_user(payload)
    Service->>DB: Query User & verify Argon2id password hash
    
    alt User has Email OTP MFA Enabled
        Service->>Service: Generate 32-byte mfa_session_token & 6-digit OTP
        Service->>Redis: SETEX mfa_pending:{token} (TTL: 300s) -> user_id|tenant_id|otp|attempts
        Service->>Outbox: enqueue(template="mfa_otp.html", otp_code)
        Service-->>Router: Return MFAChallengeResponse (masked email, mfa_token)
        Router-->>Client: HTTP 200 OK {mfa_required: true, mfa_token, masked_email}
        
        Client->>Router: POST /auth/mfa/verify-otp {mfa_token, otp_code}
        Router->>Service: verify_email_otp_login(payload)
        Service->>Redis: GET mfa_pending:{token}
        Service->>Service: hmac.compare_digest(submitted_otp, expected_otp)
        Service->>Redis: DEL mfa_pending:{token}
        Service->>DB: INSERT INTO user_sessions
        Service-->>Router: Return AuthSuccessResponse (tokens)
        Router-->>Client: HTTP 200 OK [JSON]
    else Standard Non-MFA Flow
        Service->>DB: INSERT INTO user_sessions (refresh_token_hash)
        Service-->>Router: Return AuthSuccessResponse (tokens)
        Router-->>Client: HTTP 200 OK [JSON]
    end
```

---

## 🔑 Password Reset Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Router as /auth/password/*
    participant Service as AuthService
    participant DB as PostgreSQL
    participant Redis as Redis Cache
    participant Outbox as EmailService (Outbox)

    Client->>Router: POST /auth/password/forgot {email}
    Router->>Service: request_password_reset(payload)
    Service->>DB: Query User by email
    opt User exists and active
        Service->>Service: Generate 32-byte cryptographic token
        Service->>Redis: SETEX pwd_reset:{hash(token)} (TTL: 15 min) -> user_id
        Service->>Outbox: enqueue(template="password_reset.html", reset_url)
    end
    Service-->>Router: Generic success message (prevents account enumeration)
    Router-->>Client: HTTP 200 OK {"message": "If this account exists..."}

    Note over Client: User clicks link in received email
    Client->>Router: POST /auth/password/reset {token, new_password}
    Router->>Service: reset_password(payload)
    Service->>Redis: GET pwd_reset:{hash(token)}
    Service->>DB: UPDATE users SET hashed_password = Argon2(new_password)
    Service->>DB: UPDATE user_sessions SET revoked_at = NOW() (revoke all sessions)
    Service->>Redis: DEL pwd_reset:{hash(token)}
    Service-->>Router: Return confirmation
    Router-->>Client: HTTP 200 OK {"message": "Your password has been reset successfully."}
```

---

## 🔄 Session Token Rotation & Workspace Switching

1. **Access Tokens**: Short-lived JWTs signed with HMAC-SHA256 containing:
   - `sub`: Internal user UUIDv7
   - `puid`: Public user UUIDv4
   - `tid`: Active workspace tenant UUIDv7 (optional)
   - `jti`: Cryptographically random nonce guarding against replay
   - Configured lifespan: 15 minutes.
2. **Refresh Tokens**: Opaque 512-bit URL-safe random strings. Only the SHA-256 digest is stored in `user_sessions`. Rotating the refresh token updates `refresh_token_hash` and invalidates the previous token to prevent replay attacks.
3. **Workspace Switching (`POST /auth/switch-workspace`)**:
   - Validates active membership in target workspace.
   - Rotates active session and updates its `tenant_id`.
   - Mints and returns a new access token scoped with the target `tid`.

---

## 🛡️ Security & Cryptographic Standards

- **Password Hashing**: OWASP-recommended **Argon2id** (`time_cost=3`, `memory_cost=65536` KiB, `parallelism=4`, `salt_len=16`).
- **Timing Attacks**: All OTP code comparisons use `hmac.compare_digest`.
- **Brute-Force Guard**: Failed OTP attempts increment counter in Redis; rejected after 5 attempts with `HTTP 429 Too Many Requests`.
- **Account Enumeration Defense**: Both registration and password-reset endpoints return generic confirmations or structured error codes.

---

## ⚠️ Current Implementation Boundaries & Gaps

- Domain exceptions (`EntityNotFoundException`, `EntityConflictException`, `BusinessRuleViolationException`, `PermissionDeniedException`, `AuthenticationException`, `RateLimitExceededException`) are now used in `AuthService`, decoupling business logic from FastAPI transport handlers.
- A separate database repository layer is planned for future phases to abstract SQLAlchemy session queries from services.

---

## 📖 Related Code & References

- Router: [`backend/app/api/auth/router.py`](../../backend/app/api/auth/router.py)
- Service: [`backend/app/services/auth_service.py`](../../backend/app/services/auth_service.py)
- Security Helpers: [`backend/app/core/security.py`](../../backend/app/core/security.py)
- Models: [`user.py`](../../backend/app/models/user.py), [`user_session.py`](../../backend/app/models/user_session.py), [`user_mfa_method.py`](../../backend/app/models/user_mfa_method.py)
- Email System: [Email Outbox and Background Worker](email-and-background-work.md)
