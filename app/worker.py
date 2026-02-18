"""
Celery Worker Tasks
Background task processing for AI Lead System
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from celery import Celery, Task

from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    "ai_lead_system",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    worker_prefetch_multiplier=1,  # One task at a time for better distribution
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "daily-summary": {
        "task": "app.worker.send_daily_summaries",
        "schedule": 86400.0,  # Daily (configure time via timezone)
        "options": {"queue": "reports"},
    },
    "cleanup-old-conversations": {
        "task": "app.worker.cleanup_old_data",
        "schedule": 86400.0,  # Daily
        "options": {"queue": "maintenance"},
    },
    "sync-pending-crm": {
        "task": "app.worker.sync_pending_crm_records",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"queue": "integrations"},
    },
}

# Task routing
celery_app.conf.task_routes = {
    "app.worker.process_ai_response": {"queue": "ai"},
    "app.worker.send_message_*": {"queue": "delivery"},
    "app.worker.sync_*": {"queue": "integrations"},
    "app.worker.send_*_alert": {"queue": "notifications"},
    "app.worker.send_daily_*": {"queue": "reports"},
}


# ============================================================================
# Helper for async tasks
# ============================================================================

class AsyncTask(Task):
    """Base task class that handles async functions."""
    
    def run_async(self, coro):
        """Run an async coroutine in the event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


# ============================================================================
# AI Processing Tasks
# ============================================================================

@celery_app.task(bind=True, base=AsyncTask, name="app.worker.process_ai_response")
def process_ai_response(
    self,
    conversation_id: str,
    lead_id: str,
    client_id: str,
) -> dict[str, Any]:
    """
    Process an incoming message and generate AI response.
    
    This is the main background task that:
    1. Loads conversation context
    2. Retrieves relevant knowledge base content
    3. Generates AI response
    4. Updates lead qualification
    5. Sends response via appropriate channel
    6. Handles post-response actions
    """
    async def _process():
        from app.db.session import get_async_session
        from app.services.orchestrator import ConversationOrchestrator
        
        async with get_async_session() as db:
            orchestrator = ConversationOrchestrator(db)
            await orchestrator.process_and_respond(
                conversation_id=UUID(conversation_id),
                lead_id=UUID(lead_id),
                client_id=UUID(client_id),
            )
        
        return {"status": "processed", "conversation_id": conversation_id}
    
    return self.run_async(_process())


@celery_app.task(bind=True, base=AsyncTask, name="app.worker.generate_greeting")
def generate_greeting(
    self,
    conversation_id: str,
    lead_id: str,
    client_id: str,
) -> dict[str, Any]:
    """Generate and send initial greeting for new conversation."""
    async def _generate():
        from app.db.session import get_async_session
        from app.services.orchestrator import ConversationOrchestrator
        
        async with get_async_session() as db:
            orchestrator = ConversationOrchestrator(db)
            greeting = await orchestrator.generate_greeting(
                conversation_id=UUID(conversation_id),
                lead_id=UUID(lead_id),
                client_id=UUID(client_id),
            )
        
        return {"status": "sent", "greeting": greeting}
    
    return self.run_async(_generate())


# ============================================================================
# Message Delivery Tasks
# ============================================================================

@celery_app.task(bind=True, base=AsyncTask, name="app.worker.send_message_sms")
def send_message_sms(
    self,
    to: str,
    body: str,
    from_number: str | None = None,
) -> dict[str, Any]:
    """Send SMS message via Twilio."""
    async def _send():
        from app.integrations.twilio_service import get_twilio_service
        
        twilio = get_twilio_service()
        result = await twilio.send_sms(
            to=to,
            body=body,
            from_number=from_number,
        )
        
        return {
            "status": "sent",
            "message_sid": result.get("sid"),
            "to": to,
        }
    
    return self.run_async(_send())


@celery_app.task(bind=True, base=AsyncTask, name="app.worker.send_message_whatsapp")
def send_message_whatsapp(
    self,
    to: str,
    body: str,
    from_number: str | None = None,
    media_url: str | None = None,
) -> dict[str, Any]:
    """Send WhatsApp message via Twilio."""
    async def _send():
        from app.integrations.twilio_service import get_twilio_service
        
        twilio = get_twilio_service()
        result = await twilio.send_whatsapp(
            to=to,
            body=body,
            from_number=from_number,
            media_url=media_url,
        )
        
        return {
            "status": "sent",
            "message_sid": result.get("sid"),
            "to": to,
        }
    
    return self.run_async(_send())


