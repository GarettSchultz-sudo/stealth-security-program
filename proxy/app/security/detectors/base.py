"""
Base detector class for all security detectors.

Provides the interface and common functionality for detectors.
"""

import abc
from abc import abstractmethod
from typing import Any

from app.security.models import DetectionResult, ThreatType


class BaseDetector(abc.ABC):
    """
    Abstract base class for all security detectors.

    Detectors analyze request/response content and return detection results.
    Each detector focuses on a specific threat type.
    """

    def __init__(self, name: str, threat_type: ThreatType, priority: int = 100):
        """
        Initialize the detector.

        Args:
            name: Human-readable detector name
            threat_type: The type of threat this detector identifies
            priority: Detection priority (lower = higher priority, runs first)
        """
        self.name = name
        self.threat_type = threat_type
        self.priority = priority
        self._enabled = True

    @property
    def enabled(self) -> bool:
        """Check if detector is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable this detector."""
        self._enabled = True

    def disable(self) -> None:
        """Disable this detector."""
        self._enabled = False

    @abstractmethod
    async def detect_request(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """
        Analyze a request for threats.

        Args:
            request_data: The parsed request body
            context: Additional context (user_id, agent_id, etc.)

        Returns:
            List of detection results (empty if no threats detected)
        """
        pass

    @abstractmethod
    async def detect_response(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """
        Analyze a response for threats.

        Args:
            response_data: The parsed response body
            context: Additional context (user_id, agent_id, etc.)

        Returns:
            List of detection results (empty if no threats detected)
        """
        pass

    def _create_result(
        self,
        detected: bool,
        severity: str = "low",
        confidence: float = 0.0,
        source: str = "heuristic",
        description: str = "",
        evidence: dict[str, Any] | None = None,
        rule_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DetectionResult:
        """
        Helper to create a detection result.

        Args:
            detected: Whether a threat was detected
            severity: Severity level
            confidence: Confidence score (0-1)
            source: Detection source
            description: Description of what was detected
            evidence: Evidence supporting the detection
            rule_id: ID of the rule that triggered
            metadata: Additional metadata

        Returns:
            A DetectionResult object
        """
        return DetectionResult(
            detected=detected,
            threat_type=self.threat_type,
            severity=severity,
            confidence=confidence,
            source=source,
            description=description,
            evidence=evidence or {},
            rule_id=rule_id,
            metadata=metadata or {},
        )

    def __lt__(self, other: "BaseDetector") -> bool:
        """Compare by priority for sorting."""
        return self.priority < other.priority

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, threat_type={self.threat_type.value})"


class SyncDetector(BaseDetector):
    """
    Base class for synchronous detectors that can run in the hot path.

    These detectors must complete within the latency budget (<10ms).
    Override detect_request_sync and detect_response_sync instead of
    the async versions.
    """

    @abstractmethod
    def detect_request_sync(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Synchronous request detection."""
        pass

    @abstractmethod
    def detect_response_sync(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Synchronous response detection."""
        pass

    async def detect_request(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        return self.detect_request_sync(request_data, context)

    async def detect_response(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        return self.detect_response_sync(response_data, context)


class AsyncDetector(BaseDetector):
    """
    Base class for asynchronous detectors that run in the background.

    These detectors can take longer and may trigger actions after
    the request has been processed (e.g., kill switch on active stream).
    """

    # Mark that this detector runs async and may need to kill streams
    can_kill_stream: bool = False

    async def detect_request(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        # Async detectors typically don't block requests
        return []

    async def detect_response(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        # Override this for async response analysis
        return []
