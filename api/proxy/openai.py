"""
OpenAI Chat Completions API Proxy
POST /v1/chat/completions
"""
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import os
import json
import hashlib
from decimal import Decimal
from datetime import datetime

from _lib.redis import check_rate_limit
from _lib.auth import validate_api_key
from _lib.cost import calculate_cost
from _lib.budget import check_budget, update_spend
from _lib.tokens import count_tokens_openai
from _lib.logger import log_request, structured_log
from _lib.router import get_routing_rules, apply_routing

app = FastAPI()

OPENAI_BASE = "https://api.openai.com"

@app.post("/v1/chat/completions")
async def proxy_openai(request: Request):
    start_time = datetime.utcnow()
    
    # 1. Extract API key
    api_key = request.headers.get("x-acc-api-key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # 2. Validate auth
    try:
        user_id, user_plan = await validate_api_key(api_key)
    except HTTPException as e:
        raise e
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    # 3. Rate limiting
    allowed, remaining = await check_rate_limit(key_hash)
    if not allowed:
        raise HTTPException(429, "Rate limit exceeded")
    
    # 4. Parse request
    try:
        body = await request.json()
    except:
        raise HTTPException(400, "Invalid JSON body")
    
    model = body.get("model", "gpt-4o")
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    
    # 5. Token estimation
    estimated_input = count_tokens_openai(model, messages)
    
    # 6. Budget check
    budget_status = await check_budget(user_id, Decimal("0.01"), model)
    if budget_status.get("action") == "block":
        raise HTTPException(403, f"Budget exceeded: {budget_status.get('budget_name')}")
    
    # 7. Handle downgrade
    if budget_status.get("downgrade_model"):
        model = budget_status["downgrade_model"]
        body["model"] = model
    
    # 8. Apply routing
    routing_rules = await get_routing_rules(user_id)
    model, routing_metadata = apply_routing(model, messages, routing_rules)
    body["model"] = model
    
    # 9. Forward to OpenAI
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            if stream:
                return await handle_streaming(client, body, headers, user_id, model, start_time)
            
            resp = await client.post(
                f"{OPENAI_BASE}/v1/chat/completions",
                headers=headers,
                json=body,
                timeout=120.0
            )
            
            # 10. Process response
            response_data = resp.json()
            
            usage = response_data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", estimated_input)
            output_tokens = usage.get("completion_tokens", 0)
            
            # OpenAI doesn't have cache tokens in standard API yet
            cost = calculate_cost("openai", model, input_tokens, output_tokens)
            
            latency = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await log_request(
                user_id=user_id,
                provider="openai",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=float(cost),
                latency_ms=latency,
                status_code=resp.status_code,
                metadata={"stream": stream, "routing": routing_metadata},
            )
            
            await update_spend(user_id, cost)
            
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


async def handle_streaming(client, body, headers, user_id, model, start_time):
    """Handle streaming responses"""
    resp = await client.post(
        f"{OPENAI_BASE}/v1/chat/completions",
        headers=headers,
        json=body,
        timeout=120.0
    )
    
    async def stream_generator():
        total_output = 0
        async for chunk in resp.aiter_bytes():
            total_output += len(chunk) // 4
            yield chunk
        
        latency = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        estimated_input = count_tokens_openai(model, body.get("messages", []))
        cost = calculate_cost("openai", model, estimated_input, total_output)
        
        await log_request(
            user_id=user_id,
            provider="openai",
            model=model,
            input_tokens=estimated_input,
            output_tokens=total_output,
            cost=float(cost),
            latency_ms=latency,
            status_code=200,
            metadata={"stream": True},
        )
        await update_spend(user_id, cost)
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"x-acc-model": model}
    )
