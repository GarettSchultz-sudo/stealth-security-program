"""
Token counting utilities for different LLM providers.

Uses tiktoken for OpenAI models and estimation for others.
"""

import logging
from functools import lru_cache

import tiktoken

logger = logging.getLogger(__name__)


@lru_cache(maxsize=10)
def get_tiktoken_encoder(model: str) -> tiktoken.Encoding:
    """
    Get tiktoken encoder for a model.

    Falls back to cl100k_base (GPT-4 encoding) for unknown models.
    """
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Fall back to cl100k_base (GPT-4, GPT-3.5-turbo, text-embedding-ada-002)
        logger.debug(f"Unknown model {model}, using cl100k_base encoding")
        return tiktoken.get_encoding("cl100k_base")


def count_tokens_openai(messages: list[dict], model: str = "gpt-4o") -> int:
    """
    Count tokens for OpenAI chat completions format.

    Based on OpenAI's token counting methodology.
    """
    encoder = get_tiktoken_encoder(model)

    # Token overhead per message (format tokens)
    tokens_per_message = 3  # every message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_name = 1  # if name is specified

    total = 0
    for message in messages:
        total += tokens_per_message
        for key, value in message.items():
            if isinstance(value, str):
                total += len(encoder.encode(value))
            elif isinstance(value, list):
                # Handle content arrays (vision, etc.)
                for item in value:
                    if isinstance(item, dict) and "text" in item:
                        total += len(encoder.encode(item["text"]))
            if key == "name":
                total += tokens_per_name

    total += 3  # every reply is primed with <|start|>assistant<|message|>

    return total


def count_tokens_anthropic(
    messages: list[dict],
    system: str | list[dict] | None = None,
    model: str = "claude-sonnet-4-5",
) -> int:
    """
    Estimate token count for Anthropic Messages API format.

    Anthropic uses a different tokenizer. This is an approximation.
    For accurate counts, use the response's usage field.
    """
    # Anthropic's tokenizer is not public, so we use cl100k_base as approximation
    # The ratio is roughly 1:1.1 (Anthropic tokens are slightly larger)
    encoder = get_tiktoken_encoder("cl100k_base")

    total = 0

    # System prompt
    if system:
        if isinstance(system, str):
            total += len(encoder.encode(system))
        elif isinstance(system, list):
            for block in system:
                if isinstance(block, dict) and "text" in block:
                    total += len(encoder.encode(block["text"]))

    # Messages
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            total += len(encoder.encode(content))
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if "text" in block:
                        total += len(encoder.encode(block["text"]))
                    # Image tokens are calculated differently
                    # Approximately 85-170 tokens depending on size
                    elif "source" in block:
                        total += 150  # Estimate for images

        # Role and formatting overhead
        total += 4  # Approximate overhead per message

    # Apply correction factor (Anthropic tokens are ~10% larger)
    return int(total * 1.1)


def count_tokens_google(
    contents: list[dict],
    system_instruction: str | None = None,
) -> int:
    """
    Estimate token count for Google Gemini API format.
    """
    encoder = get_tiktoken_encoder("cl100k_base")

    total = 0

    if system_instruction:
        total += len(encoder.encode(system_instruction))

    for content in contents:
        parts = content.get("parts", [])
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                total += len(encoder.encode(part["text"]))
            elif isinstance(part, str):
                total += len(encoder.encode(part))

    return int(total * 1.05)  # Slight correction factor


def count_tokens_from_text(text: str, model: str | None = None) -> int:
    """
    Count tokens in a plain text string.

    Uses tiktoken if available, otherwise falls back to estimation.
    """
    if not text:
        return 0

    try:
        encoder = get_tiktoken_encoder(model or "gpt-4")
        return len(encoder.encode(text))
    except Exception:
        # Fallback: ~4 characters per token on average
        return len(text) // 4


def extract_usage_from_response(provider: str, response_data: dict) -> dict:
    """
    Extract token usage from provider response.

    Returns dict with: input_tokens, output_tokens, cache_creation, cache_read
    """
    usage: dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }

    if provider == "anthropic":
        # Anthropic usage structure
        resp_usage = response_data.get("usage", {})
        usage["input_tokens"] = resp_usage.get("input_tokens", 0)
        usage["output_tokens"] = resp_usage.get("output_tokens", 0)
        usage["cache_creation_tokens"] = resp_usage.get("cache_creation_input_tokens", 0)
        usage["cache_read_tokens"] = resp_usage.get("cache_read_input_tokens", 0)

    elif provider == "openai":
        # OpenAI usage structure
        resp_usage = response_data.get("usage", {})
        usage["input_tokens"] = resp_usage.get("prompt_tokens", 0)
        usage["output_tokens"] = resp_usage.get("completion_tokens", 0)
        # OpenAI doesn't have prompt caching in the same way (yet)
        # But cached tokens may appear as prompt_tokens_details
        details = resp_usage.get("prompt_tokens_details", {})
        usage["cache_read_tokens"] = details.get("cached_tokens", 0)

    elif provider == "google":
        # Google Gemini usage structure
        metadata = response_data.get("usageMetadata", {})
        usage["input_tokens"] = metadata.get("promptTokenCount", 0)
        usage["output_tokens"] = metadata.get("candidatesTokenCount", 0)
        usage["cache_read_tokens"] = metadata.get("cachedContentTokenCount", 0)

    elif provider == "deepseek":
        # DeepSeek usage (OpenAI-compatible)
        resp_usage = response_data.get("usage", {})
        usage["input_tokens"] = resp_usage.get("prompt_tokens", 0)
        usage["output_tokens"] = resp_usage.get("completion_tokens", 0)
        # DeepSeek prompt caching
        details = resp_usage.get("prompt_cache_hit_tokens", 0)
        usage["cache_read_tokens"] = details

    elif provider in ("groq", "mistral"):
        # Groq/Mistral use OpenAI-compatible format
        resp_usage = response_data.get("usage", {})
        usage["input_tokens"] = resp_usage.get("prompt_tokens", 0)
        usage["output_tokens"] = resp_usage.get("completion_tokens", 0)

    return usage
