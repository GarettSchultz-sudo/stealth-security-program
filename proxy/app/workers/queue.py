"""ARQ-based job queue for background scanning tasks."""

import asyncio
import logging
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global redis pool
_redis_pool = None


async def get_redis_pool():
    """Get or create the Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        # Parse Redis URL (redis://host:port/db or Upstash REST URL)
        redis_url = settings.redis_url

        if redis_url.startswith("http"):
            # Upstash Redis REST - need to use different approach
            # For ARQ, we need native Redis connection
            # Extract host from REST URL for now
            # Format: https://xxx.upstash.io -> host=xxx.upstash.io
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            host = parsed.netloc
            # Fall back to localhost for development
            redis_settings = RedisSettings(host="localhost", port=6379, database=0)
        else:
            # Parse redis://host:port/db format
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            redis_settings = RedisSettings(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                database=int(parsed.path.lstrip("/")) if parsed.path else 0,
            )

        _redis_pool = await create_pool(redis_settings)
    return _redis_pool


async def startup(ctx: dict[str, Any]) -> None:
    """Startup hook for worker - initialize resources."""
    ctx["redis"] = await get_redis_pool()
    ctx["settings"] = settings
    logger.info("Scanner worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Shutdown hook for worker - cleanup resources."""
    logger.info("Scanner worker shutting down")


async def scan_task(ctx: dict[str, Any], scan_id: str, target: str, profile: str, scan_type: str) -> dict:
    """
    Background task to execute a security scan.

    Args:
        ctx: Worker context
        scan_id: UUID of the scan record
        target: Target to scan (URL, image, cloud account)
        profile: Scan profile (quick, standard, deep, comprehensive)
        scan_type: Type of scan (url, container, repo, cloud)

    Returns:
        Dict with scan results
    """
    from app.workers.scanner_worker import run_scan

    logger.info(f"Starting scan {scan_id} for {target} (type={scan_type}, profile={profile})")

    try:
        result = await run_scan(
            scan_id=scan_id,
            target=target,
            profile=profile,
            scan_type=scan_type,
            settings=ctx["settings"],
        )
        logger.info(f"Scan {scan_id} completed with {result.get('findings_count', 0)} findings")
        return result
    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        raise


async def enqueue_scan(scan_id: str, target: str, profile: str, scan_type: str) -> Job:
    """
    Enqueue a scan job for background processing.

    Args:
        scan_id: UUID of the scan record
        target: Target to scan
        profile: Scan profile
        scan_type: Type of scan

    Returns:
        Job object
    """
    pool = await get_redis_pool()
    job = await pool.enqueue_job(
        "scan_task",
        scan_id,
        target,
        profile,
        scan_type,
        _job_timeout=600,  # 10 minute timeout
        _job_try=3,  # Retry up to 3 times
    )
    return job


class WorkerSettings:
    """ARQ worker settings."""

    functions = [scan_task]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 600  # 10 minutes
    keep_result = 3600  # Keep results for 1 hour
