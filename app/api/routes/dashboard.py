# Dashboard API Routes

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db_session as get_db
from app.db.models import Lead, Conversation, Message, Escalation, Client, LeadScore, LeadStatus, MessageRole

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# =============================================================================
# Response Models
# =============================================================================

class DashboardStats(BaseModel):
    total_leads: int
    leads_today: int
    leads_this_week: int
    leads_this_month: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    appointments_booked: int
    active_conversations: int
    escalations_pending: int
    avg_response_time_ms: float
    qualification_rate: float
    tokens_used: int
    tokens_budget: int


class LeadsByDay(BaseModel):
    date: str
    total: int
    hot: int
    warm: int
    cold: int


class LeadsByChannel(BaseModel):
    channel: str
    count: int
    percentage: float


class LeadsByStatus(BaseModel):
    status: str
    count: int


class ConversationMetrics(BaseModel):
    total_conversations: int
    avg_messages_per_conversation: float
    avg_conversation_duration_minutes: float
    escalation_rate: float
    ai_resolution_rate: float


class HourlyActivity(BaseModel):
    hour: int
    leads: int
    messages: int


# =============================================================================
# Dashboard Stats
# =============================================================================

@router.get("/{client_id}/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    client_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive dashboard statistics for a client."""
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # Total leads
    total_leads_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.client_id == client_id)
    )
    total_leads = total_leads_result.scalar() or 0

    # Leads today
    leads_today_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(Lead.client_id == client_id, Lead.created_at >= today_start)
        )
    )
    leads_today = leads_today_result.scalar() or 0

    # Leads this week
    leads_week_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(Lead.client_id == client_id, Lead.created_at >= week_start)
        )
    )
    leads_this_week = leads_week_result.scalar() or 0

    # Leads this month
    leads_month_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(Lead.client_id == client_id, Lead.created_at >= month_start)
        )
    )
    leads_this_month = leads_month_result.scalar() or 0

    # Leads by score
    score_counts_result = await db.execute(
        select(Lead.score, func.count(Lead.id))
        .where(Lead.client_id == client_id)
        .group_by(Lead.score)
    )
    score_counts = {row[0]: row[1] for row in score_counts_result.fetchall()}
    
    hot_leads = score_counts.get(LeadScore.HOT.value, 0)
    warm_leads = score_counts.get(LeadScore.WARM.value, 0)
    cold_leads = score_counts.get(LeadScore.COLD.value, 0)

    # Appointments booked
    appointments_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.client_id == client_id,
                Lead.status == LeadStatus.APPOINTMENT_BOOKED.value
            )
        )
    )
    appointments_booked = appointments_result.scalar() or 0

    # Active conversations
    active_convos_result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.client_id == client_id,
                Conversation.is_active == True
            )
        )
    )
    active_conversations = active_convos_result.scalar() or 0

    # Pending escalations
    escalations_result = await db.execute(
        select(func.count(Escalation.id)).where(
            and_(
                Escalation.client_id == client_id,
                Escalation.resolved_at.is_(None)
            )
        )
    )
    escalations_pending = escalations_result.scalar() or 0

    # Average response time (from messages)
    avg_response_result = await db.execute(
        select(func.avg(Message.processing_time_ms))
        .join(Conversation)
        .where(
            and_(
                Conversation.client_id == client_id,
                Message.role == MessageRole.AGENT.value,
                Message.processing_time_ms.isnot(None)
            )
        )
    )
    avg_response_time_ms = avg_response_result.scalar() or 0

    # Qualification rate (leads that became qualified, appointment_booked, or handed_off)
    qualified_statuses = [
        LeadStatus.QUALIFIED.value,
        LeadStatus.APPOINTMENT_BOOKED.value,
        LeadStatus.HANDED_OFF.value,
        LeadStatus.CLOSED_WON.value,
    ]
    qualified_result = await db.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.client_id == client_id,
                Lead.status.in_(qualified_statuses)
            )
        )
    )
    qualified_count = qualified_result.scalar() or 0
    qualification_rate = (qualified_count / total_leads * 100) if total_leads > 0 else 0

    # Token usage
    client_result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = client_result.scalar_one_or_none()
    tokens_used = client.tokens_used_this_month if client else 0
    tokens_budget = client.monthly_token_budget if client else 0

    return DashboardStats(
        total_leads=total_leads,
        leads_today=leads_today,
        leads_this_week=leads_this_week,
        leads_this_month=leads_this_month,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        appointments_booked=appointments_booked,
        active_conversations=active_conversations,
        escalations_pending=escalations_pending,
        avg_response_time_ms=float(avg_response_time_ms),
        qualification_rate=round(qualification_rate, 1),
        tokens_used=tokens_used,
        tokens_budget=tokens_budget,
    )


