"""Budget management API endpoints."""

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.budget_engine import BudgetEngine
from app.models.budget import Budget, BudgetAction, BudgetPeriod, BudgetScope
from app.models.database import get_db

router = APIRouter()


class BudgetCreate(BaseModel):
    """Request body for creating a budget."""

    name: str = Field(..., min_length=1, max_length=255)
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    limit_usd: Decimal = Field(..., gt=0)
    scope: BudgetScope = BudgetScope.GLOBAL
    scope_identifier: str | None = None
    action_on_breach: BudgetAction = BudgetAction.ALERT_ONLY
    downgrade_model: str | None = None
    warning_threshold_percent: int = Field(default=80, ge=1, le=99)
    critical_threshold_percent: int = Field(default=100, ge=1, le=100)


class BudgetUpdate(BaseModel):
    """Request body for updating a budget."""

    name: str | None = Field(None, min_length=1, max_length=255)
    limit_usd: Decimal | None = Field(None, gt=0)
    action_on_breach: BudgetAction | None = None
    downgrade_model: str | None = None
    warning_threshold_percent: int | None = Field(None, ge=1, le=99)
    critical_threshold_percent: int | None = Field(None, ge=1, le=100)
    is_active: bool | None = None


class BudgetResponse(BaseModel):
    """Budget response model."""

    id: str
    name: str
    period: str
    scope: str
    scope_identifier: str | None
    limit_usd: float
    current_spend_usd: float
    remaining_usd: float
    percent_used: float
    action_on_breach: str
    downgrade_model: str | None
    warning_threshold_percent: int
    critical_threshold_percent: int
    is_active: bool
    reset_at: str
    status: str


