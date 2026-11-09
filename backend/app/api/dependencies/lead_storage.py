from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.exceptions import EntityConflictException, EntityNotFoundException
from app.schemas.lead import LeadCreate, LeadStatus, LeadUpdate


class LeadRepository:
    
    """In-memory repository for managing leads."""
    _storage: dict[UUID, dict[str, Any]] = {}

    def create(self, payload: LeadCreate) -> dict[str, Any]:
        # Enforce unique email check across leads
        for lead in self._storage.values():
            if lead["email"].lower() == payload.email.lower():
                raise EntityConflictException(
                    message=f"Lead with email '{payload.email}' already exists."
                )

        lead_id = uuid4()
        now = datetime.now(UTC)
        record = {
            "id": lead_id,
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "email": payload.email,
            "company": payload.company,
            "annual_revenue": payload.annual_revenue,
            "status": payload.status,
            "created_at": now,
            "updated_at": now,
        }
        self._storage[lead_id] = record
        return record

    def get_by_id(self, lead_id: UUID) -> dict[str, Any]:
        record = self._storage.get(lead_id)
        if not record:
            raise EntityNotFoundException("Lead", lead_id)
        return record

    def list(
        self,
        skip: int = 0,
        limit: int = 20,
        status: LeadStatus | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        results = list(self._storage.values())
        if status is not None:
            results = [lead for lead in results if lead["status"] == status]
        if search:
            q = search.lower()
            results = [
                lead
                for lead in results
                if q in lead["first_name"].lower()
                or q in lead["last_name"].lower()
                or q in lead["email"].lower()
            ]
        return results[skip : skip + limit]

    def update(self, lead_id: UUID, payload: LeadUpdate) -> dict[str, Any]:
        existing = self.get_by_id(lead_id)  # Will raise EntityNotFoundException if missing

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return existing

        for key, val in update_data.items():
            existing[key] = val

        existing["updated_at"] = datetime.now(UTC)
        self._storage[lead_id] = existing
        return existing

    def delete(self, lead_id: UUID) -> None:
        if lead_id not in self._storage:
            raise EntityNotFoundException("Lead", lead_id)
        del self._storage[lead_id]


def get_lead_repository() -> LeadRepository:
    return LeadRepository()
