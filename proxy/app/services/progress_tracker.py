"""Progress tracking service for scan jobs.

Publishes progress updates to Redis for real-time SSE streaming.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ScanPhase(str, Enum):
    """Scan execution phases."""
    QUEUED = "queued"
    INITIALIZING = "initializing"
    FETCHING = "fetching"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScanProgress:
    """Progress data for a scan."""
    scan_id: str
    status: str = "queued"
    phase: str = "queued"
    progress: int = 0
    message: str = "Scan queued"
    findings_count: int = 0
    files_scanned: int = 0
    patterns_checked: int = 0
    current_tool: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_time_remaining: Optional[int] = None  # seconds
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string for Redis storage."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "ScanProgress":
        """Deserialize from JSON string."""
        parsed = json.loads(data)
        return cls(**parsed)


class ProgressTracker:
    """
    Tracks and publishes scan progress to Redis.

    Usage:
        tracker = ProgressTracker(redis_client, scan_id)
        await tracker.start()
        await tracker.update(phase="scanning", progress=50, message="Running Nuclei...")
        await tracker.complete(findings_count=12)
    """

    # Phase progress ranges
    PHASE_RANGES = {
        ScanPhase.QUEUED: (0, 0),
        ScanPhase.INITIALIZING: (0, 5),
        ScanPhase.FETCHING: (5, 15),
        ScanPhase.SCANNING: (15, 85),
        ScanPhase.ANALYZING: (85, 95),
        ScanPhase.COMPLETED: (95, 100),
        ScanPhase.FAILED: (0, 0),
    }

    def __init__(self, redis_client: Any, scan_id: str, ttl: int = 3600):
        """
        Initialize progress tracker.

        Args:
            redis_client: Redis client instance
            scan_id: UUID of the scan
            ttl: Time-to-live for progress data in seconds (default: 1 hour)
        """
        self.redis = redis_client
        self.scan_id = scan_id
        self.ttl = ttl
        self.progress_key = f"scan:{scan_id}:progress"
        self._progress = ScanProgress(scan_id=scan_id)
        self._start_time: Optional[float] = None

    async def start(self) -> None:
        """Mark scan as started."""
        self._start_time = datetime.utcnow().timestamp()
        self._progress.status = "running"
        self._progress.phase = ScanPhase.INITIALIZING.value
        self._progress.progress = 5
        self._progress.message = "Initializing scan..."
        self._progress.started_at = datetime.utcnow().isoformat()
        await self._save()

    async def update(
        self,
        phase: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        findings_count: Optional[int] = None,
        files_scanned: Optional[int] = None,
        patterns_checked: Optional[int] = None,
        current_tool: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Update scan progress.

        Args:
            phase: Current scan phase
            progress: Progress percentage (0-100)
            message: Human-readable progress message
            findings_count: Number of findings so far
            files_scanned: Number of files scanned
            patterns_checked: Number of patterns checked
            current_tool: Currently running tool name
            metadata: Additional metadata
        """
        if phase:
            self._progress.phase = phase

        if progress is not None:
            self._progress.progress = min(100, max(0, progress))

        if message:
            self._progress.message = message

        if findings_count is not None:
            self._progress.findings_count = findings_count

        if files_scanned is not None:
            self._progress.files_scanned = files_scanned

        if patterns_checked is not None:
            self._progress.patterns_checked = patterns_checked

        if current_tool:
            self._progress.current_tool = current_tool

        if metadata:
            self._progress.metadata.update(metadata)

        # Estimate time remaining
        if self._start_time and self._progress.progress > 5:
            elapsed = datetime.utcnow().timestamp() - self._start_time
            if self._progress.progress > 0:
                total_estimated = elapsed / (self._progress.progress / 100)
                remaining = int(total_estimated - elapsed)
                self._progress.estimated_time_remaining = max(0, remaining)

        await self._save()

    async def set_phase(
        self,
        phase: ScanPhase,
        message: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Set scan phase with automatic progress calculation.

        Args:
            phase: Scan phase enum value
            message: Optional custom message
            **kwargs: Additional update parameters
        """
        min_progress, max_progress = self.PHASE_RANGES.get(phase, (0, 0))

        # Calculate progress within phase range
        # For scanning phase, we use the passed progress value scaled
        if phase == ScanPhase.SCANNING and "progress" in kwargs:
            # Scale scanning progress (0-100) to phase range (15-85)
            scan_progress = kwargs["progress"]
            phase_progress = min_progress + (max_progress - min_progress) * scan_progress / 100
            kwargs["progress"] = int(phase_progress)
        else:
            kwargs["progress"] = max_progress

        await self.update(phase=phase.value, message=message, **kwargs)

    async def increment_findings(self, count: int = 1) -> None:
        """Increment the findings count."""
        self._progress.findings_count += count
        await self._save()

    async def complete(
        self,
        findings_count: Optional[int] = None,
        files_scanned: Optional[int] = None,
        patterns_checked: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Mark scan as completed."""
        self._progress.status = "completed"
        self._progress.phase = ScanPhase.COMPLETED.value
        self._progress.progress = 100
        self._progress.message = "Scan completed successfully"
        self._progress.completed_at = datetime.utcnow().isoformat()
        self._progress.current_tool = None
        self._progress.estimated_time_remaining = 0

        if findings_count is not None:
            self._progress.findings_count = findings_count

        if files_scanned is not None:
            self._progress.files_scanned = files_scanned

        if patterns_checked is not None:
            self._progress.patterns_checked = patterns_checked

        if metadata:
            self._progress.metadata.update(metadata)

        await self._save()

    async def fail(self, error: str, metadata: Optional[dict] = None) -> None:
        """Mark scan as failed."""
        self._progress.status = "failed"
        self._progress.phase = ScanPhase.FAILED.value
        self._progress.message = f"Scan failed: {error}"
        self._progress.error = error
        self._progress.completed_at = datetime.utcnow().isoformat()
        self._progress.current_tool = None
        self._progress.estimated_time_remaining = 0

        if metadata:
            self._progress.metadata.update(metadata)

        await self._save()

    async def get_progress(self) -> ScanProgress:
        """Get current progress."""
        return self._progress

    async def _save(self) -> None:
        """Save progress to Redis."""
        try:
            await self.redis.set(
                self.progress_key,
                self._progress.to_json(),
                ex=self.ttl
            )
            logger.debug(f"Progress saved for scan {self.scan_id}: {self._progress.progress}%")
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    @classmethod
    async def get(cls, redis_client: Any, scan_id: str) -> Optional[ScanProgress]:
        """
        Get progress for a scan without creating a tracker.

        Args:
            redis_client: Redis client instance
            scan_id: UUID of the scan

        Returns:
            ScanProgress if found, None otherwise
        """
        progress_key = f"scan:{scan_id}:progress"
        try:
            data = await redis_client.get(progress_key)
            if data:
                return ScanProgress.from_json(data)
        except Exception as e:
            logger.error(f"Failed to get progress: {e}")
        return None
