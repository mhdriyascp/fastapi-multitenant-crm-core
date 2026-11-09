"""Unit tests for domain application exceptions and status codes."""

from app.core.exceptions import (
    AppException,
    AuthenticationException,
    BusinessRuleViolationException,
    EntityConflictException,
    EntityNotFoundException,
    PermissionDeniedException,
    RateLimitExceededException,
)


def test_entity_not_found_exception():
    exc = EntityNotFoundException("Tenant", "123e4567-e89b-12d3-a456-426614174000")
    assert exc.status_code == 404
    assert exc.code == "TENANT_NOT_FOUND"
    assert "not found" in exc.message


def test_entity_conflict_exception():
    exc = EntityConflictException("Email already registered.")
    assert exc.status_code == 409
    assert exc.code == "ENTITY_CONFLICT"
    assert exc.message == "Email already registered."


def test_business_rule_violation_exception():
    exc = BusinessRuleViolationException("Cannot remove self from workspace.")
    assert exc.status_code == 422
    assert exc.code == "BUSINESS_RULE_VIOLATION"


def test_permission_denied_exception():
    exc = PermissionDeniedException("You do not have active access to this workspace.")
    assert exc.status_code == 403
    assert exc.code == "PERMISSION_DENIED"


def test_authentication_exception():
    exc = AuthenticationException("Invalid email or password.")
    assert exc.status_code == 401
    assert exc.code == "AUTHENTICATION_FAILED"


def test_rate_limit_exceeded_exception():
    exc = RateLimitExceededException("Too many incorrect OTP attempts.")
    assert exc.status_code == 429
    assert exc.code == "TOO_MANY_REQUESTS"

