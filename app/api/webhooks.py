"""
Webhook Handlers
FastAPI routes for receiving leads from various channels
"""

import hashlib
import hmac
import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ChannelType, LeadStatus
from app.db.session import get_db_session
from app.services.lead_service import LeadService
from app.services.conversation_service import ConversationService

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


class SMSInbound(BaseModel):
    """Inbound SMS message (Twilio format)."""

    From: str = Field(..., alias="From")
    To: str = Field(..., alias="To")
    Body: str = Field(..., alias="Body")
    MessageSid: str = Field(..., alias="MessageSid")
    AccountSid: str = Field(..., alias="AccountSid")
    NumMedia: str = Field(default="0", alias="NumMedia")


class WhatsAppInbound(BaseModel):
    """Inbound WhatsApp message (Twilio format)."""

    From: str = Field(..., alias="From")
    To: str = Field(..., alias="To")
    Body: str = Field(..., alias="Body")
    MessageSid: str = Field(..., alias="MessageSid")
    AccountSid: str = Field(..., alias="AccountSid")
    ProfileName: str | None = Field(default=None, alias="ProfileName")
    WaId: str | None = Field(default=None, alias="WaId")


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


class TwilioResponse(BaseModel):
    """Response format for Twilio webhooks."""

    # Twilio expects TwiML, but for API responses we use this
    success: bool
    message_sid: str | None = None


# =============================================================================
# Security Helpers
# =============================================================================


def verify_twilio_signature(
    request: Request,
    signature: str,
    url: str,
    params: dict[str, Any],
) -> bool:
    """Verify Twilio webhook signature."""
    if not settings.twilio_auth_token:
        return False

    # Build the string to sign
    sorted_params = sorted(params.items())
    param_string = "".join(f"{k}{v}" for k, v in sorted_params)
    full_string = url + param_string

    # Calculate expected signature
    expected = hmac.new(
        settings.twilio_auth_token.get_secret_value().encode(),
        full_string.encode(),
        hashlib.sha1,
    ).digest()

    import base64

    expected_b64 = base64.b64encode(expected).decode()

    return hmac.compare_digest(signature, expected_b64)


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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receive lead from web form submission.
    Creates lead, starts conversation, and triggers AI response.
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

        # Queue AI response processing
        background_tasks.add_task(
            process_ai_response,
            conversation_id=conversation.id,
            lead_id=lead.id,
            client_id=lead_data.client_id,
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
# SMS Webhook (Twilio)
# =============================================================================


@router.post("/sms/inbound")
async def receive_sms(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receive inbound SMS via Twilio webhook.
    """
    # Parse form data
    form_data = await request.form()
    data = dict(form_data)

    # Verify Twilio signature in production
    if settings.is_production:
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        if not verify_twilio_signature(request, signature, url, data):
            raise HTTPException(status_code=403, detail="Invalid signature")

    sms = SMSInbound(**data)
    lead_service = LeadService(db)
    conversation_service = ConversationService(db)

    # Find client by Twilio number
    from app.services.client_service import ClientService

    client_service = ClientService(db)
    client = await client_service.get_by_phone_number(sms.To)

    if not client:
        raise HTTPException(status_code=404, detail="Client not found for this number")

    # Create or find lead
    lead = await lead_service.create_or_update_lead(
        client_id=client.id,
        phone=sms.From,
        source_channel=ChannelType.SMS,
    )

    # Find or create conversation
    conversation = await conversation_service.get_or_create_active_conversation(
        client_id=client.id,
        lead_id=lead.id,
        channel=ChannelType.SMS,
    )

    # Add message
    await conversation_service.add_message(
        conversation_id=conversation.id,
        role="lead",
        content=sms.Body,
        external_message_id=sms.MessageSid,
    )

    # Queue AI response
    background_tasks.add_task(
        process_ai_response,
        conversation_id=conversation.id,
        lead_id=lead.id,
        client_id=client.id,
    )

    # Return TwiML empty response (we'll send reply separately)
    return {"success": True, "message_sid": sms.MessageSid}


# =============================================================================
# WhatsApp Webhook (Twilio)
# =============================================================================


@router.post("/whatsapp/inbound")
async def receive_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receive inbound WhatsApp message via Twilio webhook.
    """
    form_data = await request.form()
    data = dict(form_data)

    # Verify signature in production
    if settings.is_production:
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        if not verify_twilio_signature(request, signature, url, data):
            raise HTTPException(status_code=403, detail="Invalid signature")

    wa = WhatsAppInbound(**data)
    lead_service = LeadService(db)
    conversation_service = ConversationService(db)

    # Extract phone number (remove 'whatsapp:' prefix)
    from_phone = wa.From.replace("whatsapp:", "")
    to_phone = wa.To.replace("whatsapp:", "")

    # Find client
    from app.services.client_service import ClientService

    client_service = ClientService(db)
    client = await client_service.get_by_whatsapp_number(to_phone)

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Create or find lead
    lead = await lead_service.create_or_update_lead(
        client_id=client.id,
        phone=from_phone,
        name=wa.ProfileName,
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
        content=wa.Body,
        external_message_id=wa.MessageSid,
    )

    # Queue AI response
    background_tasks.add_task(
        process_ai_response,
        conversation_id=conversation.id,
        lead_id=lead.id,
        client_id=client.id,
    )

    return {"success": True, "message_sid": wa.MessageSid}


# =============================================================================
# Live Chat Webhook
# =============================================================================


@router.post("/live-chat", response_model=WebhookResponse)
async def receive_live_chat(
    message: LiveChatMessage,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Receive message from live chat widget.
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

    # Queue AI response
    background_tasks.add_task(
        process_ai_response,
        conversation_id=conversation.id,
        lead_id=lead.id,
        client_id=message.client_id,
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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle missed call notification.
    Creates lead and initiates outbound SMS/WhatsApp.
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

    # Queue missed call follow-up
    background_tasks.add_task(
        process_missed_call_followup,
        conversation_id=conversation.id,
        lead_id=lead.id,
        client_id=call.client_id,
        caller_phone=call.caller_phone,
    )

    return WebhookResponse(
        success=True,
        message="Missed call received, follow-up initiated",
        lead_id=lead.id,
        conversation_id=conversation.id,
    )


# =============================================================================
# Background Task Handlers
# =============================================================================


async def process_ai_response(
    conversation_id: UUID,
    lead_id: UUID,
    client_id: UUID,
) -> None:
    """
    Background task to process AI response for a message.
    """
    from app.db.session import get_db_context
    from app.services.orchestrator import ConversationOrchestrator

    async with get_db_context() as db:
        orchestrator = ConversationOrchestrator(db)
        await orchestrator.process_and_respond(
            conversation_id=conversation_id,
            lead_id=lead_id,
            client_id=client_id,
        )


async def process_missed_call_followup(
    conversation_id: UUID,
    lead_id: UUID,
    client_id: UUID,
    caller_phone: str,
) -> None:
    """
    Background task to send missed call follow-up message.
    """
    from app.db.session import get_db_context
    from app.services.orchestrator import ConversationOrchestrator

    async with get_db_context() as db:
        orchestrator = ConversationOrchestrator(db)
        await orchestrator.send_missed_call_followup(
            conversation_id=conversation_id,
            lead_id=lead_id,
            client_id=client_id,
            phone=caller_phone,
        )
