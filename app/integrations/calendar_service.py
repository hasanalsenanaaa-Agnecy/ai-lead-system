"""
Cal.com Integration
Calendar and appointment booking via Cal.com API
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class CalendarService:
    """
    Cal.com integration for appointment booking.
    
    Features:
    - Get available time slots
    - Book appointments
    - Cancel/reschedule appointments
    - Manage event types per client
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.calcom_api_key
        self.base_url = settings.calcom_base_url or "https://api.cal.com/v1"
        self.default_event_type_id = settings.calcom_default_event_type_id

    # =========================================================================
    # Availability
    # =========================================================================

    async def get_available_slots(
        self,
        event_type_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        timezone: str = "UTC",
    ) -> list[dict[str, Any]]:
        """
        Get available time slots for booking.
        
        Args:
            event_type_id: Cal.com event type ID
            start_date: Start of availability window
            end_date: End of availability window
            timezone: Timezone for slots
            
        Returns:
            List of available time slots
        """
        if not self._is_configured():
            logger.warning("Cal.com not configured")
            return []

        event_type_id = event_type_id or self.default_event_type_id
        if not event_type_id:
            logger.error("No event type ID configured")
            return []

        # Default to next 7 days
        start_date = start_date or datetime.utcnow()
        end_date = end_date or (start_date + timedelta(days=7))

        try:
            response = await self._make_request(
                "GET",
                f"/availability",
                params={
                    "eventTypeId": event_type_id,
                    "startTime": start_date.isoformat(),
                    "endTime": end_date.isoformat(),
                    "timeZone": timezone,
                },
            )
            
            slots = response.get("slots", {})
            
            # Flatten slots into list
            available_slots = []
            for date, times in slots.items():
                for slot in times:
                    available_slots.append({
                        "date": date,
                        "time": slot.get("time"),
                        "datetime": slot.get("time"),
                    })
            
            logger.debug(
                "Availability fetched",
                event_type_id=event_type_id,
                slot_count=len(available_slots),
            )
            
            return available_slots
            
        except Exception as e:
            logger.error("Failed to get availability", error=str(e))
            return []

    async def get_next_available_slot(
        self,
        event_type_id: int | None = None,
        after: datetime | None = None,
        timezone: str = "UTC",
    ) -> dict[str, Any] | None:
        """
        Get the next available time slot.
        
        Args:
            event_type_id: Event type ID
            after: Find slots after this time
            timezone: Timezone
            
        Returns:
            Next available slot or None
        """
        after = after or datetime.utcnow()
        
        slots = await self.get_available_slots(
            event_type_id=event_type_id,
            start_date=after,
            end_date=after + timedelta(days=14),  # Look 2 weeks ahead
            timezone=timezone,
        )
        
        # Return first slot that's in the future
        for slot in slots:
            slot_time = datetime.fromisoformat(slot["datetime"].replace("Z", "+00:00"))
            if slot_time > after:
                return slot
        
        return None

    # =========================================================================
    # Bookings
    # =========================================================================

    async def create_booking(
        self,
        event_type_id: int | None = None,
        start_time: str | datetime = None,
        name: str = "",
        email: str = "",
        phone: str | None = None,
        notes: str | None = None,
        timezone: str = "UTC",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new booking.
        
        Args:
            event_type_id: Cal.com event type ID
            start_time: Appointment start time (ISO format)
            name: Attendee name
            email: Attendee email
            phone: Attendee phone (optional)
            notes: Booking notes
            timezone: Attendee timezone
            metadata: Additional metadata (lead_id, etc.)
            
        Returns:
            Booking details
        """
        if not self._is_configured():
            logger.warning("Cal.com not configured, skipping booking")
            return {"status": "skipped", "reason": "not_configured"}

        event_type_id = event_type_id or self.default_event_type_id
        if not event_type_id:
            raise ValueError("No event type ID provided")

        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()

        payload = {
            "eventTypeId": event_type_id,
            "start": start_time,
            "responses": {
                "name": name,
                "email": email,
                "location": {
                    "value": "phone",
                    "optionValue": phone,
                } if phone else None,
            },
            "timeZone": timezone,
            "language": "en",
        }
        
        if notes:
            payload["responses"]["notes"] = notes
            
        if metadata:
            payload["metadata"] = metadata

        try:
            response = await self._make_request(
                "POST",
                "/bookings",
                json=payload,
            )
            
            booking = response.get("booking", response)
            
            logger.info(
                "Booking created",
                booking_id=booking.get("id"),
                uid=booking.get("uid"),
                start_time=start_time,
                attendee=email,
            )
            
            return booking
            
        except Exception as e:
            logger.error(
                "Failed to create booking",
                error=str(e),
                event_type_id=event_type_id,
                attendee=email,
            )
            raise

    async def get_booking(self, booking_uid: str) -> dict[str, Any] | None:
        """Get booking details by UID."""
        if not self._is_configured():
            return None

        try:
            response = await self._make_request(
                "GET",
                f"/bookings/{booking_uid}",
            )
            return response.get("booking", response)
            
        except Exception as e:
            logger.error("Failed to get booking", error=str(e), uid=booking_uid)
            return None

    async def cancel_booking(
        self,
        booking_uid: str,
        reason: str | None = None,
    ) -> bool:
        """
        Cancel a booking.
        
        Args:
            booking_uid: Booking UID
            reason: Cancellation reason
            
        Returns:
            True if cancelled successfully
        """
        if not self._is_configured():
            return False

        try:
            await self._make_request(
                "DELETE",
                f"/bookings/{booking_uid}",
                json={"reason": reason} if reason else None,
            )
            
            logger.info("Booking cancelled", uid=booking_uid)
            return True
            
        except Exception as e:
            logger.error("Failed to cancel booking", error=str(e), uid=booking_uid)
            return False

    async def reschedule_booking(
        self,
        booking_uid: str,
        new_start_time: str | datetime,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Reschedule a booking to a new time.
        
        Args:
            booking_uid: Original booking UID
            new_start_time: New appointment time
            reason: Reschedule reason
            
        Returns:
            New booking details
        """
        if not self._is_configured():
            return {"status": "skipped", "reason": "not_configured"}

        if isinstance(new_start_time, datetime):
            new_start_time = new_start_time.isoformat()

        payload = {
            "start": new_start_time,
        }
        if reason:
            payload["reason"] = reason

        try:
            response = await self._make_request(
                "PATCH",
                f"/bookings/{booking_uid}",
                json=payload,
            )
            
            logger.info(
                "Booking rescheduled",
                uid=booking_uid,
                new_time=new_start_time,
            )
            
            return response.get("booking", response)
            
        except Exception as e:
            logger.error("Failed to reschedule", error=str(e), uid=booking_uid)
            raise

    # =========================================================================
    # Event Types
    # =========================================================================

    async def list_event_types(self) -> list[dict[str, Any]]:
        """List all event types for the account."""
        if not self._is_configured():
            return []

        try:
            response = await self._make_request("GET", "/event-types")
            return response.get("event_types", [])
            
        except Exception as e:
            logger.error("Failed to list event types", error=str(e))
            return []

    async def get_event_type(self, event_type_id: int) -> dict[str, Any] | None:
        """Get event type details."""
        if not self._is_configured():
            return None

        try:
            response = await self._make_request(
                "GET",
                f"/event-types/{event_type_id}",
            )
            return response.get("event_type", response)
            
        except Exception as e:
            logger.error("Failed to get event type", error=str(e))
            return None

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def format_slots_for_lead(
        self,
        slots: list[dict[str, Any]],
        max_slots: int = 5,
        timezone: str = "UTC",
    ) -> str:
        """
        Format available slots into a human-readable message.
        
        Args:
            slots: List of available slots
            max_slots: Maximum slots to show
            timezone: Display timezone
            
        Returns:
            Formatted message string
        """
        if not slots:
            return "I don't have any available slots right now. Let me check with the team and get back to you."
        
        lines = ["Here are some available times:"]
        
        for i, slot in enumerate(slots[:max_slots]):
            slot_time = datetime.fromisoformat(slot["datetime"].replace("Z", "+00:00"))
            formatted = slot_time.strftime("%A, %B %d at %I:%M %p")
            lines.append(f"• {formatted}")
        
        if len(slots) > max_slots:
            lines.append(f"\n...and {len(slots) - max_slots} more options available.")
        
        lines.append("\nWhich time works best for you?")
        
        return "\n".join(lines)

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _is_configured(self) -> bool:
        """Check if Cal.com is configured."""
        return bool(self.api_key)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to Cal.com API."""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
                error_data = response.json() if response.content else {}
                logger.error(
                    "Cal.com API error",
                    status=response.status_code,
                    error=error_data,
                    endpoint=endpoint,
                )
                response.raise_for_status()
            
            return response.json() if response.content else {}


# Per-client calendar service factory
_calendar_services: dict[str, CalendarService] = {}


def get_calendar_service(api_key: str | None = None) -> CalendarService:
    """
    Get calendar service instance.
    
    Args:
        api_key: Client-specific API key (uses default if not provided)
        
    Returns:
        CalendarService instance
    """
    key = api_key or "default"
    
    if key not in _calendar_services:
        _calendar_services[key] = CalendarService(api_key=api_key)
    
    return _calendar_services[key]
