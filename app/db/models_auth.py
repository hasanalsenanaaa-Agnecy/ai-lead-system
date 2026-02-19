"""
Authentication Models
User accounts, sessions, and security
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models import Base, TimestampMixin, SoftDeleteMixin


# =============================================================================
# Auth Enums
# =============================================================================


class UserRole(str, enum.Enum):
    """User roles for access control."""
    SUPER_ADMIN = "super_admin"  # Platform owner
    ADMIN = "admin"              # Client admin (full access)
    AGENT = "agent"              # Can handle leads/conversations
    VIEWER = "viewer"            # Read-only access


class TokenType(str, enum.Enum):
    """Types of tokens."""
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    TWO_FACTOR = "two_factor"


# =============================================================================
# User Model
# =============================================================================


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    User accounts for dashboard access.
    Users belong to a client (tenant).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=True,  # Null for super_admin
    )

    # Auth
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # Role & Permissions
    role: Mapped[str | None] = mapped_column(
        String(50),
        server_default="agent",
        nullable=True,
    )
    permissions: Mapped[str | None] = mapped_column(Text)  # JSON string of custom permissions

    # Status
    is_active: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    is_verified: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    
    # Email verification
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_token: Mapped[str | None] = mapped_column(String(255))
    verification_token_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Password reset
    password_reset_token: Mapped[str | None] = mapped_column(String(255))
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Two-Factor Authentication
    two_factor_enabled: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    two_factor_secret: Mapped[str | None] = mapped_column(String(255))
    two_factor_backup_codes: Mapped[str | None] = mapped_column(Text)  # JSON array, hashed

    # Session tracking
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(String(45))  # IPv6 length
    login_count: Mapped[int | None] = mapped_column(Integer, server_default="0", nullable=True)
    failed_login_attempts: Mapped[int | None] = mapped_column(Integer, server_default="0", nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Preferences
    timezone: Mapped[str | None] = mapped_column(String(50), server_default="UTC", nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), server_default="en", nullable=True)
    notification_preferences: Mapped[str | None] = mapped_column(Text)  # JSON

    # Relationships
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_client_id", "client_id"),
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until


# =============================================================================
# Session Model
# =============================================================================


class UserSession(Base, TimestampMixin):
    """
    Active user sessions for token management.
    Enables session invalidation and "remember me" functionality.
    """

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Token tracking
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_hash: Mapped[str | None] = mapped_column(String(255))
    
    # Session info
    device_info: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    
    # Expiration
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    remember_me: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    
    # Status
    is_valid: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidation_reason: Mapped[str | None] = mapped_column(String(100))

    # Last activity
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_refresh_token_hash", "refresh_token_hash"),
        Index("ix_user_sessions_is_valid", "is_valid"),
        Index("ix_user_sessions_expires_at", "expires_at"),
    )


# =============================================================================
# Audit Log Model
# =============================================================================


class AuditLog(Base, TimestampMixin):
    """
    Audit trail for security and compliance.
    Tracks who did what, when.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255))
    
    # Change tracking
    old_values: Mapped[str | None] = mapped_column(Text)  # JSON
    new_values: Mapped[str | None] = mapped_column(Text)  # JSON
    
    # Context
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    request_id: Mapped[str | None] = mapped_column(String(100))
    
    # Additional info
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(20), server_default="info", nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_client_id", "client_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_created_at", "created_at"),
    )


# =============================================================================
# Rate Limit Model
# =============================================================================


class RateLimitRecord(Base):
    """
    Rate limiting tracking per IP/user/endpoint.
    """

    __tablename__ = "rate_limit_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Identifier
    key: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "ip:192.168.1.1:login"
    
    # Tracking
    request_count: Mapped[int | None] = mapped_column(Integer, server_default="1", nullable=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Block status
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_rate_limit_key", "key"),
        Index("ix_rate_limit_window", "window_start", "window_end"),
    )
