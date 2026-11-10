"""Persistence operations for tenant-owned and shared master-data records."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper

from app.core.enums import CommonStatus
from app.core.exceptions import EntityNotFoundException
from app.core.master_data_registry import MasterDataResource
from app.models.base import Base
from app.models.platform_admin_audit import PlatformAdminAudit
from app.models.tenant_membership import TenantMembership
from app.models.user import User


class MasterDataRepository:
    """Runs SQLAlchemy reads and writes with explicit tenant scope."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_records(
        self,
        resource: MasterDataResource,
        *,
        tenant_id: UUID | None,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> list[object]:
        statement = (
            select(resource.model)
            .where(resource.model.deleted_at.is_(None))
            .order_by(resource.model.created_at, resource.model.public_id)
            .limit(limit)
        )
        if resource.scope == "tenant":
            statement = statement.where(resource.model.tenant_id == tenant_id)
        if cursor is not None:
            created_at, public_id = cursor
            statement = statement.where(
                or_(
                    resource.model.created_at > created_at,
                    and_(
                        resource.model.created_at == created_at,
                        resource.model.public_id > public_id,
                    ),
                )
            )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_record(
        self,
        resource: MasterDataResource,
        public_id: UUID,
        *,
        tenant_id: UUID | None,
    ) -> object | None:
        statement = select(resource.model).where(
            resource.model.public_id == public_id,
            resource.model.deleted_at.is_(None),
        )
        if resource.scope == "tenant":
            statement = statement.where(resource.model.tenant_id == tenant_id)
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def create_record(
        self,
        resource: MasterDataResource,
        values: dict[str, object],
        *,
        tenant_id: UUID | None,
        actor_id: UUID,
    ) -> object:
        values = await self._resolve_foreign_keys(resource, values, tenant_id=tenant_id)
        if resource.scope == "tenant":
            values["tenant_id"] = tenant_id
        values["created_by_id"] = actor_id
        record = resource.model(**values)
        self.db.add(record)
        await self.db.flush()
        return record

    async def update_record(
        self,
        resource: MasterDataResource,
        record: object,
        values: dict[str, object],
        *,
        tenant_id: UUID | None,
        actor_id: UUID,
    ) -> object:
        values = await self._resolve_foreign_keys(resource, values, tenant_id=tenant_id)
        for field, value in values.items():
            setattr(record, field, value)
        record.updated_by_id = actor_id
        record.updated_at = datetime.now(UTC)
        await self.db.flush()
        return record

    async def soft_delete_record(
        self,
        record: object,
        *,
        actor_id: UUID,
    ) -> None:
        record.deleted_at = datetime.now(UTC)
        record.deleted_by_id = actor_id
        record.status = CommonStatus.INACTIVE
        await self.db.flush()

    def record_platform_audit(
        self,
        *,
        actor_id: UUID,
        action: str,
        resource_type: str,
        resource_public_id: UUID,
        reason: str,
        before_state: dict[str, object] | None,
        after_state: dict[str, object] | None,
    ) -> None:
        self.db.add(
            PlatformAdminAudit(
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_public_id=resource_public_id,
                reason=reason,
                before_state=before_state,
                after_state=after_state,
            )
        )

    async def serialize_records(
        self,
        resource: MasterDataResource,
        records: list[object],
    ) -> list[dict[str, object]]:
        columns = resource.model.__table__.columns
        referenced_ids: dict[tuple[str, str], set[UUID]] = {}
        for record in records:
            for field in resource.fields:
                column = columns[field]
                for foreign_key in column.foreign_keys:
                    target_table, target_column = foreign_key.target_fullname.split(
                        ".", 1
                    )
                    value = getattr(record, column.name)
                    if isinstance(value, UUID):
                        referenced_ids.setdefault(
                            (target_table, target_column), set()
                        ).add(value)

        reference_values: dict[tuple[str, str], dict[UUID, UUID]] = {}
        for (target_table, target_column), identifiers in referenced_ids.items():
            if target_table == "tenant_memberships" and target_column == "user_id":
                result = await self.db.execute(
                    select(TenantMembership.user_id, User.public_id)
                    .join(User, User.id == TenantMembership.user_id)
                    .where(TenantMembership.user_id.in_(identifiers))
                )
                reference_values[(target_table, target_column)] = dict(result.all())
                continue

            target_mapper = self._mapper_for_table(target_table)
            target_model = target_mapper.class_
            if target_column == "id" and hasattr(target_model, "public_id"):
                result = await self.db.execute(
                    select(target_model.id, target_model.public_id).where(
                        target_model.id.in_(identifiers)
                    )
                )
                reference_values[(target_table, target_column)] = dict(result.all())

        serialized: list[dict[str, object]] = []
        for record in records:
            values: dict[str, object] = {}
            for name in sorted(resource.fields):
                column = columns[name]
                value = getattr(record, name)
                if value is None:
                    values[name] = None
                    continue

                foreign_key = next(iter(column.foreign_keys), None)
                if foreign_key is not None and isinstance(value, UUID):
                    key = tuple(foreign_key.target_fullname.split(".", 1))
                    public_reference_id = reference_values.get(key, {}).get(value)
                    if public_reference_id is None:
                        raise LookupError(
                            f"Unable to resolve public ID for {column.name}."
                        )
                    value = public_reference_id
                if isinstance(value, Enum):
                    value = value.value
                elif isinstance(value, Decimal):
                    value = str(value)
                values[name] = value

            serialized.append(
                {
                    "resource": resource.model.__tablename__,
                    "public_id": record.public_id,
                    "data": values,
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                }
            )
        return serialized

    async def _resolve_foreign_keys(
        self,
        resource: MasterDataResource,
        values: dict[str, object],
        *,
        tenant_id: UUID | None,
    ) -> dict[str, object]:
        resolved = values.copy()
        for column in resource.model.__table__.columns:
            if column.name not in resolved or resolved[column.name] is None:
                continue
            foreign_key = next(iter(column.foreign_keys), None)
            if foreign_key is None:
                continue
            target_table, target_column = foreign_key.target_fullname.split(".", 1)
            public_id = resolved[column.name]
            if not isinstance(public_id, UUID):
                raise TypeError(f"{column.name} must be a public UUID.")

            if target_table == "tenant_memberships" and target_column == "user_id":
                membership = (
                    await self.db.execute(
                        select(TenantMembership)
                        .join(User, User.id == TenantMembership.user_id)
                        .where(
                            TenantMembership.tenant_id == tenant_id,
                            User.public_id == public_id,
                            TenantMembership.deleted_at.is_(None),
                        )
                    )
                ).scalar_one_or_none()
                if membership is None:
                    raise EntityNotFoundException("Tenant user", public_id)
                resolved[column.name] = membership.user_id
                continue

            if target_column != "id":
                continue
            target_model = self._mapper_for_table(target_table).class_
            if not hasattr(target_model, "public_id"):
                continue

            statement = select(target_model.id).where(
                target_model.public_id == public_id,
                target_model.deleted_at.is_(None),
            )
            if hasattr(target_model, "tenant_id"):
                statement = statement.where(target_model.tenant_id == tenant_id)
            target_id = (await self.db.execute(statement)).scalar_one_or_none()
            if target_id is None:
                raise EntityNotFoundException(target_table, public_id)
            resolved[column.name] = target_id
        return resolved

    @staticmethod
    def _mapper_for_table(table_name: str) -> Mapper[object]:
        for mapper in Base.registry.mappers:
            if mapper.local_table.name == table_name:
                return mapper
        raise LookupError(f"No mapped model is registered for table {table_name!r}.")
