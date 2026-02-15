"""
Budget enforcement engine.

Checks budgets before allowing requests and updates spend after completion.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetAction, BudgetPeriod, BudgetScope


@dataclass
class BudgetDecision:
    """Result of a budget check."""

    action: str  # "allow", "warn", "block", "downgrade"
    budget_id: uuid.UUID | None = None
    percent_used: float = 0.0
    remaining_usd: Decimal = Decimal("0")
    warning_message: str | None = None
    downgrade_model: str | None = None


class BudgetEngine:
    """Engine for budget checking and enforcement."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_budget(
        self,
        user_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        model: str,
        estimated_cost: Decimal,
    ) -> BudgetDecision:
        """
        Check if a request can proceed based on budget constraints.

        Checks budgets in order: per-model > per-agent > global

        Args:
            user_id: User ID
            agent_id: Agent ID (if applicable)
            model: Requested model
            estimated_cost: Estimated cost of the request

        Returns:
            BudgetDecision with action to take
        """
        # Get all active budgets for this user
        budgets = await self._get_active_budgets(user_id)

        # Check each applicable budget
        for budget in budgets:
            if not self._budget_applies(budget, agent_id, model):
                continue

            percent_used = budget.percent_used
            remaining = budget.remaining_usd

            # Check if request would exceed budget
            if estimated_cost > remaining:
                if budget.action_on_breach == BudgetAction.BLOCK:
                    return BudgetDecision(
                        action="block",
                        budget_id=budget.id,
                        percent_used=percent_used,
                        remaining_usd=remaining,
                        warning_message=f"Budget '{budget.name}' would be exceeded",
                    )
                elif budget.action_on_breach == BudgetAction.DOWNGRADE_MODEL:
                    return BudgetDecision(
                        action="downgrade",
                        budget_id=budget.id,
                        percent_used=percent_used,
                        remaining_usd=remaining,
                        warning_message=f"Budget '{budget.name}' exceeded, downgrading",
                        downgrade_model=budget.downgrade_model,
                    )

            # Check warning threshold
            projected_percent = float((budget.current_spend_usd + estimated_cost) / budget.limit_usd * 100)
            if projected_percent >= budget.warning_threshold_percent:
                return BudgetDecision(
                    action="warn",
                    budget_id=budget.id,
                    percent_used=percent_used,
                    remaining_usd=remaining,
                    warning_message=f"Budget '{budget.name}' at {percent_used:.1f}% capacity",
                )

        return BudgetDecision(action="allow")

    async def update_spend(self, user_id: uuid.UUID, cost: Decimal) -> None:
        """
        Update budget spend after a request completes.

        Updates all applicable budgets.
        """
        budgets = await self._get_active_budgets(user_id)

        for budget in budgets:
            budget.current_spend_usd += cost

        await self.db.commit()

    async def get_budget_status(self, user_id: uuid.UUID) -> list[dict]:
        """Get status of all budgets for a user."""
        budgets = await self._get_active_budgets(user_id)

        return [
            {
                "id": str(budget.id),
                "name": budget.name,
                "period": budget.period.value,
                "scope": budget.scope.value,
                "limit_usd": float(budget.limit_usd),
                "current_spend_usd": float(budget.current_spend_usd),
                "remaining_usd": float(budget.remaining_usd),
                "percent_used": budget.percent_used,
                "reset_at": budget.reset_at.isoformat(),
                "status": self._get_budget_status_level(budget),
            }
            for budget in budgets
        ]

    async def reset_budget(self, budget_id: uuid.UUID) -> None:
        """Reset a budget's spend to zero."""
        budget = await self.db.get(Budget, budget_id)
        if budget:
            budget.current_spend_usd = Decimal("0")
            budget.reset_at = self._calculate_next_reset(budget.period)
            await self.db.commit()

    async def reset_expired_budgets(self) -> int:
        """
        Reset all budgets that have expired.

        Called by a scheduled task.

        Returns:
            Number of budgets reset
        """
        now = datetime.utcnow()

        result = await self.db.execute(
            select(Budget).where(
                and_(
                    Budget.is_active == True,  # noqa: E712
                    Budget.reset_at <= now,
                )
            )
        )
        expired_budgets = result.scalars().all()

        for budget in expired_budgets:
            budget.current_spend_usd = Decimal("0")
            budget.reset_at = self._calculate_next_reset(budget.period)

        await self.db.commit()
        return len(expired_budgets)

    async def _get_active_budgets(self, user_id: uuid.UUID) -> list[Budget]:
        """Get all active budgets for a user, ordered by specificity."""
        result = await self.db.execute(
            select(Budget)
            .where(
                and_(
                    Budget.user_id == user_id,
                    Budget.is_active == True,  # noqa: E712
                )
            )
            .order_by(Budget.scope)  # per_model, per_agent, global
        )
        return list(result.scalars().all())

    def _budget_applies(
        self,
        budget: Budget,
        agent_id: uuid.UUID | None,
        model: str,
    ) -> bool:
        """Check if a budget applies to a given request."""
        if budget.scope == BudgetScope.GLOBAL:
            return True
        elif budget.scope == BudgetScope.PER_AGENT:
            return agent_id and budget.scope_identifier == str(agent_id)
        elif budget.scope == BudgetScope.PER_MODEL:
            return model.startswith(budget.scope_identifier or "")
        elif budget.scope == BudgetScope.PER_WORKFLOW:
            # Workflow scope requires metadata that we don't have here
            return False
        return False

    def _get_budget_status_level(self, budget: Budget) -> str:
        """Get status level for a budget (ok, warning, critical)."""
        percent = budget.percent_used
        if percent >= budget.critical_threshold_percent:
            return "critical"
        elif percent >= budget.warning_threshold_percent:
            return "warning"
        return "ok"

    def _calculate_next_reset(self, period: BudgetPeriod) -> datetime:
        """Calculate the next reset time for a budget period."""
        now = datetime.utcnow()

        if period == BudgetPeriod.DAILY:
            return (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif period == BudgetPeriod.WEEKLY:
            days_until_monday = (7 - now.weekday()) % 7
            return (now + timedelta(days=days_until_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif period == BudgetPeriod.MONTHLY:
            # First day of next month
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            return next_month

        return now + timedelta(days=30)  # Default to 30 days
