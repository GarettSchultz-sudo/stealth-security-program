"""
Cost Calculation with Pricing Lookup
Auto-generated from model catalog version 2026-02-13
Total models: 91 across 16 providers
"""
from decimal import Decimal
from _lib.db import get_supabase

# Comprehensive fallback pricing if DB query fails
# Format: (provider, model): (input_price_per_mtok, output_price_per_mtok)
FALLBACK_PRICING = {
    # ============================================================================
    # ANTHROPIC - Claude Models (10 models)
    # ============================================================================
    ("anthropic", "claude-opus-4-6-20250514"): (Decimal("15.00"), Decimal("75.00")),
    ("anthropic", "claude-opus-4-20250514"): (Decimal("15.00"), Decimal("75.00")),
    ("anthropic", "claude-sonnet-4-5-20250915"): (Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-sonnet-4-20250514"): (Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-haiku-4-5-20250915"): (Decimal("0.80"), Decimal("4.00")),
    ("anthropic", "claude-3-5-sonnet-20241022"): (Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-3-5-haiku-20241022"): (Decimal("0.80"), Decimal("4.00")),
    ("anthropic", "claude-3-opus-20240229"): (Decimal("15.00"), Decimal("75.00")),
    ("anthropic", "claude-3-sonnet-20240229"): (Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-3-haiku-20240307"): (Decimal("0.25"), Decimal("1.25")),

    # ============================================================================
    # OPENAI - GPT & o-series (11 models)
    # ============================================================================
    ("openai", "gpt-5.2-pro-20260115"): (Decimal("30.00"), Decimal("120.00")),
    ("openai", "gpt-5-pro-20251001"): (Decimal("20.00"), Decimal("80.00")),
    ("openai", "gpt-5.1-20250915"): (Decimal("10.00"), Decimal("40.00")),
    ("openai", "gpt-4o-2024-11-20"): (Decimal("2.50"), Decimal("10.00")),
    ("openai", "gpt-4o-mini-2024-07-18"): (Decimal("0.15"), Decimal("0.60")),
    ("openai", "gpt-4o"): (Decimal("2.50"), Decimal("10.00")),
    ("openai", "gpt-4o-mini"): (Decimal("0.15"), Decimal("0.60")),
    ("openai", "o3-pro-20260201"): (Decimal("50.00"), Decimal("200.00")),
    ("openai", "o3-20260115"): (Decimal("20.00"), Decimal("80.00")),
    ("openai", "o3-mini-20251215"): (Decimal("5.00"), Decimal("20.00")),
    ("openai", "o1-2024-12-17"): (Decimal("15.00"), Decimal("60.00")),
    ("openai", "o1"): (Decimal("15.00"), Decimal("60.00")),
    ("openai", "o1-mini-2024-09-12"): (Decimal("3.00"), Decimal("12.00")),
    ("openai", "o1-mini"): (Decimal("3.00"), Decimal("12.00")),
    ("openai", "gpt-4-turbo"): (Decimal("10.00"), Decimal("30.00")),
    ("openai", "gpt-4"): (Decimal("30.00"), Decimal("60.00")),
    ("openai", "gpt-3.5-turbo"): (Decimal("0.50"), Decimal("1.50")),

    # ============================================================================
    # GOOGLE - Gemini Models (6 models)
    # ============================================================================
    ("google", "gemini-3-pro-preview-20260201"): (Decimal("7.00"), Decimal("21.00")),
    ("google", "gemini-2.5-pro-preview-20260115"): (Decimal("5.00"), Decimal("15.00")),
    ("google", "gemini-2.5-flash-preview-20260115"): (Decimal("0.30"), Decimal("1.20")),
    ("google", "gemini-2.0-flash-001"): (Decimal("0.10"), Decimal("0.40")),
    ("google", "gemini-2-flash-lite-preview-20250915"): (Decimal("0.075"), Decimal("0.30")),
    ("google", "gemini-1.5-pro"): (Decimal("1.25"), Decimal("5.00")),
    ("google", "gemini-1.5-flash"): (Decimal("0.075"), Decimal("0.30")),
    ("google", "gemini-1.0-pro"): (Decimal("0.50"), Decimal("1.50")),

    # ============================================================================
    # DEEPSEEK - DeepSeek Models (7 models)
    # ============================================================================
    ("deepseek", "deepseek-v3.2-20260201"): (Decimal("0.27"), Decimal("1.10")),
    ("deepseek", "deepseek-v3.1-20260115"): (Decimal("0.27"), Decimal("1.10")),
    ("deepseek", "deepseek-r1-20250120"): (Decimal("0.55"), Decimal("2.19")),
    ("deepseek", "deepseek-reasoner"): (Decimal("0.55"), Decimal("2.19")),
    ("deepseek", "deepseek-chat"): (Decimal("0.14"), Decimal("0.28")),
    ("deepseek", "deepseek-coder-v2-240614"): (Decimal("0.14"), Decimal("0.28")),
    ("deepseek", "deepseek-coder"): (Decimal("0.14"), Decimal("0.28")),

    # ============================================================================
    # XAI - Grok Models (7 models)
    # ============================================================================
    ("xai", "grok-4-20260115"): (Decimal("10.00"), Decimal("30.00")),
    ("xai", "grok-4.1-20260201"): (Decimal("12.00"), Decimal("36.00")),
    ("xai", "grok-4.1-fast-20260201"): (Decimal("5.00"), Decimal("15.00")),
    ("xai", "grok-3-20251001"): (Decimal("5.00"), Decimal("15.00")),
    ("xai", "grok-3-mini-20251115"): (Decimal("0.30"), Decimal("0.90")),
    ("xai", "grok-2-1212"): (Decimal("2.00"), Decimal("10.00")),
    ("xai", "grok-2-image-20250815"): (Decimal("8.00"), Decimal("24.00")),
    ("xai", "grok-2-vision-1212"): (Decimal("2.00"), Decimal("10.00")),
    ("xai", "grok-2-mini-1212"): (Decimal("0.20"), Decimal("1.00")),
    ("xai", "grok-beta"): (Decimal("5.00"), Decimal("15.00")),

    # ============================================================================
    # MISTRAL - Mistral AI Models (8 models)
    # ============================================================================
    ("mistral", "mistral-large-3-20260115"): (Decimal("6.00"), Decimal("18.00")),
    ("mistral", "mistral-large-2-2407"): (Decimal("3.00"), Decimal("9.00")),
    ("mistral", "mistral-large-2411"): (Decimal("3.00"), Decimal("9.00")),
    ("mistral", "mistral-medium-2505"): (Decimal("1.50"), Decimal("4.50")),
    ("mistral", "mistral-small-2501"): (Decimal("0.30"), Decimal("0.90")),
    ("mistral", "codestral-2501"): (Decimal("0.30"), Decimal("0.90")),
    ("mistral", "ministral-8b-2410"): (Decimal("0.10"), Decimal("0.10")),
    ("mistral", "ministral-3b-2410"): (Decimal("0.04"), Decimal("0.04")),
    ("mistral", "open-mixtral-8x7b"): (Decimal("0.025"), Decimal("0.025")),
    ("mistral", "open-mistral-nemo"): (Decimal("0.025"), Decimal("0.025")),

    # ============================================================================
    # COHERE - Command Models (4 models)
    # ============================================================================
    ("cohere", "command-a-20260115"): (Decimal("2.50"), Decimal("10.00")),
    ("cohere", "command-a-03-2025"): (Decimal("2.50"), Decimal("10.00")),
    ("cohere", "command-r-plus-08-2024"): (Decimal("2.50"), Decimal("10.00")),
    ("cohere", "command-r-08-2024"): (Decimal("0.15"), Decimal("0.60")),
    ("cohere", "command-vision-20250115"): (Decimal("3.00"), Decimal("12.00")),
    ("cohere", "command-r7b-12-2024"): (Decimal("0.0375"), Decimal("0.15")),

    # ============================================================================
    # PERPLEXITY - Sonar Models (3 models)
    # ============================================================================
    ("perplexity", "sonar-20260115"): (Decimal("1.00"), Decimal("1.00")),
    ("perplexity", "sonar"): (Decimal("1.00"), Decimal("1.00")),
    ("perplexity", "sonar-pro-20260115"): (Decimal("3.00"), Decimal("15.00")),
    ("perplexity", "sonar-pro"): (Decimal("3.00"), Decimal("15.00")),
    ("perplexity", "sonar-deep-research-20260201"): (Decimal("5.00"), Decimal("25.00")),
    ("perplexity", "sonar-reasoning"): (Decimal("1.00"), Decimal("5.00")),
    ("perplexity", "sonar-reasoning-pro"): (Decimal("2.00"), Decimal("8.00")),
    ("perplexity", "r1-1776"): (Decimal("2.00"), Decimal("8.00")),

    # ============================================================================
    # GROQ - Fast Inference (4 models)
    # ============================================================================
    ("groq", "llama-3.3-70b-versatile"): (Decimal("0.59"), Decimal("0.79")),
    ("groq", "llama-3.1-8b-instant"): (Decimal("0.05"), Decimal("0.08")),
    ("groq", "mixtral-8x7b-32768"): (Decimal("0.24"), Decimal("0.24")),
    ("groq", "deepseek-r1-distill-llama-70b"): (Decimal("0.59"), Decimal("0.79")),
    ("groq", "llama-3.2-3b-preview"): (Decimal("0.06"), Decimal("0.06")),
    ("groq", "gemma2-9b-it"): (Decimal("0.20"), Decimal("0.20")),
    ("groq", "qwen-2.5-32b"): (Decimal("0.20"), Decimal("0.20")),

    # ============================================================================
    # META - Llama Models (6 models)
    # ============================================================================
    ("meta", "llama-4-maverick-20260201"): (Decimal("0.20"), Decimal("0.60")),
    ("meta", "llama-4-scout-20260201"): (Decimal("0.10"), Decimal("0.30")),
    ("meta", "llama-4-behemoth-20260201"): (Decimal("0.50"), Decimal("1.50")),
    ("meta", "llama-4-scout-17b-16e-instruct"): (Decimal("0.10"), Decimal("0.30")),
    ("meta", "llama-4-maverick-17b-128e-instruct"): (Decimal("0.20"), Decimal("0.60")),
    ("meta", "llama-3.3-70b-instruct"): (Decimal("0.60"), Decimal("0.60")),
    ("meta", "llama-3.1-405b-instruct"): (Decimal("3.00"), Decimal("3.00")),

    # ============================================================================
    # AMAZON BEDROCK (5 models)
    # ============================================================================
    ("bedrock", "anthropic.claude-opus-4-6-v1"): (Decimal("15.00"), Decimal("75.00")),
    ("bedrock", "anthropic.claude-sonnet-4-5-v1"): (Decimal("3.00"), Decimal("15.00")),
    ("bedrock", "anthropic.claude-3-5-sonnet-20241022-v2:0"): (Decimal("3.00"), Decimal("15.00")),
    ("bedrock", "anthropic.claude-3-haiku-20240307-v1:0"): (Decimal("0.25"), Decimal("1.25")),
    ("bedrock", "us.meta.llama4-maverick-v1"): (Decimal("0.22"), Decimal("0.66")),
    ("bedrock", "amazon.nova-2-pro-v1"): (Decimal("0.80"), Decimal("3.20")),
    ("bedrock", "deepseek.r1-v1"): (Decimal("0.60"), Decimal("2.40")),

    # ============================================================================
    # AZURE OPENAI (4 models)
    # ============================================================================
    ("azure", "gpt-5.2-pro"): (Decimal("30.00"), Decimal("120.00")),
    ("azure", "gpt-5-pro"): (Decimal("20.00"), Decimal("80.00")),
    ("azure", "gpt-4o"): (Decimal("2.50"), Decimal("10.00")),
    ("azure", "o3-pro"): (Decimal("50.00"), Decimal("200.00")),
    ("azure", "o3"): (Decimal("20.00"), Decimal("80.00")),
    ("azure", "o1"): (Decimal("15.00"), Decimal("60.00")),

    # ============================================================================
    # TOGETHER AI (5 models)
    # ============================================================================
    ("together", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"): (Decimal("0.20"), Decimal("0.60")),
    ("together", "meta-llama/Llama-4-Scout-17B-16E-Instruct"): (Decimal("0.10"), Decimal("0.30")),
    ("together", "deepseek-ai/DeepSeek-R1"): (Decimal("0.55"), Decimal("2.19")),
    ("together", "Qwen/Qwen3-235B-A22B-Instruct"): (Decimal("0.90"), Decimal("0.90")),
    ("together", "mistralai/Mistral-Large-3"): (Decimal("6.00"), Decimal("18.00")),
    ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"): (Decimal("0.88"), Decimal("0.88")),
    ("together", "Qwen/Qwen2.5-72B-Instruct-Turbo"): (Decimal("0.90"), Decimal("0.90")),

    # ============================================================================
    # FIREWORKS AI (3 models)
    # ============================================================================
    ("fireworks", "llama4-maverick-fireworks"): (Decimal("0.18"), Decimal("0.54")),
    ("fireworks", "deepseek-r1-fireworks"): (Decimal("0.50"), Decimal("2.00")),
    ("fireworks", "qwen3-235b-fireworks"): (Decimal("0.80"), Decimal("0.80")),
    ("fireworks", "accounts/fireworks/models/llama-v3p3-70b-instruct"): (Decimal("0.90"), Decimal("0.90")),
    ("fireworks", "accounts/fireworks/models/deepseek-r1"): (Decimal("3.00"), Decimal("8.00")),

    # ============================================================================
    # AI21 - Jamba Models (2 models)
    # ============================================================================
    ("ai21", "jamba-1-7-large"): (Decimal("2.00"), Decimal("8.00")),
    ("ai21", "jamba-1-5-mini"): (Decimal("0.20"), Decimal("0.40")),

    # ============================================================================
    # ALIBABA QWEN (6 models)
    # ============================================================================
    ("qwen", "qwen-max-20260115"): (Decimal("4.00"), Decimal("12.00")),
    ("qwen", "qwen-plus-20260115"): (Decimal("0.80"), Decimal("2.00")),
    ("qwen", "qwen-turbo-20260115"): (Decimal("0.30"), Decimal("0.60")),
    ("qwen", "qwen3-235b-a22b-instruct"): (Decimal("0.90"), Decimal("0.90")),
    ("qwen", "qwen2.5-72b-instruct"): (Decimal("0.35"), Decimal("0.35")),
    ("qwen", "qwen2.5-coder-32b-instruct"): (Decimal("0.18"), Decimal("0.18")),

    # ============================================================================
    # VERTEX AI (GCP)
    # ============================================================================
    ("vertex", "gemini-2.0-flash-001"): (Decimal("0.10"), Decimal("0.40")),
    ("vertex", "claude-3-5-sonnet@20241022"): (Decimal("3.00"), Decimal("15.00")),
    ("vertex", "gemini-1.5-pro-002"): (Decimal("1.25"), Decimal("5.00")),
    ("vertex", "claude-3-opus@20240229"): (Decimal("15.00"), Decimal("75.00")),
    ("vertex", "claude-3-haiku@20240307"): (Decimal("0.25"), Decimal("1.25")),
}

def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0
) -> Decimal:
    """
    Calculate cost in USD with caching discounts
    Prices are per 1M tokens
    """
    try:
        supabase = get_supabase()
        result = supabase.table("pricing")\
            .select("*")\
            .eq("provider", provider)\
            .eq("model", model)\
            .lte("effective_from", "now()")\
            .is_("effective_to", "null")\
            .order("effective_from", desc=True)\
            .limit(1)\
            .execute()

        if result.data:
            p = result.data[0]
            input_price = Decimal(str(p["input_price_per_mtok"]))
            output_price = Decimal(str(p["output_price_per_mtok"]))
            cache_create_price = Decimal(str(p.get("cache_creation_price_per_mtok", 0) or 0))
            cache_read_price = Decimal(str(p.get("cache_read_price_per_mtok", 0) or 0))
        else:
            key = (provider, model)
            if key not in FALLBACK_PRICING:
                # Try partial match for versioned models
                base_model = "-".join(model.split("-")[:3])
                key = (provider, base_model)
            if key not in FALLBACK_PRICING:
                # Try first two parts
                base_model = "-".join(model.split("-")[:2])
                key = (provider, base_model)
            input_price, output_price = FALLBACK_PRICING.get(key, (Decimal("1"), Decimal("2")))
            cache_create_price = cache_read_price = Decimal("0")
    except Exception:
        key = (provider, model)
        input_price, output_price = FALLBACK_PRICING.get(key, (Decimal("1"), Decimal("2")))
        cache_create_price = cache_read_price = Decimal("0")

    # Calculate base cost (prices are per 1M tokens)
    base_cost = (
        Decimal(input_tokens) * input_price +
        Decimal(output_tokens) * output_price
    ) / Decimal("1000000")

    # Add cache costs
    if cache_creation_tokens:
        base_cost += (Decimal(cache_creation_tokens) * cache_create_price) / Decimal("1000000")
    if cache_read_tokens:
        base_cost += (Decimal(cache_read_tokens) * cache_read_price) / Decimal("1000000")

    return base_cost.quantize(Decimal("0.000001"))
