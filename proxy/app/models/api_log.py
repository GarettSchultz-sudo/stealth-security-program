"""API Log model - the core table for tracking all API calls."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ApiLog(BaseModel):
    """
    Core table for logging all API requests through the proxy.

    This table captures every request made through the proxy for cost tracking,
    analytics, and auditing purposes.
    """

    __tablename__ = "api_logs"

    # Request identification
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True
    )

    # Timestamp (indexed for time-based queries)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False, index=True
    )

    # Provider and model info
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # anthropic, openai, google, etc.
    model: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # claude-sonnet-4-20250514, gpt-4o, etc.
    endpoint: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # /v1/messages, /v1/chat/completions

    # Token usage
    request_tokens: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )  # Input tokens
    response_tokens: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )  # Output tokens
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Prompt caching tokens (Anthropic-specific)
    cache_creation_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Cost (stored as Decimal for precision)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=Decimal("0"))

    # Performance metrics
    latency_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Response status
    status_code: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=200)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Request metadata (task type, workflow name, etc.)
    request_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Streaming flag
    is_streaming: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Routing decision (if smart routing was applied)
    original_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # What was requested
    routed_to_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # What was actually used

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_api_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_api_logs_agent_timestamp", "agent_id", "timestamp"),
        Index("ix_api_logs_model_timestamp", "model", "timestamp"),
        Index("ix_api_logs_provider_timestamp", "provider", "timestamp"),
    )
