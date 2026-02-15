"""
Upstash Redis Client for Rate Limiting and Caching
"""
from upstash_redis import Redis
import os
import json

_redis = None

def get_redis():
    """Get or create Redis client singleton"""
    global _redis
    if _redis is None:
        _redis = Redis(
            url=os.environ["UPSTASH_REDIS_REST_URL"],
            token=os.environ["UPSTASH_REDIS_REST_TOKEN"]
        )
    return _redis

async def check_rate_limit(api_key_hash: str, limit: int = 1000, window: int = 60) -> tuple[bool, int]:
    """
    Sliding window rate limiting
    Returns: (is_allowed, remaining_requests)
    """
    redis = get_redis()
    key = f"ratelimit:{api_key_hash}:{window}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window)
    return (current <= limit, max(0, limit - current))

async def get_cached_budget(user_id: str, budget_id: str = None) -> dict | None:
    """Cache budget checks to reduce DB load"""
    redis = get_redis()
    key = f"budget:{user_id}:{budget_id or 'global'}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    return None

async def set_cached_budget(user_id: str, budget_data: dict, ttl: int = 30, budget_id: str = None):
    """Cache budget data with TTL"""
    redis = get_redis()
    key = f"budget:{user_id}:{budget_id or 'global'}"
    await redis.setex(key, ttl, json.dumps(budget_data))

async def increment_spend_cache(user_id: str, amount: float, budget_id: str = None):
    """Increment cached spend counter"""
    redis = get_redis()
    key = f"spend:{user_id}:{budget_id or 'global'}"
    await redis.incrbyfloat(key, amount)
