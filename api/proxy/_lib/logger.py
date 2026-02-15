"""
Structured Logging for API Requests
"""
import json
from datetime import datetime
from _lib.db import get_supabase

async def log_request(
    user_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    latency_ms: int,
    status_code: int,
    api_key_id: str = None,
    error_message: str = None,
    metadata: dict = None,
    is_streaming: bool = False,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
):
    """
    Log request to database (fire-and-forget)
    """
    log_data = {
        "user_id": user_id,
        "api_key_id": api_key_id,
        "provider": provider,
        "model": model,
        "request_tokens": input_tokens,
        "response_tokens": output_tokens,
        "cost_usd": cost,
        "latency_ms": latency_ms,
        "status_code": status_code,
        "error_message": error_message,
        "metadata": metadata or {},
        "is_streaming": is_streaming,
        "cache_creation_tokens": cache_creation_tokens,
        "cache_read_tokens": cache_read_tokens,
    }
    
    try:
        supabase = get_supabase()
        supabase.table("api_logs").insert(log_data).execute()
    except Exception as e:
        # Don't fail the request if logging fails
        print(f"[LOG ERROR] {datetime.utcnow().isoformat()} - {e}")
        print(f"[LOG DATA] {json.dumps(log_data)}")

def structured_log(level: str, message: str, **kwargs):
    """Print structured log to stdout (Vercel captures this)"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "message": message,
        **kwargs
    }
    print(json.dumps(log_entry))