# ============================================================================
# Notification Tasks
# ============================================================================

@celery_app.task(bind=True, base=AsyncTask, name="app.worker.send_hot_lead_alert")
def send_hot_lead_alert(
    self,
    to_emails: list[str],
    lead_name: str,
    lead_phone: str | None = None,
    lead_email: str | None = None,
    service_interest: str | None = None,
    urgency: str | None = None,
    summary: str | None = None,
    conversation_link: str | None = None,
) -> dict[str, Any]:
    """Send hot lead email alert."""
    async def _send():
        from app.integrations.email_service import get_email_service
        
        email_service = get_email_service()
        result = await email_service.send_hot_lead_alert(
            to=to_emails,
            lead_name=lead_name,
            lead_phone=lead_phone,
            lead_email=lead_email,
            service_interest=service_interest,
            urgency=urgency,
            summary=summary,
            conversation_link=conversation_link,
        )
        
        return result
    
    return self.run_async(_send())


@celery_app.task(bind=True, base=AsyncTask, name="app.worker.send_escalation_alert")
def send_escalation_alert(
    self,
    to_emails: list[str],
    lead_name: str,
    escalation_reason: str,
    lead_phone: str | None = None,
    lead_email: str | None = None,
    conversation_snippet: str | None = None,
    conversation_link: str | None = None,
) -> dict[str, Any]:
    """Send escalation email alert."""
    async def _send():
        from app.integrations.email_service import get_email_service
        
        email_service = get_email_service()
        result = await email_service.send_escalation_alert(
            to=to_emails,
            lead_name=lead_name,
            escalation_reason=escalation_reason,
            lead_phone=lead_phone,
            lead_email=lead_email,
            conversation_snippet=conversation_snippet,
            conversation_link=conversation_link,
        )
        
        return result
    
    return self.run_async(_send())


@celery_app.task(bind=True, base=AsyncTask, name="app.worker.send_sms_alert")
def send_sms_alert(
    self,
    to: str,
    message: str,
) -> dict[str, Any]:
    """Send urgent SMS alert (for hot leads)."""
    async def _send():
        from app.integrations.twilio_service import get_twilio_service
        
        twilio = get_twilio_service()
        result = await twilio.send_sms(to=to, body=message)
        
        return {"status": "sent", "sid": result.get("sid")}
    
    return self.run_async(_send())


# ============================================================================
# CRM Sync Tasks
# ============================================================================

@celery_app.task(bind=True, base=AsyncTask, name="app.worker.sync_lead_to_hubspot")
def sync_lead_to_hubspot(
    self,
    lead_id: str,
    client_id: str,
    access_token: str | None = None,
) -> dict[str, Any]:
    """Sync lead data to HubSpot CRM."""
    async def _sync():
        from app.db.session import get_async_session
        from app.services.lead_service import LeadService
        from app.services.conversation_service import ConversationService
        from app.integrations.hubspot_service import get_hubspot_service
        
        async with get_async_session() as db:
            lead_service = LeadService(db)
            conv_service = ConversationService(db)
            
            lead = await lead_service.get_by_id(UUID(lead_id))
            if not lead:
                return {"status": "error", "reason": "lead_not_found"}
            
            # Get conversation summary
            conversations = await conv_service.get_active_for_lead(UUID(lead_id))
            summary = None
            messages = []
            if conversations:
                conv = conversations[0]
                summary = conv.summary
                msgs = await conv_service.get_messages(conv.id, limit=10)
                messages = [{"role": m.role.value, "content": m.content} for m in msgs]
            
            hubspot = get_hubspot_service(access_token)
            result = await hubspot.sync_lead_data(
                email=lead.email,
                phone=lead.phone,
                name=lead.name,
                lead_score=lead.score.value if lead.score else None,
                qualification_data=lead.qualification_data,
                conversation_summary=summary,
                messages=messages,
                channel=lead.source or "WEB",
            )
            
            # Mark as synced
            await lead_service.mark_crm_synced(UUID(lead_id))
            
            return result
    
    return self.run_async(_sync())


