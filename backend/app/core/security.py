import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from app.core.config import settings
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# ---------------------------------------------------------------------------
# 1. Argon2id Password Hashing (OWASP Standard)
# ---------------------------------------------------------------------------
# Argon2id provides memory-hard protection against GPU / ASIC brute-forcing
_hasher = PasswordHasher(
    time_cost=3,        # 3 iterations
    memory_cost=65536,  # 64 MB memory
    parallelism=4,      # 4 parallel threads
    hash_len=32,
    salt_len=16,
)


class PasswordManager:
    """Handles secure password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes a plaintext password using Argon2id."""
        return _hasher.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies a plaintext password against an Argon2id hash."""
        try:
            return _hasher.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False

    @staticmethod
    def check_needs_rehash(hashed_password: str) -> bool:
        """Checks if the hash parameters need an upgrade."""
        return _hasher.check_needs_rehash(hashed_password)


# ---------------------------------------------------------------------------
# 2. JWT & Refresh Token Manager
# ---------------------------------------------------------------------------
class TokenManager:
    """Handles JWT generation, verification, and opaque refresh token hashing."""

    @staticmethod
    def create_access_token(
        subject: UUID | str,
        public_user_id: UUID | str,
        tenant_id: UUID | str | None = None,
        expires_delta: timedelta | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Creates a signed JWT access token.
        - sub: Internal user ID (UUIDv7)
        - puid: Public user ID (UUIDv4)
        - tid: Active tenant workspace ID (UUIDv7, optional)
        """
        now = datetime.now(UTC)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload: dict[str, Any] = {
            "sub": str(subject),
            "puid": str(public_user_id),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": secrets.token_hex(16),  # Unique token identifier to guard against replay
        }

        if tenant_id:
            payload["tid"] = str(tenant_id)

        if extra_claims:
            payload.update(extra_claims)

        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> dict[str, Any]:
        """
        Decodes and cryptographically verifies an access token.
        Raises jwt.PyJWTError on invalid signatures or expired tokens.
        """
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "iat"]},
        )

    @staticmethod
    def generate_refresh_token() -> tuple[str, str]:
        """
        Generates a secure opaque refresh token.
        Returns:
            - raw_token: 256-bit URL-safe token given ONLY to the client.
            - token_hash: SHA-256 digest saved in the database (user_sessions).
        """
        raw_token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        return raw_token, token_hash

    @staticmethod
    def hash_refresh_token(raw_token: str) -> str:
        """Hashes an inbound refresh token for database lookup in user_sessions."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
