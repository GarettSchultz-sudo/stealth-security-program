"""Analytics API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentUserId
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
    avg_latency_ms: float
    error_rate: float


class SpendByModel(BaseModel):
    """Spend breakdown by model."""

    model: str
    provider: str
    spend_usd: float
    requests: int
    tokens: int
    avg_latency_ms: float
    percent_of_total: float


class SpendByProvider(BaseModel):
    """Spend breakdown by provider."""

    provider: str
    spend_usd: float
    requests: int
    tokens: int
    model_count: int
    percent_of_total: float


class SpendByAgent(BaseModel):
    """Spend breakdown by agent."""

    agent_id: Optional[str]
    agent_name: str
    spend_usd: float
    requests: int
    tokens: int
    avg_latency_ms: float
    percent_of_total: float


class SpendByDay(BaseModel):
    """Daily spend data point."""

    date: str
    spend_usd: float
    requests: int
    tokens: int
    avg_latency_ms: float


class TrendData(BaseModel):
    """Trend analysis data."""

    current_period_spend: float
    previous_period_spend: float
    change_percent: float
    trend_direction: str  # "up", "down", "stable"
    daily_avg_spend: float
    projected_monthly_spend: float


class SummaryStats(BaseModel):
    """Summary statistics for dashboard."""

    today_spend_usd: float
    today_requests: int
    week_spend_usd: float
    week_requests: int
    month_spend_usd: float
    month_requests: int
    most_used_model: Optional[str]
    most_expensive_model: Optional[str]
    top_provider: Optional[str]
    avg_daily_spend_usd: float


@router.get("/overview")
async def get_overview(
    user_id: CurrentUserId,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverview:
    """Get dashboard overview statistics."""
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.sum(ApiLog.cost_usd).label("total_spend"),
            func.count(ApiLog.id).label("total_requests"),
            func.sum(ApiLog.total_tokens).label("total_tokens"),
            func.avg(ApiLog.latency_ms).label("avg_latency"),
            func.sum(case((ApiLog.status_code >= 400, 1), else_=0)).label("error_count"),
        ).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= start_date,
            )
        )
    )

    row = result.one()
    total_spend = float(row.total_spend or 0)
    total_requests = row.total_requests or 0
    total_tokens = row.total_tokens or 0
    avg_latency = float(row.avg_latency or 0)
    error_count = row.error_count or 0

    return AnalyticsOverview(
        total_spend_usd=total_spend,
        total_requests=total_requests,
        total_tokens=total_tokens,
        avg_cost_per_request=total_spend / total_requests if total_requests > 0 else 0,
        period_start=start_date.isoformat(),
        period_end=datetime.utcnow().isoformat(),
        avg_latency_ms=round(avg_latency, 2),
        error_rate=round((error_count / total_requests) * 100, 2) if total_requests > 0 else 0,
    )


@router.get("/spend/by-model")
async def get_spend_by_model(
    user_id: CurrentUserId,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[SpendByModel]:
    """Get spend breakdown by model."""
    start_date = datetime.utcnow() - timedelta(days=days)

    # First get total spend for percentage calculation
    total_result = await db.execute(
        select(func.sum(ApiLog.cost_usd)).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= start_date,
            )
        )
    )
    total_spend = float(total_result.scalar() or 0)

    result = await db.execute(
        select(
            ApiLog.model,
            ApiLog.provider,
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
            func.sum(ApiLog.total_tokens).label("tokens"),
            func.avg(ApiLog.latency_ms).label("avg_latency"),
        )
        .where(
            and_(
                ApiLog.user_id == user_id,
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
            avg_latency_ms=round(float(row.avg_latency or 0), 2),
            percent_of_total=round((float(row.spend or 0) / total_spend) * 100, 2) if total_spend > 0 else 0,
        )
        for row in result.all()
    ]


@router.get("/spend/by-day")
async def get_spend_by_day(
    user_id: CurrentUserId,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[SpendByDay]:
    """Get daily spend trend."""
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(ApiLog.timestamp).label("date"),
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
            func.sum(ApiLog.total_tokens).label("tokens"),
            func.avg(ApiLog.latency_ms).label("avg_latency"),
        )
        .where(
            and_(
                ApiLog.user_id == user_id,
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
            tokens=row.tokens or 0,
            avg_latency_ms=round(float(row.avg_latency or 0), 2),
        )
        for row in result.all()
    ]


@router.get("/projections")
async def get_projections(
    user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get projected spend based on current usage trends."""
    # Get last 7 days of spend for trend analysis
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(
            func.date(ApiLog.timestamp).label("date"),
            func.sum(ApiLog.cost_usd).label("spend"),
        )
        .where(
            and_(
                ApiLog.user_id == user_id,
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


@router.get("/spend/by-provider", response_model=list[SpendByProvider])
async def get_spend_by_provider(
    user_id: CurrentUserId,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[SpendByProvider]:
    """Get spend breakdown by provider."""
    start_date = datetime.utcnow() - timedelta(days=days)

    # First get total spend for percentage calculation
    total_result = await db.execute(
        select(func.sum(ApiLog.cost_usd)).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= start_date,
            )
        )
    )
    total_spend = float(total_result.scalar() or 0)

    result = await db.execute(
        select(
            ApiLog.provider,
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
            func.sum(ApiLog.total_tokens).label("tokens"),
            func.count(func.distinct(ApiLog.model)).label("model_count"),
        )
        .where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= start_date,
            )
        )
        .group_by(ApiLog.provider)
        .order_by(func.sum(ApiLog.cost_usd).desc())
    )

    return [
        SpendByProvider(
            provider=row.provider,
            spend_usd=float(row.spend or 0),
            requests=row.requests,
            tokens=row.tokens or 0,
            model_count=row.model_count,
            percent_of_total=round((float(row.spend or 0) / total_spend) * 100, 2) if total_spend > 0 else 0,
        )
        for row in result.all()
    ]


