"""Persistence operations for configured navigation menus."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.menu import Menu, MenuPermission


class MenuRepository:
    """Loads active menu definitions and their RBAC permission links."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active_menus(self) -> list[Menu]:
        statement = (
            select(Menu)
            .where(Menu.is_active.is_(True))
            .options(
                selectinload(Menu.menu_permissions).selectinload(
                    MenuPermission.permission
                )
            )
            .order_by(Menu.sort_order, Menu.title, Menu.code, Menu.id)
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())