@celery_app.task(bind=True, base=AsyncTask, name="app.worker.sync_pending_crm_records")
def sync_pending_crm_records(self) -> dict[str, Any]:
    """Sync all pending leads to CRM (periodic task)."""
    async def _sync():
        from app.db.session import get_async_session
        from sqlalchemy import select
        from app.db.models import Lead, Client
        
        async with get_async_session() as db:
            # Find leads not synced in last hour
            cutoff = datetime.utcnow() - timedelta(hours=1)
            
            result = await db.execute(
                select(Lead)
                .where(Lead.crm_synced_at < cutoff)
                .where(Lead.email.isnot(None))  # Must have email for HubSpot
                .limit(50)
            )
            leads = result.scalars().all()
            
            synced = 0
            for lead in leads:
                try:
                    sync_lead_to_hubspot.delay(
                        lead_id=str(lead.id),
                        client_id=str(lead.client_id),
                    )
                    synced += 1
                except Exception:
                    pass
            
            return {"queued": synced}
    
    return self.run_async(_sync())


# ============================================================================
# Calendar Tasks
# ============================================================================

@celery_app.task(bind=True, base=AsyncTask, name="app.worker.book_appointment")
def book_appointment(
    self,
    lead_id: str,
    client_id: str,
    start_time: str,
    event_type_id: int | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Book appointment via Cal.com."""
    async def _book():
        from app.db.session import get_async_session
        from app.services.lead_service import LeadService
        from app.integrations.calendar_service import get_calendar_service
        
        async with get_async_session() as db:
            lead_service = LeadService(db)
            lead = await lead_service.get_by_id(UUID(lead_id))
            
            if not lead:
                return {"status": "error", "reason": "lead_not_found"}
            
            calendar = get_calendar_service(api_key)
            booking = await calendar.create_booking(
                event_type_id=event_type_id,
                start_time=start_time,
                name=lead.name or "Lead",
                email=lead.email or "",
                phone=lead.phone,
                metadata={"lead_id": lead_id, "client_id": client_id},
            )
            
            # Update lead with appointment info
            await lead_service.schedule_appointment(
                lead_id=UUID(lead_id),
                appointment_time=datetime.fromisoformat(start_time.replace("Z", "+00:00")),
                notes=f"Booking ID: {booking.get('uid')}",
            )
            
            return {
                "status": "booked",
                "booking_uid": booking.get("uid"),
                "start_time": start_time,
            }
    
    return self.run_async(_book())


# ============================================================================
# Report Tasks
# ============================================================================

@celery_app.task(bind=True, base=AsyncTask, name="app.worker.send_daily_summaries")
def send_daily_summaries(self) -> dict[str, Any]:
    """Send daily summary emails to all active clients."""
    async def _send():
        from app.db.session import get_async_session
        from sqlalchemy import select, func
        from app.db.models import Client, Lead, Conversation, Escalation, ClientStatus
        from app.integrations.email_service import get_email_service
        
        async with get_async_session() as db:
            # Get active clients
            result = await db.execute(
                select(Client).where(Client.status == ClientStatus.ACTIVE)
            )
            clients = result.scalars().all()
            
            email_service = get_email_service()
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            
            sent = 0
            for client in clients:
                if not client.notification_email:
                    continue
                
                # Get stats for yesterday
                stats = await _get_daily_stats(db, client.id, yesterday)
                
                try:
                    await email_service.send_daily_summary(
                        to=client.notification_email,
                        client_name=client.name,
                        date=yesterday.strftime("%B %d, %Y"),
                        **stats,
                    )
                    sent += 1
                except Exception:
                    pass
            
            return {"sent": sent, "clients": len(clients)}
    
    return self.run_async(_send())


async def _get_daily_stats(db, client_id: UUID, date) -> dict[str, Any]:
    """Get daily statistics for a client."""
    from sqlalchemy import select, func, and_
    from app.db.models import Lead, Conversation, Escalation, LeadScore
    
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())
    
    # Total leads
    result = await db.execute(
        select(func.count(Lead.id))
        .where(Lead.client_id == client_id)
        .where(Lead.created_at.between(start, end))
    )
    total_leads = result.scalar() or 0
    
    # Hot leads
    result = await db.execute(
        select(func.count(Lead.id))
        .where(Lead.client_id == client_id)
        .where(Lead.created_at.between(start, end))
        .where(Lead.score == LeadScore.HOT)
    )
    hot_leads = result.scalar() or 0
    
    # Conversations
    result = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.client_id == client_id)
        .where(Conversation.created_at.between(start, end))
    )
    conversations = result.scalar() or 0
    
    # Escalations
    result = await db.execute(
        select(func.count(Escalation.id))
        .where(Escalation.client_id == client_id)
        .where(Escalation.created_at.between(start, end))
    )
    escalations = result.scalar() or 0
    
    # Appointments (leads with appointment in date range)
    result = await db.execute(
        select(func.count(Lead.id))
        .where(Lead.client_id == client_id)
        .where(Lead.appointment_at.between(start, end))
    )
    appointments = result.scalar() or 0
    
    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "appointments_booked": appointments,
        "conversations_handled": conversations,
        "escalations": escalations,
    }


# ============================================================================
# Maintenance Tasks
# ============================================================================

@celery_app.task(bind=True, base=AsyncTask, name="app.worker.cleanup_old_data")
def cleanup_old_data(self) -> dict[str, Any]:
    """Clean up old conversation data (per retention policy)."""
    async def _cleanup():
        from app.db.session import get_async_session
        from sqlalchemy import delete
        from app.db.models import Message, Conversation
        
        async with get_async_session() as db:
            # Delete messages older than 90 days
            cutoff = datetime.utcnow() - timedelta(days=90)
            
            result = await db.execute(
                delete(Message).where(Message.created_at < cutoff)
            )
            deleted_messages = result.rowcount
            
            # Delete empty conversations
            result = await db.execute(
                delete(Conversation)
                .where(Conversation.created_at < cutoff)
                .where(Conversation.message_count == 0)
            )
            deleted_conversations = result.rowcount
            
            await db.commit()
            
            return {
                "deleted_messages": deleted_messages,
                "deleted_conversations": deleted_conversations,
            }
    
    return self.run_async(_cleanup())


@celery_app.task(bind=True, base=AsyncTask, name="app.worker.update_token_usage")
def update_token_usage(
    self,
    client_id: str,
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> dict[str, Any]:
    """Update client token usage (called after each AI interaction)."""
    async def _update():
        from app.db.session import get_async_session
        from app.services.client_service import ClientService
        
        async with get_async_session() as db:
            client_service = ClientService(db)
            await client_service.track_token_usage(
                client_id=UUID(client_id),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            
            return {"status": "updated"}
    
    return self.run_async(_update())


# ============================================================================
# Knowledge Base Tasks
# ============================================================================

@celery_app.task(bind=True, base=AsyncTask, name="app.worker.ingest_document")
def ingest_document(
    self,
    kb_id: str,
    content: str,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest document into knowledge base (async)."""
    async def _ingest():
        from app.db.session import get_async_session
        from app.services.knowledge_service import KnowledgeService
        
        async with get_async_session() as db:
            kb_service = KnowledgeService(db)
            chunks = await kb_service.ingest_document(
                kb_id=UUID(kb_id),
                content=content,
                source=source,
                metadata=metadata,
            )
            
            return {"status": "ingested", "chunks": chunks}
    
    return self.run_async(_ingest())


@celery_app.task(bind=True, base=AsyncTask, name="app.worker.bulk_ingest_faqs")
def bulk_ingest_faqs(
    self,
    kb_id: str,
    faqs: list[dict[str, str]],
) -> dict[str, Any]:
    """Bulk ingest FAQs into knowledge base."""
    async def _ingest():
        from app.db.session import get_async_session
        from app.services.knowledge_service import KnowledgeService
        
        async with get_async_session() as db:
            kb_service = KnowledgeService(db)
            total_chunks = await kb_service.bulk_ingest_faqs(
                kb_id=UUID(kb_id),
                faqs=faqs,
            )
            
            return {"status": "ingested", "total_chunks": total_chunks}
    
    return self.run_async(_ingest())
