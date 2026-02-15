"""Analytics API endpoints."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_log import ApiLog
from app.models.database import get_db

router = APIRouter()


class AnalyticsOverview(BaseModel):
    """Dashboard overview statistics."""

    total_spend_usd: float
    total_requests: int
    total_tokens: int
    avg_cost_per_request: float
    period_start: str
    period_end: str


class SpendByModel(BaseModel):
    """Spend breakdown by model."""

    model: str
    provider: str
    spend_usd: float
    requests: int
    tokens: int


class SpendByDay(BaseModel):
    """Daily spend data point."""

    date: str
    spend_usd: float
    requests: int


@router.get("/overview")
async def get_overview(
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = "00000000-0000-0000-0000-000000000001",  # TODO: Auth
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverview:
    """Get dashboard overview statistics."""
    import uuid

    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.sum(ApiLog.cost_usd).label("total_spend"),
            func.count(ApiLog.id).label("total_requests"),
            func.sum(ApiLog.total_tokens).label("total_tokens"),
        ).where(
            and_(
                ApiLog.user_id == uuid.UUID(user_id),
                ApiLog.timestamp >= start_date,
            )
        )
    )

    row = result.one()
    total_spend = float(row.total_spend or 0)
    total_requests = row.total_requests or 0
    total_tokens = row.total_tokens or 0

    return AnalyticsOverview(
        total_spend_usd=total_spend,
        total_requests=total_requests,
        total_tokens=total_tokens,
        avg_cost_per_request=total_spend / total_requests if total_requests > 0 else 0,
        period_start=start_date.isoformat(),
        period_end=datetime.utcnow().isoformat(),
    )


@router.get("/spend/by-model")
async def get_spend_by_model(
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> list[SpendByModel]:
    """Get spend breakdown by model."""
    import uuid

    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            ApiLog.model,
            ApiLog.provider,
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
            func.sum(ApiLog.total_tokens).label("tokens"),
        )
        .where(
            and_(
                ApiLog.user_id == uuid.UUID(user_id),
                ApiLog.timestamp >= start_date,
            )
        )
        .group_by(ApiLog.model, ApiLog.provider)
        .order_by(func.sum(ApiLog.cost_usd).desc())
    )

    return [
        SpendByModel(
            model=row.model,
            provider=row.provider,
            spend_usd=float(row.spend or 0),
            requests=row.requests,
            tokens=row.tokens or 0,
        )
        for row in result.all()
    ]


@router.get("/spend/by-day")
async def get_spend_by_day(
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> list[SpendByDay]:
    """Get daily spend trend."""
    import uuid

    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(ApiLog.timestamp).label("date"),
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
        )
        .where(
            and_(
                ApiLog.user_id == uuid.UUID(user_id),
                ApiLog.timestamp >= start_date,
            )
        )
        .group_by(func.date(ApiLog.timestamp))
        .order_by(func.date(ApiLog.timestamp))
    )

    return [
        SpendByDay(
            date=str(row.date),
            spend_usd=float(row.spend or 0),
            requests=row.requests,
        )
        for row in result.all()
    ]


@router.get("/projections")
async def get_projections(
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get projected spend based on current usage trends."""
    import uuid
    from datetime import datetime

    # Get last 7 days of spend for trend analysis
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(
            func.date(ApiLog.timestamp).label("date"),
            func.sum(ApiLog.cost_usd).label("spend"),
        )
        .where(
            and_(
                ApiLog.user_id == uuid.UUID(user_id),
                ApiLog.timestamp >= seven_days_ago,
            )
        )
        .group_by(func.date(ApiLog.timestamp))
        .order_by(func.date(ApiLog.timestamp))
    )

    daily_spends = [float(row.spend or 0) for row in result.all()]

    if not daily_spends:
        return {
            "projected_daily_usd": 0,
            "projected_monthly_usd": 0,
            "trend": "no_data",
            "days_analyzed": 0,
        }

    # Calculate average daily spend
    avg_daily = sum(daily_spends) / len(daily_spends)

    # Determine trend
    if len(daily_spends) >= 3:
        recent = sum(daily_spends[-3:]) / 3
        earlier = sum(daily_spends[:3]) / 3
        if recent > earlier * 1.2:
            trend = "increasing"
        elif recent < earlier * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    return {
        "projected_daily_usd": round(avg_daily, 4),
        "projected_monthly_usd": round(avg_daily * 30, 2),
        "trend": trend,
        "days_analyzed": len(daily_spends),
        "avg_daily_spend_usd": round(avg_daily, 4),
    }
