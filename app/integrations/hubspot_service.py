"""
HubSpot CRM Integration
Contact management, deal tracking, and activity logging
"""

from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class HubSpotService:
    """
    HubSpot CRM integration.
    
    Features:
    - Contact create/update/search
    - Deal management
    - Activity logging (notes, calls, meetings)
    - Lead scoring sync
    - Custom properties
    """

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or settings.hubspot_access_token
        self.base_url = "https://api.hubapi.com"
        
    # =========================================================================
    # Contacts
    # =========================================================================

    async def create_contact(
        self,
        email: str | None = None,
        phone: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new contact in HubSpot.
        
        Args:
            email: Contact email
            phone: Contact phone
            first_name: First name
            last_name: Last name
            properties: Additional custom properties
            
        Returns:
            Created contact data
        """
        if not self._is_configured():
            logger.warning("HubSpot not configured, skipping contact creation")
            return {"status": "skipped", "reason": "not_configured"}

        contact_props = {}
        
        if email:
            contact_props["email"] = email
        if phone:
            contact_props["phone"] = phone
        if first_name:
            contact_props["firstname"] = first_name
        if last_name:
            contact_props["lastname"] = last_name
        if properties:
            contact_props.update(properties)

        payload = {"properties": contact_props}

        try:
            response = await self._make_request(
                "POST",
                "/crm/v3/objects/contacts",
                json=payload,
            )
            
            logger.info(
                "Contact created in HubSpot",
                contact_id=response.get("id"),
                email=email,
            )
            
            return response
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # Contact already exists, try to update instead
                logger.info("Contact exists, updating instead", email=email)
                existing = await self.search_contact_by_email(email)
                if existing:
                    return await self.update_contact(
                        existing["id"],
                        properties=contact_props,
                    )
            raise

    async def update_contact(
        self,
        contact_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update an existing contact.
        
        Args:
            contact_id: HubSpot contact ID
            properties: Properties to update
            
        Returns:
            Updated contact data
        """
        if not self._is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        payload = {"properties": properties}

        try:
            response = await self._make_request(
                "PATCH",
                f"/crm/v3/objects/contacts/{contact_id}",
                json=payload,
            )
            
            logger.info("Contact updated", contact_id=contact_id)
            return response
            
        except Exception as e:
            logger.error("Failed to update contact", error=str(e))
            raise

    async def get_contact(self, contact_id: str) -> dict[str, Any] | None:
        """Get contact by ID."""
        if not self._is_configured():
            return None

        try:
            return await self._make_request(
                "GET",
                f"/crm/v3/objects/contacts/{contact_id}",
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def search_contact_by_email(self, email: str) -> dict[str, Any] | None:
        """Search for a contact by email."""
        if not self._is_configured():
            return None

        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email,
                }]
            }],
            "properties": ["email", "phone", "firstname", "lastname", "lifecyclestage"],
        }

        try:
            response = await self._make_request(
                "POST",
                "/crm/v3/objects/contacts/search",
                json=payload,
            )
            
            results = response.get("results", [])
            return results[0] if results else None
            
        except Exception as e:
            logger.error("Contact search failed", error=str(e), email=email)
            return None

    async def search_contact_by_phone(self, phone: str) -> dict[str, Any] | None:
        """Search for a contact by phone number."""
        if not self._is_configured():
            return None

        # Normalize phone for search
        normalized = "".join(c for c in phone if c.isdigit())

        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "phone",
                    "operator": "CONTAINS_TOKEN",
                    "value": normalized[-10:],  # Last 10 digits
                }]
            }],
            "properties": ["email", "phone", "firstname", "lastname"],
        }

        try:
            response = await self._make_request(
                "POST",
                "/crm/v3/objects/contacts/search",
                json=payload,
            )
            
            results = response.get("results", [])
            return results[0] if results else None
            
        except Exception as e:
            logger.error("Contact search failed", error=str(e), phone=phone)
            return None

    async def create_or_update_contact(
        self,
        email: str | None = None,
        phone: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create or update a contact based on email/phone match.
        
        Searches for existing contact first, then creates or updates.
        """
        if not self._is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        # Try to find existing contact
        existing = None
        if email:
            existing = await self.search_contact_by_email(email)
        if not existing and phone:
            existing = await self.search_contact_by_phone(phone)

        properties = kwargs.get("properties", {})
        if email:
            properties["email"] = email
        if phone:
            properties["phone"] = phone

        if existing:
            return await self.update_contact(
                existing["id"],
                properties=properties,
            )
        else:
            return await self.create_contact(
                email=email,
                phone=phone,
                first_name=kwargs.get("first_name"),
                last_name=kwargs.get("last_name"),
                properties=properties,
            )

    # =========================================================================
    # Deals
    # =========================================================================

    async def create_deal(
        self,
        deal_name: str,
        pipeline: str | None = None,
        stage: str | None = None,
        amount: float | None = None,
        contact_id: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new deal in HubSpot.
        
        Args:
            deal_name: Deal name
            pipeline: Pipeline ID
            stage: Stage ID
            amount: Deal amount
            contact_id: Associated contact ID
            properties: Additional properties
            
        Returns:
            Created deal data
        """
        if not self._is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        deal_props = {
            "dealname": deal_name,
        }
        
        if pipeline:
            deal_props["pipeline"] = pipeline
        if stage:
            deal_props["dealstage"] = stage
        if amount is not None:
            deal_props["amount"] = str(amount)
        if properties:
            deal_props.update(properties)

        payload = {"properties": deal_props}

        try:
            response = await self._make_request(
                "POST",
                "/crm/v3/objects/deals",
                json=payload,
            )
            
            deal_id = response.get("id")
            
            # Associate with contact if provided
            if contact_id and deal_id:
                await self.associate_contact_deal(contact_id, deal_id)
            
            logger.info(
                "Deal created",
                deal_id=deal_id,
                name=deal_name,
            )
            
            return response
            
        except Exception as e:
            logger.error("Failed to create deal", error=str(e))
            raise

    async def update_deal(
        self,
        deal_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a deal."""
        if not self._is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        payload = {"properties": properties}

        try:
            response = await self._make_request(
                "PATCH",
                f"/crm/v3/objects/deals/{deal_id}",
                json=payload,
            )
            
            logger.info("Deal updated", deal_id=deal_id)
            return response
            
        except Exception as e:
            logger.error("Failed to update deal", error=str(e))
            raise

    async def update_deal_stage(
        self,
        deal_id: str,
        stage: str,
    ) -> dict[str, Any]:
        """Update deal stage."""
        return await self.update_deal(deal_id, {"dealstage": stage})

    # =========================================================================
    # Associations
    # =========================================================================

    async def associate_contact_deal(
        self,
        contact_id: str,
        deal_id: str,
    ) -> bool:
        """Associate a contact with a deal."""
        if not self._is_configured():
            return False

        try:
            await self._make_request(
                "PUT",
                f"/crm/v3/objects/contacts/{contact_id}/associations/deals/{deal_id}/contact_to_deal",
            )
            
            logger.debug(
                "Contact associated with deal",
                contact_id=contact_id,
                deal_id=deal_id,
            )
            return True
            
        except Exception as e:
            logger.error("Failed to associate contact/deal", error=str(e))
            return False

    # =========================================================================
    # Notes & Activities
    # =========================================================================

    async def create_note(
        self,
        body: str,
        contact_id: str | None = None,
        deal_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a note (engagement) in HubSpot.
        
        Args:
            body: Note content
            contact_id: Associated contact
            deal_id: Associated deal
            
        Returns:
            Created note data
        """
        if not self._is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        payload = {
            "properties": {
                "hs_note_body": body,
                "hs_timestamp": datetime.utcnow().isoformat() + "Z",
            }
        }

        try:
            response = await self._make_request(
                "POST",
                "/crm/v3/objects/notes",
                json=payload,
            )
            
            note_id = response.get("id")
            
            # Associate with contact/deal
            if note_id and contact_id:
                await self._associate_engagement(note_id, "contacts", contact_id)
            if note_id and deal_id:
                await self._associate_engagement(note_id, "deals", deal_id)
            
            logger.debug("Note created", note_id=note_id)
            return response
            
        except Exception as e:
            logger.error("Failed to create note", error=str(e))
            raise

    async def log_conversation(
        self,
        contact_id: str,
        summary: str,
        messages: list[dict[str, str]] | None = None,
        channel: str = "CHAT",
        deal_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Log a conversation as a note in HubSpot.
        
        Args:
            contact_id: Contact ID
            summary: Conversation summary
            messages: Optional list of messages
            channel: Channel type (CHAT, SMS, WHATSAPP)
            deal_id: Optional associated deal
            
        Returns:
            Created note data
        """
        note_parts = [f"**AI Conversation ({channel})**", "", summary]
        
        if messages:
            note_parts.append("")
            note_parts.append("**Conversation Transcript:**")
            for msg in messages[-10:]:  # Last 10 messages
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")[:500]  # Truncate
                note_parts.append(f"[{role}] {content}")
        
        return await self.create_note(
            body="\n".join(note_parts),
            contact_id=contact_id,
            deal_id=deal_id,
        )

    async def _associate_engagement(
        self,
        engagement_id: str,
        object_type: str,
        object_id: str,
    ) -> bool:
        """Associate an engagement with an object."""
        try:
            await self._make_request(
                "PUT",
                f"/crm/v3/objects/notes/{engagement_id}/associations/{object_type}/{object_id}/note_to_{object_type[:-1]}",
            )
            return True
        except Exception:
            return False

    # =========================================================================
    # Lead Scoring
    # =========================================================================

    async def update_lead_score(
        self,
        contact_id: str,
        score: str,
        score_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Update lead score on a contact.
        
        Args:
            contact_id: Contact ID
            score: Score value (HOT, WARM, COLD)
            score_reason: Reason for score
            
        Returns:
            Updated contact data
        """
        properties = {
            "ai_lead_score": score.upper(),
            "ai_lead_score_updated": datetime.utcnow().isoformat(),
        }
        
        if score_reason:
            properties["ai_lead_score_reason"] = score_reason

        return await self.update_contact(contact_id, properties)

    async def update_lifecycle_stage(
        self,
        contact_id: str,
        stage: str,
    ) -> dict[str, Any]:
        """
        Update contact lifecycle stage.
        
        Common stages: subscriber, lead, marketingqualifiedlead, 
        salesqualifiedlead, opportunity, customer, evangelist
        """
        return await self.update_contact(
            contact_id,
            {"lifecyclestage": stage},
        )

    # =========================================================================
    # Sync Helpers
    # =========================================================================

    async def sync_lead_data(
        self,
        email: str | None = None,
        phone: str | None = None,
        name: str | None = None,
        lead_score: str | None = None,
        qualification_data: dict[str, Any] | None = None,
        conversation_summary: str | None = None,
        messages: list[dict[str, str]] | None = None,
        channel: str = "WEB",
    ) -> dict[str, Any]:
        """
        Comprehensive sync of lead data to HubSpot.
        
        Creates/updates contact, logs conversation, updates lead score.
        
        Args:
            email: Contact email
            phone: Contact phone
            name: Contact name
            lead_score: AI lead score (HOT, WARM, COLD)
            qualification_data: Extracted qualification info
            conversation_summary: Conversation summary
            messages: Conversation messages
            channel: Source channel
            
        Returns:
            Sync results
        """
        if not self._is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        results = {}

        # Parse name into first/last
        first_name, last_name = None, None
        if name:
            parts = name.strip().split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else None

        # Build properties
        properties = {
            "ai_conversation_channel": channel,
            "ai_last_conversation": datetime.utcnow().isoformat(),
        }
        
        if qualification_data:
            if qualification_data.get("service_interest"):
                properties["ai_service_interest"] = qualification_data["service_interest"]
            if qualification_data.get("urgency"):
                properties["ai_urgency"] = qualification_data["urgency"]
            if qualification_data.get("budget_range"):
                properties["ai_budget_range"] = qualification_data["budget_range"]
            if qualification_data.get("timeline"):
                properties["ai_timeline"] = qualification_data["timeline"]

        # Create/update contact
        contact = await self.create_or_update_contact(
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            properties=properties,
        )
        results["contact"] = contact
        
        contact_id = contact.get("id")
        if not contact_id:
            return results

        # Update lead score
        if lead_score:
            await self.update_lead_score(contact_id, lead_score)
            results["lead_score_updated"] = True

        # Log conversation
        if conversation_summary or messages:
            note = await self.log_conversation(
                contact_id=contact_id,
                summary=conversation_summary or "AI qualification conversation",
                messages=messages,
                channel=channel,
            )
            results["note"] = note

        logger.info(
            "Lead synced to HubSpot",
            contact_id=contact_id,
            email=email,
            score=lead_score,
        )

        return results

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _is_configured(self) -> bool:
        """Check if HubSpot is configured."""
        return bool(self.access_token)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to HubSpot API."""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
            )
            
            if response.status_code >= 400:
                logger.error(
                    "HubSpot API error",
                    status=response.status_code,
                    response=response.text[:500],
                    endpoint=endpoint,
                )
                response.raise_for_status()
            
            return response.json() if response.content else {}


# Per-client HubSpot service factory
_hubspot_services: dict[str, HubSpotService] = {}


def get_hubspot_service(access_token: str | None = None) -> HubSpotService:
    """
    Get HubSpot service instance.
    
    Args:
        access_token: Client-specific access token
        
    Returns:
        HubSpotService instance
    """
    key = access_token or "default"
    
    if key not in _hubspot_services:
        _hubspot_services[key] = HubSpotService(access_token=access_token)
    
    return _hubspot_services[key]
