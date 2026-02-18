"""
Conversation Service
Business logic for conversation and message management
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ChannelType,
    Conversation,
    EscalationReason,
    Message,
    MessageRole,
)


class ConversationService:
    """Service for managing conversations and messages."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        """Get conversation by ID."""
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def create_conversation(
        self,
        client_id: UUID,
        lead_id: UUID,
        channel: ChannelType,
        channel_conversation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            client_id=client_id,
            lead_id=lead_id,
            channel=channel.value if isinstance(channel, ChannelType) else channel,
            session_id=channel_conversation_id,
            is_active=True,
            message_count=0,
        )

        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)

        return conversation

    async def get_active_conversation(
        self,
        client_id: UUID,
        lead_id: UUID,
        channel: ChannelType,
        max_age_hours: int = 24,
    ) -> Conversation | None:
        """Get active conversation for lead on channel within time window."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        result = await self.db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.client_id == client_id,
                    Conversation.lead_id == lead_id,
                    Conversation.channel == (channel.value if isinstance(channel, ChannelType) else channel),
                    Conversation.is_active == True,
                    Conversation.updated_at >= cutoff,
                )
            )
            .order_by(Conversation.updated_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_or_create_active_conversation(
        self,
        client_id: UUID,
        lead_id: UUID,
        channel: ChannelType,
        max_age_hours: int = 24,
    ) -> Conversation:
        """Get existing active conversation or create new one."""
        existing = await self.get_active_conversation(
            client_id, lead_id, channel, max_age_hours
        )

        if existing:
            return existing

        return await self.create_conversation(
            client_id=client_id,
            lead_id=lead_id,
            channel=channel,
        )

    async def get_or_create_by_session(
        self,
        client_id: UUID,
        lead_id: UUID,
        session_id: str,
        channel: ChannelType,
    ) -> Conversation:
        """Get conversation by session ID or create new one."""
        result = await self.db.execute(
            select(Conversation).where(
                and_(
                    Conversation.client_id == client_id,
                    Conversation.session_id == session_id,
                    Conversation.is_active == True,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        return await self.create_conversation(
            client_id=client_id,
            lead_id=lead_id,
            channel=channel,
            channel_conversation_id=session_id,
        )

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,  # "lead", "agent", "human", "system"
        content: str,
        content_type: str = "text",
        tokens_input: int = 0,
        tokens_output: int = 0,
        model_used: str | None = None,
        confidence_score: float | None = None,
        processing_time_ms: int | None = None,
        external_message_id: str | None = None,
        intent: str | None = None,
        sentiment: str | None = None,
        entities: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role.value if isinstance(role, MessageRole) else (MessageRole(role).value if isinstance(role, str) and role in [e.value for e in MessageRole] else role),
            content=content,
            content_type=content_type,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model_used=model_used,
            confidence_score=confidence_score,
            processing_time_ms=processing_time_ms,
            external_message_id=external_message_id,
            intent=intent,
            sentiment=sentiment,
            entities=entities,
            msg_metadata=metadata or {},
        )

        self.db.add(message)

        # Update conversation stats
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.message_count += 1

        await self.db.flush()
        await self.db.refresh(message)

        return message

    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = 50,
        before_id: UUID | None = None,
    ) -> list[Message]:
        """Get messages for a conversation."""
        query = select(Message).where(Message.conversation_id == conversation_id)

        if before_id:
            # Get message timestamp for pagination
            before_msg = await self.db.execute(
                select(Message.created_at).where(Message.id == before_id)
            )
            before_time = before_msg.scalar_one_or_none()
            if before_time:
                query = query.where(Message.created_at < before_time)

        query = query.order_by(Message.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        # Return in chronological order
        return list(reversed(messages))

    async def get_recent_messages(
        self,
        conversation_id: UUID,
        limit: int = 10,
    ) -> list[Message]:
        """Get most recent messages for context."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def get_message_history_for_prompt(
        self,
        conversation_id: UUID,
        limit: int = 10,
    ) -> list[dict[str, str]]:
        """Get message history formatted for LLM prompt."""
        messages = await self.get_recent_messages(conversation_id, limit)

        history = []
        for msg in messages:
            role = "user" if msg.role == MessageRole.LEAD.value else "assistant"
            history.append({"role": role, "content": msg.content})

        return history

    async def escalate_conversation(
        self,
        conversation_id: UUID,
        reason: EscalationReason,
        reason_details: str | None = None,
    ) -> Conversation | None:
        """Mark conversation as escalated."""
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return None

        conversation.is_escalated = True
        conversation.escalation_reason = reason.value if isinstance(reason, EscalationReason) else reason
        conversation.escalated_at = datetime.utcnow()

        await self.db.flush()
        return conversation

    async def end_conversation(
        self,
        conversation_id: UUID,
    ) -> Conversation | None:
        """Mark conversation as ended."""
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return None

        conversation.is_active = False
        conversation.ended_at = datetime.utcnow()

        await self.db.flush()
        return conversation

    async def update_summary(
        self,
        conversation_id: UUID,
        summary: str,
    ) -> Conversation | None:
        """Update conversation summary for long-term memory."""
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return None

        conversation.summary = summary

        await self.db.flush()
        return conversation

    async def get_conversation_count(
        self,
        client_id: UUID,
        since: datetime | None = None,
    ) -> int:
        """Get count of conversations for a client."""
        query = select(func.count()).select_from(Conversation).where(
            Conversation.client_id == client_id
        )

        if since:
            query = query.where(Conversation.created_at >= since)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_active_conversations(
        self,
        client_id: UUID,
        limit: int = 100,
    ) -> list[Conversation]:
        """Get active conversations for a client."""
        result = await self.db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.client_id == client_id,
                    Conversation.is_active == True,
                )
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_escalated_conversations(
        self,
        client_id: UUID,
        limit: int = 50,
    ) -> list[Conversation]:
        """Get escalated conversations needing attention."""
        result = await self.db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.client_id == client_id,
                    Conversation.is_escalated == True,
                    Conversation.is_active == True,
                )
            )
            .order_by(Conversation.escalated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def calculate_response_metrics(
        self,
        conversation_id: UUID,
    ) -> dict[str, Any]:
        """Calculate response time metrics for a conversation."""
        messages = await self.get_messages(conversation_id, limit=1000)

        if len(messages) < 2:
            return {"avg_response_time_ms": None}

        response_times = []
        prev_lead_msg = None

        for msg in messages:
            if msg.role == MessageRole.LEAD.value:
                prev_lead_msg = msg
            elif msg.role == MessageRole.AGENT.value and prev_lead_msg:
                diff = (msg.created_at - prev_lead_msg.created_at).total_seconds() * 1000
                response_times.append(int(diff))
                prev_lead_msg = None

        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            return {
                "avg_response_time_ms": int(avg_response_time),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "response_count": len(response_times),
            }

        return {"avg_response_time_ms": None}
