"""
Comprehensive pricing data for all LLM providers.

Prices are in USD per million tokens.
Last updated: February 2026
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass
class ModelPricing:
    """Pricing information for a single model."""

    provider: str
    model: str
    input_per_mtok: Decimal  # Price per million input tokens
    output_per_mtok: Decimal  # Price per million output tokens
    cache_create_per_mtok: Decimal = Decimal("0")  # Prompt caching - creation
    cache_read_per_mtok: Decimal = Decimal("0")  # Prompt caching - read
    batch_discount_percent: int = 50  # Discount for batch processing
    effective_date: str = "2026-02-01"


# Comprehensive pricing table
PRICING_TABLE: dict[str, ModelPricing] = {
    # ============================================
    # ANTHROPIC - Claude 4.x Series (Current)
    # ============================================
    "claude-opus-4-5-20250929": ModelPricing(
        provider="anthropic",
        model="claude-opus-4-5-20250929",
        input_per_mtok=Decimal("15.00"),
        output_per_mtok=Decimal("75.00"),
        cache_create_per_mtok=Decimal("18.75"),
        cache_read_per_mtok=Decimal("1.50"),
    ),
    "claude-opus-4-5": ModelPricing(
        provider="anthropic",
        model="claude-opus-4-5",
        input_per_mtok=Decimal("15.00"),
        output_per_mtok=Decimal("75.00"),
        cache_create_per_mtok=Decimal("18.75"),
        cache_read_per_mtok=Decimal("1.50"),
    ),
    "claude-sonnet-4-5-20250929": ModelPricing(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        input_per_mtok=Decimal("3.00"),
        output_per_mtok=Decimal("15.00"),
        cache_create_per_mtok=Decimal("3.75"),
        cache_read_per_mtok=Decimal("0.30"),
    ),
    "claude-sonnet-4-5": ModelPricing(
        provider="anthropic",
        model="claude-sonnet-4-5",
        input_per_mtok=Decimal("3.00"),
        output_per_mtok=Decimal("15.00"),
        cache_create_per_mtok=Decimal("3.75"),
        cache_read_per_mtok=Decimal("0.30"),
    ),
    "claude-sonnet-4-20250514": ModelPricing(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_per_mtok=Decimal("3.00"),
        output_per_mtok=Decimal("15.00"),
        cache_create_per_mtok=Decimal("3.75"),
        cache_read_per_mtok=Decimal("0.30"),
    ),
    "claude-haiku-4-5-20251001": ModelPricing(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        input_per_mtok=Decimal("0.80"),
        output_per_mtok=Decimal("4.00"),
        cache_create_per_mtok=Decimal("1.00"),
        cache_read_per_mtok=Decimal("0.08"),
    ),
    "claude-haiku-4-5": ModelPricing(
        provider="anthropic",
        model="claude-haiku-4-5",
        input_per_mtok=Decimal("0.80"),
        output_per_mtok=Decimal("4.00"),
        cache_create_per_mtok=Decimal("1.00"),
        cache_read_per_mtok=Decimal("0.08"),
    ),
    # Claude 3.5 Series (Legacy)
    "claude-3-5-sonnet-20241022": ModelPricing(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        input_per_mtok=Decimal("3.00"),
        output_per_mtok=Decimal("15.00"),
        cache_create_per_mtok=Decimal("3.75"),
        cache_read_per_mtok=Decimal("0.30"),
    ),
    "claude-3-5-haiku-20241022": ModelPricing(
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        input_per_mtok=Decimal("0.80"),
        output_per_mtok=Decimal("4.00"),
        cache_create_per_mtok=Decimal("1.00"),
        cache_read_per_mtok=Decimal("0.08"),
    ),
    # ============================================
    # OPENAI - GPT Series
    # ============================================
    "gpt-4o": ModelPricing(
        provider="openai",
        model="gpt-4o",
        input_per_mtok=Decimal("2.50"),
        output_per_mtok=Decimal("10.00"),
    ),
    "gpt-4o-2024-11-20": ModelPricing(
        provider="openai",
        model="gpt-4o-2024-11-20",
        input_per_mtok=Decimal("2.50"),
        output_per_mtok=Decimal("10.00"),
    ),
    "gpt-4o-mini": ModelPricing(
        provider="openai",
        model="gpt-4o-mini",
        input_per_mtok=Decimal("0.15"),
        output_per_mtok=Decimal("0.60"),
    ),
    "gpt-4-turbo": ModelPricing(
        provider="openai",
        model="gpt-4-turbo",
        input_per_mtok=Decimal("10.00"),
        output_per_mtok=Decimal("30.00"),
    ),
    "gpt-4": ModelPricing(
        provider="openai",
        model="gpt-4",
        input_per_mtok=Decimal("30.00"),
        output_per_mtok=Decimal("60.00"),
    ),
    # OpenAI o-series (reasoning models)
    "o1": ModelPricing(
        provider="openai",
        model="o1",
        input_per_mtok=Decimal("15.00"),
        output_per_mtok=Decimal("60.00"),
    ),
    "o1-mini": ModelPricing(
        provider="openai",
        model="o1-mini",
        input_per_mtok=Decimal("1.50"),
        output_per_mtok=Decimal("6.00"),
    ),
    "o3-mini": ModelPricing(
        provider="openai",
        model="o3-mini",
        input_per_mtok=Decimal("1.10"),
        output_per_mtok=Decimal("4.40"),
    ),
    # ============================================
    # GOOGLE - Gemini Series
    # ============================================
    "gemini-2.5-pro-preview": ModelPricing(
        provider="google",
        model="gemini-2.5-pro-preview",
        input_per_mtok=Decimal("1.25"),
        output_per_mtok=Decimal("10.00"),
        cache_create_per_mtok=Decimal("2.50"),
        cache_read_per_mtok=Decimal("0.31"),
    ),
    "gemini-2.0-flash": ModelPricing(
        provider="google",
        model="gemini-2.0-flash",
        input_per_mtok=Decimal("0.10"),
        output_per_mtok=Decimal("0.40"),
    ),
    "gemini-1.5-pro": ModelPricing(
        provider="google",
        model="gemini-1.5-pro",
        input_per_mtok=Decimal("1.25"),
        output_per_mtok=Decimal("5.00"),
        cache_create_per_mtok=Decimal("2.50"),
        cache_read_per_mtok=Decimal("0.31"),
    ),
    "gemini-1.5-flash": ModelPricing(
        provider="google",
        model="gemini-1.5-flash",
        input_per_mtok=Decimal("0.075"),
        output_per_mtok=Decimal("0.30"),
    ),
    # ============================================
    # DEEPSEEK
    # ============================================
    "deepseek-chat": ModelPricing(
        provider="deepseek",
        model="deepseek-chat",
        input_per_mtok=Decimal("0.27"),
        output_per_mtok=Decimal("1.10"),
        cache_create_per_mtok=Decimal("0.135"),
        cache_read_per_mtok=Decimal("0.027"),
    ),
    "deepseek-reasoner": ModelPricing(
        provider="deepseek",
        model="deepseek-reasoner",
        input_per_mtok=Decimal("0.55"),
        output_per_mtok=Decimal("2.19"),
        cache_create_per_mtok=Decimal("0.14"),
        cache_read_per_mtok=Decimal("0.014"),
    ),
    # ============================================
    # GROQ (Fast inference)
    # ============================================
    "llama-3.3-70b-versatile": ModelPricing(
        provider="groq",
        model="llama-3.3-70b-versatile",
        input_per_mtok=Decimal("0.59"),
        output_per_mtok=Decimal("0.79"),
    ),
    "llama-3.1-8b-instant": ModelPricing(
        provider="groq",
        model="llama-3.1-8b-instant",
        input_per_mtok=Decimal("0.05"),
        output_per_mtok=Decimal("0.08"),
    ),
    "mixtral-8x7b-32768": ModelPricing(
        provider="groq",
        model="mixtral-8x7b-32768",
        input_per_mtok=Decimal("0.24"),
        output_per_mtok=Decimal("0.24"),
    ),
    # ============================================
    # MISTRAL
    # ============================================
    "mistral-large-2411": ModelPricing(
        provider="mistral",
        model="mistral-large-2411",
        input_per_mtok=Decimal("2.00"),
        output_per_mtok=Decimal("6.00"),
    ),
    "mistral-small-2402": ModelPricing(
        provider="mistral",
        model="mistral-small-2402",
        input_per_mtok=Decimal("0.20"),
        output_per_mtok=Decimal("0.60"),
    ),
    "codestral-2405": ModelPricing(
        provider="mistral",
        model="codestral-2405",
        input_per_mtok=Decimal("0.20"),
        output_per_mtok=Decimal("0.60"),
    ),
}


def get_pricing(model: str) -> ModelPricing | None:
    """
    Get pricing for a model.

    Args:
        model: Model identifier

    Returns:
        ModelPricing if found, None otherwise
    """
    # Direct lookup
    if model in PRICING_TABLE:
        return PRICING_TABLE[model]

    # Try partial match (for version variants)
    for key, pricing in PRICING_TABLE.items():
        if model.startswith(key) or key.startswith(model):
            return pricing

    return None


def get_all_models_by_provider(provider: str) -> list[str]:
    """Get all models for a given provider."""
    return [
        model for model, pricing in PRICING_TABLE.items()
        if pricing.provider == provider.lower()
    ]


# Provider API base URLs
PROVIDER_BASE_URLS: dict[str, str] = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com",
    "google": "https://generativelanguage.googleapis.com",
    "deepseek": "https://api.deepseek.com",
    "groq": "https://api.groq.com/openai",
    "mistral": "https://api.mistral.ai",
}
