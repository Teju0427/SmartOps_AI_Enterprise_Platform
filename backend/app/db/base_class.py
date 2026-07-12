"""
Declarative base and common mixins shared by every ORM model.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr

# Naming convention keeps Alembic-generated constraint names deterministic
# across environments (dev / test / prod) - important for autogenerate diffs.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        # CamelCase -> snake_case, e.g. MaintenanceLog -> maintenance_log
        import re
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return name


class UUIDPrimaryKeyMixin:
    """Every table uses a UUID primary key - avoids sequential-ID enumeration
    attacks on a public API and simplifies multi-region / offline-sync scenarios."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )


class TimestampMixin:
    """created_at / updated_at columns, always stored in UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft-delete support - required for audit trail compliance in
    industrial/enterprise settings where hard deletes are rarely permitted."""

    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
