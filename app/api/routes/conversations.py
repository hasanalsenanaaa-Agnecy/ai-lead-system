"""
Conversations API Routes
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChannelType, EscalationReason, MessageRole
from app.db.session import get_db_session
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


# =============================================================================
# Request/Response Models
# =============================================================================


class MessageCreate(BaseModel):
    """Request model for adding a message."""

    role: str  # "lead", "agent", "human", "system"
    content: str
    metadata: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    """Response model for message data."""

    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    content_type: str
    tokens_input: int
    tokens_output: int
    model_used: str | None
    confidence_score: float | None
    processing_time_ms: int | None
    external_message_id: str | None
    intent: str | None
    sentiment: str | None
    metadata: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response model for conversation data."""

    id: UUID
    client_id: UUID
    lead_id: UUID
    channel: ChannelType
    is_active: bool
    is_escalated: bool
    escalation_reason: EscalationReason | None
    escalated_at: datetime | None
    message_count: int
    agent_message_count: int
    lead_message_count: int
    total_tokens_used: int
    avg_response_time_ms: int | None
    first_response_at: datetime | None
    last_message_at: datetime | None
    ended_at: datetime | None
    summary: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """Response model for conversation with messages."""

    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    """Response model for conversation list."""

    conversations: list[ConversationResponse]
    total: int


class EscalateRequest(BaseModel):
    """Request model for escalation."""

    reason: EscalationReason
    reason_details: str | None = None


class SummaryUpdate(BaseModel):
    """Request model for updating summary."""

    summary: str


# =============================================================================
# Routes
# =============================================================================


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: UUID,
    include_messages: bool = Query(True),
    message_limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    """Get conversation by ID with messages."""
    service = ConversationService(db)

    conversation = await service.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = []
    if include_messages:
        messages = await service.get_messages(conversation_id, limit=message_limit)

    return ConversationWithMessages(
        **{
            **conversation.__dict__,
            "messages": messages,
        }
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    before_id: UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Get messages for a conversation."""
    service = ConversationService(db)

    conversation = await service.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await service.get_messages(
        conversation_id, limit=limit, before_id=before_id
    )

    return messages


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    conversation_id: UUID,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Add a message to a conversation (for human agents)."""
    service = ConversationService(db)

    conversation = await service.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message = await service.add_message(
        conversation_id=conversation_id,
        role=message_data.role,
        content=message_data.content,
        metadata=message_data.metadata,
    )

    return message


@router.post("/{conversation_id}/escalate", response_model=ConversationResponse)
async def escalate_conversation(
    conversation_id: UUID,
    escalate_data: EscalateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Escalate conversation to human."""
    service = ConversationService(db)

    conversation = await service.escalate_conversation(
        conversation_id,
        reason=escalate_data.reason,
        reason_details=escalate_data.reason_details,
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.post("/{conversation_id}/end", response_model=ConversationResponse)
async def end_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """End/close a conversation."""
    service = ConversationService(db)

    conversation = await service.end_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.patch("/{conversation_id}/summary", response_model=ConversationResponse)
async def update_summary(
    conversation_id: UUID,
    summary_data: SummaryUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update conversation summary."""
    service = ConversationService(db)

    conversation = await service.update_summary(
        conversation_id, summary_data.summary
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.get("/{conversation_id}/metrics")
async def get_conversation_metrics(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get response time metrics for a conversation."""
    service = ConversationService(db)

    conversation = await service.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    metrics = await service.calculate_response_metrics(conversation_id)

    return {
        "conversation_id": str(conversation_id),
        "message_count": conversation.message_count,
        "total_tokens_used": conversation.total_tokens_used,
        **metrics,
    }


@router.get("/client/{client_id}/active", response_model=ConversationListResponse)
async def get_active_conversations(
    client_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
):
    """Get active conversations for a client."""
    service = ConversationService(db)

    conversations = await service.get_active_conversations(client_id, limit=limit)

    return ConversationListResponse(
        conversations=conversations,
        total=len(conversations),
    )


@router.get("/client/{client_id}/escalated", response_model=ConversationListResponse)
async def get_escalated_conversations(
    client_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
):
    """Get escalated conversations needing attention."""
    service = ConversationService(db)

    conversations = await service.get_escalated_conversations(client_id, limit=limit)

    return ConversationListResponse(
        conversations=conversations,
        total=len(conversations),
    )


@router.get("/lead/{lead_id}", response_model=ConversationListResponse)
async def get_conversations_by_lead(
    lead_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    """Get all conversations for a lead."""
    service = ConversationService(db)

    # This would need a new service method
    # For now, just return empty
    return ConversationListResponse(
        conversations=[],
        total=0,
    )