# =============================================================================
# Leads Analytics
# =============================================================================

@router.get("/{client_id}/leads-by-day", response_model=List[LeadsByDay])
async def get_leads_by_day(
    client_id: str,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get lead counts by day for the specified period."""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Query with date truncation and score grouping
    result = await db.execute(
        select(
            func.date(Lead.created_at).label('date'),
            Lead.score,
            func.count(Lead.id).label('count')
        )
        .where(
            and_(
                Lead.client_id == client_id,
                Lead.created_at >= start_date
            )
        )
        .group_by(func.date(Lead.created_at), Lead.score)
        .order_by(func.date(Lead.created_at))
    )
    
    # Process results into daily aggregates
    daily_data = {}
    for row in result.fetchall():
        date_str = row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date)
        if date_str not in daily_data:
            daily_data[date_str] = {'total': 0, 'hot': 0, 'warm': 0, 'cold': 0}
        daily_data[date_str]['total'] += row.count
        if row.score in [LeadScore.HOT.value, LeadScore.WARM.value, LeadScore.COLD.value]:
            daily_data[date_str][row.score] += row.count

    # Fill in missing days
    result_list = []
    current_date = start_date.date()
    end_date = datetime.utcnow().date()
    
    while current_date <= end_date:
        date_str = current_date.isoformat()
        data = daily_data.get(date_str, {'total': 0, 'hot': 0, 'warm': 0, 'cold': 0})
        result_list.append(LeadsByDay(
            date=date_str,
            total=data['total'],
            hot=data['hot'],
            warm=data['warm'],
            cold=data['cold'],
        ))
        current_date += timedelta(days=1)

    return result_list


@router.get("/{client_id}/leads-by-channel", response_model=List[LeadsByChannel])
async def get_leads_by_channel(
    client_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get lead distribution by source channel."""
    
    result = await db.execute(
        select(Lead.source_channel, func.count(Lead.id).label('count'))
        .where(
            and_(
                Lead.client_id == client_id,
                Lead.source_channel.isnot(None)
            )
        )
        .group_by(Lead.source_channel)
        .order_by(func.count(Lead.id).desc())
    )
    
    rows = result.fetchall()
    total = sum(row.count for row in rows)
    
    return [
        LeadsByChannel(
            channel=row.source_channel or 'unknown',
            count=row.count,
            percentage=round(row.count / total * 100, 1) if total > 0 else 0
        )
        for row in rows
    ]


@router.get("/{client_id}/leads-by-status", response_model=List[LeadsByStatus])
async def get_leads_by_status(
    client_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get lead distribution by status."""
    
    result = await db.execute(
        select(Lead.status, func.count(Lead.id).label('count'))
        .where(Lead.client_id == client_id)
        .group_by(Lead.status)
        .order_by(func.count(Lead.id).desc())
    )
    
    return [
        LeadsByStatus(status=row.status, count=row.count)
        for row in result.fetchall()
    ]


# =============================================================================
# Conversation Analytics
# =============================================================================

@router.get("/{client_id}/conversation-metrics", response_model=ConversationMetrics)
async def get_conversation_metrics(
    client_id: str,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation performance metrics."""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total conversations
    total_result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.client_id == client_id,
                Conversation.created_at >= start_date
            )
        )
    )
    total_conversations = total_result.scalar() or 0

    # Average messages per conversation
    avg_messages_result = await db.execute(
        select(func.avg(Conversation.message_count)).where(
            and_(
                Conversation.client_id == client_id,
                Conversation.created_at >= start_date
            )
        )
    )
    avg_messages = avg_messages_result.scalar() or 0

    # Average conversation duration (for ended conversations)
    # Using raw SQL for date diff calculation
    duration_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', Conversation.ended_at - Conversation.created_at) / 60
            )
        ).where(
            and_(
                Conversation.client_id == client_id,
                Conversation.created_at >= start_date,
                Conversation.ended_at.isnot(None)
            )
        )
    )
    avg_duration = duration_result.scalar() or 0

    # Escalation rate
    escalated_result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.client_id == client_id,
                Conversation.created_at >= start_date,
                Conversation.is_escalated == True
            )
        )
    )
    escalated_count = escalated_result.scalar() or 0
    escalation_rate = (escalated_count / total_conversations * 100) if total_conversations > 0 else 0

    # AI resolution rate (conversations that ended without escalation)
    resolved_result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.client_id == client_id,
                Conversation.created_at >= start_date,
                Conversation.ended_at.isnot(None),
                Conversation.is_escalated == False
            )
        )
    )
    resolved_count = resolved_result.scalar() or 0
    ended_result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.client_id == client_id,
                Conversation.created_at >= start_date,
                Conversation.ended_at.isnot(None)
            )
        )
    )
    ended_count = ended_result.scalar() or 0
    ai_resolution_rate = (resolved_count / ended_count * 100) if ended_count > 0 else 0

    return ConversationMetrics(
        total_conversations=total_conversations,
        avg_messages_per_conversation=round(float(avg_messages), 1),
        avg_conversation_duration_minutes=round(float(avg_duration), 1),
        escalation_rate=round(escalation_rate, 1),
        ai_resolution_rate=round(ai_resolution_rate, 1),
    )


