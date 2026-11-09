import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import settings
from app.core.constants import ROLE_ORG_OWNER
from app.core.email import EmailService
from app.core.enums import MembershipStatus, MFAMethodType, TenantStatus, UserStatus
from app.core.security import PasswordManager, TokenManager
from app.models.membership_role import MembershipRole
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.models.user_mfa_method import UserMFAMethod
from app.models.user_session import UserSession
from app.schemas.auth import (
    AuthSuccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MFAChallengeResponse,
    ResetPasswordRequest,
    SwitchWorkspaceRequest,
    SwitchWorkspaceResponse,
    TokenResponse,
    UserProfileResponse,
    UserRegisterRequest,
    VerifyEmailOTPRequest,
    WorkspaceItemResponse,
    WorkspaceRoleInfo,
)
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class AuthService:
    """Core identity, authentication, and session orchestration service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(
        self,
        payload: UserRegisterRequest,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSuccessResponse:
        """
        Registers a new user account:
        1. Validates email & username uniqueness.
        2. Hashes password via Argon2id.
        3. Optionally creates an initial Tenant and assigns the 'Organization Owner' role.
        4. Issues short-lived access token and records a refresh session.
        """
        # 1. Uniqueness checks
        existing_email = await self.db.execute(
            select(User.id).where(User.email == payload.email.lower().strip())
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists.",
            )

        if payload.username:
            existing_username = await self.db.execute(
                select(User.id).where(User.username == payload.username.strip())
            )
            if existing_username.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This username is already taken.",
                )

        # 2. Instantiate User
        user = User(
            email=payload.email.lower().strip(),
            username=payload.username.strip() if payload.username else None,
            hashed_password=PasswordManager.hash_password(payload.password),
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            status=UserStatus.ACTIVE,
            is_verified=False,
            is_platform_admin=False,
        )
        self.db.add(user)
        await self.db.flush()

        active_tenant_id: UUID | None = None

        # 3. Provision Initial Tenant if requested
        if payload.organization_name:
            slug = re.sub(r"[^a-z0-9]+", "-", payload.organization_name.lower()).strip("-")
            tenant = Tenant(
                name=payload.organization_name.strip(),
                slug=f"{slug}-{user.id.hex[:6]}",
                status=TenantStatus.ACTIVE,
                created_by_id=user.id,
            )
            self.db.add(tenant)
            await self.db.flush()
            active_tenant_id = tenant.id

            # Create Owner Membership
            membership = TenantMembership(
                tenant_id=tenant.id,
                user_id=user.id,
                status=MembershipStatus.ACTIVE,
                joined_at=datetime.now(UTC),
                created_by_id=user.id,
            )
            self.db.add(membership)
            await self.db.flush()

            # Assign System Role 'org_owner'
            role_query = await self.db.execute(
                select(Role).where(
                    Role.code == ROLE_ORG_OWNER,
                    Role.tenant_id.is_(None),
                )
            )
            owner_role = role_query.scalar_one_or_none()
            if owner_role:
                membership_role = MembershipRole(
                    membership_id=membership.id,
                    role_id=owner_role.id,
                    assigned_by=user.id,
                )
                self.db.add(membership_role)
                await self.db.flush()

        # 4. Issue Session Tokens
        tokens = await self._create_user_session(
            user=user,
            tenant_id=active_tenant_id,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        return AuthSuccessResponse(
            user=UserProfileResponse.model_validate(user),
            tokens=tokens,
            active_tenant_id=active_tenant_id,
        )

    async def authenticate_user(
        self,
        payload: LoginRequest,
        redis: Redis,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSuccessResponse | MFAChallengeResponse:
        user_query = await self.db.execute(
            select(User).where(User.email == payload.email.lower().strip())
        )
        user = user_query.scalar_one_or_none()
        if (
            user is None
            or user.status != UserStatus.ACTIVE
            or user.deleted_at is not None
            or user.hashed_password is None
            or not PasswordManager.verify_password(
                payload.password, user.hashed_password
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        active_tenant_id = payload.tenant_id
        if active_tenant_id is not None:
            membership_query = await self.db.execute(
                select(TenantMembership.id)
                .join(Tenant, TenantMembership.tenant_id == Tenant.id)
                .where(
                    TenantMembership.tenant_id == active_tenant_id,
                    TenantMembership.user_id == user.id,
                    TenantMembership.status == MembershipStatus.ACTIVE,
                    TenantMembership.deleted_at.is_(None),
                    Tenant.status == TenantStatus.ACTIVE,
                    Tenant.deleted_at.is_(None),
                )
            )
            if (
                membership_query.scalar_one_or_none() is None
                and not user.is_platform_admin
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have active access to this workspace.",
                )
        elif not user.is_platform_admin:
            membership_query = await self.db.execute(
                select(TenantMembership.tenant_id)
                .join(Tenant, TenantMembership.tenant_id == Tenant.id)
                .where(
                    TenantMembership.user_id == user.id,
                    TenantMembership.status == MembershipStatus.ACTIVE,
                    TenantMembership.deleted_at.is_(None),
                    Tenant.status == TenantStatus.ACTIVE,
                    Tenant.deleted_at.is_(None),
                )
                .order_by(TenantMembership.joined_at.desc().nullslast())
                .limit(1)
            )
            active_tenant_id = membership_query.scalar_one_or_none()

        # Check if user has Email MFA enabled
        if await self.is_email_mfa_enabled(user.id):
            return await self.initiate_email_mfa_challenge(
                user=user,
                tenant_id=active_tenant_id,
                redis=redis,
            )

        # Standard non-MFA flow
        user.last_login_at = datetime.now(UTC)
        await self.db.flush()

        tokens = await self._create_user_session(
            user=user,
            tenant_id=active_tenant_id,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        return AuthSuccessResponse(
            user=UserProfileResponse.model_validate(user),
            tokens=tokens,
            active_tenant_id=active_tenant_id,
        )

    async def refresh_tokens(
        self,
        raw_refresh_token: str,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        """
        Rotates refresh token and issues a new access token.
        Revokes old session hash to prevent replay attacks.
        """
        token_hash = TokenManager.hash_refresh_token(raw_refresh_token)

        session_query = await self.db.execute(
            select(UserSession).where(
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
        active_session = session_query.scalar_one_or_none()

        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token.",
            )

        now = datetime.now(UTC)
        if active_session.expires_at <= now:
            active_session.revoked_at = now
            await self.db.flush()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please log in again.",
            )

        user_query = await self.db.execute(
            select(User).where(User.id == active_session.user_id)
        )
        user = user_query.scalar_one_or_none()
        if not user or user.status != UserStatus.ACTIVE or user.deleted_at is not None:
            active_session.revoked_at = now
            await self.db.flush()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is no longer active.",
            )

        new_raw_token, new_token_hash = TokenManager.generate_refresh_token()
        active_session.refresh_token_hash = new_token_hash
        active_session.ip_address = client_ip or active_session.ip_address
        active_session.user_agent = user_agent or active_session.user_agent
        active_session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.db.flush()

        access_token = TokenManager.create_access_token(
            subject=user.id,
            public_user_id=user.public_id,
            tenant_id=active_session.tenant_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_raw_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_user_workspaces(self, user_id: UUID) -> list[WorkspaceItemResponse]:
        """
        Retrieves all active tenant workspaces where the user has an active membership,
        including their assigned roles.
        """
        query = (
            select(TenantMembership)
            .where(
                TenantMembership.user_id == user_id,
                TenantMembership.status == MembershipStatus.ACTIVE,
                TenantMembership.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantMembership.tenant),
                selectinload(TenantMembership.membership_roles).selectinload(MembershipRole.role),
            )
        )
        result = await self.db.execute(query)
        memberships = result.scalars().all()

        workspaces: list[WorkspaceItemResponse] = []
        for m in memberships:
            if not m.tenant or m.tenant.status != TenantStatus.ACTIVE or m.tenant.deleted_at is not None:
                continue

            roles: list[WorkspaceRoleInfo] = [
                WorkspaceRoleInfo(code=mr.role.code, name=mr.role.name)
                for mr in m.membership_roles
                if mr.role and mr.role.is_active and not mr.role.deleted_at
            ]

            workspaces.append(
                WorkspaceItemResponse(
                    tenant_id=m.tenant.id,
                    tenant_name=m.tenant.name,
                    tenant_slug=m.tenant.slug,
                    joined_at=m.joined_at,
                    is_active=True,
                    roles=roles,
                )
            )

        return workspaces

    async def switch_workspace(
        self,
        user: User,
        payload: SwitchWorkspaceRequest,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> SwitchWorkspaceResponse:
        """
        Validates membership in target workspace, updates the active session,
        and issues a fresh JWT access token scoped to the target tenant.
        """
        # 1. Verify user has an active membership in the target tenant
        membership_query = await self.db.execute(
            select(TenantMembership)
            .join(Tenant, TenantMembership.tenant_id == Tenant.id)
            .where(
                TenantMembership.tenant_id == payload.target_tenant_id,
                TenantMembership.user_id == user.id,
                TenantMembership.status == MembershipStatus.ACTIVE,
                TenantMembership.deleted_at.is_(None),
                Tenant.status == TenantStatus.ACTIVE,
                Tenant.deleted_at.is_(None),
            )
        )
        membership = membership_query.scalar_one_or_none()
        if not membership and not user.is_platform_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have active access to this workspace.",
            )

        # 2. Validate current refresh token & session
        token_hash = TokenManager.hash_refresh_token(payload.refresh_token)
        session_query = await self.db.execute(
            select(UserSession).where(
                UserSession.refresh_token_hash == token_hash,
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
        )
        active_session = session_query.scalar_one_or_none()

        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session. Please log in again.",
            )

        # 3. Rotate session to point to the new tenant context
        now = datetime.now(UTC)
        new_raw_token, new_token_hash = TokenManager.generate_refresh_token()

        active_session.tenant_id = payload.target_tenant_id
        active_session.refresh_token_hash = new_token_hash
        active_session.ip_address = client_ip or active_session.ip_address
        active_session.user_agent = user_agent or active_session.user_agent
        active_session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.db.flush()

        # 4. Mint new access token with target tenant_id claim
        access_token = TokenManager.create_access_token(
            subject=user.id,
            public_user_id=user.public_id,
            tenant_id=payload.target_tenant_id,
        )

        return SwitchWorkspaceResponse(
            active_tenant_id=payload.target_tenant_id,
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=new_raw_token,
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            ),
        )

    async def revoke_session(self, raw_refresh_token: str) -> None:
        """Revokes an active session by setting revoked_at timestamp."""
        token_hash = TokenManager.hash_refresh_token(raw_refresh_token)
        session_query = await self.db.execute(
            select(UserSession).where(
                UserSession.refresh_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
        )
        user_session = session_query.scalar_one_or_none()
        if user_session:
            user_session.revoked_at = datetime.now(UTC)
            await self.db.flush()

    async def _create_user_session(
        self,
        user: User,
        tenant_id: UUID | None,
        client_ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        """Internal helper to mint access token and persist a new user_sessions row."""
        raw_refresh, token_hash = TokenManager.generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        session_record = UserSession(
            user_id=user.id,
            tenant_id=tenant_id,
            refresh_token_hash=token_hash,
            ip_address=client_ip,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        self.db.add(session_record)
        await self.db.flush()

        access_token = TokenManager.create_access_token(
            subject=user.id,
            public_user_id=user.public_id,
            tenant_id=tenant_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def _mask_email(email: str) -> str:
        """Masks an email for safe display (e.g. alex@acme.com -> a***x@acme.com)."""
        name, domain = email.split("@", 1)
        if len(name) <= 2:
            masked_name = name[0] + "*"
        else:
            masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
        return f"{masked_name}@{domain}"

    # ---------------------------------------------------------------------------
    # Password Reset (Outbox-Driven)
    # ---------------------------------------------------------------------------
    async def request_password_reset(
        self,
        payload: ForgotPasswordRequest,
        redis: Redis,
    ) -> None:
        """
        Generates a secure, time-limited reset token and enqueues a transactional outbox email.
        Always returns generic response to prevent account enumeration.
        """
        user_query = await self.db.execute(
            select(User).where(User.email == payload.email.lower().strip())
        )
        user = user_query.scalar_one_or_none()
        if not user or user.status != UserStatus.ACTIVE or user.deleted_at is not None:
            return  # Prevent user enumeration

        # 32-byte cryptographic token
        raw_token = secrets.token_urlsafe(32)
        token_hash = TokenManager.hash_refresh_token(raw_token)

        # Store token hash in Redis with TTL from settings
        ttl_seconds = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60
        redis_key = f"pwd_reset:{token_hash}"
        await redis.setex(redis_key, ttl_seconds, str(user.id))

        # Dynamic frontend reset URL from settings/.env
        reset_link = (
            f"{settings.FRONTEND_BASE_URL.rstrip('/')}/auth/reset-password?token={raw_token}"
        )

        # Enqueue transactional outbox email record in PostgreSQL + ARQ
        user_display_name = f"{user.first_name} {user.last_name}".strip() or "there"
        await EmailService.enqueue(
            db=self.db,
            recipient=user.email,
            subject=f"Reset Your Password - {settings.PROJECT_NAME}",
            template_name="password_reset.html",
            template_context={
                "user_name": user_display_name,
                "user_email": user.email,
                "reset_url": reset_link,
                "expire_minutes": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
            },
            tenant_id=None,
        )

    async def reset_password(
        self,
        payload: ResetPasswordRequest,
        redis: Redis,
    ) -> None:
        """Validates token, updates password, and revokes all active sessions."""
        token_hash = TokenManager.hash_refresh_token(payload.token)
        redis_key = f"pwd_reset:{token_hash}"

        user_id_str = await redis.get(redis_key)
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or previously used password reset token.",
            )

        user_uuid = UUID(user_id_str)
        user_query = await self.db.execute(select(User).where(User.id == user_uuid))
        user = user_query.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Update password hash and mark timestamp
        user.hashed_password = PasswordManager.hash_password(payload.new_password)
        user.password_changed_at = datetime.now(UTC)

        # Invalidate all active sessions for this user (force re-login everywhere)
        now = datetime.now(UTC)
        sessions_query = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
        )
        for s in sessions_query.scalars().all():
            s.revoked_at = now

        # Delete the consumed reset token from Redis
        await redis.delete(redis_key)
        await self.db.flush()

    # ---------------------------------------------------------------------------
    # MFA & Dashboard Login Verification (Outbox-Driven)
    # ---------------------------------------------------------------------------
    async def is_email_mfa_enabled(self, user_id: UUID) -> bool:
        """Checks if verified email MFA method is active for user."""
        query = await self.db.execute(
            select(UserMFAMethod.id).where(
                UserMFAMethod.user_id == user_id,
                UserMFAMethod.method_type == MFAMethodType.EMAIL_OTP,
                UserMFAMethod.is_verified.is_(True),
            )
        )
        return query.scalar_one_or_none() is not None

    async def initiate_email_mfa_challenge(
        self,
        user: User,
        tenant_id: UUID | None,
        redis: Redis,
    ) -> MFAChallengeResponse:
        """Generates a 6-digit numeric OTP and enqueues a transactional outbox email."""
        mfa_session_token = secrets.token_urlsafe(32)
        # 6-digit numeric OTP
        otp_code = f"{secrets.randbelow(1_000_000):06d}"

        # Store in Redis: mfa_pending:{token} -> user_id|tenant_id|otp_code|attempts
        redis_key = f"mfa_pending:{mfa_session_token}"
        tenant_str = str(tenant_id) if tenant_id else "none"
        redis_val = f"{user.id}|{tenant_str}|{otp_code}|0"

        # TTL strictly from settings
        await redis.setex(redis_key, settings.MFA_OTP_EXPIRE_SECONDS, redis_val)

        # Enqueue transactional outbox email record in PostgreSQL + ARQ
        user_display_name = f"{user.first_name} {user.last_name}".strip() or "there"
        await EmailService.enqueue(
            db=self.db,
            recipient=user.email,
            subject=f"{otp_code} is your {settings.PROJECT_NAME} verification code",
            template_name="mfa_otp.html",
            template_context={
                "user_name": user_display_name,
                "otp_code": otp_code,
                "expire_minutes": settings.MFA_OTP_EXPIRE_SECONDS // 60,
            },
            tenant_id=tenant_id,
        )

        return MFAChallengeResponse(
            mfa_required=True,
            mfa_token=mfa_session_token,
            method="email_otp",
            masked_email=self._mask_email(user.email),
        )

    async def verify_email_otp_login(
        self,
        payload: VerifyEmailOTPRequest,
        redis: Redis,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSuccessResponse:
        """Verifies the 6-digit OTP and establishes the dashboard session."""
        redis_key = f"mfa_pending:{payload.mfa_token}"
        data = await redis.get(redis_key)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA challenge has expired or is invalid. Please log in again.",
            )

        try:
            user_id_str, tenant_str, expected_otp, attempts_str = data.split("|")
            attempts = int(attempts_str)
        except (ValueError, AttributeError):
            await redis.delete(redis_key)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrupted MFA session. Please log in again.",
            )

        # Guard against brute force (Max 5 attempts)
        if attempts >= 5:
            await redis.delete(redis_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect OTP attempts. Please log in again.",
            )

        # Constant-time comparison
        if not hmac.compare_digest(payload.otp_code.strip(), expected_otp):
            new_val = f"{user_id_str}|{tenant_str}|{expected_otp}|{attempts + 1}"
            ttl = await redis.ttl(redis_key)
            if ttl > 0:
                await redis.setex(redis_key, ttl, new_val)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP verification code.",
            )

        # OTP is valid — remove challenge
        await redis.delete(redis_key)

        user_uuid = UUID(user_id_str)
        active_tenant = UUID(tenant_str) if tenant_str != "none" else None

        user_query = await self.db.execute(select(User).where(User.id == user_uuid))
        user = user_query.scalar_one_or_none()
        if (
            user is None
            or user.status != UserStatus.ACTIVE
            or user.deleted_at is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive, suspended, or deleted.",
            )

        user.last_login_at = datetime.now(UTC)
        tokens = await self._create_user_session(
            user=user,
            tenant_id=active_tenant,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        return AuthSuccessResponse(
            user=UserProfileResponse.model_validate(user),
            tokens=tokens,
            active_tenant_id=active_tenant,
        )

    async def toggle_email_mfa(
        self,
        user: User,
        enable: bool,
        current_password: str,
    ) -> str:
        """Enables or disables Email OTP MFA for the authenticated user."""
        if user.hashed_password is None or not PasswordManager.verify_password(
            current_password, user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password confirmation.",
            )

        query = await self.db.execute(
            select(UserMFAMethod).where(
                UserMFAMethod.user_id == user.id,
                UserMFAMethod.method_type == MFAMethodType.EMAIL_OTP,
            )
        )
        method = query.scalar_one_or_none()

        if enable:
            if not method:
                method = UserMFAMethod(
                    user_id=user.id,
                    method_type=MFAMethodType.EMAIL_OTP,
                    is_verified=True,
                    is_primary=True,
                )
                self.db.add(method)
            else:
                method.is_verified = True
                method.is_primary = True
            await self.db.flush()
            return "Email OTP multi-factor authentication has been enabled."
        else:
            if method:
                await self.db.delete(method)
                await self.db.flush()
            return "Email OTP multi-factor authentication has been disabled."
