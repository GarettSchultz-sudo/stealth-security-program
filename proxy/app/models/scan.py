"""ClawShell Scan models for security scanning."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ScanStatus(str, enum.Enum):
    """Status of a skill scan."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanProfile(str, enum.Enum):
    """Scan depth profiles."""

    QUICK = "quick"  # Basic checks only
    STANDARD = "standard"  # Standard security scan
    DEEP = "deep"  # Deep analysis with SAST
    COMPREHENSIVE = "comprehensive"  # Full scan with external APIs


class RiskLevel(str, enum.Enum):
    """Risk assessment levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingSeverity(str, enum.Enum):
    """Severity levels for findings."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingType(str, enum.Enum):
    """Types of security findings."""

    VULNERABILITY = "vulnerability"
    MALWARE = "malware"
    SECRET = "secret"
    MISCONFIGURATION = "misconfiguration"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    PERMISSION_ISSUE = "permission_issue"
    LICENSE_ISSUE = "license_issue"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"


class FindingStatus(str, enum.Enum):
    """Status of a finding."""

    OPEN = "open"
    CONFIRMED = "confirmed"
    FIXED = "fixed"
    SUPPRESSED = "suppressed"
    FALSE_POSITIVE = "false_positive"


class MonitorStatus(str, enum.Enum):
    """Status of skill monitoring."""

    ACTIVE = "active"
    PAUSED = "paused"
    ALERTED = "alerted"
    DISABLED = "disabled"


class ComplianceFramework(str, enum.Enum):
    """Supported compliance frameworks."""

    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    HIPAA = "HIPAA"
    PCI_DSS = "PCI_DSS"
    GDPR = "GDPR"
    NIST_CSF = "NIST_CSF"
    CUSTOM = "CUSTOM"


class ComplianceStatus(str, enum.Enum):
    """Compliance assessment status."""

    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"


class ClawHubSkill(BaseModel):
    """Registry of ClawHub skills."""

    __tablename__ = "clawhub_skills"

    skill_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    package_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    permissions: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    clawhub_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    scans: Mapped[list["SkillScan"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    trust_score: Mapped["TrustScore | None"] = relationship(back_populates="skill", uselist=False)
    monitored_by: Mapped[list["MonitoredSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


class SkillScan(BaseModel):
    """Security scan of a ClawHub skill."""

    __tablename__ = "skill_scans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clawhub_skills.id"), nullable=False, index=True
    )

    # Scan configuration
    profile: Mapped[ScanProfile] = mapped_column(
        Enum(ScanProfile), default=ScanProfile.STANDARD, nullable=False
    )
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False
    )

    # Results
    trust_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Scan details
    scan_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    files_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    patterns_checked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # External API results
    virustotal_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snyk_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Scan metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    scan_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    skill: Mapped["ClawHubSkill"] = relationship(back_populates="scans")
    findings: Mapped[list["SkillFinding"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan"
    )


class SkillFinding(BaseModel):
    """Individual security finding from a scan."""

    __tablename__ = "skill_findings"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill_scans.id"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clawhub_skills.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Finding details
    finding_type: Mapped[FindingType] = mapped_column(Enum(FindingType), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(Enum(FindingSeverity), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Location
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    cwe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cve: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cvss_score: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)

    # Pattern matched
    pattern_matched: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Remediation
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    references: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    # Status
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus), default=FindingStatus.OPEN, nullable=False
    )
    suppressed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suppressed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    suppress_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    scan: Mapped["SkillScan"] = relationship(back_populates="findings")


class TrustScore(BaseModel):
    """Computed trust score for a skill."""

    __tablename__ = "trust_scores"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clawhub_skills.id"), nullable=False, unique=True, index=True
    )

    # Overall score
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)

    # Component scores (weighted)
    code_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author_reputation_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    community_validation_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    security_posture_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    behavior_profile_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Breakdown
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Validity
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Latest scan reference
    latest_scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill_scans.id"), nullable=True
    )

    # Relationships
    skill: Mapped["ClawHubSkill"] = relationship(back_populates="trust_score")


class MonitoredSkill(BaseModel):
    """User's monitored skills for real-time protection."""

    __tablename__ = "monitored_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_monitored_skill_user_skill"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clawhub_skills.id"), nullable=False, index=True
    )

    # Monitoring configuration
    status: Mapped[MonitorStatus] = mapped_column(
        Enum(MonitorStatus), default=MonitorStatus.ACTIVE, nullable=False
    )
    check_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Alert configuration
    alert_on_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alert_on_high: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alert_on_new_findings: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alert_channels: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Baseline
    baseline_trust_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_finding_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Statistics
    total_checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alerts_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    skill: Mapped["ClawHubSkill"] = relationship(back_populates="monitored_by")


class ComplianceReport(BaseModel):
    """Compliance report for skill security."""

    __tablename__ = "compliance_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Report details
    framework: Mapped[ComplianceFramework] = mapped_column(
        Enum(ComplianceFramework), nullable=False
    )
    framework_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    report_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Scope
    skill_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )

    # Results
    overall_status: Mapped[ComplianceStatus | None] = mapped_column(
        Enum(ComplianceStatus), nullable=True
    )
    controls_evaluated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    controls_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    controls_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Detailed results
    control_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    recommendations: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Evidence
    evidence_urls: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    # Report file
    report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_format: Mapped[str] = mapped_column(String(20), nullable=False, default="pdf")

    # Validity
    report_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScanCredits(BaseModel):
    """User's scan credits allocation."""

    __tablename__ = "scan_credits"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uq_scan_credits_user_period"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Credit allocation
    total_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Credit costs by profile
    quick_scan_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    standard_scan_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    deep_scan_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    comprehensive_scan_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    # Period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Rollover
    rollover_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    @property
    def remaining_credits(self) -> int:
        """Calculate remaining credits."""
        return self.total_credits - self.used_credits


class MalwareSignature(BaseModel):
    """Database of known malware signatures."""

    __tablename__ = "malware_signatures"

    signature_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    signature_name: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_type: Mapped[str] = mapped_column(String(50), nullable=False)
    pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[FindingSeverity] = mapped_column(Enum(FindingSeverity), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    references: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
