"""
ClawShell Scan API Routes - Security Scanning for OpenClaw Skills

Endpoints:
- POST /scan - Initiate a skill scan
- GET /scan/{scan_id} - Get scan status and results
- GET /trust/{skill_id} - Get trust score for a skill
- POST /monitoring/{skill_id} - Start monitoring a skill
- GET /monitoring - List monitored skills
- POST /compliance - Generate compliance report
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# Using Supabase client for database operations
from _lib.db import get_supabase
from _lib.auth import get_current_user
from _lib.redis import get_redis

router = APIRouter(prefix="/scan", tags=["scan"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ScanRequest(BaseModel):
    """Request to scan a ClawHub skill."""

    skill_id: str = Field(..., description="ClawHub skill identifier")
    profile: str = Field(default="standard", description="Scan profile: quick, standard, deep, comprehensive")
    skill_url: Optional[str] = Field(None, description="URL to fetch skill from if not cached")


class ScanResponse(BaseModel):
    """Response from scan initiation."""

    scan_id: str
    status: str
    message: str


class ScanResultResponse(BaseModel):
    """Full scan result response."""

    id: str
    skill_id: str
    skill_name: str
    status: str
    profile: str
    trust_score: Optional[int]
    risk_level: Optional[str]
    recommendation: Optional[str]
    findings: list[dict]
    scan_duration_ms: Optional[int]
    files_scanned: int
    patterns_checked: int
    created_at: str
    completed_at: Optional[str]


class TrustScoreResponse(BaseModel):
    """Trust score for a skill."""

    skill_id: str
    skill_name: str
    overall_score: int
    risk_level: str
    recommendation: str
    components: dict
    valid_until: Optional[str]
    last_scan_at: Optional[str]


class MonitoringRequest(BaseModel):
    """Request to start monitoring a skill."""

    skill_id: str
    check_interval_seconds: int = Field(default=3600, ge=300, le=86400)
    alert_on_critical: bool = True
    alert_on_high: bool = True
    alert_on_new_findings: bool = True
    alert_channels: dict = Field(default_factory=lambda: {"email": True})


class MonitoringResponse(BaseModel):
    """Monitoring status response."""

    id: str
    skill_id: str
    status: str
    check_interval_seconds: int
    last_check_at: Optional[str]
    next_check_at: Optional[str]
    baseline_trust_score: Optional[int]
    findings_detected: int
    alerts_sent: int


class ComplianceReportRequest(BaseModel):
    """Request to generate a compliance report."""

    framework: str = Field(..., description="SOC2, ISO27001, HIPAA, PCI_DSS, GDPR, NIST_CSF")
    skill_ids: list[str] = Field(default_factory=list, description="Skills to include (empty = all monitored)")
    report_period_days: int = Field(default=30, ge=1, le=365)


class ComplianceReportResponse(BaseModel):
    """Compliance report response."""

    id: str
    framework: str
    overall_status: str
    controls_evaluated: int
    controls_passed: int
    controls_failed: int
    generated_at: str
    report_url: Optional[str]


# ============================================================================
# Scan Endpoints
# ============================================================================


@router.post("/scan", response_model=ScanResponse)
async def initiate_scan(
    request: ScanRequest,
    user: dict = Depends(get_current_user),
) -> ScanResponse:
    """Initiate a security scan of a ClawHub skill."""
    supabase = get_supabase()
    redis = get_redis()
    user_id = user["id"]

    # Check user has enough credits
    credits = await _check_credits(supabase, user_id, request.profile)
    if not credits["has_credits"]:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient scan credits. Need {credits['cost']}, have {credits['remaining']}",
        )

    # Check if skill exists in our registry
    skill = await _get_or_create_skill(supabase, request.skill_id, request.skill_url)

    # Create scan record
    scan_id = str(uuid4())
    scan_data = {
        "id": scan_id,
        "user_id": user_id,
        "skill_id": skill["id"],
        "profile": request.profile,
        "status": "pending",
        "files_scanned": 0,
        "patterns_checked": 0,
    }

    supabase.table("skill_scans").insert(scan_data).execute()

    # Queue scan job (using Redis as simple queue)
    job = {
        "scan_id": scan_id,
        "skill_id": skill["id"],
        "skill_clawhub_id": request.skill_id,
        "profile": request.profile,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
    }
    await redis.lpush("clawshell:scan_queue", json.dumps(job))

    return ScanResponse(
        scan_id=scan_id,
        status="pending",
        message="Scan queued successfully",
    )


@router.get("/scan/{scan_id}", response_model=ScanResultResponse)
async def get_scan_result(
    scan_id: str,
    user: dict = Depends(get_current_user),
) -> ScanResultResponse:
    """Get the status and results of a scan."""
    supabase = get_supabase()
    user_id = user["id"]

    # Get scan record
    result = (
        supabase.table("skill_scans")
        .select("*, clawhub_skills(*)")
        .eq("id", scan_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan = result.data

    # Get findings if scan is completed
    findings = []
    if scan["status"] == "completed":
        findings_result = (
            supabase.table("skill_findings")
            .select("*")
            .eq("scan_id", scan_id)
            .execute()
        )
        findings = findings_result.data or []

    skill = scan.get("clawhub_skills", {})

    return ScanResultResponse(
        id=scan["id"],
        skill_id=skill.get("skill_id", "unknown"),
        skill_name=skill.get("name", "unknown"),
        status=scan["status"],
        profile=scan["profile"],
        trust_score=scan.get("trust_score"),
        risk_level=scan.get("risk_level"),
        recommendation=scan.get("recommendation"),
        findings=findings,
        scan_duration_ms=scan.get("scan_duration_ms"),
        files_scanned=scan.get("files_scanned", 0),
        patterns_checked=scan.get("patterns_checked", 0),
        created_at=scan["created_at"],
        completed_at=scan.get("completed_at"),
    )


@router.get("/scans")
async def list_scans(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict:
    """List user's scans."""
    supabase = get_supabase()
    user_id = user["id"]

    query = (
        supabase.table("skill_scans")
        .select("id, created_at, status, profile, trust_score, risk_level, clawhub_skills(skill_id, name)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()

    return {
        "scans": result.data or [],
        "limit": limit,
        "offset": offset,
    }


# ============================================================================
# Trust Score Endpoints
# ============================================================================


@router.get("/trust/{skill_id}", response_model=TrustScoreResponse)
async def get_trust_score(
    skill_id: str,
    refresh: bool = Query(default=False, description="Force refresh of trust score"),
) -> TrustScoreResponse:
    """Get the trust score for a skill (public endpoint)."""
    supabase = get_supabase()

    # Get skill
    skill_result = (
        supabase.table("clawhub_skills")
        .select("*")
        .eq("skill_id", skill_id)
        .single()
        .execute()
    )

    if not skill_result.data:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = skill_result.data

    # Get latest trust score
    trust_result = (
        supabase.table("trust_scores")
        .select("*")
        .eq("skill_id", skill["id"])
        .gte("valid_until", datetime.utcnow().isoformat())
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if trust_result.data and not refresh:
        trust = trust_result.data[0]
        return TrustScoreResponse(
            skill_id=skill_id,
            skill_name=skill["name"],
            overall_score=trust["overall_score"],
            risk_level=trust["risk_level"],
            recommendation=_score_to_recommendation(trust["overall_score"]),
            components={
                "code_quality": trust.get("code_quality_score"),
                "author_reputation": trust.get("author_reputation_score"),
                "community_validation": trust.get("community_validation_score"),
                "security_posture": trust.get("security_posture_score"),
                "behavior_profile": trust.get("behavior_profile_score"),
            },
            valid_until=trust.get("valid_until"),
            last_scan_at=trust.get("created_at"),
        )

    # If no valid trust score, return default
    return TrustScoreResponse(
        skill_id=skill_id,
        skill_name=skill["name"],
        overall_score=50,
        risk_level="medium",
        recommendation="caution",
        components={
            "code_quality": None,
            "author_reputation": None,
            "community_validation": None,
            "security_posture": None,
            "behavior_profile": None,
        },
        valid_until=None,
        last_scan_at=None,
    )


# ============================================================================
# Monitoring Endpoints
# ============================================================================


@router.post("/monitoring", response_model=MonitoringResponse)
async def start_monitoring(
    request: MonitoringRequest,
    user: dict = Depends(get_current_user),
) -> MonitoringResponse:
    """Start monitoring a skill for security changes."""
    supabase = get_supabase()
    user_id = user["id"]

    # Get or create skill
    skill = await _get_or_create_skill(supabase, request.skill_id, None)

    # Check if already monitoring
    existing = (
        supabase.table("monitored_skills")
        .select("*")
        .eq("user_id", user_id)
        .eq("skill_id", skill["id"])
        .execute()
    )

    if existing.data:
        # Update existing monitoring
        update_data = {
            "status": "active",
            "check_interval_seconds": request.check_interval_seconds,
            "alert_on_critical": request.alert_on_critical,
            "alert_on_high": request.alert_on_high,
            "alert_on_new_findings": request.alert_on_new_findings,
            "alert_channels": request.alert_channels,
            "next_check_at": datetime.utcnow().isoformat(),
        }
        result = (
            supabase.table("monitored_skills")
            .update(update_data)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
        monitor = result.data[0]
    else:
        # Create new monitoring
        monitor_data = {
            "user_id": user_id,
            "skill_id": skill["id"],
            "status": "active",
            "check_interval_seconds": request.check_interval_seconds,
            "alert_on_critical": request.alert_on_critical,
            "alert_on_high": request.alert_on_high,
            "alert_on_new_findings": request.alert_on_new_findings,
            "alert_channels": request.alert_channels,
            "next_check_at": datetime.utcnow().isoformat(),
        }
        result = supabase.table("monitored_skills").insert(monitor_data).execute()
        monitor = result.data[0]

    return MonitoringResponse(
        id=monitor["id"],
        skill_id=request.skill_id,
        status=monitor["status"],
        check_interval_seconds=monitor["check_interval_seconds"],
        last_check_at=monitor.get("last_check_at"),
        next_check_at=monitor.get("next_check_at"),
        baseline_trust_score=monitor.get("baseline_trust_score"),
        findings_detected=monitor.get("findings_detected", 0),
        alerts_sent=monitor.get("alerts_sent", 0),
    )


@router.get("/monitoring")
async def list_monitored_skills(
    user: dict = Depends(get_current_user),
) -> list[MonitoringResponse]:
    """List all monitored skills for the user."""
    supabase = get_supabase()
    user_id = user["id"]

    result = (
        supabase.table("monitored_skills")
        .select("*, clawhub_skills(skill_id, name)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    monitored = []
    for m in result.data or []:
        skill = m.get("clawhub_skills", {})
        monitored.append(
            MonitoringResponse(
                id=m["id"],
                skill_id=skill.get("skill_id", "unknown"),
                status=m["status"],
                check_interval_seconds=m["check_interval_seconds"],
                last_check_at=m.get("last_check_at"),
                next_check_at=m.get("next_check_at"),
                baseline_trust_score=m.get("baseline_trust_score"),
                findings_detected=m.get("findings_detected", 0),
                alerts_sent=m.get("alerts_sent", 0),
            )
        )

    return monitored


@router.delete("/monitoring/{monitor_id}")
async def stop_monitoring(
    monitor_id: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Stop monitoring a skill."""
    supabase = get_supabase()
    user_id = user["id"]

    result = (
        supabase.table("monitored_skills")
        .update({"status": "disabled"})
        .eq("id", monitor_id)
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Monitoring not found")

    return {"status": "disabled", "message": "Monitoring stopped"}


# ============================================================================
# Compliance Endpoints
# ============================================================================


@router.post("/compliance", response_model=ComplianceReportResponse)
async def generate_compliance_report(
    request: ComplianceReportRequest,
    user: dict = Depends(get_current_user),
) -> ComplianceReportResponse:
    """Generate a compliance report for monitored skills."""
    supabase = get_supabase()
    user_id = user["id"]

    # Validate framework
    valid_frameworks = ["SOC2", "ISO27001", "HIPAA", "PCI_DSS", "GDPR", "NIST_CSF"]
    if request.framework not in valid_frameworks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid framework. Must be one of: {valid_frameworks}",
        )

    # Get skills to include
    if request.skill_ids:
        skills_result = (
            supabase.table("clawhub_skills")
            .select("id")
            .in_("skill_id", request.skill_ids)
            .execute()
        )
        skill_ids = [s["id"] for s in skills_result.data or []]
    else:
        # Get all monitored skills
        monitored_result = (
            supabase.table("monitored_skills")
            .select("skill_id")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )
        skill_ids = [m["skill_id"] for m in monitored_result.data or []]

    if not skill_ids:
        raise HTTPException(
            status_code=400,
            detail="No skills to include in report",
        )

    # Create report record
    report_id = str(uuid4())
    report_data = {
        "id": report_id,
        "user_id": user_id,
        "framework": request.framework,
        "skill_ids": skill_ids,
        "overall_status": "partially_compliant",  # Will be updated by worker
        "report_period_start": (datetime.utcnow() - timedelta(days=request.report_period_days)).isoformat(),
        "report_period_end": datetime.utcnow().isoformat(),
    }

    result = supabase.table("compliance_reports").insert(report_data).execute()

    # Queue report generation job
    redis = get_redis()
    job = {
        "report_id": report_id,
        "framework": request.framework,
        "skill_ids": skill_ids,
        "user_id": user_id,
    }
    await redis.lpush("clawshell:compliance_queue", json.dumps(job))

    return ComplianceReportResponse(
        id=report_id,
        framework=request.framework,
        overall_status="pending",
        controls_evaluated=0,
        controls_passed=0,
        controls_failed=0,
        generated_at=datetime.utcnow().isoformat(),
        report_url=None,
    )


@router.get("/compliance")
async def list_compliance_reports(
    user: dict = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List user's compliance reports."""
    supabase = get_supabase()
    user_id = user["id"]

    result = (
        supabase.table("compliance_reports")
        .select("*")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {"reports": result.data or []}


# ============================================================================
# Credits Endpoints
# ============================================================================


@router.get("/credits")
async def get_scan_credits(
    user: dict = Depends(get_current_user),
) -> dict:
    """Get user's current scan credits."""
    supabase = get_supabase()
    user_id = user["id"]

    result = (
        supabase.table("scan_credits")
        .select("*")
        .eq("user_id", user_id)
        .gte("period_end", datetime.utcnow().isoformat())
        .order("period_start", desc=True)
        .limit(1)
        .execute()
    )

    if result.data:
        credits = result.data[0]
        return {
            "total_credits": credits["total_credits"],
            "used_credits": credits["used_credits"],
            "remaining_credits": credits["total_credits"] - credits["used_credits"],
            "period_end": credits["period_end"],
            "scan_costs": {
                "quick": credits.get("quick_scan_cost", 1),
                "standard": credits.get("standard_scan_cost", 2),
                "deep": credits.get("deep_scan_cost", 5),
                "comprehensive": credits.get("comprehensive_scan_cost", 10),
            },
        }

    # Default free tier
    return {
        "total_credits": 50,
        "used_credits": 0,
        "remaining_credits": 50,
        "period_end": None,
        "scan_costs": {
            "quick": 1,
            "standard": 2,
            "deep": 5,
            "comprehensive": 10,
        },
    }


# ============================================================================
# Helper Functions
# ============================================================================


async def _check_credits(supabase, user_id: str, profile: str) -> dict:
    """Check if user has enough credits for a scan."""
    costs = {
        "quick": 1,
        "standard": 2,
        "deep": 5,
        "comprehensive": 10,
    }
    cost = costs.get(profile, 2)

    result = (
        supabase.table("scan_credits")
        .select("*")
        .eq("user_id", user_id)
        .gte("period_end", datetime.utcnow().isoformat())
        .order("period_start", desc=True)
        .limit(1)
        .execute()
    )

    if result.data:
        credits = result.data[0]
        remaining = credits["total_credits"] - credits["used_credits"]
        return {
            "has_credits": remaining >= cost,
            "cost": cost,
            "remaining": remaining,
        }

    # Free tier: 50 credits
    return {
        "has_credits": 50 >= cost,
        "cost": cost,
        "remaining": 50,
    }


async def _get_or_create_skill(
    supabase, skill_id: str, skill_url: Optional[str]
) -> dict:
    """Get skill from registry or create if not exists."""
    result = (
        supabase.table("clawhub_skills")
        .select("*")
        .eq("skill_id", skill_id)
        .single()
        .execute()
    )

    if result.data:
        return result.data

    # Create new skill record
    skill_data = {
        "skill_id": skill_id,
        "name": skill_id,  # Will be updated by worker
        "clawhub_url": skill_url,
    }

    result = supabase.table("clawhub_skills").insert(skill_data).execute()
    return result.data[0]


def _score_to_recommendation(score: int) -> str:
    """Convert score to recommendation."""
    if score >= 70:
        return "safe"
    elif score >= 50:
        return "caution"
    else:
        return "avoid"


import json  # Add import at top
