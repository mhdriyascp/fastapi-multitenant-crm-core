from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils.compat import uuid7

from app.models.base import AuditableLifecycleBase

if TYPE_CHECKING:
    from app.models.identity_master import TeamMember


class MasterDataBase(AuditableLifecycleBase):
    """Shared identifiers and lifecycle fields for master data records."""

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    public_id: Mapped[UUID] = mapped_column(
        unique=True, index=True, default=uuid4, nullable=False
    )


class TenantMasterData(MasterDataBase):
    """Base for tenant-owned master data."""

    __abstract__ = True

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )


class Organization(TenantMasterData):
    """An operating organization within a SaaS tenant."""

    __tablename__ = "organizations"
    __table_args__ = (
        Index(
            "uq_organizations_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(30))
    website: Mapped[str | None] = mapped_column(String(255))
    country_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT")
    )
    default_currency_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("currencies.id", ondelete="RESTRICT")
    )
    timezone_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("time_zones.id", ondelete="RESTRICT")
    )


class LegalEntity(TenantMasterData):
    """A legally registered entity belonging to an organization."""

    __tablename__ = "legal_entities"
    __table_args__ = (
        Index(
            "uq_legal_entities_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    tax_identifier: Mapped[str | None] = mapped_column(String(100))
    country_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT")
    )
    default_currency_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("currencies.id", ondelete="RESTRICT")
    )


class Branch(TenantMasterData):
    """A branch or office belonging to an organization."""

    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_branches_tenant_id_id"),
        Index(
            "uq_branches_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    legal_entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("legal_entities.id", ondelete="RESTRICT"), index=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    parent_branch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class Department(TenantMasterData):
    """An organization department, optionally nested under another department."""

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_departments_tenant_id_id"),
        Index(
            "uq_departments_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    parent_department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Designation(TenantMasterData):
    """A job position or grade that can be assigned within a tenant."""

    __tablename__ = "designations"
    __table_args__ = (
        Index(
            "uq_designations_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)


class Team(TenantMasterData):
    """A functional team within an organization."""

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_teams_tenant_id_id"),
        Index(
            "uq_teams_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), index=True
    )
    parent_team_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )


class Location(TenantMasterData):
    """A physical or operational location owned by a tenant."""

    __tablename__ = "locations"
    __table_args__ = (
        Index(
            "uq_locations_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address_line_1: Mapped[str | None] = mapped_column(String(255))
    address_line_2: Mapped[str | None] = mapped_column(String(255))
    country_id: Mapped[UUID] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="RESTRICT"), index=True
    )
    city_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cities.id", ondelete="RESTRICT"), index=True
    )
    postal_code: Mapped[str | None] = mapped_column(String(30))
    timezone_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("time_zones.id", ondelete="RESTRICT")
    )


class BusinessUnit(TenantMasterData):
    """A business division within an organization."""

    __tablename__ = "business_units"
    __table_args__ = (
        Index(
            "uq_business_units_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    parent_business_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_units.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class CostCenter(TenantMasterData):
    """A financial cost-allocation unit within an organization."""

    __tablename__ = "cost_centers"
    __table_args__ = (
        Index(
            "uq_cost_centers_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    business_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_units.id", ondelete="RESTRICT"), index=True
    )
    default_currency_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("currencies.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class FiscalYear(TenantMasterData):
    """A named financial year for an organization."""

    __tablename__ = "fiscal_years"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_fiscal_years_tenant_id_id"),
        CheckConstraint("ends_on >= starts_on", name="ck_fiscal_year_dates"),
        Index(
            "uq_fiscal_years_tenant_code_active",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)


class Currency(MasterDataBase):
    """A shared currency reference based on an ISO 4217 code."""

    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(10))
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    __table_args__ = (
        CheckConstraint(
            "decimal_places >= 0 AND decimal_places <= 6",
            name="ck_currencies_decimal_places",
        ),
        Index(
            "uq_currencies_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Country(MasterDataBase):
    """A shared country reference based on ISO 3166 codes."""

    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(String(2), nullable=False)
    alpha3_code: Mapped[str | None] = mapped_column(String(3))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    calling_code: Mapped[str | None] = mapped_column(String(10))

    __table_args__ = (
        Index(
            "uq_countries_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_countries_alpha3_active",
            "alpha3_code",
            unique=True,
            postgresql_where=text("alpha3_code IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class State(MasterDataBase):
    """A state, province, or equivalent first-level administrative area."""

    __tablename__ = "states"

    country_id: Mapped[UUID] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (
        Index(
            "uq_states_country_code_active",
            "country_id",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class City(MasterDataBase):
    """A city or locality within a country and optional state."""

    __tablename__ = "cities"

    country_id: Mapped[UUID] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str | None] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(150), nullable=False)


class TimeZone(MasterDataBase):
    """A shared IANA time-zone identifier."""

    __tablename__ = "time_zones"

    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    __table_args__ = (
        Index(
            "uq_time_zones_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Language(MasterDataBase):
    """A shared language or locale reference."""

    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(35), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        Index(
            "uq_languages_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class UnitOfMeasure(MasterDataBase):
    """A shared unit-of-measure reference."""

    __tablename__ = "units_of_measure"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(30))
    dimension: Mapped[str | None] = mapped_column(String(50))

    __table_args__ = (
        Index(
            "uq_units_of_measure_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class TaxType(MasterDataBase):
    """A shared tax classification such as VAT, GST, or sales tax."""

    __tablename__ = "tax_types"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index(
            "uq_tax_types_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class TaxRate(TenantMasterData):
    """A tenant-specific tax rate with a defined jurisdiction and effective date."""

    __tablename__ = "tax_rates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_tax_rates_tenant_id_id"),
        CheckConstraint("rate >= 0 AND rate <= 100", name="ck_tax_rates_rate_percent"),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_tax_rates_effective_dates",
        ),
        Index(
            "uq_tax_rates_tenant_code_start_active",
            "tenant_id",
            "code",
            "valid_from",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    legal_entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("legal_entities.id", ondelete="RESTRICT"), index=True
    )
    tax_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("tax_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    country_id: Mapped[UUID] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    state_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("states.id", ondelete="RESTRICT"), index=True
    )
    city_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cities.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