def calculate_next_reset(period: BudgetPeriod) -> datetime:
    """Calculate the next reset time for a budget period."""
    from datetime import timedelta

    now = datetime.utcnow()

    if period == BudgetPeriod.DAILY:
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == BudgetPeriod.WEEKLY:
        days_until_monday = (7 - now.weekday()) % 7
        return (now + timedelta(days=days_until_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == BudgetPeriod.MONTHLY:
        if now.month == 12:
            return now.replace(year=now.year + 1, month=1, day=1)
        return now.replace(month=now.month + 1, day=1)

    return now + timedelta(days=30)


def get_budget_status(percent_used: float, warning: int, critical: int) -> str:
    """Get status level for a budget."""
    if percent_used >= critical:
        return "critical"
    elif percent_used >= warning:
        return "warning"
    return "ok"


@router.post("", response_model=BudgetResponse)
async def create_budget(
    budget_data: BudgetCreate,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Create a new budget."""
    budget = Budget(
        user_id=uuid.UUID(user_id),
        name=budget_data.name,
        period=budget_data.period,
        limit_usd=budget_data.limit_usd,
        scope=budget_data.scope,
        scope_identifier=budget_data.scope_identifier,
        action_on_breach=budget_data.action_on_breach,
        downgrade_model=budget_data.downgrade_model,
        warning_threshold_percent=budget_data.warning_threshold_percent,
        critical_threshold_percent=budget_data.critical_threshold_percent,
        reset_at=calculate_next_reset(budget_data.period),
    )

    db.add(budget)
    await db.commit()
    await db.refresh(budget)

    return BudgetResponse(
        id=str(budget.id),
        name=budget.name,
        period=budget.period.value,
        scope=budget.scope.value,
        scope_identifier=budget.scope_identifier,
        limit_usd=float(budget.limit_usd),
        current_spend_usd=float(budget.current_spend_usd),
        remaining_usd=float(budget.remaining_usd),
        percent_used=budget.percent_used,
        action_on_breach=budget.action_on_breach.value,
        downgrade_model=budget.downgrade_model,
        warning_threshold_percent=budget.warning_threshold_percent,
        critical_threshold_percent=budget.critical_threshold_percent,
        is_active=budget.is_active,
        reset_at=budget.reset_at.isoformat(),
        status=get_budget_status(
            budget.percent_used,
            budget.warning_threshold_percent,
            budget.critical_threshold_percent,
        ),
    )


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> list[BudgetResponse]:
    """List all budgets for the current user."""
    result = await db.execute(
        select(Budget)
        .where(Budget.user_id == uuid.UUID(user_id))
        .order_by(Budget.created_at.desc())
    )
    budgets = result.scalars().all()

    return [
        BudgetResponse(
            id=str(b.id),
            name=b.name,
            period=b.period.value,
            scope=b.scope.value,
            scope_identifier=b.scope_identifier,
            limit_usd=float(b.limit_usd),
            current_spend_usd=float(b.current_spend_usd),
            remaining_usd=float(b.remaining_usd),
            percent_used=b.percent_used,
            action_on_breach=b.action_on_breach.value,
            downgrade_model=b.downgrade_model,
            warning_threshold_percent=b.warning_threshold_percent,
            critical_threshold_percent=b.critical_threshold_percent,
            is_active=b.is_active,
            reset_at=b.reset_at.isoformat(),
            status=get_budget_status(
                b.percent_used, b.warning_threshold_percent, b.critical_threshold_percent
            ),
        )
        for b in budgets
    ]


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Get a specific budget by ID."""
    budget = await db.get(Budget, uuid.UUID(budget_id))

    if not budget or budget.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Budget not found")

    return BudgetResponse(
        id=str(budget.id),
        name=budget.name,
        period=budget.period.value,
        scope=budget.scope.value,
        scope_identifier=budget.scope_identifier,
        limit_usd=float(budget.limit_usd),
        current_spend_usd=float(budget.current_spend_usd),
        remaining_usd=float(budget.remaining_usd),
        percent_used=budget.percent_used,
        action_on_breach=budget.action_on_breach.value,
        downgrade_model=budget.downgrade_model,
        warning_threshold_percent=budget.warning_threshold_percent,
        critical_threshold_percent=budget.critical_threshold_percent,
        is_active=budget.is_active,
        reset_at=budget.reset_at.isoformat(),
        status=get_budget_status(
            budget.percent_used, budget.warning_threshold_percent, budget.critical_threshold_percent
        ),
    )


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    budget_data: BudgetUpdate,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Update a budget."""
    budget = await db.get(Budget, uuid.UUID(budget_id))

    if not budget or budget.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Budget not found")

    update_data = budget_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(budget, key, value)

    await db.commit()
    await db.refresh(budget)

    return BudgetResponse(
        id=str(budget.id),
        name=budget.name,
        period=budget.period.value,
        scope=budget.scope.value,
        scope_identifier=budget.scope_identifier,
        limit_usd=float(budget.limit_usd),
        current_spend_usd=float(budget.current_spend_usd),
        remaining_usd=float(budget.remaining_usd),
        percent_used=budget.percent_used,
        action_on_breach=budget.action_on_breach.value,
        downgrade_model=budget.downgrade_model,
        warning_threshold_percent=budget.warning_threshold_percent,
        critical_threshold_percent=budget.critical_threshold_percent,
        is_active=budget.is_active,
        reset_at=budget.reset_at.isoformat(),
        status=get_budget_status(
            budget.percent_used, budget.warning_threshold_percent, budget.critical_threshold_percent
        ),
    )


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete (soft delete) a budget."""
    budget = await db.get(Budget, uuid.UUID(budget_id))

    if not budget or budget.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Budget not found")

    budget.is_active = False
    await db.commit()

    return {"status": "deleted", "id": budget_id}


@router.post("/{budget_id}/reset")
async def reset_budget(
    budget_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually reset a budget's spend."""
    budget = await db.get(Budget, uuid.UUID(budget_id))

    if not budget or budget.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Budget not found")

    budget.current_spend_usd = Decimal("0")
    budget.reset_at = calculate_next_reset(budget.period)
    await db.commit()

    return {
        "status": "reset",
        "id": budget_id,
        "new_reset_at": budget.reset_at.isoformat(),
    }


class BudgetStatusResponse(BaseModel):
    """Budget status response model."""

    id: str
    name: str
    period: str
    scope: str
    limit_usd: float
    current_spend_usd: float
    remaining_usd: float
    percent_used: float
    status: str
    reset_at: str
    alert_thresholds: dict


class BudgetUsageHistoryResponse(BaseModel):
    """Budget usage history response model."""

    budget_id: str
    budget_name: str
    period: str
    limit_usd: float
    current_spend_usd: float
    days_included: int
    total_cost_usd: float
    total_requests: int
    daily_usage: list[dict]


class BudgetSummaryResponse(BaseModel):
    """Budget summary with alerts response model."""

    total_budgets: int
    active_alerts: list[dict]
    budgets: list[dict]
    overall_status: str


@router.get("/status/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> BudgetSummaryResponse:
    """
    Get comprehensive budget summary including alert status.

    Returns all budgets, their current status, and any active alerts.
    """
    engine = BudgetEngine(db)
    summary = await engine.get_budget_summary_with_alerts(uuid.UUID(user_id))
    return BudgetSummaryResponse(**summary)


@router.get("/{budget_id}/status", response_model=BudgetStatusResponse)
async def get_budget_status(
    budget_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> BudgetStatusResponse:
    """
    Get current status of a specific budget.

    Includes alert thresholds and real-time spend information.
    """
    budget = await db.get(Budget, uuid.UUID(budget_id))

    if not budget or budget.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Budget not found")

    engine = BudgetEngine(db)
    status_level = engine._get_budget_status_level(budget)

    return BudgetStatusResponse(
        id=str(budget.id),
        name=budget.name,
        period=budget.period.value,
        scope=budget.scope.value,
        limit_usd=float(budget.limit_usd),
        current_spend_usd=float(budget.current_spend_usd),
        remaining_usd=float(budget.remaining_usd),
        percent_used=budget.percent_used,
        status=status_level,
        reset_at=budget.reset_at.isoformat(),
        alert_thresholds={
            "warning": budget.warning_threshold_percent,
            "critical": budget.critical_threshold_percent,
            "standard": [50, 75, 90, 100],
        },
    )


@router.get("/{budget_id}/history", response_model=BudgetUsageHistoryResponse)
async def get_budget_usage_history(
    budget_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history"),
    db: AsyncSession = Depends(get_db),
) -> BudgetUsageHistoryResponse:
    """
    Get usage history for a specific budget.

    Returns daily aggregated spending data for the specified time period.
    """
    engine = BudgetEngine(db)
    history = await engine.get_budget_usage_history(
        budget_id=uuid.UUID(budget_id),
        user_id=uuid.UUID(user_id),
        days=days,
    )

    if "error" in history:
        raise HTTPException(status_code=history.get("status", 404), detail=history["error"])

    return BudgetUsageHistoryResponse(**history)
