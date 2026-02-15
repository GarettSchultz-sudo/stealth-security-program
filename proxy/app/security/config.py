"""
Security engine configuration.

Defines thresholds, detection levels, and response policies.
"""

from dataclasses import dataclass, field

from app.security.models import ResponseAction, SeverityLevel


@dataclass
class DetectionThresholds:
    """Thresholds for various detection types."""

    # Prompt Injection
    injection_confidence_high: float = 0.8
    injection_confidence_medium: float = 0.5
    injection_confidence_low: float = 0.2

    # Data Exfiltration
    max_data_volume_kb: int = 100  # Alert if > 100KB in single response
    entropy_threshold: float = 4.5  # High entropy indicates potential secrets

    # Runaway Detection
    max_calls_per_minute: int = 60
    max_calls_per_hour: int = 500
    similar_request_threshold: int = 5  # Same content N times

    # Behavioral Anomaly
    anomaly_z_score_threshold: float = 2.0
    baseline_window_days: int = 7
    min_baseline_samples: int = 100

    # Credential Detection
    min_entropy_for_secrets: float = 4.0
    max_secret_length: int = 256


@dataclass
class ResponsePolicy:
    """Policy mapping detections to responses."""

    # By severity
    critical_action: ResponseAction = ResponseAction.BLOCK
    high_action: ResponseAction = ResponseAction.ALERT
    medium_action: ResponseAction = ResponseAction.LOG
    low_action: ResponseAction = ResponseAction.LOG
    info_action: ResponseAction = ResponseAction.LOG

    # By threat type (overrides severity)
    threat_actions: dict[str, ResponseAction] = field(
        default_factory=lambda: {
            "prompt_injection": ResponseAction.BLOCK,
            "credential_exposure": ResponseAction.REDACT,
            "data_exfiltration": ResponseAction.BLOCK,
            "runaway_loop": ResponseAction.THROTTLE,
        }
    )

    # Escalation (number of times before escalating)
    escalation_threshold: int = 3
    escalation_window_hours: int = 24


@dataclass
class SecurityConfig:
    """Main security configuration."""

    # Detection levels: monitor (log only), warn (alerts), enforce (block)
    default_detection_level: str = "monitor"

    # Enable/disable specific detectors
    enable_prompt_injection_detection: bool = True
    enable_data_exfiltration_detection: bool = True
    enable_credential_detection: bool = True
    enable_runaway_detection: bool = True
    enable_behavioral_anomaly: bool = True
    enable_tool_abuse_detection: bool = True
    enable_skill_scanning: bool = True

    # Thresholds
    thresholds: DetectionThresholds = field(default_factory=DetectionThresholds)

    # Response policies
    response_policy: ResponsePolicy = field(default_factory=ResponsePolicy)

    # Kill switch settings
    auto_kill_enabled: bool = False
    auto_kill_threshold: float = 0.95  # Confidence threshold for auto-kill
    kill_requires_confirmation: bool = True

    # Latency budget (milliseconds)
    max_sync_detection_ms: int = 10
    max_total_middleware_ms: int = 50

    # Telemetry
    enable_event_streaming: bool = True
    event_retention_days: int = 90
    baseline_update_interval_seconds: int = 300

    # External integrations
    virustotal_api_key: str | None = None
    abuseipdb_api_key: str | None = None

    # Rule hot-reload
    rule_reload_interval_seconds: int = 60

    def get_action_for_detection(
        self,
        threat_type: str,
        severity: SeverityLevel,
        confidence: float,
        detection_level: str | None = None,
    ) -> ResponseAction:
        """
        Determine the appropriate response action for a detection.

        Args:
            threat_type: Type of threat detected
            severity: Severity level
            confidence: Detection confidence (0-1)
            detection_level: Override detection level (monitor/warn/enforce)

        Returns:
            The action to take
        """
        level = detection_level or self.default_detection_level

        # Monitor level: only log
        if level == "monitor":
            return ResponseAction.LOG

        # Check threat-specific action
        if threat_type in self.response_policy.threat_actions:
            base_action = self.response_policy.threat_actions[threat_type]
            if level == "enforce":
                return base_action
            elif level == "warn" and base_action in [
                ResponseAction.BLOCK,
                ResponseAction.QUARANTINE,
                ResponseAction.KILL,
            ]:
                return ResponseAction.ALERT
            return base_action

        # Severity-based action
        severity_actions = {
            SeverityLevel.CRITICAL: self.response_policy.critical_action,
            SeverityLevel.HIGH: self.response_policy.high_action,
            SeverityLevel.MEDIUM: self.response_policy.medium_action,
            SeverityLevel.LOW: self.response_policy.low_action,
            SeverityLevel.INFO: self.response_policy.info_action,
        }

        action = severity_actions.get(severity, ResponseAction.LOG)

        # Downgrade aggressive actions in warn mode
        if level == "warn" and action in [
            ResponseAction.BLOCK,
            ResponseAction.QUARANTINE,
            ResponseAction.KILL,
        ]:
            return ResponseAction.ALERT

        return action


# Global config instance
_security_config: SecurityConfig | None = None


def get_security_config() -> SecurityConfig:
    """Get the security configuration singleton."""
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config


def configure_security(config: SecurityConfig) -> None:
    """Set the security configuration."""
    global _security_config
    _security_config = config
