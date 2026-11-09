from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.constants import ROLE_PLATFORM_ADMIN
from app.core.email import EmailService
from app.core.enums import MembershipStatus, RoleAuditAction, UserStatus
from app.core.exceptions import (
    BusinessRuleViolationException,
    EntityConflictException,
    EntityNotFoundException,
)
from app.models.membership_role import MembershipRole
from app.models.role import Role
from app.models.role_assignment_audit import RoleAssignmentAudit
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.schemas.member import (
    InviteMemberRequest,
    MemberResponse,
    MemberUserSummary,
    RoleSummary,
    UpdateMemberRolesRequest,
)


class MemberService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_members(self, tenant_id: UUID) -> list[MemberResponse]:
        """Lists all active members in the specified tenant workspace."""
        query = (
            select(TenantMembership)
            .where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantMembership.user),
                selectinload(TenantMembership.membership_roles).selectinload(
                    MembershipRole.role
                ),
            )
            .order_by(TenantMembership.created_at.asc())
        )
        result = await self.db.execute(query)
        memberships = result.scalars().all()

        output: list[MemberResponse] = []
        for m in memberships:
            if not m.user:
                continue

            roles = [
                RoleSummary(id=mr.role.id, code=mr.role.code, name=mr.role.name)
                for mr in m.membership_roles
                if mr.role and mr.role.is_active and not mr.role.deleted_at
            ]

            output.append(
                MemberResponse(
                    membership_id=m.id,
                    status=m.status,
                    joined_at=m.joined_at,
                    user=MemberUserSummary(
                        id=m.user.id,
                        public_id=m.user.public_id,
                        email=m.user.email,
                        first_name=m.user.first_name,
                        last_name=m.user.last_name,
                    ),
                    roles=roles,
                )
            )

        return output

    async def invite_member(
        self,
        tenant_id: UUID,
        inviter_id: UUID,
        payload: InviteMemberRequest,
    ) -> MemberResponse:
        """
        Invites or associates a user with the tenant and assigns initial roles.
        Audits every role assignment in role_assignment_audits and enqueues an invitation email.
        """
        # 1. Resolve Tenant
        tenant_query = await self.db.execute(
            select(Tenant).where(
                Tenant.id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
        )
        tenant = tenant_query.scalar_one_or_none()
        if not tenant:
            raise EntityNotFoundException("Tenant", tenant_id)

        # 2. Resolve Inviter details (for email display)
        inviter_query = await self.db.execute(
            select(User).where(User.id == inviter_id)
        )
        inviter = inviter_query.scalar_one_or_none()
        inviter_name = (
            f"{inviter.first_name} {inviter.last_name}".strip()
            if inviter
            else "A team administrator"
        )

        # 3. Resolve or create target user account
        user_query = await self.db.execute(
            select(User).where(User.email == payload.email.lower().strip())
        )
        user = user_query.scalar_one_or_none()

        if not user:
            # User invited before setting password (invite/OAuth flow)
            user = User(
                email=payload.email.lower().strip(),
                first_name=payload.first_name.strip(),
                last_name=payload.last_name.strip(),
                status=UserStatus.ACTIVE,
                is_verified=False,
            )
            self.db.add(user)
            await self.db.flush()

        # 4. Check if already an active member of this tenant
        existing_membership = await self.db.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user.id,
                TenantMembership.deleted_at.is_(None),
            )
        )
        if existing_membership.scalar_one_or_none():
            raise EntityConflictException("User is already a member of this workspace.")

        # 5. Create TenantMembership
        membership = TenantMembership(
            tenant_id=tenant_id,
            user_id=user.id,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(UTC),
            invited_by=inviter_id,
            created_by_id=inviter_id,
        )
        self.db.add(membership)
        await self.db.flush()

        # 6. Resolve & assign roles (disallowing platform_admin at tenant scope)
        roles_query = await self.db.execute(
            select(Role).where(
                Role.code.in_(payload.role_codes),
                Role.code != ROLE_PLATFORM_ADMIN,
                (Role.tenant_id.is_(None)) | (Role.tenant_id == tenant_id),
                Role.is_active.is_(True),
            )
        )
        roles = roles_query.scalars().all()

        if not roles:
            raise BusinessRuleViolationException(
                f"None of the specified roles {payload.role_codes} are valid for this workspace."
            )

        assigned_role_summaries: list[RoleSummary] = []
        role_display_names: list[str] = []
        for role in roles:
            mr = MembershipRole(
                membership_id=membership.id,
                role_id=role.id,
                assigned_by=inviter_id,
            )
            self.db.add(mr)

            # Audit record (SOC2/ISO compliance)
            audit = RoleAssignmentAudit(
                membership_id=membership.id,
                role_id=role.id,
                action=RoleAuditAction.ASSIGNED,
                performed_by=inviter_id,
                reason="Initial workspace invitation",
            )
            self.db.add(audit)

            assigned_role_summaries.append(
                RoleSummary(id=role.id, code=role.code, name=role.name)
            )
            role_display_names.append(role.name)

        await self.db.flush()

        # 7. Enqueue Transactional Outbox Email
        invite_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/auth/login"
        invitee_display_name = (
            f"{user.first_name} {user.last_name}".strip() or "there"
        )

        await EmailService.enqueue(
            db=self.db,
            recipient=user.email,
            subject=f"Invitation to join {tenant.name} on {settings.PROJECT_NAME}",
            template_name="workspace_invitation.html",
            template_context={
                "invitee_name": invitee_display_name,
                "inviter_name": inviter_name,
                "tenant_name": tenant.name,
                "roles": role_display_names,
                "invite_url": invite_url,
            },
            tenant_id=tenant.id,
        )

        return MemberResponse(
            membership_id=membership.id,
            status=membership.status,
            joined_at=membership.joined_at,
            user=MemberUserSummary(
                id=user.id,
                public_id=user.public_id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
            ),
            roles=assigned_role_summaries,
        )

    async def remove_member(
        self,
        tenant_id: UUID,
        membership_id: UUID,
        actor_id: UUID,
    ) -> None:
        """Removes a member from the workspace (soft-delete)."""
        membership_query = await self.db.execute(
            select(TenantMembership).where(
                TenantMembership.id == membership_id,
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.deleted_at.is_(None),
            )
        )
        membership = membership_query.scalar_one_or_none()

        if not membership:
            raise EntityNotFoundException("TenantMembership", membership_id)

        if membership.user_id == actor_id:
            raise BusinessRuleViolationException("You cannot remove yourself from the workspace.")

        now = datetime.now(UTC)
        membership.deleted_at = now
        membership.deleted_by_id = actor_id
        # Use REVOKED or fallback to REMOVED
        membership.status = getattr(
            MembershipStatus, "REVOKED", MembershipStatus.SUSPENDED
        )
        await self.db.flush()

    async def list_assignable_roles(self, tenant_id: UUID) -> list[RoleSummary]:
        """Lists roles that can be assigned within the tenant workspace."""
        query = (
            select(Role)
            .where(
                Role.code != ROLE_PLATFORM_ADMIN,  # Platform admin cannot be assigned at tenant scope
                (Role.tenant_id.is_(None)) | (Role.tenant_id == tenant_id),
                Role.is_active.is_(True),
                Role.deleted_at.is_(None),
            )
            .order_by(Role.is_system.desc(), Role.name.asc())
        )
        result = await self.db.execute(query)
        roles = result.scalars().all()
        return [RoleSummary(id=r.id, code=r.code, name=r.name) for r in roles]

    async def update_member_roles(
        self,
        tenant_id: UUID,
        membership_id: UUID,
        actor_id: UUID,
        payload: UpdateMemberRolesRequest,
    ) -> MemberResponse:
        """
        Replaces a member's assigned roles with a new set of role codes.
        Records audit logs for revoked and newly assigned roles.
        """
        # 1. Fetch membership
        query = (
            select(TenantMembership)
            .where(
                TenantMembership.id == membership_id,
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.status == MembershipStatus.ACTIVE,
                TenantMembership.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantMembership.user),
                selectinload(TenantMembership.membership_roles).selectinload(
                    MembershipRole.role
                ),
            )
        )
        membership = (await self.db.execute(query)).scalar_one_or_none()
        if not membership:
            raise EntityNotFoundException("TenantMembership", membership_id)

        # 2. Prevent self-demotion/promotion if modifying own membership
        if membership.user_id == actor_id:
            raise BusinessRuleViolationException("You cannot modify your own roles.")

        # 3. Resolve target roles
        roles_query = await self.db.execute(
            select(Role).where(
                Role.code.in_(payload.role_codes),
                Role.code != ROLE_PLATFORM_ADMIN,
                (Role.tenant_id.is_(None)) | (Role.tenant_id == tenant_id),
                Role.is_active.is_(True),
            )
        )
        new_roles = {r.code: r for r in roles_query.scalars().all()}
        missing_codes = set(payload.role_codes) - set(new_roles.keys())
        if missing_codes:
            raise BusinessRuleViolationException(f"Invalid or inactive role codes: {list(missing_codes)}")

        current_role_codes = {
            mr.role.code: mr for mr in membership.membership_roles if mr.role
        }

        # 4. Determine roles to add and remove
        to_add = set(new_roles.keys()) - set(current_role_codes.keys())
        to_remove = set(current_role_codes.keys()) - set(new_roles.keys())

        # Process removals
        for code in to_remove:
            mr = current_role_codes[code]
            await self.db.delete(mr)
            audit = RoleAssignmentAudit(
                membership_id=membership.id,
                role_id=mr.role_id,
                action=RoleAuditAction.REVOKED,
                performed_by=actor_id,
                reason="Role updated via member administration",
            )
            self.db.add(audit)

        # Process additions
        for code in to_add:
            role = new_roles[code]
            mr = MembershipRole(
                membership_id=membership.id,
                role_id=role.id,
                assigned_by=actor_id,
            )
            self.db.add(mr)
            audit = RoleAssignmentAudit(
                membership_id=membership.id,
                role_id=role.id,
                action=RoleAuditAction.ASSIGNED,
                performed_by=actor_id,
                reason="Role updated via member administration",
            )
            self.db.add(audit)

        await self.db.flush()

        # 5. Return updated representation
        return MemberResponse(
            membership_id=membership.id,
            status=membership.status,
            joined_at=membership.joined_at,
            user=MemberUserSummary(
                id=membership.user.id,
                public_id=membership.user.public_id,
                email=membership.user.email,
                first_name=membership.user.first_name,
                last_name=membership.user.last_name,
            ),
            roles=[
                RoleSummary(id=r.id, code=r.code, name=r.name)
                for r in new_roles.values()
            ],
        )
