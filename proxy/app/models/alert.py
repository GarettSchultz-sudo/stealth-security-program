"""Alert model for notifications."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AlertType(str, enum.Enum):
    """Types of alerts."""

    BUDGET_WARNING = "budget_warning"  # Budget approaching limit
    BUDGET_BREACH = "budget_breach"  # Budget exceeded
    COST_SPIKE = "cost_spike"  # Unusual cost increase
    ERROR_RATE = "error_rate"  # High error rate detected
    AGENT_INACTIVE = "agent_inactive"  # Agent hasn't been seen


class AlertDelivery(str, enum.Enum):
    """Alert delivery methods."""

    EMAIL = "email"
    SLACK_WEBHOOK = "slack_webhook"
    DISCORD_WEBHOOK = "discord_webhook"
    GENERIC_WEBHOOK = "generic_webhook"


class Alert(BaseModel):
    """Alert configuration for notifications."""

    __tablename__ = "alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    budget_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True
    )

    # Alert configuration
    type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    threshold_percent: Mapped[int] = mapped_column(default=80)  # Trigger at this percentage

    # Delivery configuration
    delivery: Mapped[AlertDelivery] = mapped_column(
        Enum(AlertDelivery), default=AlertDelivery.EMAIL, nullable=False
    )
    delivery_config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # webhook_url, email, etc.

    # Status tracking
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trigger_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Cooldown to prevent spam
    cooldown_minutes: Mapped[int] = mapped_column(
        default=60, nullable=False
    )  # Min time between triggers

    # Relationships
    user: Mapped["User"] = relationship(back_populates="alerts")

    @property
    def can_trigger(self) -> bool:
        """Check if enough time has passed since last trigger."""
        if not self.last_triggered:
            return True
        elapsed = datetime.now(self.last_triggered.tzinfo) - self.last_triggered
        return elapsed.total_seconds() >= (self.cooldown_minutes * 60)
