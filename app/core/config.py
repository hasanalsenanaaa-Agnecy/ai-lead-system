"""
Application Settings
Centralized configuration management using Pydantic Settings
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file's directory (project root),
# so it works regardless of the working directory uvicorn is launched from.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = "ai-lead-system"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: SecretStr = Field(..., min_length=32)

    # -------------------------------------------------------------------------
    # API Server
    # -------------------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # Comma-separated list of allowed origins for CORS.
    # Development default includes common local dev servers.
    # In production, set ALLOWED_ORIGINS=https://dashboard.yourdomain.com
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        """Parse ALLOWED_ORIGINS into a list, filtering out empty strings."""
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: SecretStr
    database_pool_size: int = 20
    database_max_overflow: int = 10

    supabase_url: str
    supabase_anon_key: SecretStr
    supabase_service_key: SecretStr

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # -------------------------------------------------------------------------
    # AI Providers - Anthropic
    # -------------------------------------------------------------------------
    anthropic_api_key: SecretStr
    anthropic_model_qualification: str = "claude-sonnet-4-20250514"
    anthropic_model_routing: str = "claude-haiku-3-5-20241022"
    anthropic_max_tokens: int = 2048
    anthropic_temperature: float = 0.3

    # -------------------------------------------------------------------------
    # AI Providers - OpenAI (Backup)
    # -------------------------------------------------------------------------
    openai_api_key: SecretStr | None = None
    openai_model_fallback: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # -------------------------------------------------------------------------
    # Meta WhatsApp Cloud API
    # -------------------------------------------------------------------------
    meta_whatsapp_token: SecretStr | None = None
    meta_whatsapp_phone_number_id: str | None = None
    meta_whatsapp_business_account_id: str | None = None
    meta_app_secret: SecretStr | None = None
    meta_webhook_verify_token: str | None = None

    # -------------------------------------------------------------------------
    # Cal.com (Calendar)
    # -------------------------------------------------------------------------
    calcom_api_key: SecretStr | None = None
    calcom_base_url: str = "https://api.cal.com/v1"
    calcom_default_event_type_id: int | None = None

    # -------------------------------------------------------------------------
    # HubSpot (CRM)
    # -------------------------------------------------------------------------
    hubspot_access_token: SecretStr | None = None
    hubspot_portal_id: str | None = None

    # -------------------------------------------------------------------------
    # Email (SendGrid or SMTP)
    # -------------------------------------------------------------------------
    sendgrid_api_key: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    email_from_address: str = "noreply@aileads.local"
    email_from_name: str = "AI Lead System"

    # -------------------------------------------------------------------------
    # Monitoring
    # -------------------------------------------------------------------------
    sentry_dsn: str | None = None
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1
    logtail_source_token: str | None = None

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    api_key_header: str = "X-API-Key"
    webhook_secret: SecretStr | None = None

    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 100

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    enable_voice_ai: bool = False
    enable_whatsapp: bool = True
    enable_web_chat: bool = True
    enable_prompt_caching: bool = True

    # -------------------------------------------------------------------------
    # Cost Controls
    # -------------------------------------------------------------------------
    default_monthly_token_budget: int = 1_000_000
    alert_threshold_percent: int = 80
    max_conversation_length: int = 50

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return upper

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
