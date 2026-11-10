"""Response schemas for permission-filtered navigation menus."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MenuView(BaseModel):
    """One visible menu item with its visible descendants."""

    public_id: UUID
    title: str
    code: str
    path: str | None
    icon: str | None
    sort_order: int
    children: list["MenuView"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
