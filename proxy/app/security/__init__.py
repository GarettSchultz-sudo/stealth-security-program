"""
ClawShell Runtime Protection Engine

A real-time security layer that monitors, detects, and responds to threats
as OpenClaw AI agents execute through the ClawShell proxy.

Components:
- SecurityEngine: Central orchestrator for all detectors
- SecurityMiddleware: FastAPI middleware for request/response interception
- Detectors: Individual threat detection modules
- Models: Data structures for events, policies, and results
- RuleEngine: Custom organization-specific detection rules
"""

from app.security.config import SecurityConfig, configure_security, get_security_config
from app.security.detectors import (
    AnomalyDetector,
    AsyncDetector,
    BaseDetector,
    CredentialDetector,
    DataExfiltrationDetector,
    FallbackSemanticDetector,
    PromptInjectionDetector,
    RunawayDetector,
    SemanticDetector,
    SyncDetector,
    ToolAbuseDetector,
)
from app.security.engine import DetectionSummary, SecurityEngine
from app.security.middleware import SecurityMiddleware, StreamingSecurityInterceptor
from app.security.models import (
    AgentSecurityPolicy,
    BehavioralBaseline,
    DetectionResult,
    DetectionRule,
    DetectionSource,
    QuarantinedRequest,
    ResponseAction,
    SecurityEvent,
    SeverityLevel,
    ThreatIndicator,
    ThreatType,
)
from app.security.rule_engine import CustomRuleDetector, RuleCompiler, RuleEvaluator

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
    # Rule Engine
    "CustomRuleDetector",
    "RuleCompiler",
    "RuleEvaluator",
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
    "SemanticDetector",
    "FallbackSemanticDetector",
]
