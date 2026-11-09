from enum import Enum


# ---------------------------------------------------------------------------
# Global User & Identity Lifecycles
# ---------------------------------------------------------------------------
class UserStatus(str, Enum):
    """Lifecycle states for global user accounts."""
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


# ---------------------------------------------------------------------------
# Tenant & Organization Lifecycles
# ---------------------------------------------------------------------------
class TenantStatus(str, Enum):
    """Lifecycle states for customer organizations / tenants."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Organization Membership Lifecycles
# ---------------------------------------------------------------------------
class MembershipStatus(str, Enum):
    """Lifecycle states for a user's association with a specific tenant."""
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    REMOVED = "removed"


# ---------------------------------------------------------------------------
# Security & Session Lifecycles
# ---------------------------------------------------------------------------
class SessionStatus(str, Enum):
    """Lifecycle states for user login sessions."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Multi-Factor Authentication (MFA) Lifecycles
# ---------------------------------------------------------------------------
class MFAMethodStatus(str, Enum):
    """Status of user multi-factor authentication methods."""
    PENDING_CONFIRMATION = "pending_confirmation"
    ACTIVE = "active"
    DISABLED = "disabled"
  
# ---------------------------------------------------------------------------
# Multi-Factor Authentication (MFA) Lifecycles
# ---------------------------------------------------------------------------
class MFAMethodType(str, Enum):
    TOTP = "totp"
    WEBAUTHN = "webauthn"
    EMAIL_OTP = "email_otp"


# ---------------------------------------------------------------------------
# Role Audit Actions
# ---------------------------------------------------------------------------
class RoleAuditAction(str, Enum):
    ASSIGNED = "assigned"
    REVOKED = "revoked"
    

# ---------------------------------------------------------------------------
#Common Audit Actions
# ---------------------------------------------------------------------------

class CommonStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

#---------------------------------------------------------------------------
# Email Outbox Lifecycles
#---------------------------------------------------------------------------    
class EmailOutboxStatus(str, Enum):
    """Lifecycle states for transactional outbox emails."""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
