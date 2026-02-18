"""
Webhook API routes for handling incoming messages from Twilio.
"""
import uuid
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, Depends, Form, Header
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.config import settings
from app.services.lead_service import lead_service
from app.integrations.twilio_integration import twilio_service, notification_service
from app.models.models import ChannelType, Client
from sqlalchemy import select

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def get_client_by_phone(
    db: AsyncSession,
    phone_number: str
) -> Client:
    """Find client by their Twilio phone number."""
    # Check SMS number
    result = await db.execute(
        select(Client).where(Client.twilio_phone_number == phone_number)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        # Check WhatsApp number (strip whatsapp: prefix if present)
        clean_number = phone_number.replace("whatsapp:", "")
        result = await db.execute(
            select(Client).where(Client.twilio_whatsapp_number == clean_number)
        )
        client = result.scalar_one_or_none()
    
    return client


@router.post("/twilio/sms")
async def handle_twilio_sms(
    request: Request,
    db: AsyncSession = Depends(get_db),
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(None),
    x_twilio_signature: str = Header(None, alias="X-Twilio-Signature")
):
    """
    Handle incoming SMS messages from Twilio.
    
    This endpoint receives webhooks from Twilio when SMS messages arrive.
    """
    try:
        # Validate Twilio signature in production
        if settings.ENVIRONMENT == "production":
            form_data = await request.form()
            form_dict = {k: v for k, v in form_data.items()}
            
            url = str(request.url)
            if not twilio_service.validate_webhook_request(url, form_dict, x_twilio_signature or ""):
                logger.warning("Invalid Twilio signature", url=url)
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Find client by phone number
        client = await get_client_by_phone(db, To)
        
        if not client:
            logger.warning("No client found for number", to_number=To)
            # Return empty TwiML - don't respond to unknown numbers
            return Response(
                content=twilio_service.generate_twiml_response(),
                media_type="application/xml"
            )
        
        # Process the message
        result = await lead_service.process_incoming_message(
            db=db,
            client_id=client.id,
            phone=From,
            message_text=Body,
            channel=ChannelType.SMS,
            external_message_id=MessageSid
        )
        
        # Send response if we have one
        if result.get("response_text"):
            # Send async response (don't use TwiML for better control)
            await twilio_service.send_sms(
                to=From,
                body=result["response_text"],
                from_number=To
            )
        
        # Send hot lead notification if needed
        if result.get("should_notify_human") and client.hot_lead_notification_phones:
            await notification_service.notify_hot_lead(
                client_phone_numbers=client.hot_lead_notification_phones,
                lead_name=result.get("entities", {}).get("name"),
                lead_phone=From,
                service_interest=result.get("entities", {}).get("service_needed"),
                summary=Body[:200]
            )
        
        # Return empty TwiML (we're sending response separately)
        return Response(
            content=twilio_service.generate_twiml_response(),
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error("SMS webhook error", error=str(e))
        # Return empty response to avoid Twilio retries
        return Response(
            content=twilio_service.generate_twiml_response(),
            media_type="application/xml"
        )


@router.post("/twilio/whatsapp")
async def handle_twilio_whatsapp(
    request: Request,
    db: AsyncSession = Depends(get_db),
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(default=""),
    MessageSid: str = Form(None),
    NumMedia: int = Form(default=0),
    x_twilio_signature: str = Header(None, alias="X-Twilio-Signature")
):
    """
    Handle incoming WhatsApp messages from Twilio.
    """
    try:
        # Validate signature in production
        if settings.ENVIRONMENT == "production":
            form_data = await request.form()
            form_dict = {k: v for k, v in form_data.items()}
            
            url = str(request.url)
            if not twilio_service.validate_webhook_request(url, form_dict, x_twilio_signature or ""):
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Clean WhatsApp prefixes
        clean_from = From.replace("whatsapp:", "")
        clean_to = To.replace("whatsapp:", "")
        
        # Find client
        client = await get_client_by_phone(db, clean_to)
        
        if not client:
            logger.warning("No client found for WhatsApp number", to_number=clean_to)
            return Response(
                content=twilio_service.generate_twiml_response(),
                media_type="application/xml"
            )
        
        # Handle media messages
        message_text = Body
        if NumMedia > 0 and not Body:
            message_text = "[Media message received]"
        
        # Process the message
        result = await lead_service.process_incoming_message(
            db=db,
            client_id=client.id,
            phone=clean_from,
            message_text=message_text,
            channel=ChannelType.WHATSAPP,
            external_message_id=MessageSid
        )
        
        # Send response
        if result.get("response_text"):
            await twilio_service.send_whatsapp(
                to=clean_from,
                body=result["response_text"],
                from_number=clean_to
            )
        
        # Notify for hot leads
        if result.get("should_notify_human") and client.hot_lead_notification_phones:
            await notification_service.notify_hot_lead(
                client_phone_numbers=client.hot_lead_notification_phones,
                lead_name=result.get("entities", {}).get("name"),
                lead_phone=clean_from,
                service_interest=result.get("entities", {}).get("service_needed"),
                summary=message_text[:200]
            )
        
        return Response(
            content=twilio_service.generate_twiml_response(),
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error("WhatsApp webhook error", error=str(e))
        return Response(
            content=twilio_service.generate_twiml_response(),
            media_type="application/xml"
        )


@router.post("/twilio/status")
async def handle_twilio_status(
    request: Request,
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    To: str = Form(None),
    ErrorCode: str = Form(None)
):
    """
    Handle message status callbacks from Twilio.
    """
    logger.info(
        "Message status update",
        message_sid=MessageSid,
        status=MessageStatus,
        to=To,
        error_code=ErrorCode
    )
    
    # TODO: Update message delivery status in database
    
    return {"status": "received"}


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoints."""
    return {"status": "healthy", "service": "webhooks"}
