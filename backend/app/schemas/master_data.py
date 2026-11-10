"""Request and response models for generic master-data endpoints."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MasterDataValue = str | int | float | bool | UUID | date | datetime | None


class MasterDataWriteRequest(BaseModel):
    """Values to create or update on the selected master-data resource."""

    values: dict[str, object] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class PlatformMasterDataWriteRequest(MasterDataWriteRequest):
    """Global catalog mutation request with a required audit reason."""

    reason: str = Field(min_length=8, max_length=500)


class MasterDataRecord(BaseModel):
    """A master-data row with its public identifier and resource-specific fields."""

    resource: str
    public_id: UUID
    data: dict[str, MasterDataValue]
    created_at: datetime
    updated_at: datetime | None


class MasterDataPage(BaseModel):
    """One bounded page of master-data records."""

    items: list[MasterDataRecord]
    next_cursor: str | None
