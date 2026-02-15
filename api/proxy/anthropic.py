"""
Anthropic Messages API Proxy
POST /v1/messages
"""
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import os
import json
import hashlib
from decimal import Decimal
from datetime import datetime

from _lib.db import get_supabase
from _lib.redis import check_rate_limit
from _lib.auth import validate_api_key
from _lib.cost import calculate_cost
from _lib.budget import check_budget, update_spend
from _lib.tokens import count_tokens_anthropic
from _lib.logger import log_request, structured_log
from _lib.router import get_routing_rules, apply_routing

app = FastAPI()

ANTHROPIC_BASE = "https://api.anthropic.com"

@app.post("/v1/messages")
async def proxy_anthropic(request: Request):
    start_time = datetime.utcnow()
    
    # 1. Extract API key
    api_key = request.headers.get("x-acc-api-key") or request.headers.get("x-api-key")
    
    # 2. Validate auth
    try:
        user_id, user_plan = await validate_api_key(api_key)
    except HTTPException as e:
        raise e
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    # 3. Rate limiting
    allowed, remaining = await check_rate_limit(key_hash)
    if not allowed:
        raise HTTPException(429, "Rate limit exceeded. Please retry later.")
    
    # 4. Parse request body
    try:
        body = await request.json()
    except:
        raise HTTPException(400, "Invalid JSON body")
    
    model = body.get("model", "claude-sonnet-4-20250514")
    messages = body.get("messages", [])
    system = body.get("system", "")
    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens", 4096)
    
    # 5. Token estimation for budget check
    estimated_input = count_tokens_anthropic(model, messages, system)
    
    # 6. Budget check
    budget_status = await check_budget(user_id, Decimal("0.01"), model)
    if budget_status.get("action") == "block":
        raise HTTPException(403, f"Budget exceeded: {budget_status.get('budget_name', 'Unknown')}")
    
    # 7. Handle downgrade
    if budget_status.get("downgrade_model"):
        original_model = model
        model = budget_status["downgrade_model"]
        body["model"] = model
        structured_log("info", "Model downgraded due to budget", 
                      original=original_model, downgraded=model, user_id=user_id)
    
    # 8. Get routing rules and apply
    routing_rules = await get_routing_rules(user_id)
    model, routing_metadata = apply_routing(model, messages, routing_rules)
    body["model"] = model
    
    # 9. Forward to Anthropic
    headers = {
        "x-api-key": os.environ.get("ANTHROPIC_API_KEY"),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            if stream:
                return await handle_streaming(request, client, body, headers, user_id, model, start_time, key_hash)
            
            resp = await client.post(
                f"{ANTHROPIC_BASE}/v1/messages",
                headers=headers,
                json=body,
                timeout=120.0
            )
            
            # 10. Process response
            response_data = resp.json()
            
            # Calculate cost
            usage = response_data.get("usage", {})
            input_tokens = usage.get("input_tokens", estimated_input)
            output_tokens = usage.get("output_tokens", 0)
            cache_creation = usage.get("cache_creation_input_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            
            cost = calculate_cost(
                "anthropic", model,
                input_tokens, output_tokens,
                cache_creation, cache_read
            )
            
            # Log request
            latency = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await log_request(
                user_id=user_id,
                provider="anthropic",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=float(cost),
                latency_ms=latency,
                status_code=resp.status_code,
                metadata={"stream": stream, "routing": routing_metadata},
                cache_creation_tokens=cache_creation,
                cache_read_tokens=cache_read,
            )
            
            # Update budget spend
            await update_spend(user_id, cost)
            
            # Return with cost headers
            return Response(
                content=json.dumps(response_data),
                status_code=resp.status_code,
                headers={
                    "content-type": "application/json",
                    "x-acc-cost": str(cost),
                    "x-acc-tokens": str(input_tokens + output_tokens),
                    "x-acc-model": model,
                    "x-ratelimit-remaining": str(remaining),
                }
            )
            
        except httpx.TimeoutException:
            raise HTTPException(504, "Upstream timeout")
        except httpx.RequestError as e:
            structured_log("error", "Upstream request failed", error=str(e))
            raise HTTPException(502, f"Upstream error: {str(e)}")


async def handle_streaming(request, client, body, headers, user_id, model, start_time, key_hash):
    """Handle streaming responses"""
    from _lib.logger import structured_log
    
    resp = await client.post(
        f"{ANTHROPIC_BASE}/v1/messages",
        headers=headers,
        json=body,
        timeout=120.0
    )
    
    # For streaming, we'll estimate costs and update later
    # This is a simplified approach - production would parse SSE events
    
    async def stream_generator():
        total_output = 0
        async for chunk in resp.aiter_bytes():
            # Rough token estimation from chunk size
            total_output += len(chunk) // 4
            yield chunk
        
        # Log after stream completes
        latency = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        estimated_input = count_tokens_anthropic(model, body.get("messages", []), body.get("system", ""))
        cost = calculate_cost("anthropic", model, estimated_input, total_output)
        
        await log_request(
            user_id=user_id,
            provider="anthropic",
            model=model,
            input_tokens=estimated_input,
            output_tokens=total_output,
            cost=float(cost),
            latency_ms=latency,
            status_code=resp.status_code,
            metadata={"stream": True},
        )
        await update_spend(user_id, cost)
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "x-acc-model": model,
        }
    )
