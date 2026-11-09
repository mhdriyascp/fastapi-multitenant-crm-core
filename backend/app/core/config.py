import json
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Platform configuration and security settings."""

    # ---------------------------------------------------------------------------
    # Application & Environment
    # ---------------------------------------------------------------------------
    PROJECT_NAME: str = "Enterprise CRM & IAM"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # ---------------------------------------------------------------------------
    # Base URLs
    # ---------------------------------------------------------------------------
    BACKEND_BASE_URL: str = Field(
        default="http://127.0.0.1:8000",
        description="Public/routable backend API base URL",
    )
    FRONTEND_BASE_URL: str = Field(
        default="http://localhost:3000",
        description="Client frontend/dashboard URL",
    )

    # ---------------------------------------------------------------------------
    # CORS Configuration (Accepts list, JSON string, or comma-separated string)
    # ---------------------------------------------------------------------------
    CORS_ORIGINS: list[str] | str = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed origins for CORS",
    )

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, value: Any) -> list[str]:
        """Normalizes comma-separated strings or JSON arrays into a list of strings."""
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return ["http://localhost:3000", "http://127.0.0.1:3000"]
            if value.startswith("[") and value.endswith("]"):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(i).strip() for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip() for i in value.split(",") if i.strip()]
        elif isinstance(value, list):
            return [str(i).strip() for i in value if str(i).strip()]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ---------------------------------------------------------------------------
    # Database & Cache
    # ---------------------------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+asyncpg://crm_admin:admin%402k26@localhost:5432/crm_db"
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---------------------------------------------------------------------------
    # Email / SMTP Settings
    # ---------------------------------------------------------------------------
    SMTP_HOST: str = Field(default="localhost", description="SMTP server host")
    SMTP_PORT: int = Field(default=1025, description="SMTP server port")
    SMTP_USER: str | None = Field(default=None, description="SMTP authentication user")
    SMTP_PASSWORD: str | None = Field(default=None, description="SMTP authentication password")
    SMTP_TLS: bool = Field(default=False, description="Use TLS/STARTTLS")
    EMAILS_FROM_EMAIL: str = Field(default="noreply@crm.local", description="Sender address")
    EMAILS_FROM_NAME: str = Field(default="Enterprise CRM", description="Sender display name")

    # ---------------------------------------------------------------------------
    # Security, JWT & Lifecycles
    # ---------------------------------------------------------------------------
    JWT_SECRET_KEY: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        description="Cryptographic secret key for signing JWTs",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    MFA_OTP_EXPIRE_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
