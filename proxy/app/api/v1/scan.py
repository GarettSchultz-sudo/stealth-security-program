"""API endpoint for executing real security scans."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from redis import asyncio as aioredis

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scanning"])


async def get_redis():
    """Get Redis client for progress tracking."""
    settings = get_settings()
    redis_url = settings.redis_url

    if redis_url.startswith("http"):
        # Upstash REST - use aioredis compatible URL
        from upstash_redis.asyncio import Redis as UpstashRedis
        return UpstashRedis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
        )
    else:
        return await aioredis.from_url(redis_url)


class ScanRequest(BaseModel):
    """Request to start a scan."""
    scan_id: str
    target: str
    profile: str = "standard"
    scan_type: str | None = None


class ScanStatusResponse(BaseModel):
    """Response for scan status."""
    scan_id: str
    status: str
    trust_score: int | None = None
    risk_level: str | None = None
    findings_count: int = 0
    message: str = ""


async def execute_scan_task(scan_id: str, target: str, profile: str, scan_type: str | None):
    """
    Background task to execute a real security scan.

    This is called by the background task runner and updates the database directly.
    Includes progress tracking for real-time UI updates.
    """
    from app.workers.scanner_worker import run_scan, ScanType
    from app.models.database import AsyncSessionLocal
    from app.services.progress_tracker import ProgressTracker
    from sqlalchemy import text

    redis = None
    tracker = None

    try:
        # Initialize Redis for progress tracking
        redis = await get_redis()
        tracker = ProgressTracker(redis, scan_id)
        await tracker.start()

        # Run the actual scan
        result = await run_scan(
            scan_id=scan_id,
            target=target,
            profile=profile,
            scan_type=scan_type,
            settings=get_settings(),
        )

        # Complete progress tracking
        await tracker.complete(
            findings_count=result.get("findings_count", 0),
            files_scanned=result.get("files_scanned", 0),
            patterns_checked=result.get("patterns_checked", 0),
        )

        # Update database with results
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE skill_scans
                    SET status = :status,
                        trust_score = :trust_score,
                        risk_level = :risk_level,
                        recommendation = :recommendation,
                        files_scanned = :files_scanned,
                        patterns_checked = :patterns_checked,
                        scan_duration_ms = :scan_duration_ms,
                        completed_at = NOW()
                    WHERE id = :scan_id
                """),
                {
                    "scan_id": scan_id,
                    "status": result["status"],
                    "trust_score": result["trust_score"],
                    "risk_level": result["risk_level"],
                    "recommendation": result["recommendation"],
                    "files_scanned": result["files_scanned"],
                    "patterns_checked": result["patterns_checked"],
                    "scan_duration_ms": result["scan_duration_ms"],
                },
            )
            await session.commit()

            # Insert findings
            for finding in result.get("findings", []):
                await session.execute(
                    text("""
                        INSERT INTO skill_findings (
                            scan_id, pattern_type, severity, description,
                            confidence, created_at
                        ) VALUES (
                            :scan_id, :pattern_type, :severity, :description,
                            :confidence, NOW()
                        )
                    """),
                    {
                        "scan_id": scan_id,
                        "pattern_type": finding.get("check_id", finding.get("pattern_type", "unknown")),
                        "severity": finding.get("severity", "info"),
                        "description": finding.get("title", finding.get("description", "")),
                        "confidence": finding.get("confidence", 1.0),
                    },
                )
            await session.commit()

        logger.info(f"Scan {scan_id} completed with {result.get('findings_count', 0)} findings")

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")

        # Update progress tracker
        if tracker:
            await tracker.fail(str(e))

        # Update scan status to failed
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE skill_scans
                    SET status = 'failed',
                        completed_at = NOW()
                    WHERE id = :scan_id
                """),
                {"scan_id": scan_id},
            )
            await session.commit()

    finally:
        if redis:
            await redis.close()


@router.post("/execute")
async def execute_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Execute a real security scan in the background.

    This endpoint is called by the dashboard to start a scan.
    The scan runs in a background task and updates the database when complete.
    """
    logger.info(f"Starting scan {request.scan_id} for {request.target}")

    # Queue the scan as a background task
    background_tasks.add_task(
        execute_scan_task,
        scan_id=request.scan_id,
        target=request.target,
        profile=request.profile,
        scan_type=request.scan_type,
    )

    return {
        "scan_id": request.scan_id,
        "status": "pending",
        "message": "Scan started successfully",
    }


@router.get("/status/{scan_id}")
async def get_scan_status(scan_id: str) -> ScanStatusResponse:
    """Get the status of a scan."""
    from app.models.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, status, trust_score, risk_level, recommendation
                FROM skill_scans
                WHERE id = :scan_id
            """),
            {"scan_id": scan_id},
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Scan not found")

        return ScanStatusResponse(
            scan_id=str(row[0]),
            status=row[1] or "pending",
            trust_score=row[2],
            risk_level=row[3],
            findings_count=0,  # Would need to count from skill_findings
            message="Scan in progress" if row[1] == "pending" else "Scan completed",
        )


@router.get("/progress/{scan_id}")
async def get_scan_progress(scan_id: str) -> dict[str, Any]:
    """
    Get real-time scan progress from Redis.

    This endpoint is polled by the SSE endpoint or can be called directly.
    """
    from app.services.progress_tracker import ProgressTracker

    redis = await get_redis()
    try:
        progress = await ProgressTracker.get(redis, scan_id)

        if not progress:
            # Fallback to database status
            from app.models.database import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("SELECT status FROM skill_scans WHERE id = :scan_id"),
                    {"scan_id": scan_id},
                )
                row = result.fetchone()

                if not row:
                    raise HTTPException(status_code=404, detail="Scan not found")

                return {
                    "scan_id": scan_id,
                    "status": row[0] or "pending",
                    "progress": 0,
                    "message": "Waiting for scan to start...",
                }

        return {
            "scan_id": scan_id,
            "status": progress.status,
            "phase": progress.phase,
            "progress": progress.progress,
            "message": progress.message,
            "findings_count": progress.findings_count,
            "files_scanned": progress.files_scanned,
            "patterns_checked": progress.patterns_checked,
            "current_tool": progress.current_tool,
            "estimated_time_remaining": progress.estimated_time_remaining,
            "error": progress.error,
        }

    finally:
        await redis.close()
