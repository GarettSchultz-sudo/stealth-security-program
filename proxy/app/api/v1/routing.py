"""Smart routing configuration API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.smart_router import FALLBACK_CHAINS, SmartRouter
from app.models.database import get_db
from app.models.routing_rule import RoutingRule

router = APIRouter()


class RoutingRuleCreate(BaseModel):
    """Routing rule creation request."""

    name: str
    description: str | None = None
    priority: int = 100
    condition: dict
    target_provider: str
    target_model: str
    fallback_provider: str | None = None
    fallback_model: str | None = None


class RoutingRuleUpdate(BaseModel):
    """Routing rule update request."""

    name: str | None = None
    description: str | None = None
    priority: int | None = None
    condition: dict | None = None
    target_provider: str | None = None
    target_model: str | None = None
    fallback_provider: str | None = None
    fallback_model: str | None = None
    is_active: bool | None = None


class RoutingRuleResponse(BaseModel):
    """Routing rule response model."""

    id: str
    name: str
    description: str | None
    priority: int
    condition: dict
    target_provider: str
    target_model: str
    fallback_provider: str | None
    fallback_model: str | None
    is_active: bool
    times_applied: int
    estimated_savings_usd: float
    created_at: str


class RoutingSimulateRequest(BaseModel):
    """Request for simulating routing."""

    requested_model: str
    messages: list[dict]
    metadata: dict | None = None


class CheapestModelRequest(BaseModel):
    """Request for finding cheapest model."""

    capability_requirements: dict | None = None
    provider_filter: list[str] | None = None
    min_context_window: int | None = None


class FallbackModelRequest(BaseModel):
    """Request for getting fallback model."""

    primary_model: str
    unavailable_models: list[str] | None = None


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


@router.post("/cheapest")
async def get_cheapest_model(
    request: CheapestModelRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Find the cheapest model that meets capability requirements.

    This is a cost optimization endpoint that returns the most cost-effective
    model matching your specified requirements.

    Example request body:
    {
        "capability_requirements": {
            "supports_vision": true,
            "supports_function_calling": true
        },
        "provider_filter": ["anthropic", "openai"],
        "min_context_window": 100000
    }
    """
    router = SmartRouter(db)

    return router.get_cheapest_model(
        capability_requirements=request.capability_requirements,
        provider_filter=request.provider_filter,
        min_context_window=request.min_context_window,
    )


@router.post("/fallback")
async def get_fallback_model(
    request: FallbackModelRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the best fallback model when primary is unavailable.

    Returns the next best model from the fallback chain that can handle
    similar workloads to the primary model.

    Example request body:
    {
        "primary_model": "claude-opus-4-5",
        "unavailable_models": ["claude-sonnet-4-5"]
    }
    """
    router = SmartRouter(db)

    return router.get_fallback_model(
        primary_model=request.primary_model,
        unavailable_models=request.unavailable_models,
    )


@router.get("/fallback-chains")
async def get_fallback_chains() -> dict:
    """
    Get all fallback chain configurations.

    Returns the complete mapping of models to their fallback chains.
    Useful for debugging and understanding fallback behavior.
    """
    return {
        "fallback_chains": FALLBACK_CHAINS,
        "total_models_with_fallbacks": len(FALLBACK_CHAINS),
    }


@router.get("/fallback-chain/{model}")
async def get_model_fallback_chain(model: str) -> dict:
    """
    Get the fallback chain for a specific model.

    Args:
        model: Model identifier (URL encoded if needed)

    Returns:
        Dict with the fallback chain for the requested model
    """
    chain = FALLBACK_CHAINS.get(model, [])

    if not chain:
        return {
            "model": model,
            "fallback_chain": [],
            "has_fallback": False,
            "message": f"No fallback chain configured for model: {model}",
        }

    return {
        "model": model,
        "fallback_chain": chain,
        "has_fallback": True,
        "fallback_count": len(chain),
    }


@router.get("/rules/{rule_id}", response_model=RoutingRuleResponse)
async def get_rule(
    rule_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> RoutingRuleResponse:
    """Get a single routing rule by ID."""
    rule = await db.get(RoutingRule, uuid.UUID(rule_id))

    if not rule or rule.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Rule not found")

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
