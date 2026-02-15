"""
Cost calculation utilities.

Uses Decimal for precision to avoid floating point errors with money.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.core.pricing_data import get_pricing


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> Decimal:
    """
    Calculate the cost of an API request.

    Args:
        provider: LLM provider name
        model: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Tokens used for cache creation (prompt caching)
        cache_read_tokens: Tokens read from cache (cheaper)

    Returns:
        Cost in USD as Decimal
    """
    pricing = get_pricing(model)

    if not pricing:
        # Unknown model - use a default estimate
        # This shouldn't happen in production with complete pricing data
        return _estimate_unknown_cost(input_tokens, output_tokens)

    # Calculate regular input cost (excluding cached tokens)
    regular_input_tokens = input_tokens - cache_creation_tokens - cache_read_tokens
    if regular_input_tokens < 0:
        regular_input_tokens = 0

    # Calculate costs for each token type
    input_cost = (Decimal(regular_input_tokens) / Decimal("1_000_000")) * pricing.input_per_mtok
    output_cost = (Decimal(output_tokens) / Decimal("1_000_000")) * pricing.output_per_mtok
    cache_creation_cost = (
        Decimal(cache_creation_tokens) / Decimal("1_000_000")
    ) * pricing.cache_create_per_mtok
    cache_read_cost = (
        Decimal(cache_read_tokens) / Decimal("1_000_000")
    ) * pricing.cache_read_per_mtok

    total_cost = input_cost + output_cost + cache_creation_cost + cache_read_cost

    # Round to 6 decimal places (micros)
    return total_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _estimate_unknown_cost(input_tokens: int, output_tokens: int) -> Decimal:
    """
    Estimate cost for an unknown model.

    Uses conservative mid-range pricing estimates.
    """
    # Estimate: $3/MTok input, $15/MTok output
    input_cost = (Decimal(input_tokens) / Decimal("1_000_000")) * Decimal("3.00")
    output_cost = (Decimal(output_tokens) / Decimal("1_000_000")) * Decimal("15.00")
    total = input_cost + output_cost
    return total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def calculate_savings(
    original_model: str,
    routed_model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    """
    Calculate savings from smart routing.

    Args:
        original_model: Originally requested model
        routed_model: Model that was actually used
        input_tokens: Input token count
        output_tokens: Output token count

    Returns:
        Amount saved in USD
    """
    original_cost = calculate_cost("", original_model, input_tokens, output_tokens)
    routed_cost = calculate_cost("", routed_model, input_tokens, output_tokens)

    savings = original_cost - routed_cost
    return max(Decimal("0"), savings)


def get_cost_breakdown(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> dict[str, Any]:
    """
    Get detailed cost breakdown for an API request.

    Returns dict with per-component costs.
    """
    pricing = get_pricing(model)

    if not pricing:
        return {
            "total": float(_estimate_unknown_cost(input_tokens, output_tokens)),
            "input": 0,
            "output": 0,
            "cache_creation": 0,
            "cache_read": 0,
            "pricing_source": "estimated",
        }

    regular_input = max(0, input_tokens - cache_creation_tokens - cache_read_tokens)

    return {
        "total": float(
            calculate_cost(
                provider,
                model,
                input_tokens,
                output_tokens,
                cache_creation_tokens,
                cache_read_tokens,
            )
        ),
        "input": float((Decimal(regular_input) / Decimal("1_000_000")) * pricing.input_per_mtok),
        "output": float((Decimal(output_tokens) / Decimal("1_000_000")) * pricing.output_per_mtok),
        "cache_creation": float(
            (Decimal(cache_creation_tokens) / Decimal("1_000_000")) * pricing.cache_create_per_mtok
        ),
        "cache_read": float(
            (Decimal(cache_read_tokens) / Decimal("1_000_000")) * pricing.cache_read_per_mtok
        ),
        "pricing_source": "known",
        "pricing_per_mtok": {
            "input": float(pricing.input_per_mtok),
            "output": float(pricing.output_per_mtok),
            "cache_create": float(pricing.cache_create_per_mtok),
            "cache_read": float(pricing.cache_read_per_mtok),
        },
    }


def estimate_request_cost(
    provider: str,
    model: str,
    estimated_input_tokens: int,
    estimated_output_tokens: int = 500,
) -> Decimal:
    """
    Estimate the cost of a request before making it.

    Used for budget pre-checking.
    """
    return calculate_cost(
        provider,
        model,
        estimated_input_tokens,
        estimated_output_tokens,
    )
