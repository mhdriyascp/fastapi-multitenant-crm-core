from uuid import UUID, uuid4

from app.models.menu import Menu, MenuPermission
from app.models.permission import Permission
from app.services.menu_service import MenuService
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _menu(
    *,
    code: str,
    title: str,
    sort_order: int,
    parent_id: UUID | None = None,
    permission_codes: tuple[str, ...] = (),
) -> Menu:
    menu = Menu(
        id=uuid4(),
        public_id=uuid4(),
        parent_id=parent_id,
        title=title,
        code=code,
        path=f"/{code}",
        icon=None,
        sort_order=sort_order,
        is_active=True,
        menu_permissions=[],
    )
    menu.menu_permissions = [
        MenuPermission(
            id=uuid4(),
            menu_id=menu.id,
            permission=Permission(
                id=uuid4(),
                public_id=uuid4(),
                module="test",
                resource="test",
                action="read",
                code=permission_code,
                is_active=True,
            ),
        )
        for permission_code in permission_codes
    ]
    return menu


def test_menu_view_is_authenticated_and_registered_in_tenant_openapi() -> None:
    response = client.get("/api/v1/navigation/menus/")

    assert response.status_code == 401
    paths = client.get("/openapi/v1.json").json()["paths"]
    assert "/api/v1/navigation/menus/" in paths
    assert "get" in paths["/api/v1/navigation/menus/"]


def test_menu_tree_filters_by_effective_permission_and_sorts_siblings() -> None:
    parent = _menu(
        code="crm",
        title="CRM",
        sort_order=10,
        permission_codes=("crm.admin",),
    )
    visible_child = _menu(
        code="leads",
        title="Leads",
        sort_order=20,
        parent_id=parent.id,
        permission_codes=("crm.lead.read",),
    )
    visible_unrestricted_child = _menu(
        code="accounts",
        title="Accounts",
        sort_order=10,
        parent_id=parent.id,
    )
    hidden_child = _menu(
        code="payroll",
        title="Payroll",
        sort_order=1,
        permission_codes=("payroll.read",),
    )
    home = _menu(code="home", title="Home", sort_order=0)

    tree = MenuService.build_menu_tree(
        [parent, visible_child, visible_unrestricted_child, hidden_child, home],
        {"crm.lead.read"},
    )

    assert [item.code for item in tree] == ["home", "crm"]
    assert [item.code for item in tree[1].children] == ["accounts", "leads"]
    assert tree[1].path == "/crm"
    assert "payroll" not in {item.code for item in tree}


def test_wildcard_permission_shows_all_active_menu_definitions() -> None:
    first = _menu(code="first", title="First", sort_order=2, permission_codes=("a",))
    second = _menu(code="second", title="Second", sort_order=1, permission_codes=("b",))

    tree = MenuService.build_menu_tree([first, second], {"*"})

    assert [item.code for item in tree] == ["second", "first"]


def test_menu_with_only_inactive_permission_links_is_not_public() -> None:
    menu = _menu(code="restricted", title="Restricted", sort_order=1)
    permission = Permission(
        id=uuid4(),
        public_id=uuid4(),
        module="test",
        resource="test",
        action="read",
        code="test.read",
        is_active=False,
    )
    menu.menu_permissions = [
        MenuPermission(id=uuid4(), menu_id=menu.id, permission=permission)
    ]

    tree = MenuService.build_menu_tree([menu], set())

    assert tree == []
