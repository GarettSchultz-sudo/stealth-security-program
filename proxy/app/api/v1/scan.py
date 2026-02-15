"""API endpoint for executing real security scans."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scanning"])


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
    """
    from app.workers.scanner_worker import run_scan, ScanType
    from app.models.database import AsyncSessionLocal
    from sqlalchemy import text

    try:
        # Run the actual scan
        result = await run_scan(
            scan_id=scan_id,
            target=target,
            profile=profile,
            scan_type=scan_type,
            settings=get_settings(),
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
                        "pattern_type": finding["check_id"],
                        "severity": finding["severity"],
                        "description": finding["title"],
                        "confidence": finding.get("confidence", 1.0),
                    },
                )
            await session.commit()

        logger.info(f"Scan {scan_id} completed with {result['findings_count']} findings")

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
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
