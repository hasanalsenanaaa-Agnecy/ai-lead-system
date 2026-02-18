"""
Twilio Integration Service.
Handles SMS, WhatsApp, and Voice communications.
"""
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
import structlog

from app.core.config import settings
from app.models.models import ChannelType

logger = structlog.get_logger()


class TwilioService:
    """
    Service for handling Twilio communications.
    Supports SMS, WhatsApp, and Voice.
    """
    
    def __init__(self):
        self.client = TwilioClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        self.default_from_number = settings.TWILIO_PHONE_NUMBER
        self.default_whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER
    
    def validate_webhook_request(
        self,
        url: str,
        params: Dict[str, str],
        signature: str
    ) -> bool:
        """
        Validate incoming Twilio webhook request.
        
        Args:
            url: The full URL of the webhook endpoint
            params: The POST parameters from the request
            signature: The X-Twilio-Signature header value
            
        Returns:
            True if request is valid, False otherwise
        """
        return self.validator.validate(url, params, signature)
    
    async def send_sms(
        self,
        to: str,
        body: str,
        from_number: Optional[str] = None,
        status_callback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an SMS message.
        
        Args:
            to: Recipient phone number (E.164 format)
            body: Message content
            from_number: Sender number (defaults to configured number)
            status_callback: URL for delivery status updates
            
        Returns:
            Dict with message SID and status
        """
        try:
            message = self.client.messages.create(
                to=to,
                from_=from_number or self.default_from_number,
                body=body,
                status_callback=status_callback
            )
            
            logger.info(
                "SMS sent",
                message_sid=message.sid,
                to=to,
                status=message.status
            )
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "channel": ChannelType.SMS.value
            }
            
        except TwilioRestException as e:
            logger.error(
                "Failed to send SMS",
                error=str(e),
                to=to
            )
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code
            }
    
    async def send_whatsapp(
        self,
        to: str,
        body: str,
        from_number: Optional[str] = None,
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message.
        
        Args:
            to: Recipient phone number (E.164 format, without whatsapp: prefix)
            body: Message content
            from_number: Sender number (defaults to configured WhatsApp number)
            media_url: Optional URL of media to include
            
        Returns:
            Dict with message SID and status
        """
        try:
            # Format WhatsApp numbers
            whatsapp_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
            whatsapp_from = from_number or self.default_whatsapp_number
            if not whatsapp_from.startswith("whatsapp:"):
                whatsapp_from = f"whatsapp:{whatsapp_from}"
            
            params = {
                "to": whatsapp_to,
                "from_": whatsapp_from,
                "body": body
            }
            
            if media_url:
                params["media_url"] = [media_url]
            
            message = self.client.messages.create(**params)
            
            logger.info(
                "WhatsApp message sent",
                message_sid=message.sid,
                to=to,
                status=message.status
            )
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "channel": ChannelType.WHATSAPP.value
            }
            
        except TwilioRestException as e:
            logger.error(
                "Failed to send WhatsApp message",
                error=str(e),
                to=to
            )
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code
            }
    
    async def send_message(
        self,
        to: str,
        body: str,
        channel: ChannelType,
        from_number: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send message on specified channel.
        
        Args:
            to: Recipient phone number
            body: Message content
            channel: ChannelType (SMS, WHATSAPP)
            from_number: Optional sender number
            
        Returns:
            Dict with message SID and status
        """
        if channel == ChannelType.SMS:
            return await self.send_sms(to, body, from_number, **kwargs)
        elif channel == ChannelType.WHATSAPP:
            return await self.send_whatsapp(to, body, from_number, **kwargs)
        else:
            return {
                "success": False,
                "error": f"Unsupported channel: {channel}"
            }
    
    async def send_templated_whatsapp(
        self,
        to: str,
        template_sid: str,
        template_variables: Dict[str, str],
        from_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp template message (for business-initiated conversations).
        
        Args:
            to: Recipient phone number
            template_sid: Twilio content template SID
            template_variables: Variables to substitute in template
            from_number: Sender number
            
        Returns:
            Dict with message SID and status
        """
        try:
            whatsapp_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
            whatsapp_from = from_number or self.default_whatsapp_number
            if not whatsapp_from.startswith("whatsapp:"):
                whatsapp_from = f"whatsapp:{whatsapp_from}"
            
            message = self.client.messages.create(
                to=whatsapp_to,
                from_=whatsapp_from,
                content_sid=template_sid,
                content_variables=template_variables
            )
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "channel": ChannelType.WHATSAPP.value
            }
            
        except TwilioRestException as e:
            logger.error(
                "Failed to send templated WhatsApp",
                error=str(e),
                to=to
            )
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code
            }
    
    def parse_incoming_message(
        self,
        webhook_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse incoming webhook data from Twilio.
        
        Args:
            webhook_data: Raw webhook POST data
            
        Returns:
            Normalized message data
        """
        # Determine channel
        from_number = webhook_data.get("From", "")
        to_number = webhook_data.get("To", "")
        
        is_whatsapp = from_number.startswith("whatsapp:") or to_number.startswith("whatsapp:")
        channel = ChannelType.WHATSAPP if is_whatsapp else ChannelType.SMS
        
        # Clean phone numbers
        clean_from = from_number.replace("whatsapp:", "")
        clean_to = to_number.replace("whatsapp:", "")
        
        return {
            "message_sid": webhook_data.get("MessageSid"),
            "account_sid": webhook_data.get("AccountSid"),
            "from_number": clean_from,
            "to_number": clean_to,
            "body": webhook_data.get("Body", ""),
            "channel": channel,
            "num_media": int(webhook_data.get("NumMedia", 0)),
            "media_urls": self._extract_media_urls(webhook_data),
            "from_city": webhook_data.get("FromCity"),
            "from_state": webhook_data.get("FromState"),
            "from_country": webhook_data.get("FromCountry"),
            "from_zip": webhook_data.get("FromZip"),
            "timestamp": datetime.utcnow()
        }
    
    def _extract_media_urls(self, webhook_data: Dict[str, Any]) -> List[str]:
        """Extract media URLs from webhook data."""
        media_urls = []
        num_media = int(webhook_data.get("NumMedia", 0))
        
        for i in range(num_media):
            url = webhook_data.get(f"MediaUrl{i}")
            if url:
                media_urls.append(url)
        
        return media_urls
    
    def generate_twiml_response(
        self,
        message: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> str:
        """
        Generate TwiML response for webhook.
        
        Args:
            message: Optional message to send back
            action_url: Optional URL for further actions
            
        Returns:
            TwiML XML string
        """
        from twilio.twiml.messaging_response import MessagingResponse
        
        response = MessagingResponse()
        
        if message:
            response.message(message)
        
        return str(response)
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get status of a sent message."""
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "message_sid": message.sid,
                "status": message.status,
                "date_sent": message.date_sent,
                "date_updated": message.date_updated,
                "error_code": message.error_code,
                "error_message": message.error_message
            }
            
        except TwilioRestException as e:
            return {
                "error": str(e),
                "message_sid": message_sid
            }
    
    async def lookup_phone(self, phone_number: str) -> Dict[str, Any]:
        """
        Lookup phone number details using Twilio Lookup API.
        
        Args:
            phone_number: Phone number to lookup
            
        Returns:
            Phone number details
        """
        try:
            lookup = self.client.lookups.v2.phone_numbers(phone_number).fetch()
            
            return {
                "phone_number": lookup.phone_number,
                "valid": lookup.valid,
                "country_code": lookup.country_code,
                "national_format": lookup.national_format,
                "carrier": lookup.carrier if hasattr(lookup, 'carrier') else None
            }
            
        except TwilioRestException as e:
            logger.error("Phone lookup failed", error=str(e), phone=phone_number)
            return {
                "phone_number": phone_number,
                "valid": None,
                "error": str(e)
            }


