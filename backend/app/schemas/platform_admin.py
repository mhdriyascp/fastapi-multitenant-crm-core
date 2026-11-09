"""Request and response models for platform administration."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from app.core.enums import TenantStatus


class PlatformRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlatformPermissionResponse(BaseModel):
    public_id: UUID
    code: str
    module: str
    resource: str
    action: str
    description: str | None


class PlatformRoleCreate(PlatformRequestModel):
    code: str = Field(pattern=r"^platform_[a-z0-9_]+$", max_length=100)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permission_codes: list[str] = Field(default_factory=list, max_length=100)
    reason: str = Field(min_length=3, max_length=500)


class PlatformRoleResponse(BaseModel):
    public_id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    permission_codes: list[str]


class PlatformRolePermissionsUpdate(PlatformRequestModel):
    permission_codes: list[str] = Field(max_length=100)
    reason: str = Field(min_length=3, max_length=500)


class PlatformOperatorRoleUpdate(PlatformRequestModel):
    role_public_ids: list[UUID] = Field(max_length=50)
    reason: str = Field(min_length=3, max_length=500)


class PlatformOperatorListItem(BaseModel):
    public_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    is_platform_admin: bool


class PlatformOperatorResponse(BaseModel):
    public_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    roles: list[PlatformRoleResponse]


class PlatformTenantResponse(BaseModel):
    public_id: UUID
    name: str
    slug: str
    email: EmailStr | None
    status: TenantStatus


class PlatformTenantUpdate(PlatformRequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    status: TenantStatus | None = None
    reason: str = Field(min_length=3, max_length=500)


class TenantBranding(PlatformRequestModel):
    logo_url: HttpUrl | None = None
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TenantSettingsUpdate(PlatformRequestModel):
    locale: str = Field(default="en-US", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    date_format: Literal["YYYY-MM-DD", "MM/DD/YYYY", "DD/MM/YYYY"] = "YYYY-MM-DD"
    branding: TenantBranding = Field(default_factory=TenantBranding)
    reason: str = Field(min_length=3, max_length=500)


class TenantSettingsResponse(BaseModel):
    tenant_public_id: UUID
    values: dict[str, Any]
    updated_at: datetime | None


class SubscriptionPlanCreate(PlatformRequestModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,79}$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_minor: int = Field(default=0, ge=0, le=100_000_000)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    entitlements: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("entitlements")
    @classmethod
    def validate_entitlements(cls, entitlements: dict[str, Any]) -> dict[str, Any]:
        allowed = {"max_users", "max_storage_gb", "modules"}
        unknown = set(entitlements) - allowed
        if unknown:
            raise ValueError(
                f"Unsupported entitlement keys: {', '.join(sorted(unknown))}"
            )
        for key in ("max_users", "max_storage_gb"):
            if key in entitlements and (
                not isinstance(entitlements[key], int)
                or isinstance(entitlements[key], bool)
                or entitlements[key] < 1
            ):
                raise ValueError(f"{key} must be a positive integer")
        if "modules" in entitlements and (
            not isinstance(entitlements["modules"], list)
            or not all(
                isinstance(item, str) and item for item in entitlements["modules"]
            )
        ):
            raise ValueError("modules must be a list of non-empty strings")
        return entitlements


class SubscriptionPlanUpdate(PlatformRequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_minor: int | None = Field(default=None, ge=0, le=100_000_000)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    entitlements: dict[str, Any] | None = None
    is_active: bool | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("entitlements")
    @classmethod
    def validate_entitlements(
        cls, entitlements: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if entitlements is None:
            return None
        allowed = {"max_users", "max_storage_gb", "modules"}
        unknown = set(entitlements) - allowed
        if unknown:
            raise ValueError(
                f"Unsupported entitlement keys: {', '.join(sorted(unknown))}"
            )
        for key in ("max_users", "max_storage_gb"):
            if key in entitlements and (
                not isinstance(entitlements[key], int)
                or isinstance(entitlements[key], bool)
                or entitlements[key] < 1
            ):
                raise ValueError(f"{key} must be a positive integer")
        if "modules" in entitlements and (
            not isinstance(entitlements["modules"], list)
            or not all(
                isinstance(item, str) and item for item in entitlements["modules"]
            )
        ):
            raise ValueError("modules must be a list of non-empty strings")
        return entitlements


class SubscriptionPlanResponse(BaseModel):
    public_id: UUID
    code: str
    name: str
    description: str | None
    price_minor: int
    currency: str
    entitlements: dict[str, Any]
    is_active: bool
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TenantSubscriptionUpdate(PlatformRequestModel):
    plan_public_id: UUID
    status: Literal["trialing", "active", "past_due", "cancelled"] = "active"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_period(self):
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError("ends_at must be after starts_at")
        return self


class TenantSubscriptionResponse(BaseModel):
    public_id: UUID
    tenant_public_id: UUID
    plan: SubscriptionPlanResponse
    status: str
    starts_at: datetime
    ends_at: datetime | None


class PlatformAuditResponse(BaseModel):
    public_id: UUID
    actor_public_id: UUID | None
    tenant_public_id: UUID | None
    action: str
    resource_type: str
    resource_public_id: UUID | None
    reason: str
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    created_at: datetime
