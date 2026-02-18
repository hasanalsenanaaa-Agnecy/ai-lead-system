"""
Client Service
Business logic for client/tenant management
"""

import hashlib
import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Client, ClientStatus, QualificationRule

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ClientService:
    """Service for managing clients (tenants)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, client_id: UUID) -> Client | None:
        """Get client by ID."""
        result = await self.db.execute(
            select(Client).where(
                and_(Client.id == client_id, Client.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Client | None:
        """Get client by slug."""
        result = await self.db.execute(
            select(Client).where(
                and_(Client.slug == slug, Client.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()

    async def get_by_api_key(self, api_key: str) -> Client | None:
        """Get client by API key."""
        # Hash the provided key and compare
        key_hash = self._hash_api_key(api_key)

        result = await self.db.execute(
            select(Client).where(
                and_(
                    Client.api_key_hash == key_hash,
                    Client.status == ClientStatus.ACTIVE,
                    Client.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone: str) -> Client | None:
        """Get client by their Twilio phone number."""
        # Phone numbers are stored in config
        result = await self.db.execute(
            select(Client).where(
                and_(
                    Client.status == ClientStatus.ACTIVE,
                    Client.deleted_at.is_(None),
                )
            )
        )
        clients = result.scalars().all()

        for client in clients:
            config = client.config or {}
            if config.get("twilio_phone_number") == phone:
                return client
            if config.get("twilio_numbers", []):
                if phone in config["twilio_numbers"]:
                    return client

        return None

    async def get_by_whatsapp_number(self, phone: str) -> Client | None:
        """Get client by their WhatsApp number."""
        result = await self.db.execute(
            select(Client).where(
                and_(
                    Client.status == ClientStatus.ACTIVE,
                    Client.deleted_at.is_(None),
                )
            )
        )
        clients = result.scalars().all()

        for client in clients:
            config = client.config or {}
            if config.get("whatsapp_number") == phone:
                return client
            # Also check without prefix variations
            clean_phone = phone.lstrip("+")
            if config.get("whatsapp_number", "").lstrip("+") == clean_phone:
                return client

        return None

    async def create_client(
        self,
        name: str,
        slug: str,
        industry: str,
        owner_name: str | None = None,
        owner_email: str | None = None,
        owner_phone: str | None = None,
        website: str | None = None,
        timezone: str = "America/New_York",
        primary_language: str = "en",
        plan: str = "growth",
        config: dict[str, Any] | None = None,
    ) -> tuple[Client, str]:
        """
        Create a new client.
        Returns the client and the plain API key (store this securely, it won't be shown again).
        """
        # Generate API key
        api_key = self._generate_api_key()
        api_key_hash = self._hash_api_key(api_key)

        # Generate webhook secret
        webhook_secret = secrets.token_urlsafe(32)
        webhook_secret_hash = pwd_context.hash(webhook_secret)

        client = Client(
            name=name,
            slug=slug,
            status=ClientStatus.ONBOARDING,
            industry=industry,
            owner_name=owner_name,
            owner_email=owner_email,
            owner_phone=owner_phone,
            website=website,
            timezone=timezone,
            primary_language=primary_language,
            plan=plan,
            api_key_hash=api_key_hash,
            webhook_secret_hash=webhook_secret_hash,
            config=config or {},
            monthly_token_budget=self._get_budget_for_plan(plan),
        )

        self.db.add(client)
        await self.db.flush()
        await self.db.refresh(client)

        return client, api_key

    async def update_client(
        self,
        client_id: UUID,
        **updates: Any,
    ) -> Client | None:
        """Update client fields."""
        client = await self.get_by_id(client_id)
        if not client:
            return None

        for key, value in updates.items():
            if hasattr(client, key) and value is not None:
                setattr(client, key, value)

        client.updated_at = datetime.utcnow()
        await self.db.flush()
        return client

    async def update_config(
        self,
        client_id: UUID,
        config_updates: dict[str, Any],
    ) -> Client | None:
        """Update client configuration."""
        client = await self.get_by_id(client_id)
        if not client:
            return None

        current_config = client.config or {}
        client.config = {**current_config, **config_updates}
        client.updated_at = datetime.utcnow()

        await self.db.flush()
        return client

    async def activate_client(self, client_id: UUID) -> Client | None:
        """Activate a client."""
        return await self.update_client(client_id, status=ClientStatus.ACTIVE)

    async def pause_client(self, client_id: UUID) -> Client | None:
        """Pause a client."""
        return await self.update_client(client_id, status=ClientStatus.PAUSED)

    async def rotate_api_key(self, client_id: UUID) -> tuple[Client | None, str | None]:
        """Rotate client's API key."""
        client = await self.get_by_id(client_id)
        if not client:
            return None, None

        new_api_key = self._generate_api_key()
        client.api_key_hash = self._hash_api_key(new_api_key)
        client.updated_at = datetime.utcnow()

        await self.db.flush()
        return client, new_api_key

    async def get_client_config(self, client_id: UUID) -> dict[str, Any]:
        """Get full client configuration including defaults."""
        client = await self.get_by_id(client_id)
        if not client:
            return {}

        # Default configuration
        defaults = {
            "business_name": client.name,
            "industry": client.industry,
            "timezone": client.timezone,
            "language": client.primary_language,
            "business_hours": "Monday-Friday 9:00 AM - 5:00 PM",
            "services": [],
            "qualification_questions": [
                "What service are you interested in?",
                "What is your timeline?",
                "What is your location/service area?",
            ],
            "hot_lead_triggers": [
                "Needs immediate service",
                "Has budget ready",
                "Decision maker",
                "Urgent problem",
            ],
            "escalation_triggers": [
                "Request to speak with human",
                "Complaint or frustration",
                "Complex technical question",
                "Pricing negotiation",
            ],
            "tone": "professional_friendly",
            "max_messages_before_escalation": 15,
            "response_delay_ms": 1000,
            "enable_appointment_booking": True,
            "calendar_integration": None,
            "crm_integration": None,
        }

        # Merge with client-specific config
        return {**defaults, **(client.config or {})}

    async def update_token_usage(
        self,
        client_id: UUID,
        tokens_used: int,
    ) -> tuple[bool, int]:
        """
        Update token usage for billing period.
        Returns (is_within_budget, remaining_tokens).
        """
        client = await self.get_by_id(client_id)
        if not client:
            return False, 0

        client.tokens_used_this_month += tokens_used
        remaining = client.monthly_token_budget - client.tokens_used_this_month

        await self.db.flush()
        return remaining > 0, max(0, remaining)

    async def reset_monthly_usage(self, client_id: UUID) -> Client | None:
        """Reset monthly token usage (called at billing cycle)."""
        client = await self.get_by_id(client_id)
        if not client:
            return None

        client.tokens_used_this_month = 0
        client.billing_cycle_start = datetime.utcnow()

        await self.db.flush()
        return client

    async def get_qualification_rules(
        self,
        client_id: UUID,
        category: str | None = None,
    ) -> list[QualificationRule]:
        """Get qualification rules for a client."""
        query = select(QualificationRule).where(
            and_(
                QualificationRule.client_id == client_id,
                QualificationRule.is_active == True,
            )
        )

        if category:
            query = query.where(QualificationRule.category == category)

        query = query.order_by(QualificationRule.priority.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_clients(self) -> list[Client]:
        """Get all active clients."""
        result = await self.db.execute(
            select(Client).where(
                and_(
                    Client.status == ClientStatus.ACTIVE,
                    Client.deleted_at.is_(None),
                )
            )
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _generate_api_key(self) -> str:
        """Generate a secure API key."""
        return f"als_{secrets.token_urlsafe(32)}"

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _get_budget_for_plan(self, plan: str) -> int:
        """Get monthly token budget for plan."""
        budgets = {
            "starter": 500_000,
            "growth": 1_000_000,
            "scale": 2_000_000,
        }
        return budgets.get(plan, 1_000_000)
