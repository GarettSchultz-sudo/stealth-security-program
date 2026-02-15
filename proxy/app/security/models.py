"""
Pydantic models for the security engine.

Defines data structures for threats, alerts, events, and responses.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ThreatType(str, enum.Enum):
    """Categories of security threats detected by ClawShell."""

    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    CREDENTIAL_EXPOSURE = "credential_exposure"
    TOOL_ABUSE = "tool_abuse"
    RUNAWAY_LOOP = "runaway_loop"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    SKILL_VIOLATION = "skill_violation"
    NETWORK_ABUSE = "network_abuse"
    PII_EXPOSURE = "pii_exposure"
    CUSTOM = "custom"


class SeverityLevel(str, enum.Enum):
    """Severity levels for security events."""

    CRITICAL = "critical"  # Immediate action required, potential breach
    HIGH = "high"  # Significant threat, likely malicious
    MEDIUM = "medium"  # Suspicious activity, needs review
    LOW = "low"  # Minor concern, informational
    INFO = "info"  # Informational only, no action needed


class ResponseAction(str, enum.Enum):
    """Actions that can be taken in response to a detection."""

    LOG = "log"  # Record event only
    ALERT = "alert"  # Send notification
    WARN = "warn"  # Insert warning in response
    THROTTLE = "throttle"  # Rate-limit API calls
    DOWNGRADE = "downgrade"  # Force cheaper/safer model
    BLOCK = "block"  # Reject the request
    QUARANTINE = "quarantine"  # Block and save for review
    KILL = "kill"  # Terminate all agent connections
    REDACT = "redact"  # Remove sensitive data before proceeding


class DetectionSource(str, enum.Enum):
    """Source of the detection."""

    SIGNATURE = "signature"  # Pattern/signature match
    HEURISTIC = "heuristic"  # Rule-based heuristic
    BEHAVIORAL = "behavioral"  # Anomaly from baseline
    SEMANTIC = "semantic"  # Semantic/embedding analysis
    EXTERNAL = "external"  # External threat intel
    USER_REPORT = "user_report"  # User-reported issue


class DetectionResult(BaseModel):
    """Result from a single detector."""

    detected: bool = False
    threat_type: ThreatType
    severity: SeverityLevel = SeverityLevel.LOW
    confidence: Decimal = Field(default=Decimal("0.0"), ge=0, le=1)
    source: DetectionSource = DetectionSource.HEURISTIC
    description: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    rule_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityEvent(BaseModel):
    """A security event to be logged and potentially acted upon."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    skill_id: uuid.UUID | None = None
    request_id: uuid.UUID | None = None

    # Detection details
    threat_type: ThreatType
    severity: SeverityLevel
    confidence: Decimal = Field(default=Decimal("0.0"), ge=0, le=1)
    source: DetectionSource

    # Content summaries (not full request/response to avoid sensitive data)
    request_summary: str | None = None
    response_summary: str | None = None

    # What was detected
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)

    # Response taken
    action_taken: ResponseAction = ResponseAction.LOG
    action_details: dict[str, Any] = Field(default_factory=dict)

    # Rule that triggered this
    rule_id: str | None = None
    rule_name: str | None = None

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class AgentSecurityPolicy(BaseModel):
    """Security policy for an agent."""

    agent_id: uuid.UUID
    org_id: uuid.UUID

    # Detection level
    detection_level: str = "monitor"  # monitor, warn, enforce

    # Tool policies
    tool_allowlist: list[str] = Field(default_factory=list)
    tool_denylist: list[str] = Field(default_factory=list)

    # Auto-kill settings
    auto_kill_enabled: bool = False
    auto_kill_threshold: int = 100  # Confidence threshold for auto-kill

    # Notification settings
    notify_on_critical: bool = True
    notify_on_high: bool = True
    notify_on_medium: bool = False
    notification_channels: list[str] = Field(default_factory=lambda: ["dashboard"])

    # Thresholds
    rate_limit_per_minute: int | None = None
    max_tokens_per_request: int | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BehavioralBaseline(BaseModel):
    """Behavioral baseline for an agent."""

    agent_id: uuid.UUID
    metric_name: str

    # Statistical measures
    baseline_mean: Decimal
    baseline_stddev: Decimal
    sample_count: int

    # Current value
    current_value: Decimal | None = None

    # Window
    window_start: datetime
    window_end: datetime

    # Z-score threshold for anomaly
    anomaly_threshold: Decimal = Decimal("2.0")

    @property
    def is_anomalous(self) -> bool:
        """Check if current value is anomalous."""
        if self.current_value is None or self.baseline_stddev == 0:
            return False
        z_score = abs((self.current_value - self.baseline_mean) / self.baseline_stddev)
        return z_score > self.anomaly_threshold


class QuarantinedRequest(BaseModel):
    """A request that has been quarantined for review."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID
    agent_id: uuid.UUID | None = None

    # Encrypted request body for later review
    request_body_encrypted: str

    # Why it was quarantined
    detection_reasons: list[DetectionResult] = Field(default_factory=list)

    # Status
    status: str = "pending_review"  # pending_review, approved, rejected

    # Review details
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class DetectionRule(BaseModel):
    """A detection rule that can be matched against requests/responses."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    org_id: uuid.UUID | None = None  # None for built-in rules
    name: str
    description: str | None = None

    # Rule type
    rule_type: str = "pattern"  # pattern, threshold, behavioral, composite

    # Rule definition (format depends on type)
    # Pattern: { "patterns": [...], "match_type": "any|all" }
    # Threshold: { "metric": "...", "operator": ">|<|=", "value": ... }
    # Behavioral: { "metric": "...", "z_score_threshold": ... }
    # Composite: { "rules": [...], "logic": "and|or" }
    rule_definition: dict[str, Any]

    # Severity when matched
    severity: SeverityLevel = SeverityLevel.MEDIUM

    # Action to take
    action: ResponseAction = ResponseAction.ALERT

    # State
    enabled: bool = True
    is_builtin: bool = False

    # Metadata
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ThreatIndicator(BaseModel):
    """An indicator of compromise (IOC)."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    # Type of indicator
    ioc_type: str  # ip, domain, hash, pattern, url

    # The indicator value
    ioc_value: str

    # Source of the indicator
    source: str  # e.g., "virustotal", "abuseipdb", "custom"

    # Severity
    severity: SeverityLevel = SeverityLevel.MEDIUM

    # Related threat types
    threat_types: list[ThreatType] = Field(default_factory=list)

    # Expiration
    expires_at: datetime | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