@router.get("/spend/by-agent", response_model=list[SpendByAgent])
async def get_spend_by_agent(
    user_id: CurrentUserId,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[SpendByAgent]:
    """Get spend breakdown by agent."""
    start_date = datetime.utcnow() - timedelta(days=days)

    # First get total spend for percentage calculation
    total_result = await db.execute(
        select(func.sum(ApiLog.cost_usd)).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= start_date,
            )
        )
    )
    total_spend = float(total_result.scalar() or 0)

    result = await db.execute(
        select(
            ApiLog.agent_id,
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
            func.sum(ApiLog.total_tokens).label("tokens"),
            func.avg(ApiLog.latency_ms).label("avg_latency"),
        )
        .where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= start_date,
            )
        )
        .group_by(ApiLog.agent_id)
        .order_by(func.sum(ApiLog.cost_usd).desc())
    )

    return [
        SpendByAgent(
            agent_id=str(row.agent_id) if row.agent_id else None,
            agent_name=f"Agent {str(row.agent_id)[:8]}" if row.agent_id else "Unassigned",
            spend_usd=float(row.spend or 0),
            requests=row.requests,
            tokens=row.tokens or 0,
            avg_latency_ms=round(float(row.avg_latency or 0), 2),
            percent_of_total=round((float(row.spend or 0) / total_spend) * 100, 2) if total_spend > 0 else 0,
        )
        for row in result.all()
    ]


@router.get("/trends", response_model=TrendData)
async def get_trends(
    user_id: CurrentUserId,
    days: int = Query(default=14, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
) -> TrendData:
    """Get trend analysis comparing current vs previous period."""
    now = datetime.utcnow()
    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    # Current period spend
    current_result = await db.execute(
        select(func.sum(ApiLog.cost_usd)).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= current_start,
            )
        )
    )
    current_spend = float(current_result.scalar() or 0)

    # Previous period spend
    previous_result = await db.execute(
        select(func.sum(ApiLog.cost_usd)).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= previous_start,
                ApiLog.timestamp < current_start,
            )
        )
    )
    previous_spend = float(previous_result.scalar() or 0)

    # Calculate change
    if previous_spend > 0:
        change_percent = ((current_spend - previous_spend) / previous_spend) * 100
    elif current_spend > 0:
        change_percent = 100.0  # Went from zero to non-zero
    else:
        change_percent = 0.0

    # Determine trend direction
    if change_percent > 10:
        trend_direction = "up"
    elif change_percent < -10:
        trend_direction = "down"
    else:
        trend_direction = "stable"

    # Daily average
    daily_avg = current_spend / days if days > 0 else 0

    return TrendData(
        current_period_spend=round(current_spend, 4),
        previous_period_spend=round(previous_spend, 4),
        change_percent=round(change_percent, 2),
        trend_direction=trend_direction,
        daily_avg_spend=round(daily_avg, 4),
        projected_monthly_spend=round(daily_avg * 30, 2),
    )


@router.get("/summary", response_model=SummaryStats)
async def get_summary(
    user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
) -> SummaryStats:
    """Get summary statistics for the dashboard."""
    now = datetime.utcnow()

    # Today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # This week (last 7 days)
    week_start = now - timedelta(days=7)

    # This month
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Today's stats
    today_result = await db.execute(
        select(
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
        ).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= today_start,
            )
        )
    )
    today_row = today_result.one()

    # Week stats
    week_result = await db.execute(
        select(
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
        ).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= week_start,
            )
        )
    )
    week_row = week_result.one()

    # Month stats
    month_result = await db.execute(
        select(
            func.sum(ApiLog.cost_usd).label("spend"),
            func.count(ApiLog.id).label("requests"),
        ).where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= month_start,
            )
        )
    )
    month_row = month_result.one()

    # Most used model
    most_used_result = await db.execute(
        select(ApiLog.model)
        .where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= month_start,
            )
        )
        .group_by(ApiLog.model)
        .order_by(func.count(ApiLog.id).desc())
        .limit(1)
    )
    most_used_model = most_used_result.scalar()

    # Most expensive model
    most_expensive_result = await db.execute(
        select(ApiLog.model)
        .where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= month_start,
            )
        )
        .group_by(ApiLog.model)
        .order_by(func.sum(ApiLog.cost_usd).desc())
        .limit(1)
    )
    most_expensive_model = most_expensive_result.scalar()

    # Top provider
    top_provider_result = await db.execute(
        select(ApiLog.provider)
        .where(
            and_(
                ApiLog.user_id == user_id,
                ApiLog.timestamp >= month_start,
            )
        )
        .group_by(ApiLog.provider)
        .order_by(func.sum(ApiLog.cost_usd).desc())
        .limit(1)
    )
    top_provider = top_provider_result.scalar()

    # Average daily spend (based on month)
    days_in_month = (now - month_start).days + 1
    month_spend = float(month_row.spend or 0)
    avg_daily = month_spend / days_in_month if days_in_month > 0 else 0

    return SummaryStats(
        today_spend_usd=float(today_row.spend or 0),
        today_requests=today_row.requests or 0,
        week_spend_usd=float(week_row.spend or 0),
        week_requests=week_row.requests or 0,
        month_spend_usd=month_spend,
        month_requests=month_row.requests or 0,
        most_used_model=most_used_model,
        most_expensive_model=most_expensive_model,
        top_provider=top_provider,
        avg_daily_spend_usd=round(avg_daily, 4),
    )
