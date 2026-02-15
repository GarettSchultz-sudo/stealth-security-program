"""
Streaming Interceptor for Real-time Budget Enforcement

Intercepts streaming responses and enforces budget limits mid-stream.
Supports graceful termination and context preservation for model switching.
"""

import asyncio
import hashlib
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import httpx

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


class StreamState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    COMPLETED = "completed"


@dataclass
class StreamContext:
    """Context for an active streaming request"""

    session_id: str
    user_id: str
    budget_id: str
    model: str
    provider: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    accumulated_content: str = ""
    total_tokens: int = 0
    cost_so_far: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    state: StreamState = StreamState.ACTIVE
    last_chunk_time: datetime = field(default_factory=datetime.utcnow)
    chunk_count: int = 0


@dataclass
class BudgetCheckResult:
    """Result of a budget check"""

    allowed: bool
    current_spend: float
    limit: float
    percent_used: float
    recommended_action: str  # "continue", "downgrade", "block"
    recommended_model: Optional[str] = None
    estimated_remaining: float = 0.0


class StreamingInterceptor:
    """
    Intercepts streaming responses for budget enforcement.

    Features:
    - Real-time budget checking during streams
    - Graceful stream termination
    - Context preservation for model switching
    - Cost tracking per chunk
    """

    def __init__(self):
        self.active_streams: Dict[str, StreamContext] = {}
        self._http_client = httpx.AsyncClient()

    async def check_budget(self, user_id: str, budget_id: str) -> BudgetCheckResult:
        """Check current budget status from Supabase"""
        try:
            response = await self._http_client.get(
                f"{SUPABASE_URL}/rest/v1/budgets",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                },
                params={"id": f"eq.{budget_id}", "select": "*"},
            )

            if response.status_code != 200:
                return BudgetCheckResult(
                    allowed=True,  # Fail open
                    current_spend=0,
                    limit=float("inf"),
                    percent_used=0,
                    recommended_action="continue",
                )

            budgets = response.json()
            if not budgets:
                return BudgetCheckResult(
                    allowed=True,
                    current_spend=0,
                    limit=float("inf"),
                    percent_used=0,
                    recommended_action="continue",
                )

            budget = budgets[0]
            current_spend = budget.get("current_spend_usd", 0)
            limit = budget.get("limit_usd", 1)
            percent_used = (current_spend / limit) * 100 if limit > 0 else 100

            recommended_action = "continue"
            recommended_model = None

            if percent_used >= 100:
                recommended_action = "block"
            elif percent_used >= 90:
                recommended_action = "downgrade"
                # Could query for recommended model here

            return BudgetCheckResult(
                allowed=percent_used < 100,
                current_spend=current_spend,
                limit=limit,
                percent_used=percent_used,
                recommended_action=recommended_action,
                recommended_model=recommended_model,
                estimated_remaining=max(0, limit - current_spend),
            )

        except Exception as e:
            print(f"Error checking budget: {e}")
            return BudgetCheckResult(
                allowed=True,  # Fail open
                current_spend=0,
                limit=float("inf"),
                percent_used=0,
                recommended_action="continue",
            )

    async def log_request(
        self,
        user_id: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        latency_ms: int,
        status_code: int = 200,
    ) -> None:
        """Log request to Supabase"""
        try:
            await self._http_client.post(
                f"{SUPABASE_URL}/rest/v1/request_logs",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={
                    "user_id": user_id,
                    "model": model,
                    "provider": provider,
                    "method": "POST",
                    "path": "/v1/chat/completions",
                    "status_code": status_code,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "cost_usd": cost_usd,
                    "latency_ms": latency_ms,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            print(f"Error logging request: {e}")

    def start_stream(
        self,
        session_id: str,
        user_id: str,
        budget_id: str,
        model: str,
        provider: str,
        messages: List[Dict[str, Any]],
    ) -> StreamContext:
        """Register a new streaming request"""
        context = StreamContext(
            session_id=session_id,
            user_id=user_id,
            budget_id=budget_id,
            model=model,
            provider=provider,
            messages=messages.copy(),
        )
        self.active_streams[session_id] = context
        return context

    def get_stream_context(self, session_id: str) -> Optional[StreamContext]:
        """Get context for an active stream"""
        return self.active_streams.get(session_id)

    async def intercept_stream(
        self,
        session_id: str,
        stream_generator: AsyncGenerator[bytes, None],
        on_budget_exceeded: Optional[Callable[[StreamContext], None]] = None,
        check_interval: int = 10,  # Check budget every N chunks
    ) -> AsyncGenerator[bytes, None]:
        """
        Intercept a streaming response for budget enforcement.

        Yields chunks while checking budget periodically.
        Terminates gracefully if budget is exceeded.
        """
        context = self.active_streams.get(session_id)
        if not context:
            async for chunk in stream_generator:
                yield chunk
            return

        chunk_count = 0
        start_time = time.time()

        try:
            async for chunk in stream_generator:
                # Update context
                context.last_chunk_time = datetime.utcnow()
                context.chunk_count = chunk_count
                context.state = StreamState.ACTIVE

                # Check budget periodically
                if chunk_count > 0 and chunk_count % check_interval == 0:
                    budget_check = await self.check_budget(
                        context.user_id, context.budget_id
                    )

                    if not budget_check.allowed:
                        context.state = StreamState.TERMINATED
                        if on_budget_exceeded:
                            on_budget_exceeded(context)
                        break

                    if budget_check.recommended_action == "downgrade":
                        # Could emit a warning event here
                        pass

                # Accumulate content for context preservation
                try:
                    context.accumulated_content += chunk.decode("utf-8")
                except:
                    pass

                yield chunk
                chunk_count += 1

        except asyncio.CancelledError:
            context.state = StreamState.TERMINATED
            raise

        finally:
            # Calculate final cost and log
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            # Estimate tokens from accumulated content
            estimated_tokens = len(context.accumulated_content) // 4
            estimated_cost = self._estimate_cost(
                context.model, len(str(context.messages)), estimated_tokens
            )

            await self.log_request(
                user_id=context.user_id,
                model=context.model,
                provider=context.provider,
                prompt_tokens=len(str(context.messages)) // 4,
                completion_tokens=estimated_tokens,
                cost_usd=estimated_cost,
                latency_ms=latency_ms,
                status_code=200 if context.state != StreamState.TERMINATED else 429,
            )

            context.state = StreamState.COMPLETED

    def terminate_stream(self, session_id: str) -> Optional[StreamContext]:
        """Terminate an active stream"""
        context = self.active_streams.get(session_id)
        if context:
            context.state = StreamState.TERMINATED
        return context

    def get_messages_for_continuation(
        self, session_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get messages for continuing a conversation with a different model.

        Includes the original messages plus any accumulated assistant response.
        """
        context = self.active_streams.get(session_id)
        if not context:
            return None

        messages = context.messages.copy()

        # Add accumulated assistant response if any
        if context.accumulated_content:
            messages.append(
                {"role": "assistant", "content": context.accumulated_content}
            )

        return messages

    def _estimate_cost(
        self, model: str, prompt_chars: int, completion_tokens: int
    ) -> float:
        """Estimate cost based on model and token counts"""
        # Simplified cost estimation
        cost_per_1k_tokens = {
            "gpt-4o": 0.005,
            "gpt-4o-mini": 0.00015,
            "gpt-4-turbo": 0.01,
            "gpt-3.5-turbo": 0.0005,
            "claude-3-opus-20240229": 0.015,
            "claude-3-sonnet-20240229": 0.003,
            "claude-3-haiku-20240307": 0.00025,
        }

        rate = cost_per_1k_tokens.get(model, 0.001)
        prompt_tokens = prompt_chars // 4
        total_tokens = prompt_tokens + completion_tokens

        return (total_tokens / 1000) * rate

    async def cleanup(self):
        """Cleanup resources"""
        await self._http_client.aclose()
        self.active_streams.clear()


# Singleton instance
_interceptor: Optional[StreamingInterceptor] = None


def get_streaming_interceptor() -> StreamingInterceptor:
    """Get the singleton interceptor instance"""
    global _interceptor
    if _interceptor is None:
        _interceptor = StreamingInterceptor()
    return _interceptor
