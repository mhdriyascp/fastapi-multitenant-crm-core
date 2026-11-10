"""Business rules for tenant-owned and shared master-data APIs."""

import base64
import binascii
from datetime import datetime
from uuid import UUID

from app.core.enums import CommonStatus
from app.core.exceptions import (
    BusinessRuleViolationException,
    EntityConflictException,
    EntityNotFoundException,
    PermissionDeniedException,
)
from app.core.master_data_registry import MASTER_DATA_RESOURCES, MasterDataResource
from app.repositories.master_data_repository import MasterDataRepository
from app.schemas.master_data import MasterDataPage, MasterDataRecord
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class MasterDataService:
    """Validates master-data changes and coordinates repository transactions."""

    def __init__(self, db: AsyncSession):
        self.repository = MasterDataRepository(db)

    async def list_records(
        self,
        resource_name: str,
        *,
        tenant_id: UUID | None,
        limit: int,
        cursor: str | None,
    ) -> MasterDataPage:
        resource = self._get_resource(resource_name)
        self._require_scope(resource, tenant_id)
        decoded_cursor = self._decode_cursor(cursor) if cursor is not None else None
        records = await self.repository.list_records(
            resource,
            tenant_id=tenant_id,
            limit=limit + 1,
            cursor=decoded_cursor,
        )
        has_more = len(records) > limit
        records = records[:limit]
        serialized = await self.repository.serialize_records(resource, records)
        return MasterDataPage(
            items=[MasterDataRecord.model_validate(record) for record in serialized],
            next_cursor=(
                self._encode_cursor(records[-1].created_at, records[-1].public_id)
                if has_more and records
                else None
            ),
        )

    async def get_record(
        self,
        resource_name: str,
        public_id: UUID,
        *,
        tenant_id: UUID | None,
    ) -> MasterDataRecord:
        resource = self._get_resource(resource_name)
        self._require_scope(resource, tenant_id)
        record = await self.repository.get_record(
            resource,
            public_id,
            tenant_id=tenant_id,
        )
        if record is None:
            raise EntityNotFoundException(resource.model.__tablename__, public_id)
        serialized = await self.repository.serialize_records(resource, [record])
        return MasterDataRecord.model_validate(serialized[0])

    async def create_record(
        self,
        resource_name: str,
        values: dict[str, object],
        *,
        tenant_id: UUID | None,
        actor_id: UUID,
        reason: str | None = None,
    ) -> MasterDataRecord:
        resource = self._get_resource(resource_name)
        self._require_scope(resource, tenant_id)
        reason = self._audit_reason(resource, reason)
        normalized = self._validate_values(resource, values, creating=True)
        try:
            record = await self.repository.create_record(
                resource,
                normalized,
                tenant_id=tenant_id,
                actor_id=actor_id,
            )
        except IntegrityError as exc:
            raise EntityConflictException(
                "The master-data record conflicts with an existing record or reference."
            ) from exc
        serialized = await self.repository.serialize_records(resource, [record])
        response = MasterDataRecord.model_validate(serialized[0])
        if reason is not None:
            self.repository.record_platform_audit(
                actor_id=actor_id,
                action=f"platform.{resource.permission_prefix}.created",
                resource_type=resource.model.__tablename__,
                resource_public_id=response.public_id,
                reason=reason,
                before_state=None,
                after_state=response.model_dump(mode="json"),
            )
        return response

    async def update_record(
        self,
        resource_name: str,
        public_id: UUID,
        values: dict[str, object],
        *,
        tenant_id: UUID | None,
        actor_id: UUID,
        reason: str | None = None,
    ) -> MasterDataRecord:
        resource = self._get_resource(resource_name)
        self._require_scope(resource, tenant_id)
        reason = self._audit_reason(resource, reason)
        normalized = self._validate_values(resource, values, creating=False)
        record = await self.repository.get_record(
            resource,
            public_id,
            tenant_id=tenant_id,
        )
        if record is None:
            raise EntityNotFoundException(resource.model.__tablename__, public_id)
        previous = await self.repository.serialize_records(resource, [record])
        before_state = MasterDataRecord.model_validate(previous[0]).model_dump(
            mode="json"
        )
        try:
            record = await self.repository.update_record(
                resource,
                record,
                normalized,
                tenant_id=tenant_id,
                actor_id=actor_id,
            )
        except IntegrityError as exc:
            raise EntityConflictException(
                "The master-data update conflicts with an existing record or reference."
            ) from exc
        serialized = await self.repository.serialize_records(resource, [record])
        response = MasterDataRecord.model_validate(serialized[0])
        if reason is not None:
            self.repository.record_platform_audit(
                actor_id=actor_id,
                action=f"platform.{resource.permission_prefix}.updated",
                resource_type=resource.model.__tablename__,
                resource_public_id=response.public_id,
                reason=reason,
                before_state=before_state,
                after_state=response.model_dump(mode="json"),
            )
        return response

    async def delete_record(
        self,
        resource_name: str,
        public_id: UUID,
        *,
        tenant_id: UUID | None,
        actor_id: UUID,
        reason: str | None = None,
    ) -> None:
        resource = self._get_resource(resource_name)
        self._require_scope(resource, tenant_id)
        reason = self._audit_reason(resource, reason)
        record = await self.repository.get_record(
            resource,
            public_id,
            tenant_id=tenant_id,
        )
        if record is None:
            raise EntityNotFoundException(resource.model.__tablename__, public_id)
        previous = await self.repository.serialize_records(resource, [record])
        before_state = MasterDataRecord.model_validate(previous[0]).model_dump(
            mode="json"
        )
        try:
            await self.repository.soft_delete_record(record, actor_id=actor_id)
        except IntegrityError as exc:
            raise EntityConflictException(
                "The master-data record is referenced by another record."
            ) from exc
        if reason is not None:
            after = await self.repository.serialize_records(resource, [record])
            self.repository.record_platform_audit(
                actor_id=actor_id,
                action=f"platform.{resource.permission_prefix}.soft_deleted",
                resource_type=resource.model.__tablename__,
                resource_public_id=record.public_id,
                reason=reason,
                before_state=before_state,
                after_state=MasterDataRecord.model_validate(after[0]).model_dump(
                    mode="json"
                ),
            )

    @staticmethod
    def _get_resource(resource_name: str) -> MasterDataResource:
        resource = MASTER_DATA_RESOURCES.get(resource_name)
        if resource is None:
            raise EntityNotFoundException("Master-data resource", resource_name)
        return resource

    @staticmethod
    def _require_scope(
        resource: MasterDataResource,
        tenant_id: UUID | None,
    ) -> None:
        if resource.scope == "tenant" and tenant_id is None:
            raise PermissionDeniedException(
                "A tenant context is required for this master-data resource."
            )

    @staticmethod
    def _audit_reason(
        resource: MasterDataResource,
        reason: str | None,
    ) -> str | None:
        if resource.scope != "shared":
            return None
        normalized = reason.strip() if reason else ""
        if len(normalized) < 8:
            raise BusinessRuleViolationException(
                "A reason of at least 8 characters is required for global catalog changes."
            )
        return normalized

    @staticmethod
    def _validate_values(
        resource: MasterDataResource,
        values: dict[str, object],
        *,
        creating: bool,
    ) -> dict[str, object]:
        model = resource.model
        columns = model.__table__.columns
        writable_columns = {field: columns[field] for field in resource.fields}
        unknown = set(values) - writable_columns.keys()
        if unknown:
            raise BusinessRuleViolationException(
                f"Unsupported fields for {model.__tablename__}: {', '.join(sorted(unknown))}."
            )
        if creating:
            missing = {
                column.name
                for column in writable_columns.values()
                if not column.nullable
                and column.default is None
                and column.server_default is None
                and column.name not in values
            }
            if missing:
                raise BusinessRuleViolationException(
                    f"Missing required fields for {model.__tablename__}: "
                    f"{', '.join(sorted(missing))}."
                )

        normalized: dict[str, object] = {}
        for field, value in values.items():
            column = writable_columns[field]
            if value is None:
                if not column.nullable:
                    raise BusinessRuleViolationException(f"{field} cannot be null.")
                normalized[field] = None
                continue
            try:
                expected_type = column.type.python_type
                validated_value = TypeAdapter(expected_type).validate_python(value)
            except (TypeError, ValueError, ValidationError, NotImplementedError) as exc:
                raise BusinessRuleViolationException(
                    f"Invalid value for {field}."
                ) from exc
            max_length = getattr(column.type, "length", None)
            if (
                isinstance(validated_value, str)
                and max_length is not None
                and len(validated_value) > max_length
            ):
                raise BusinessRuleViolationException(
                    f"{field} exceeds the maximum length of {max_length}."
                )
            normalized[field] = validated_value

        if "status" in normalized and not isinstance(
            normalized["status"], CommonStatus
        ):
            raise BusinessRuleViolationException("status must be active or inactive.")
        return normalized

    @staticmethod
    def _encode_cursor(created_at: datetime, public_id: UUID) -> str:
        payload = f"{created_at.isoformat()}\n{public_id}".encode()
        return base64.urlsafe_b64encode(payload).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
        if not cursor or len(cursor) > 256:
            raise BusinessRuleViolationException("Invalid pagination cursor.")
        try:
            padded_cursor = cursor + "=" * (-len(cursor) % 4)
            payload = base64.b64decode(
                padded_cursor,
                altchars=b"-_",
                validate=True,
            ).decode()
            created_at_value, public_id_value = payload.split("\n", maxsplit=1)
            created_at = datetime.fromisoformat(created_at_value)
            public_id = UUID(public_id_value)
            if created_at.tzinfo is None:
                raise ValueError("Cursor timestamp must include a timezone.")
        except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
            raise BusinessRuleViolationException("Invalid pagination cursor.") from exc
        return created_at, public_id
