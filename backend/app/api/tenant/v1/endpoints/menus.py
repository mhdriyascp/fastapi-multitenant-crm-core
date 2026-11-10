"""Tenant API for the authenticated user's visible navigation menus."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthenticatedContext, get_current_context
from app.api.dependencies.database import get_db
from app.repositories.menu_repository import MenuRepository
from app.schemas.menu import MenuView
from app.services.menu_service import MenuService

router = APIRouter()


@router.get(
    "/",
    response_model=list[MenuView],
    summary="List visible navigation menus",
    description=(
        "Returns active menus allowed by the caller's effective RBAC permissions, "
        "ordered by sort_order within each parent."
    ),
)
async def list_visible_menus(
    context: Annotated[AuthenticatedContext, Depends(get_current_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MenuView]:
    return await MenuService(MenuRepository(db)).list_visible_menus(context.permissions)
