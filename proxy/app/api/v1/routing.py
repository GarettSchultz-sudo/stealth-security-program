"""Smart routing configuration API endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.smart_router import SmartRouter
from app.models.database import get_db
from app.models.routing_rule import RoutingRule

router = APIRouter()


class RoutingRuleCreate(BaseModel):
    """Routing rule creation request."""

    name: str
    description: Optional[str] = None
    priority: int = 100
    condition: dict
    target_provider: str
    target_model: str
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None


class RoutingRuleUpdate(BaseModel):
    """Routing rule update request."""

    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    condition: Optional[dict] = None
    target_provider: Optional[str] = None
    target_model: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    is_active: Optional[bool] = None


class RoutingRuleResponse(BaseModel):
    """Routing rule response model."""

    id: str
    name: str
    description: Optional[str]
    priority: int
    condition: dict
    target_provider: str
    target_model: str
    fallback_provider: Optional[str]
    fallback_model: Optional[str]
    is_active: bool
    times_applied: int
    estimated_savings_usd: float
    created_at: str


class RoutingSimulateRequest(BaseModel):
    """Request for simulating routing."""

    requested_model: str
    messages: list[dict]
    metadata: Optional[dict] = None


@router.post("/rules", response_model=RoutingRuleResponse)
async def create_rule(
    rule_data: RoutingRuleCreate,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> RoutingRuleResponse:
    """Create a new routing rule."""
    rule = RoutingRule(
        user_id=uuid.UUID(user_id),
        name=rule_data.name,
        description=rule_data.description,
        priority=rule_data.priority,
        condition=rule_data.condition,
        target_provider=rule_data.target_provider,
        target_model=rule_data.target_model,
        fallback_provider=rule_data.fallback_provider,
        fallback_model=rule_data.fallback_model,
    )

    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return RoutingRuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        priority=rule.priority,
        condition=rule.condition,
        target_provider=rule.target_provider,
        target_model=rule.target_model,
        fallback_provider=rule.fallback_provider,
        fallback_model=rule.fallback_model,
        is_active=rule.is_active,
        times_applied=rule.times_applied,
        estimated_savings_usd=rule.estimated_savings_usd,
        created_at=rule.created_at.isoformat(),
    )


@router.get("/rules", response_model=list[RoutingRuleResponse])
async def list_rules(
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> list[RoutingRuleResponse]:
    """List all routing rules in priority order."""
    result = await db.execute(
        select(RoutingRule)
        .where(RoutingRule.user_id == uuid.UUID(user_id))
        .order_by(RoutingRule.priority, RoutingRule.created_at)
    )
    rules = result.scalars().all()

    return [
        RoutingRuleResponse(
            id=str(r.id),
            name=r.name,
            description=r.description,
            priority=r.priority,
            condition=r.condition,
            target_provider=r.target_provider,
            target_model=r.target_model,
            fallback_provider=r.fallback_provider,
            fallback_model=r.fallback_model,
            is_active=r.is_active,
            times_applied=r.times_applied,
            estimated_savings_usd=r.estimated_savings_usd,
            created_at=r.created_at.isoformat(),
        )
        for r in rules
    ]


@router.put("/rules/{rule_id}", response_model=RoutingRuleResponse)
async def update_rule(
    rule_id: str,
    rule_data: RoutingRuleUpdate,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> RoutingRuleResponse:
    """Update a routing rule."""
    rule = await db.get(RoutingRule, uuid.UUID(rule_id))

    if not rule or rule.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = rule_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)

    return RoutingRuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        priority=rule.priority,
        condition=rule.condition,
        target_provider=rule.target_provider,
        target_model=rule.target_model,
        fallback_provider=rule.fallback_provider,
        fallback_model=rule.fallback_model,
        is_active=rule.is_active,
        times_applied=rule.times_applied,
        estimated_savings_usd=rule.estimated_savings_usd,
        created_at=rule.created_at.isoformat(),
    )


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a routing rule."""
    rule = await db.get(RoutingRule, uuid.UUID(rule_id))

    if not rule or rule.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()

    return {"status": "deleted", "id": rule_id}


@router.post("/simulate")
async def simulate_routing(
    simulate_data: RoutingSimulateRequest,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Simulate routing to see what would happen (dry-run)."""
    router = SmartRouter(db)

    return await router.simulate_routing(
        user_id=uuid.UUID(user_id),
        requested_model=simulate_data.requested_model,
        messages=simulate_data.messages,
        metadata=simulate_data.metadata,
    )
