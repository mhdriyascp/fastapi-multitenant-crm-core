from typing import Any


class AppException(Exception):
    """Base exception for all domain-specific application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class EntityNotFoundException(AppException):
    """Raised when a requested resource does not exist in the system."""

    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{entity_id}' not found.",
            code=f"{entity_name.upper()}_NOT_FOUND",
            status_code=404,
        )


class EntityConflictException(AppException):
    """Raised when an entity violates a uniqueness constraint (e.g., duplicate email)."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(
            message=message,
            code="ENTITY_CONFLICT",
            status_code=409,
            details=details,
        )


class BusinessRuleViolationException(AppException):
    """Raised when an operation violates a domain business rule."""

    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION"):
        super().__init__(
            message=message,
            code=code,
            status_code=422,
        )
