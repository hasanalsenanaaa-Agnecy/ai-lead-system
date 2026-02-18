"""
Database Models
Multi-tenant architecture with row-level security support
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    type_annotation_map = {
        dict[str, Any]: JSON,
        list[str]: ARRAY(String),
    }


# =============================================================================
# Enums
# =============================================================================


class ClientStatus(str, enum.Enum):
    """Client account status."""

    ACTIVE = "active"
    PAUSED = "paused"
    ONBOARDING = "onboarding"
    CHURNED = "churned"


class LeadStatus(str, enum.Enum):
    """Lead qualification status."""

    NEW = "new"
    QUALIFYING = "qualifying"
    QUALIFIED = "qualified"
    APPOINTMENT_BOOKED = "appointment_booked"
    HANDED_OFF = "handed_off"
    NURTURING = "nurturing"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    DISQUALIFIED = "disqualified"


class LeadScore(str, enum.Enum):
    """Lead temperature/priority."""

    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    UNSCORED = "unscored"


class ChannelType(str, enum.Enum):
    """Communication channel types."""

    WEB_FORM = "web_form"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    LIVE_CHAT = "live_chat"
    EMAIL = "email"
    MISSED_CALL = "missed_call"


class MessageRole(str, enum.Enum):
    """Message sender role."""

    LEAD = "lead"
    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"


class EscalationReason(str, enum.Enum):
    """Reasons for human escalation."""

    LEAD_REQUEST = "lead_request"
    LOW_CONFIDENCE = "low_confidence"
    HIGH_VALUE = "high_value"
    LONG_CONVERSATION = "long_conversation"
    NEGATIVE_SENTIMENT = "negative_sentiment"
    AGENT_ERROR = "agent_error"


# =============================================================================
# Mixin Classes
# =============================================================================


class TimestampMixin:
    """Adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft delete capability."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# =============================================================================
# Core Models
# =============================================================================


class Client(Base, TimestampMixin, SoftDeleteMixin):
    """
    Client/tenant in the system.
    Each client is a business using the AI lead system.
    """

    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus),
        default=ClientStatus.ONBOARDING,
        nullable=False,
    )

    # Business Info
    industry: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(500))
    timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")
    primary_language: Mapped[str] = mapped_column(String(10), default="en")

    # Contact
    owner_name: Mapped[str | None] = mapped_column(String(255))
    owner_email: Mapped[str | None] = mapped_column(String(255))
    owner_phone: Mapped[str | None] = mapped_column(String(50))

    # Configuration
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Billing
    plan: Mapped[str] = mapped_column(String(50), default="growth")
    monthly_token_budget: Mapped[int] = mapped_column(Integer, default=1_000_000)
    tokens_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    billing_cycle_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # API Access
    api_key_hash: Mapped[str | None] = mapped_column(String(255))
    webhook_secret_hash: Mapped[str | None] = mapped_column(String(255))

    # Relationships
    leads: Mapped[list["Lead"]] = relationship(back_populates="client", lazy="dynamic")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="client", lazy="dynamic"
    )
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(
        back_populates="client", lazy="dynamic"
    )
    qualification_rules: Mapped[list["QualificationRule"]] = relationship(
        back_populates="client", lazy="dynamic"
    )



class Lead(Base, TimestampMixin, SoftDeleteMixin):
    """
    Lead/prospect record.
    Represents a potential customer engaging with the AI system.
    """

    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Contact Info
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))

    # Source & Channel
    source_channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType),
        nullable=False,
    )
    source_campaign: Mapped[str | None] = mapped_column(String(255))
    source_medium: Mapped[str | None] = mapped_column(String(100))
    landing_page: Mapped[str | None] = mapped_column(String(500))

    # Qualification
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus),
        default=LeadStatus.NEW,
        nullable=False,
    )
    score: Mapped[LeadScore] = mapped_column(
        Enum(LeadScore),
        default=LeadScore.UNSCORED,
        nullable=False,
    )
    score_value: Mapped[int] = mapped_column(Integer, default=0)
    qualification_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Service Interest
    service_interest: Mapped[str | None] = mapped_column(String(255))
    urgency: Mapped[str | None] = mapped_column(String(50))
    budget_range: Mapped[str | None] = mapped_column(String(100))
    preferred_contact_time: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))

    # Appointment
    appointment_scheduled: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    appointment_type: Mapped[str | None] = mapped_column(String(100))

    # Assignment
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    handed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # External IDs
    external_crm_id: Mapped[str | None] = mapped_column(String(255))
    external_contact_id: Mapped[str | None] = mapped_column(String(255))

    # Metadata
    lead_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="leads")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="lead", lazy="dynamic"
    )

    __table_args__ = (
        Index("ix_leads_client_id", "client_id"),
        Index("ix_leads_phone", "phone"),
        Index("ix_leads_email", "email"),
        Index("ix_leads_status", "status"),
        Index("ix_leads_score", "score"),
        Index("ix_leads_client_status", "client_id", "status"),
        Index("ix_leads_created_at", "created_at"),
    )


