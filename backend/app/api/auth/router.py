from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedContext, get_current_context, get_db
from app.core.redis import get_redis
from app.schemas.auth import (
    AuthSuccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    MFAChallengeResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SwitchWorkspaceRequest,
    SwitchWorkspaceResponse,
    ToggleMFAEmailRequest,
    TokenResponse,
    UserProfileResponse,
    UserRegisterRequest,
    VerifyEmailOTPRequest,
    WorkspaceItemResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=AuthSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthSuccessResponse:
    """Registers a new user, optionally provisions a workspace, and returns tokens."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.register_user(
        payload=payload, client_ip=client_ip, user_agent=user_agent
    )


@router.post(
    "/login",
    response_model=AuthSuccessResponse | MFAChallengeResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user credentials",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthSuccessResponse | MFAChallengeResponse:
    """Authenticates credentials and establishes a new user session."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.authenticate_user(
        payload=payload, redis=redis, client_ip=client_ip, user_agent=user_agent
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue a new access token",
)
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotates an existing active refresh token and returns a fresh JWT."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.refresh_tokens(
        raw_refresh_token=payload.refresh_token,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke active user session",
)
async def logout(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Explicitly revokes an active session."""
    service = AuthService(db)
    await service.revoke_session(raw_refresh_token=payload.refresh_token)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current authenticated user profile",
)
async def get_current_user_profile(
    context: AuthenticatedContext = Depends(get_current_context),
) -> UserProfileResponse:
    """Returns the profile of the currently authenticated token bearer."""
    return UserProfileResponse.model_validate(context.user)


@router.get(
    "/workspaces",
    response_model=list[WorkspaceItemResponse],
    summary="List workspaces accessible by current user",
)
async def list_workspaces(
    context: AuthenticatedContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceItemResponse]:
    """Returns all tenant workspaces where the authenticated user has an active membership."""
    service = AuthService(db)
    return await service.get_user_workspaces(user_id=context.user.id)


@router.post(
    "/switch-workspace",
    response_model=SwitchWorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Switch active tenant workspace",
)
async def switch_workspace(
    payload: SwitchWorkspaceRequest,
    request: Request,
    context: AuthenticatedContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> SwitchWorkspaceResponse:
    """Switches active workspace context and issues a new access token scoped to target tenant."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.switch_workspace(
        user=context.user,
        payload=payload,
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