"""
Leads API Routes
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChannelType, LeadScore, LeadStatus
from app.db.session import get_db_session
from app.services.lead_service import LeadService

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


# =============================================================================
# Request/Response Models
# =============================================================================


class LeadCreate(BaseModel):
    """Request model for creating a lead."""

    client_id: UUID
    phone: str | None = None
    email: EmailStr | None = None
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    source_channel: ChannelType = ChannelType.WEB_FORM
    source_campaign: str | None = None
    source_medium: str | None = None
    landing_page: str | None = None
    service_interest: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    """Request model for updating a lead."""

    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    service_interest: str | None = None
    urgency: str | None = None
    budget_range: str | None = None
    location: str | None = None
    preferred_contact_time: str | None = None
    status: LeadStatus | None = None
    score: LeadScore | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class QualificationUpdate(BaseModel):
    """Request model for updating qualification data."""

    service_interest: str | None = None
    urgency: str | None = None
    budget_confirmed: bool | None = None
    budget_range: str | None = None
    location: str | None = None
    preferred_contact_time: str | None = None
    decision_maker: bool | None = None
    timeline: str | None = None


class AppointmentSchedule(BaseModel):
    """Request model for scheduling appointment."""

    appointment_time: datetime
    appointment_type: str | None = None


class LeadHandoff(BaseModel):
    """Request model for handing off lead."""

    assigned_to: str


class LeadResponse(BaseModel):
    """Response model for lead data."""

    id: UUID
    client_id: UUID
    phone: str | None
    email: str | None
    name: str | None
    first_name: str | None
    last_name: str | None
    source_channel: ChannelType
    source_campaign: str | None
    status: LeadStatus
    score: LeadScore
    score_value: int
    service_interest: str | None
    urgency: str | None
    budget_range: str | None
    location: str | None
    preferred_contact_time: str | None
    appointment_scheduled: datetime | None
    assigned_to: str | None
    handed_off_at: datetime | None
    qualification_data: dict[str, Any]
    tags: list[str] | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Response model for lead list."""

    leads: list[LeadResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Routes
# =============================================================================


@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new lead."""
    service = LeadService(db)

    lead = await service.create_or_update_lead(
        client_id=lead_data.client_id,
        source_channel=lead_data.source_channel,
        phone=lead_data.phone,
        email=lead_data.email,
        name=lead_data.name,
        first_name=lead_data.first_name,
        last_name=lead_data.last_name,
        source_campaign=lead_data.source_campaign,
        source_medium=lead_data.source_medium,
        landing_page=lead_data.landing_page,
        service_interest=lead_data.service_interest,
        metadata=lead_data.metadata,
    )

    return lead


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get lead by ID."""
    service = LeadService(db)
    lead = await service.get_by_id(lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    updates: LeadUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update lead fields."""
    service = LeadService(db)

    # Filter out None values
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    lead = await service.update_lead(lead_id, **update_data)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.patch("/{lead_id}/qualification", response_model=LeadResponse)
async def update_qualification(
    lead_id: UUID,
    qualification: QualificationUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update lead qualification data."""
    service = LeadService(db)

    qual_data = {k: v for k, v in qualification.model_dump().items() if v is not None}

    lead = await service.update_qualification(lead_id, qual_data)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.patch("/{lead_id}/score", response_model=LeadResponse)
async def update_score(
    lead_id: UUID,
    score: LeadScore,
    score_value: int | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Update lead score."""
    service = LeadService(db)

    lead = await service.update_score(lead_id, score, score_value)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.patch("/{lead_id}/status", response_model=LeadResponse)
async def update_status(
    lead_id: UUID,
    status: LeadStatus,
    db: AsyncSession = Depends(get_db_session),
):
    """Update lead status."""
    service = LeadService(db)

    lead = await service.update_status(lead_id, status)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.post("/{lead_id}/appointment", response_model=LeadResponse)
async def schedule_appointment(
    lead_id: UUID,
    appointment: AppointmentSchedule,
    db: AsyncSession = Depends(get_db_session),
):
    """Schedule appointment for lead."""
    service = LeadService(db)

    lead = await service.schedule_appointment(
        lead_id,
        appointment.appointment_time,
        appointment.appointment_type,
    )

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.post("/{lead_id}/handoff", response_model=LeadResponse)
async def handoff_lead(
    lead_id: UUID,
    handoff: LeadHandoff,
    db: AsyncSession = Depends(get_db_session),
):
    """Hand off lead to human team member."""
    service = LeadService(db)

    lead = await service.hand_off_lead(lead_id, handoff.assigned_to)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.get("/client/{client_id}", response_model=LeadListResponse)
async def get_leads_by_client(
    client_id: UUID,
    status: LeadStatus | None = None,
    score: LeadScore | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    """Get leads for a client with optional filters."""
    service = LeadService(db)

    if status:
        leads = await service.get_leads_by_status(client_id, status, limit=page_size)
    elif score == LeadScore.HOT:
        leads = await service.get_hot_leads(client_id, limit=page_size)
    else:
        # Basic pagination (would need proper implementation)
        leads = await service.get_leads_by_status(
            client_id, LeadStatus.NEW, limit=page_size
        )

    return LeadListResponse(
        leads=leads,
        total=len(leads),
        page=page,
        page_size=page_size,
    )


@router.get("/client/{client_id}/hot", response_model=LeadListResponse)
async def get_hot_leads(
    client_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    """Get hot leads requiring immediate attention."""
    service = LeadService(db)

    leads = await service.get_hot_leads(client_id, limit=limit)

    return LeadListResponse(
        leads=leads,
        total=len(leads),
        page=1,
        page_size=limit,
    )
