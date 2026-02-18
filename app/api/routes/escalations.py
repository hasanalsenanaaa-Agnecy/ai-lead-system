# Escalations API Routes

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import Escalation, Conversation, Lead

router = APIRouter(prefix="/api/v1/escalations", tags=["escalations"])


# =============================================================================
# Response Models
# =============================================================================

class EscalationResponse(BaseModel):
    id: str
    client_id: str
    conversation_id: str
    lead_id: str
    reason: str
    reason_details: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    created_at: datetime
    
    # Related data
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    lead_email: Optional[str] = None
    lead_score: Optional[str] = None
    conversation_channel: Optional[str] = None
    message_count: Optional[int] = None

    class Config:
        from_attributes = True


class ResolveRequest(BaseModel):
    resolved_by: str
    notes: Optional[str] = None


class EscalationStats(BaseModel):
    total: int
    pending: int
    resolved_today: int
    avg_resolution_time_minutes: float
    by_reason: dict


# =============================================================================
# List Escalations
# =============================================================================

@router.get("/client/{client_id}", response_model=List[EscalationResponse])
async def list_escalations(
    client_id: str,
    resolved: Optional[bool] = Query(default=None, description="Filter by resolution status"),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List escalations for a client.
    
    - **resolved=false**: Show only pending escalations
    - **resolved=true**: Show only resolved escalations
    - **resolved=None**: Show all escalations
    """
    
    query = (
        select(Escalation)
        .options(
            selectinload(Escalation.conversation),
            selectinload(Escalation.lead),
        )
        .where(Escalation.client_id == client_id)
    )
    
    if resolved is not None:
        if resolved:
            query = query.where(Escalation.resolved_at.isnot(None))
        else:
            query = query.where(Escalation.resolved_at.is_(None))
    
    query = query.order_by(Escalation.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    escalations = result.scalars().all()
    
    # Transform to response model with related data
    response = []
    for esc in escalations:
        resp = EscalationResponse(
            id=str(esc.id),
            client_id=str(esc.client_id),
            conversation_id=str(esc.conversation_id),
            lead_id=str(esc.lead_id),
            reason=esc.reason,
            reason_details=esc.reason_details,
            resolved_at=esc.resolved_at,
            resolved_by=esc.resolved_by,
            created_at=esc.created_at,
        )
        
        # Add lead info if available
        if esc.lead:
            resp.lead_name = esc.lead.name
            resp.lead_phone = esc.lead.phone
            resp.lead_email = esc.lead.email
            resp.lead_score = esc.lead.score
        
        # Add conversation info if available
        if esc.conversation:
            resp.conversation_channel = esc.conversation.channel
            resp.message_count = esc.conversation.message_count
        
        response.append(resp)
    
    return response


# =============================================================================
# Get Single Escalation
# =============================================================================

@router.get("/{escalation_id}", response_model=EscalationResponse)
async def get_escalation(
    escalation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific escalation."""
    
    result = await db.execute(
        select(Escalation)
        .options(
            selectinload(Escalation.conversation),
            selectinload(Escalation.lead),
        )
        .where(Escalation.id == escalation_id)
    )
    
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    resp = EscalationResponse(
        id=str(escalation.id),
        client_id=str(escalation.client_id),
        conversation_id=str(escalation.conversation_id),
        lead_id=str(escalation.lead_id),
        reason=escalation.reason,
        reason_details=escalation.reason_details,
        resolved_at=escalation.resolved_at,
        resolved_by=escalation.resolved_by,
        created_at=escalation.created_at,
    )
    
    if escalation.lead:
        resp.lead_name = escalation.lead.name
        resp.lead_phone = escalation.lead.phone
        resp.lead_email = escalation.lead.email
        resp.lead_score = escalation.lead.score
    
    if escalation.conversation:
        resp.conversation_channel = escalation.conversation.channel
        resp.message_count = escalation.conversation.message_count
    
    return resp


# =============================================================================
# Resolve Escalation
# =============================================================================

@router.post("/{escalation_id}/resolve", response_model=EscalationResponse)
async def resolve_escalation(
    escalation_id: str,
    request: ResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an escalation as resolved.
    
    This should be called after a human agent has handled the escalated conversation.
    """
    
    result = await db.execute(
        select(Escalation)
        .options(
            selectinload(Escalation.conversation),
            selectinload(Escalation.lead),
        )
        .where(Escalation.id == escalation_id)
    )
    
    escalation = result.scalar_one_or_none()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    if escalation.resolved_at:
        raise HTTPException(status_code=400, detail="Escalation already resolved")
    
    # Update escalation
    escalation.resolved_at = datetime.utcnow()
    escalation.resolved_by = request.resolved_by
    
    if request.notes:
        escalation.reason_details = f"{escalation.reason_details or ''}\n\nResolution notes: {request.notes}".strip()
    
    await db.commit()
    await db.refresh(escalation)
    
    resp = EscalationResponse(
        id=str(escalation.id),
        client_id=str(escalation.client_id),
        conversation_id=str(escalation.conversation_id),
        lead_id=str(escalation.lead_id),
        reason=escalation.reason,
        reason_details=escalation.reason_details,
        resolved_at=escalation.resolved_at,
        resolved_by=escalation.resolved_by,
        created_at=escalation.created_at,
    )
    
    if escalation.lead:
        resp.lead_name = escalation.lead.name
        resp.lead_phone = escalation.lead.phone
        resp.lead_email = escalation.lead.email
        resp.lead_score = escalation.lead.score
    
    if escalation.conversation:
        resp.conversation_channel = escalation.conversation.channel
        resp.message_count = escalation.conversation.message_count
    
    return resp


# =============================================================================
# Escalation Stats
# =============================================================================

@router.get("/client/{client_id}/stats", response_model=EscalationStats)
async def get_escalation_stats(
    client_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get escalation statistics for a client."""
    from sqlalchemy import func
    from datetime import timedelta
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Total escalations
    total_result = await db.execute(
        select(func.count(Escalation.id)).where(Escalation.client_id == client_id)
    )
    total = total_result.scalar() or 0
    
    # Pending escalations
    pending_result = await db.execute(
        select(func.count(Escalation.id)).where(
            and_(
                Escalation.client_id == client_id,
                Escalation.resolved_at.is_(None)
            )
        )
    )
    pending = pending_result.scalar() or 0
    
    # Resolved today
    resolved_today_result = await db.execute(
        select(func.count(Escalation.id)).where(
            and_(
                Escalation.client_id == client_id,
                Escalation.resolved_at >= today_start
            )
        )
    )
    resolved_today = resolved_today_result.scalar() or 0
    
    # Average resolution time
    avg_resolution_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', Escalation.resolved_at - Escalation.created_at) / 60
            )
        ).where(
            and_(
                Escalation.client_id == client_id,
                Escalation.resolved_at.isnot(None)
            )
        )
    )
    avg_resolution_time = avg_resolution_result.scalar() or 0
    
    # By reason
    by_reason_result = await db.execute(
        select(Escalation.reason, func.count(Escalation.id))
        .where(Escalation.client_id == client_id)
        .group_by(Escalation.reason)
    )
    by_reason = {row[0]: row[1] for row in by_reason_result.fetchall()}
    
    return EscalationStats(
        total=total,
        pending=pending,
        resolved_today=resolved_today,
        avg_resolution_time_minutes=round(float(avg_resolution_time), 1),
        by_reason=by_reason,
    )


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/client/{client_id}/resolve-all")
async def resolve_all_escalations(
    client_id: str,
    request: ResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resolve all pending escalations for a client."""
    
    result = await db.execute(
        select(Escalation).where(
            and_(
                Escalation.client_id == client_id,
                Escalation.resolved_at.is_(None)
            )
        )
    )
    
    escalations = result.scalars().all()
    resolved_count = 0
    
    for escalation in escalations:
        escalation.resolved_at = datetime.utcnow()
        escalation.resolved_by = request.resolved_by
        resolved_count += 1
    
    await db.commit()
    
    return {
        "resolved_count": resolved_count,
        "message": f"Resolved {resolved_count} escalations"
    }
