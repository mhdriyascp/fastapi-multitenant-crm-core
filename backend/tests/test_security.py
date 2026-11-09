"""Unit tests for Argon2id hashing and JWT token security utilities."""

from uuid import uuid4

from app.core.security import PasswordManager, TokenManager


def test_password_hash_and_verify():
    password = "SuperSecretPassword123!"
    hashed = PasswordManager.hash_password(password)

    # Hash should be generated and non-empty
    assert hashed != password
    assert hashed.startswith("$argon2id$")

    # Correct password verifies
    assert PasswordManager.verify_password(password, hashed) is True

    # Incorrect password fails verification
    assert PasswordManager.verify_password("WrongPassword123!", hashed) is False


def test_token_creation_and_decode():
    user_id = uuid4()
    public_id = uuid4()
    tenant_id = uuid4()

    token = TokenManager.create_access_token(
        subject=user_id,
        public_user_id=public_id,
        tenant_id=tenant_id,
    )

    assert isinstance(token, str)

    # Decode and verify claims
    claims = TokenManager.decode_access_token(token)
    assert claims["sub"] == str(user_id)
    assert claims["puid"] == str(public_id)
    assert claims["tid"] == str(tenant_id)
    assert "exp" in claims
    assert "jti" in claims


def test_refresh_token_generation_and_hashing():
    raw_token, token_hash = TokenManager.generate_refresh_token()

    assert len(raw_token) > 32
    assert len(token_hash) == 64  # SHA-256 hex digest length

    # Hashing raw token directly reproduces the same hash
    assert TokenManager.hash_refresh_token(raw_token) == token_hash

