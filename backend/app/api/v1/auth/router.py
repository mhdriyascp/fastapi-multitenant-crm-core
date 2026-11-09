from app.api.deps import AuthenticatedContext, get_current_context, get_db
from app.core.redis import get_redis
from app.schemas.auth import (
    AuthSuccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    MFAChallengeResponse,
    ResetPasswordRequest,
    ToggleMFAEmailRequest,
    VerifyEmailOTPRequest,
)
from app.services.auth_service import AuthService
from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ---------------------------------------------------------------------------
# Update Login Endpoint to support Redis & MFA Response
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=AuthSuccessResponse | MFAChallengeResponse,
    status_code=status.HTTP_200_OK,
    summary="User login with automatic MFA detection",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthSuccessResponse | MFAChallengeResponse:
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.authenticate_user(
        payload=payload,
        redis=redis,
        client_ip=client_ip,
        user_agent=user_agent,
    )


# ---------------------------------------------------------------------------
# Password Reset Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/password/forgot",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset link/token",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    service = AuthService(db)
    await service.request_password_reset(payload, redis)
    return MessageResponse(
        message="If this account exists, a password reset link has been dispatched."
    )


@router.post(
    "/password/reset",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using received token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    service = AuthService(db)
    await service.reset_password(payload, redis)
    return MessageResponse(
        message="Your password has been reset successfully. Please log in with your new credentials."
    )


# ---------------------------------------------------------------------------
# MFA Email OTP Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/mfa/verify-otp",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Email OTP to complete login",
)
async def verify_mfa_otp(
    payload: VerifyEmailOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthSuccessResponse:
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.verify_email_otp_login(
        payload=payload,
        redis=redis,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.post(
    "/mfa/email/toggle",
    response_model=MessageResponse,
    summary="Enable or disable Email OTP MFA for account",
)
async def toggle_mfa_email(
    payload: ToggleMFAEmailRequest,
    context: AuthenticatedContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    service = AuthService(db)
    msg = await service.toggle_email_mfa(
        user=context.user,
        enable=payload.enable,
        current_password=payload.current_password,
    )
    return MessageResponse(message=msg)
