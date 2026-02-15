"""Proxy endpoints that mimic LLM provider APIs."""

import hashlib
import os
import time
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.core.cost_calculator import calculate_cost

router = APIRouter()
settings = get_settings()

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


async def validate_api_key(api_key: str) -> dict | None:
    """
    Validate API key against Supabase database.

    Returns user info if valid, None if invalid.
    """
    import httpx

    if not api_key or not api_key.startswith("acc_"):
        return None

    # Hash the key (SHA-256) to match storage
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Query Supabase for the API key
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/api_keys",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                },
                params={
                    "select": "id,user_id,name,is_active",
                    "key_hash": f"eq.{key_hash}",
                    "is_active": "eq.true",
                },
                timeout=10.0,
            )

            if response.status_code != 200:
                return None

            data = response.json()
            if not data or len(data) == 0:
                return None

            key_record = data[0]

            # Update last_used_at in background (fire and forget)
            try:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/api_keys",
                    headers={
                        "apikey": SUPABASE_SERVICE_KEY,
                        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                    params={"id": f"eq.{key_record['id']}"},
                    json={"last_used_at": datetime.utcnow().isoformat()},
                )
            except Exception:
                pass  # Don't fail on last_used update error

            return key_record

        except Exception as e:
            print(f"Error validating API key: {e}")
            return None


async def get_current_user_id(
    authorization: str | None = Header(None, alias="Authorization"),
    x_acc_api_key: str | None = Header(None, alias="x-acc-api-key"),
) -> str:
    """
    Validate ACC API key and return user ID.

    Supports two authentication methods:
    1. Bearer token: Authorization: Bearer acc_xxx
    2. Header: x-acc-api-key: acc_xxx
    """
    # Extract API key from either header
    api_key = None

    if x_acc_api_key:
        api_key = x_acc_api_key
    elif authorization:
        api_key = authorization[7:] if authorization.startswith("Bearer ") else authorization

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Use Authorization: Bearer acc_xxx or x-acc-api-key header",
        )

    # Validate the key
    key_info = await validate_api_key(api_key)

    if not key_info:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    if not key_info.get("is_active"):
        raise HTTPException(status_code=403, detail="API key has been revoked")

    return key_info["user_id"]


@router.post("/messages")
async def anthropic_messages(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    """
    Anthropic Messages API compatible endpoint.

    Forwards requests to Anthropic and logs usage for cost tracking.
    Supports both streaming and non-streaming responses.
    """
    import httpx

    start_time = time.monotonic()

    # Get request body
    body = await request.json()
    model = body.get("model", "claude-3-opus-20240229")
    is_streaming = body.get("stream", False)

    # Get Anthropic API key
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    # Forward request to Anthropic
    headers = {
        "x-api-key": anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    # Handle streaming response
    if is_streaming:
        return await _handle_anthropic_streaming(
            body=body,
            headers=headers,
            model=model,
            user_id=user_id,
            start_time=start_time,
        )

    # Non-streaming request
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("error", {}).get("message", "Anthropic API error"),
                )

            # Log the request to Supabase (background)
            response_data = response.json()
            usage = response_data.get("usage", {})

            # Calculate actual cost using pricing table
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
            cache_read_tokens = usage.get("cache_read_input_tokens", 0)

            cost = calculate_cost(
                provider="anthropic",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
            )
            cost_usd = float(cost)

            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Log request
            try:
                async with httpx.AsyncClient(timeout=10.0) as log_client:
                    await log_client.post(
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
                            "provider": "anthropic",
                            "method": "POST",
                            "path": "/v1/messages",
                            "status_code": 200,
                            "prompt_tokens": input_tokens,
                            "completion_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens,
                            "cost_usd": cost_usd,
                            "latency_ms": latency_ms,
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    )
            except Exception as e:
                print(f"Error logging request: {e}")

            return response.json()

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Anthropic API request timed out")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")


@router.post("/chat/completions")
async def openai_chat_completions(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    """
    OpenAI Chat Completions API compatible endpoint.

    Forwards requests to OpenAI and logs usage for cost tracking.
    Supports both streaming and non-streaming responses.
    """
    import httpx

    start_time = time.monotonic()

    # Get request body
    body = await request.json()
    model = body.get("model", "gpt-4o-mini")
    is_streaming = body.get("stream", False)

    # Get OpenAI API key
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    # Forward request to OpenAI
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json",
    }

    # Handle streaming response
    if is_streaming:
        return await _handle_openai_streaming(
            body=body,
            headers=headers,
            model=model,
            user_id=user_id,
            start_time=start_time,
        )

    # Non-streaming request
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("error", {}).get("message", "OpenAI API error"),
                )

            # Log the request to Supabase
            response_data = response.json()
            usage = response_data.get("usage", {})

            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            # Calculate actual cost using pricing table
            cost = calculate_cost(
                provider="openai",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            cost_usd = float(cost)

            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Log request
            try:
                async with httpx.AsyncClient(timeout=10.0) as log_client:
                    await log_client.post(
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
                            "provider": "openai",
                            "method": "POST",
                            "path": "/v1/chat/completions",
                            "status_code": 200,
                            "prompt_tokens": input_tokens,
                            "completion_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens,
                            "cost_usd": cost_usd,
                            "latency_ms": latency_ms,
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    )
            except Exception as e:
                print(f"Error logging request: {e}")

            return response.json()

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="OpenAI API request timed out")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")


