"""
Stream handler for processing SSE streaming responses.

Captures token usage from streaming responses for accurate cost tracking.
"""

import json


class StreamHandler:
    """Handles streaming SSE responses from LLM providers."""

    def extract_usage_from_stream_chunk(self, provider: str, chunk: dict) -> dict | None:
        """
        Extract usage data from a streaming chunk.

        Different providers send usage at different points:
        - Anthropic: In the final 'message_delta' event
        - OpenAI: In the final chunk if stream_options.include_usage=true

        Args:
            provider: Provider name (anthropic, openai, etc.)
            chunk: Parsed JSON chunk from the stream

        Returns:
            Dict with token counts if found, None otherwise
        """
        if provider == "anthropic":
            return self._extract_anthropic_usage(chunk)
        elif provider == "openai":
            return self._extract_openai_usage(chunk)
        elif provider == "google":
            return self._extract_google_usage(chunk)
        return None

    def _extract_anthropic_usage(self, chunk: dict) -> dict | None:
        """
        Extract usage from Anthropic streaming chunk.

        Anthropic sends usage in:
        1. 'message_start' event with initial usage (input only)
        2. 'message_delta' event with final usage (output tokens)
        """
        event_type = chunk.get("type")

        if event_type == "message_start":
            message = chunk.get("message", {})
            usage = message.get("usage", {})
            return {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": 0,
                "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
                "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
            }

        elif event_type == "message_delta":
            usage = chunk.get("usage", {})
            return {
                "input_tokens": 0,  # Already counted in message_start
                "output_tokens": usage.get("output_tokens", 0),
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
            }

        return None

    def _extract_openai_usage(self, chunk: dict) -> dict | None:
        """
        Extract usage from OpenAI streaming chunk.

        OpenAI sends usage in the final chunk if stream_options.include_usage=true.
        """
        # Check for usage in the chunk
        usage = chunk.get("usage")
        if usage:
            return {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "cache_creation_tokens": 0,
                "cache_read_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            }

        # Check for usage in choices (some responses include it there)
        choices = chunk.get("choices", [])
        if choices and len(choices) > 0:
            finish_reason = choices[0].get("finish_reason")
            if finish_reason:
                # This is the last chunk, but usage might be separate
                pass

        return None

    def _extract_google_usage(self, chunk: dict) -> dict | None:
        """Extract usage from Google Gemini streaming chunk."""
        usage_metadata = chunk.get("usageMetadata")
        if usage_metadata:
            return {
                "input_tokens": usage_metadata.get("promptTokenCount", 0),
                "output_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "cache_creation_tokens": 0,
                "cache_read_tokens": usage_metadata.get("cachedContentTokenCount", 0),
            }
        return None

    async def process_stream_chunk(
        self, provider: str, raw_line: str
    ) -> tuple[str | None, dict | None]:
        """
        Process a raw SSE line.

        Args:
            provider: Provider name
            raw_line: Raw line from SSE stream

        Returns:
            Tuple of (reformatted_line, usage_data)
        """
        if not raw_line.startswith("data: "):
            return raw_line, None

        data_str = raw_line[6:]
        if data_str.strip() == "[DONE]":
            return raw_line, None

        try:
            chunk = json.loads(data_str)
            usage = self.extract_usage_from_stream_chunk(provider, chunk)
            return raw_line, usage
        except json.JSONDecodeError:
            return raw_line, None
