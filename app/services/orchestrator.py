"""
Conversation Orchestrator
Coordinates the flow from message receipt to AI response to delivery
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from app.agents.qualification_agent import (
    AgentAction,
    ClientConfig,
    ConversationContext,
    LeadQualificationAgent,
    QualificationData,
    RouterAgent,
)
from app.core.config import settings
from app.db.models import ChannelType, EscalationReason, LeadScore, LeadStatus
from app.db.session import AsyncSession
from app.services.client_service import ClientService
from app.services.conversation_service import ConversationService
from app.services.lead_service import LeadService
from app.services.knowledge_service import KnowledgeService
from app.integrations.twilio_service import get_twilio_service
from app.integrations.email_service import get_email_service
from app.integrations.calendar_service import get_calendar_service
from app.integrations.hubspot_service import get_hubspot_service

logger = structlog.get_logger()


class ConversationOrchestrator:
    """
    Main orchestrator for conversation flow.
    Handles message processing, AI response, and channel delivery.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.lead_service = LeadService(db)
        self.conversation_service = ConversationService(db)
        self.client_service = ClientService(db)
        self.knowledge_service = KnowledgeService(db)
        self.router = RouterAgent()
        self.twilio = get_twilio_service()
        self.email_service = get_email_service()

    async def process_and_respond(
        self,
        conversation_id: UUID,
        lead_id: UUID,
        client_id: UUID,
    ) -> None:
        """
        Main processing flow for an incoming message.
        1. Load context
        2. Check for quick escalation
        3. Retrieve RAG context if needed
        4. Generate AI response
        5. Update lead qualification
        6. Send response
        7. Handle post-response actions
        """
        try:
            # Load all required data
            conversation = await self.conversation_service.get_by_id(conversation_id)
            lead = await self.lead_service.get_by_id(lead_id)
            client = await self.client_service.get_by_id(client_id)

            if not all([conversation, lead, client]):
                logger.error(
                    "Missing required data for processing",
                    conversation_id=conversation_id,
                    lead_id=lead_id,
                    client_id=client_id,
                )
                return

            # Get the latest message
            messages = await self.conversation_service.get_recent_messages(
                conversation_id, limit=1
            )
            if not messages:
                logger.error("No messages found in conversation", conversation_id=conversation_id)
                return

            latest_message = messages[-1]

            # Get client configuration
            client_config = await self._build_client_config(client)

            # Quick escalation check
            should_escalate, escalation_reason = await self.router.should_escalate(
                latest_message.content,
                conversation.message_count,
            )

            if should_escalate:
                await self._handle_escalation(
                    conversation=conversation,
                    lead=lead,
                    reason=escalation_reason or "Rule triggered",
                )
                return

            # Build conversation context
            message_history = await self.conversation_service.get_message_history_for_prompt(
                conversation_id, limit=10
            )

            # Get RAG context if available
            rag_context = await self._get_rag_context(client_id, latest_message.content)

            context = ConversationContext(
                conversation_id=conversation_id,
                lead_id=lead_id,
                lead_name=lead.name or lead.first_name,
                lead_phone=lead.phone,
                lead_email=lead.email,
                channel=conversation.channel.value,
                message_history=message_history[:-1],  # Exclude the message we're responding to
                current_qualification=self._build_qualification_data(lead),
                rag_context=rag_context,
            )

            # Generate AI response
            agent = LeadQualificationAgent(client_config)
            response = await agent.process_message(latest_message.content, context)

            # Add response delay for natural feel (configurable per client)
            delay = client.config.get("response_delay_ms", 1000) / 1000
            await asyncio.sleep(delay)

            # Save agent response as message
            await self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="agent",
                content=response.message,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                model_used=response.model_used,
                confidence_score=response.confidence,
                processing_time_ms=response.processing_time_ms,
                intent=response.intent.value,
            )

            # Update lead qualification
            await self._update_lead_from_response(lead, response)

            # Track token usage
            total_tokens = response.tokens_input + response.tokens_output
            await self.client_service.update_token_usage(client_id, total_tokens)

            # Handle post-response actions
            await self._handle_action(
                action=response.action,
                conversation=conversation,
                lead=lead,
                client=client,
                response=response,
            )

            # Send response to channel
            await self._send_to_channel(
                channel=conversation.channel,
                recipient=lead.phone or lead.email,
                message=response.message,
                client=client,
            )

            logger.info(
                "Processed message successfully",
                conversation_id=str(conversation_id),
                lead_id=str(lead_id),
                intent=response.intent.value,
                action=response.action.value,
                lead_score=response.lead_score.value,
                tokens_used=total_tokens,
            )

        except Exception as e:
            logger.error(
                "Error processing message",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=True,
            )
            # Send fallback message
            await self._send_fallback_message(conversation_id, lead_id, client_id)

    async def send_missed_call_followup(
        self,
        conversation_id: UUID,
        lead_id: UUID,
        client_id: UUID,
        phone: str,
    ) -> None:
        """Send automated follow-up for missed call."""
        try:
            client = await self.client_service.get_by_id(client_id)
            lead = await self.lead_service.get_by_id(lead_id)

            if not client or not lead:
                return

            # Get client config for business name
            client_config = await self.client_service.get_client_config(client_id)
            business_name = client_config.get("business_name", client.name)

            # Generate missed call message
            message = (
                f"Hi! We noticed you called {business_name} but we missed you. "
                f"How can we help you today? Reply here and we'll get back to you right away."
            )

            # Add system message to conversation
            await self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="agent",
                content=message,
                metadata={"type": "missed_call_followup"},
            )

            # Send via SMS/WhatsApp
            await self._send_to_channel(
                channel=ChannelType.SMS,
                recipient=phone,
                message=message,
                client=client,
            )

            logger.info(
                "Sent missed call follow-up",
                conversation_id=str(conversation_id),
                lead_id=str(lead_id),
                phone=phone,
            )

        except Exception as e:
            logger.error("Error sending missed call follow-up", error=str(e))

    async def send_greeting(
        self,
        conversation_id: UUID,
        lead_id: UUID,
        client_id: UUID,
    ) -> None:
        """Send initial greeting message."""
        try:
            client = await self.client_service.get_by_id(client_id)
            lead = await self.lead_service.get_by_id(lead_id)
            conversation = await self.conversation_service.get_by_id(conversation_id)

            if not all([client, lead, conversation]):
                return

            client_config = await self._build_client_config(client)

            context = ConversationContext(
                conversation_id=conversation_id,
                lead_id=lead_id,
                lead_name=lead.name or lead.first_name,
                lead_phone=lead.phone,
                lead_email=lead.email,
                channel=conversation.channel.value,
                message_history=[],
                current_qualification=QualificationData(),
            )

            agent = LeadQualificationAgent(client_config)
            response = await agent.generate_greeting(context)

            await self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="agent",
                content=response.message,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                model_used=response.model_used,
            )

            await self._send_to_channel(
                channel=conversation.channel,
                recipient=lead.phone or lead.email,
                message=response.message,
                client=client,
            )

        except Exception as e:
            logger.error("Error sending greeting", error=str(e))

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _build_client_config(self, client) -> ClientConfig:
        """Build client configuration for agent."""
        config = await self.client_service.get_client_config(client.id)

        return ClientConfig(
            client_id=client.id,
            business_name=config.get("business_name", client.name),
            industry=client.industry or "General",
            services=config.get("services", []),
            business_hours=config.get("business_hours", "Monday-Friday 9AM-5PM"),
            timezone=client.timezone,
            qualification_questions=config.get("qualification_questions", []),
            hot_lead_triggers=config.get("hot_lead_triggers", []),
            escalation_triggers=config.get("escalation_triggers", []),
            language=client.primary_language,
            tone=config.get("tone", "professional_friendly"),
            custom_instructions=config.get("custom_instructions", ""),
        )

    def _build_qualification_data(self, lead) -> QualificationData:
        """Build qualification data from lead record."""
        qual_data = lead.qualification_data or {}

        return QualificationData(
            service_interest=lead.service_interest or qual_data.get("service_interest"),
            urgency=lead.urgency or qual_data.get("urgency"),
            budget_confirmed=qual_data.get("budget_confirmed"),
            budget_range=lead.budget_range or qual_data.get("budget_range"),
            location=lead.location or qual_data.get("location"),
            preferred_contact_time=lead.preferred_contact_time
            or qual_data.get("preferred_contact_time"),
            decision_maker=qual_data.get("decision_maker"),
            timeline=qual_data.get("timeline"),
            additional_notes=qual_data.get("additional_notes", []),
        )

    async def _get_rag_context(
        self,
        client_id: UUID,
        query: str,
        top_k: int = 3,
    ) -> list[str] | None:
        """Retrieve relevant context from knowledge base."""
        try:
            results = await self.knowledge_service.search(
                client_id=client_id,
                query=query,
                max_results=top_k,
            )
            
            if not results:
                return None
            
            # Format results for prompt injection
            context_parts = []
            for result in results:
                context_parts.append(
                    f"[{result['knowledge_base']} - {result['source']}]\n{result['content']}"
                )
            
            return context_parts
            
        except Exception as e:
            logger.error("RAG retrieval failed", error=str(e))
            return None

    async def _update_lead_from_response(self, lead, response) -> None:
        """Update lead record with extracted qualification data."""
        qual_data = response.qualification_data

        updates = {}
        if qual_data.service_interest:
            updates["service_interest"] = qual_data.service_interest
        if qual_data.urgency:
            updates["urgency"] = qual_data.urgency
        if qual_data.budget_range:
            updates["budget_range"] = qual_data.budget_range
        if qual_data.location:
            updates["location"] = qual_data.location
        if qual_data.preferred_contact_time:
            updates["preferred_contact_time"] = qual_data.preferred_contact_time

        if updates:
            await self.lead_service.update_lead(lead.id, **updates)

        # Update qualification data JSON
        await self.lead_service.update_qualification(
            lead.id, qual_data.to_dict()
        )

        # Update score
        if response.lead_score != LeadScore.UNSCORED:
            await self.lead_service.update_score(lead.id, response.lead_score)

    async def _handle_action(
        self,
        action: AgentAction,
        conversation,
        lead,
        client,
        response,
    ) -> None:
        """Handle post-response actions based on agent decision."""

        if action == AgentAction.ESCALATE_TO_HUMAN:
            await self._handle_escalation(
                conversation=conversation,
                lead=lead,
                reason=response.escalation_reason or "Agent requested",
            )

        elif action == AgentAction.TRANSFER_HOT_LEAD:
            await self._handle_hot_lead_transfer(
                conversation=conversation,
                lead=lead,
                client=client,
            )

        elif action == AgentAction.BOOK_APPOINTMENT:
            await self._handle_appointment_booking(
                conversation=conversation,
                lead=lead,
                client=client,
            )

        elif action == AgentAction.ADD_TO_NURTURE:
            await self.lead_service.update_status(lead.id, LeadStatus.NURTURING)

        elif action == AgentAction.END_CONVERSATION:
            await self.conversation_service.end_conversation(conversation.id)

    async def _handle_escalation(
        self,
        conversation,
        lead,
        reason: str,
    ) -> None:
        """Handle escalation to human."""
        # Map reason string to enum
        reason_enum = EscalationReason.LEAD_REQUEST
        if "long conversation" in reason.lower():
            reason_enum = EscalationReason.LONG_CONVERSATION
        elif "confidence" in reason.lower():
            reason_enum = EscalationReason.LOW_CONFIDENCE
        elif "high value" in reason.lower():
            reason_enum = EscalationReason.HIGH_VALUE

        await self.conversation_service.escalate_conversation(
            conversation.id,
            reason=reason_enum,
            reason_details=reason,
        )

        # Update lead status
        await self.lead_service.update_status(lead.id, LeadStatus.QUALIFYING)

        # Send notification to client team
        try:
            client = await self.client_service.get_by_id(conversation.client_id)
            if client and client.notification_email:
                # Get conversation snippet
                messages = await self.conversation_service.get_messages(
                    conversation.id, limit=5
                )
                snippet = "\n".join([
                    f"[{m.role.value.upper()}] {m.content[:200]}" 
                    for m in messages
                ])
                
                await self.email_service.send_escalation_alert(
                    to=client.notification_email,
                    lead_name=lead.name or "Unknown",
                    escalation_reason=reason,
                    lead_phone=lead.phone,
                    lead_email=lead.email,
                    conversation_snippet=snippet,
                    conversation_link=f"{settings.app_url}/conversations/{conversation.id}" if hasattr(settings, 'app_url') else None,
                )
        except Exception as e:
            logger.error("Failed to send escalation notification", error=str(e))

        logger.info(
            "Conversation escalated",
            conversation_id=str(conversation.id),
            lead_id=str(lead.id),
            reason=reason,
        )

    async def _handle_hot_lead_transfer(
        self,
        conversation,
        lead,
        client,
    ) -> None:
        """Handle hot lead immediate transfer."""
        await self.lead_service.update_score(lead.id, LeadScore.HOT)
        await self.lead_service.update_status(lead.id, LeadStatus.HANDED_OFF)

        # Get qualification data for alert
        qual_data = lead.qualification_data or {}
        
        # Get conversation summary
        summary = await self.conversation_service.get_conversation_summary(conversation.id)

        # Send immediate email notification
        try:
            if client.notification_email:
                await self.email_service.send_hot_lead_alert(
                    to=client.notification_email,
                    lead_name=lead.name or "Unknown",
                    lead_phone=lead.phone,
                    lead_email=lead.email,
                    service_interest=qual_data.get("service_interest"),
                    urgency=qual_data.get("urgency"),
                    summary=summary,
                    conversation_link=f"{settings.app_url}/conversations/{conversation.id}" if hasattr(settings, 'app_url') else None,
                )
        except Exception as e:
            logger.error("Failed to send hot lead email", error=str(e))

        # Send SMS alert to client for immediate action
        try:
            client_config = await self.client_service.get_client_config(client.id)
            alert_phone = client_config.get("hot_lead_sms_number")
            
            if alert_phone:
                await self.twilio.send_sms(
                    to=alert_phone,
                    body=f"🔥 HOT LEAD: {lead.name or 'Unknown'}\nPhone: {lead.phone or 'N/A'}\nInterest: {qual_data.get('service_interest', 'N/A')}\nUrgency: {qual_data.get('urgency', 'N/A')}\n\nCall them NOW!",
                )
        except Exception as e:
            logger.error("Failed to send hot lead SMS", error=str(e))

        # Sync to CRM
        try:
            hubspot = get_hubspot_service()
            await hubspot.sync_lead_data(
                email=lead.email,
                phone=lead.phone,
                name=lead.name,
                lead_score="HOT",
                qualification_data=qual_data,
                conversation_summary=summary,
                channel=conversation.channel.value,
            )
        except Exception as e:
            logger.error("Failed to sync hot lead to CRM", error=str(e))

        logger.info(
            "Hot lead transferred",
            conversation_id=str(conversation.id),
            lead_id=str(lead.id),
        )

    async def _handle_appointment_booking(
        self,
        conversation,
        lead,
        client,
    ) -> None:
        """Handle appointment booking via Cal.com."""
        try:
            # Get client's calendar config
            client_config = await self.client_service.get_client_config(client.id)
            calcom_api_key = client_config.get("calcom_api_key")
            event_type_id = client_config.get("calcom_event_type_id")
            
            if not calcom_api_key:
                logger.warning("Cal.com not configured for client", client_id=str(client.id))
                return
            
            calendar = get_calendar_service(calcom_api_key)
            
            # Get next available slot
            slot = await calendar.get_next_available_slot(
                event_type_id=event_type_id,
                timezone=client.timezone or "UTC",
            )
            
            if not slot:
                logger.warning("No available slots for booking")
                return
            
            # Create the booking
            booking = await calendar.create_booking(
                event_type_id=event_type_id,
                start_time=slot["datetime"],
                name=lead.name or "Lead",
                email=lead.email or "",
                phone=lead.phone,
                metadata={
                    "lead_id": str(lead.id),
                    "client_id": str(client.id),
                    "conversation_id": str(conversation.id),
                },
                timezone=client.timezone or "UTC",
            )
            
            if booking and booking.get("uid"):
                # Update lead with appointment info
                from datetime import datetime as dt
                appointment_time = dt.fromisoformat(slot["datetime"].replace("Z", "+00:00"))
                
                await self.lead_service.schedule_appointment(
                    lead_id=lead.id,
                    appointment_time=appointment_time,
                    notes=f"Cal.com Booking: {booking.get('uid')}",
                )
                
                # Send confirmation email to lead
                if lead.email:
                    await self.email_service.send_appointment_confirmation(
                        to=lead.email,
                        lead_name=lead.name or "there",
                        appointment_time=appointment_time.strftime("%A, %B %d at %I:%M %p"),
                        service=lead.service_interest,
                        notes="We look forward to speaking with you!",
                    )
                
                logger.info(
                    "Appointment booked",
                    lead_id=str(lead.id),
                    booking_uid=booking.get("uid"),
                    time=slot["datetime"],
                )
                
        except Exception as e:
            logger.error("Failed to book appointment", error=str(e))

    async def _send_to_channel(
        self,
        channel: ChannelType,
        recipient: str | None,
        message: str,
        client,
    ) -> None:
        """Send message via appropriate channel."""
        if not recipient:
            logger.warning("No recipient for channel delivery")
            return

        logger.info(
            "Sending message to channel",
            channel=channel.value,
            recipient=recipient,
            message_preview=message[:100],
        )

        try:
            if channel == ChannelType.SMS and settings.enable_sms:
                # Get client's Twilio number if configured
                client_config = await self.client_service.get_client_config(client.id)
                from_number = client_config.get("twilio_phone_number")
                
                await self.twilio.send_sms(
                    to=recipient,
                    body=message,
                    from_number=from_number,
                )
                
            elif channel == ChannelType.WHATSAPP and settings.enable_whatsapp:
                client_config = await self.client_service.get_client_config(client.id)
                from_number = client_config.get("twilio_whatsapp_number")
                
                await self.twilio.send_whatsapp(
                    to=recipient,
                    body=message,
                    from_number=from_number,
                )
                
            elif channel in [ChannelType.WEB_FORM, ChannelType.LIVE_CHAT]:
                # Web channels are handled via the API response directly
                # No push notification needed - client polls or uses websocket
                logger.debug("Web channel - no push delivery needed")
                
            elif channel == ChannelType.EMAIL:
                # Send email response
                await self.email_service.send_email(
                    to=recipient,
                    subject="Response from " + client.name,
                    body_html=f"<p>{message}</p>",
                )
                
            else:
                logger.warning("Unsupported channel for delivery", channel=channel.value)
                
        except Exception as e:
            logger.error(
                "Failed to send message to channel",
                channel=channel.value,
                recipient=recipient,
                error=str(e),
            )

    async def _send_fallback_message(
        self,
        conversation_id: UUID,
        lead_id: UUID,
        client_id: UUID,
    ) -> None:
        """Send fallback message when AI fails."""
        try:
            client = await self.client_service.get_by_id(client_id)
            conversation = await self.conversation_service.get_by_id(conversation_id)
            lead = await self.lead_service.get_by_id(lead_id)

            if not all([client, conversation, lead]):
                return

            fallback_message = (
                "I apologize, but I'm having a moment of difficulty. "
                "Let me connect you with our team directly. "
                "Someone will reach out to you shortly!"
            )

            await self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="agent",
                content=fallback_message,
                metadata={"type": "fallback_error"},
            )

            # Escalate conversation
            await self.conversation_service.escalate_conversation(
                conversation_id,
                reason=EscalationReason.AGENT_ERROR,
                reason_details="AI processing error",
            )

            # Send fallback message
            await self._send_to_channel(
                channel=conversation.channel,
                recipient=lead.phone or lead.email,
                message=fallback_message,
                client=client,
            )

        except Exception as e:
            logger.error("Error sending fallback message", error=str(e))
