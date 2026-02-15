"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database (SQLite for local dev, PostgreSQL for production)
    database_url: str = "sqlite+aiosqlite:///./clawshell.db"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: str = "change-this-to-a-secure-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_team: str = ""
    stripe_price_enterprise: str = ""

    # Email
    resend_api_key: str = ""
    from_email: str = "noreply@clawshell.io"

    # Sentry
    sentry_dsn: str = ""

    # App
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    log_level: str = "INFO"
    environment: str = "development"

    # Rate Limiting
    rate_limit_requests: int = 1000
    rate_limit_window_seconds: int = 60

    # Proxy
    proxy_timeout_seconds: int = 300
    max_stream_buffer_size: int = 1048576  # 1MB

    # Security Engine
    security_enabled: bool = True
    security_detection_level: str = "monitor"  # monitor, warn, enforce
    security_auto_kill: bool = False
    security_auto_kill_threshold: float = 0.95

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
