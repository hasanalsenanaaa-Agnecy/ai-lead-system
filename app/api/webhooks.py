"""
Webhook Handlers
FastAPI routes for receiving leads from various channels
"""

import hashlib
import hmac
import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ChannelType, LeadStatus
from app.db.session import get_db_session
from app.services.lead_service import LeadService
from app.services.conversation_service import ConversationService
from app.integrations.whatsapp_service import get_whatsapp_service
from app.worker import (
    process_ai_response as process_ai_response_task,
    process_missed_call_followup as process_missed_call_followup_task,
    mark_whatsapp_as_read as mark_whatsapp_as_read_task,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# =============================================================================
# Request Models
# =============================================================================


class WebFormLead(BaseModel):
    """Lead submission from web form."""

    client_id: UUID
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    message: str
    service_interest: str | None = None
    source_campaign: str | None = None
    source_medium: str | None = None
    landing_page: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MissedCallWebhook(BaseModel):
    """Missed call notification."""

    client_id: UUID
    caller_phone: str
    caller_name: str | None = None
    called_number: str
    call_time: str
    voicemail_url: str | None = None


class LiveChatMessage(BaseModel):
    """Live chat widget message."""

    client_id: UUID
    session_id: str
    visitor_id: str | None = None
    name: str | None = None
    email: str | None = None
    message: str
    page_url: str | None = None
    user_agent: str | None = None


# =============================================================================
# Response Models
# =============================================================================


class WebhookResponse(BaseModel):
    """Standard webhook response."""

    success: bool
    message: str
    lead_id: UUID | None = None
    conversation_id: UUID | None = None


# =============================================================================
# Security Helpers
# =============================================================================


async def verify_client_api_key(
    x_api_key: Annotated[str, Header()],
    db: AsyncSession = Depends(get_db_session),
) -> UUID:
    """Verify client API key and return client_id."""
    from app.services.client_service import ClientService

    client_service = ClientService(db)
    client = await client_service.get_by_api_key(x_api_key)

    if not client:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return client.id


# =============================================================================
# Web Form Webhook
# =============================================================================


@router.post("/web-form", response_model=WebhookResponse)
async def receive_web_form(
    lead_data: WebFormLead,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receive lead from web form submission.
    Creates lead, starts conversation, and triggers AI response via Celery.
    """
    lead_service = LeadService(db)
    conversation_service = ConversationService(db)

    try:
        # Create or update lead
        lead = await lead_service.create_or_update_lead(
            client_id=lead_data.client_id,
            phone=lead_data.phone,
            email=lead_data.email,
            name=lead_data.name or f"{lead_data.first_name or ''} {lead_data.last_name or ''}".strip(),
            first_name=lead_data.first_name,
            last_name=lead_data.last_name,
            source_channel=ChannelType.WEB_FORM,
            source_campaign=lead_data.source_campaign,
            source_medium=lead_data.source_medium,
            landing_page=lead_data.landing_page,
            service_interest=lead_data.service_interest,
            metadata=lead_data.metadata,
        )

        # Create conversation
        conversation = await conversation_service.create_conversation(
            client_id=lead_data.client_id,
            lead_id=lead.id,
            channel=ChannelType.WEB_FORM,
        )

        # Add initial message
        await conversation_service.add_message(
            conversation_id=conversation.id,
            role="lead",
            content=lead_data.message,
        )

        # Queue AI response via Celery (retries, persistence, dead-letter)
        process_ai_response_task.delay(
            str(conversation.id),
            str(lead.id),
            str(lead_data.client_id),
        )

        return WebhookResponse(
            success=True,
            message="Lead received and processing",
            lead_id=lead.id,
            conversation_id=conversation.id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WhatsApp Webhook (Meta Cloud API)
# =============================================================================


@router.get("/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    """
    Handle Meta webhook verification challenge (GET).
    Meta sends: hub.mode, hub.verify_token, hub.challenge
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    wa = get_whatsapp_service()
    result = wa.verify_webhook_challenge(mode, token, challenge)

    if result is not None:
        return PlainTextResponse(content=result)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_whatsapp(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receive inbound WhatsApp messages via Meta Cloud API webhook.
    Payload format: { object: "whatsapp_business_account", entry: [...] }
    """
    body_bytes = await request.body()

    # Verify signature in production
    if settings.is_production:
        signature = request.headers.get("X-Hub-Signature-256", "")
        wa = get_whatsapp_service()
        if not wa.verify_signature(body_bytes, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    body = await request.json()

    # Meta sometimes sends status updates, not messages
    if body.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    wa = get_whatsapp_service()
    incoming_messages = wa.extract_messages(body)

    if not incoming_messages:
        # Might be a status update (delivered / read) – acknowledge it
        return {"status": "ok"}

    lead_service = LeadService(db)
    conversation_service = ConversationService(db)

    from app.services.client_service import ClientService
    client_service = ClientService(db)

    for msg in incoming_messages:
        from_phone = msg["from_phone"]
        message_id = msg["message_id"]
        text = msg["text"]
        profile_name = msg["profile_name"]

        if not text:
            # Skip non-text messages for now (images, stickers, etc.)
            continue

        # Find which client owns this WhatsApp number
        # The phone_number_id receiving this webhook is in the payload
        # For now, look up by the WhatsApp number in client config
        phone_number_id = None
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                meta_data = value.get("metadata", {})
                phone_number_id = meta_data.get("phone_number_id")
                display_phone = meta_data.get("display_phone_number")

        client = None
        if display_phone:
            client = await client_service.get_by_whatsapp_number(display_phone)
        if not client and phone_number_id:
            client = await client_service.get_by_whatsapp_phone_number_id(phone_number_id)

        if not client:
            # Could not match to a client – still acknowledge
            continue

        # Create or update lead
        lead = await lead_service.create_or_update_lead(
            client_id=client.id,
            phone=f"+{from_phone}",
            name=profile_name,
            source_channel=ChannelType.WHATSAPP,
        )

        # Find or create conversation
        conversation = await conversation_service.get_or_create_active_conversation(
            client_id=client.id,
            lead_id=lead.id,
            channel=ChannelType.WHATSAPP,
        )

        # Add message
        await conversation_service.add_message(
            conversation_id=conversation.id,
            role="lead",
            content=text,
            external_message_id=message_id,
        )

        # Mark as read via Celery
        mark_whatsapp_as_read_task.delay(message_id)

        # Queue AI response via Celery
        process_ai_response_task.delay(
            str(conversation.id),
            str(lead.id),
            str(client.id),
        )

    return {"status": "ok"}


# =============================================================================
# Live Chat Webhook
# =============================================================================


@router.post("/live-chat", response_model=WebhookResponse)
async def receive_live_chat(
    message: LiveChatMessage,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receive message from live chat widget.
    Queues AI response via Celery.
    """
    lead_service = LeadService(db)
    conversation_service = ConversationService(db)

    # Create or find lead
    lead = await lead_service.create_or_update_lead(
        client_id=message.client_id,
        email=message.email,
        name=message.name,
        source_channel=ChannelType.LIVE_CHAT,
        landing_page=message.page_url,
        metadata={"visitor_id": message.visitor_id, "user_agent": message.user_agent},
    )

    # Find or create conversation by session
    conversation = await conversation_service.get_or_create_by_session(
        client_id=message.client_id,
        lead_id=lead.id,
        session_id=message.session_id,
        channel=ChannelType.LIVE_CHAT,
    )

    # Add message
    await conversation_service.add_message(
        conversation_id=conversation.id,
        role="lead",
        content=message.message,
    )

    # Queue AI response via Celery
    process_ai_response_task.delay(
        str(conversation.id),
        str(lead.id),
        str(message.client_id),
    )

    return WebhookResponse(
        success=True,
        message="Message received",
        lead_id=lead.id,
        conversation_id=conversation.id,
    )


# =============================================================================
# Missed Call Webhook
# =============================================================================


@router.post("/missed-call", response_model=WebhookResponse)
async def receive_missed_call(
    call: MissedCallWebhook,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle missed call notification.
    Creates lead and initiates outbound WhatsApp follow-up via Celery.
    """
    lead_service = LeadService(db)
    conversation_service = ConversationService(db)

    # Create or find lead
    lead = await lead_service.create_or_update_lead(
        client_id=call.client_id,
        phone=call.caller_phone,
        name=call.caller_name,
        source_channel=ChannelType.MISSED_CALL,
        metadata={"voicemail_url": call.voicemail_url, "call_time": call.call_time},
    )

    # Create conversation
    conversation = await conversation_service.create_conversation(
        client_id=call.client_id,
        lead_id=lead.id,
        channel=ChannelType.MISSED_CALL,
    )

    # Queue missed call follow-up via Celery
    process_missed_call_followup_task.delay(
        str(conversation.id),
        str(lead.id),
        str(call.client_id),
        call.caller_phone,
    )

    return WebhookResponse(
        success=True,
        message="Missed call received, follow-up initiated",
        lead_id=lead.id,
        conversation_id=conversation.id,
    )


# NOTE: All background processing is now handled by Celery tasks in app/worker.py
# Tasks used: process_ai_response, process_missed_call_followup, mark_whatsapp_as_read
# This provides automatic retries, dead-letter queues, and task persistence via Redis.
