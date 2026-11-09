import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import INITIAL_PERMISSIONS, SYSTEM_ROLES
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://crm_admin:admin%402k26@localhost:5432/crm_db",
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def seed_permissions(session: AsyncSession) -> dict[str, Permission]:
    """
    Inserts missing permissions or updates existing descriptions idempotently.
    Returns a dictionary mapping permission codes to their Permission ORM instances.
    """
    print("🔹 Synchronizing foundational IAM permissions...")
    permission_cache: dict[str, Permission] = {}

    for module, resource, action, code, description in INITIAL_PERMISSIONS:
        query = select(Permission).where(Permission.code == code)
        result = await session.execute(query)
        perm = result.scalar_one_or_none()

        if not perm:
            perm = Permission(
                module=module,
                resource=resource,
                action=action,
                code=code,
                description=description,
                is_active=True,
            )
            session.add(perm)
            await session.flush()
            print(f"  [+] Created permission: {code}")
        else:
            # Sync description and module metadata if changed
            if perm.description != description or perm.action != action:
                perm.description = description
                perm.action = action
                await session.flush()

        permission_cache[code] = perm

    return permission_cache


async def seed_roles_and_mappings(
    session: AsyncSession,
    permission_cache: dict[str, Permission],
) -> None:
    """
    Inserts system roles and performs complete two-way synchronization:
    - Adds missing permission mappings.
    - Prunes obsolete permission mappings (e.g. revokes permission edits from non-superadmins).
    """
    print("🔹 Synchronizing global system roles and role-permission matrices...")

    for role_def in SYSTEM_ROLES:
        # Global system roles always have tenant_id == None
        query = select(Role).where(
            Role.code == role_def["code"],
            Role.tenant_id.is_(None),
        )
        result = await session.execute(query)
        role = result.scalar_one_or_none()

        if not role:
            role = Role(
                tenant_id=None,
                name=role_def["name"],
                code=role_def["code"],
                description=role_def["description"],
                is_system=role_def["is_system"],
                is_platform=False,
                is_active=True,
            )
            session.add(role)
            await session.flush()
            print(f"  [+] Created system role: {role_def['name']} ({role_def['code']})")
        else:
            # Sync name / description
            role.name = role_def["name"]
            role.description = role_def["description"]
            role.is_platform = False
            await session.flush()

        # Determine target permission IDs for this role
        target_permission_codes = role_def["permissions"]
        if target_permission_codes == ["*"]:
            assigned_perms = list(permission_cache.values())
        else:
            assigned_perms = [
                permission_cache[code]
                for code in target_permission_codes
                if code in permission_cache
            ]

        target_perm_ids = {p.id for p in assigned_perms}

        # 1. Query currently assigned permission IDs in DB
        current_mappings_query = select(RolePermission.permission_id).where(
            RolePermission.role_id == role.id
        )
        current_res = await session.execute(current_mappings_query)
        current_perm_ids = set(current_res.scalars().all())

        # 2. Add missing permissions
        to_add = target_perm_ids - current_perm_ids
        for perm_id in to_add:
            session.add(RolePermission(role_id=role.id, permission_id=perm_id))
            # Reverse-lookup permission code for informative logging
            code = next(c for c, p in permission_cache.items() if p.id == perm_id)
            print(f"    ↳ [+] Linked permission '{code}' to '{role.code}'")

        # 3. Prune obsolete / revoked permissions
        to_remove = current_perm_ids - target_perm_ids
        if to_remove:
            delete_stmt = delete(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id.in_(to_remove),
            )
            await session.execute(delete_stmt)
            for perm_id in to_remove:
                code = next((c for c, p in permission_cache.items() if p.id == perm_id), str(perm_id))
                print(f"    ↳ [-] Revoked permission '{code}' from '{role.code}'")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            perms = await seed_permissions(session)
            await seed_roles_and_mappings(session, perms)
        await session.commit()
    print("✅ RBAC synchronization completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
