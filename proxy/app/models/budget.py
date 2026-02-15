"""Budget model for cost limits and enforcement."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class BudgetPeriod(str, enum.Enum):
    """Budget reset period."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class BudgetScope(str, enum.Enum):
    """Scope of budget application."""

    GLOBAL = "global"  # Applies to all usage
    PER_AGENT = "per_agent"  # Specific to one agent
    PER_MODEL = "per_model"  # Specific to a model
    PER_WORKFLOW = "per_workflow"  # Specific to a workflow


class BudgetAction(str, enum.Enum):
    """Action to take when budget is breached."""

    ALERT_ONLY = "alert_only"  # Just send notification
    BLOCK = "block"  # Block requests
    DOWNGRADE_MODEL = "downgrade_model"  # Switch to cheaper model


class Budget(BaseModel):
    """Budget configuration for cost control."""

    __tablename__ = "budgets"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    period: Mapped[BudgetPeriod] = mapped_column(Enum(BudgetPeriod), default=BudgetPeriod.MONTHLY, nullable=False)

    # Budget limits
    limit_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_spend_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Scope configuration
    scope: Mapped[BudgetScope] = mapped_column(Enum(BudgetScope), default=BudgetScope.GLOBAL, nullable=False)
    scope_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)  # agent_id, model name, or workflow name

    # Action on breach
    action_on_breach: Mapped[BudgetAction] = mapped_column(
        Enum(BudgetAction), default=BudgetAction.ALERT_ONLY, nullable=False
    )
    downgrade_model: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Target model for downgrade

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    warning_threshold_percent: Mapped[int] = mapped_column(default=80)  # Alert at this percentage
    critical_threshold_percent: Mapped[int] = mapped_column(default=100)  # Alert/action at this percentage

    # Relationships
    user: Mapped["User"] = relationship(back_populates="budgets")

    __table_args__ = (
        Index("ix_budgets_user_scope", "user_id", "scope", "scope_identifier"),
    )

    @property
    def percent_used(self) -> float:
        """Calculate percentage of budget used."""
        if self.limit_usd == 0:
            return 0.0
        return float((self.current_spend_usd / self.limit_usd) * 100)

    @property
    def remaining_usd(self) -> Decimal:
        """Calculate remaining budget."""
        return max(Decimal("0"), self.limit_usd - self.current_spend_usd)
