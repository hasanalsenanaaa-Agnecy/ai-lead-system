"""
Lead Service
Business logic for lead management
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChannelType, Lead, LeadScore, LeadStatus


class LeadService:
    """Service for managing leads."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, lead_id: UUID) -> Lead | None:
        """Get lead by ID."""
        result = await self.db.execute(select(Lead).where(Lead.id == lead_id))
        return result.scalar_one_or_none()

    async def get_by_phone(self, client_id: UUID, phone: str) -> Lead | None:
        """Get lead by phone number for a specific client."""
        result = await self.db.execute(
            select(Lead).where(
                and_(
                    Lead.client_id == client_id,
                    Lead.phone == phone,
                    Lead.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, client_id: UUID, email: str) -> Lead | None:
        """Get lead by email for a specific client."""
        result = await self.db.execute(
            select(Lead).where(
                and_(
                    Lead.client_id == client_id,
                    Lead.email == email.lower(),
                    Lead.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def find_existing_lead(
        self,
        client_id: UUID,
        phone: str | None = None,
        email: str | None = None,
    ) -> Lead | None:
        """Find existing lead by phone or email."""
        conditions = [Lead.client_id == client_id, Lead.deleted_at.is_(None)]

        contact_conditions = []
        if phone:
            contact_conditions.append(Lead.phone == phone)
        if email:
            contact_conditions.append(Lead.email == email.lower())

        if not contact_conditions:
            return None

        conditions.append(or_(*contact_conditions))

        result = await self.db.execute(
            select(Lead).where(and_(*conditions)).order_by(Lead.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def create_lead(
        self,
        client_id: UUID,
        source_channel: ChannelType,
        phone: str | None = None,
        email: str | None = None,
        name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        source_campaign: str | None = None,
        source_medium: str | None = None,
        landing_page: str | None = None,
        service_interest: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Lead:
        """Create a new lead."""
        lead = Lead(
            client_id=client_id,
            phone=phone,
            email=email.lower() if email else None,
            name=name,
            first_name=first_name,
            last_name=last_name,
            source_channel=source_channel.value if isinstance(source_channel, ChannelType) else source_channel,
            source_campaign=source_campaign,
            source_medium=source_medium,
            landing_page=landing_page,
            service_interest=service_interest,
            status=LeadStatus.NEW.value,
            score=LeadScore.UNSCORED.value,
            lead_metadata=metadata or {},
        )

        self.db.add(lead)
        await self.db.flush()
        await self.db.refresh(lead)

        return lead

    async def create_or_update_lead(
        self,
        client_id: UUID,
        source_channel: ChannelType,
        phone: str | None = None,
        email: str | None = None,
        name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        source_campaign: str | None = None,
        source_medium: str | None = None,
        landing_page: str | None = None,
        service_interest: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Lead:
        """Create a new lead or update existing one if found."""
        # Try to find existing lead
        existing = await self.find_existing_lead(client_id, phone, email)

        if existing:
            # Update existing lead with new info
            if name and not existing.name:
                existing.name = name
            if first_name and not existing.first_name:
                existing.first_name = first_name
            if last_name and not existing.last_name:
                existing.last_name = last_name
            if email and not existing.email:
                existing.email = email.lower()
            if phone and not existing.phone:
                existing.phone = phone
            if service_interest:
                existing.service_interest = service_interest
            if metadata:
                existing.lead_metadata = {**(existing.lead_metadata or {}), **metadata}

            existing.updated_at = datetime.utcnow()
            await self.db.flush()
            return existing

        # Create new lead
        return await self.create_lead(
            client_id=client_id,
            source_channel=source_channel,
            phone=phone,
            email=email,
            name=name,
            first_name=first_name,
            last_name=last_name,
            source_campaign=source_campaign,
            source_medium=source_medium,
            landing_page=landing_page,
            service_interest=service_interest,
            metadata=metadata,
        )

    async def update_lead(
        self,
        lead_id: UUID,
        **updates: Any,
    ) -> Lead | None:
        """Update lead fields."""
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None

        for key, value in updates.items():
            if hasattr(lead, key) and value is not None:
                setattr(lead, key, value)

        lead.updated_at = datetime.utcnow()
        await self.db.flush()
        return lead

    async def update_qualification(
        self,
        lead_id: UUID,
        qualification_data: dict[str, Any],
    ) -> Lead | None:
        """Update lead qualification data."""
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None

        # Merge with existing qualification data
        current_data = lead.qualification_data or {}
        for key, value in qualification_data.items():
            if value is not None:
                current_data[key] = value

        lead.qualification_data = current_data

        # Update individual fields if present
        if "service_interest" in qualification_data:
            lead.service_interest = qualification_data["service_interest"]
        if "urgency" in qualification_data:
            lead.urgency = qualification_data["urgency"]
        if "budget_range" in qualification_data:
            lead.budget_range = qualification_data["budget_range"]
        if "location" in qualification_data:
            lead.location = qualification_data["location"]
        if "preferred_contact_time" in qualification_data:
            lead.preferred_contact_time = qualification_data["preferred_contact_time"]

        lead.updated_at = datetime.utcnow()
        await self.db.flush()
        return lead

    async def update_score(
        self,
        lead_id: UUID,
        score: LeadScore,
        score_value: int | None = None,
    ) -> Lead | None:
        """Update lead score."""
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None

        lead.score = score.value if isinstance(score, LeadScore) else score
        if score_value is not None:
            lead.score_value = score_value

        lead.updated_at = datetime.utcnow()
        await self.db.flush()
        return lead

    async def update_status(
        self,
        lead_id: UUID,
        status: LeadStatus,
    ) -> Lead | None:
        """Update lead status."""
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None

        lead.status = status.value if isinstance(status, LeadStatus) else status
        lead.updated_at = datetime.utcnow()
        await self.db.flush()
        return lead

    async def schedule_appointment(
        self,
        lead_id: UUID,
        appointment_time: datetime,
        appointment_type: str | None = None,
    ) -> Lead | None:
        """Schedule appointment for lead."""
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None

        lead.appointment_at = appointment_time
        lead.appointment_notes = appointment_type
        lead.status = LeadStatus.APPOINTMENT_BOOKED.value
        lead.updated_at = datetime.utcnow()

        await self.db.flush()
        return lead

    async def hand_off_lead(
        self,
        lead_id: UUID,
        assigned_to: str,
    ) -> Lead | None:
        """Hand off lead to human team member."""
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None

        lead.handed_off_to = assigned_to
        lead.handed_off_at = datetime.utcnow()
        lead.status = LeadStatus.HANDED_OFF.value
        lead.updated_at = datetime.utcnow()

        await self.db.flush()
        return lead

    async def sync_to_crm(
        self,
        lead_id: UUID,
        crm_id: str,
        contact_id: str | None = None,
    ) -> Lead | None:
        """Update lead with CRM IDs after sync."""
        lead = await self.get_by_id(lead_id)
        if not lead:
            return None

        lead.crm_contact_id = crm_id
        if contact_id:
            lead.crm_contact_id = contact_id

        await self.db.flush()
        return lead

    async def get_leads_by_status(
        self,
        client_id: UUID,
        status: LeadStatus,
        limit: int = 100,
    ) -> list[Lead]:
        """Get leads by status for a client."""
        result = await self.db.execute(
            select(Lead)
            .where(
                and_(
                    Lead.client_id == client_id,
                    Lead.status == (status.value if isinstance(status, LeadStatus) else status),
                    Lead.deleted_at.is_(None),
                )
            )
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_hot_leads(self, client_id: UUID, limit: int = 50) -> list[Lead]:
        """Get hot leads requiring immediate attention."""
        result = await self.db.execute(
            select(Lead)
            .where(
                and_(
                    Lead.client_id == client_id,
                    Lead.score == LeadScore.HOT.value,
                    Lead.status.not_in([LeadStatus.CLOSED_WON.value, LeadStatus.CLOSED_LOST.value]),
                    Lead.deleted_at.is_(None),
                )
            )
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
