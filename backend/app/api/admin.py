"""
Admin API routes for managing leads, conversations, and clients.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.models.models import (
    Lead, Conversation, Message, Client, KnowledgeBaseEntry, Appointment,
    LeadStatus, LeadScore, ChannelType, ClientStatus, ClientVertical
)
from app.services.lead_service import lead_service, appointment_service
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/v1", tags=["admin"])


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class ClientCreate(BaseModel):
    name: str
    slug: str
    email: str
    vertical: ClientVertical = ClientVertical.OTHER
    phone: Optional[str] = None
    website: Optional[str] = None
    timezone: str = "UTC"
    ai_persona_name: str = "AI Assistant"
    services_offered: Optional[List[str]] = None
    qualification_questions: Optional[List[str]] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    status: Optional[ClientStatus] = None
    timezone: Optional[str] = None
    ai_persona_name: Optional[str] = None
    ai_persona_prompt: Optional[str] = None
    services_offered: Optional[List[str]] = None
    qualification_questions: Optional[List[str]] = None
    business_hours: Optional[dict] = None
    twilio_phone_number: Optional[str] = None
    twilio_whatsapp_number: Optional[str] = None
    hot_lead_notification_phones: Optional[List[str]] = None
    hot_lead_notification_emails: Optional[List[str]] = None
    crm_type: Optional[str] = None
    crm_config: Optional[dict] = None


class ClientResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    email: str
    vertical: ClientVertical
    status: ClientStatus
    phone: Optional[str]
    website: Optional[str]
    timezone: str
    ai_persona_name: str
    services_offered: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class LeadResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    phone: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    status: LeadStatus
    score: LeadScore
    score_value: float
    source: Optional[str]
    initial_channel: ChannelType
    service_interested: Optional[str]
    timeline: Optional[str]
    budget_range: Optional[str]
    qualified_at: Optional[datetime]
    appointment_scheduled_at: Optional[datetime]
    handed_off_at: Optional[datetime]
    first_contact_at: datetime
    last_contact_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    score: Optional[LeadScore] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    service_interested: Optional[str] = None
    timeline: Optional[str] = None
    budget_range: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    channel: ChannelType
    is_active: bool
    is_human_takeover: bool
    message_count: int
    avg_confidence_score: float
    started_at: datetime
    last_message_at: datetime
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    confidence_score: Optional[float]
    intent_detected: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class KnowledgeBaseCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    source: Optional[str] = None
    metadata: Optional[dict] = None


class KnowledgeBaseResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    content: str
    category: Optional[str]
    source: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):
    lead_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int = 30
    service_type: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    lead_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    service_type: Optional[str]
    notes: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_leads: int
    new_leads_today: int
    hot_leads: int
    warm_leads: int
    appointments_today: int
    appointments_this_week: int
    avg_response_time_seconds: Optional[float]
    conversion_rate: Optional[float]


# =============================================================================
# CLIENT ROUTES
# =============================================================================

@router.post("/clients", response_model=ClientResponse)
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new client."""
    # Check slug uniqueness
    existing = await db.execute(
        select(Client).where(Client.slug == client_data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    client = Client(**client_data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    
    return client


@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(
    status: Optional[ClientStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all clients."""
    query = select(Client)
    
    if status:
        query = query.where(Client.status == status)
    
    query = query.order_by(Client.created_at.desc())
    result = await db.execute(query)
    
    return list(result.scalars().all())


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get client by ID."""
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return client


@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID,
    client_data: ClientUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update client."""
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    await db.commit()
    await db.refresh(client)
    
    return client


# =============================================================================
# LEAD ROUTES
# =============================================================================

@router.get("/clients/{client_id}/leads", response_model=List[LeadResponse])
async def list_leads(
    client_id: uuid.UUID,
    status: Optional[LeadStatus] = None,
    score: Optional[LeadScore] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List leads for a client."""
    leads = await lead_service.get_leads(
        db=db,
        client_id=client_id,
        status=status,
        score=score,
        limit=limit,
        offset=offset
    )
    return leads


@router.get("/clients/{client_id}/leads/hot", response_model=List[LeadResponse])
async def get_hot_leads(
    client_id: uuid.UUID,
    since_hours: int = Query(default=24, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Get hot leads from the last N hours."""
    since = datetime.utcnow() - timedelta(hours=since_hours)
    leads = await lead_service.get_hot_leads(db, client_id, since)
    return leads


@router.get("/clients/{client_id}/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    client_id: uuid.UUID,
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get lead by ID."""
    lead = await lead_service.get_lead_by_id(db, lead_id, client_id)
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return lead


@router.patch("/clients/{client_id}/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    client_id: uuid.UUID,
    lead_id: uuid.UUID,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update lead."""
    lead = await lead_service.get_lead_by_id(db, lead_id, client_id)
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    await db.commit()
    await db.refresh(lead)
    
    return lead


# =============================================================================
# CONVERSATION ROUTES
# =============================================================================

@router.get("/clients/{client_id}/leads/{lead_id}/conversations", response_model=List[ConversationResponse])
async def get_lead_conversations(
    client_id: uuid.UUID,
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get conversations for a lead."""
    result = await db.execute(
        select(Conversation)
        .where(
            and_(
                Conversation.lead_id == lead_id,
                Conversation.client_id == client_id
            )
        )
        .order_by(Conversation.started_at.desc())
    )
    return list(result.scalars().all())


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a conversation."""
    messages = await lead_service.get_conversation_messages(
        db, conversation_id, limit
    )
    return messages


# =============================================================================
# KNOWLEDGE BASE ROUTES
# =============================================================================

@router.post("/clients/{client_id}/knowledge", response_model=KnowledgeBaseResponse)
async def create_knowledge_entry(
    client_id: uuid.UUID,
    entry_data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new knowledge base entry."""
    entry = await rag_service.add_knowledge_entry(
        db=db,
        client_id=client_id,
        **entry_data.model_dump()
    )
    return entry


@router.get("/clients/{client_id}/knowledge", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_entries(
    client_id: uuid.UUID,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List knowledge base entries."""
    query = select(KnowledgeBaseEntry).where(
        KnowledgeBaseEntry.client_id == client_id
    )
    
    if category:
        query = query.where(KnowledgeBaseEntry.category == category)
    
    query = query.order_by(KnowledgeBaseEntry.created_at.desc())
    result = await db.execute(query)
    
    return list(result.scalars().all())


@router.delete("/clients/{client_id}/knowledge/{entry_id}")
async def delete_knowledge_entry(
    client_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a knowledge base entry."""
    deleted = await rag_service.delete_knowledge_entry(db, entry_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {"status": "deleted"}


# =============================================================================
# APPOINTMENT ROUTES
# =============================================================================

@router.post("/clients/{client_id}/appointments", response_model=AppointmentResponse)
async def create_appointment(
    client_id: uuid.UUID,
    appointment_data: AppointmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new appointment."""
    appointment = await appointment_service.schedule_appointment(
        db=db,
        client_id=client_id,
        **appointment_data.model_dump()
    )
    return appointment


@router.get("/clients/{client_id}/appointments", response_model=List[AppointmentResponse])
async def list_appointments(
    client_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """List appointments."""
    appointments = await appointment_service.get_appointments(
        db=db,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date
    )
    return appointments


# =============================================================================
# DASHBOARD & ANALYTICS
# =============================================================================

@router.get("/clients/{client_id}/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics for a client."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=today.weekday())
    
    # Total leads
    total_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.client_id == client_id)
    )
    total_leads = total_result.scalar() or 0
    
    # New leads today
    new_today_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.client_id == client_id,
                Lead.created_at >= today
            )
        )
    )
    new_leads_today = new_today_result.scalar() or 0
    
    # Hot leads
    hot_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.client_id == client_id,
                Lead.score == LeadScore.HOT
            )
        )
    )
    hot_leads = hot_result.scalar() or 0
    
    # Warm leads
    warm_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.client_id == client_id,
                Lead.score == LeadScore.WARM
            )
        )
    )
    warm_leads = warm_result.scalar() or 0
    
    # Appointments today
    appts_today_result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.client_id == client_id,
                Appointment.scheduled_at >= today,
                Appointment.scheduled_at < today + timedelta(days=1)
            )
        )
    )
    appointments_today = appts_today_result.scalar() or 0
    
    # Appointments this week
    appts_week_result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.client_id == client_id,
                Appointment.scheduled_at >= week_start,
                Appointment.scheduled_at < week_start + timedelta(days=7)
            )
        )
    )
    appointments_this_week = appts_week_result.scalar() or 0
    
    return DashboardStats(
        total_leads=total_leads,
        new_leads_today=new_leads_today,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        appointments_today=appointments_today,
        appointments_this_week=appointments_this_week,
        avg_response_time_seconds=None,  # TODO: Calculate from messages
        conversion_rate=None  # TODO: Calculate from lead status
    )
