"""
Database Models Export
"""

from app.db.models import (
    Base,
    Client,
    Lead,
    Conversation,
    Message,
    KnowledgeBase,
    KnowledgeChunk,
    QualificationRule,
    Escalation,
    UsageLog,
    # Enums
    ClientStatus,
    LeadStatus,
    LeadScore,
    ChannelType,
    MessageRole,
    EscalationReason,
)

from app.db.models_auth import (
    User,
    UserSession,
    AuditLog,
    RateLimitRecord,
    # Enums
    UserRole,
    TokenType,
)

from app.db.session import (
    get_db_session,
    get_db_session,
    get_db_context,
    init_db,
    close_db,
    async_session_factory,
)

__all__ = [
    # Base
    "Base",
    # Core Models
    "Client",
    "Lead",
    "Conversation",
    "Message",
    "KnowledgeBase",
    "KnowledgeChunk",
    "QualificationRule",
    "Escalation",
    "UsageLog",
    # Auth Models
    "User",
    "UserSession",
    "AuditLog",
    "RateLimitRecord",
    # Enums
    "ClientStatus",
    "LeadStatus",
    "LeadScore",
    "ChannelType",
    "MessageRole",
    "EscalationReason",
    "UserRole",
    "TokenType",
    # Session
    "get_db",
    "get_db_session",
    "get_db_context",
    "init_db",
    "close_db",
    "async_session_factory",
]
