"""
Smart routing engine for model selection.

Evaluates routing rules to determine the best model for a request.
Includes cost optimization and model fallback capabilities.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pricing_data import PRICING_TABLE, ModelPricing, get_pricing
from app.models.routing_rule import RoutingRule


# Fallback chains for models when primary is unavailable
# Ordered from best to worst alternative within same capability tier
FALLBACK_CHAINS: dict[str, list[str]] = {
    # Claude 4.x Opus tier
    "claude-opus-4-5": ["claude-sonnet-4-5", "claude-3-5-sonnet-20241022", "claude-haiku-4-5"],
    "claude-opus-4-5-20250929": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
    # Claude 4.x Sonnet tier
    "claude-sonnet-4-5": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-haiku-4-5"],
    "claude-sonnet-4-5-20250929": ["claude-sonnet-4-5", "claude-3-5-sonnet-20241022", "claude-haiku-4-5"],
    "claude-sonnet-4-20250514": ["claude-sonnet-4-5", "claude-3-5-sonnet-20241022", "claude-haiku-4-5"],
    # Claude 4.x Haiku tier
    "claude-haiku-4-5": ["claude-haiku-4-5-20251001", "claude-3-5-haiku-20241022"],
    "claude-haiku-4-5-20251001": ["claude-haiku-4-5", "claude-3-5-haiku-20241022"],
    # Claude 3.5 series
    "claude-3-5-sonnet-20241022": ["claude-sonnet-4-5", "claude-haiku-4-5", "claude-3-5-haiku-20241022"],
    "claude-3-5-haiku-20241022": ["claude-haiku-4-5", "gpt-4o-mini"],
    # GPT-4 series
    "gpt-4o": ["gpt-4o-2024-11-20", "gpt-4o-mini", "claude-sonnet-4-5"],
    "gpt-4o-2024-11-20": ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-5"],
    "gpt-4o-mini": ["claude-haiku-4-5", "gemini-2.0-flash"],
    "gpt-4-turbo": ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-5"],
    "gpt-4": ["gpt-4-turbo", "gpt-4o", "claude-opus-4-5"],
    # OpenAI o-series (reasoning models)
    "o1": ["claude-opus-4-5", "o1-mini"],
    "o1-mini": ["o3-mini", "deepseek-reasoner", "claude-sonnet-4-5"],
    "o3-mini": ["o1-mini", "deepseek-reasoner", "claude-sonnet-4-5"],
    # Gemini series
    "gemini-2.5-pro-preview": ["gemini-1.5-pro", "claude-sonnet-4-5", "gpt-4o"],
    "gemini-2.0-flash": ["gemini-1.5-flash", "gpt-4o-mini", "claude-haiku-4-5"],
    "gemini-1.5-pro": ["gemini-2.5-pro-preview", "claude-sonnet-4-5", "gpt-4o"],
    "gemini-1.5-flash": ["gemini-2.0-flash", "gpt-4o-mini", "claude-haiku-4-5"],
    # DeepSeek
    "deepseek-chat": ["claude-haiku-4-5", "gpt-4o-mini", "gemini-2.0-flash"],
    "deepseek-reasoner": ["o1-mini", "o3-mini", "claude-sonnet-4-5"],
    # Groq
    "llama-3.3-70b-versatile": ["llama-3.1-8b-instant", "claude-sonnet-4-5", "gpt-4o"],
    "llama-3.1-8b-instant": ["claude-haiku-4-5", "gpt-4o-mini", "gemini-2.0-flash"],
    "mixtral-8x7b-32768": ["llama-3.3-70b-versatile", "claude-sonnet-4-5", "gpt-4o"],
    # Mistral
    "mistral-large-2411": ["claude-sonnet-4-5", "gpt-4o", "mistral-small-2402"],
    "mistral-small-2402": ["claude-haiku-4-5", "gpt-4o-mini", "gemini-2.0-flash"],
    "codestral-2405": ["claude-sonnet-4-5", "gpt-4o", "mistral-small-2402"],
}


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

    def get_cheapest_model(
        self,
        capability_requirements: dict[str, Any] | None = None,
        provider_filter: list[str] | None = None,
        min_context_window: int | None = None,
    ) -> dict[str, Any]:
        """
        Find the cheapest model that meets specified capability requirements.

        Args:
            capability_requirements: Dict with optional keys:
                - "supports_vision": bool
                - "supports_streaming": bool
                - "supports_function_calling": bool
                - "min_output_tokens": int
            provider_filter: List of allowed providers (e.g., ["anthropic", "openai"])
            min_context_window: Minimum context window size required

        Returns:
            Dict with model info including pricing, or None if no match
        """
        capability_requirements = capability_requirements or {}

        # Capability metadata for models (simplified for MVP)
        MODEL_CAPABILITIES: dict[str, dict[str, Any]] = {
            # Anthropic models
            "claude-opus-4-5": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 16384},
            "claude-opus-4-5-20250929": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 16384},
            "claude-sonnet-4-5": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 16384},
            "claude-sonnet-4-5-20250929": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 16384},
            "claude-sonnet-4-20250514": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 16384},
            "claude-haiku-4-5": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 8192},
            "claude-haiku-4-5-20251001": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 8192},
            "claude-3-5-sonnet-20241022": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 8192},
            "claude-3-5-haiku-20241022": {"vision": True, "streaming": True, "function_calling": True, "context": 200000, "max_output": 8192},
            # OpenAI models
            "gpt-4o": {"vision": True, "streaming": True, "function_calling": True, "context": 128000, "max_output": 16384},
            "gpt-4o-2024-11-20": {"vision": True, "streaming": True, "function_calling": True, "context": 128000, "max_output": 16384},
            "gpt-4o-mini": {"vision": True, "streaming": True, "function_calling": True, "context": 128000, "max_output": 16384},
            "gpt-4-turbo": {"vision": True, "streaming": True, "function_calling": True, "context": 128000, "max_output": 4096},
            "gpt-4": {"vision": False, "streaming": True, "function_calling": True, "context": 8192, "max_output": 4096},
            "o1": {"vision": False, "streaming": False, "function_calling": False, "context": 200000, "max_output": 100000},
            "o1-mini": {"vision": False, "streaming": False, "function_calling": False, "context": 128000, "max_output": 65536},
            "o3-mini": {"vision": False, "streaming": True, "function_calling": True, "context": 200000, "max_output": 100000},
            # Google models
            "gemini-2.5-pro-preview": {"vision": True, "streaming": True, "function_calling": True, "context": 1000000, "max_output": 65536},
            "gemini-2.0-flash": {"vision": True, "streaming": True, "function_calling": True, "context": 1000000, "max_output": 8192},
            "gemini-1.5-pro": {"vision": True, "streaming": True, "function_calling": True, "context": 2000000, "max_output": 8192},
            "gemini-1.5-flash": {"vision": True, "streaming": True, "function_calling": True, "context": 1000000, "max_output": 8192},
            # DeepSeek
            "deepseek-chat": {"vision": False, "streaming": True, "function_calling": True, "context": 64000, "max_output": 8192},
            "deepseek-reasoner": {"vision": False, "streaming": True, "function_calling": False, "context": 64000, "max_output": 8192},
            # Groq
            "llama-3.3-70b-versatile": {"vision": False, "streaming": True, "function_calling": True, "context": 128000, "max_output": 8192},
            "llama-3.1-8b-instant": {"vision": False, "streaming": True, "function_calling": True, "context": 128000, "max_output": 8192},
            "mixtral-8x7b-32768": {"vision": False, "streaming": True, "function_calling": True, "context": 32768, "max_output": 4096},
            # Mistral
            "mistral-large-2411": {"vision": False, "streaming": True, "function_calling": True, "context": 128000, "max_output": 8192},
            "mistral-small-2402": {"vision": False, "streaming": True, "function_calling": True, "context": 32000, "max_output": 8192},
            "codestral-2405": {"vision": False, "streaming": True, "function_calling": True, "context": 256000, "max_output": 8192},
        }

        candidates: list[tuple[str, ModelPricing, Decimal]] = []

        for model_id, pricing in PRICING_TABLE.items():
            # Check provider filter
            if provider_filter and pricing.provider not in provider_filter:
                continue

            # Get capabilities
            caps = MODEL_CAPABILITIES.get(model_id, {})
            if not caps:
                continue  # Skip unknown models

            # Check capability requirements
            if capability_requirements.get("supports_vision") and not caps.get("vision", False):
                continue
            if capability_requirements.get("supports_streaming") and not caps.get("streaming", True):
                continue
            if capability_requirements.get("supports_function_calling") and not caps.get("function_calling", True):
                continue
            if min_context_window and caps.get("context", 0) < min_context_window:
                continue
            min_output = capability_requirements.get("min_output_tokens")
            if min_output and caps.get("max_output", 0) < min_output:
                continue

            # Calculate average cost per 1M tokens (50% input, 50% output assumption)
            avg_cost = (pricing.input_per_mtok + pricing.output_per_mtok) / Decimal("2")
            candidates.append((model_id, pricing, avg_cost))

        if not candidates:
            return {
                "model": None,
                "provider": None,
                "error": "No models match the specified requirements",
            }

        # Sort by average cost (cheapest first)
        candidates.sort(key=lambda x: x[2])

        # Return cheapest option
        best_model, best_pricing, best_avg_cost = candidates[0]
        return {
            "model": best_model,
            "provider": best_pricing.provider,
            "input_cost_per_mtok": float(best_pricing.input_per_mtok),
            "output_cost_per_mtok": float(best_pricing.output_per_mtok),
            "avg_cost_per_mtok": float(best_avg_cost),
            "cache_supported": best_pricing.cache_create_per_mtok > Decimal("0"),
        }

    def get_fallback_model(self, primary_model: str, unavailable_models: list[str] | None = None) -> dict[str, Any]:
        """
        Get the best fallback model when the primary model is unavailable.

        Args:
            primary_model: The model that is unavailable
            unavailable_models: List of models known to be unavailable

        Returns:
            Dict with fallback model info, or original if no fallback exists
        """
        unavailable_models = unavailable_models or []
        unavailable_set = set(unavailable_models)
        unavailable_set.add(primary_model)

        # Get fallback chain for this model
        fallback_chain = FALLBACK_CHAINS.get(primary_model, [])

        # Find first available fallback
        for fallback_model in fallback_chain:
            if fallback_model not in unavailable_set:
                pricing = get_pricing(fallback_model)
                if pricing:
                    return {
                        "model": fallback_model,
                        "provider": pricing.provider,
                        "input_cost_per_mtok": float(pricing.input_per_mtok),
                        "output_cost_per_mtok": float(pricing.output_per_mtok),
                        "is_fallback": True,
                        "original_model": primary_model,
                    }

        # No fallback available - check if we can use a generic fallback
        generic_fallbacks = [
            "claude-sonnet-4-5",
            "gpt-4o",
            "claude-haiku-4-5",
        ]

        for generic in generic_fallbacks:
            if generic not in unavailable_set:
                pricing = get_pricing(generic)
                if pricing:
                    return {
                        "model": generic,
                        "provider": pricing.provider,
                        "input_cost_per_mtok": float(pricing.input_per_mtok),
                        "output_cost_per_mtok": float(pricing.output_per_mtok),
                        "is_fallback": True,
                        "original_model": primary_model,
                        "fallback_type": "generic",
                    }

        # No fallback available at all
        return {
            "model": primary_model,
            "provider": None,
            "is_fallback": False,
            "error": "No fallback models available",
            "original_model": primary_model,
        }

    def get_fallback_chain(self, model: str) -> list[str]:
        """
        Get the full fallback chain for a model.

        Args:
            model: Model to get fallback chain for

        Returns:
            List of fallback models in order of preference
        """
        return FALLBACK_CHAINS.get(model, [])
