"""
Core proxy handler for intercepting and forwarding LLM API requests.

This is the heart of ClawShell - it intercepts requests,
logs them, enforces budgets, applies routing rules, and forwards to providers.
"""

import json
import time
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import httpx
from fastapi import BackgroundTasks, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.budget_engine import BudgetEngine
from app.core.cost_calculator import calculate_cost
from app.core.pricing_data import PROVIDER_BASE_URLS
from app.core.smart_router import SmartRouter
from app.core.stream_handler import StreamHandler
from app.core.token_counter import (
    count_tokens_anthropic,
    count_tokens_openai,
    extract_usage_from_response,
)
from app.models.api_log import ApiLog

settings = get_settings()


class ProxyHandler:
    """Handles proxying of LLM API requests."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.budget_engine = BudgetEngine(db)
        self.smart_router = SmartRouter(db)
        self.stream_handler = StreamHandler()
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.proxy_timeout_seconds),
            follow_redirects=True,
        )

    async def handle_anthropic_request(
        self,
        request: Request,
        user_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """
        Handle Anthropic Messages API request.

        Endpoint: POST /v1/messages
        """
        start_time = time.monotonic()
        request_id = uuid.uuid4()

        # Read request body
        body = await request.body()
        request_data = json.loads(body)

        # Extract key fields
        model = request_data.get("model", "claude-sonnet-4-5")
        messages = request_data.get("messages", [])
        system = request_data.get("system")
        is_streaming = request_data.get("stream", False)

        # Estimate input tokens for budget check
        count_tokens_anthropic(messages, system, model)
        estimated_cost = Decimal("0.10")  # Conservative $0.10 estimate

        # Check budget
        budget_decision = await self.budget_engine.check_budget(
            user_id=user_id,
            agent_id=agent_id,
            model=model,
            estimated_cost=estimated_cost,
        )

        if budget_decision.action == "block":
            return Response(
                content=json.dumps(
                    {
                        "error": {
                            "type": "budget_exceeded",
                            "message": "Budget limit exceeded. Please increase your budget or wait for reset.",
                        }
                    }
                ),
                status_code=429,
                media_type="application/json",
                headers={
                    "x-acc-request-id": str(request_id),
                    "x-acc-budget-status": "exceeded",
                },
            )

        # Apply routing rules
        routing_decision = await self.smart_router.route_request(
            user_id=user_id,
            agent_id=agent_id,
            requested_model=model,
            messages=messages,
            metadata={"system": system, "stream": is_streaming},
        )

        # Update model if routed
        original_model = model
        if routing_decision.target_model != model:
            model = routing_decision.target_model
            request_data["model"] = model

        # Get provider API key from headers
        provider_api_key = request.headers.get("anthropic-api-key") or request.headers.get(
            "x-api-key"
        )

        if not provider_api_key:
            return Response(
                content=json.dumps(
                    {
                        "error": {
                            "type": "missing_api_key",
                            "message": "Missing Anthropic API key. Include 'anthropic-api-key' header.",
                        }
                    }
                ),
                status_code=401,
                media_type="application/json",
            )

        # Forward to Anthropic
        headers = {
            "Content-Type": "application/json",
            "x-api-key": provider_api_key,
            "anthropic-version": request.headers.get("anthropic-version", "2023-06-01"),
        }

        provider_url = f"{PROVIDER_BASE_URLS['anthropic']}/v1/messages"

        try:
            if is_streaming:
                return await self._handle_streaming_request(
                    provider_url=provider_url,
                    headers=headers,
                    request_data=request_data,
                    provider="anthropic",
                    original_model=original_model,
                    routed_model=model,
                    user_id=user_id,
                    agent_id=agent_id,
                    request_id=request_id,
                    start_time=start_time,
                    background_tasks=background_tasks,
                )
            else:
                return await self._handle_standard_request(
                    provider_url=provider_url,
                    headers=headers,
                    request_data=request_data,
                    provider="anthropic",
                    original_model=original_model,
                    routed_model=model,
                    user_id=user_id,
                    agent_id=agent_id,
                    request_id=request_id,
                    start_time=start_time,
                    background_tasks=background_tasks,
                )

        except httpx.TimeoutException:
            return Response(
                content=json.dumps({"error": {"type": "timeout", "message": "Request timed out"}}),
                status_code=504,
                media_type="application/json",
            )
        except httpx.RequestError as e:
            return Response(
                content=json.dumps({"error": {"type": "proxy_error", "message": str(e)}}),
                status_code=502,
                media_type="application/json",
            )

    async def handle_openai_request(
        self,
        request: Request,
        user_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """
        Handle OpenAI Chat Completions API request.

        Endpoint: POST /v1/chat/completions
        """
        start_time = time.monotonic()
        request_id = uuid.uuid4()

        body = await request.body()
        request_data = json.loads(body)

        model = request_data.get("model", "gpt-4o")
        messages = request_data.get("messages", [])
        is_streaming = request_data.get("stream", False)

        # Estimate tokens
        count_tokens_openai(messages, model)
        estimated_cost = Decimal("0.10")

        # Check budget
        budget_decision = await self.budget_engine.check_budget(
            user_id=user_id,
            agent_id=agent_id,
            model=model,
            estimated_cost=estimated_cost,
        )

        if budget_decision.action == "block":
            return Response(
                content=json.dumps(
                    {"error": {"type": "budget_exceeded", "message": "Budget limit exceeded"}}
                ),
                status_code=429,
                media_type="application/json",
                headers={"x-acc-request-id": str(request_id)},
            )

        # Routing
        routing_decision = await self.smart_router.route_request(
            user_id=user_id,
            agent_id=agent_id,
            requested_model=model,
            messages=messages,
            metadata={"stream": is_streaming},
        )

        original_model = model
        if routing_decision.target_model != model:
            model = routing_decision.target_model
            request_data["model"] = model

        # Get API key
        provider_api_key = request.headers.get("authorization", "").replace("Bearer ", "")
        if not provider_api_key:
            return Response(
                content=json.dumps({"error": {"type": "missing_api_key"}}),
                status_code=401,
                media_type="application/json",
            )

        # Forward to OpenAI
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider_api_key}",
        }

        provider_url = f"{PROVIDER_BASE_URLS['openai']}/v1/chat/completions"

        try:
            if is_streaming:
                return await self._handle_streaming_request(
                    provider_url=provider_url,
                    headers=headers,
                    request_data=request_data,
                    provider="openai",
                    original_model=original_model,
                    routed_model=model,
                    user_id=user_id,
                    agent_id=agent_id,
                    request_id=request_id,
                    start_time=start_time,
                    background_tasks=background_tasks,
                )
            else:
                return await self._handle_standard_request(
                    provider_url=provider_url,
                    headers=headers,
                    request_data=request_data,
                    provider="openai",
                    original_model=original_model,
                    routed_model=model,
                    user_id=user_id,
                    agent_id=agent_id,
                    request_id=request_id,
                    start_time=start_time,
                    background_tasks=background_tasks,
                )

        except httpx.TimeoutException:
            return Response(
                content=json.dumps({"error": {"type": "timeout"}}),
                status_code=504,
                media_type="application/json",
            )
        except httpx.RequestError as e:
            return Response(
                content=json.dumps({"error": {"type": "proxy_error", "message": str(e)}}),
                status_code=502,
                media_type="application/json",
            )

    async def _handle_standard_request(
        self,
        provider_url: str,
        headers: dict,
        request_data: dict,
        provider: str,
        original_model: str,
        routed_model: str,
        user_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        request_id: uuid.UUID,
        start_time: float,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle non-streaming request."""
        response = await self.http_client.post(
            provider_url,
            headers=headers,
            json=request_data,
        )

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Extract usage from response
        response_data = response.json() if response.status_code == 200 else {}
        usage = extract_usage_from_response(provider, response_data)

        # Calculate cost
        cost = calculate_cost(
            provider=provider,
            model=routed_model,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cache_creation_tokens=usage["cache_creation_tokens"],
            cache_read_tokens=usage["cache_read_tokens"],
        )

        # Log in background
        background_tasks.add_task(
            self._log_request,
            user_id=user_id,
            agent_id=agent_id,
            request_id=request_id,
            provider=provider,
            model=routed_model,
            original_model=original_model if original_model != routed_model else None,
            endpoint="/v1/messages" if provider == "anthropic" else "/v1/chat/completions",
            request_tokens=usage["input_tokens"],
            response_tokens=usage["output_tokens"],
            cache_creation_tokens=usage["cache_creation_tokens"],
            cache_read_tokens=usage["cache_read_tokens"],
            cost_usd=cost,
            latency_ms=latency_ms,
            status_code=response.status_code,
            is_streaming=False,
        )

        # Update budget spend
        await self.budget_engine.update_spend(user_id, cost)

        # Return response with ACC headers
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={
                "Content-Type": "application/json",
                "x-acc-request-id": str(request_id),
                "x-acc-cost": str(cost),
                "x-acc-tokens-input": str(usage["input_tokens"]),
                "x-acc-tokens-output": str(usage["output_tokens"]),
                "x-acc-model-used": routed_model,
                "x-acc-latency-ms": str(latency_ms),
            },
        )

    async def _handle_streaming_request(
        self,
        provider_url: str,
        headers: dict,
        request_data: dict,
        provider: str,
        original_model: str,
        routed_model: str,
        user_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        request_id: uuid.UUID,
        start_time: float,
        background_tasks: BackgroundTasks,
    ) -> StreamingResponse:
        """Handle streaming request with SSE."""

        async def stream_generator() -> AsyncGenerator[bytes, None]:
            usage_data = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
            }

            async with self.http_client.stream(
                "POST",
                provider_url,
                headers=headers,
                json=request_data,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield line.encode() + b"\n\n"
                            break

                        try:
                            data = json.loads(data_str)
                            # Extract usage from final chunk
                            extracted = self.stream_handler.extract_usage_from_stream_chunk(
                                provider, data
                            )
                            if extracted:
                                usage_data.update(extracted)

                            # Re-emit the SSE event
                            yield line.encode() + b"\n\n"
                        except json.JSONDecodeError:
                            yield line.encode() + b"\n\n"

            # Calculate cost after stream completes
            latency_ms = int((time.monotonic() - start_time) * 1000)
            cost = calculate_cost(
                provider=provider,
                model=routed_model,
                input_tokens=usage_data["input_tokens"],
                output_tokens=usage_data["output_tokens"],
                cache_creation_tokens=usage_data["cache_creation_tokens"],
                cache_read_tokens=usage_data["cache_read_tokens"],
            )

            # Log in background (cannot use background_tasks in generator)
            await self._log_request(
                user_id=user_id,
                agent_id=agent_id,
                request_id=request_id,
                provider=provider,
                model=routed_model,
                original_model=original_model if original_model != routed_model else None,
                endpoint="/v1/messages" if provider == "anthropic" else "/v1/chat/completions",
                request_tokens=usage_data["input_tokens"],
                response_tokens=usage_data["output_tokens"],
                cache_creation_tokens=usage_data["cache_creation_tokens"],
                cache_read_tokens=usage_data["cache_read_tokens"],
                cost_usd=cost,
                latency_ms=latency_ms,
                status_code=200,
                is_streaming=True,
            )

            await self.budget_engine.update_spend(user_id, cost)

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "x-acc-request-id": str(request_id),
                "x-acc-model-used": routed_model,
            },
        )

    async def _log_request(
        self,
        user_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        request_id: uuid.UUID,
        provider: str,
        model: str,
        original_model: str | None,
        endpoint: str,
        request_tokens: int,
        response_tokens: int,
        cache_creation_tokens: int,
        cache_read_tokens: int,
        cost_usd: Decimal,
        latency_ms: int,
        status_code: int,
        is_streaming: bool,
    ) -> None:
        """Log request to database."""
        log_entry = ApiLog(
            id=request_id,
            user_id=user_id,
            agent_id=agent_id,
            provider=provider,
            model=model,
            original_model=original_model,
            routed_to_model=model if original_model else None,
            endpoint=endpoint,
            request_tokens=request_tokens,
            response_tokens=response_tokens,
            total_tokens=request_tokens + response_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status_code=status_code,
            is_streaming=is_streaming,
        )

        self.db.add(log_entry)
        await self.db.commit()
