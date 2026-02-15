"""
ClawShell Runtime Protection Engine

A real-time security layer that monitors, detects, and responds to threats
as OpenClaw AI agents execute through the ClawShell proxy.

Components:
- SecurityEngine: Central orchestrator for all detectors
- SecurityMiddleware: FastAPI middleware for request/response interception
- Detectors: Individual threat detection modules
- Models: Data structures for events, policies, and results
"""

from app.security.engine import SecurityEngine, DetectionSummary
from app.security.middleware import SecurityMiddleware, StreamingSecurityInterceptor
from app.security.models import (
    SecurityEvent,
    ThreatType,
    SeverityLevel,
    DetectionResult,
    DetectionSource,
    ResponseAction,
    AgentSecurityPolicy,
    BehavioralBaseline,
    QuarantinedRequest,
    DetectionRule,
    ThreatIndicator,
)
from app.security.config import SecurityConfig, get_security_config, configure_security
from app.security.detectors import (
    BaseDetector,
    SyncDetector,
    AsyncDetector,
    PromptInjectionDetector,
    CredentialDetector,
    DataExfiltrationDetector,
    RunawayDetector,
    ToolAbuseDetector,
    AnomalyDetector,
)

__all__ = [
    # Engine
    "SecurityEngine",
    "DetectionSummary",
    # Middleware
    "SecurityMiddleware",
    "StreamingSecurityInterceptor",
    # Models
    "SecurityEvent",
    "ThreatType",
    "SeverityLevel",
    "DetectionResult",
    "DetectionSource",
    "ResponseAction",
    "AgentSecurityPolicy",
    "BehavioralBaseline",
    "QuarantinedRequest",
    "DetectionRule",
    "ThreatIndicator",
    # Config
    "SecurityConfig",
    "get_security_config",
    "configure_security",
    # Detectors
    "BaseDetector",
    "SyncDetector",
    "AsyncDetector",
    "PromptInjectionDetector",
    "CredentialDetector",
    "DataExfiltrationDetector",
    "RunawayDetector",
    "ToolAbuseDetector",
    "AnomalyDetector",
]
