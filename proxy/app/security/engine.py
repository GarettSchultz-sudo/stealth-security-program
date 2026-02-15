"""
ClawShell Security Engine

Central orchestrator for runtime protection that:
- Coordinates all detectors
- Applies policies and thresholds
- Takes actions (block, warn, alert, etc.)
- Logs security events
- Manages quarantine
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable

from app.security.config import SecurityConfig
from app.security.detectors import (
    BaseDetector,
    SyncDetector,
    AsyncDetector,
    PromptInjectionDetector,
    CredentialDetector,
    DataExfiltrationDetector,
    RunawayDetector,
    ToolAbuseDetector,
    SemanticDetector,
    FallbackSemanticDetector,
)
from app.security.detectors.anomaly import AnomalyDetector
from app.security.rule_engine import CustomRuleDetector
from app.security.models import (
    AgentSecurityPolicy,
    DetectionResult,
    DetectionSource,
    QuarantinedRequest,
    ResponseAction,
    SecurityEvent,
    SeverityLevel,
    ThreatIndicator,
    ThreatType,
)

logger = logging.getLogger(__name__)


@dataclass
class DetectionSummary:
    """Summary of all detections for a request/response."""
    detected: bool = False
    results: list[DetectionResult] = field(default_factory=list)
    max_severity: SeverityLevel = SeverityLevel.LOW
    max_confidence: Decimal = Decimal("0")
    threat_types: set[ThreatType] = field(default_factory=set)
    actions_required: set[ResponseAction] = field(default_factory=set)

    def add_result(self, result: DetectionResult) -> None:
        """Add a detection result."""
        self.results.append(result)
        if result.detected:
            self.detected = True
            self.threat_types.add(result.threat_type)
            # Update max severity
            severity_order = [SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]
            if severity_order.index(result.severity) > severity_order.index(self.max_severity):
                self.max_severity = result.severity
            if result.confidence > self.max_confidence:
                self.max_confidence = result.confidence


class SecurityEngine:
    """
    Central security engine for ClawShell Runtime Protection.

    Coordinates all detectors and applies security policies.
    """

    def __init__(self, config: SecurityConfig | None = None):
        self.config = config or SecurityConfig()
        self._detectors: list[BaseDetector] = []
        self._sync_detectors: list[SyncDetector] = []
        self._async_detectors: list[AsyncDetector] = []

        # Policy storage (in production, this would be database-backed)
        self._policies: dict[str, AgentSecurityPolicy] = {}

        # Threat indicators cache
        self._threat_indicators: dict[str, ThreatIndicator] = {}

        # Action handlers
        self._action_handlers: dict[ResponseAction, Callable] = {}

        # Thread pool for sync detectors
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="security_")

        # Event handlers
        self._event_handlers: list[Callable[[SecurityEvent], None]] = []

        # Initialize built-in detectors
        self._init_builtin_detectors()

    def _init_builtin_detectors(self) -> None:
        """Initialize built-in detectors."""
        builtin = [
            PromptInjectionDetector(),
            CredentialDetector(),
            DataExfiltrationDetector(),
            RunawayDetector(),
            ToolAbuseDetector(),
            AnomalyDetector(),
            CustomRuleDetector(),
            FallbackSemanticDetector(),  # Always available as fallback
            SemanticDetector(),  # Requires sentence-transformers
        ]

        for detector in builtin:
            self.register_detector(detector)

    def register_detector(self, detector: BaseDetector) -> None:
        """Register a detector with the engine."""
        self._detectors.append(detector)

        if isinstance(detector, SyncDetector):
            self._sync_detectors.append(detector)
        elif isinstance(detector, AsyncDetector):
            self._async_detectors.append(detector)

        # Sort by priority
        self._detectors.sort()
        self._sync_detectors.sort()
        self._async_detectors.sort()

        logger.info(f"Registered detector: {detector.name} (priority={detector.priority})")

    def register_action_handler(
        self, action: ResponseAction, handler: Callable
    ) -> None:
        """Register a handler for a specific action type."""
        self._action_handlers[action] = handler

    def register_event_handler(self, handler: Callable[[SecurityEvent], None]) -> None:
        """Register a handler for security events."""
        self._event_handlers.append(handler)

    async def analyze_request(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> DetectionSummary:
        """
        Analyze a request for security threats.

        Runs all detectors in priority order and aggregates results.
        """
        summary = DetectionSummary()
        context = context or {}

        # Run sync detectors in thread pool
        loop = asyncio.get_event_loop()

        sync_tasks = [
            loop.run_in_executor(
                self._executor,
                self._run_sync_detector_request,
                detector,
                request_data,
                context,
            )
            for detector in self._sync_detectors
            if detector.enabled
        ]

        # Run async detectors concurrently
        async_tasks = [
            detector.detect_request(request_data, context)
            for detector in self._async_detectors
            if detector.enabled
        ]

        # Wait for all detectors
        sync_results = await asyncio.gather(*sync_tasks, return_exceptions=True)
        async_results = await asyncio.gather(*async_tasks, return_exceptions=True)

        # Process sync results
        for i, result in enumerate(sync_results):
            if isinstance(result, Exception):
                logger.error(f"Sync detector error: {result}")
            elif isinstance(result, list):
                for r in result:
                    summary.add_result(r)

        # Process async results
        for i, result in enumerate(async_results):
            if isinstance(result, Exception):
                logger.error(f"Async detector error: {result}")
            elif isinstance(result, list):
                for r in result:
                    summary.add_result(r)

        # Check threat indicators
        indicator_results = self._check_threat_indicators(request_data, context)
        for r in indicator_results:
            summary.add_result(r)

        # Determine required actions
        if summary.detected:
            summary.actions_required = self._determine_actions(summary, context)

        return summary

    async def analyze_response(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> DetectionSummary:
        """
        Analyze a response for security threats.

        Runs all detectors and checks for data exfiltration.
        """
        summary = DetectionSummary()
        context = context or {}

        loop = asyncio.get_event_loop()

        sync_tasks = [
            loop.run_in_executor(
                self._executor,
                self._run_sync_detector_response,
                detector,
                response_data,
                context,
            )
            for detector in self._sync_detectors
            if detector.enabled
        ]

        async_tasks = [
            detector.detect_response(response_data, context)
            for detector in self._async_detectors
            if detector.enabled
        ]

        sync_results = await asyncio.gather(*sync_tasks, return_exceptions=True)
        async_results = await asyncio.gather(*async_tasks, return_exceptions=True)

        for result in sync_results:
            if isinstance(result, list):
                for r in result:
                    summary.add_result(r)

        for result in async_results:
            if isinstance(result, list):
                for r in result:
                    summary.add_result(r)

        if summary.detected:
            summary.actions_required = self._determine_actions(summary, context)

        return summary

    def _run_sync_detector_request(
        self,
        detector: SyncDetector,
        request_data: dict[str, Any],
        context: dict[str, Any],
    ) -> list[DetectionResult]:
        """Run a sync detector in thread pool."""
        try:
            return detector.detect_request_sync(request_data, context)
        except Exception as e:
            logger.error(f"Detector {detector.name} error: {e}")
            return []

    def _run_sync_detector_response(
        self,
        detector: SyncDetector,
        response_data: dict[str, Any],
        context: dict[str, Any],
    ) -> list[DetectionResult]:
        """Run a sync detector in thread pool."""
        try:
            return detector.detect_response_sync(response_data, context)
        except Exception as e:
            logger.error(f"Detector {detector.name} error: {e}")
            return []

    def _check_threat_indicators(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any],
    ) -> list[DetectionResult]:
        """Check request against threat indicators (IOCs)."""
        results = []

        # Extract text to check
        text_parts = []
        for msg in request_data.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str):
                text_parts.append(content)

        combined_text = " ".join(text_parts).lower()

        # Check each indicator
        for key, indicator in self._threat_indicators.items():
            if indicator.ioc_value.lower() in combined_text:
                results.append(DetectionResult(
                    detected=True,
                    threat_type=indicator.threat_types[0] if indicator.threat_types else ThreatType.CUSTOM,
                    severity=indicator.severity,
                    confidence=Decimal("0.9"),
                    source=DetectionSource.EXTERNAL,
                    description=f"Threat indicator matched: {indicator.ioc_type}",
                    evidence={
                        "ioc_type": indicator.ioc_type,
                        "ioc_value": indicator.ioc_value[:50] + "..." if len(indicator.ioc_value) > 50 else indicator.ioc_value,
                        "source": indicator.source,
                    },
                    rule_id="threat_indicator_v1",
                ))

        return results

    def _determine_actions(
        self,
        summary: DetectionSummary,
        context: dict[str, Any],
    ) -> set[ResponseAction]:
        """Determine what actions to take based on detections."""
        actions = set()

        # Get policy if available
        agent_id = context.get("agent_id")
        policy = self._policies.get(str(agent_id)) if agent_id else None

        # Always log
        actions.add(ResponseAction.LOG)

        # Based on severity
        if summary.max_severity == SeverityLevel.CRITICAL:
            if summary.max_confidence >= Decimal("0.8"):
                actions.add(ResponseAction.BLOCK)
                if policy and policy.auto_kill_enabled:
                    if summary.max_confidence * 100 >= policy.auto_kill_threshold:
                        actions.add(ResponseAction.KILL)
            actions.add(ResponseAction.ALERT)
            actions.add(ResponseAction.QUARANTINE)

        elif summary.max_severity == SeverityLevel.HIGH:
            if summary.max_confidence >= Decimal("0.85"):
                actions.add(ResponseAction.BLOCK)
            elif summary.max_confidence >= Decimal("0.7"):
                actions.add(ResponseAction.WARN)
            actions.add(ResponseAction.ALERT)

        elif summary.max_severity == SeverityLevel.MEDIUM:
            if summary.max_confidence >= Decimal("0.9"):
                actions.add(ResponseAction.WARN)
            actions.add(ResponseAction.THROTTLE)

        # Threat-type specific actions
        if ThreatType.CREDENTIAL_EXPOSURE in summary.threat_types:
            actions.add(ResponseAction.REDACT)

        if ThreatType.DATA_EXFILTRATION in summary.threat_types:
            if summary.max_severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
                actions.add(ResponseAction.BLOCK)

        # Apply policy overrides
        if policy:
            if policy.detection_level == "enforce":
                if summary.max_severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
                    actions.add(ResponseAction.BLOCK)
            elif policy.detection_level == "warn":
                actions.discard(ResponseAction.BLOCK)
                actions.add(ResponseAction.WARN)

        return actions

    async def take_actions(
        self,
        summary: DetectionSummary,
        request_data: dict[str, Any] | None = None,
        response_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[ResponseAction, Any]:
        """Execute the required actions."""
        context = context or {}
        action_results = {}

        for action in summary.actions_required:
            handler = self._action_handlers.get(action)
            if handler:
                try:
                    result = await handler(
                        action=action,
                        summary=summary,
                        request_data=request_data,
                        response_data=response_data,
                        context=context,
                    )
                    action_results[action] = result
                except Exception as e:
                    logger.error(f"Action handler error for {action}: {e}")
                    action_results[action] = {"error": str(e)}
            else:
                # Default handling
                action_results[action] = self._default_action(action, summary, context)

        # Create and emit security event
        event = self._create_event(summary, action_results, context)
        self._emit_event(event)

        return action_results

    def _default_action(
        self,
        action: ResponseAction,
        summary: DetectionSummary,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Default action handling."""
        if action == ResponseAction.LOG:
            logger.info(
                f"Security event: {summary.max_severity.value} - "
                f"{[t.value for t in summary.threat_types]} - "
                f"confidence={summary.max_confidence}"
            )
            return {"logged": True}

        elif action == ResponseAction.BLOCK:
            return {
                "blocked": True,
                "reason": f"Security policy violation: {summary.max_severity.value}",
            }

        elif action == ResponseAction.WARN:
            return {
                "warning": "This request has been flagged for security review.",
                "severity": summary.max_severity.value,
            }

        elif action == ResponseAction.REDACT:
            return {"redacted": True, "fields_redacted": []}

        return {"action": action.value}

    def _create_event(
        self,
        summary: DetectionSummary,
        action_results: dict[ResponseAction, Any],
        context: dict[str, Any],
    ) -> SecurityEvent:
        """Create a security event from detection results."""
        return SecurityEvent(
            org_id=uuid.UUID(context["org_id"]) if context.get("org_id") else None,
            agent_id=uuid.UUID(context["agent_id"]) if context.get("agent_id") else None,
            request_id=uuid.UUID(context["request_id"]) if context.get("request_id") else None,
            threat_type=list(summary.threat_types)[0] if summary.threat_types else ThreatType.CUSTOM,
            severity=summary.max_severity,
            confidence=summary.max_confidence,
            source=summary.results[0].source if summary.results else DetectionSource.HEURISTIC,
            description=summary.results[0].description if summary.results else "No description",
            evidence={"results": [r.model_dump() for r in summary.results]},
            action_taken=list(action_results.keys())[0] if action_results else ResponseAction.LOG,
            action_details=action_results,
            rule_id=summary.results[0].rule_id if summary.results else None,
        )

    def _emit_event(self, event: SecurityEvent) -> None:
        """Emit a security event to all handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    # Policy management
    def set_policy(self, policy: AgentSecurityPolicy) -> None:
        """Set security policy for an agent."""
        self._policies[str(policy.agent_id)] = policy

    def get_policy(self, agent_id: str) -> AgentSecurityPolicy | None:
        """Get security policy for an agent."""
        return self._policies.get(agent_id)

    # Threat indicator management
    def add_threat_indicator(self, indicator: ThreatIndicator) -> None:
        """Add a threat indicator."""
        key = f"{indicator.ioc_type}:{indicator.ioc_value[:100]}"
        self._threat_indicators[key] = indicator

    def remove_threat_indicator(self, ioc_type: str, ioc_value: str) -> None:
        """Remove a threat indicator."""
        key = f"{ioc_type}:{ioc_value[:100]}"
        self._threat_indicators.pop(key, None)

    # Detector management
    def enable_detector(self, name: str) -> bool:
        """Enable a detector by name."""
        for detector in self._detectors:
            if detector.name == name:
                detector.enable()
                return True
        return False

    def disable_detector(self, name: str) -> bool:
        """Disable a detector by name."""
        for detector in self._detectors:
            if detector.name == name:
                detector.disable()
                return True
        return False

    def get_detector_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all detectors."""
        return {
            d.name: {
                "enabled": d.enabled,
                "threat_type": d.threat_type.value,
                "priority": d.priority,
                "type": "sync" if isinstance(d, SyncDetector) else "async",
            }
            for d in self._detectors
        }

    async def shutdown(self) -> None:
        """Shutdown the engine and cleanup resources."""
        self._executor.shutdown(wait=True)
        logger.info("Security engine shutdown complete")
