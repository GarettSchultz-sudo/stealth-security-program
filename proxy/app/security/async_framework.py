"""
Async Detection Framework

Provides infrastructure for background detection tasks that can:
- Run asynchronously without blocking request processing
- Trigger actions after detection (including stream kills)
- Aggregate results from multiple async detectors
- Handle timeouts and error recovery
"""

import asyncio
import contextlib
import logging
import uuid
from abc import abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.security.detectors.base import BaseDetector
from app.security.models import (
    DetectionResult,
    SeverityLevel,
    ThreatType,
)

logger = logging.getLogger(__name__)


@dataclass
class AsyncDetectionTask:
    """Represents a pending or completed async detection task."""

    task_id: str
    detector_name: str
    request_id: str | None = None
    agent_id: str | None = None
    status: str = "pending"  # pending, running, completed, failed, killed
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    results: list[DetectionResult] = field(default_factory=list)
    error: str | None = None


@dataclass
class StreamKillRequest:
    """Request to kill an active stream."""

    stream_id: str
    agent_id: str
    reason: str
    severity: SeverityLevel
    confidence: float
    triggered_by: str  # detector name
    created_at: datetime = field(default_factory=datetime.utcnow)


class AsyncDetectorManager:
    """
    Manages async detection tasks and coordinates with streaming responses.

    This class handles:
    - Spawning and tracking background detection tasks
    - Processing results and triggering follow-up actions
    - Managing stream kill requests
    - Timeout handling and cleanup
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 50,
        task_timeout_seconds: float = 30.0,
        result_callback: Callable[[AsyncDetectionTask], Coroutine] | None = None,
        kill_callback: Callable[[StreamKillRequest], Coroutine] | None = None,
    ):
        self._max_concurrent = max_concurrent_tasks
        self._timeout = task_timeout_seconds
        self._result_callback = result_callback
        self._kill_callback = kill_callback

        self._tasks: dict[str, AsyncDetectionTask] = {}
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._stream_sessions: dict[str, str] = {}  # agent_id -> stream_id
        self._pending_kills: list[StreamKillRequest] = []

        self._lock = asyncio.Lock()

    async def submit_detection(
        self,
        detector: "AsyncDetectionBase",
        content: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Submit a detection task for background processing.

        Returns task_id for tracking.
        """
        task_id = str(uuid.uuid4())
        context = context or {}

        # Create task record
        detection_task = AsyncDetectionTask(
            task_id=task_id,
            detector_name=detector.name,
            request_id=context.get("request_id"),
            agent_id=context.get("agent_id"),
            status="pending",
        )

        async with self._lock:
            self._tasks[task_id] = detection_task

        # Spawn background task
        async_task = asyncio.create_task(
            self._run_detection(detector, content, context, detection_task)
        )
        self._active_tasks[task_id] = async_task

        return task_id

    async def _run_detection(
        self,
        detector: "AsyncDetectionBase",
        content: dict[str, Any],
        context: dict[str, Any],
        task: AsyncDetectionTask,
    ) -> None:
        """Execute detection with timeout and error handling."""
        task.status = "running"

        try:
            # Run with timeout
            results = await asyncio.wait_for(
                detector.detect_async(content, context),
                timeout=self._timeout,
            )

            task.results = results
            task.status = "completed"
            task.completed_at = datetime.utcnow()

            # Check for kill-worthy detections
            if detector.can_kill_stream:
                await self._check_kill_trigger(detector, results, context)

            # Call result callback if set
            if self._result_callback:
                await self._result_callback(task)

        except TimeoutError:
            task.status = "timeout"
            task.error = f"Detection timed out after {self._timeout}s"
            logger.warning(f"Async detection timeout: {detector.name}")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"Async detection failed: {detector.name} - {e}")

        finally:
            async with self._lock:
                self._active_tasks.pop(task.task_id, None)

    async def _check_kill_trigger(
        self,
        detector: "AsyncDetectionBase",
        results: list[DetectionResult],
        context: dict[str, Any],
    ) -> None:
        """Check if results warrant a stream kill."""
        agent_id = context.get("agent_id")
        if not agent_id:
            return

        for result in results:
            if not result.detected:
                continue

            # Check kill conditions
            should_kill = (
                result.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
                and result.confidence >= detector.kill_confidence_threshold
            )

            if should_kill:
                stream_id = self._stream_sessions.get(agent_id)
                if stream_id:
                    kill_request = StreamKillRequest(
                        stream_id=stream_id,
                        agent_id=agent_id,
                        reason=result.description,
                        severity=result.severity,
                        confidence=float(result.confidence),
                        triggered_by=detector.name,
                    )
                    self._pending_kills.append(kill_request)

                    if self._kill_callback:
                        await self._kill_callback(kill_request)

                    logger.critical(
                        f"Stream kill requested: agent={agent_id} "
                        f"detector={detector.name} severity={result.severity.value}"
                    )

    def register_stream(self, agent_id: str, stream_id: str) -> None:
        """Register an active stream session."""
        self._stream_sessions[agent_id] = stream_id

    def unregister_stream(self, agent_id: str) -> None:
        """Unregister a stream session."""
        self._stream_sessions.pop(agent_id, None)

    def get_pending_kills(self, agent_id: str | None = None) -> list[StreamKillRequest]:
        """Get pending kill requests, optionally filtered by agent."""
        if agent_id:
            return [k for k in self._pending_kills if k.agent_id == agent_id]
        return list(self._pending_kills)

    def clear_pending_kills(self, agent_id: str | None = None) -> int:
        """Clear pending kill requests and return count cleared."""
        if agent_id:
            count = sum(1 for k in self._pending_kills if k.agent_id == agent_id)
            self._pending_kills = [k for k in self._pending_kills if k.agent_id != agent_id]
        else:
            count = len(self._pending_kills)
            self._pending_kills.clear()
        return count

    async def get_task_status(self, task_id: str) -> AsyncDetectionTask | None:
        """Get status of a detection task."""
        return self._tasks.get(task_id)

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float = 10.0,
    ) -> AsyncDetectionTask | None:
        """Wait for a task to complete."""
        if task_id not in self._active_tasks:
            return self._tasks.get(task_id)

        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(
                self._active_tasks[task_id],
                timeout=timeout,
            )

        return self._tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id not in self._active_tasks:
            return False

        self._active_tasks[task_id].cancel()

        if task_id in self._tasks:
            self._tasks[task_id].status = "cancelled"

        return True

    def get_stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        status_counts = {}
        for task in self._tasks.values():
            status_counts[task.status] = status_counts.get(task.status, 0) + 1

        return {
            "total_tasks": len(self._tasks),
            "active_tasks": len(self._active_tasks),
            "status_breakdown": status_counts,
            "active_streams": len(self._stream_sessions),
            "pending_kills": len(self._pending_kills),
        }


