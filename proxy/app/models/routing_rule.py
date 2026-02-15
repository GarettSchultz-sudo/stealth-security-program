"""Routing Rule model for smart model selection."""

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class RoutingRule(BaseModel):
    """
    Smart routing rule for model selection.

    Rules are evaluated in priority order. First matching rule wins.
    """

    __tablename__ = "routing_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)  # Lower = higher priority

    # Condition for matching (JSON structure)
    # Examples:
    # {"task_type": "simple", "token_estimate_max": 1000}
    # {"agent_id": "uuid", "model_requested": "claude-opus-4-5"}
    # {"time_of_day_start": "09:00", "time_of_day_end": "17:00"}
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Target configuration
    target_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # anthropic, openai, etc.
    target_model: Mapped[str] = mapped_column(String(100), nullable=False)  # Model to route to

    # Fallback if target fails
    fallback_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Analytics
    times_applied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_savings_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)