class Conversation(Base, TimestampMixin):
    """
    Conversation thread between lead and AI agent.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Channel
    channel: Mapped[ChannelType] = mapped_column(Enum(ChannelType), nullable=False)
    channel_conversation_id: Mapped[str | None] = mapped_column(String(255))

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[EscalationReason | None] = mapped_column(Enum(EscalationReason))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Metrics
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    agent_message_count: Mapped[int] = mapped_column(Integer, default=0)
    lead_message_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_ms: Mapped[int | None] = mapped_column(Integer)

    # Timing
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Summary (for long-term memory)
    summary: Mapped[str | None] = mapped_column(Text)
    summary_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Metadata
    lead_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="conversations")
    lead: Mapped["Lead"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        lazy="dynamic",
        order_by="Message.created_at",
    )

    __table_args__ = (
        Index("ix_conversations_client_id", "client_id"),
        Index("ix_conversations_lead_id", "lead_id"),
        Index("ix_conversations_is_active", "is_active"),
        Index("ix_conversations_channel", "channel"),
        Index("ix_conversations_created_at", "created_at"),
    )


class Message(Base, TimestampMixin):
    """
    Individual message in a conversation.
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Content
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="text")

    # AI Processing
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    model_used: Mapped[str | None] = mapped_column(String(100))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)

    # External
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    delivery_status: Mapped[str | None] = mapped_column(String(50))

    # Analysis
    intent: Mapped[str | None] = mapped_column(String(100))
    sentiment: Mapped[str | None] = mapped_column(String(50))
    entities: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    # Metadata
    lead_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_role", "role"),
        Index("ix_messages_created_at", "created_at"),
    )


class KnowledgeBase(Base, TimestampMixin, SoftDeleteMixin):
    """
    Client-specific knowledge base for RAG.
    """

    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="general")
    source_type: Mapped[str] = mapped_column(String(50), default="document")
    source_url: Mapped[str | None] = mapped_column(String(500))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="knowledge_bases")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="knowledge_base",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_knowledge_bases_client_id", "client_id"),
        Index("ix_knowledge_bases_category", "category"),
    )


class KnowledgeChunk(Base, TimestampMixin):
    """
    Individual chunk of knowledge for vector search.
    """

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Embedding stored separately in pgvector extension
    # We'll create a separate table for vector storage

    # Metadata
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_knowledge_chunks_knowledge_base_id", "knowledge_base_id"),
        Index("ix_knowledge_chunks_client_id", "client_id"),
    )


class QualificationRule(Base, TimestampMixin):
    """
    Client-specific qualification rules for lead scoring.
    """

    __tablename__ = "qualification_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Rule Definition
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="qualification")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Rule Logic
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # Scoring Impact
    score_impact: Mapped[int] = mapped_column(Integer, default=0)
    result_score: Mapped[LeadScore | None] = mapped_column(Enum(LeadScore))
    result_action: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="qualification_rules")

    __table_args__ = (
        Index("ix_qualification_rules_client_id", "client_id"),
        Index("ix_qualification_rules_category", "category"),
        Index("ix_qualification_rules_is_active", "is_active"),
    )


class Escalation(Base, TimestampMixin):
    """
    Human escalation requests.
    """

    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Escalation Details
    reason: Mapped[EscalationReason] = mapped_column(Enum(EscalationReason), nullable=False)
    reason_details: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(50), default="normal")

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolution_notes: Mapped[str | None] = mapped_column(Text)

    # Notifications
    notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notification_channels: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    __table_args__ = (
        Index("ix_escalations_client_id", "client_id"),
        Index("ix_escalations_status", "status"),
        Index("ix_escalations_created_at", "created_at"),
    )


class UsageLog(Base, TimestampMixin):
    """
    Token usage tracking for billing and cost control.
    """

    __tablename__ = "usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Usage Details
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_total: Mapped[int] = mapped_column(Integer, nullable=False)

    # Cost (in microdollars for precision)
    cost_microdollars: Mapped[int] = mapped_column(Integer, default=0)

    # Context
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    __table_args__ = (
        Index("ix_usage_logs_client_id", "client_id"),
        Index("ix_usage_logs_created_at", "created_at"),
        Index("ix_usage_logs_client_created", "client_id", "created_at"),
    )
