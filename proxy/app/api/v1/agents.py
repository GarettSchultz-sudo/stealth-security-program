"""Agent management API endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentStatus, AgentType
from app.models.database import get_db

router = APIRouter()


class AgentCreate(BaseModel):
    """Agent creation request."""

    name: str
    agent_type: AgentType = AgentType.CUSTOM
    description: Optional[str] = None
    metadata: Optional[dict] = None


class AgentUpdate(BaseModel):
    """Agent update request."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AgentStatus] = None
    metadata: Optional[dict] = None


class AgentResponse(BaseModel):
    """Agent response model."""

    id: str
    name: str
    agent_type: str
    agent_identifier: str
    description: Optional[str]
    status: str
    last_seen: Optional[str]
    created_at: str


class AgentWithStats(AgentResponse):
    """Agent response with usage statistics."""

    total_requests: int
    total_spend_usd: float
    total_tokens: int


@router.post("", response_model=AgentResponse)
async def register_agent(
    agent_data: AgentCreate,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Register a new agent."""
    import secrets

    # Generate unique identifier
    agent_identifier = f"agent_{secrets.token_hex(8)}"

    agent = Agent(
        user_id=uuid.UUID(user_id),
        name=agent_data.name,
        agent_type=agent_data.agent_type,
        agent_identifier=agent_identifier,
        description=agent_data.description,
        metadata_=agent_data.metadata,
        last_seen=datetime.utcnow(),
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        agent_type=agent.agent_type.value,
        agent_identifier=agent.agent_identifier,
        description=agent.description,
        status=agent.status.value,
        last_seen=agent.last_seen.isoformat() if agent.last_seen else None,
        created_at=agent.created_at.isoformat(),
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> list[AgentResponse]:
    """List all agents for the current user."""
    result = await db.execute(
        select(Agent)
        .where(Agent.user_id == uuid.UUID(user_id))
        .order_by(Agent.last_seen.desc())
    )
    agents = result.scalars().all()

    return [
        AgentResponse(
            id=str(a.id),
            name=a.name,
            agent_type=a.agent_type.value,
            agent_identifier=a.agent_identifier,
            description=a.description,
            status=a.status.value,
            last_seen=a.last_seen.isoformat() if a.last_seen else None,
            created_at=a.created_at.isoformat(),
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentWithStats)
async def get_agent(
    agent_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> AgentWithStats:
    """Get agent details with usage statistics."""
    from sqlalchemy import func

    from app.models.api_log import ApiLog

    agent = await db.get(Agent, uuid.UUID(agent_id))

    if not agent or agent.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get stats
    result = await db.execute(
        select(
            func.count(ApiLog.id).label("total_requests"),
            func.sum(ApiLog.cost_usd).label("total_spend"),
            func.sum(ApiLog.total_tokens).label("total_tokens"),
        ).where(ApiLog.agent_id == agent.id)
    )

    stats = result.one()

    return AgentWithStats(
        id=str(agent.id),
        name=agent.name,
        agent_type=agent.agent_type.value,
        agent_identifier=agent.agent_identifier,
        description=agent.description,
        status=agent.status.value,
        last_seen=agent.last_seen.isoformat() if agent.last_seen else None,
        created_at=agent.created_at.isoformat(),
        total_requests=stats.total_requests or 0,
        total_spend_usd=float(stats.total_spend or 0),
        total_tokens=stats.total_tokens or 0,
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Update an agent."""
    agent = await db.get(Agent, uuid.UUID(agent_id))

    if not agent or agent.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "metadata":
            setattr(agent, "metadata_", value)
        else:
            setattr(agent, key, value)

    await db.commit()
    await db.refresh(agent)

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        agent_type=agent.agent_type.value,
        agent_identifier=agent.agent_identifier,
        description=agent.description,
        status=agent.status.value,
        last_seen=agent.last_seen.isoformat() if agent.last_seen else None,
        created_at=agent.created_at.isoformat(),
    )


@router.delete("/{agent_id}")
async def deregister_agent(
    agent_id: str,
    user_id: str = "00000000-0000-0000-0000-000000000001",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deregister an agent."""
    agent = await db.get(Agent, uuid.UUID(agent_id))

    if not agent or agent.user_id != uuid.UUID(user_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = AgentStatus.INACTIVE
    await db.commit()

    return {"status": "deregistered", "id": agent_id}