class NotificationService:
    """Service for sending notifications to client team."""
    
    def __init__(self):
        self.twilio_service = TwilioService()
    
    async def notify_hot_lead(
        self,
        client_phone_numbers: List[str],
        lead_name: str,
        lead_phone: str,
        service_interest: str,
        summary: str
    ) -> List[Dict[str, Any]]:
        """
        Send hot lead notification to client team.
        
        Args:
            client_phone_numbers: List of phone numbers to notify
            lead_name: Lead's name
            lead_phone: Lead's phone number
            service_interest: What they're interested in
            summary: Brief conversation summary
            
        Returns:
            List of send results
        """
        message = f"""🔥 HOT LEAD ALERT!

Name: {lead_name or 'Unknown'}
Phone: {lead_phone}
Interest: {service_interest or 'Not specified'}

Summary: {summary[:200]}

Reply to this lead ASAP!"""

        results = []
        for phone in client_phone_numbers:
            result = await self.twilio_service.send_sms(
                to=phone,
                body=message
            )
            results.append(result)
        
        return results
    
    async def notify_handoff(
        self,
        client_phone_numbers: List[str],
        lead_name: str,
        lead_phone: str,
        reason: str,
        conversation_summary: str
    ) -> List[Dict[str, Any]]:
        """Send handoff notification to client team."""
        message = f"""⚠️ HANDOFF REQUESTED

Lead: {lead_name or 'Unknown'} ({lead_phone})
Reason: {reason}

Context: {conversation_summary[:250]}

Please follow up with this lead."""

        results = []
        for phone in client_phone_numbers:
            result = await self.twilio_service.send_sms(
                to=phone,
                body=message
            )
            results.append(result)
        
        return results


# Export service instances
twilio_service = TwilioService()
notification_service = NotificationService()
