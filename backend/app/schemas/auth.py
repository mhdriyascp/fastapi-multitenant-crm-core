from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# 1. Inbound Request Payloads
# ---------------------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    """Payload for user self-registration."""

    email: EmailStr = Field(..., description="Primary login email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plaintext password (min 8 chars)",
    )
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    username: str | None = Field(default=None, min_length=3, max_length=100)
    organization_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        description="Optional company/workspace name to auto-provision an initial tenant",
    )


class LoginRequest(BaseModel):
    """Payload for password authentication."""

    email: EmailStr
    password: str
    tenant_id: UUID | None = Field(
        default=None,
        description="Optional tenant workspace context ID for the session",
    )


class RefreshTokenRequest(BaseModel):
    """Payload for rotating refresh token."""

    refresh_token: str = Field(..., description="Opaque 256-bit refresh token")


# ---------------------------------------------------------------------------
# 2. Outbound Response Payloads
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    """Standard Bearer token envelope with refresh capability."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class UserProfileResponse(BaseModel):
    """Public user identity projection."""

    public_id: UUID
    email: EmailStr
    username: str | None = None
    first_name: str
    last_name: str
    is_verified: bool
    is_platform_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthSuccessResponse(BaseModel):
    """Response returned upon successful login or registration."""

    user: UserProfileResponse
    tokens: TokenResponse
    active_tenant_id: UUID | None = None
    
# ---------------------------------------------------------------------------
# 3. Workspace Discovery & Switching Schemas
# ---------------------------------------------------------------------------
class WorkspaceRoleInfo(BaseModel):
    """Role information for a workspace membership."""

    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class WorkspaceItemResponse(BaseModel):
    """Workspace / Tenant summary for the user."""

    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    joined_at: datetime | None
    is_active: bool
    roles: list[WorkspaceRoleInfo]

    model_config = ConfigDict(from_attributes=True)


class SwitchWorkspaceRequest(BaseModel):
    """Payload to switch active workspace context."""

    target_tenant_id: UUID = Field(..., description="Target tenant ID to switch into")
    refresh_token: str = Field(..., description="Current active refresh token")


class SwitchWorkspaceResponse(BaseModel):
    """Response returned upon switching active workspace."""

    active_tenant_id: UUID
    tokens: TokenResponse

# ---------------------------------------------------------------------------
# Password Reset Schemas
# ---------------------------------------------------------------------------
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Account email to receive reset code/link")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset token received via email")
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# MFA & Dashboard Login Challenge Schemas
# ---------------------------------------------------------------------------
class MFAChallengeResponse(BaseModel):
    """Returned by /auth/login when MFA is required before dashboard entry."""

    mfa_required: bool = True
    mfa_token: str = Field(..., description="Short-lived token for verifying MFA")
    method: str = "email_otp"
    masked_email: str = Field(..., description="Masked destination, e.g., a***r@acme.com")


class VerifyEmailOTPRequest(BaseModel):
    mfa_token: str = Field(..., description="Temporary challenge token from login")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit numeric OTP")


class ResendOTPRequest(BaseModel):
    mfa_token: str = Field(..., description="Temporary challenge token from login")


class ToggleMFAEmailRequest(BaseModel):
    enable: bool = Field(..., description="True to enable Email OTP MFA, False to disable")
    current_password: str = Field(..., description="Current password for verification")
