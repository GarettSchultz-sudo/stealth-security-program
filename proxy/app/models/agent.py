"""Agent model for tracking AI agents."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
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
    INACTIVE = "inactive"
    ERROR = "error"


class Agent(BaseModel):
    """Registered AI agent for tracking."""

    __tablename__ = "agents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(
        Enum(AgentType), default=AgentType.CUSTOM, nullable=False
    )
    agent_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.ACTIVE, nullable=False
    )
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="agents")
