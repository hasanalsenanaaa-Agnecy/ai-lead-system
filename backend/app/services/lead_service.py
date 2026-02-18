"""
Lead Management Service.
Orchestrates lead handling, conversation flow, and integrations.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from app.core.config import settings
from app.models.models import (
    Lead, Conversation, Message, Client, Appointment,
    LeadStatus, LeadScore, ChannelType, MessageRole, HandoffReason
)
from app.services.ai_agent import (
    qualification_agent, quick_router,
    QualificationResult, ConversationContext
)
from app.services.rag_service import rag_service

logger = structlog.get_logger()


class LeadService:
    """
    Service for managing leads and conversations.
    """
    
    async def get_or_create_lead(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        phone: str,
        channel: ChannelType,
        **kwargs
    ) -> Tuple[Lead, bool]:
        """
        Get existing lead by phone or create new one.
        
        Returns:
            Tuple of (Lead, is_new)
        """
        # Try to find existing lead
        result = await db.execute(
            select(Lead).where(
                and_(
                    Lead.client_id == client_id,
                    Lead.phone == phone
                )
            )
        )
        lead = result.scalar_one_or_none()
        
        if lead:
            # Update last contact time
            lead.last_contact_at = datetime.utcnow()
            await db.commit()
            return lead, False
        
        # Create new lead
        lead = Lead(
            client_id=client_id,
            phone=phone,
            initial_channel=channel,
            status=LeadStatus.NEW,
            score=LeadScore.UNKNOWN,
            first_name=kwargs.get("first_name"),
            last_name=kwargs.get("last_name"),
            email=kwargs.get("email"),
            source=kwargs.get("source", channel.value)
        )
        
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        logger.info("Created new lead", lead_id=str(lead.id), phone=phone)
        return lead, True
    
    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        lead: Lead,
        channel: ChannelType
    ) -> Tuple[Conversation, bool]:
        """
        Get active conversation or create new one.
        
        Returns:
            Tuple of (Conversation, is_new)
        """
        # Look for active conversation on this channel
        result = await db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.lead_id == lead.id,
                    Conversation.channel == channel,
                    Conversation.is_active == True
                )
            )
            .order_by(Conversation.started_at.desc())
        )
        conversation = result.scalar_one_or_none()
        
        # Check if conversation is stale
        if conversation:
            stale_threshold = datetime.utcnow() - timedelta(
                hours=settings.CONVERSATION_STALE_HOURS
            )
            if conversation.last_message_at < stale_threshold:
                # Mark old conversation as inactive
                conversation.is_active = False
                conversation.ended_at = datetime.utcnow()
                conversation = None
        
        if conversation:
            return conversation, False
        
        # Create new conversation
        conversation = Conversation(
            lead_id=lead.id,
            client_id=lead.client_id,
            channel=channel,
            is_active=True
        )
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        logger.info(
            "Created new conversation",
            conversation_id=str(conversation.id),
            lead_id=str(lead.id)
        )
        return conversation, True
    
    async def get_conversation_messages(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        limit: int = 50
    ) -> List[Message]:
        """Get messages for a conversation."""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
        **kwargs
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            confidence_score=kwargs.get("confidence_score"),
            intent_detected=kwargs.get("intent_detected"),
            entities_extracted=kwargs.get("entities_extracted"),
            external_message_id=kwargs.get("external_message_id"),
            input_tokens=kwargs.get("input_tokens"),
            output_tokens=kwargs.get("output_tokens")
        )
        
        db.add(message)
        
        # Update conversation stats
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                last_message_at=datetime.utcnow(),
                message_count=Conversation.message_count + 1
            )
        )
        
        await db.commit()
        await db.refresh(message)
        
        return message
    
    async def process_incoming_message(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        phone: str,
        message_text: str,
        channel: ChannelType,
        external_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming message from a lead.
        Main entry point for message handling.
        
        Returns:
            Dict with response_text, lead_id, conversation_id, should_notify, etc.
        """
        try:
            # Get client
            client_result = await db.execute(
                select(Client).where(Client.id == client_id)
            )
            client = client_result.scalar_one_or_none()
            
            if not client:
                raise ValueError(f"Client not found: {client_id}")
            
            # Quick spam check
            if await quick_router.is_spam_or_irrelevant(message_text):
                logger.info("Ignored spam message", phone=phone)
                return {
                    "response_text": None,
                    "action": "ignored",
                    "reason": "spam_detected"
                }
            
            # Get or create lead
            lead, is_new_lead = await self.get_or_create_lead(
                db, client_id, phone, channel
            )
            
            # Get or create conversation
            conversation, is_new_conversation = await self.get_or_create_conversation(
                db, lead, channel
            )
            
            # Store incoming message
            await self.add_message(
                db,
                conversation.id,
                MessageRole.LEAD,
                message_text,
                external_message_id=external_message_id
            )
            
            # Check for immediate human handoff keywords
            if await quick_router.requires_human(message_text):
                return await self._handle_human_request(
                    db, lead, conversation, message_text
                )
            
            # Check message count limit
            if conversation.message_count >= settings.MAX_CONVERSATION_MESSAGES:
                return await self._handle_long_conversation(
                    db, lead, conversation
                )
            
            # Get conversation history
            messages = await self.get_conversation_messages(db, conversation.id)
            
            # Get knowledge base context
            knowledge_context = await rag_service.get_context_for_conversation(
                db, client_id, message_text
            )
            
            # Build conversation context
            context = ConversationContext(
                client=client,
                lead=lead,
                conversation=conversation,
                messages=messages[:-1],  # Exclude the message we just added
                knowledge_context=knowledge_context,
                incoming_message=message_text,
                channel=channel
            )
            
            # Get AI response
            result = await qualification_agent.qualify_and_respond(context)
            
            # Store AI response
            ai_message = await self.add_message(
                db,
                conversation.id,
                MessageRole.AI,
                result.response_text,
                confidence_score=result.confidence,
                intent_detected=result.intent,
                entities_extracted=result.entities,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens
            )
            
            # Update lead with extracted info and score
            await self._update_lead_from_result(db, lead, result)
            
            # Handle handoff if needed
            should_notify_human = False
            if result.should_handoff:
                should_notify_human = await self._handle_handoff(
                    db, lead, conversation, result
                )
            
            # Check if hot lead
            if result.score == LeadScore.HOT:
                should_notify_human = True
            
            await db.commit()
            
            return {
                "response_text": result.response_text,
                "lead_id": str(lead.id),
                "conversation_id": str(conversation.id),
                "is_new_lead": is_new_lead,
                "lead_score": result.score.value,
                "score_value": result.score_value,
                "confidence": result.confidence,
                "should_notify_human": should_notify_human,
                "handoff_reason": result.handoff_reason.value if result.handoff_reason else None,
                "intent": result.intent,
                "action": "responded"
            }
            
        except Exception as e:
            logger.error(
                "Failed to process message",
                error=str(e),
                phone=phone,
                client_id=str(client_id)
            )
            # Return fallback response
            return {
                "response_text": "Thanks for reaching out! Someone from our team will get back to you shortly.",
                "error": str(e),
                "action": "fallback"
            }
    
    async def _update_lead_from_result(
        self,
        db: AsyncSession,
        lead: Lead,
        result: QualificationResult
    ) -> None:
        """Update lead record with AI analysis results."""
        # Update score
        lead.score = result.score
        lead.score_value = result.score_value
        lead.status = result.suggested_status
        
        # Extract and update entities
        entities = result.entities
        
        if entities.get("name"):
            # Try to split name
            name_parts = entities["name"].split(" ", 1)
            lead.first_name = lead.first_name or name_parts[0]
            if len(name_parts) > 1:
                lead.last_name = lead.last_name or name_parts[1]
        
        if entities.get("email"):
            lead.email = lead.email or entities["email"]
        
        if entities.get("service_needed"):
            lead.service_interested = entities["service_needed"]
        
        if entities.get("timeline"):
            lead.timeline = entities["timeline"]
        
        if entities.get("budget"):
            lead.budget_range = entities["budget"]
        
        if entities.get("location"):
            lead.address = lead.address or entities["location"]
        
        # Store full qualification data
        lead.qualification_data = lead.qualification_data or {}
        lead.qualification_data.update({
            "last_intent": result.intent,
            "last_confidence": result.confidence,
            "last_entities": entities,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Mark as qualified if threshold met
        if result.score_value >= settings.LEAD_SCORE_WARM_THRESHOLD and not lead.qualified_at:
            lead.qualified_at = datetime.utcnow()
    
    async def _handle_human_request(
        self,
        db: AsyncSession,
        lead: Lead,
        conversation: Conversation,
        message: str
    ) -> Dict[str, Any]:
        """Handle explicit request for human agent."""
        # Mark for handoff
        lead.status = LeadStatus.HANDED_OFF
        lead.handed_off_at = datetime.utcnow()
        lead.handoff_reason = HandoffReason.LEAD_REQUESTED
        
        conversation.is_human_takeover = True
        
        # Add system message
        await self.add_message(
            db,
            conversation.id,
            MessageRole.SYSTEM,
            "Lead requested human agent"
        )
        
        response = "I'll connect you with a team member right away. They'll be reaching out to you shortly!"
        
        await self.add_message(
            db,
            conversation.id,
            MessageRole.AI,
            response
        )
        
        await db.commit()
        
        return {
            "response_text": response,
            "lead_id": str(lead.id),
            "conversation_id": str(conversation.id),
            "should_notify_human": True,
            "handoff_reason": HandoffReason.LEAD_REQUESTED.value,
            "action": "human_requested"
        }
    
    async def _handle_long_conversation(
        self,
        db: AsyncSession,
        lead: Lead,
        conversation: Conversation
    ) -> Dict[str, Any]:
        """Handle conversation that has exceeded message limit."""
        lead.handoff_reason = HandoffReason.LONG_CONVERSATION
        conversation.is_human_takeover = True
        
        response = "I want to make sure you get the best help possible. Let me have one of our team members continue this conversation with you. They'll reach out shortly!"
        
        await self.add_message(
            db,
            conversation.id,
            MessageRole.AI,
            response
        )
        
        await db.commit()
        
        return {
            "response_text": response,
            "lead_id": str(lead.id),
            "conversation_id": str(conversation.id),
            "should_notify_human": True,
            "handoff_reason": HandoffReason.LONG_CONVERSATION.value,
            "action": "message_limit_reached"
        }
    
    async def _handle_handoff(
        self,
        db: AsyncSession,
        lead: Lead,
        conversation: Conversation,
        result: QualificationResult
    ) -> bool:
        """Process handoff to human agent."""
        lead.status = LeadStatus.HANDED_OFF
        lead.handed_off_at = datetime.utcnow()
        lead.handoff_reason = result.handoff_reason
        
        conversation.is_human_takeover = True
        
        return True
    
    async def get_lead_by_id(
        self,
        db: AsyncSession,
        lead_id: uuid.UUID,
        client_id: Optional[uuid.UUID] = None
    ) -> Optional[Lead]:
        """Get lead by ID with optional client filter."""
        query = select(Lead).where(Lead.id == lead_id)
        
        if client_id:
            query = query.where(Lead.client_id == client_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_leads(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        status: Optional[LeadStatus] = None,
        score: Optional[LeadScore] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Lead]:
        """Get leads with filters."""
        query = select(Lead).where(Lead.client_id == client_id)
        
        if status:
            query = query.where(Lead.status == status)
        
        if score:
            query = query.where(Lead.score == score)
        
        query = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_hot_leads(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        since: Optional[datetime] = None
    ) -> List[Lead]:
        """Get hot leads, optionally since a certain time."""
        query = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.score == LeadScore.HOT
            )
        )
        
        if since:
            query = query.where(Lead.created_at >= since)
        
        query = query.order_by(Lead.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_leads_needing_followup(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        hours_since_contact: int = 24
    ) -> List[Lead]:
        """Get leads that need follow-up."""
        threshold = datetime.utcnow() - timedelta(hours=hours_since_contact)
        
        result = await db.execute(
            select(Lead).where(
                and_(
                    Lead.client_id == client_id,
                    Lead.status.in_([LeadStatus.CONTACTED, LeadStatus.QUALIFIED]),
                    Lead.last_contact_at < threshold
                )
            ).order_by(Lead.last_contact_at.asc())
        )
        
        return list(result.scalars().all())


class AppointmentService:
    """Service for managing appointments."""
    
    async def schedule_appointment(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        lead_id: uuid.UUID,
        scheduled_at: datetime,
        duration_minutes: int = 30,
        service_type: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Appointment:
        """Schedule a new appointment."""
        appointment = Appointment(
            client_id=client_id,
            lead_id=lead_id,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            service_type=service_type,
            notes=notes
        )
        
        db.add(appointment)
        
        # Update lead status
        await db.execute(
            update(Lead)
            .where(Lead.id == lead_id)
            .values(
                status=LeadStatus.APPOINTMENT_SCHEDULED,
                appointment_scheduled_at=scheduled_at,
                appointment_notes=notes
            )
        )
        
        await db.commit()
        await db.refresh(appointment)
        
        logger.info(
            "Scheduled appointment",
            appointment_id=str(appointment.id),
            lead_id=str(lead_id)
        )
        
        return appointment
    
    async def get_appointments(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Appointment]:
        """Get appointments within date range."""
        query = select(Appointment).where(Appointment.client_id == client_id)
        
        if start_date:
            query = query.where(Appointment.scheduled_at >= start_date)
        
        if end_date:
            query = query.where(Appointment.scheduled_at <= end_date)
        
        query = query.order_by(Appointment.scheduled_at.asc())
        
        result = await db.execute(query)
        return list(result.scalars().all())


# Export service instances
lead_service = LeadService()
appointment_service = AppointmentService()
