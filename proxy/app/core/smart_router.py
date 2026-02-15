"""
Smart routing engine for model selection.

Evaluates routing rules to determine the best model for a request.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pricing_data import get_pricing
from app.models.routing_rule import RoutingRule


@dataclass
class RoutingDecision:
    """Result of a routing evaluation."""

    target_provider: str
    target_model: str
    reason: str
    original_model: str | None = None
    estimated_savings_usd: Decimal = Decimal("0")
    rule_id: uuid.UUID | None = None


class SmartRouter:
    """Engine for intelligent model routing."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def route_request(
        self,
        user_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        requested_model: str,
        messages: list[dict],
        metadata: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        """
        Determine which model to use for a request.

        Evaluates routing rules in priority order and returns the first match.
        If no rules match, returns the originally requested model.

        Args:
            user_id: User ID
            agent_id: Agent ID (if applicable)
            requested_model: Model that was originally requested
            messages: Chat messages for the request
            metadata: Additional request metadata

        Returns:
            RoutingDecision with target model and reason
        """
        # Get active routing rules for this user
        rules = await self._get_active_rules(user_id)

        # Estimate request complexity
        estimated_tokens = self._estimate_total_tokens(messages, metadata)
        task_type = self._classify_task_type(messages, metadata)
        time_of_day = datetime.utcnow().strftime("%H:%M")

        # Evaluate each rule in priority order
        for rule in rules:
            if self._rule_matches(
                rule=rule,
                agent_id=agent_id,
                requested_model=requested_model,
                estimated_tokens=estimated_tokens,
                task_type=task_type,
                time_of_day=time_of_day,
                metadata=metadata,
            ):
                # Calculate potential savings
                savings = self._estimate_savings(
                    original_model=requested_model,
                    target_model=rule.target_model,
                    estimated_tokens=estimated_tokens,
                )

                # Update rule analytics
                rule.times_applied += 1
                rule.estimated_savings_usd += float(savings)
                await self.db.commit()

                return RoutingDecision(
                    target_provider=rule.target_provider,
                    target_model=rule.target_model,
                    reason=f"Matched rule: {rule.name}",
                    original_model=requested_model,
                    estimated_savings_usd=savings,
                    rule_id=rule.id,
                )

        # No rules matched, use requested model
        pricing = get_pricing(requested_model)
        provider = pricing.provider if pricing else "unknown"

        return RoutingDecision(
            target_provider=provider,
            target_model=requested_model,
            reason="No routing rules matched",
        )

    async def simulate_routing(
        self,
        user_id: uuid.UUID,
        requested_model: str,
        messages: list[dict],
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """
        Simulate routing to show estimated savings (dry-run).

        Returns detailed information about what would happen.
        """
        decision = await self.route_request(
            user_id=user_id,
            agent_id=None,
            requested_model=requested_model,
            messages=messages,
            metadata=metadata,
        )

        return {
            "original_model": decision.original_model or requested_model,
            "routed_model": decision.target_model,
            "provider": decision.target_provider,
            "reason": decision.reason,
            "estimated_savings_usd": float(decision.estimated_savings_usd),
            "rule_id": str(decision.rule_id) if decision.rule_id else None,
            "would_route": decision.target_model != requested_model,
        }

    async def _get_active_rules(self, user_id: uuid.UUID) -> list[RoutingRule]:
        """Get active routing rules sorted by priority."""
        result = await self.db.execute(
            select(RoutingRule)
            .where(
                and_(
                    RoutingRule.user_id == user_id,
                    RoutingRule.is_active == True,  # noqa: E712
                )
            )
            .order_by(RoutingRule.priority)
        )
        return list(result.scalars().all())

    def _rule_matches(
        self,
        rule: RoutingRule,
        agent_id: uuid.UUID | None,
        requested_model: str,
        estimated_tokens: int,
        task_type: str,
        time_of_day: str,
        metadata: dict | None,
    ) -> bool:
        """Check if a routing rule matches the request."""
        condition = rule.condition

        if not condition:
            return False

        # Check each condition
        if "agent_id" in condition and str(agent_id) != condition["agent_id"]:
            return False

        if "model_requested" in condition:
            if not requested_model.startswith(condition["model_requested"]):
                return False

        if "token_estimate_max" in condition:
            if estimated_tokens > condition["token_estimate_max"]:
                return False

        if "token_estimate_min" in condition:
            if estimated_tokens < condition["token_estimate_min"]:
                return False

        if "task_type" in condition and task_type != condition["task_type"]:
            return False

        if "time_of_day_start" in condition and "time_of_day_end" in condition:
            start = condition["time_of_day_start"]
            end = condition["time_of_day_end"]
            if not (start <= time_of_day <= end):
                return False

        return True

    def _estimate_total_tokens(
        self,
        messages: list[dict],
        metadata: dict | None,
    ) -> int:
        """Estimate total tokens for a request."""
        total = 0

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4  # Rough estimate
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        total += len(block["text"]) // 4

        if metadata and "system" in metadata:
            system = metadata["system"]
            if isinstance(system, str):
                total += len(system) // 4

        return total

    def _classify_task_type(
        self,
        messages: list[dict],
        metadata: dict | None,
    ) -> str:
        """Classify the type of task based on messages."""
        # Simple heuristic classification
        system = ""
        if metadata and "system" in metadata:
            system = str(metadata["system"]).lower()

        # Check for specific task patterns
        if "code" in system or "programming" in system:
            return "code"
        elif "analyze" in system or "analysis" in system:
            return "analysis"
        elif "summarize" in system or "summary" in system:
            return "summarization"
        elif "translate" in system:
            return "translation"
        elif len(messages) <= 2:
            return "simple"
        else:
            return "general"

    def _estimate_savings(
        self,
        original_model: str,
        target_model: str,
        estimated_tokens: int,
    ) -> Decimal:
        """Estimate cost savings from routing."""
        if original_model == target_model:
            return Decimal("0")

        original_pricing = get_pricing(original_model)
        target_pricing = get_pricing(target_model)

        if not original_pricing or not target_pricing:
            return Decimal("0")

        # Estimate cost difference (assuming 50/50 input/output split)
        input_tokens = estimated_tokens // 2
        output_tokens = estimated_tokens // 2

        original_cost = (
            Decimal(input_tokens) / Decimal("1_000_000")
        ) * original_pricing.input_per_mtok + (
            Decimal(output_tokens) / Decimal("1_000_000")
        ) * original_pricing.output_per_mtok

        target_cost = (
            Decimal(input_tokens) / Decimal("1_000_000")
        ) * target_pricing.input_per_mtok + (
            Decimal(output_tokens) / Decimal("1_000_000")
        ) * target_pricing.output_per_mtok

        return max(Decimal("0"), original_cost - target_cost)
