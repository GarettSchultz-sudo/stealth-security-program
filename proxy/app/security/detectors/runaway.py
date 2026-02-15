"""
Runaway Loop Detector

Detects runaway agent behavior including:
- Excessive API calls in short time periods
- Similar/identical repeated requests
- Budget consumption rate anomalies
"""

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.security.detectors.base import SyncDetector
from app.security.models import DetectionResult, ThreatType


@dataclass
class AgentActivity:
    """Track activity for an agent."""

    request_count: int = 0
    request_times: list[float] = field(default_factory=list)
    request_hashes: list[str] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    window_start: float = field(default_factory=time.time)


class RunawayDetector(SyncDetector):
    """Detects runaway agent behavior."""

    def __init__(self):
        super().__init__(
            name="runaway_detector",
            threat_type=ThreatType.RUNAWAY_LOOP,
            priority=20,
        )

        # Track activity per agent
        self._agent_activity: dict[str, AgentActivity] = defaultdict(AgentActivity)

        # Thresholds
        self._max_calls_per_minute = 60
        self._max_calls_per_5_minutes = 200
        self._similar_request_threshold = 5  # Same request N times
        self._window_size_seconds = 300  # 5 minutes

    def detect_request_sync(
        self,
        request_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Check for runaway patterns in requests."""
        results = []

        if not context:
            return results

        agent_id = context.get("agent_id")
        user_id = context.get("user_id")

        if not agent_id:
            return results

        activity_key = f"{user_id}:{agent_id}"
        activity = self._agent_activity[activity_key]

        current_time = time.time()

        # Clean old entries
        activity.request_times = [
            t for t in activity.request_times if current_time - t < self._window_size_seconds
        ]
        activity.request_hashes = activity.request_hashes[-100:]  # Keep last 100

        # Record this request
        activity.request_count += 1
        activity.request_times.append(current_time)

        # Calculate request hash for similarity detection
        request_hash = self._hash_request(request_data)
        activity.request_hashes.append(request_hash)

        # Check rate
        rate_results = self._check_rate(activity, current_time)
        results.extend(rate_results)

        # Check similar requests
        similarity_results = self._check_similarity(activity)
        results.extend(similarity_results)

        return results

    def detect_response_sync(
        self,
        response_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectionResult]:
        """Update activity tracking after response."""
        # Response detection is handled in request detection
        # This is for future enhancements
        return []

    def _hash_request(self, request_data: dict[str, Any]) -> str:
        """Create a hash of the request for similarity detection."""
        # Normalize and hash key fields
        key_content = []

        if "model" in request_data:
            key_content.append(f"model:{request_data['model']}")

        # Hash messages (normalized)
        messages = request_data.get("messages", [])
        for msg in messages[-3:]:  # Last 3 messages
            content = msg.get("content", "")
            if isinstance(content, str):
                # Normalize whitespace
                normalized = " ".join(content.split())
                key_content.append(normalized[:200])  # Truncate for consistent hashing

        combined = "|".join(key_content)
        return hashlib.md5(combined.encode()).hexdigest()

    def _check_rate(self, activity: AgentActivity, current_time: float) -> list[DetectionResult]:
        """Check if request rate exceeds thresholds."""
        results = []

        # Check per-minute rate
        one_minute_ago = current_time - 60
        requests_last_minute = sum(1 for t in activity.request_times if t > one_minute_ago)

        if requests_last_minute > self._max_calls_per_minute:
            results.append(
                self._create_result(
                    detected=True,
                    severity="high",
                    confidence=0.9,
                    source="behavioral",
                    description=f"High request rate detected: {requests_last_minute} calls/minute",
                    evidence={
                        "requests_per_minute": requests_last_minute,
                        "threshold": self._max_calls_per_minute,
                    },
                    rule_id="runaway_rate_v1",
                )
            )

        # Check 5-minute rate
        five_minutes_ago = current_time - 300
        requests_last_5min = sum(1 for t in activity.request_times if t > five_minutes_ago)

        if requests_last_5min > self._max_calls_per_5_minutes:
            results.append(
                self._create_result(
                    detected=True,
                    severity="critical",
                    confidence=0.95,
                    source="behavioral",
                    description=f"Runaway loop detected: {requests_last_5min} calls in 5 minutes",
                    evidence={
                        "requests_5_minutes": requests_last_5min,
                        "threshold": self._max_calls_per_5_minutes,
                    },
                    rule_id="runaway_loop_v1",
                )
            )

        return results

    def _check_similarity(self, activity: AgentActivity) -> list[DetectionResult]:
        """Check for repeated similar requests."""
        results = []

        if len(activity.request_hashes) < self._similar_request_threshold:
            return results

        # Count occurrences of recent hashes
        recent_hashes = activity.request_hashes[-20:]  # Last 20 requests
        hash_counts: dict[str, int] = defaultdict(int)
        for h in recent_hashes:
            hash_counts[h] += 1

        # Find any hash that appears too many times
        for hash_val, count in hash_counts.items():
            if count >= self._similar_request_threshold:
                results.append(
                    self._create_result(
                        detected=True,
                        severity="medium",
                        confidence=0.8,
                        source="behavioral",
                        description=f"Repeated similar requests detected: {count} times",
                        evidence={
                            "repeat_count": count,
                            "threshold": self._similar_request_threshold,
                            "request_hash": hash_val[:8],
                        },
                        rule_id="runaway_repeat_v1",
                    )
                )
                break  # Only report once

        return results

    def reset_agent(self, agent_key: str) -> None:
        """Reset activity tracking for an agent."""
        if agent_key in self._agent_activity:
            del self._agent_activity[agent_key]
