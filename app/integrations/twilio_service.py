"""
Twilio Integration
SMS and WhatsApp message delivery via Twilio API
"""

import hashlib
import hmac
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class TwilioService:
    """
    Twilio integration for SMS and WhatsApp messaging.
    
    Features:
    - Send SMS messages
    - Send WhatsApp messages
    - Webhook signature verification
    - Message status tracking
    - Rate limiting awareness
    """

    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.phone_number = settings.twilio_phone_number
        self.whatsapp_number = settings.twilio_whatsapp_number
        self.webhook_url = settings.twilio_webhook_url
        
        # API base URL
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"

    # =========================================================================
    # SMS
    # =========================================================================

    async def send_sms(
        self,
        to: str,
        body: str,
        from_number: str | None = None,
        status_callback: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an SMS message.
        
        Args:
            to: Recipient phone number (E.164 format)
            body: Message content
            from_number: Sender number (defaults to configured number)
            status_callback: URL to receive status updates
            
        Returns:
            Twilio message response
        """
        if not self._is_configured():
            logger.warning("Twilio not configured, skipping SMS")
            return {"status": "skipped", "reason": "not_configured"}

        from_number = from_number or self.phone_number
        
        payload = {
            "To": self._normalize_phone(to),
            "From": from_number,
            "Body": body[:1600],  # SMS character limit
        }
        
        if status_callback:
            payload["StatusCallback"] = status_callback
        
        try:
            response = await self._make_request(
                "POST",
                f"{self.base_url}/Messages.json",
                data=payload,
            )
            
            logger.info(
                "SMS sent",
                message_sid=response.get("sid"),
                to=to,
                status=response.get("status"),
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to send SMS", error=str(e), to=to)
            raise

    async def send_sms_batch(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """
        Send multiple SMS messages.
        
        Args:
            messages: List of {"to": str, "body": str}
            
        Returns:
            List of responses
        """
        results = []
        for msg in messages:
            try:
                result = await self.send_sms(
                    to=msg["to"],
                    body=msg["body"],
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "status": "failed",
                    "error": str(e),
                    "to": msg["to"],
                })
        
        return results

    # =========================================================================
    # WhatsApp
    # =========================================================================

    async def send_whatsapp(
        self,
        to: str,
        body: str,
        from_number: str | None = None,
        media_url: str | None = None,
        status_callback: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a WhatsApp message.
        
        Args:
            to: Recipient phone number (E.164 format, without whatsapp: prefix)
            body: Message content
            from_number: Sender WhatsApp number (defaults to configured)
            media_url: Optional media URL to attach
            status_callback: URL to receive status updates
            
        Returns:
            Twilio message response
        """
        if not self._is_configured():
            logger.warning("Twilio not configured, skipping WhatsApp")
            return {"status": "skipped", "reason": "not_configured"}

        from_number = from_number or self.whatsapp_number
        
        # Ensure WhatsApp prefix
        to_formatted = self._format_whatsapp_number(to)
        from_formatted = self._format_whatsapp_number(from_number)
        
        payload = {
            "To": to_formatted,
            "From": from_formatted,
            "Body": body,
        }
        
        if media_url:
            payload["MediaUrl"] = media_url
            
        if status_callback:
            payload["StatusCallback"] = status_callback
        
        try:
            response = await self._make_request(
                "POST",
                f"{self.base_url}/Messages.json",
                data=payload,
            )
            
            logger.info(
                "WhatsApp message sent",
                message_sid=response.get("sid"),
                to=to,
                status=response.get("status"),
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to send WhatsApp", error=str(e), to=to)
            raise

    async def send_whatsapp_template(
        self,
        to: str,
        template_sid: str,
        template_variables: dict[str, str] | None = None,
        from_number: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a WhatsApp template message.
        Required for initiating conversations outside 24-hour window.
        
        Args:
            to: Recipient phone number
            template_sid: Twilio content template SID
            template_variables: Variables for template placeholders
            from_number: Sender WhatsApp number
            
        Returns:
            Twilio message response
        """
        if not self._is_configured():
            logger.warning("Twilio not configured, skipping WhatsApp template")
            return {"status": "skipped", "reason": "not_configured"}

        from_number = from_number or self.whatsapp_number
        
        to_formatted = self._format_whatsapp_number(to)
        from_formatted = self._format_whatsapp_number(from_number)
        
        payload = {
            "To": to_formatted,
            "From": from_formatted,
            "ContentSid": template_sid,
        }
        
        if template_variables:
            payload["ContentVariables"] = str(template_variables)
        
        try:
            response = await self._make_request(
                "POST",
                f"{self.base_url}/Messages.json",
                data=payload,
            )
            
            logger.info(
                "WhatsApp template sent",
                message_sid=response.get("sid"),
                to=to,
                template_sid=template_sid,
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to send WhatsApp template", error=str(e))
            raise

    # =========================================================================
    # Voice (Outbound Call for Hot Lead Alert)
    # =========================================================================

    async def make_call(
        self,
        to: str,
        twiml_url: str | None = None,
        twiml: str | None = None,
        from_number: str | None = None,
        status_callback: str | None = None,
    ) -> dict[str, Any]:
        """
        Make an outbound call.
        Used for hot lead alerts to client.
        
        Args:
            to: Phone number to call
            twiml_url: URL returning TwiML instructions
            twiml: Inline TwiML (alternative to URL)
            from_number: Caller ID
            status_callback: Status callback URL
            
        Returns:
            Twilio call response
        """
        if not self._is_configured():
            logger.warning("Twilio not configured, skipping call")
            return {"status": "skipped", "reason": "not_configured"}

        from_number = from_number or self.phone_number
        
        payload = {
            "To": self._normalize_phone(to),
            "From": from_number,
        }
        
        if twiml_url:
            payload["Url"] = twiml_url
        elif twiml:
            payload["Twiml"] = twiml
        else:
            # Default: simple announcement
            payload["Twiml"] = "<Response><Say>You have a new hot lead waiting.</Say></Response>"
        
        if status_callback:
            payload["StatusCallback"] = status_callback
        
        try:
            response = await self._make_request(
                "POST",
                f"{self.base_url}/Calls.json",
                data=payload,
            )
            
            logger.info(
                "Outbound call initiated",
                call_sid=response.get("sid"),
                to=to,
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to make call", error=str(e), to=to)
            raise

    # =========================================================================
    # Webhook Verification
    # =========================================================================

    def verify_signature(
        self,
        url: str,
        params: dict[str, str],
        signature: str,
    ) -> bool:
        """
        Verify Twilio webhook signature.
        
        Args:
            url: Full webhook URL
            params: POST parameters from webhook
            signature: X-Twilio-Signature header value
            
        Returns:
            True if signature is valid
        """
        if not self.auth_token:
            logger.warning("Auth token not set, cannot verify signature")
            return False
        
        # Sort parameters and append to URL
        sorted_params = sorted(params.items())
        data = url + "".join(f"{k}{v}" for k, v in sorted_params)
        
        # Calculate expected signature
        expected = hmac.new(
            self.auth_token.encode(),
            data.encode(),
            hashlib.sha1,
        ).digest()
        
        import base64
        expected_b64 = base64.b64encode(expected).decode()
        
        return hmac.compare_digest(expected_b64, signature)

    # =========================================================================
    # Message Status
    # =========================================================================

    async def get_message(self, message_sid: str) -> dict[str, Any]:
        """Get message details by SID."""
        if not self._is_configured():
            return {"status": "error", "reason": "not_configured"}
        
        try:
            return await self._make_request(
                "GET",
                f"{self.base_url}/Messages/{message_sid}.json",
            )
        except Exception as e:
            logger.error("Failed to get message", error=str(e), sid=message_sid)
            raise

    # =========================================================================
    # Phone Number Lookup
    # =========================================================================

    async def lookup_phone(
        self,
        phone_number: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Look up phone number information.
        
        Args:
            phone_number: Phone number to look up
            fields: Optional fields to include (caller_name, line_type_intelligence)
            
        Returns:
            Lookup response with phone info
        """
        if not self._is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        url = f"https://lookups.twilio.com/v2/PhoneNumbers/{self._normalize_phone(phone_number)}"
        
        params = {}
        if fields:
            params["Fields"] = ",".join(fields)
        
        try:
            return await self._make_request("GET", url, params=params)
        except Exception as e:
            logger.error("Lookup failed", error=str(e))
            raise

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _is_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        return bool(self.account_sid and self.auth_token)

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format."""
        # Remove any non-digit characters except +
        cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
        
        # Ensure + prefix
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        
        return cleaned

    def _format_whatsapp_number(self, phone: str) -> str:
        """Format phone number for WhatsApp."""
        normalized = self._normalize_phone(phone)
        
        # Remove existing whatsapp: prefix if present
        if normalized.startswith("whatsapp:"):
            normalized = normalized[9:]
        
        return f"whatsapp:{normalized}"

    async def _make_request(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to Twilio API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                auth=(self.account_sid, self.auth_token),
                data=data,
                params=params,
            )
            
            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                logger.error(
                    "Twilio API error",
                    status=response.status_code,
                    error=error_data,
                )
                response.raise_for_status()
            
            return response.json()


# Singleton instance
_twilio_service: TwilioService | None = None


def get_twilio_service() -> TwilioService:
    """Get singleton Twilio service instance."""
    global _twilio_service
    if _twilio_service is None:
        _twilio_service = TwilioService()
    return _twilio_service
