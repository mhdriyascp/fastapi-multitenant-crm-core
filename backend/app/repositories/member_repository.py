"""Member and workspace IAM persistence repository.

Handles raw database queries and mutations with explicit tenant scoping,
keeping database concerns separate from business and authorization workflows.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import ROLE_PLATFORM_ADMIN
from app.core.enums import MembershipStatus, RoleAuditAction, UserStatus
from app.models.membership_role import MembershipRole
from app.models.role import Role
from app.models.role_assignment_audit import RoleAssignmentAudit
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.models.user import User


class MemberRepository:
    """Encapsulates all SQLAlchemy persistence operations for tenant memberships."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Loads a tenant workspace by its ID if active and not soft-deleted."""
        query = select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Loads a user account by its internal ID."""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Finds a user account by email address (case-insensitive)."""
        query = select(User).where(User.email == email.lower().strip())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_invited_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """Creates an unverified user record to hold an invited member profile."""
        user = User(
            email=email.lower().strip(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            status=UserStatus.ACTIVE,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_active_membership_by_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> TenantMembership | None:
        """Finds an existing active membership for a user within a specific tenant."""
        query = select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
            TenantMembership.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_membership(
        self,
        tenant_id: UUID,
        user_id: UUID,
        inviter_id: UUID,
    ) -> TenantMembership:
        """Creates a new active tenant membership."""
        membership = TenantMembership(
            tenant_id=tenant_id,
            user_id=user_id,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(UTC),
            invited_by=inviter_id,
            created_by_id=inviter_id,
        )
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def get_membership_by_identifier(
        self,
        tenant_id: UUID,
        membership_identifier: UUID,
    ) -> TenantMembership | None:
        """
        Loads a membership by internal id or public_id, eagerly loading
        user and assigned roles for response assembly.
        """
        query = (
            select(TenantMembership)
            .where(
                TenantMembership.tenant_id == tenant_id,
                (TenantMembership.id == membership_identifier)
                | (TenantMembership.public_id == membership_identifier),
                TenantMembership.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantMembership.user),
                selectinload(TenantMembership.membership_roles).selectinload(
                    MembershipRole.role
                ),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_members(self, tenant_id: UUID) -> list[TenantMembership]:
        """Lists all active members in a tenant workspace with eager-loaded relations."""
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
        return list(result.scalars().all())

    async def list_assignable_roles(self, tenant_id: UUID) -> list[Role]:
        """Lists all global and tenant-specific active roles available for assignment."""
        query = (
            select(Role)
            .where(
                Role.code != ROLE_PLATFORM_ADMIN,
                (Role.tenant_id.is_(None)) | (Role.tenant_id == tenant_id),
                Role.is_active.is_(True),
                Role.deleted_at.is_(None),
            )
            .order_by(Role.is_system.desc(), Role.name.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_roles_by_codes(
        self,
        tenant_id: UUID,
        role_codes: list[str],
    ) -> list[Role]:
        """Resolves a list of role codes against assignable workspace roles."""
        query = select(Role).where(
            Role.code.in_(role_codes),
            Role.code != ROLE_PLATFORM_ADMIN,
            (Role.tenant_id.is_(None)) | (Role.tenant_id == tenant_id),
            Role.is_active.is_(True),
            Role.deleted_at.is_(None),
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    def add_membership_role(
        self,
        membership_id: UUID,
        role_id: UUID,
        assigned_by: UUID,
    ) -> MembershipRole:
        """Associates a role with a tenant membership."""
        membership_role = MembershipRole(
            membership_id=membership_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        self.db.add(membership_role)
        return membership_role

    async def delete_membership_role(self, membership_role: MembershipRole) -> None:
        """Removes a role assignment from a membership."""
        await self.db.delete(membership_role)

    def record_role_audit(
        self,
        membership_id: UUID,
        role_id: UUID,
        action: RoleAuditAction,
        performed_by: UUID,
        reason: str,
    ) -> RoleAssignmentAudit:
        """Creates an immutable audit trail record for role changes."""
        audit = RoleAssignmentAudit(
            membership_id=membership_id,
            role_id=role_id,
            action=action,
            performed_by=performed_by,
            reason=reason,
        )
        self.db.add(audit)
        return audit

    async def soft_delete_membership(
        self,
        membership: TenantMembership,
        actor_id: UUID,
    ) -> None:
        """Soft-deletes a membership record and updates its lifecycle status."""
        membership.deleted_at = datetime.now(UTC)
        membership.deleted_by_id = actor_id
        membership.status = getattr(
            MembershipStatus, "REVOKED", MembershipStatus.SUSPENDED
        )
        await self.db.flush()

