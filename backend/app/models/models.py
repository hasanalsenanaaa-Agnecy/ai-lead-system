"""
Database models for the AI Lead Response System.
Multi-tenant architecture with row-level security concepts.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime, ForeignKey,
    JSON, Index, UniqueConstraint, Enum as SQLEnum, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from pgvector.sqlalchemy import Vector

from app.core.database import Base


# Enums
class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    APPOINTMENT_SCHEDULED = "appointment_scheduled"
    HANDED_OFF = "handed_off"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    NURTURE = "nurture"
    UNRESPONSIVE = "unresponsive"


class LeadScore(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    UNKNOWN = "unknown"


class ChannelType(str, Enum):
    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    WEB_CHAT = "web_chat"
    EMAIL = "email"


class MessageRole(str, Enum):
    LEAD = "lead"
    AI = "ai"
    HUMAN_AGENT = "human_agent"
    SYSTEM = "system"


class ClientVertical(str, Enum):
    HOME_SERVICES = "home_services"
    REAL_ESTATE = "real_estate"
    MED_SPA = "med_spa"
    LEGAL = "legal"
    OTHER = "other"


class ClientStatus(str, Enum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    PAUSED = "paused"
    CHURNED = "churned"


class HandoffReason(str, Enum):
    LEAD_REQUESTED = "lead_requested"
    LOW_CONFIDENCE = "low_confidence"
    HIGH_VALUE = "high_value"
    LONG_CONVERSATION = "long_conversation"
    NEGATIVE_SENTIMENT = "negative_sentiment"
    COMPLEX_QUERY = "complex_query"
    ESCALATION = "escalation"


# =============================================================================
# CLIENT (TENANT) MODELS
# =============================================================================

class Client(Base):
    """
    Client/Tenant model. Each client is a business using the lead system.
    This is the root of multi-tenancy.
    """
    __tablename__ = "clients"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    vertical: Mapped[ClientVertical] = mapped_column(
        SQLEnum(ClientVertical), default=ClientVertical.OTHER
    )
    status: Mapped[ClientStatus] = mapped_column(
        SQLEnum(ClientStatus), default=ClientStatus.ONBOARDING
    )
    
    # Contact
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Business Details
    business_hours: Mapped[Optional[dict]] = mapped_column(JSON)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Twilio Configuration
    twilio_phone_number: Mapped[Optional[str]] = mapped_column(String(50))
    twilio_whatsapp_number: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Integration Config
    crm_type: Mapped[Optional[str]] = mapped_column(String(50))
    crm_config: Mapped[Optional[dict]] = mapped_column(JSON)
    calendar_type: Mapped[Optional[str]] = mapped_column(String(50))
    calendar_config: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # AI Configuration
    ai_persona_name: Mapped[str] = mapped_column(String(100), default="AI Assistant")
    ai_persona_prompt: Mapped[Optional[str]] = mapped_column(Text)
    qualification_questions: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    services_offered: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    
    # Notification Settings
    hot_lead_notification_emails: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(255)))
    hot_lead_notification_phones: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(50)))
    
    # Billing
    monthly_retainer: Mapped[Optional[float]] = mapped_column(Float)
    setup_fee_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="client", cascade="all, delete-orphan")
    users: Mapped[List["User"]] = relationship("User", back_populates="client", cascade="all, delete-orphan")
    knowledge_base: Mapped[List["KnowledgeBaseEntry"]] = relationship(
        "KnowledgeBaseEntry", back_populates="client", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("ix_clients_status", "status"),
        Index("ix_clients_vertical", "vertical"),
    )


# =============================================================================
# USER MODEL (Admin users for clients)
# =============================================================================

class User(Base):
    """User accounts for client admin access."""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_client_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="users")
    
    __table_args__ = (
        Index("ix_users_client_id", "client_id"),
    )


# =============================================================================
# LEAD MODELS
# =============================================================================

class Lead(Base):
    """Lead/Contact model. Each potential customer is a lead."""
    __tablename__ = "leads"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    
    # Contact Info
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Lead Status & Score
    status: Mapped[LeadStatus] = mapped_column(
        SQLEnum(LeadStatus), default=LeadStatus.NEW
    )
    score: Mapped[LeadScore] = mapped_column(
        SQLEnum(LeadScore), default=LeadScore.UNKNOWN
    )
    score_value: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Source & Channel
    source: Mapped[Optional[str]] = mapped_column(String(100))
    initial_channel: Mapped[ChannelType] = mapped_column(
        SQLEnum(ChannelType), default=ChannelType.SMS
    )
    
    # Qualification Data
    qualified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    qualification_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Service Interest
    service_interested: Mapped[Optional[str]] = mapped_column(String(255))
    budget_range: Mapped[Optional[str]] = mapped_column(String(100))
    timeline: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Location
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    zip_code: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Appointment
    appointment_scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    appointment_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Handoff
    handed_off_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    handoff_reason: Mapped[Optional[HandoffReason]] = mapped_column(SQLEnum(HandoffReason))
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255))
    
    # CRM Sync
    external_crm_id: Mapped[Optional[str]] = mapped_column(String(255))
    crm_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(50)))
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    first_contact_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_contact_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="leads")
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="lead", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        UniqueConstraint("client_id", "phone", name="uq_lead_client_phone"),
        Index("ix_leads_client_id", "client_id"),
        Index("ix_leads_status", "status"),
        Index("ix_leads_score", "score"),
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_client_status", "client_id", "status"),
    )


# =============================================================================
# CONVERSATION MODELS
# =============================================================================

class Conversation(Base):
    """Conversation thread with a lead."""
    __tablename__ = "conversations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE")
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    
    # Conversation Status
    channel: Mapped[ChannelType] = mapped_column(SQLEnum(ChannelType))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_human_takeover: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # AI Confidence tracking
    avg_confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("ix_conversations_lead_id", "lead_id"),
        Index("ix_conversations_client_id", "client_id"),
        Index("ix_conversations_active", "is_active"),
    )


class Message(Base):
    """Individual message in a conversation."""
    __tablename__ = "messages"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    
    # Message Content
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # AI Metadata (for AI messages)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    intent_detected: Mapped[Optional[str]] = mapped_column(String(100))
    entities_extracted: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Delivery Status
    external_message_id: Mapped[Optional[str]] = mapped_column(String(255))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Token Usage (for cost tracking)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_created_at", "created_at"),
    )


# =============================================================================
# KNOWLEDGE BASE (RAG)
# =============================================================================

class KnowledgeBaseEntry(Base):
    """Knowledge base entries for RAG. Stores client-specific FAQs, services, etc."""
    __tablename__ = "knowledge_base"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    
    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Vector Embedding (1536 dimensions for text-embedding-3-small)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(1536))
    
    # Metadata
    source: Mapped[Optional[str]] = mapped_column(String(255))
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="knowledge_base")
    
    __table_args__ = (
        Index("ix_knowledge_base_client_id", "client_id"),
        Index("ix_knowledge_base_category", "category"),
    )


# =============================================================================
# APPOINTMENTS
# =============================================================================

class Appointment(Base):
    """Scheduled appointments."""
    __tablename__ = "appointments"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE")
    )
    
    # Appointment Details
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    service_type: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # External Calendar
    external_calendar_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Reminders
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    __table_args__ = (
        Index("ix_appointments_client_id", "client_id"),
        Index("ix_appointments_scheduled_at", "scheduled_at"),
        Index("ix_appointments_status", "status"),
    )


# =============================================================================
# ANALYTICS & TRACKING
# =============================================================================

class DailyMetrics(Base):
    """Daily aggregated metrics per client."""
    __tablename__ = "daily_metrics"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Lead Metrics
    leads_new: Mapped[int] = mapped_column(Integer, default=0)
    leads_qualified: Mapped[int] = mapped_column(Integer, default=0)
    leads_hot: Mapped[int] = mapped_column(Integer, default=0)
    leads_handed_off: Mapped[int] = mapped_column(Integer, default=0)
    
    # Conversation Metrics
    conversations_started: Mapped[int] = mapped_column(Integer, default=0)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    messages_received: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_seconds: Mapped[Optional[float]] = mapped_column(Float)
    
    # Appointment Metrics
    appointments_scheduled: Mapped[int] = mapped_column(Integer, default=0)
    appointments_completed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Cost Tracking
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    
    __table_args__ = (
        UniqueConstraint("client_id", "date", name="uq_daily_metrics_client_date"),
        Index("ix_daily_metrics_client_id", "client_id"),
        Index("ix_daily_metrics_date", "date"),
    )


# =============================================================================
# API KEYS & WEBHOOKS
# =============================================================================

class ApiKey(Base):
    """API keys for external integrations."""
    __tablename__ = "api_keys"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    __table_args__ = (
        Index("ix_api_keys_client_id", "client_id"),
        Index("ix_api_keys_key_prefix", "key_prefix"),
    )