class AsyncDetectionBase(BaseDetector):
    """
    Enhanced base class for async detectors with full framework integration.

    Provides:
    - Async detection with timeout handling
    - Stream kill capability
    - Result aggregation
    - Progress callbacks
    """

    can_kill_stream: bool = False
    kill_confidence_threshold: float = 0.9

    def __init__(
        self,
        name: str,
        threat_type: ThreatType,
        priority: int = 100,
    ):
        super().__init__(name, threat_type, priority)
        self._progress_callback: Callable[[float], Coroutine] | None = None

    def set_progress_callback(self, callback: Callable[[float], Coroutine]) -> None:
        """Set callback for progress updates (0.0 to 1.0)."""
        self._progress_callback = callback

    async def report_progress(self, progress: float) -> None:
        """Report detection progress."""
        if self._progress_callback:
            await self._progress_callback(progress)

    @abstractmethod
    async def detect_async(
        self,
        content: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """
        Perform async detection.

        Override this method instead of detect_request/detect_response.

        Args:
            content: Either request_data or response_data
            context: Detection context

        Returns:
            List of detection results
        """
        pass

    async def detect_request(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Not used for async detectors."""
        return []

    async def detect_response(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Not used for async detectors."""
        return []


class BackgroundAnalysisDetector(AsyncDetectionBase):
    """
    Example async detector for background analysis.

    Performs expensive analysis that can't block request processing:
    - ML model inference
    - External API calls
    - Large-scale pattern analysis
    """

    can_kill_stream: bool = True
    kill_confidence_threshold: float = 0.85

    def __init__(self):
        super().__init__(
            name="background_analyzer",
            threat_type=ThreatType.BEHAVIORAL_ANOMALY,
            priority=150,  # Low priority, runs last
        )
        self._analysis_functions: list[Callable] = []

    def register_analysis(self, func: Callable[[dict, dict], Coroutine]) -> None:
        """Register an async analysis function."""
        self._analysis_functions.append(func)

    async def detect_async(
        self,
        content: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Run all registered analysis functions."""
        results = []
        context = context or {}

        total_functions = len(self._analysis_functions)
        for i, func in enumerate(self._analysis_functions):
            try:
                func_results = await func(content, context)
                if func_results:
                    results.extend(func_results)

                # Report progress
                await self.report_progress((i + 1) / total_functions)

            except Exception as e:
                logger.error(f"Analysis function failed: {e}")

        return results
