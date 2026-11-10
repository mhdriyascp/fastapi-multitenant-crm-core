"""Builds the navigation tree visible to an authenticated user."""

from uuid import UUID

from app.models.menu import Menu
from app.repositories.menu_repository import MenuRepository
from app.schemas.menu import MenuView


class MenuService:
    """Applies effective RBAC permissions and stable hierarchical ordering."""

    def __init__(self, repository: MenuRepository):
        self.repository = repository

    async def list_visible_menus(self, permissions: set[str]) -> list[MenuView]:
        menus = await self.repository.list_active_menus()
        return self.build_menu_tree(menus, permissions)

    @staticmethod
    def build_menu_tree(
        menus: list[Menu],
        permissions: set[str],
    ) -> list[MenuView]:
        menus_by_id = {menu.id: menu for menu in menus}
        children_by_parent: dict[UUID | None, list[Menu]] = {}
        visible_ids: set[UUID] = set()

        for menu in menus:
            children_by_parent.setdefault(menu.parent_id, []).append(menu)
            required_permissions = {
                link.permission.code
                for link in menu.menu_permissions
                if link.permission.is_active
            }
            if (
                not menu.menu_permissions
                or "*" in permissions
                or (required_permissions & permissions)
            ):
                visible_ids.add(menu.id)

        for items in children_by_parent.values():
            items.sort(key=lambda menu: (menu.sort_order, menu.title, menu.code))

        # A visible child keeps its active ancestors as navigation containers.
        for menu_id in tuple(visible_ids):
            parent_id = menus_by_id[menu_id].parent_id
            while parent_id is not None and parent_id in menus_by_id:
                visible_ids.add(parent_id)
                parent_id = menus_by_id[parent_id].parent_id

        def build(parent_id: UUID | None) -> list[MenuView]:
            return [
                MenuView(
                    public_id=menu.public_id,
                    title=menu.title,
                    code=menu.code,
                    path=menu.path,
                    icon=menu.icon,
                    sort_order=menu.sort_order,
                    children=build(menu.id),
                )
                for menu in children_by_parent.get(parent_id, ())
                if menu.id in visible_ids
            ]

        return build(None)
