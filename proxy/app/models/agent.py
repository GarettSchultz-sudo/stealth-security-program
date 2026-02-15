"""Agent model for tracking AI agents."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AgentType(str, enum.Enum):
    """Types of AI agents."""

    OPENCLAW = "openclaw"
    LANGCHAIN = "langchain"
    CREWAI = "crewai"
    AUTOGPT = "autogpt"
    CUSTOM = "custom"


class AgentStatus(str, enum.Enum):
    """Agent operational status."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class TaskStatus(str, enum.Enum):
    """Status of agent tasks."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Agent(BaseModel):
    """Registered AI agent for tracking."""

    __tablename__ = "agents"

    # If using Supabase Auth, user_id is optional (agent may use api_key_id)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Configuration
    default_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    budget_limit: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string of tags

    # Status
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.ACTIVE, nullable=False
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metrics (aggregated)
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=Decimal("0"))
    total_tasks_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tasks_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    user: Mapped["User | None"] = relationship(back_populates="agents")
    tasks: Mapped[list["AgentTask"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    heartbeats: Mapped[list["AgentHeartbeat"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentTask(BaseModel):
    """Task tracking for agents."""

    __tablename__ = "agent_tasks"
    __table_args__ = (
        UniqueConstraint("agent_id", "task_id", name="uq_agent_task"),
        Index("ix_agent_tasks_active", "agent_id", "status", postgresql_where="status IN ('pending', 'running')"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Task identification
    task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Task hierarchy
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )

    # Status tracking
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False
    )
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Model usage
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Metrics
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0"))
    api_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Results
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="tasks")
    events: Mapped[list["TaskEvent"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    child_tasks: Mapped[list["AgentTask"]] = relationship(
        backref="parent_task", remote_side="AgentTask.id"
    )


class AgentHeartbeat(BaseModel):
    """Heartbeat records for agent health monitoring."""

    __tablename__ = "agent_heartbeats"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Current state
    current_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")

    # System info
    cpu_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    memory_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamp
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Additional data
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="heartbeats")


class TaskEvent(BaseModel):
    """Audit trail for task lifecycle events."""

    __tablename__ = "task_events"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Associated API call (if applicable)
    api_log_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    task: Mapped["AgentTask"] = relationship(back_populates="events")
