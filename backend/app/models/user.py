"""
User & RBAC models.

Role-based access control uses a simple Role enum rather than a fully
dynamic permissions table - sufficient for the platform's five operator
personas while keeping authorization checks O(1) and easy to audit.
Promote to a Role/Permission join table if custom per-tenant roles are
ever required.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    ADMIN = "admin"                  # Full platform control incl. user management
    OPERATIONS_MANAGER = "operations_manager"  # Fleet, maintenance, inventory decisions
    ANALYST = "analyst"              # Read + forecasting/BI access, no write on equipment
    FINANCE = "finance"              # Revenue, pricing, customer profitability
    FIELD_TECHNICIAN = "field_technician"      # Maintenance logs & alerts only
    VIEWER = "viewer"                # Read-only dashboard access


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"), nullable=False, default=UserRole.VIEWER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)

    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted refresh tokens so they can be individually revoked
    (logout / compromised-device response) rather than relying purely
    on short-lived access tokens."""

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Immutable audit trail - required for enterprise compliance.
    No updated_at/soft-delete mixins on purpose: audit rows are append-only."""

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON-serialized detail

    user: Mapped["User"] = relationship(back_populates="audit_logs")