async def _handle_anthropic_streaming(
    body: dict,
    headers: dict,
    model: str,
    user_id: str,
    start_time: float,
) -> StreamingResponse:
    """
    Handle streaming response from Anthropic API.

    Collects usage data from the stream and logs the request upon completion.
    """
    import httpx
    import json

    async def stream_generator():
        usage_data = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                # Extract usage from message_start or final message_delta
                                if data.get("type") == "message_start":
                                    message = data.get("message", {})
                                    usage = message.get("usage", {})
                                    usage_data["input_tokens"] = usage.get("input_tokens", 0)
                                    usage_data["cache_creation_input_tokens"] = usage.get(
                                        "cache_creation_input_tokens", 0
                                    )
                                    usage_data["cache_read_input_tokens"] = usage.get(
                                        "cache_read_input_tokens", 0
                                    )
                                elif data.get("type") == "message_delta":
                                    usage = data.get("usage", {})
                                    usage_data["output_tokens"] = usage.get("output_tokens", 0)
                            except json.JSONDecodeError:
                                pass
                    yield line + "\n\n"

        # Log request after stream completes
        latency_ms = int((time.monotonic() - start_time) * 1000)
        cost = calculate_cost(
            provider="anthropic",
            model=model,
            input_tokens=usage_data["input_tokens"],
            output_tokens=usage_data["output_tokens"],
            cache_creation_tokens=usage_data["cache_creation_input_tokens"],
            cache_read_tokens=usage_data["cache_read_input_tokens"],
        )
        cost_usd = float(cost)

        # Log to Supabase
        try:
            async with httpx.AsyncClient(timeout=10.0) as log_client:
                await log_client.post(
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
                        "provider": "anthropic",
                        "method": "POST",
                        "path": "/v1/messages",
                        "status_code": 200,
                        "prompt_tokens": usage_data["input_tokens"],
                        "completion_tokens": usage_data["output_tokens"],
                        "total_tokens": usage_data["input_tokens"] + usage_data["output_tokens"],
                        "cost_usd": cost_usd,
                        "latency_ms": latency_ms,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            print(f"Error logging streaming request: {e}")

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Acc-Provider": "anthropic",
            "X-Acc-Model": model,
        },
    )


async def _handle_openai_streaming(
    body: dict,
    headers: dict,
    model: str,
    user_id: str,
    start_time: float,
) -> StreamingResponse:
    """
    Handle streaming response from OpenAI API.

    Collects usage data from the stream and logs the request upon completion.
    """
    import httpx
    import json

    async def stream_generator():
        usage_data = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield line + "\n\n"
                            break
                        try:
                            data = json.loads(data_str)
                            # OpenAI includes usage in the final chunk when stream_options.include_usage is true
                            if "usage" in data:
                                usage_data["prompt_tokens"] = data["usage"].get("prompt_tokens", 0)
                                usage_data["completion_tokens"] = data["usage"].get(
                                    "completion_tokens", 0
                                )
                        except json.JSONDecodeError:
                            pass
                    yield line + "\n\n"

        # Log request after stream completes
        latency_ms = int((time.monotonic() - start_time) * 1000)
        cost = calculate_cost(
            provider="openai",
            model=model,
            input_tokens=usage_data["prompt_tokens"],
            output_tokens=usage_data["completion_tokens"],
        )
        cost_usd = float(cost)

        # Log to Supabase
        try:
            async with httpx.AsyncClient(timeout=10.0) as log_client:
                await log_client.post(
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
                        "provider": "openai",
                        "method": "POST",
                        "path": "/v1/chat/completions",
                        "status_code": 200,
                        "prompt_tokens": usage_data["prompt_tokens"],
                        "completion_tokens": usage_data["completion_tokens"],
                        "total_tokens": usage_data["prompt_tokens"] + usage_data["completion_tokens"],
                        "cost_usd": cost_usd,
                        "latency_ms": latency_ms,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            print(f"Error logging streaming request: {e}")

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Acc-Provider": "openai",
            "X-Acc-Model": model,
        },
    )


@router.get("/models")
async def list_models():
    """List available models."""
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
            {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai"},
            {"id": "gpt-4-turbo", "object": "model", "owned_by": "openai"},
            {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
            {"id": "claude-3-opus-20240229", "object": "model", "owned_by": "anthropic"},
            {"id": "claude-3-sonnet-20240229", "object": "model", "owned_by": "anthropic"},
            {"id": "claude-3-haiku-20240307", "object": "model", "owned_by": "anthropic"},
        ],
    }