@router.get("/{client_id}/hourly-activity", response_model=List[HourlyActivity])
async def get_hourly_activity(
    client_id: str,
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Get activity distribution by hour of day."""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Leads by hour
    leads_result = await db.execute(
        select(
            func.extract('hour', Lead.created_at).label('hour'),
            func.count(Lead.id).label('count')
        )
        .where(
            and_(
                Lead.client_id == client_id,
                Lead.created_at >= start_date
            )
        )
        .group_by(func.extract('hour', Lead.created_at))
    )
    leads_by_hour = {int(row.hour): row.count for row in leads_result.fetchall()}

    # Messages by hour
    messages_result = await db.execute(
        select(
            func.extract('hour', Message.created_at).label('hour'),
            func.count(Message.id).label('count')
        )
        .join(Conversation)
        .where(
            and_(
                Conversation.client_id == client_id,
                Message.created_at >= start_date
            )
        )
        .group_by(func.extract('hour', Message.created_at))
    )
    messages_by_hour = {int(row.hour): row.count for row in messages_result.fetchall()}

    return [
        HourlyActivity(
            hour=hour,
            leads=leads_by_hour.get(hour, 0),
            messages=messages_by_hour.get(hour, 0),
        )
        for hour in range(24)
    ]


# =============================================================================
# Recent Activity
# =============================================================================

@router.get("/{client_id}/recent-leads")
async def get_recent_leads(
    client_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get most recent leads."""
    
    result = await db.execute(
        select(Lead)
        .where(Lead.client_id == client_id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    
    return result.scalars().all()


@router.get("/{client_id}/recent-conversations")
async def get_recent_conversations(
    client_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Get most recent conversations."""
    
    query = select(Conversation).where(Conversation.client_id == client_id)
    
    if active_only:
        query = query.where(Conversation.is_active == True)
    
    query = query.order_by(Conversation.updated_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{client_id}/pending-escalations")
async def get_pending_escalations(
    client_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get pending escalations that need attention."""
    
    result = await db.execute(
        select(Escalation)
        .where(
            and_(
                Escalation.client_id == client_id,
                Escalation.resolved_at.is_(None)
            )
        )
        .order_by(Escalation.created_at.desc())
    )
    
    return result.scalars().all()
