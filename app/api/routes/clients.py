"""
Clients API Routes
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClientStatus
from app.db.session import get_db_session
from app.services.client_service import ClientService

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ClientCreate(BaseModel):
    """Request model for creating a client."""

    name: str
    slug: str
    industry: str
    owner_name: str | None = None
    owner_email: EmailStr | None = None
    owner_phone: str | None = None
    website: str | None = None
    timezone: str = "America/New_York"
    primary_language: str = "en"
    plan: str = "growth"
    config: dict[str, Any] | None = None


class ClientUpdate(BaseModel):
    """Request model for updating a client."""

    name: str | None = None
    industry: str | None = None
    owner_name: str | None = None
    owner_email: EmailStr | None = None
    owner_phone: str | None = None
    website: str | None = None
    timezone: str | None = None
    primary_language: str | None = None
    plan: str | None = None


class ConfigUpdate(BaseModel):
    """Request model for updating client configuration."""

    config: dict[str, Any]


class ClientResponse(BaseModel):
    """Response model for client data."""

    id: UUID
    name: str
    slug: str
    status: ClientStatus
    industry: str | None
    website: str | None
    timezone: str
    primary_language: str
    owner_name: str | None
    owner_email: str | None
    owner_phone: str | None
    plan: str
    monthly_token_budget: int
    tokens_used_this_month: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientWithConfigResponse(ClientResponse):
    """Response model for client with full configuration."""

    config: dict[str, Any]


class ClientCreateResponse(ClientResponse):
    """Response model for client creation (includes API key)."""

    api_key: str


class ApiKeyRotateResponse(BaseModel):
    """Response model for API key rotation."""

    client_id: UUID
    api_key: str
    message: str


class UsageResponse(BaseModel):
    """Response model for usage data."""

    client_id: UUID
    monthly_token_budget: int
    tokens_used_this_month: int
    tokens_remaining: int
    usage_percent: float


# =============================================================================
# Routes
# =============================================================================


@router.post("", response_model=ClientCreateResponse, status_code=201)
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new client/tenant.
    Returns the API key - store this securely, it won't be shown again.
    """
    service = ClientService(db)

    # Check if slug already exists
    existing = await service.get_by_slug(client_data.slug)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Client with slug '{client_data.slug}' already exists",
        )

    client, api_key = await service.create_client(
        name=client_data.name,
        slug=client_data.slug,
        industry=client_data.industry,
        owner_name=client_data.owner_name,
        owner_email=client_data.owner_email,
        owner_phone=client_data.owner_phone,
        website=client_data.website,
        timezone=client_data.timezone,
        primary_language=client_data.primary_language,
        plan=client_data.plan,
        config=client_data.config,
    )

    return ClientCreateResponse(**client.__dict__, api_key=api_key)


@router.get("/{client_id}", response_model=ClientWithConfigResponse)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get client by ID."""
    service = ClientService(db)

    client = await service.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return ClientWithConfigResponse(**client.__dict__)


@router.get("/slug/{slug}", response_model=ClientWithConfigResponse)
async def get_client_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get client by slug."""
    service = ClientService(db)

    client = await service.get_by_slug(slug)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return ClientWithConfigResponse(**client.__dict__)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    updates: ClientUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update client fields."""
    service = ClientService(db)

    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    client = await service.update_client(client_id, **update_data)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return client


@router.patch("/{client_id}/config", response_model=ClientWithConfigResponse)
async def update_client_config(
    client_id: UUID,
    config_data: ConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update client configuration."""
    service = ClientService(db)

    client = await service.update_config(client_id, config_data.config)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return ClientWithConfigResponse(**client.__dict__)


@router.get("/{client_id}/config")
async def get_client_full_config(
    client_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get full client configuration including defaults."""
    service = ClientService(db)

    config = await service.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"client_id": str(client_id), "config": config}


@router.post("/{client_id}/activate", response_model=ClientResponse)
async def activate_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Activate a client."""
    service = ClientService(db)

    client = await service.activate_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return client


@router.post("/{client_id}/pause", response_model=ClientResponse)
async def pause_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Pause a client."""
    service = ClientService(db)

    client = await service.pause_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return client


@router.post("/{client_id}/rotate-api-key", response_model=ApiKeyRotateResponse)
async def rotate_api_key(
    client_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Rotate client's API key.
    Returns the new API key - store this securely, it won't be shown again.
    The old key is immediately invalidated.
    """
    service = ClientService(db)

    client, new_api_key = await service.rotate_api_key(client_id)
    if not client or not new_api_key:
        raise HTTPException(status_code=404, detail="Client not found")

    return ApiKeyRotateResponse(
        client_id=client_id,
        api_key=new_api_key,
        message="API key rotated successfully. Store this key securely.",
    )


@router.get("/{client_id}/usage", response_model=UsageResponse)
async def get_client_usage(
    client_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get client token usage for current billing period."""
    service = ClientService(db)

    client = await service.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    remaining = client.monthly_token_budget - client.tokens_used_this_month
    usage_percent = (
        (client.tokens_used_this_month / client.monthly_token_budget) * 100
        if client.monthly_token_budget > 0
        else 0
    )

    return UsageResponse(
        client_id=client_id,
        monthly_token_budget=client.monthly_token_budget,
        tokens_used_this_month=client.tokens_used_this_month,
        tokens_remaining=max(0, remaining),
        usage_percent=round(usage_percent, 2),
    )


@router.post("/{client_id}/reset-usage", response_model=UsageResponse)
async def reset_monthly_usage(
    client_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Reset monthly token usage (for billing cycle reset)."""
    service = ClientService(db)

    client = await service.reset_monthly_usage(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return UsageResponse(
        client_id=client_id,
        monthly_token_budget=client.monthly_token_budget,
        tokens_used_this_month=0,
        tokens_remaining=client.monthly_token_budget,
        usage_percent=0,
    )
