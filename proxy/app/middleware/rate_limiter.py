"""Rate limiting middleware for API endpoints.

Uses Redis-based sliding window algorithm for rate limiting.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests: int
    window_seconds: int
    key_prefix: str = "ratelimit"


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    Usage:
        limiter = RateLimiter(redis_client)
        allowed = await limiter.check("user:123", limit=100, window=60)
    """

    def __init__(self, redis_client, key_prefix: str = "ratelimit"):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for rate limit keys
        """
        self.redis = redis_client
        self.key_prefix = key_prefix

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (e.g., user ID, IP address)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        full_key = f"{self.key_prefix}:{key}"
        now = time.time()
        window_start = now - window_seconds

        try:
            # Use Redis pipeline for atomic operations
            async with self.redis.pipeline() as pipe:
                # Remove old entries outside the window
                pipe.zremrangebyscore(full_key, 0, window_start)

                # Count current entries
                pipe.zcard(full_key)

                # Execute pipeline
                results = await pipe.execute()

            current_count = results[1] if len(results) > 1 else 0

            if current_count >= limit:
                # Rate limit exceeded
                retry_after = int(window_seconds - (now - window_start))
                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset": int(now + window_seconds),
                    "retry_after": retry_after,
                }

            # Add new request
            await self.redis.zadd(full_key, {str(now): now})
            await self.redis.expire(full_key, window_seconds)

            return True, {
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset": int(now + window_seconds),
            }

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request on error (fail open)
            return True, {"limit": limit, "remaining": limit, "reset": 0}

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        full_key = f"{self.key_prefix}:{key}"
        await self.redis.delete(full_key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Supports multiple rate limit tiers:
    - Global rate limit (all requests)
    - Per-IP rate limit
    - Per-user rate limit (if authenticated)

    Usage:
        app.add_middleware(
            RateLimitMiddleware,
            redis_client=redis,
            global_limit=RateLimit(requests=10000, window_seconds=60),
            ip_limit=RateLimit(requests=100, window_seconds=60),
            user_limit=RateLimit(requests=500, window_seconds=60),
        )
    """

    def __init__(
        self,
        app,
        redis_client=None,
        global_limit: Optional[RateLimit] = None,
        ip_limit: Optional[RateLimit] = None,
        user_limit: Optional[RateLimit] = None,
        exclude_paths: Optional[list[str]] = None,
        get_user_id: Optional[Callable] = None,
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            redis_client: Redis client (can be set later via app.state)
            global_limit: Global rate limit
            ip_limit: Per-IP rate limit
            user_limit: Per-user rate limit
            exclude_paths: Paths to exclude from rate limiting
            get_user_id: Async function to extract user ID from request
        """
        super().__init__(app)
        self.redis = redis_client
        self.global_limit = global_limit or RateLimit(requests=10000, window_seconds=60)
        self.ip_limit = ip_limit or RateLimit(requests=100, window_seconds=60)
        self.user_limit = user_limit or RateLimit(requests=500, window_seconds=60)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.get_user_id = get_user_id

    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiter."""

        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get Redis client
        redis = self.redis or getattr(request.app.state, "redis", None)
        if not redis:
            # No Redis available, skip rate limiting
            return await call_next(request)

        limiter = RateLimiter(redis)

        # Check global rate limit
        allowed, info = await limiter.check(
            "global",
            self.global_limit.requests,
            self.global_limit.window_seconds,
        )
        if not allowed:
            return self._rate_limit_response(info, "Global rate limit exceeded")

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check IP rate limit
        allowed, info = await limiter.check(
            f"ip:{client_ip}",
            self.ip_limit.requests,
            self.ip_limit.window_seconds,
        )
        if not allowed:
            return self._rate_limit_response(info, "Rate limit exceeded")

        # Check user rate limit if authenticated
        user_id = None
        if self.get_user_id:
            try:
                user_id = await self.get_user_id(request)
            except Exception:
                pass

        if user_id:
            allowed, info = await limiter.check(
                f"user:{user_id}",
                self.user_limit.requests,
                self.user_limit.window_seconds,
            )
            if not allowed:
                return self._rate_limit_response(info, "User rate limit exceeded")

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(info.get("reset", 0))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to client host
        if request.client:
            return request.client.host

        return "unknown"

    def _rate_limit_response(self, info: dict, message: str) -> JSONResponse:
        """Create rate limit exceeded response."""
        response = JSONResponse(
            status_code=429,
            content={
                "detail": message,
                "limit": info.get("limit"),
                "remaining": info.get("remaining", 0),
                "reset": info.get("reset"),
                "retry_after": info.get("retry_after"),
            },
        )
        response.headers["Retry-After"] = str(info.get("retry_after", 60))
        response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(info.get("reset", 0))
        return response


# Scan-specific rate limits
SCAN_RATE_LIMITS = {
    # Per scan type limits
    "quick": RateLimit(requests=60, window_seconds=60),      # 1/minute
    "standard": RateLimit(requests=30, window_seconds=60),   # 0.5/minute
    "deep": RateLimit(requests=10, window_seconds=60),       # 1/6 minutes
    "comprehensive": RateLimit(requests=5, window_seconds=60),  # 1/12 minutes
}


async def check_scan_rate_limit(
    redis_client,
    user_id: str,
    profile: str = "standard",
) -> tuple[bool, dict]:
    """
    Check rate limit for scan requests.

    Args:
        redis_client: Redis client
        user_id: User ID
        profile: Scan profile (quick, standard, deep, comprehensive)

    Returns:
        Tuple of (allowed, info)
    """
    limiter = RateLimiter(redis_client, prefix="scanlimit")

    # Get profile-specific limit
    rate_limit = SCAN_RATE_LIMITS.get(profile, SCAN_RATE_LIMITS["standard"])

    return await limiter.check(
        f"user:{user_id}:{profile}",
        rate_limit.requests,
        rate_limit.window_seconds,
    )
