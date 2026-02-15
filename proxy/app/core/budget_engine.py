"""
Budget enforcement engine.

Checks budgets before allowing requests and updates spend after completion.
Handles real-time spend tracking, alert thresholds, and budget resets.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetAction, BudgetPeriod, BudgetScope

logger = logging.getLogger(__name__)

# Default alert thresholds (percentage of budget used)
DEFAULT_ALERT_THRESHOLDS = [50, 75, 90, 100]


@dataclass
class BudgetDecision:
    """Result of a budget check."""

    action: str  # "allow", "warn", "block", "downgrade"
    budget_id: uuid.UUID | None = None
    percent_used: float = 0.0
    remaining_usd: Decimal = Decimal("0")
    warning_message: str | None = None
    downgrade_model: str | None = None
    alerts_triggered: list[dict] = field(default_factory=list)


@dataclass
class BudgetAlert:
    """Represents a budget alert that was triggered."""

    budget_id: uuid.UUID
    budget_name: str
    threshold_percent: int
    current_percent: float
    current_spend_usd: Decimal
    limit_usd: Decimal
    alert_type: str  # "warning", "critical", "breach"


class BudgetEngine:
    """Engine for budget checking and enforcement."""

    def __init__(
        self,
        db: AsyncSession,
        alert_callback: Callable[[BudgetAlert], None] | None = None,
    ):
        self.db = db
        self.alert_callback = alert_callback
        # Track which thresholds have been alerted for each budget in this session
        self._alerted_thresholds: dict[uuid.UUID, set[int]] = {}

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
        alerts_triggered: list[dict] = []

        # Check each applicable budget
        for budget in budgets:
            if not self._budget_applies(budget, agent_id, model):
                continue

            percent_used = budget.percent_used
            remaining = budget.remaining_usd

            # Calculate projected spend after this request
            projected_spend = budget.current_spend_usd + estimated_cost
            projected_percent = float((projected_spend / budget.limit_usd) * 100) if budget.limit_usd > 0 else 0.0

            # Check alert thresholds and fire alerts if needed
            alert = self._check_alert_thresholds(budget, percent_used, projected_percent)
            if alert:
                alerts_triggered.append({
                    "budget_id": str(alert.budget_id),
                    "budget_name": alert.budget_name,
                    "threshold_percent": alert.threshold_percent,
                    "current_percent": alert.current_percent,
                    "alert_type": alert.alert_type,
                })
                if self.alert_callback:
                    try:
                        self.alert_callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback failed: {e}")

            # Check if request would exceed budget
            if estimated_cost > remaining:
                if budget.action_on_breach == BudgetAction.BLOCK:
                    return BudgetDecision(
                        action="block",
                        budget_id=budget.id,
                        percent_used=percent_used,
                        remaining_usd=remaining,
                        warning_message=f"Budget '{budget.name}' would be exceeded",
                        alerts_triggered=alerts_triggered,
                    )
                elif budget.action_on_breach == BudgetAction.DOWNGRADE_MODEL:
                    return BudgetDecision(
                        action="downgrade",
                        budget_id=budget.id,
                        percent_used=percent_used,
                        remaining_usd=remaining,
                        warning_message=f"Budget '{budget.name}' exceeded, downgrading",
                        downgrade_model=budget.downgrade_model,
                        alerts_triggered=alerts_triggered,
                    )

            # Check warning threshold
            if projected_percent >= budget.warning_threshold_percent:
                return BudgetDecision(
                    action="warn",
                    budget_id=budget.id,
                    percent_used=percent_used,
                    remaining_usd=remaining,
                    warning_message=f"Budget '{budget.name}' at {percent_used:.1f}% capacity",
                    alerts_triggered=alerts_triggered,
                )

        return BudgetDecision(action="allow", alerts_triggered=alerts_triggered)

    async def update_spend(
        self,
        user_id: uuid.UUID,
        cost: Decimal,
        agent_id: uuid.UUID | None = None,
        model: str | None = None,
    ) -> list[BudgetAlert]:
        """
        Update budget spend after a request completes.

        Updates all applicable budgets and checks for alert thresholds.

        Args:
            user_id: User ID
            cost: Cost to add to budgets
            agent_id: Optional agent ID for scoped budgets
            model: Optional model for scoped budgets

        Returns:
            List of BudgetAlert that were triggered
        """
        budgets = await self._get_active_budgets(user_id)
        triggered_alerts: list[BudgetAlert] = []

        for budget in budgets:
            # For scoped budgets, only update if they apply
            if not self._budget_applies(budget, agent_id, model):
                continue

            # Record previous state for alert checking
            previous_percent = budget.percent_used

            # Update spend
            budget.current_spend_usd += cost

            # Check new state for alerts
            new_percent = budget.percent_used

            # Check if we crossed any thresholds
            alert = self._check_threshold_crossing(budget, previous_percent, new_percent)
            if alert:
                triggered_alerts.append(alert)
                if self.alert_callback:
                    try:
                        self.alert_callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback failed: {e}")

        await self.db.commit()
        return triggered_alerts

    async def record_real_time_spend(
        self,
        user_id: uuid.UUID,
        cost: Decimal,
        agent_id: uuid.UUID | None = None,
        model: str | None = None,
    ) -> dict:
        """
        Record spend in real-time with immediate alert checking.

        This is the primary method for updating spend during active requests.

        Args:
            user_id: User ID
            cost: Cost to add
            agent_id: Optional agent ID
            model: Optional model name

        Returns:
            Dict with updated budgets and any triggered alerts
        """
        alerts = await self.update_spend(user_id, cost, agent_id, model)

        # Get fresh budget status
        budgets = await self._get_active_budgets(user_id)
        budget_status = [
            {
                "id": str(b.id),
                "name": b.name,
                "current_spend_usd": float(b.current_spend_usd),
                "limit_usd": float(b.limit_usd),
                "percent_used": b.percent_used,
                "status": self._get_budget_status_level(b),
            }
            for b in budgets
            if self._budget_applies(b, agent_id, model)
        ]

        return {
            "budgets_updated": len(budget_status),
            "alerts_triggered": [
                {
                    "budget_name": a.budget_name,
                    "threshold_percent": a.threshold_percent,
                    "current_percent": a.current_percent,
                    "alert_type": a.alert_type,
                }
                for a in alerts
            ],
            "budget_status": budget_status,
        }

    def _check_alert_thresholds(
        self,
        budget: Budget,
        current_percent: float,
        projected_percent: float,
    ) -> BudgetAlert | None:
        """
        Check if any alert thresholds should be triggered.

        Uses standard thresholds: 50%, 75%, 90%, 100%
        """
        # Initialize alerted thresholds for this budget if needed
        if budget.id not in self._alerted_thresholds:
            self._alerted_thresholds[budget.id] = set()

        # Check each threshold
        for threshold in DEFAULT_ALERT_THRESHOLDS:
            if projected_percent >= threshold and threshold not in self._alerted_thresholds[budget.id]:
                # Mark this threshold as alerted
                self._alerted_thresholds[budget.id].add(threshold)

                # Determine alert type
                if threshold >= 100:
                    alert_type = "breach"
                elif threshold >= budget.critical_threshold_percent:
                    alert_type = "critical"
                else:
                    alert_type = "warning"

                return BudgetAlert(
                    budget_id=budget.id,
                    budget_name=budget.name,
                    threshold_percent=threshold,
                    current_percent=projected_percent,
                    current_spend_usd=budget.current_spend_usd,
                    limit_usd=budget.limit_usd,
                    alert_type=alert_type,
                )

        return None

    def _check_threshold_crossing(
        self,
        budget: Budget,
        previous_percent: float,
        new_percent: float,
    ) -> BudgetAlert | None:
        """
        Check if we crossed any thresholds with this spend update.
        """
        # Initialize alerted thresholds for this budget if needed
        if budget.id not in self._alerted_thresholds:
            self._alerted_thresholds[budget.id] = set()

        # Check each threshold
        for threshold in DEFAULT_ALERT_THRESHOLDS:
            # Check if we crossed this threshold
            if previous_percent < threshold <= new_percent:
                if threshold not in self._alerted_thresholds[budget.id]:
                    self._alerted_thresholds[budget.id].add(threshold)

                    # Determine alert type
                    if threshold >= 100:
                        alert_type = "breach"
                    elif threshold >= budget.critical_threshold_percent:
                        alert_type = "critical"
                    else:
                        alert_type = "warning"

                    return BudgetAlert(
                        budget_id=budget.id,
                        budget_name=budget.name,
                        threshold_percent=threshold,
                        current_percent=new_percent,
                        current_spend_usd=budget.current_spend_usd,
                        limit_usd=budget.limit_usd,
                        alert_type=alert_type,
                    )

        return None

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
                "alert_thresholds": {
                    "warning": budget.warning_threshold_percent,
                    "critical": budget.critical_threshold_percent,
                    "standard": DEFAULT_ALERT_THRESHOLDS,
                },
            }
            for budget in budgets
        ]

    async def get_budget_usage_history(
        self,
        budget_id: uuid.UUID,
        user_id: uuid.UUID,
        days: int = 30,
    ) -> dict:
        """
        Get usage history for a specific budget.

        Aggregates API logs to show spending over time.

        Args:
            budget_id: Budget ID to get history for
            user_id: User ID (for authorization)
            days: Number of days of history to retrieve

        Returns:
            Dict with budget info and daily usage history
        """
        from app.models.api_log import ApiLog

        # Verify budget belongs to user
        budget = await self.db.get(Budget, budget_id)
        if not budget or budget.user_id != user_id:
            return {"error": "Budget not found", "status": 404}

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Query daily aggregated usage
        # Note: This uses PostgreSQL's date_trunc for daily aggregation
        result = await self.db.execute(
            select(
                func.date_trunc("day", ApiLog.timestamp).label("day"),
                func.sum(ApiLog.cost_usd).label("total_cost"),
                func.count(ApiLog.id).label("request_count"),
                func.sum(ApiLog.total_tokens).label("total_tokens"),
            )
            .where(
                and_(
                    ApiLog.user_id == user_id,
                    ApiLog.timestamp >= start_date,
                    ApiLog.timestamp <= end_date,
                )
            )
            .group_by(func.date_trunc("day", ApiLog.timestamp))
            .order_by(func.date_trunc("day", ApiLog.timestamp))
        )

        daily_usage = []
        for row in result:
            daily_usage.append({
                "date": row.day.isoformat() if row.day else None,
                "cost_usd": float(row.total_cost) if row.total_cost else 0.0,
                "request_count": row.request_count or 0,
                "total_tokens": row.total_tokens or 0,
            })

        # Calculate totals
        total_cost = sum(d["cost_usd"] for d in daily_usage)
        total_requests = sum(d["request_count"] for d in daily_usage)

        return {
            "budget_id": str(budget_id),
            "budget_name": budget.name,
            "period": budget.period.value,
            "limit_usd": float(budget.limit_usd),
            "current_spend_usd": float(budget.current_spend_usd),
            "days_included": days,
            "total_cost_usd": total_cost,
            "total_requests": total_requests,
            "daily_usage": daily_usage,
        }

    async def get_budget_summary_with_alerts(self, user_id: uuid.UUID) -> dict:
        """
        Get comprehensive budget summary including alert status.

        Returns:
            Dict with all budgets, their status, and any active alerts
        """
        budgets = await self._get_active_budgets(user_id)

        summary = {
            "total_budgets": len(budgets),
            "active_alerts": [],
            "budgets": [],
            "overall_status": "ok",
        }

        for budget in budgets:
            status = self._get_budget_status_level(budget)
            percent = budget.percent_used

            budget_info = {
                "id": str(budget.id),
                "name": budget.name,
                "period": budget.period.value,
                "scope": budget.scope.value,
                "limit_usd": float(budget.limit_usd),
                "current_spend_usd": float(budget.current_spend_usd),
                "remaining_usd": float(budget.remaining_usd),
                "percent_used": percent,
                "status": status,
                "reset_at": budget.reset_at.isoformat(),
            }
            summary["budgets"].append(budget_info)

            # Track alerts
            if status == "critical":
                summary["overall_status"] = "critical"
                summary["active_alerts"].append({
                    "budget_name": budget.name,
                    "type": "critical",
                    "message": f"Budget '{budget.name}' is at {percent:.1f}% capacity",
                    "percent_used": percent,
                })
            elif status == "warning" and summary["overall_status"] != "critical":
                summary["overall_status"] = "warning"
                summary["active_alerts"].append({
                    "budget_name": budget.name,
                    "type": "warning",
                    "message": f"Budget '{budget.name}' is at {percent:.1f}% capacity",
                    "percent_used": percent,
                })

        return summary

    async def reset_budget(self, budget_id: uuid.UUID) -> None:
        """Reset a budget's spend to zero."""
        budget = await self.db.get(Budget, budget_id)
        if budget:
            budget.current_spend_usd = Decimal("0")
            budget.reset_at = self._calculate_next_reset(budget.period)
            # Clear alerted thresholds for this budget
            if budget.id in self._alerted_thresholds:
                del self._alerted_thresholds[budget.id]
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
            # Clear alerted thresholds for this budget
            if budget.id in self._alerted_thresholds:
                del self._alerted_thresholds[budget.id]

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
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
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
