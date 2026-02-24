"""
Meta WhatsApp Cloud API Integration
Handles sending and receiving WhatsApp messages via the Meta (Facebook) Cloud API.
"""

import hashlib
import hmac
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class WhatsAppService:
    """
    Client for Meta WhatsApp Cloud API.

    Required settings:
        - meta_whatsapp_token          : Permanent system-user token or temp token
        - meta_whatsapp_phone_number_id: Phone-number ID (not the phone number itself)
        - meta_app_secret              : App secret for webhook signature verification
        - meta_webhook_verify_token    : Arbitrary string you set in Meta dashboard
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def _is_configured(self) -> bool:
        return bool(
            settings.meta_whatsapp_token
            and settings.meta_whatsapp_phone_number_id
        )

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            token = settings.meta_whatsapp_token.get_secret_value() if settings.meta_whatsapp_token else ""
            self._client = httpx.AsyncClient(
                base_url=GRAPH_API_BASE,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Sending messages
    # ------------------------------------------------------------------

    async def send_message(
        self,
        to: str,
        text: str,
        *,
        phone_number_id: str | None = None,
        preview_url: bool = False,
    ) -> dict[str, Any]:
        """
        Send a plain-text WhatsApp message.

        Args:
            to: Recipient phone number in international format (e.g. "+14155238886").
            text: Message body.
            phone_number_id: Override the default phone-number-id from settings.
            preview_url: Whether to render URL previews in the message.

        Returns:
            Meta API response dict containing ``messages[0].id`` (the wamid).
        """
        if not self._is_configured():
            logger.warning("WhatsApp service not configured – message not sent")
            return {"status": "not_configured"}

        pid = phone_number_id or settings.meta_whatsapp_phone_number_id
        recipient = self._normalize_phone(to)

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text,
            },
        }

        return await self._post(f"/{pid}/messages", payload)

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en_US",
        components: list[dict[str, Any]] | None = None,
        *,
        phone_number_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a pre-approved template message (required outside 24-hour window).

        Args:
            to: Recipient phone number.
            template_name: Name of the approved template.
            language_code: Template language, e.g. ``en_US``.
            components: Optional header / body / button parameter components.
            phone_number_id: Override the default phone-number-id.
        """
        if not self._is_configured():
            logger.warning("WhatsApp service not configured – template not sent")
            return {"status": "not_configured"}

        pid = phone_number_id or settings.meta_whatsapp_phone_number_id
        recipient = self._normalize_phone(to)

        template_obj: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template_obj["components"] = components

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": template_obj,
        }

        return await self._post(f"/{pid}/messages", payload)

    async def send_media(
        self,
        to: str,
        media_type: str,
        media_url: str,
        caption: str | None = None,
        *,
        phone_number_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an image / video / document / audio message.

        Args:
            to: Recipient phone number.
            media_type: One of ``image``, ``video``, ``document``, ``audio``.
            media_url: Public URL of the media file.
            caption: Optional caption (images / videos / documents only).
        """
        if not self._is_configured():
            return {"status": "not_configured"}

        pid = phone_number_id or settings.meta_whatsapp_phone_number_id
        recipient = self._normalize_phone(to)

        media_obj: dict[str, Any] = {"link": media_url}
        if caption and media_type in ("image", "video", "document"):
            media_obj["caption"] = caption

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": media_type,
            media_type: media_obj,
        }

        return await self._post(f"/{pid}/messages", payload)

    async def mark_as_read(
        self,
        message_id: str,
        *,
        phone_number_id: str | None = None,
    ) -> dict[str, Any]:
        """Mark an incoming message as read (sends blue ticks)."""
        if not self._is_configured():
            return {"status": "not_configured"}

        pid = phone_number_id or settings.meta_whatsapp_phone_number_id

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return await self._post(f"/{pid}/messages", payload)

    # ------------------------------------------------------------------
    # Webhook verification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def verify_webhook_challenge(
        mode: str | None,
        token: str | None,
        challenge: str | None,
    ) -> str | None:
        """
        Handle the Meta webhook *verification request* (GET).

        Returns the ``hub.challenge`` value if mode == "subscribe" and
        the token matches, else ``None``.
        """
        if (
            mode == "subscribe"
            and token
            and token == settings.meta_webhook_verify_token
        ):
            return challenge
        return None

    @staticmethod
    def verify_signature(payload_bytes: bytes, signature_header: str) -> bool:
        """
        Validate the ``X-Hub-Signature-256`` header on incoming webhooks.

        Args:
            payload_bytes: Raw request body bytes.
            signature_header: Value of ``X-Hub-Signature-256`` header
                              (format: ``sha256=<hex>``).
        """
        if not settings.meta_app_secret:
            logger.warning("meta_app_secret not set – skipping signature check")
            return True  # allow in dev, enforce in prod via settings

        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_sig = hmac.new(
            settings.meta_app_secret.get_secret_value().encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, signature_header[7:])

    # ------------------------------------------------------------------
    # Parsing helpers (for incoming webhook payloads)
    # ------------------------------------------------------------------

    @staticmethod
    def extract_messages(body: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract message objects from a Meta webhook payload.

        Returns a list of dicts, each with:
            - from_phone: sender phone number
            - message_id: ``wamid.*``
            - timestamp: Unix timestamp string
            - type: ``text``, ``image``, ``interactive``, etc.
            - text: message body (for text messages)
            - profile_name: sender's WhatsApp profile name
            - raw: the original message dict
        """
        messages: list[dict[str, Any]] = []

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("messaging_product") != "whatsapp":
                    continue

                contacts = {
                    c["wa_id"]: c.get("profile", {}).get("name")
                    for c in value.get("contacts", [])
                }

                for msg in value.get("messages", []):
                    text_body = ""
                    if msg.get("type") == "text":
                        text_body = msg.get("text", {}).get("body", "")
                    elif msg.get("type") == "interactive":
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            text_body = interactive.get("button_reply", {}).get("title", "")
                        elif interactive.get("type") == "list_reply":
                            text_body = interactive.get("list_reply", {}).get("title", "")

                    messages.append(
                        {
                            "from_phone": msg.get("from"),
                            "message_id": msg.get("id"),
                            "timestamp": msg.get("timestamp"),
                            "type": msg.get("type"),
                            "text": text_body,
                            "profile_name": contacts.get(msg.get("from")),
                            "raw": msg,
                        }
                    )

        return messages

    @staticmethod
    def extract_statuses(body: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract message-status updates (sent, delivered, read, failed)."""
        statuses: list[dict[str, Any]] = []

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for status in value.get("statuses", []):
                    statuses.append(
                        {
                            "message_id": status.get("id"),
                            "status": status.get("status"),
                            "timestamp": status.get("timestamp"),
                            "recipient_id": status.get("recipient_id"),
                            "errors": status.get("errors"),
                        }
                    )

        return statuses

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request to the Graph API."""
        client = self._get_client()
        try:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(
                "WhatsApp API request succeeded",
                path=path,
                to=payload.get("to"),
                message_id=data.get("messages", [{}])[0].get("id") if data.get("messages") else None,
            )
            return data
        except httpx.HTTPStatusError as e:
            error_body = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else {}
            logger.error(
                "WhatsApp API error",
                path=path,
                status=e.response.status_code,
                error=error_body,
            )
            return {"error": error_body, "status_code": e.response.status_code}
        except Exception as e:
            logger.error("WhatsApp API request failed", path=path, error=str(e))
            return {"error": str(e)}

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Ensure phone is digits-only (no + prefix) as Meta API expects."""
        return phone.lstrip("+").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")


# --------------------------------------------------------------------------
# Module-level singleton
# --------------------------------------------------------------------------

_whatsapp_service: WhatsAppService | None = None


def get_whatsapp_service() -> WhatsAppService:
    """Return (or create) the module-level WhatsApp service singleton."""
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service
